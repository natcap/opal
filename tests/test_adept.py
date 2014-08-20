"""Top-level tests for running the permitting tool through to the end."""
import os
import shutil
import json

from invest_natcap.testing import GISTest

import adept.i18n
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
            'impact_type': 'Road/Paved',
#            'area_of_influence_uri': os.path.join(DATA, 'sample_aoi.shp'),
            'ecosystems_map_uri': os.path.join(DATA,
                'ecosys_dis_nat_comp_fac.shp'),
            'custom_static_map_uri': os.path.join(DATA,
                'DEM.tif'),
            'search_areas_uri': os.path.join(DATA, 'Hydrographic_subzones.shp'),
            'threat_map': os.path.join(DATA, 'DEM.tif'),
#            'avoidance_areas': os.path.join(DATA, 'sample_aoi.shp'),
            'data_dir': '..',
#            'custom_static_maps': os.path.join(os.getcwd(), '..',
#                'custom_static_maps'),
#            'custom_servicesheds': 'global'
        }
        adept_core.execute(args)

    def test_smoke_es(self):
        adept.i18n.language.set('es')
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

        args = {
            'workspace_dir': self.workspace,
            'project_footprint_uri': os.path.join(DATA, ('Example permitting'
                ' footprints'), 'Example_mining_projects.shp'),
            'impact_type': 'Road/Paved',
#            'area_of_influence_uri': os.path.join(DATA, 'sample_aoi.shp'),
            'ecosystems_map_uri': os.path.join(DATA,
                'ecosys_dis_nat_comp_fac.shp'),
            'custom_static_map_uri': os.path.join(DATA,
                'DEM.tif'),
            'search_areas_uri': os.path.join(DATA, 'Hydrographic_subzones.shp'),
            'threat_map': os.path.join(DATA, 'DEM.tif'),
#            'avoidance_areas': os.path.join(DATA, 'sample_aoi.shp'),
            'data_dir': '..',
#            'custom_static_maps': os.path.join(os.getcwd(), '..',
#                'custom_static_maps'),
#            'custom_servicesheds': 'global'
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
        municipalities = os.path.join(TEST_DATA, 'limited_servicesheds_2.shp')
        biodiversity_impact = json.load(open(os.path.join(self.workspace,
            'Medio Magdalena', 'bio_impacts.json')))
        selected_parcels = os.path.join(self.workspace, 'Medio Magdalena',
            'selected_offsets.shp')
        natural_parcels = os.path.join(TEST_DATA,
            'medio_magdalena_avail_offsets.shp')

        # create a hacky temp object here so I can pass something in with the
        # correct attribute.
        class Custom(object):
            def __init__(self):
                self.total = None

        custom = Custom()
        custom.total = {1: 1, 2: 2}
        custom_static_values_flat = custom
        project_footprint = os.path.join(self.workspace, 'intermediate',
            'impact_sites', 'impact_Medio Magdalena.shp')
        sediment_total_impact = {
            'sediment': 1234567,
            'nutrient': 1234567,
            'carbon': 1234567,
            'custom': 9999999,
        }
        impact_type = 'An impact type!'
        output_workspace = self.workspace
        impact_sites = os.path.join(self.workspace, 'intermediate',
            'impact_sites', 'impacts_Medio Magdalena.shp')

        tmp_muni = os.path.join(self.workspace,
            'tmp_municipalities.shp')
        if os.path.exists(tmp_muni):
            os.remove(tmp_muni)

        adept_core.build_report(
            municipalities=municipalities,
            biodiversity_impact=biodiversity_impact,
            selected_parcels=selected_parcels,
            project_footprint=project_footprint,
            total_impacts=sediment_total_impact,
            impact_type=impact_type,
            output_workspace=output_workspace,
            impact_sites=impact_sites,
            pop_col='Pop_center',
            report_name='report.html',
            natural_parcels=natural_parcels,
            impacts_error=True,
            suggested_parcels=[],
            custom_es_servicesheds='global',
        )

