import os

from invest_natcap.testing import GISTest

from adept import offsets

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')

class OffsetTest(GISTest):
    def test_locate_parcels(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        selection_area = os.path.join(DATA, 'sample_aoi.shp')
        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')

        offsets.locate_parcels(ecosystems, selection_area, impact_sites)
