import os

from adept import adept_core

DATA = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')

ADEPT_ARGS = {
    'workspace_dir': os.path.join(os.getcwd(), 'adept_workspace'),
    'project_footprint_uri': os.path.join(DATA, 'Example permitting footprints',
        'Example_mining_projects.shp'),
    'impact_type': 'Road/Mine',
    'area_of_influence_uri': os.path.join(DATA, 'sample_aoi.shp'),
    'ecosystems_map_uri': os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp'),
    'custom_static_map_uri': os.path.join(DATA,
        'sample_static_impact_map.tif'),
}

if __name__ == '__main__':
    adept_core.execute(ADEPT_ARGS)


