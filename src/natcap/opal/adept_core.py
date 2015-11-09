"""Adept_core contains the core logic for the natcap.opal permitting tool."""
# -*- coding: utf-8 -*-

import json
import glob
import logging
import os
import shutil
import tempfile
from types import BooleanType
from types import StringType
import time

from osgeo import ogr
import pygeoprocessing

from natcap.invest import reporting
import natcap.opal
import natcap.opal.i18n
import preprocessing
import offsets
import static_maps
import reporting as opal_reporting
import analysis
import utils

logging.basicConfig(format='%(asctime)s %(name)-18s %(levelname)-8s \
     %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('natcap.opal')

SOURCE_DATA = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
REPORT_DATA = os.path.join(natcap.opal.local_dir(__file__), 'report_data')
_ = natcap.opal.i18n.language.ugettext
LABEL_PROTECTION = 'Protection'
LABEL_RESTORATION = 'Restoration'
DIST_OPAL = 'opal'
DIST_MAFE = 'mafe-t'

class InvalidImpactsVector(Exception): pass
class InvalidInput(Exception): pass

def execute(args):
    """The main execution function for natcap.opal.
        args - a python dictionary containing the following elements:
            'workspace_dir' - A uri to the output workspace.
            'project_footprint_uri' - a URI to a shapefile of the project
                footprint
            'impact_type' - "Road/Mine" or "Bare ground/Paved".
            'area_of_influence_uri' - a uri to a shapefile that defines the
                area of influcence of the impact site
            'ecosystems_map_uri' - a URI to an OGR vector with all the
                ecosystems polygons.
            'offset_parcels' - a URI to an OGR vector with parcels that can be
                selected as offset parcels.  May be the same URI as
                args['ecosystems_map_uri'] in cases where args['offset_scheme']
                is 'Protection'.
            'threat_map' - ?
            'species_richness_map' - ?
            'search_areas_uri' - a URI to an OGR vector containing search area.
                TODO: rename this to be hydrosubzones.
            'avoidance_areas' - a URI to an OGR vector of areas within which
                offset parcels may not be selected.
            'conservation_portfolio' - a URI to an OGR vector of priority areas
                for conservation.  Regions defined in the conservation
                portfolio will be selected over other offset parcels within the
                same search area.
            'previously_granted_impacts' - ?
            'previously_selected_offsets' - an OGR vector with previously
                selected offset parcels.  These parcels may not be selected
                again.
            'municipalities_uri' - A URI to a vector of municipalities. If not
                provided, the tool will try to use the internal municipalities
                vector.  If neither is provided nor available, an exception
                will be raised.
            'data_dir' - a URI to a folder that contains a folder called
                'data', which itself contains the necessary colombia tool data.
            'sediment_static_maps' - a uri to a folder that contains the three
                static maps generated. (optional)
            'nutrient_static_maps' - a uri to a folder that contains the three
                static maps generated. (optional)
            'carbon_static_maps' - a uri to a folder that contains the three
                static maps generated. (optional)
            'custom_static_maps' - a uri to a folder that contains the three
                static maps generated. (optional)
            'custom_servicesheds' - a string, either 'hydrological' or
                'global'.  Required if custom_static_maps argument is provided.
                If 'hydrological', the custom_static_maps folder must also
                contain appropriate percent-to-stream rasters, following the
                same naming convention as the other routed static data folders.
            'do_carbon' - Boolean.  Optional.  Whether to include carbon in
                calculations.  Defaults to True if not specified.
            'do_nutrient' - Boolean.  Optional.  Whether to include nitrogen
                in calculations. Defaults to True if not specified.
            'do_sediment' - Boolean.  Optional.  Whether to include sediment
                in calculations. Defaults to True if not specified.
            'offset_scheme' - a number.  The number must be one of [0, 1, 2],
                and indicates the following offset selection schemes:
                    0 - Ecosystem services only will be considered when
                        selecting offset parcels.
                    1 - Biodiversity only will be considered when selecting
                        offset parcels.
                    2 - Both biodiversity and ecosystem services will be
                        considered when selecting offset parcels.
                    This input is optional.  When not provided, defaults to 1.
            'carbon_mitigation_ratio' - (optional) The numeric factor by which
                carbon impact quantities will be multiplied to calculate the
                required offset quantitiy in the report.  This defaults to 1.0
                if not provided by the user.
            'nutrient_mitigation_ratio' - (optional) The numeric factor by which
                nutrient impact quantities will be multiplied to calculate the
                required offset quantitiy in the report.  This defaults to 1.0
                if not provided by the user.
            'sediment_mitigation_ratio' - (optional) The numeric factor by which
                sediment impact quantities will be multiplied to calculate the
                required offset quantitiy in the report.  This defaults to 1.0
                if not provided by the user.
            'custom_mitigation_ratio' - (optional) The numeric factor by which
                custom ES impact quantities will be multiplied to calculate the
                required offset quantitiy in the report.  This defaults to 1.0
                if not provided by the user.
            'prop_offset' - (optional) the proportion of (impacts * mitigation
                ratio) that the set of recommended parcels should offset.
                Defaults to 1.0 if not user-defined.
            'distribution' - (optional) The distribution of the tool we're
                running.  Either 'mafe-t' or 'opal'.  Defaults to 'mafe-t' if
                not provided.

        Returns nothing."""

    LOGGER.debug('Current language: "%s"', natcap.opal.i18n.language.current_lang)
    # build a list of possible places to look for the ascii art text file in
    # order of priority.
    possible_dirs = []
    if natcap.opal.is_frozen():
        possible_dirs += [natcap.opal.get_frozen_dir()]
    possible_dirs += [os.path.dirname(__file__), os.getcwd()]
    ascii_art_uri = ''
    for dirname in possible_dirs:
        ascii_art_uri = os.path.join(dirname, 'ASCII_NAME.txt')
        if os.path.exists(ascii_art_uri):
            break

    if os.path.exists(ascii_art_uri):
        with open(ascii_art_uri) as ascii_art:
            for line in ascii_art:
                LOGGER.debug(r'%s', line.rstrip())
    else:
        LOGGER.debug(r'   _____       .___             __    ')
        LOGGER.debug(r'  /  _  \    __| _/____ _______/  |_  ')
        LOGGER.debug(r' /  /_\  \  / __ |/ __ \\____ \   __\ ')
        LOGGER.debug(r'/    |    \/ /_/ \  ___/|  |_> >  |   ')
        LOGGER.debug(r'\____|__  /\____ |\___  >   __/|__|   ')
        LOGGER.debug(r'        \/      \/    \/|__|          ')
        LOGGER.debug(r'                                      ')

    common_data = static_maps.get_common_data_json(args['data_dir'])

    dirs = {
        'workspace': os.path.abspath(args['workspace_dir']),
        'intermediate': os.path.join(args['workspace_dir'], 'intermediate'),
        'impact_sites': os.path.join(args['workspace_dir'], 'intermediate',
            'impact_sites'),
        'temp': os.path.join(args['workspace_dir'], 'temp'),
        'results': os.path.join(args['workspace_dir'], 'results'),
    }
    LOGGER.debug('workspace directories: %s', json.dumps(dirs, indent=4,
        sort_keys=True))
    old_temp_dir = tempfile.tempdir
    tempfile.temp_dir = dirs['temp']

    try:
        _ecosystems = args['ecosystems_map_uri']
    except KeyError:
        _ecosystems = common_data['ecosystems']

    try:
        # allow the user to not include offset_parcels.  This would be default
        # behavior in MAFE-T
        _offset_parcels = args['offset_parcels']
    except KeyError:
        _offset_parcels = _ecosystems

    files = {
        'active_hydrozones': os.path.join(dirs['intermediate'],
            'active_hydrozones.shp'),
        'max_search_area': os.path.join(dirs['intermediate'],
            'search_area.shp'),
        'ecosystems': _ecosystems,
        'offset_parcels': _offset_parcels,
        'prep_offset_sites': os.path.join(dirs['temp'],
            'tmp_offset_sites.shp'),
        'prep_natural_parcels': os.path.join(dirs['intermediate'],
            'prepared_ecosystems.shp'),
        'global_impacted_subzones': os.path.join(dirs['intermediate'],
            'impacted_subzones.shp'),
        'union_of_subzones': os.path.join(dirs['intermediate'],
            'union_impacted_subzones.shp'),
        'buffered_subzones': os.path.join(dirs['intermediate'],
            'buffered_subzones.shp'),
        'base_report': os.path.join(dirs['results'], 'index.html'),
        'impacted_sb3': os.path.join(dirs['intermediate'],
                                     'impacted_softboundary3.shp')
    }

    pygeoprocessing.create_directories(dirs.values())

    try:
        if args['offset_scheme'] not in [0, 1, 2]:
            raise InvalidInput(('Offset scheme %s is invalid.  Must be ',
                ' in [0, 1, 2]') % args['offset_scheme'])
    except KeyError:
        # raised when the offset_scheme key is not in args.
        # When this happens, assume the default behavior, to use biodiversity
        # as an offset scheme.
        args['offset_scheme'] = offsets.OFFSET_SCHEME_BIODIV

    # a list of all the ecosystem services we care about right now.  Only using
    # the custom static map right now as a proxy for sediment.
    # TODO: if user provided custom static map, add a 'custom' service.
    # TODO: Add a static protection map here.
    LOGGER.debug("User-defined impact type: %s", args['impact_type'])
    assert args['impact_type'] in ['Road/Paved', 'Mine/Bare'], ('Invalid '
        'impact type %s' % args['impact_type'])

    if args['impact_type'] == 'Road/Paved':
        impact_key = 'paved'
    else:
        impact_key = 'bare'
    LOGGER.debug('Using impact type %s', impact_key)

    LOGGER.debug('Checking desired services to consider')
    desired_services = []
    for service in ['carbon', 'nutrient', 'sediment']:
        key = 'do_%s' % service
        try:
            do_service = args[key]
        except KeyError:
            do_service = True
        if do_service:
            desired_services.append(service)

    if len(desired_services) == 0:
        raise RuntimeError('You must select at least one service')
    LOGGER.debug('Considering services %s', desired_services)

    if 'custom_static_maps' in args:
        LOGGER.debug('User specified that custom ES should be considered')
        desired_services.append('custom')
        assert args['custom_servicesheds'] in ['hydrological', 'global']
        custom_servicesheds = args['custom_servicesheds']
    else:
        custom_servicesheds = None

    impact_services = []
    protection_services = []
    for es_name in desired_services:
        args_key = '%s_static_maps' % es_name

        use_percent_to_stream = False
        if es_name in ['nutrient']:
            use_percent_to_stream = True
        elif es_name == 'custom':
            LOGGER.debug('Checking for custom ES inputs.')
            # We only want to use percent_to_stream if we're using hydrological
            # servicesheds.
            # this might raise a keyError if the user doesn't provide the right
            # inputs.  They should expect an error in this case anyways.
            if args['custom_servicesheds'] == 'hydrological':
                LOGGER.debug('Custom ES inputs are hydrological')
                use_percent_to_stream = True

        try:
            if args['offset_type'] == LABEL_PROTECTION:
                future_base = 'protect'
            elif args['offset_type'] == LABEL_RESTORATION:
                future_base = 'restore'
            else:
                raise InvalidInput(('Offset type is invalid.  Must be one of ',
                    '"Protection" or "Restoration", "%s" found' % future_base))

            static_maps_dir = args[args_key]
            LOGGER.debug('User defined custom static maps for %s', es_name)
            fmt_string = '%s_%s_static_map.tif'
            impact_filename = fmt_string % (es_name, impact_key)
            protection_filename = fmt_string % (es_name, future_base)

            if use_percent_to_stream:
                pts_fmt_string = '%s_%s_pts.tif'
                impact_percent_to_stream = os.path.join(static_maps_dir,
                    pts_fmt_string % (es_name, impact_key))
                protect_percent_to_stream = os.path.join(static_maps_dir,
                    pts_fmt_string % (es_name, future_base))
            else:
                impact_percent_to_stream = None
                protect_percent_to_stream = None

            static_impact_map = os.path.join(static_maps_dir, impact_filename)
            static_protection_map = os.path.join(static_maps_dir,
                protection_filename)
            LOGGER.debug('Using custom static impact map %s',
                static_impact_map)
            LOGGER.debug('Using custom static protection map %s',
                static_protection_map)
        except KeyError:
            # If The user defined custom static map values, we want to
            # consider them.  If not, we want to skip them.
            if es_name == 'custom':
                continue

            static_impact_map = common_data['static_maps'][impact_key][es_name]
            static_protection_map = common_data['static_maps']['protection'][es_name]

            if use_percent_to_stream:
                impact_percent_to_stream = common_data['percent_to_stream'][es_name][impact_key]
                protect_percent_to_stream = common_data['percent_to_stream'][es_name]['protection']
            else:
                impact_percent_to_stream = None
                protect_percent_to_stream = None

            LOGGER.debug('No custom static maps defined for %s', es_name)
            LOGGER.debug('Using default static impact map %s',
                static_impact_map)
            LOGGER.debug('Using default static future scenario map %s',
                static_protection_map)


        static_data = {
            'static_impact': static_impact_map,
            'static_protection': static_protection_map,
            'pts_impact': impact_percent_to_stream,
            'pts_protection': protect_percent_to_stream,
        }

        protection_services.append((es_name, static_data))

    # verify that the correct maps exist on disk.  If they don't exist, raise
    # an error.  They might not have installed static maps with the Colombia
    # installer.
    for es_name, static_data in protection_services:
        LOGGER.debug('Verifying static maps exist for %s', es_name)

        files_to_check = [
            ('static_impact', 'static impact'),
            ('static_protection', 'static protection'),
            ('pts_impact', 'impact percent-to-stream'),
            ('pts_protection', 'protection percent-to-stream'),
        ]

        for raster_key, label in files_to_check:
            file_uri = static_data[raster_key]
            if file_uri is None:
                continue

            if not os.path.exists(file_uri):
                file_uri = os.path.abspath(file_uri)
                LOGGER.critical('Expecting %s map at %s, but not found',
                    label, file_uri)
                raise IOError('File not found: %s' % file_uri)

    LOGGER.debug('Considering services: %s', [r[0] for r in protection_services])

    # get a list of all static maps for all services.
    all_static_maps = []
    for map_list in [s[1].values() for s in protection_services]:
        for map_uri in map_list:
            if map_uri is not None:
                all_static_maps.append(map_uri)
    if not preprocessing.impacts_in_static_maps(all_static_maps,
            args['project_footprint_uri']):
        raise InvalidImpactsVector(('Some polygon(s) do not intersect static '
            'maps.  Correct this and re-run the tool.'))

    # Check distribution if it's provided.  Otherwise, assume we're in OPAL.
    if 'distribution' in args:
        if args['distribution'] not in [DIST_OPAL, DIST_MAFE]:
            raise RuntimeError('Distribution must be one of %s, %s found' %
                ([DIST_OPAL, DIST_MAFE], args['distribution']))
    else:
        args['distribution'] = DIST_OPAL
    LOGGER.debug('Using distribution %s' % args['distribution'])

    try:
        hydro_subzones = args['search_areas_uri']
        LOGGER.debug('Using user-provided hydro subzones: %s', hydro_subzones)

        hydrozones = os.path.join(dirs['intermediate'], 'hydrozones.shp')
        # build the hydrozones out of the hydrosubzones by zone attribute
        contained_subzones = preprocessing.union_by_attribute(hydro_subzones,
            'zone', hydrozones)
    except KeyError:
        hydro_subzones = common_data['hydrosubzones']
        hydrozones = common_data['hydrozones']
        LOGGER.debug('Using default hydro subzones: %s', hydro_subzones)
        LOGGER.debug('Using default hydrozones: %s', hydrozones)

    try:
        municipalities = args['municipalities_uri']
        LOGGER.debug('Using user-provided municipalities: %s', municipalities)
    except KeyError:
        municipalities = common_data['municipalities']
        LOGGER.debug('Using default municipalities: %s', municipalities)
    finally:
        # Raise error about required municipalities only if the file can't be
        # found.
        if args['distribution'] == DIST_OPAL:
            if not os.path.exists(municipalities):
                municipalities = None
            else:
                # if the user prvided a softboundary3 (municipalities), save off a vector
                # of all the municipalities that intersect the impact sites.
                preprocessing.locate_intersecting_polygons(
                    municipalities, args['project_footprint_uri'],
                    files['impacted_sb3'])
        else:
            raise RuntimeError(("Municipalities vector is required, "
                "but was not provided or could not be found"))

    try:
        area_of_influence = args['area_of_influence_uri']
        LOGGER.debug('Using user-provided AOI')
    except KeyError:
        LOGGER.debug('Building AOI from hydro subzones')
        area_of_influence = os.path.join(dirs['intermediate'], 'aoi_computed.shp')
        preprocessing.prepare_aoi(args['project_footprint_uri'],
            hydro_subzones, area_of_influence)

    LOGGER.info('Determining active hydrozone')
    preprocessing.locate_intersecting_polygons(hydrozones,
        args['project_footprint_uri'], files['active_hydrozones'])

    LOGGER.info('Preparing impact sites')
    impact_sites_list = preprocessing.prepare_impact_sites(args['project_footprint_uri'],
        hydrozones, dirs['impact_sites'])

    LOGGER.info('Finding the union of active hydrozones and the AOI')
    preprocessing.union_of_vectors([files['active_hydrozones'],
        area_of_influence], files['max_search_area'])

    if 'include_lci' not in args:
        args['include_lci'] = True
    else:
        assert type(args['include_lci']) is BooleanType, ('Key "include_lci"'
            ' must be a boolean.  %s found' % type(args['include_lci']))

    LOGGER.info('Preparing offset sites')
    preprocessing.prepare_offset_parcels(files['offset_parcels'],
        files['active_hydrozones'], files['prep_offset_sites'],
        include_lci=args['include_lci'])

    # if the natural and offset parcels are found in different vectors, then
    # we'll need to prepare a subset of the natural parcels as well.
    # If natural and offset parcels are found in the same vector, then we can
    # use the prepared offset parcels vector for the prepared natural parcels.
    _abspath = lambda p: os.path.abspath(p)
    if _abspath(files['offset_parcels']) != _abspath(files['ecosystems']):
        LOGGER.info('Preparing impacted natural parcels')

        # Build a vector of the hydro subzones that intersect the impact sites.
        preprocessing.locate_intersecting_polygons(args['search_areas_uri'],
            args['project_footprint_uri'], files['global_impacted_subzones'])
        preprocessing.union_of_vectors([files['global_impacted_subzones']],
            files['union_of_subzones'])

        # when buffering, include at least 1000 extra distance units of
        # parcels, just in case there are any parcels near the boundary of the
        # hydrozones that need to be included in the LCI calculations.
        preprocessing.buffer_vector(files['union_of_subzones'], 1000,
            files['buffered_subzones'])

        preprocessing.prepare_offset_parcels(files['ecosystems'],
            files['buffered_subzones'], files['prep_natural_parcels'],
            include_lci=args['include_lci'])
    else:
        LOGGER.debug('Offset parcels are natural')
        files['prep_natural_parcels'] = files['prep_offset_sites']


    try:
        servicesheds = args['servicesheds_uri']
        LOGGER.debug('User provided custom servicesheds: %s', servicesheds)
    except KeyError:
        servicesheds = common_data['servicesheds']
        LOGGER.debug('Using default servicesheds: %s', servicesheds)

    # Start looping through all of the impacted hydrozones
    for impact_sites_data in impact_sites_list:
        if type(impact_sites_data['name']) is StringType:
            recode = lambda s: s.decode('utf-8')
        else:
            recode = lambda s: s.encode('utf-8')
        impact_sites_data['name'] = recode(impact_sites_data['name'])

        LOGGER.debug('Processing impacts for hydrozone %s',
            impact_sites_data['name'])
        _clean_hydrozone_name = impact_sites_data['name'].lower().replace(' ', '_')

        hzone_dir = os.path.join(dirs['results'], _clean_hydrozone_name)
        hzone_dev = os.path.join(hzone_dir, '_dev')
        hzone_static_maps = os.path.join(hzone_dir, 'static_data')
        pygeoprocessing.create_directories([hzone_dir, hzone_dev,
            hzone_static_maps])

        hzone_paths = {
            'offset_sites': os.path.join(hzone_dir, 'offset_sites_available.shp'),
            'all_offsets': os.path.join(hzone_dir, 'potential_offsets_in_zone.shp'),
            'all_natural_parcels': os.path.join(hzone_dir, 'natural_parcels_in_zone.shp'),
            'impact_sites': impact_sites_data['uri'],
            'bio_impacts': os.path.join(hzone_dev, 'bio_impacts.json'),
            'selected_offsets': os.path.join(hzone_dir, 'offset_sites_filtered.shp'),
            'impacted_muni': os.path.join(hzone_dir, 'impacted_softboundary2.shp'),
            'servicesheds': os.path.join(hzone_dir, 'servicesheds_in_zone.shp'),
            'hydrozone': os.path.join(hzone_dir, 'impacted_zone.shp'),
            'hydrosubzones': os.path.join(hzone_dir, 'impacted_subzones.shp'),
            'parcel_info': os.path.join(hzone_dev, 'selected_parcels.json'),
        }

        LOGGER.info('Locating the current hydrozone polygon')
        preprocessing.locate_intersecting_polygons(files['active_hydrozones'],
            hzone_paths['impact_sites'], hzone_paths['hydrozone'])

        # TODO: use a split_vector function?
        LOGGER.info('Locating servicesheds intersecting this hydrozone')
        preprocessing.locate_intersecting_polygons(servicesheds,
            hzone_paths['hydrozone'], hzone_paths['servicesheds'])

        LOGGER.info('Locating offset parcels available for this hydrozone')
        preprocessing.locate_intersecting_polygons(files['prep_offset_sites'],
            hzone_paths['hydrozone'], hzone_paths['all_offsets'], clip=True)

        LOGGER.info('Locating natural parcels available for this hydrozone')
        preprocessing.locate_intersecting_polygons(files['prep_natural_parcels'],
            hzone_paths['hydrozone'], hzone_paths['all_natural_parcels'],
            clip=True)

        LOGGER.info('Cutting out the impact sites from available offset parcels.')
        preprocessing.subtract_vectors(hzone_paths['all_offsets'],
            hzone_paths['impact_sites'], hzone_paths['offset_sites'])

        LOGGER.info('Aggregating services provided by parcels')
        service_impacts = {}
        for service_name, static_data in protection_services:
            LOGGER.debug('Aggregating stats for service %s', service_name)
            LOGGER.debug('Aggregating %s stats for offset sites', service_name)
            _ = analysis.aggregate_stats(static_data['static_protection'],
                hzone_paths['offset_sites'], 'FID', service_name,
                static_data['pts_protection'])
            LOGGER.debug('Aggregating %s stats for impact sites', service_name)
            service_impacts[service_name] = analysis.aggregate_stats(
                static_data['static_impact'], hzone_paths['impact_sites'], 'FID',
                service_name, static_data['pts_impact'])

        for args_key, col_name in [('threat_map', 'Threat'), ('richness_map',
            'Richness')]:
            if args_key not in args:
                continue
            LOGGER.debug('Found %s map in args.  Calculating stats.',
                col_name.lower())
            _ = analysis.aggregate_stats(args[args_key],
                hzone_paths['impact_sites'], 'FID', col_name)
            _ = analysis.aggregate_stats(args[args_key],
                hzone_paths['offset_sites'], 'FID', col_name)
            _ = analysis.aggregate_stats(args[args_key],
                hzone_paths['all_offsets'], 'FID', col_name)

    #    LOGGER.info('Selecting offset parcels')
    #    offset_dir = os.path.join(output_dir, 'offsets')
    #    offset_info = offsets.select_offsets(offset_sites, impact_sites, offset_dir)
    #
    #    # find the impact sum
    #    total_impacts = {
    #        'sediment': sum(map(lambda r: r['services']['sediment']['impact'],
    #            offset_info.values()))
    #    }
    #
    #    LOGGER.debug(json.dumps(offset_info, sort_keys=True, indent=4))

        # get the proper impacts from the returned service impacts from the
        # above analysis step.
        _get_impacts = lambda k: sum(service_impacts[k].values())
        total_impacts = dict((service, _get_impacts(service)) for service in
            desired_services)
#        total_impacts = {
#            'sediment': _get_impacts('sediment'),
#            'nutrient': _get_impacts('nutrient'),
#            'carbon': _get_impacts('carbon'),
#        }
        if 'custom' in service_impacts:
            total_impacts['custom'] = _get_impacts('custom')

        LOGGER.debug('Total impacts: %s', total_impacts)

        # TODO: Write these values to JSON in the calculat_bio_impact function
        biodiversity_impact = analysis.calculate_biodiversity_impact(
            hzone_paths['impact_sites'], hzone_paths['all_natural_parcels'])
        json.dump(biodiversity_impact, open(hzone_paths['bio_impacts'], 'w'), sort_keys=True,
            indent=4)

        LOGGER.info(biodiversity_impact)

        # Build a vector of the current hydro subzones.
        preprocessing.locate_intersecting_polygons(hydro_subzones,
            hzone_paths['impact_sites'], hzone_paths['hydrosubzones'])

        comparison_vectors = {
            'AOI': area_of_influence,
            'Subzone': hzone_paths['hydrosubzones'],
        }

        try:
            comparison_vectors['Conservation Portfolio'] = \
                args['conservation_portfolio']
        except KeyError:
            LOGGER.debug('Conservation portfolio not in args, skipping.')

        if municipalities is not None:
            # Get all the municipalities that intersect with the impact vector.
            preprocessing.locate_intersecting_polygons(municipalities,
                hzone_paths['impact_sites'], hzone_paths['impacted_muni'])
            comparison_vectors['City'] = hzone_paths['impacted_muni']

        #biodiversity_impact contains ONLY the biodiversity impacts.
        _, recommended_parcels = offsets._select_offsets(
            hzone_paths['offset_sites'],
            hzone_paths['impact_sites'], biodiversity_impact,
            hzone_paths['selected_offsets'], hzone_paths['parcel_info'],
            comparison_vectors, total_impacts.keys(),
            offset_scheme=args['offset_scheme'])

        # take the parcels selected in _select_offsets and calculate the
        # percent_overlap
        temp_municipalities = os.path.join(hzone_dir,
            'servicesheds_with_offset_parcels.shp')
        per_offset_data = analysis.percent_overlap(
            hzone_paths['selected_offsets'], hzone_paths['servicesheds'],
            temp_municipalities, 'pop_center')
        json.dump(per_offset_data, open(os.path.join(hzone_dev,
            'per_offset_data.json'), 'w'), indent=4, sort_keys=True)
        opal_reporting.write_per_offset_csv(per_offset_data,
            os.path.join(hzone_dir, 'offset_benefits_per_serviceshed.csv'))


        #########################
        # PARCEL RECOMMENDATION #
        #########################
        # parcel data contains information for us to drive the offset value per
        # serviceshed as well.
        parcel_data = offsets.translate_parcel_data(per_offset_data)
        json.dump(parcel_data, open(os.path.join(hzone_dev,
            'translated_parcel_data.json'), 'w'), indent=4, sort_keys=True)

        # 2 of the offset schemes use ES.  If we're using ES, include ES parcel
        # analysis and offset recommendation.
        if args['offset_scheme'] != offsets.OFFSET_SCHEME_BIODIV:
            temp_municipalities_2 = os.path.join(dirs['temp'],
                'municipalities_intersecting_impacts.shp')
            per_impact_data = analysis.percent_overlap(
                hzone_paths['impact_sites'], hzone_paths['servicesheds'],
                temp_municipalities_2, 'pop_center')
            json.dump(per_impact_data, open(os.path.join(hzone_dev,
                'per_impact_data.json'), 'w'), indent=4, sort_keys=True)

            # collect ES impacts from per_impact_data
            es_hydro_requirements = offsets.translate_es_impacts(per_impact_data)
            json.dump(es_hydro_requirements, open(os.path.join(hzone_dev,
                'es_hydro_requirements.json'), 'w'), indent=4, sort_keys=True)

            # group offset parcels by serviceshed and merge them into the
            # es_hydro_requirements
            offset_parcels_by_sshed = offsets.group_offset_parcels_by_sshed(
                per_offset_data)
            empty_services = dict((k, 0) for k in es_hydro_requirements.values()[0])
            for sshed_name, sshed_offsets in offset_parcels_by_sshed.iteritems():
                try:
                    es_hydro_requirements[sshed_name]['parcels'] = sshed_offsets
                except KeyError:
                    # when there are no impacts for this serviceshed (but there are
                    # offsets), then we can skip the serviceshed.
                    continue
            json.dump({'offset_parcels_by_sshed': offset_parcels_by_sshed,
                'es_hydro_requirements': es_hydro_requirements},
                open(os.path.join(hzone_dev,
                'es_hydro_requirements_complete.json'), 'w'), indent=4,
                sort_keys=True)
        else:
            es_hydro_requirements = None

        # biodiversity requirements stored in the `biodiversity_impact`
        # variable.
        # hydro_es_req - this would need to be determined from the
        # per_impact_data
        if 'prop_offset' not in args:
            LOGGER.debug('Defaulting to prop_offset=1.0')
            args['prop_offset'] = 1.0
        recommended_parcels = offsets.select_set_multifactor(parcel_data,
            biodiversity_impact, es_hydro_requirements,
            proportion_offset=args['prop_offset'])
        json.dump(recommended_parcels, open(os.path.join(hzone_dev,
            'recommended_parcels.json'), 'w'), indent=4, sort_keys=True)

        # check to see if the user provided avoidance areas.  If so, check to
        # see if any of the impact sites intersect the provided avoidance
        # areas.
        try:
            impacts_disallowed = analysis.vectors_intersect(
                hzone_paths['impact_sites'], args['avoidance_areas'])
        except KeyError:
            impacts_disallowed = False

        service_mitigation_ratios = {}
        for service in total_impacts.keys():
            mit_ratio_key = '%s_mitigation_ratio' % service
            try:
                mit_ratio = float(args[mit_ratio_key])
            except KeyError:
                mit_ratio = 1.0
            service_mitigation_ratios[service] = mit_ratio

        # We only want to include the AOI in the report if the user actually
        # provided an AOI (so we did not compute it for them), and we're
        # running OPAL.
        include_aoi = True
        if 'area_of_influence_uri' not in args:
            if args['distribution'] == DIST_OPAL:
                include_aoi = False
        LOGGER.debug('Include AOI column: %s', include_aoi)

        # We only want to include the subzones column in the parcels CSV iff
        # there is only 1 subzone for this zone.
        include_subzone = impact_sites_data['name'] in contained_subzones
        LOGGER.debug('Name: %s', impact_sites_data['name'])
        LOGGER.debug('Contained subzones: %s', contained_subzones)
        LOGGER.debug('Include subzone column: %s', include_subzone)

        LOGGER.info("Building output report")
        build_report(hzone_paths['servicesheds'], biodiversity_impact,
            hzone_paths['selected_offsets'],
            args['project_footprint_uri'], total_impacts,
            args['impact_type'], hzone_dir, hzone_paths['impact_sites'],
            'pop_center', '%s_report.html' % _clean_hydrozone_name,
            hzone_paths['all_natural_parcels'], impacts_disallowed,
            suggested_parcels=recommended_parcels,
            custom_es_servicesheds=custom_servicesheds,
            dev_dir = hzone_dev, service_mitrat=service_mitigation_ratios,
            per_offset_data=per_offset_data, prop_offset=args['prop_offset'],
            distribution=args['distribution'], include_aoi_column=include_aoi,
            include_subzone_column=include_subzone,
            hzone_name=impact_sites_data['name'])

        # copy static maps to the workspace.
        LOGGER.info('Clipping static data to the hydrozone for reference')
        for service_name, static_data in protection_services:
            for impact_raster_key in ['static_impact', 'static_protection']:
                src_file = static_data[impact_raster_key]
                dest_filename = os.path.join(hzone_static_maps,
                    '%s_%s.tif' % (service_name, impact_raster_key))
                LOGGER.info('Clipping %s:%s', impact_raster_key, src_file)
                try:
                    static_maps.clip_static_map(src_file, hzone_paths['hydrozone'],
                        dest_filename)
                except Exception as error:
                    LOGGER.error('Could not clip static map: %s', error)


    # return tempfile.tempdir to its original state.
    tempfile.tempdir = old_temp_dir
    shutil.rmtree(dirs['temp'])

    write_results_index(dirs['results'], files['base_report'],
                         distribution=args['distribution'])

def write_results_index(results_dir, out_file, distribution):
    """
    Write an HTML page to the results folder with links to per-zone analyses.

    This HTML page is extremely simple relative to the interactivity contained
    in the analysis pages.  It's just a UL with some helptext, where each LI
    links to the given hydrozones analysis.

    Parameters:
        results_dir (string): A string filepath to the folder containing each
            of the per-hydrozone results directories.
        out_file (string): The path to the file to which the HTML file will be
            written.
        distribution (string): The name of the distribution to write to the
            file.

    Returns:
        None
    """
    zone_glob = os.path.join(results_dir, '*')
    zone_directory_basenames = [os.path.basename(d)
                                for d in glob.glob(zone_glob)
                                if os.path.isdir(d)]
    LOGGER.debug('Zone directory basenames: %s', zone_directory_basenames)

    reporting_config = {
        'title': _('Report'),
        'sortable': False,
        'totals': False,
        'out_uri': out_file,
        'elements': [
            {
                'type': 'head',
                'section': 'head',
                'format': 'style',
                'position': 0,
                'input_type': 'File',
                'data_src': os.path.join(REPORT_DATA, 'table_style.css')
            },
            {
                'type': 'text',
                'section': 'body',
                'input_type': 'text',
                'position': 0,
                'text': (
                    '<h1>{distribution} {title}</h1>'
                    '{help_text}'
                    '<ul>{formatted_hzone_list}</ul>'
                ).format(
                    distribution=distribution.upper(),
                    title=_('Per-Zone Analyses'),
                    help_text=_(
                        'Select a zone to navigate to its impact summary.'
                    ),
                    formatted_hzone_list='\n'.join([
                        '<li><a href="{href}">{text}</li>'.format(
                            href=os.path.join(d, d + '_report.html'),
                            text=d)
                        for d in zone_directory_basenames])
                )
            }
        ]
    }
    reporting.generate_report(reporting_config)

def build_report(municipalities, biodiversity_impact, selected_parcels,
    project_footprint, total_impacts,
    impact_type, output_workspace, impact_sites, pop_col, report_name,
    natural_parcels, impacts_error=False, suggested_parcels=[],
    custom_es_servicesheds=None, dev_dir='_dev', service_mitrat={'carbon': 1.0,
        'nutrient': 1.0, 'sediment': 1.0}, per_offset_data=None,
    prop_offset=1.0, distribution='opal', include_aoi_column=True,
    include_subzone_column=True, hzone_name=''):

    # sort the suggested offset parcels
    suggested_parcels = sorted(suggested_parcels)

    impact_columns = [
        {
            'name': _('Impact footprint shapefile'),
            'total': False,
            'attr':{'class':'round2'}},
    ]

    dev_dir = os.path.join(output_workspace, dev_dir)

    if not os.path.exists(dev_dir):
        os.makedirs(dev_dir)

    # Determine which municipalities the selected polygons overlap with.
    temp_municipalities = os.path.join(output_workspace,
        'servicesheds_with_offset_parcels.shp')
#    per_offset_data = analysis.percent_overlap(selected_parcels,
#        municipalities, temp_municipalities, pop_col)

#    LOGGER.debug('Per-offset data: \n%s',
#        json.dumps(per_offset_data, indent=4, sort_keys=True))
#    json.dump(per_offset_data, open(os.path.join(dev_dir,
#        'per_offset_data.json'), 'w'), indent=4, sort_keys=True)
#    opal_reporting.write_per_offset_csv(per_offset_data,
#            os.path.join(output_workspace, 'offset_benefits_to_servicesheds.csv'))
#    LOGGER.debug('Total impacts: %s', total_impacts)

    biodiversity_data = []
    for ecosystem_name, bio_impact_dict in biodiversity_impact.iteritems():
        try:
            ecosystem_name = unicode(ecosystem_name, 'utf-8')
        except TypeError:
            # happens when trying to decode a unicode string to unicode.
            pass

        ecosystem_impact_dict = {
            _('Ecosystem type'): ecosystem_name,
            _('Total impacted area (ha)'): round(bio_impact_dict['impacted_area'], 2),
            _('Required offset area (ha)'): round(bio_impact_dict['mitigation_area'],
                2),
            _('Mean mitigation ratio'): round(bio_impact_dict['mitigation_ratio'], 2),
            _('No. patches impacted'): bio_impact_dict['patches_impacted'],

            # initialize for the biodiversity impacts table
            _('Area offset (ha)'): 0.0,
            _('Net benefits (ha)'): bio_impact_dict['mitigation_area'] * -1.0,
        }
        biodiversity_data.append(ecosystem_impact_dict)

    # determine whether to skip biodiversity based on the length of the
    # biodiversity impacts dict.
    skip_biodiv = len(biodiversity_impact) == 0
    EMPTY_REPORT_OBJ = lambda : {
        'type': 'text',
        'section': 'body',
        'position': 0,
        'text': '',
    }.copy()
    if not skip_biodiv:
        impacted_parcels_table = opal_reporting.impacted_parcels_table(
            impact_sites, natural_parcels, os.path.join(output_workspace,
            'impacted_natural_ecosystems.csv'))
    else:
        impacted_parcels_table = EMPTY_REPORT_OBJ()

    # get the amount of service required for global services from the
    # impact and the mitigation ratio.
    adjusted_global_impacts = {}
    for service_name, service_impact in total_impacts.iteritems():
        adjusted_impact = service_impact * service_mitrat[service_name]
        adjusted_global_impacts[service_name] = adjusted_impact

    LOGGER.debug('Total impacts before adjustment: %s', total_impacts)
    LOGGER.debug('adjusted_global_impacts: %s', adjusted_global_impacts)
    offset_parcels_table = opal_reporting.build_parcel_table(per_offset_data,
        adjusted_global_impacts.copy(), os.path.join(output_workspace,
        'offset_sites_filtered_table.csv'), distribution, include_aoi_column,
        include_subzone_column, suggested_parcels)

    report_args = {
        'title': _('Report'),
        'sortable': True,
        'totals': True,
        'out_uri': os.path.join(output_workspace, report_name),
        'elements': [
            {
                'type': 'head',
                'section': 'head',
                'format': 'style',
                'position': 0,
                'input_type': 'File',
                'data_src': os.path.join(REPORT_DATA, 'table_style.css')
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'input_type': 'File',
                'data_src': os.path.join(REPORT_DATA, 'permitting_functions.js'),
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'input_type': 'File',
                'data_src': os.path.join(REPORT_DATA, 'toc.min.js'),
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'script',
                'input_type': 'File',
                'data_src': os.path.join(REPORT_DATA, 'table_row_mouseover.js'),
            },
            {  # add in the JSON data necessary for interactive tables
                'type': 'head',
                'section': 'head',
                'format': 'json',
                'data_src': json.dumps(recurse_sigfig(per_offset_data, 3)),
                'input_type': 'Text',
                'attributes': {'id': 'muni-data'},
            },
            {
                'type': 'head',
                'section': 'head',
                'format': 'json',
                'input_type': 'Text',
                'data_src': json.dumps(opal_reporting.get_impact_data(
                    temp_municipalities, impact_sites, pop_col,
                    'pop_size', service_mitrat,
                    os.path.join(dev_dir, 'serviceshed_data.json'))),
                'attributes': {'id': 'impact-data'},
            },
            {
                'type': 'text',
                'section': 'body',
                'input_type': 'text',
                'position': 0,
                'text': '<div id="TOC">%s</div><div id="content">',
            },
            {
                'type': 'text',
                'section': 'body',
                'input_type': 'text',
                'position': 0,
                'text': ('<div class="notice">%s</div>' %_('<b>NOTE:</b> Impact'
                    ' and offset values are <b>unitless</b> unless you have'
                    ' calibrated your static map model runs.')),
            },
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': ''.join([
                    '<h1>{hzone}: {title}</h1>'.format(
                        hzone=hzone_name,
                        title=_('Summary of impacts to ecosystems and '
                                'ecosystem services').encode('utf-8')),
                    '<p>{i18n_impact}: <strong>{imp_type}</strong></p>'.format(
                        i18n_impact=_('Impact type').encode('utf-8'),
                        imp_type=impact_type)
                    ])
            },
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': '<h2>%s</h2>' % _('Total impacts to ecosystem services'),
            },
            opal_reporting.es_impacts_table(total_impacts, service_mitrat),
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': '<h2>%s</h2>' % _('Total impacts to terrestrial ecosystems'),
            } if not skip_biodiv else EMPTY_REPORT_OBJ(),
            {
                'type': 'table',
                'section': 'body',
                'sortable': True,
                'checkbox': False,
                'total': True,
                'data_type': 'dictionary',
                'key': _('Ecosystem type'),
                'columns': [
                    {
                        'name': _('Ecosystem type'),
                        'total': False
                    },
                    {
                        'name': _('No. patches impacted'),
                        'total': True
                    },
                    {
                        'name': _('Mean mitigation ratio'),
                        'total': False,
                        'attr': {'class': 'round2'},
                    },
                    {
                        'name': _('Total impacted area (ha)'),
                        'total': True,
                        'attr': {'class': 'round2'},
                    },
                    {
                        'name': _('Required offset area (ha)'),
                        'total': True,
                        'attr': {'class': 'round2'},
                    },
                ],
                'data': biodiversity_data,
            } if not skip_biodiv else EMPTY_REPORT_OBJ(),
            {
                'type': 'text',
                'section': 'body',
                'position': 0,
                'text': '<h2>%s</h2>' % _('Details of impacts to terrestrial ecosystems'),
            } if not skip_biodiv else EMPTY_REPORT_OBJ(),
            impacted_parcels_table,
            {
                'type': 'text',
                'section': 'body',
                #'position': 0,
                'text': '<div><h1>%s</h1>' % _('Offset patches and mitigation potential'),
            },
            {
                'type': 'text',
                'section': 'body',
                #'position': 0,
                'text': (
                    '<h2>{title}</h2>{export_csv}<br/><br/>'
                    '{all_offsets_title}: <b>{offsets_link}</b>'
                    '<br/>').format(
                        title=_('Possible offset patches').encode('utf-8'),
                        export_csv=('<a href="#" '
                                    'class="export">Export CSV</a>'),
                        all_offsets_title=_('GIS vector with all selected '
                                            'offset patches').encode('utf-8'),
                        offsets_link=os.path.relpath(
                            selected_parcels,
                            os.path.join(output_workspace, '..', '..')))
            },
            {
                'type': 'text',
                'section': 'body',
                #'position': 0,
                'text': '<b>%s: %s</b><br/>%s<br/>' % (_('Suggested offset parcels').encode('utf-8'),
                    suggested_parcels,
                    (_('Suggested parcels account for %sx impacts x mitigation ratio') % prop_offset).encode('utf-8'))
            },
            offset_parcels_table,
            {
                'type': 'text',
                'section': 'body',
                #'position': 0,
                'text': '</div><div><h1>%s</h1>' % _('Net benefits to ecosystems and ecosystem services'),
            },
            {
                'type': 'text',
                'section': 'body',
                'text': '<h2>%s</h2>' % _('Benefits to terrestrial ecosystems'),
            } if not skip_biodiv else EMPTY_REPORT_OBJ(),
            {
                'type': 'table',
                'section': 'body',
                'sortable': True,
                'total': False,
                'attributes': {'id': 'bio_table'},
                'data_type': 'dictionary',
                'key': _('Ecosystem type'),
                'columns': [
                    {
                        'name': _('Ecosystem type'),
                        'total': False
                    },
                    {
                        'name': _('Total impacted area (ha)'),
                        'total': True
                    },
                    {
                        'name': _('Required offset area (ha)'),
                        'total': False,
                        'attr': {'class': 'required_offset round2'}
                    },
                    {
                        'name': _('Area offset (ha)'),
                        'total': False,
                        'attr': {'class': 'area_offset round2'}
                    },
                    {
                        'name': _('Net benefits (ha)'),
                        'total': False,
                        'attr': {'class': 'net round2'}
                    },
                ],
                'data': biodiversity_data,
            } if not skip_biodiv else EMPTY_REPORT_OBJ(),
            {
                'type': 'text',
                'section': 'body',
                'text': '<h2>%s</h2>' % _('Ecosystem service benefits'),
            },
            {
                'type': 'text',
                'section': 'body',
                'input_type': 'text',
                'position': 0,
                'text': ('<div id="metadata">'
                         'OPAL {opal_version}<br/>'
                         '{timestamp}<br/>'
                         '</div>').format(
                             opal_version=natcap.opal.__version__,
                             timestamp=time.strftime('%Y-%m-%d %H:%M:%S'))
            },
            {
                'type': 'text',
                'section': 'body',
                'text': '</div></div>',
            },
        ]
    }
    if True in map(lambda x: x in total_impacts.keys(), ['sediment',
        'nutrient']) or custom_es_servicesheds == 'hydrological':
        LOGGER.debug('Including the hydrological table')
        hydro_services = []
        for possible_hydro_service in ['sediment', 'nutrient']:
            if possible_hydro_service in total_impacts.keys():
                hydro_services.append(possible_hydro_service)
        if custom_es_servicesheds == 'hydrological':
            hydro_services.append('custom')
        hydrological_table =  opal_reporting.es_benefits_table(hydro_services)
        report_args['elements'].insert(-2, hydrological_table)

    if 'carbon' in total_impacts or custom_es_servicesheds == 'global':
        LOGGER.debug('Including the global table')
        global_table = opal_reporting.global_benefits_table(
            custom_es_servicesheds == 'global', adjusted_global_impacts)
        report_args['elements'].insert(-2, global_table)

    # If the user's impact sites intersect an avoidance area, then insert a
    # warning into the HTML report.
    if impacts_error == True:
        warning = {
            'type': 'text',
            'section': 'body',
            'input_type': 'text',
            'position': 0,
            'text': ('<div class="warning">%s</div>' %_('WARNING: Impact sites'
                ' intersect an avoidance area')),
        }

        # insert the warning just after the impact site summary label.
        report_args['elements'].insert(5, warning)

    reporting.generate_report(report_args)

