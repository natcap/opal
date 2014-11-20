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
import json

from osgeo import ogr
from osgeo import gdal
import matplotlib
matplotlib.use('Agg')  # for rendering plots without $DISPLAY set.
import matplotlib.pyplot as plt
import numpy
import scipy
import invest_natcap
from invest_natcap import raster_utils
from invest_natcap.sdr import sdr
import adept
from adept import static_maps
from adept import preprocessing

RASTER_CY_LOGGER = logging.getLogger('raster_cython_utils')
RASTER_CY_LOGGER.setLevel(logging.WARNING)

RASTER_UTILS_LOGGER = logging.getLogger('raster_utils')
RASTER_UTILS_LOGGER.setLevel(logging.WARNING)

LOGGER = logging.getLogger('sdr_simulations')

def get_last_impact(logfile_uri):
    """Open the target logfile and take the first two integers of the last
    line.  Returns a tuple of (watershed_id, impact_number) of the last run of
    the tool."""
    logfile = open(logfile_uri, 'r')
    lines_in_logfile = 0
    for line in logfile:
        lines_in_logfile += 1

    # if we only have the title row, don't analyze for the ws, impact
    if lines_in_logfile == 1:
        logfile.close()
        return (1, 0)

    watershed, impact_num = line.split(',')[0:2]
    logfile.close()
    return (int(watershed), int(impact_num))

def clip_raster_to_watershed(in_raster, ws_vector, out_uri):
    """Clip the input raster to ws_vector, saving the output raster to out_uri.
        in_raster - a URI to an input GDAL raster.
        ws_vector - a URI to an OGR vector that contains a single polygon of a
            watershed.
        out_uri - a URI to where the output raster should be saved.
    """
    datatype = raster_utils.get_datatype_from_uri(in_raster)
    nodata = raster_utils.get_nodata_from_uri(in_raster)
    pixel_size = raster_utils.get_pixel_size_from_uri(in_raster)

    raster_utils.vectorize_datasets([in_raster], lambda x: x,
        out_uri, datatype, nodata, pixel_size, 'intersection',
        dataset_to_align_index=0, aoi_uri=ws_vector)


