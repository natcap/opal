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

