# test_sdr.py
#
# Script to test the functionality of invest_natcap.sdr as a replacement for
# the sediment model as it's used in the OPAL/MAFE tool.
#
# This script takes no command-line arguments.
#
# DEPENDENCIES:
# python 2.7
# invest_natcap
# adept
# InVEST dev environment

import os
import tempfile
import logging
import random
import shutil
import multiprocessing

from osgeo import ogr
from osgeo import gdal
import matplotlib
matplotlib.use('Agg')  # for rendering plots without $DISPLAY set.
import matplotlib.pyplot as plt
import numpy
import scipy
from invest_natcap import raster_utils
from invest_natcap.sdr import sdr
from adept import static_maps
from adept import preprocessing

LOGGER = logging.getLogger('sdr_simulations')

def test_static_map_quality(base_run, base_static_map, landuse_uri,
    impact_lucode, watersheds_uri, workspace, config, num_iterations=5,
    start_ws=0, start_impact=0):
# base_run = sed_exp.tif, in the case of the sediment model, run on the base LULC
# base_static_map = the static map generated from the base_run and the whole
#   landscape converted to the target impact type
# landuse_uri = a URI to the LULC used for the base static map
# impact_lucode = a numeric landuse code to use to convert the underlying lulc
# watersheds = a URI to an OGR vector to use for watersheds. must have ws_id
#   column.
# num_iterations = the number of iterations to run within each watershed.
# workspace = the workspace in which all of this should run
# start_ws = int id of which watershed in which to start the simulations.
# start_impact = int id of which impact site to start on.  This only applies to
# the starting watershed, all others will start at 0.

    old_tempdir = tempfile.tempdir
    temp_dir = os.path.join(workspace, 'tmp')  # for ALL tempfiles
    tempfile.tempdir = temp_dir  # all tempfiles will be saved here.

    # make a copy of the configuration dictionary so that we don't modify it
    # accidentally.
    config = config.copy()

    # make all the folders we know about at the moment
    raster_utils.create_directories([workspace, temp_dir])

    # Open a logfile so we can incrementally write model data we care about
    logfile_uri = os.path.join(workspace, 'impact_site_simulation.csv')
    logfile = open(logfile_uri, 'a' if start_ws > 0 else 'w')
    labels = ['ws_id', 'Impact ID', 'Impact Area', 'Static Estimate',
        'InVEST Estimate', 'Estimate Ratio', 'Mean current SDR under impact',
        'Mean converted SDR under impact', 'Mean flow accumulation under impact',
        'Max flow accumulation under impact']
    logfile.write("%s\n" % ','.join(labels))

    lulc_nodata = raster_utils.get_nodata_from_uri(landuse_uri)
    lulc_pixel_size = raster_utils.get_cell_size_from_uri(landuse_uri)

    # limit the watersheds to just those that intersect the input lulc.
    current_watersheds = os.path.join(temp_dir, 'current_watersheds.shp')
    preprocessing.filter_by_raster(landuse_uri, watersheds_uri,
        current_watersheds, clip=True)

    # get the sediment export from the base raster, passed in from the user.
    # calculate for each watershed, so I can access these later.
    base_export = raster_utils.aggregate_raster_values_uri(
        base_run, current_watersheds, 'ws_id', 'sum').total
    LOGGER.debug('All watershed ids: %s', base_export.keys())

    # split the watersheds so I can use each watershed as an AOI for the
    # correct model later on.
    watersheds_dir = os.path.join(workspace, 'watershed_vectors')
    split_watersheds = static_maps.split_datasource(current_watersheds, watersheds_dir, ['ws_id'])

    for ws_index, watershed_uri in enumerate(split_watersheds):
        if ws_index < start_ws:
            LOGGER.debug('Watershed %s is less than start index %s. skipping',
                ws_index, start_ws)
            continue

        watershed_workspace = os.path.join(workspace, 'watershed_%s' %
            ws_index)
        if not os.path.exists(watershed_workspace):
            os.makedirs(watershed_workspace)

        # create an LULC just for this watershed.
        watershed_lulc = os.path.join(watershed_workspace,
            'watershed_lulc.tif')
        raster_utils.vectorize_datasets([landuse_uri], lambda x: x,
            watershed_lulc, gdal.GDT_Float32, lulc_nodata, lulc_pixel_size,
            'intersection', dataset_to_align_index=0, aoi_uri=watershed_uri)

        # get this watershed's ws_id
        watershed_vector = ogr.Open(watershed_uri)
        watershed_layer = watershed_vector.GetLayer()
        watershed = watershed_layer.GetFeature(0)
        watershed_id = watershed.GetField('ws_id')
        LOGGER.debug('This watershed\'s ws_id: %s', watershed_id)

        # We only want to run the model using the ONE current watershed.
        config['watersheds_uri'] = watershed_uri

        # If we're not in the starting watershed, then reset the starting index
        # of the impact site.
        if ws_index != start_impact:
            start_impact = 0

        for run_number in range(start_impact, num_iterations):
            impact_site_length = random.uniform(500, 3000)
            impact_workspace = os.path.join(watershed_workspace,
                'random_impact_%s' % run_number)

            impact_site = os.path.join(impact_workspace, 'impact_%s.shp' %
                run_number)
            impact_mask = os.path.join(impact_workspace, 'impact_mask.tif')

            if os.path.exists(impact_workspace):
                shutil.rmtree(impact_workspace)

            if not os.path.exists(impact_workspace):
                os.makedirs(impact_workspace)

            # make a random impact vector somewhere in the current watershed.
            static_maps.make_random_impact_vector(impact_site, watershed_uri,
                impact_site_length)
            impact_site_area = static_maps.get_polygon_area(impact_site)

            # Create a raster mask for the randomized impact site.
            # Any non-nodata pixels underneath the impact site are marked by 1.
            def mask_op(value):
                if value == lulc_nodata:
                    return lulc_nodata
                return 1.0
            raster_utils.vectorize_datasets([watershed_lulc], mask_op, impact_mask,
                gdal.GDT_Float32, lulc_nodata, lulc_pixel_size, 'intersection',
                dataset_to_align_index=0, aoi_uri=impact_site)

            # TODO: convert the landcover where the mask is 1.
            converted_landcover = os.path.join(impact_workspace,
                'converted_lulc.tif')
            def convert_impact(mask_value, lulc_value):
                if mask_value == 1:
                    return impact_lucode
                return lulc_value
            raster_utils.vectorize_datasets([impact_mask, watershed_lulc],
                convert_impact, converted_landcover, gdal.GDT_Float32, lulc_nodata,
                lulc_pixel_size, 'union', dataset_to_align_index=0)

            # run the target model on the converted landcover.
            config['lulc_uri'] = converted_landcover
            config['workspace_dir'] = impact_workspace
            sdr.execute(config)

            # get the SDR raster
            sdr_uri = os.path.join(impact_workspace, 'intermediate',
                'sdr_factor.tif')

            # Aggregate the sediment export from this impact simulation over
            # the target watershed
            impact_ws_export = raster_utils.aggregate_raster_values_uri(
                sdr_uri, watershed_uri, 'ws_id').total[watershed_id]

            base_ws_export = base_export[watershed_id]

            # Get the export from the static map under the impacted area.
            # only 1 feature in the impactd area, so we access that number with
            # index 1.
            static_estimate = raster_utils.aggregate_raster_values_uri(
                base_static_map, impact_site, 'id').total[1]

            mean_sdr_current_impact = raster_utils.aggregate_raster_values_uri(
                landuse_uri, impact_site, 'id').pixel_mean[1]

            mean_sdr_converted_impact = raster_utils.aggregate_raster_values_uri(
                converted_landcover, impact_site, 'id').pixel_mean[1]

            if '_prepare' in config:
                flow_accumulation = config['_prepare']['flow_accumulation_uri']
            else:
                flow_accumulation = os.path.join(impact_workspace,
                    'prepared_data', 'flow_accumulation.tif')
            f_a_stats = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_site, 'id')
            mean_f_a = f_a_stats.pixel_mean[1]
            max_f_a = f_a_stats.pixel_max[1]

            invest_estimate = base_ws_export - impact_ws_export
            export_ratio = static_estimate / invest_estimate

            # Now that we've completed the simulation, write these values to
            # the CSV file we've started.
            values_to_write = [watershed_id, run_number, impact_site_area,
                static_estimate, invest_estimate, export_ratio,
                mean_sdr_current_impact, mean_sdr_converted_impact, mean_f_a,
                max_f_a]
            logfile.write("%s\n" % ','.join(map(str, values_to_write)))
    logfile.close()

    # create preliminary chart for this set of simulations
    out_png = os.path.join(workspace, 'simulations.png')
    graph_it(logfile_uri, out_png)

