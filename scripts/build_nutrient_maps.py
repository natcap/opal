import os
import logging

from adept import static_maps

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
CLIPPED_DATA = os.path.join(DATA, 'colombia_clipped')
FULL_DATA = os.path.join(DATA, 'colombia_tool_data')

LOGGER = logging.getLogger('nutrient_sm_cli')


def get_paths(workspace, scenario, model):
    """Convenience function to build paths based on workspace, scenario, model.

    workspace (string): The path to the workspace.
    scenario (string): The scenario we're building (usually either 'paved'
        or 'bare')
    model (string): The string name of the model to run.  One of 'sediment'
        or 'nutrient'.

    returns a dictionary with the following entries:
    {
        'base_run': The string path to the base export raster.
        'base_static_map': The string path to the base static map for this
            model and scenario.
        'workspace': The string path to the workspace location on disk.
    }
    """
    return {
        'base_run': os.path.join(workspace, 'nutrient_base', 'output',
                                 'n_export.tif'),
        'base_static_map': os.path.join(workspace,
            '%s_%s_static_map.tif' % (model, scenario)),
        'workspace': os.path.join(workspace, scenario),
    }

def test_existing_sm(args):
    """A function to run randomized simulations on an existing static map.

    Note:
    This function only runs tests for the paved scenario and only for
    the current landuse/landcover scenario.

    Configuration parameters will be loaded from the target model's static
    JSON configuration in the adept package.

    Parameters:
        args - a python dictionary with the following entries:
            'workspace_dir': the workspace location
            'model_name': The string name of the model to run.  One of
                'sediment' or 'nutrient'
            'landuse_uri': The path to the LULC on disk.
            'paved_landcover_code': The numeric landcover code to use.
            'num_simulations': The numeric number of simulations to run.
    """
    model = 'paved'
    paths = get_paths(args['workspace_dir'], model, args['model_name'])
    config = static_maps.get_static_data_json(args['model_name'])
    static_maps.test_static_map_quality(
        base_run=paths['base_run'],
        base_static_map=paths['base_static_map'],
        landuse_uri=args['landuse_uri'],
        impact_lucode=args['%s_landcover_code' % model],
        watersheds_uri=config['watersheds_uri'],
        model_name=args['model_name'],
        workspace=paths['workspace'],
        config=config,
        num_iterations=args['num_simulations']
    )


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
        'num_simulations': 5,
    }
    if os.path.exists(args['workspace_dir']):
        shutil.rmtree(args['workspace_dir'])
    os.makedirs(args['workspace_dir'])
    static_maps.execute(args)
