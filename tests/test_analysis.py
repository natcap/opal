import os
import shutil
import json

from invest_natcap.testing import GISTest

from adept import analysis

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')
TEST_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_testing')

class AnalysisTest(GISTest):
    def test_vectors_intersect(self):
        vector_1 = os.path.join(DATA, 'sample_aoi.shp')
        vector_2 = os.path.join(DATA, 'watersheds_cuencas.shp')
        self.assertEqual(True, analysis.vectors_intersect(vector_1, vector_2))

        vector_2 = os.path.join(DATA, 'Protected_areas.shp')
        self.assertEqual(False, analysis.vectors_intersect(vector_1, vector_2))
