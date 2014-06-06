# Assume I'm executing this from the root of the permitting dir.


import shutil
import os
import tempfile

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

if __name__ == '__main__':
    lulc_uri = os.path.join(FULL_DATA, 'ecosystems.tif')
    model_name = 'nutrient'
    num_iterations = 50
    workspace = '/media/jadoug06/Natural Capital Project/james/nutrient_map_quality'
#    workspace = os.path.join(os.getcwd(), 'ignore_me', 'nutrient_map_quality')
    impact_region = os.path.join(FULL_DATA, 'servicesheds_col.shp')
    watersheds = os.path.join(FULL_DATA, 'watersheds_cuencas.shp')

    if not os.path.exists(workspace):
        os.makedirs(workspace)

    temp_dir = os.path.join(workspace, 'tmp')
    tempfile.tempdir = temp_dir
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    base_workspace = os.path.join(workspace, 'base_run')
    base_run = os.path.join(base_workspace, 'output', 'n_export.tif')
    if not os.path.exists(base_run):
        static_maps.execute_model(model_name, lulc_uri, base_workspace)

    for impact_name, impact_lucode in [('paved', 89), ('bare', 301)]:
        impact_workspace = os.path.join(workspace, impact_name)
        impact_static_map = os.path.join(DATA, 'colombia_static_data',
            '%s_%s_static_map_lzw.tif' % (model_name, impact_name))

        # set config to {} so that most settings are taken from default static
        # data values.
        static_maps.test_static_map_quality(base_run, impact_static_map,
            lulc_uri, impact_lucode, watersheds, model_name, impact_workspace,
            config=static_maps.get_static_data_json(model_name),
            num_iterations=num_iterations)

        csv_path = os.path.join(impact_workspace, 'impact_site_simulation.csv')
        static_maps.graph_it(csv_path, os.path.join(impact_workspace,
            '%s_%s_plot.png' % (model_name, impact_name)))

