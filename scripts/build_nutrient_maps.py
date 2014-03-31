import os

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

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
    static_maps.execute(args)
