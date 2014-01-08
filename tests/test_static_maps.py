import os

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils
from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

class SedimentStaticMapTest(GISTest):
    def setUp(self):
        self.config = {
            "workspace_dir": "",
            "dem_uri": os.path.join(CLIPPED_DATA, 'dem.tif'),
            "erosivity_uri": os.path.join(CLIPPED_DATA, "erosivity.tif"),
            "erodibility_uri": os.path.join(CLIPPED_DATA, "erodibility.tif"),
            "landuse_uri": "",
            "watersheds_uri": os.path.join(CLIPPED_DATA, "servicesheds_col.shp"),
            "reservoir_locations_uri": os.path.join(CLIPPED_DATA, "reservoirs.shp"),
            "reservoir_properties_uri": "",
            "biophysical_table_uri": os.path.join(FULL_DATA, "Biophysical_Colombia.csv"),
            "threshold_flow_accumulation": 40,
            "slope_threshold": "5",
            "sediment_threshold_table_uri": os.path.join(FULL_DATA, "sediment_threshold.csv"),
        }

    def test_execute_sediment_smoke(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        workspace = 'test_workspace'
        static_maps.execute_model('sediment', lulc_uri, workspace,
            config=self.config)

    def test_sediment_static_map(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        target_lucode = 124
        static_map_uri = 'sediment_static_map.tif'

        static_maps.build_static_map('sediment', lulc_uri, target_lucode,
            static_map_uri, config=self.config)

class CarbonStaticMapTest(GISTest):
    def setUp(self):
        self.config = {
            "workspace_dir": "",
            "do_biophysical": True,
            "do_uncertainty": False,
            "do_valuation": False,
            "lulc_cur_uri": "",
            "carbon_pools_uri": os.path.join(FULL_DATA, "Carbon_pools_Colombia.csv")
        }

    def test_execute_carbon_smoke(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        workspace = 'test_workspace_carbon'
        static_maps.execute_model('carbon', lulc_uri, workspace,
            config=self.config)

    def test_carbon_static_map(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        target_lucode = 124
        static_map_uri = 'carbon_static_map.tif'

        static_maps.build_static_map('carbon', lulc_uri, target_lucode,
            static_map_uri, config=self.config)

