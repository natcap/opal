"""Top-level tests for running the permitting tool through to the end."""
import os
import shutil

from invest_natcap.testing import GISTest

from adept import adept_core

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')

class AdeptTest(GISTest):
    def setUp(self):
        self.workspace = os.path.join(os.getcwd(), 'adept_smoke')

        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    def test_smoke(self):
        args = {
            'workspace_dir': self.workspace,
            'project_footprint_uri': os.path.join(DATA, ('Example permitting'
                ' footprints'), 'Example_mining_projects.shp'),
            'impact_type': 'Road/Mine',
            'area_of_influence_uri': os.path.join(DATA, 'sample_aoi.shp'),
            'ecosystems_map_uri': os.path.join(DATA,
                'ecosys_dis_nat_comp_fac.shp'),
            'custom_static_map_uri': os.path.join(DATA,
                'DEM.tif'),
            'hydrozones': os.path.join(DATA, 'hydrozones.shp'),
            'data_dir': '..',
        }
        adept_core.execute(args)

    def test_write_vector(self):
        os.makedirs(self.workspace)

        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')
        out_vector = os.path.join(self.workspace, 'test_out.shp')
        feature_indices = range(5, 10)


        adept_core.write_vector(impact_sites, feature_indices, out_vector,
            'all')

