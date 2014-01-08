import os

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils
from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

class StaticMapTest(GISTest):
    def test_execute_sediment_smoke(self):
        config = {
            "workspace_dir": "",
            "dem_uri": os.path.join(CLIPPED_DATA, 'dem.tif'),
            "erosivity_uri": os.path.join(CLIPPED_DATA, "erosivity.tif"),
            "erodibility_uri": os.path.join(CLIPPED_DATA, "erodibility.tif"),
            "landuse_uri": "",
            "watersheds_uri": os.path.join(CLIPPED_DATA, "servicesheds_col.shp"),
            "reservoir_locations_uri": os.path.join(CLIPPED_DATA, "reservoirs.shp"),
            "reservoir_properties_uri": "",
            "biophysical_table_uri": os.path.join(FULL_DATA, "Biophysical_Colombia.csv"),
            "threshold_flow_accumulation": 4000,
            "slope_threshold": "5",
            "sediment_threshold_table_uri": os.path.join(FULL_DATA, "sediment_threshold.csv"),
        }

        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        workspace = 'test_workspace'
        static_maps.execute_model('sediment', lulc_uri, workspace,
            config=config)