def write_vector(in_vector_uri, feature_indices, out_vector_uri,
        include_fields=None, new_fields=None, new_values=None, field_types={}):
    in_vector = ogr.Open(in_vector_uri)
    in_layer = in_vector.GetLayer()
    in_layer_srs = in_layer.GetSpatialRef()
    in_layer_defn = in_layer.GetLayerDefn()

    if os.path.exists(out_vector_uri):
        LOGGER.warning('%s already exists on disk', out_vector_uri)
        preprocessing.rm_shapefile(out_vector_uri)

    LOGGER.debug('Creating a new vector at %s', out_vector_uri)
    LOGGER.debug('Out vector type: %s', type(out_vector_uri))
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = out_driver.CreateDataSource(out_vector_uri)

    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    out_layer = out_vector.CreateLayer(layer_name, srs=in_layer_srs)

    # map the old index to the new index.
    field_indices = {}
    if include_fields is None:
        LOGGER.debug('No fields will be copied')
        include_fields = []

    if include_fields is 'all':
        LOGGER.debug('All fields will be copied')
        field_names = []
        for index in range(in_layer_defn.GetFieldCount()):
            field_defn = in_layer_defn.GetFieldDefn(index)
            field_names.append(field_defn.GetName())
        include_fields = field_names

    LOGGER.debug('Copying fields %s', include_fields)
    for old_field in include_fields:
        old_field_index =  in_layer_defn.GetFieldIndex(old_field)
        old_field_defn = in_layer_defn.GetFieldDefn(old_field_index)

        # create a new field in the output layer based on the old field
        # definition
        out_layer.CreateField(old_field_defn)
        out_layer_defn = out_layer.GetLayerDefn()
        new_field_index = out_layer_defn.GetFieldIndex(old_field)
        field_indices[old_field_index] = new_field_index

    # assume new_fields is a list of fieldnames, and all new fields are floats.
    if new_fields is not None:
        LOGGER.debug('Creating new fields %s', new_fields)
        for fieldname in new_fields:
            try:
                field_type = field_types[fieldname]
            except KeyError:
                field_type = ogr.OFTReal
            field_defn = ogr.FieldDefn(fieldname, field_type)
            out_layer.CreateField(field_defn)

    layer_schema = map(lambda d: d.GetName(), out_layer.schema)

    index_map = {}
    for feature_index in feature_indices:
        old_feature = in_layer.GetFeature(feature_index)
        new_feature = ogr.Feature(out_layer_defn)
        new_feature.SetGeometry(old_feature.GetGeometryRef())

        for old_index, new_index in field_indices.iteritems():
            old_value = old_feature.GetField(old_index)
            new_feature.SetField(new_index, old_value)

            if new_values is not None:
                for fieldname, value in new_values[feature_index].iteritems():
                    if fieldname not in layer_schema:
                        continue

                    new_feature.SetField(fieldname, value)

        out_layer.CreateFeature(new_feature)

        index_map[feature_index] = new_feature.GetFID()

    return index_map


def recurse_sigfig(per_offset_data, num_digits):
    """
    Recurse through a dictionary of offset data.  Any impacts to ecosystem
    services will be rounded to `num_digits` significant figures.

    Parameters:
        per_offset_data(dict): A dictionary of values, mapping string parcel
            IDs to dictionaries of values, including keys with service names.
        num_digits(int): The number of digits to round to.

    Returns:
        A dictionary of the same structure as `per_offset_data`.
    """

    service_names = set([_('Sediment'), _('Nitrogen'), _('Carbon'),
                         _('Custom')])

    def _recurse(iterable, key=None):
        if isinstance(iterable, dict):
            return_iterable = {}
            for key, value in iterable.iteritems():
                return_iterable[key] = _recurse(value, key=key)
            return return_iterable
        elif isinstance(iterable, list):
            return [_recurse(item) for item in iterable]
        else:
            if key in service_names:
                return opal_reporting.sigfig(iterable, num_digits)
            else:
                return iterable

    return _recurse(per_offset_data)
