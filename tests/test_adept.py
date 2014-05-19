"""Top-level tests for running the permitting tool through to the end."""
import os
import shutil
import json

from invest_natcap.testing import GISTest

from adept import adept_core
from adept import analysis

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')
TEST_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_testing')

class AdeptTest(GISTest):
    def setUp(self):
        self.workspace = os.path.join(os.getcwd(), 'adept_smoke')

    def test_smoke(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

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

    def test_smoke_multi_hydrozone(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

        args = {
            'workspace_dir': self.workspace,
            'project_footprint_uri': os.path.join(TEST_DATA,
                'multi_hydrozone_impact_nat.shp'),
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

    def test_percent_overlap(self):
        os.makedirs(self.workspace)

        offset_sites = os.path.join(TEST_DATA, 'selected_offsets.shp')
        municipalities = os.path.join(DATA, 'Municipalities.shp')
        temp_file = os.path.join(self.workspace, 'tmp_inters_muni.shp')

        analysis.percent_overlap(offset_sites, municipalities, temp_file)

    def test_reporting(self):
        municipalities = os.path.join(DATA, 'Servicesheds_Col.shp')
        biodiversity_impact = json.load(open(os.path.join(self.workspace,
            'Medio Magdalena', 'bio_impacts.json')))
        selected_parcels = os.path.join(self.workspace, 'Medio Magdalena',
            'selected_offsets.shp')

        # create a hacky temp object here so I can pass something in with the
        # correct attribute.
        class Custom(object):
            def __init__(self):
                self.total = None

        custom = Custom()
        custom.total = {1: 1, 2: 2}
        custom_static_values_flat = custom
        project_footprint = os.path.join(DATA, ('Example permitting'
            ' footprints'), 'Example_mining_projects.shp')
        sediment_total_impact = {
            'sediment': 1234567,
            'nutrient': 1234567,
            'carbon': 1234567,
        }
        impact_type = 'An impact type!'
        output_workspace = self.workspace
        impact_sites = os.path.join(self.workspace, 'intermediate',
            'impact_sites.shp')

        os.remove(os.path.join(self.workspace, 'tmp_municipalities.shp'))

        adept_core.build_report(municipalities, biodiversity_impact,
            selected_parcels,
            custom_static_values_flat, project_footprint,
            sediment_total_impact, impact_type, output_workspace, impact_sites,
            'Pop_center')
