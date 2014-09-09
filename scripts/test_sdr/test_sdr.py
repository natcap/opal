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

from osgeo import ogr
from osgeo import gdal
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
    logfile = open(logfile_uri, 'a')
    labels = ['ws_id', 'Impact ID', 'Impact Area', 'Static Estimate',
        'InVEST Estimate', 'Estimate Ratio']
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
            sdr_uri = os.path.join(impact_workspace, 'intermediate', 'sdr.tif')

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

            invest_estimate = base_ws_export - impact_ws_export
            export_ratio = static_estimate / invest_estimate

            # Now that we've completed the simulation, write these values to
            # the CSV file we've started.
            values_to_write = [watershed_id, run_number, impact_site_area,
                static_estimate, invest_estimate, export_ratio]
            logfile.write("%s\n" % ','.join(map(str, values_to_write)))
    logfile.close()


if __name__ == '__main__':
# Start with willammette sample data for SDR

    invest_data = 'invest-natcap.invest-3/test/invest-data'
    base_data = os.path.join(invest_data, 'Base_Data')
    sediment_data = os.path.join(invest_data, 'Sedimentation', 'input')
    prepare_dir = 'sdr_prepare'

    # Construct the arguments to be used as a base set for all of the
    # simulations.
    config = {
        'workspace_dir': 'willammette_run_sdr',
        'dem_uri': os.path.join(base_data, 'Freshwater', 'dem'),
        'erosivity_uri': os.path.join(base_data, 'Freshwater', 'erosivity'),
        'erodibility_uri': os.path.join(base_data, 'Freshwater', 'erodibility'),
        'landuse_uri': os.path.join(base_data, 'Terrestrial', 'lulc_samp_cur'),
        'watersheds_uri': os.path.join(base_data, 'Freshwater',
            'watersheds.shp'),
        'biophysical_table_uri': os.path.join(base_data, 'Freshwater',
            'biophysical_table.csv'),
        'threshold_flow_accumulation': 1000,
        'k_param': 2,
        'sdr_max': 0.8,
    }

    # run the SDR model on the base scenario (which is the current state of the
    # config dictionary)
    sdr.execute(config)



