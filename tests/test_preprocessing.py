import os
import shutil

from invest_natcap.testing import GISTest

from adept import preprocessing

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')

class PreprocessingTest(GISTest):
    def test_split_multipolygons(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')

        workspace = os.path.join(os.getcwd(), 'test_split_workspace')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

        os.makedirs(workspace)
        out_vector = os.path.join(workspace, 'test_split.shp')

        preprocessing.split_multipolygons(ecosystems, out_vector, ['Ecos_dis',
            'Ecosistema', 'FACTOR_DE'])