def test_static_map_quality(base_sed_exp, base_sdr, base_static_map, usle_static_map, landuse_uri,
    impact_lucode, watersheds_uri, workspace, config, num_iterations=5,
    start_ws=0, start_impact=0, end_ws=None):
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

    # only write label headers if this is the top row.
    if start_ws == 0 and start_impact == 0:
        labels = ['ws_id',
            'Impact ID',
            'Impact Area',
            'Static Estimate',
            'InVEST Estimate',
            'Estimate Ratio',
            'Mean sed_exp under impact current',
            'Mean sed_exp under impact converted',
            'Mean current SDR under impact',
            'Mean converted SDR under impact',
            'Mean flow accumulation under impact',
            'Max flow accumulation under impact',
            'Total delta-USLE*sdr under impact']
        logfile.write("%s\n" % ','.join(labels))
    logfile.close()

    lulc_nodata = raster_utils.get_nodata_from_uri(landuse_uri)
    lulc_pixel_size = raster_utils.get_cell_size_from_uri(landuse_uri)

    # limit the watersheds to just those that intersect the input lulc.
    current_watersheds = os.path.join(temp_dir, 'current_watersheds.shp')
    preprocessing.filter_by_raster(landuse_uri, watersheds_uri,
        current_watersheds, clip=True)

    # split the watersheds so I can use each watershed as an AOI for the
    # correct model later on.
    watersheds_dir = os.path.join(workspace, 'watershed_vectors')
    split_watersheds = static_maps.split_datasource(current_watersheds, watersheds_dir, ['ws_id'])

    if end_ws is None:
        end_ws = len(split_watersheds)

    for ws_index, watershed_uri in enumerate(split_watersheds):
        if ws_index < start_ws:
            LOGGER.debug('Watershed %s is less than start index %s. skipping',
                ws_index, start_ws)
            continue

        if ws_index > end_ws:
            LOGGER.debug('Watershed %s > end_ws %s. Skipping.', ws_index,
                end_ws)
            continue

        watershed_workspace = os.path.join(workspace, 'watershed_%s' %
            ws_index)
        if not os.path.exists(watershed_workspace):
            os.makedirs(watershed_workspace)

        # create an LULC just for this watershed.
        watershed_lulc = os.path.join(watershed_workspace,
            'watershed_lulc.tif')
        clip_raster_to_watershed(landuse_uri, watershed_uri, watershed_lulc)

        # Create rasters of only those base_run and base static_map pixels
        # that are in the watershed.
        ws_base_sed_exp = os.path.join(watershed_workspace,
            'watershed_base_sed_exp.tif')
        clip_raster_to_watershed(base_sed_exp, watershed_uri, ws_base_sed_exp)
        ws_base_export = raster_utils.aggregate_raster_values_uri(
            ws_base_sed_exp, watershed_uri, 'ws_id').total[ws_index]

        ws_base_sdr = os.path.join(watershed_workspace,
            'watershed_base_sdr.tif')
        clip_raster_to_watershed(base_sdr, watershed_uri, ws_base_sdr)

        ws_static_map = os.path.join(watershed_workspace,
            'watershed_static_map.tif')
        clip_raster_to_watershed(base_static_map, watershed_uri, ws_static_map)

        ws_usle = os.path.join(watershed_workspace, 'watershed_usle.tif')
        clip_raster_to_watershed(usle_static_map, watershed_uri, ws_usle)

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
            config['landuse_uri'] = converted_landcover
            config['workspace_dir'] = impact_workspace
            if '_prepare' in config:
                del config['_prepare']
            sdr.execute(config)

            impact_sdr_uri = os.path.join(impact_workspace, 'intermediate',
                'sdr_factor.tif')
            impact_sed_exp = os.path.join(impact_workspace, 'output',
                'sed_export.tif')

            # Aggregate the sediment export from this impact simulation over
            # the target watershed
            impact_ws_export = raster_utils.aggregate_raster_values_uri(
                impact_sdr_uri, watershed_uri, 'ws_id').total[watershed_id]

            # Get the export from the static map under the impacted area.
            # only 1 feature in the impactd area, so we access that number with
            # index 1.
            static_estimate = raster_utils.aggregate_raster_values_uri(
                base_static_map, impact_site, 'id').total[1]

            mean_sdr_current_impact = raster_utils.aggregate_raster_values_uri(
                base_sdr, impact_site, 'id').pixel_mean[1]

            mean_sdr_converted_impact = raster_utils.aggregate_raster_values_uri(
                impact_sdr_uri, impact_site, 'id').pixel_mean[1]

            usle_sum_impact = raster_utils.aggregate_raster_values_uri(
                ws_usle, impact_site, 'id').total[1]

            base_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                ws_base_sed_exp, impact_site, 'id').pixel_mean[1]

            impact_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                impact_sed_exp, impact_site, 'id').pixel_mean[1]

            if '_prepare' in config:
                flow_accumulation = config['_prepare']['flow_accumulation_uri']
            else:
                flow_accumulation = os.path.join(impact_workspace,
                    'prepared_data', 'flow_accumulation.tif')
            f_a_stats = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_site, 'id')
            mean_f_a = f_a_stats.pixel_mean[1]
            max_f_a = f_a_stats.pixel_max[1]

            invest_estimate = ws_base_export - impact_ws_export
            export_ratio = static_estimate / invest_estimate

            # Now that we've completed the simulation, write these values to
            # the CSV file we've started.
            values_to_write = [
                watershed_id,
                run_number,
                impact_site_area,
                static_estimate,
                invest_estimate,
                export_ratio,
                base_sed_exp_estimate,
                impact_sed_exp_estimate,
                mean_sdr_current_impact,
                mean_sdr_converted_impact,
                mean_f_a,
                max_f_a,
                usle_sum_impact
            ]

            # reopen the file just to write the line, then close the file.
            # This prevents a situation when the file is accidentally closed in
            # a long-running process.
            logfile = open(logfile_uri, 'a')
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

def write_version_data(workspace, file_uri='pkg_versions.json'):
    file_uri = os.path.join(workspace, file_uri)
    version_data = {
        'invest_natcap': invest_natcap.__version__,
        'adept': adept.__version__,
    }
    json.dump(version_data, open(file_uri, 'w'), sort_keys=True, indent=4)

def _get_version_data(file_uri):
    return json.load(open(file_uri))

def invest_changed(workspace):
    """Check if the InVEST version of the target workspace is different from
    the one currently installed.  Returns a boolean."""
    invest_version_uri = os.path.join(workspace, 'pkg_versions.json')
    if not os.path.exists(invest_version_uri):
        return True  # if no version file, assume InVEST has changed.

    pkg_versions = _get_version_data(invest_version_uri)
    if pkg_versions['invest_natcap'] == invest_natcap.__version__:
        return False
    return True

