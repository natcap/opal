"""Adept_core contains the core logic for the adept permitting tool."""

import logging

from invest_natcap import raster_utils

logging.basicConfig(format='%(asctime)s %(name)-18s %(levelname)-8s \
     %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('adept')

def execute(args):
    """The main execution function for adept.
        args - a python dictionary containing the following elements:
           'project_footprint_uri' - a URI to a shapefile of the project
                footprint
            'impact_type' - 0 or 1 depending on if it's a road/mine or
                bare ground/paved
            'area_of_influence_uri' - a uri to a shapefile that defines the
                area of influcence of the impact site
            'custom_static_map_uri' - a uri to a custom static map to assess
                impact
            

        Returns nothing."""

    LOGGER.debug('   _____       .___             __   ')
    LOGGER.debug('  /  _  \\    __| _/____ _______/  |_ ')
    LOGGER.debug(' /  /_\\  \\  / __ |/ __ \\\\____ \\   __\\\\')
    LOGGER.debug('/    |    \\/ /_/ \\  ___/|  |_> >  |  ')
    LOGGER.debug('\\____|__  /\\____ |\\___  >   __/|__|  ')
    LOGGER.debug('        \\/      \\/    \\/|__|         ')
    LOGGER.debug('                                     ')
    
    #can we rasterize based on polygon Z value?
    custom_static_values_flat = raster_utils.aggregate_raster_values_uri(
        args['custom_static_map_uri'], args['area_of_influence_uri'], 
        None)
        
    custom_static_values_id = raster_utils.aggregate_raster_values_uri(
        args['custom_static_map_uri'], args['area_of_influence_uri'], 
        'Id')
        
    LOGGER.debug('custom_static_values_flat = %s' % str(custom_static_values_flat))
    LOGGER.debug('custom_static_values_id = %s' % str(custom_static_values_id))
    