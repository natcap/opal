import os
import unittest
import shutil

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils
from natcap.opal import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')
INVEST_DATA = os.path.join(os.path.dirname(__file__), '..', '..',
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
            static_map_uri, base_run=lulc_uri, config=self.config)

    def test_sediment_static_map_quality_sims(self):
        lulc_uri = os.path.join(CLIPPED_DATA, 'ecosystems.tif')
        target_lucode = 124
        static_map_uri = 'sediment_static_map.tif'
        workspace = 'simulations_workspace'

        static_maps.build_static_map('sediment', lulc_uri, target_lucode,
            static_map_uri, base_run=lulc_uri, workspace=workspace, config=self.config, num_simulations=5)

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
        lulc_uri = os.path.join(FULL_DATA, 'ecosystems.tif')
        impact_lucode = 60  # paved landcover code
        model_name = 'sediment'
        num_iterations = 10
        workspace = os.path.join(os.getcwd(), 'static_map_quality')
        impact_region = os.path.join(FULL_DATA, 'servicesheds_col.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        # tweak the config for running on full datasets
        self.config = {
            "workspace_dir": "",
            "dem_uri": os.path.join(FULL_DATA, 'DEM.tif'),
            "erosivity_uri": os.path.join(FULL_DATA, "Erosivity.tif"),
            "erodibility_uri": os.path.join(FULL_DATA, "Erodability.tif"),
            "landuse_uri": "",
#            "watersheds_uri": os.path.join(FULL_DATA, "Servicesheds_Col.shp"),
            "watersheds_uri": os.path.join(FULL_DATA, "watersheds_cuencas.shp"),
            "reservoir_locations_uri": os.path.join(FULL_DATA, "Reservoirs.shp"),
            "reservoir_properties_uri": "",
            "biophysical_table_uri": os.path.join(FULL_DATA, "Biophysical_Colombia.csv"),
            "threshold_flow_accumulation": 40,
            "slope_threshold": "5",
            "sediment_threshold_table_uri": os.path.join(FULL_DATA, "sediment_threshold.csv"),
        }
        watersheds_uri = self.config['watersheds_uri']

        #base_workspace = os.path.join(workspace, 'base_run')
        #static_maps.execute_model(model_name, lulc_uri, base_workspace, self.config)

        # assume that I've generated the static map before
        base_workspace = os.path.join(os.path.dirname(__file__), '..',
            'sediment_static_maps', 'sediment_base')
        base_run = os.path.join(base_workspace, 'output', 'sed_export.tif')
        base_static_map = os.path.join(base_workspace, '..',
            'sediment_paved_static_map.tif')

        if not os.path.exists(base_run):
            raise IOError(('You must generate a sediment static map.  Its '
                'base export must be located here: %s' % os.path.abspath(base_run)))

        if not os.path.exists(base_static_map):
            raise IOError(('You must generate a sediment static map in its '
                'usual place: %s' % os.path.abspath(base_static_map)))

        static_maps.test_static_map_quality(base_run, base_static_map,
            lulc_uri, impact_lucode, watersheds_uri, model_name, workspace,
            self.config)

        csv_path = os.path.join(workspace, 'impact_site_simulation.csv')
        static_maps.graph_it(csv_path, os.path.join(workspace,
            'results_plot.png'))


    def test_static_map_quality_willamette(self):
        TERRESTRIAL = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial')
        FRESHWATER = os.path.join(INVEST_DATA, 'Base_Data', 'Freshwater')
        lulc_uri = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial',
            'lulc_samp_cur')
        impact_lucode = 88
        model_name = 'sediment'
        num_iterations = 50  # not used unless explicitly pased to function
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
        self.config['k_param'] = 2
        self.config['sdr_max'] = 0.8
        self.config['ic_0_param'] = 0.5
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

