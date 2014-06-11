import os
import logging
import shutil

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

LOGGER = logging.getLogger('nutrient_sm_cli')

if __name__ == '__main__':
    args = {
        'paved_landcover_code': 89,
        'bare_landcover_code': 301,
        'workspace_dir': os.path.join(os.getcwd(), 'nutrient_static_maps'),
        'model_name': 'nutrient',
        'landuse_uri': os.path.join(FULL_DATA, 'ecosystems.tif'),
        'fut_landuse_uri': os.path.join(FULL_DATA, 'es_comp_rd.tif'),
        'do_parallelism': True,
        'valuation_enabled': False,
    }
    if os.path.exists(args['workspace_dir']):
        shutil.rmtree(args['workspace_dir'])
    os.makedirs(args['workspace_dir'])
    static_maps.execute(args)
