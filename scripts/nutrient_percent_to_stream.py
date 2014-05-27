# this script is to take an existing nutrient static map generation run and
# generate the percent_to_stream rasters.  This is necessary in cases where we
# have a complete workspace from before percent_to_stream rasters were added to
# the nutrient model.
# I'm assuming that this script is being executed from the
# invest-natcap.permitting folder.


import os
import logging

from invest_natcap.routing import routing_utils

DATA = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
LOGGER = logging.getLogger('nutrient_pts_builder')

if __name__ == '__main__':
    output_workspace = os.path.join(os.getcwd(), 'calculated_pts')
    input_workspace = os.path.join(os.getcwd(), '..', 'ignore_me',
        'nutrient_static_maps')

    if not os.path.exists(output_workspace):
        os.makedirs(output_workspace)

    for scenario in ['bare', 'paved', 'protection']:
        scenario_workspace = os.path.join(input_workspace, scenario,
            'nutrient_converted')
        intermediate = os.path.join(os.path.abspath(scenario_workspace), 'intermediate')

        in_flow_direction = os.path.join(intermediate, 'flow_direction.tif')
        in_dem = os.path.join(DATA, 'DEM.tif')
        in_stream = os.path.join(intermediate, 'stream.tif')
        in_retention = os.path.join(intermediate, 'eff_n.tif')
        in_source = os.path.join(intermediate, 'alv_n.tif')
        pixel_export = os.path.join(output_workspace, 'n_export.tif')

        percent_to_stream = os.path.join(output_workspace,
            'nutrient_%s_pts.tif' % scenario)

        LOGGER.debug('Building %s', percent_to_stream)
        routing_utils.pixel_amount_exported(
            in_flow_direction, in_dem, in_stream, in_retention, in_source,
            pixel_export, percent_to_stream_uri=percent_to_stream)



