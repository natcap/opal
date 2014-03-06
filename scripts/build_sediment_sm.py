import os

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

if __name__ == '__main__':
    lulc_uri = os.path.join(FULL_DATA, 'ecosystems.tif')
    target_lucode = 124
    workspace = os.path.join(os.getcwd(), 'sediment_static_map')
    static_map_uri = os.path.join(workspace, 'sediment_static_map_full.tif')

    static_maps.build_static_map('sediment', lulc_uri, target_lucode,
        static_map_uri, workspace=workspace)
