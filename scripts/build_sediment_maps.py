import os
import logging
import shutil
import sys

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')
TEST_DATA = os.path.join(DATA, 'colombia_testing')

LOGGER = logging.getLogger('sediment_sm_cli')

if __name__ == '__main__':
    args = {
        'paved_landcover_code': 89,
        'bare_landcover_code': 301,
        'workspace_dir': os.path.join(os.getcwd(), 'sediment_static_maps'),
        'model_name': 'sediment',
        'landuse_uri': os.path.join(FULL_DATA, 'ecosystems.tif'),
        'fut_landuse_uri': os.path.join(FULL_DATA, 'es_comp_rd.tif'),
        'do_parallelism': True,
    }

    try:
        argument_1 = sys.argv[1]
    except IndexError:
        argument_1 = False

    if argument_1 == '--test':
        LOGGER.debug('Using testing URIs instead')
        args['landuse_uri'] = os.path.join(TEST_DATA, 'ecosystems_small_lzw.tif')
        args['fut_landuse_uri'] = os.path.join(TEST_DATA, 'es_comp_rd_small_lzw.tif')
        args['dem_uri'] = os.path.join(TEST_DATA, 'DEM_small_lzw.tif')

    if os.path.exists(args['workspace_dir']):
        shutil.rmtree(args['workspace_dir'])
    os.makedirs(args['workspace_dir'])
    static_maps.execute(args)