#        difference_raster = os.path.join(workspace, 'difference.tif')
#        converted_raster = os.path.join(static_map_workspace,
#            'sediment_converted', 'output', 'sed_export.tif')
#        static_maps.subtract_rasters(base_run, converted_raster,
#            difference_raster)

        # invert is False here because we're running sediment on the paved
        # scenario.
        static_maps.test_static_map_quality(base_run, static_map_uri,
            lulc_uri, impact_lucode, watersheds, model_name, workspace,
            self.config, num_iterations=num_iterations, invert=False)

        print 'graphing'
        log_file = os.path.join(workspace, 'impact_site_simulation.csv')
        graph_file = os.path.join(workspace, 'results_plot.png')
        static_maps.graph_it(log_file, graph_file)

    def test_graphing(self):
        workspace = os.path.join(os.getcwd(), 'static_map_quality')
        csv_path = os.path.join(workspace, 'impact_site_simulation.csv')
        graph_file = os.path.join(workspace, 'results_plot.png')
        static_maps.graph_it(csv_path, graph_file)

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

    def test_carbon_static_map_quality(self):
        TERRESTRIAL = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial')
        FRESHWATER = os.path.join(INVEST_DATA, 'Base_Data', 'Freshwater')
        lulc_uri = os.path.join(INVEST_DATA, 'Base_Data', 'Terrestrial',
            'lulc_samp_cur')
        impact_lucode = 88
        model_name = 'carbon'
        num_iterations = 15  # not used unless explicitly pased to function
        workspace = os.path.join(os.getcwd(), 'static_map_quality_carbon')
        watersheds = os.path.join(FRESHWATER, 'watersheds.shp')

        self.config['carbon_pools_uri'] = os.path.join(INVEST_DATA, 'Carbon',
            'Input', 'carbon_pools_samp.csv')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        base_workspace = os.path.join(workspace, 'base_run')
        static_maps.execute_model(model_name, lulc_uri, base_workspace, self.config)
        base_run = os.path.join(base_workspace, 'output', 'tot_C_cur.tif')

        static_map_uri = os.path.join(workspace, 'base_static_map.tif')
        static_map_workspace = os.path.join(workspace, 'static_map')
        static_maps.build_static_map(model_name, lulc_uri, impact_lucode,
            static_map_uri, base_run, self.config,
            workspace=static_map_workspace)

        static_maps.test_static_map_quality(base_run, static_map_uri,
            lulc_uri, impact_lucode, watersheds, model_name, workspace,
            self.config, num_iterations=num_iterations)

        print 'graphing'
        log_file = os.path.join(workspace, 'impact_site_simulation.csv')
        graph_file = os.path.join(workspace, 'results_plot.png')
        static_maps.graph_it(log_file, graph_file)

class RasterMathTest(GISTest):
    def setUp(self):
        self.workspace = os.path.join(os.path.dirname(__file__), 'raster_math')

        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)
        os.makedirs(self.workspace)

    def test_raster_math_smoke(self):
        sample_raster = os.path.join(FULL_DATA, 'ecosystems.tif')
        args = {
            'workspace': self.workspace,
            'name': 'sample',
            'base_uri': sample_raster,
            'paved_uri': sample_raster,
            'bare_uri': sample_raster,
            'protection_uri': sample_raster,
        }

        static_maps.raster_math(args)

        for filename_base in ['bare', 'protection', 'paved']:
            filename = os.path.join(self.workspace, '%s_%s_static_map.tif' % (
                args['name'], filename_base))
            self.assertEqual(os.path.exists(filename), True)

class NutrientStaticMapTest(GISTest):
    def setUp(self):
        self.config = {
            "workspace_dir": "",
            "dem_uri": os.path.join(CLIPPED_DATA, 'dem.tif'),
            "lulc_uri": "",
            "watersheds_uri": os.path.join(CLIPPED_DATA, "servicesheds_col.shp"),
            "biophysical_table_uri": os.path.join(FULL_DATA, "Biophysical_Colombia.csv"),
            "soil_depth_uri": os.path.join(FULL_DATA, 'Soil_depth.tif'),
            "precipitation": os.path.join(FULL_DATA, 'Precipitation.tif'),
            "pawc_uri": os.path.join(FULL_DATA, 'Plant_available_water_content.tif'),
            "eto_uri": os.path.join(FULL_DATA, 'Ref_evapotranspiration.tif'),
            "seasonality_constant": 5,
            "calc_p": False,
            "calc_n": True,
            "water_purification_threshold_table_uri": os.path.join(FULL_DATA,
                'sediment_threshold.csv'),
            "accum_threshold": 1000,
            "depth_to_root_rest_layer_uri": os.path.join(FULL_DATA,
                'Soil_depth.tif'),
            "valuation_enabled": False,
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

    def test_execute(self):
        self.config['workspace_dir'] = os.path.join(os.getcwd(),
            'nut_execute_test')
        self.config['model_name'] = 'nutrient'
        self.config['paved_landcover_code'] = 60
        self.config['bare_landcover_code'] = 80
        self.config['landuse_uri'] = os.path.join(CLIPPED_DATA,
            'ecosystems.tif')
        self.config['do_parallelism'] = True
        self.config['fut_landuse_uri'] = os.path.join(CLIPPED_DATA,
            'ecosystems.tif')  # just to ensure it runs.

        static_maps.execute(self.config)

    def test_execute_quality(self):
        self.config['workspace_dir'] = os.path.join(os.getcwd(),
            'nut_execute_test')
        self.config['model_name'] = 'nutrient'
        self.config['paved_landcover_code'] = 60
        self.config['bare_landcover_code'] = 80
        self.config['landuse_uri'] = os.path.join(CLIPPED_DATA,
            'ecosystems.tif')
        self.config['do_parallelism'] = True
        self.config['fut_landuse_uri'] = os.path.join(CLIPPED_DATA,
            'ecosystems.tif')  # just to ensure it runs.
        self.config['num_simulations'] = 5

        if os.path.exists(self.config['workspace_dir']):
            shutil.rmtree(self.config['workspace_dir'])

        static_maps.execute(self.config)
