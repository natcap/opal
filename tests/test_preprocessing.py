import json
import os
import shutil

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils

from adept import preprocessing

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')

class PreprocessingTest(GISTest):
    def test_split_multipolygons(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')

        workspace = os.path.join(os.getcwd(), 'test_split_workspace')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

        os.makedirs(workspace)
        out_vector = os.path.join(workspace, 'test_split.shp')

        preprocessing.split_multipolygons(ecosystems, out_vector, ['Ecos_dis',
            'Ecosistema', 'FACTOR_DE'])

#        raster_uri = os.path.join(DATA, 'ecosystems.tif')
#        raster_stats = raster_utils.aggregate_raster_values_uri(raster_uri, out_vector,
#            shapefile_field='FID')
#
#        json_file = open(os.path.join(workspace, 'raster_stats.json'), 'w')
#        raster_stats_dict = {
#            'total': raster_stats.total,
#            'pixel_mean': raster_stats.pixel_mean,
#            'hectare_mean': raster_stats.hectare_mean,
#            'n_pixels': raster_stats.n_pixels,
#            'pixel_min': raster_stats.pixel_min,
#            'pixel_max': raster_stats.pixel_max,
#        }
#        json.dump(raster_stats_dict, json_file, indent=4)
#        json_file.close()

    def test_exclude_polygons(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        workspace = os.path.join(os.getcwd(), 'test_split_workspace')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        crop_vector = os.path.join(DATA, 'hydrozones.shp')
        out_vector = os.path.join(workspace, 'test_crop.shp')
        preprocessing.exclude_polygons(ecosystems, crop_vector, 8,
            out_vector)

    def test_prepare_impact_sites(self):
        services = [
            ('sediment', os.path.join(DATA, 'ecosystems.tif'))
        ]
        workspace = os.path.join(os.getcwd(), 'output_ag_stats')
        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')
        out_vector = os.path.join(workspace, 'output.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        preprocessing.prepare_impact_sites(impact_sites, services,
            out_vector)

    def test_prepare_offset_parcels(self):
        services = [
            ('sediment', os.path.join(DATA, 'ecosystems.tif'))
        ]
        workspace = os.path.join(os.getcwd(), 'output_ag_stats')
        offset_parcels = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        out_vector = os.path.join(workspace, 'offset_parcels.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        preprocessing.prepare_offset_parcels(offset_parcels, services,
            out_vector)

    def test_locate_hydrozone(self):
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        aoi_vector= os.path.join(DATA, 'sample_aoi.shp')
        workspace = os.path.join(os.getcwd(), 'output_hydrozone')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)
        output_vector = os.path.join(workspace, 'focal_hydrozone.shp')

        preprocessing.locate_hydrozone(hydrozones, aoi_vector, output_vector)