def test_one_watershed_paved():
    """Test a single watershed, if possible."""
    old_workspace = '/colossus/colombia_sdr'
    base_run = os.path.join(old_workspace, 'base_run', 'output',
        'sed_export.tif')
    base_static_map = os.path.join(old_workspace, 'paved_static_map.tif')
    landuse_uri = os.path.join(os.getcwd(), 'data', 'colombia_tool_data',
        'ecosystems.tif')
    impact_lucode = 19
    tool_data = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
    watersheds_uri = os.path.join(tool_data, 'watersheds_cuencas.shp')
    output_workspace = '/colossus/colombia_sdr_noprepare'
    config = {
        'dem_uri': os.path.join(tool_data, 'DEM.tif'),
        'erosivity_uri': os.path.join(tool_data, 'Erosivity.tif'),
        'erodibility_uri': os.path.join(tool_data, 'Erodability.tif'),
        'landuse_uri': landuse_uri,
        'watersheds_uri': watersheds_uri,
        'biophysical_table_uri': os.path.join(tool_data,
            'Biophysical_Colombia.csv'),
        'threshold_flow_accumulation': 100,  # yes, 100!
        'k_param': 2,
        'sdr_max': 0.8,
        'ic_0_param': 0.5,
    }
    num_iterations = 20

    kwargs = {
        'base_run': base_run,
        'base_static_map': base_static_map,
        'landuse_uri': landuse_uri,
        'impact_lucode': impact_lucode,
        'watersheds_uri': watersheds_uri,
        'workspace': output_workspace,
        'config': config,
        'num_iterations': num_iterations
    }

    test_static_map_quality(**kwargs)

def test_one_watershed_bare():
    """Test a single watershed, if possible."""
    old_workspace = '/colossus/colombia_sdr'
    base_run = os.path.join(old_workspace, 'base_run', 'intermediate',
        'sdr_factor.tif')
    base_sed_exp = os.path.join(old_workspace, 'base_run', 'output',
        'sed_export.tif')
    base_static_map = os.path.join(old_workspace, 'bare_static_map.tif')
    usle_static_map = os.path.join(old_workspace, 'bare_usle_static_map.tif')
    landuse_uri = os.path.join(os.getcwd(), 'data', 'colombia_tool_data',
        'ecosystems.tif')
    impact_lucode = 42
    tool_data = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
    watersheds_uri = os.path.join(tool_data, 'watersheds_cuencas.shp')
    output_workspace = '/colossus/colombia_sdr_noprepare_bare'
    config = {
        'dem_uri': os.path.join(tool_data, 'DEM.tif'),
        'erosivity_uri': os.path.join(tool_data, 'Erosivity.tif'),
        'erodibility_uri': os.path.join(tool_data, 'Erodability.tif'),
        'landuse_uri': landuse_uri,
        'watersheds_uri': watersheds_uri,
        'biophysical_table_uri': os.path.join(tool_data,
            'Biophysical_Colombia.csv'),
        'threshold_flow_accumulation': 100,  # yes, 100!
        'k_param': 2,
        'sdr_max': 0.8,
        'ic_0_param': 0.5,
    }
    num_iterations = 20

    kwargs = {
        'base_sdr': base_run,
        'base_sed_exp': base_sed_exp,
        'base_static_map': base_static_map,
        'usle_static_map': usle_static_map,
        'landuse_uri': landuse_uri,
        'impact_lucode': impact_lucode,
        'watersheds_uri': watersheds_uri,
        'workspace': output_workspace,
        'config': config,
        'num_iterations': num_iterations,
        'start_ws': 8,
        'end_ws': 8,
    }

    test_static_map_quality(**kwargs)

def create_usle_static_map(usle_current, usle_bare, sdr_current, out_uri):
    usle_nodata = raster_utils.get_nodata_from_uri(usle_current)
    usle_pixel_size = raster_utils.get_cell_size_from_uri(usle_current)

    def _calculate(usle_cur, usle_bare, sdr_cur):
        return numpy.where(usle_cur == usle_nodata, usle_nodata,
            numpy.multiply(numpy.subtract(usle_bare, usle_cur), sdr_cur))

    raster_utils.vectorize_datasets([usle_current, usle_bare, sdr_current],
        _calculate, dataset_out_uri=out_uri, datatype_out=gdal.GDT_Float32,
        nodata_out=usle_nodata, pixel_size_out=usle_pixel_size,
        bounding_box_mode='intersection', vectorize_op=False)