def graph_it(log_file, out_file):
    all_rows = []
    out_of_bounds = []
    opened_log_file = open(log_file)
    opened_log_file.next()  # skip the column headers.
    for line in opened_log_file:
        values = map(float, line.split(','))
        ws_id, run_num, impact_area, static_est, invest_est, ratio,\
        _mean_cur_sdr, _mean_imp_sdr, _mean_f_a, _max_f_a = values

#        if ratio > 3 or ratio < -3:
#            out_of_bounds.append(ratio)
#        else:
#            all_rows.append((impact_area, ratio))
        all_rows.append((impact_area, ratio))

    # smoother with 95 % confidence intervals
    all_rows = sorted(all_rows, key=lambda x: x[0])
    areas = [r[0] for r in all_rows]
    ratios = [r[1] for r in all_rows]

#    LOGGER.debug('These values were outliers: %s', out_of_bounds)
    plt.plot(areas, ratios, 'ro')
    plt.xlabel('Impact Site Area (m^2)')
    plt.ylabel('(Static Est. / InVEST Est)')

    areas_np = numpy.array(areas)
    ratios_np = numpy.array(ratios)

    n = len(ratios_np)
    t = scipy.linspace(0,max(areas), n)

    #Linear regressison -polyfit - polyfit can be used other orders polys
    (ar,br) = scipy.polyfit(areas_np , ratios_np, 1)
    xr = scipy.polyval([ar,br],t)

    plt.ticklabel_format(style='sci',axis='x',scilimits=(0,0))

    plt.plot(t, xr,'g--')  # plot the linear regression line.
    plt.savefig(out_file)

