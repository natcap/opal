import os
import unittest
import shutil

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils
from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')
INVEST_DATA = os.path.join(os.path.dirname(__file__), '..',
    'invest-natcap.invest-3', 'test', 'invest-data')

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

    @unittest.skip("This takes 13 hours to run.")
    def test_sediment_static_map_full(self):
        lulc_uri = os.path.join(FULL_DATA, 'ecosystems.tif')
        target_lucode = 124
        static_map_uri = 'sediment_static_map_full.tif'

        static_maps.build_static_map('sediment', lulc_uri, target_lucode,
            static_map_uri)

    def test_execute(self):
        self.config['workspace_dir'] = os.path.join(os.getcwd(),
            'sed_execute_test')
        self.config['model_name'] = 'sediment'
        self.config['paved_landcover_code'] = 60
        self.config['bare_landcover_code'] = 80
        self.config['landuse_uri'] = os.path.join(CLIPPED_DATA,
            'ecosystems.tif')
        self.config['do_parallelism'] = True

        static_maps.execute(self.config)

    def test_static_map_quality(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        impact_lucode = 60
        model_name = 'sediment'
        num_iterations = 10
        workspace = os.path.join(os.getcwd(), 'static_map_quality')
        impact_region = os.path.join(CLIPPED_DATA, 'servicesheds_col.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        base_workspace = os.path.join(workspace, 'base_run')
        static_maps.execute_model(model_name, lulc_uri, base_workspace, self.config)
        base_run = os.path.join(base_workspace, 'output', 'sed_export.tif')

        static_maps.test_static_map_quality(lulc_uri, impact_lucode, base_run,
            self.config, model_name, num_iterations, impact_region, workspace)

        static_maps.graph_it(os.path.join(workspace, 'logfile.txt'))

    def test_static_map_quality_willamette(self):
        TERRESTRIAL = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial')
        FRESHWATER = os.path.join(INVEST_DATA, 'Base_Data', 'Freshwater')
        lulc_uri = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial',
            'lulc_samp_cur')
        impact_lucode = 60
        model_name = 'sediment'
        num_iterations = 20  # not used unless explicitly pased to function
        workspace = os.path.join(os.getcwd(), 'static_map_quality')
        watersheds = os.path.join(FRESHWATER, 'watersheds.shp')

        self.config['dem_uri'] = os.path.join(FRESHWATER, 'dem')
        self.config['erosivity_uri'] = os.path.join(FRESHWATER, 'erosivity')
        self.config['erodibility_uri'] = os.path.join(FRESHWATER, 'erodibility')
        self.config['watersheds_uri'] = os.path.join(FRESHWATER,
            'watersheds.shp')
        self.config['biophysical_table_uri'] = os.path.join(FRESHWATER,
            'biophysical_table.csv')
        self.config['threshold_flow_accumulation'] = 400
        self.config['slope_threshold'] = "5",
        self.config['sediment_threshold_table_uri'] = os.path.join(INVEST_DATA,
            'Sedimentation', 'input', 'sediment_threshold_table.csv')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        base_workspace = os.path.join(workspace, 'base_run')
        static_maps.execute_model(model_name, lulc_uri, base_workspace, self.config)
        base_run = os.path.join(base_workspace, 'output', 'sed_export.tif')

        static_map_uri = os.path.join(workspace, 'base_static_map.tif')
        static_map_workspace = os.path.join(workspace, 'static_map')
        static_maps.build_static_map(model_name, lulc_uri, impact_lucode,
            static_map_uri, base_run, self.config,
            workspace=static_map_workspace)

        static_maps.test_static_map_quality(base_run, static_map_uri,
            lulc_uri, impact_lucode, watersheds, model_name, workspace,
            self.config, num_iterations=num_iterations)
        #static_maps.graph_it(os.path.join(workspace, 'logfile.txt'))

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

    @unittest.skip("This takes a long time to run")
    def test_carbon_static_map_full(self):
        lulc_uri = os.path.join(FULL_DATA, 'ecosystems.tif')
        target_lucode = 124
        static_map_uri = 'carbon_static_map_full.tif'

        static_maps.build_static_map('carbon', lulc_uri, target_lucode,
            static_map_uri)

