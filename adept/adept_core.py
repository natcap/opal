"""Adept_core contains the core logic for the adept permitting tool."""

import logging
import os

from invest_natcap import raster_utils
from invest_natcap import reporting

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
    
    raster_utils.create_directories([args['workspace_dir']])
    
    #can we rasterize based on polygon Z value?
    LOGGER.info(
        "Assessing impact of project footprint over a custom static map")
    custom_static_values_flat = raster_utils.aggregate_raster_values_uri(
        args['custom_static_map_uri'], args['project_footprint_uri'], 
        None)
    
    LOGGER.debug('custom_static_values_flat = %s' % str(custom_static_values_flat))
    
    LOGGER.info("Building output report")
    impact_dict = {
        0: {
            'Site':os.path.basename(args['project_footprint_uri']),
            'Impact Type': 'null',
            'Impact Amount': custom_static_values_flat.total.values()[0]
        },
    }
    columns = {
        0: {'name': 'Site', 'total': False},
        1: {'name': 'Impact Type', 'total': False},
        2: {'name': 'Impact Amount', 'total': False},
    }
    
    css_uri = '../reporting_data/table_style.css'
    jsc_uri = '../reporting_data/sorttable.js'
    jquery_uri = '../reporting_data/jquery-1.10.2.min.js'
    jsc_fun_uri = '../reporting_data/total_functions.js'
    
    report_args = {
        'title': 'Adept Test Report',
        'elements': [
            {
                'type': 'table',
                'section': 'body',
                'sortable': True,
                'checkbox': True,
                'total':True,
                'data_type':'dictionary',
                'columns':columns,
                'key':'ws_id',
                'data': impact_dict,
                'position': 1
            },
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': 'Here is an example of some text'
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'link',
                'position': 0,
                'src': css_uri
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'position': 1,
                'src': jsc_uri
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'position': 2,
                'src': jquery_uri
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'position': 3,
                'src': jsc_fun_uri
            }
        ],
        'out_uri': os.path.join(args['workspace_dir'], 'report.html')
    }
    
    reporting.generate_report(report_args)
    