def prepare_scenario(scenario_name, impact_lucode, scenario_workspace,
        config_dict):
    config = config_dict.copy()

    # return the converted SDR run.
    new_lulc_uri = os.path.join(scenario_workspace,
        '%s_lulc.tif' % scenario_name)
    static_maps.convert_lulc(base_landuse_uri, impact_lucode,
        new_lulc_uri)
    config['landuse_uri'] = new_lulc_uri

    # now, run the model on this (should already have preprocessed inputs)
    config['workspace_dir'] = os.path.join(scenario_workspace,
        '%s_converted' % scenario_name)
    sdr.execute(config)


if __name__ == '__main__':
    # WILLAMETTE SAMPLE DATA
    invest_data = 'invest-natcap.invest-3/test/invest-data'
    base_data = os.path.join(invest_data, 'Base_Data')

    # Construct the arguments to be used as a base set for all of the
    # simulations.
    workspace = 'willamette_sdr'
    base_landuse_uri = os.path.join(base_data, 'Terrestrial', 'lulc_samp_cur')
    config = {
        'workspace_dir': os.path.join(workspace, 'base_run'),
        'dem_uri': os.path.join(base_data, 'Freshwater', 'dem'),
        'erosivity_uri': os.path.join(base_data, 'Freshwater', 'erosivity'),
        'erodibility_uri': os.path.join(base_data, 'Freshwater', 'erodibility'),
        'landuse_uri': base_landuse_uri,
        'watersheds_uri': os.path.join(base_data, 'Freshwater',
            'watersheds.shp'),
        'biophysical_table_uri': os.path.join(base_data, 'Freshwater',
            'biophysical_table.csv'),
        'threshold_flow_accumulation': 1000,
        'k_param': 2,
        'sdr_max': 0.8,
        'ic_0_param': 0.5,
    }

