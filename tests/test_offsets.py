import os
import shutil
import json

from invest_natcap.testing import GISTest

from adept import offsets

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')

class OffsetTest(GISTest):
    def test_locate_parcels(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        selection_area = os.path.join(DATA, 'sample_aoi.shp')
        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')

        workspace = os.path.join(os.getcwd(), 'offset_selection')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        offsets.locate_parcels(ecosystems, selection_area, impact_sites,
                workspace)

    def test_locate_offsets(self):
        previous_run = os.path.join(os.getcwd(), 'adept_smoke', ('Medio '
            'Magdalena'))

        if not os.path.exists(previous_run):
            raise AssertionError('You need to run a smoke test first')

        offset_sites = os.path.join(previous_run, 'offset_sites.shp')
        impact_sites = os.path.join(previous_run, '..', 'intermediate',
            'impact_sites', 'impacts_Medio Magdalena.shp')
        biodiversity_impacts = json.load(open(os.path.join(previous_run,
            'bio_impacts.json')))

        workspace = os.path.join(os.getcwd(), 'locate_offsets')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        output_vector = os.path.join(workspace, 'selected_offsets.shp')
        output_json = os.path.join(workspace, 'selected_parcels.json')

        offsets._select_offsets(offset_sites, impact_sites,
            biodiversity_impacts, output_vector,
            output_json)

    def test_select_set(self):
        parcels = {
            "9": {
                "area": 1567158.9849871695,
                "carbon": -41740.11022949219,
                "distance": 68392.0666114756,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 101.98334048409549,
                "sediment": 960.6894835291009
            },
            "10": {
                "area": 2190366.102658473,
                "carbon": -57960.36039733887,
                "distance": 71844.34045539482,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 0.430961374858671,
                "sediment": 8.788755132081802
            },
            "12": {
                "area": 7720670.530109197,
                "carbon": -205240.22917175293,
                "distance": 72989.58445179298,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 5776.272301197052,
                "sediment": 291505.14841365814
            },
            "13": {
                "area": 27162962.551896445,
                "carbon": -727099.5685424805,
                "distance": 68818.84478922746,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 6887.324089407921,
                "sediment": 342200.58039855957
            },
            "14": {
                "area": 2730070.2869472504,
                "carbon": -71801.63966369629,
                "distance": 70782.70976486948,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 1308.9485659856064,
                "sediment": 68000.25302813595
            },
            "15": {
                "area": 1508448.6858091652,
                "carbon": -40009.950271606445,
                "distance": 43006.831610647816,
                "ecosystem_type": "Bosques naturales del orobioma bajo de los Andes en NorAndina Montano_Valle_MaOrobiomas bajos de los Andes",
                "nutrient": 161.5203453078866,
                "sediment": 103.01930912258103
            },
        }

        rules = [
            ('area', 9999999)
        ]

        parcels = offsets.select_set(parcels, rules)
        self.assertEqual(parcels, ['10', '12', '14', '15', '9'])


