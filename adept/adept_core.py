"""Adept_core contains the core logic for the adept permitting tool."""

import logging
import os
import shutil
import ogr
import sys
import shapely.geometry
import shapely.wkb
import shapely.speedups
import shapely.prepared
import shapely.ops


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

    LOGGER.debug('custom_static_values_flat = %s', str(custom_static_values_flat))

    LOGGER.info("Building output report")
    impact_columns = {
        0: {'name': 'Site Shapefile', 'total': False},
        2: {'name': 'Custom Impact Amount', 'total': True},
        3: {'name': 'Water Yield Impact Amount', 'total': True},
        4: {'name': 'Carbon Storage Impact Amount', 'total': True},
        5: {'name': 'Biodiversity Impact Amount', 'total': True},
    }

    biodiversity_impact = calculate_biodiversity_impact(
        args['project_footprint_uri'], args['ecosystems_map_uri'])
    
    LOGGER.info(biodiversity_impact)
    
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

    offset_biodiversity_column_index = 5
    for ecosystem_name, bio_impact_dict in biodiversity_impact.iteritems():
        ecosystem_name = unicode(ecosystem_name, 'utf-8')
        impact_dict[0][ecosystem_name] = bio_impact_dict['area']
        impact_dict[0]['(impact factor) ' + ecosystem_name] = (
            bio_impact_dict['mitigation_area'])
        
        impact_columns[offset_biodiversity_column_index] = {
            'name': ecosystem_name,
            'total': True,
        }
        offset_biodiversity_column_index += 1
        impact_columns[offset_biodiversity_column_index] = {
            'name': '(impact factor) ' + ecosystem_name,
            'total': True,
        }
        offset_biodiversity_column_index += 1

    
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


def calculate_biodiversity_impact(permitting_area_ds_uri, ecosystems_ds_uri):
    
    #1) Load the permitting_area dataset into a shapely permitting_area_polygon
    permitting_area_ds = ogr.Open(permitting_area_ds_uri)
    permitting_area_layer = permitting_area_ds.GetLayer()
    polygon_list = []
    for feature_index in xrange(permitting_area_layer.GetFeatureCount()):
        feature = permitting_area_layer.GetFeature(feature_index)
        geometry = feature.GetGeometryRef()
        polygon_list.append(shapely.wkb.loads(geometry.ExportToWkb()))
    permitting_area_polygon = shapely.ops.cascaded_union(polygon_list)

    if not permitting_area_polygon.is_valid:
        print 'permitting area is not valid'
        sys.exit(1)

    #2) Make a spatial index?
    if shapely.speedups.available:
        print 'speedups available. speeding up'
        shapely.speedups.enable()

    #3) Loop through each feature in permitting_area ds and build a polygon out of it
    biodiversity_impacts = {}
    ecosystems_ds = ogr.Open(ecosystems_ds_uri)
    ecosystems_ds_layer = ecosystems_ds.GetLayer()
    for feature_index in xrange(ecosystems_ds_layer.GetFeatureCount()):
        feature = ecosystems_ds_layer.GetFeature(feature_index)
        ecosystem_type = feature.GetField('Ecos_dis')
        print ('testing ecosystem %s', ecosystem_type)
        impact_factor = feature.GetField('FACTOR_DE')
        geometry = feature.GetGeometryRef()
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
        prepared_polygon = shapely.prepared.prep(polygon)
        if prepared_polygon.intersects(permitting_area_polygon):
            print '\npermitting area intersects! calculating area overlap'
            intersection = permitting_area_polygon.intersection(polygon)

            biodiversity_impacts[ecosystem_type] = {
                'area': intersection.area / 10000.0,
                'mitigation_area': intersection.area / 10000.0 * impact_factor
            }

            print 'overlaps ', biodiversity_impacts[ecosystem_type]['area'],
            print 'Ha required offset: ',
            print biodiversity_impacts[ecosystem_type]['mitigation_area'], ' Ha'
    print '\ndone'
    return biodiversity_impacts
