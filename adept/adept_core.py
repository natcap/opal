"""Adept_core contains the core logic for the adept permitting tool."""

import logging
import os
import shutil

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
            'impact_type' - "Road/Mine" or "Bare ground/Paved".
            'area_of_influence_uri' - a uri to a shapefile that defines the
                area of influcence of the impact site
            'custom_static_map_uri' - a uri to a custom static map to assess
                impact
            

        Returns nothing."""

    LOGGER.debug('   _____       .___             __   ')
    LOGGER.debug('  /  _  \\    __| _/____ _______/  |_ ')
    LOGGER.debug(' /  /_\\  \\  / __ |/ __ \\\\____ \\   __\\')
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
    impact_columns = {
        0: {'name': 'Site Shapefile', 'total': False},
        2: {'name': 'Custom Impact Amount', 'total': True},
        3: {'name': 'Water Yield Impact Amount', 'total': True},
        4: {'name': 'Carbon Storage Impact Amount', 'total': True},
        5: {'name': 'Biodiversity Impact Amount', 'total': True},
    }
    
    impact_dict = {
        0: {
            'Site Shapefile': (
                '<a href="%s">%s</a>' % (
                    args['project_footprint_uri'],
                    os.path.basename(args['project_footprint_uri']))),
            'Custom Impact Amount': custom_static_values_flat.total.values()[0],
            'Water Yield Impact Amount': 'n/a',
            'Carbon Storage Impact Amount': 'n/a',
            'Biodiversity Impact Amount': 'n/a',
        },
    }
    
    offset_columns = {
        0: {'name': 'Offset Site', 'total': False},
        1: {'name': 'Custom Offset Amount', 'total': True},
        2: {'name': 'Water Yield Offset Amount', 'total': True},
        3: {'name': 'Carbon Storage Offset Amount', 'total': True},
        4: {'name': 'Biodiversity Offset Amount', 'total': True},
    }
    
    offset_dict = {
        0: {
            'Offset Site': 'Sample Site 1',
            'Custom Offset Amount': 534.3,
            'Water Yield Offset Amount': 'n/a',
            'Carbon Storage Offset Amount': 'n/a',
            'Biodiversity Offset Amount': 'n/a',
        },
        1: {
            'Offset Site': 'Sample Site 2',
            'Custom Offset Amount': 1234.2,
            'Water Yield Offset Amount': 'n/a',
            'Carbon Storage Offset Amount': 'n/a',
            'Biodiversity Offset Amount': 'n/a',
        },
    }
    
    report_data_source_directory = 'adept_report_html_style_data'
    report_data_out_directory = (
        os.path.join(args['workspace_dir'], report_data_source_directory))
    
    if os.path.exists(report_data_out_directory):
        try:
            shutil.rmtree(report_data_out_directory)
        except OSError as e:
            LOGGER.warn(e)
    
    try:
        shutil.copytree(
            report_data_source_directory,
            report_data_out_directory)
    except OSError as e:
            LOGGER.warn(e)
    
    
    css_uri = os.path.join(
        report_data_source_directory, 'table_style.css')
    jsc_uri = os.path.join(
        report_data_source_directory, 'sorttable.js')
    jquery_uri = os.path.join(
        report_data_source_directory, 'jquery-1.10.2.min.js')
    jsc_fun_uri = os.path.join(
        report_data_source_directory, 'total_functions.js')
    
    report_args = {
        'title': 'Adept Test Report',
        'elements': [
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
            },
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': (
                    '<h1>Impact Site Summary</h1><p>Impact Type: '
                    '<strong>%s</strong></p>' % args['impact_type']),
            },
            {
                'type': 'table',
                'section': 'body',
                'sortable': True,
                'checkbox': True,
                'total':True,
                'data_type':'dictionary',
                'columns': impact_columns,
                'data': impact_dict,
                'position': 1
            },
            {
                'type': 'text',
                'section': 'body',
                'position': 2,
                'text': '<h1>Offset Site Summary</h1>'
            },
            {
                'type': 'table',
                'section': 'body',
                'sortable': True,
                'checkbox': True,
                'total':True,
                'data_type':'dictionary',
                'columns': offset_columns,
                'data': offset_dict,
                'position': 3
            },
        ],
        'out_uri': os.path.join(args['workspace_dir'], 'report.html')
    }
    
    reporting.generate_report(report_args)
    