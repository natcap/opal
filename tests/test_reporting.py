import os
import shutil

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils

from adept import reporting

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')
TEST_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_testing')
CLIPPED_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_clipped')

class ReportingTest(GISTest):
    def test_impacted_parcels_table(self):
        offset_sites = os.path.join(TEST_DATA,
            'medio_magdalena_avail_offsets.shp')
        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')
        workspace = os.path.join(os.getcwd(), 'impacted_parcels')
        csv_uri = os.path.join(workspace, 'parcels.csv')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        reporting.impacted_parcels_table(impact_sites, offset_sites, csv_uri)