#    # COLOMBIA SAMPLE DATA
#    # Assume that everything is in a folder called 'tool_data' in the current
#    # folder that contains all of our data for testing.
#    workspace = '/colossus/colombia_sdr'
#    tool_data = 'data/colombia_tool_data'
#    base_landuse_uri = os.path.join(tool_data, 'ecosystems.tif')
#    config = {
#        'workspace_dir': os.path.join(workspace, 'base_run'),
#        'dem_uri': os.path.join(tool_data, 'DEM.tif'),
#        'erosivity_uri': os.path.join(tool_data, 'Erosivity.tif'),
#        'erodibility_uri': os.path.join(tool_data, 'Erodability.tif'),
#        'landuse_uri': base_landuse_uri,
#        'watersheds_uri': os.path.join(tool_data, 'watersheds_cuencas.shp'),
#        'biophysical_table_uri': os.path.join(tool_data,
#            'Biophysical_Colombia.csv'),
#        'threshold_flow_accumulation': 1000,
#        'k_param': 2,
#        'sdr_max': 0.8,
#        'ic_0_param': 0.5,
#    }

    # run the SDR model on the base scenario (which is the current state of the
    # config dictionary)
#    config['_prepare'] = sdr._prepare(**config)
    sdr.execute(config)

    # get the SDR raster from the intermediate folder.  This is our base run.
    base_run = os.path.join(config['workspace_dir'], 'intermediate',
        'sdr_factor.tif')

    scenarios = [
        ('paved', 19),
        ('bare', 42),
    ]
    scenario_processes = []
    for scenario_name, impact_lucode in scenarios:
        scenario_workspace = os.path.join(workspace, scenario_name)
        # First off, convert the landcover to the target impact type
        if not os.path.exists(scenario_workspace):
            os.makedirs(scenario_workspace)

        # get the paved SDR raster.  This is our converted run.
        converted_run = os.path.join(scenario_workspace,
            '%s_converted' % scenario_name, 'intermediate', 'sdr_factor.tif')

        prepare_scenario(scenario_name, impact_lucode, scenario_workspace,
            config)

        scenario_process = multiprocessing.Process(target=prepare_scenario,
            args=(scenario_name, impact_lucode, scenario_workspace, config))
        scenario_processes.append(scenario_process)
        scenario_process.start()

    # join on the two executing processes
    for scenario_p in scenario_processes:
        scenario_p.join()

    scenario_processes = []
    static_map_uris = {}
    for scenario_name, impact_lucode in scenarios:
        print 'SCENARIO'
        # subtract the two rasters.  This yields the static map, which we'll test.
        static_map_uri = os.path.join(workspace,
            '%s_static_map.tif' % scenario_name)
        static_map_uris[scenario_name] = static_map_uri

        process = multiprocessing.Process(target=static_maps.subtract_rasters,
            args=(base_run, converted_run, static_map_uri))
        scenario_processes.append(process)
        process.start()

    # join the executing subtraction processes
    for scenario_p in scenario_processes:
        scenario_p.join()

    scenario_processes = []
    for scenario_name, impact_lucode in scenarios:
        # now, run the simulations!
        # Currently running 5 iterations per watershed.
        scenario_workspace = os.path.join(workspace, scenario_name)
        keyword_args = {
            'base_run': base_run,
            'base_static_map': static_map_uris[scenario_name],
            'landuse_uri': base_landuse_uri,
            'impact_lucode': impact_lucode,
            'watersheds_uri': config['watersheds_uri'],
            'workspace': os.path.join(scenario_workspace, 'simulations'),
            'config': config,
            'num_iterations': 5
        }
        test_static_map_quality
        process = multiprocessing.Process(target=test_static_map_quality,
            kwargs=keyword_args)
        scenario_processes.append(process)
        process.start()

    # join the executing subtraction processes
    for scenario_p in scenario_processes:
        scenario_p.join()

