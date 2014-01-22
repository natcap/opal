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