if __name__ == '__main__':
#    test_one_watershed_bare()
#    sys.exit(0)

#    # WILLAMETTE SAMPLE DATA
#    invest_data = 'invest-natcap.invest-3/test/invest-data'
#    base_data = os.path.join(invest_data, 'Base_Data')
#
#    # Construct the arguments to be used as a base set for all of the
#    # simulations.
#    workspace = 'willamette_sdr'
#    base_landuse_uri = os.path.join(base_data, 'Terrestrial', 'lulc_samp_cur')
#    config = {
#        'workspace_dir': os.path.join(workspace, 'base_run'),
#        'dem_uri': os.path.join(base_data, 'Freshwater', 'dem'),
#        'erosivity_uri': os.path.join(base_data, 'Freshwater', 'erosivity'),
#        'erodibility_uri': os.path.join(base_data, 'Freshwater', 'erodibility'),
#        'landuse_uri': base_landuse_uri,
#        'watersheds_uri': os.path.join(base_data, 'Freshwater',
#            'watersheds.shp'),
#        'biophysical_table_uri': os.path.join(base_data, 'Freshwater',
#            'biophysical_table.csv'),
#        'threshold_flow_accumulation': 1000,
#        'k_param': 2,
#        'sdr_max': 0.8,
#        'ic_0_param': 0.5,
#    }

    # COLOMBIA SAMPLE DATA
    # Assume that everything is in a folder called 'tool_data' in the current
    # folder that contains all of our data for testing.
    workspace = '/colossus/colombia_sdr'
    tool_data = 'data/colombia_tool_data'
    base_landuse_uri = os.path.join(tool_data, 'ecosystems.tif')
    config = {
        'workspace_dir': os.path.join(workspace, 'base_run'),
        'dem_uri': os.path.join(tool_data, 'DEM.tif'),
        'erosivity_uri': os.path.join(tool_data, 'Erosivity.tif'),
        'erodibility_uri': os.path.join(tool_data, 'Erodability.tif'),
        'landuse_uri': base_landuse_uri,
        'watersheds_uri': os.path.join(tool_data, 'watersheds_cuencas.shp'),
        'biophysical_table_uri': os.path.join(tool_data,
            'Biophysical_Colombia.csv'),
        'threshold_flow_accumulation': 100,  # yes, 100!
        'k_param': 2,
        'sdr_max': 0.8,
        'ic_0_param': 0.5,
    }

    # set the tempdir to be within the workspace
    temp_dir = os.path.join(config['workspace_dir'], 'tmp')
    tempfile.tempdir = temp_dir
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    if invest_changed(config['workspace_dir']):
        # run the SDR model on the base scenario (which is the current state of the
        # config dictionary)
        config['_prepare'] = sdr._prepare(**config)
        sdr.execute(config)
        write_version_data(config['workspace_dir'])
    else:
        _intermediate_dir = os.path.join(config['workspace_dir'],
            'prepared_data')
        config['_prepare'] = {
            'aligned_dem_uri': os.path.join(_intermediate_dir,
                'aligned_dem.tif'),
            'aligned_lulc_uri': os.path.join(_intermediate_dir,
                'aligned_lulc.tif'),
            'aligned_erosivity_uri': os.path.join(_intermediate_dir,
                'aligned_erosivity.tif'),
            'aligned_erodibility_uri': os.path.join(_intermediate_dir,
                'aligned_erodibility.tif'),
            'dem_offset_uri': os.path.join(_intermediate_dir,
                'dem_offset.tif'),
            'thresholded_slope_uri': os.path.join(_intermediate_dir,
                'thresholded_slope.tif'),
            'flow_accumulation_uri': os.path.join(_intermediate_dir,
                'flow_accumulation.tif'),
            'flow_direction_uri': os.path.join(_intermediate_dir,
                'flow_direction.tif'),
            'ls_uri': os.path.join(_intermediate_dir, 'ls.tif'),
        }

    PARALLELIZE = True

    # get the SDR raster from the intermediate folder.  This is our base run.
    base_sed_export = os.path.join(config['workspace_dir'], 'output',
        'sed_export.tif')
    base_usle = os.path.join(config['workspace_dir'], 'output',
        'usle.tif')
    base_sdr = os.path.join(config['workspace_dir'], 'intermediate',
        'sdr_factor.tif')

    scenarios = [
        ('paved', 89),
        ('bare', 301),
    ]
    scenario_processes = []
    for scenario_name, impact_lucode in scenarios:
        scenario_workspace = os.path.join(workspace, scenario_name)
        # First off, convert the landcover to the target impact type
        if not os.path.exists(scenario_workspace):
            os.makedirs(scenario_workspace)

        # get the paved SDR raster.  This is our converted run.
        converted_run = os.path.join(scenario_workspace,
            '%s_converted' % scenario_name, 'output', 'sed_export.tif')

        if invest_changed(scenario_workspace) or not os.path.exists(converted_run):
            converted_args = (scenario_name, impact_lucode, scenario_workspace, config)
            usle_args = (scenario_name, impact_lucode, scenario_workspace, config)
            if PARALLELIZE:
                scenario_process = multiprocessing.Process(target=prepare_scenario,
                    args=converted_args)
                scenario_processes.append(scenario_process)
                scenario_process.start()
            else:
                prepare_scenario(*converted_args)
            write_version_data(scenario_workspace)

    # join on the two executing processes
    for scenario_p in scenario_processes:
        scenario_p.join()

    scenario_processes = []
    static_map_uris = {}
    for scenario_name, impact_lucode in scenarios:
        scenario_workspace = os.path.join(workspace, scenario_name)
        print 'SCENARIO'
        # subtract the two rasters.  This yields the static map, which we'll test.
        static_map_uri = os.path.join(workspace,
            '%s_static_map.tif' % scenario_name)
        usle_map_uri = os.path.join(workspace,
            '%s_usle_static_map.tif' % scenario_name)

        static_map_uris[scenario_name] = {}
        static_map_uris[scenario_name]['sed'] = static_map_uri
        static_map_uris[scenario_name]['usle'] = usle_map_uri

        converted_run = os.path.join(scenario_workspace,
            '%s_converted' % scenario_name, 'output', 'sed_export.tif')
        converted_usle_run = os.path.join(scenario_workspace,
            '%s_converted' % scenario_name, 'output', 'usle.tif')

        subtract_args = (base_sed_export, converted_run, static_map_uri)
        create_usle_args = (base_usle, converted_usle_run, base_sdr, usle_map_uri)
        if PARALLELIZE:
            process = multiprocessing.Process(target=static_maps.subtract_rasters,
                args=subtract_args)
            scenario_processes.append(process)
            process.start()

            process_2 = multiprocessing.Process(target=create_usle_static_map,
                args=create_usle_args)
            scenario_processes.append(process_2)
            process_2.start()
        else:
            static_maps.subtract_rasters(*subtract_args)
            static_maps.subtract_rasters(*create_usle_args)

    # join the executing subtraction processes
    for scenario_p in scenario_processes:
        scenario_p.join()

    scenario_processes = []
    for scenario_name, impact_lucode in scenarios:
        # now, run the simulations!
        # Currently running 5 iterations per watershed.
        scenario_workspace = os.path.join(workspace, scenario_name)
        keyword_args = {
            'base_sed_exp': base_sed_export,
            'base_sdr': base_sdr,
            'base_static_map': static_map_uris[scenario_name]['sed'],
            'usle_static_map': static_map_uris[scenario_name]['usle'],
            'landuse_uri': base_landuse_uri,
            'impact_lucode': impact_lucode,
            'watersheds_uri': config['watersheds_uri'],
            'workspace': os.path.join(scenario_workspace, 'simulations'),
            'config': config,
            'num_iterations': 20
        }

        simulations_csv = os.path.join(keyword_args['workspace'],
            'impact_site_simulation.csv')
        if os.path.exists(simulations_csv):
            start_ws, start_impact = get_last_impact(simulations_csv)
            start_ws -= 1
        else:
            start_ws = 0
            start_impact = 0
        keyword_args['start_ws'] = start_ws
        keyword_args['start_impact'] = start_impact

        print start_ws
        print start_impact
        #raise Exception

        if PARALLELIZE:
            process = multiprocessing.Process(target=test_static_map_quality,
                kwargs=keyword_args)
            scenario_processes.append(process)
            process.start()
        else:
            test_static_map_quality(**keyword_args)

    # join the executing subtraction processes
    for scenario_p in scenario_processes:
        scenario_p.join()

