"""A module for the generation of report-related functions."""
import codecs
import csv
import json
import logging
import os
import tempfile
from types import FloatType
from types import IntType
from types import StringType
from types import UnicodeType

from osgeo import ogr
import shapely.geos
import shapely.validation

import adept_core
import natcap.opal.i18n
import offsets
import preprocessing
import utils

LOGGER = logging.getLogger('natcap.opal.reporting')
_ = natcap.opal.i18n.language.ugettext

def sigfig(number, places):
    """
    Round `number` to `places` significant digits.

    Parameters:
        number (int or float): A number to round.
        places (int): The number of places to round to.

    Returns:
        A number
    """

    # Passing a negative int to round() gives us a sigfig determination.
    # Example: round(12345, -2) = 12300
    ndigits = -int(len(str(abs(number)).split('.')[0]) - places)
    return round(number, ndigits)

def _recode(string):
    """Re-encode an input string as UTF-8 if it isn't already encoded.  If
    the input value is not a string, return the value as-is."""
    if type(string) is StringType:
        return string.decode('utf-8')
    elif type(string) is UnicodeType:
        return string.encode('utf-8')
    return string

def get_impact_data(municipalities_vector, impacts_vector, name_col, pop_col,
        service_mitrat, out_json_file=None):
    """Calculate per-impact information as it relates to municipalities.

        municipalities_vector - a URI to an OGR vector
        impacts_vector - a URI to an OGR vector
        name_col - a field name in the municipalities vector that contains the
            polygon name
        pop_col - a field name in the municipalities vector containing an
            integer representing the population of the polygon.
        service_mitrat - a python list of strings containing services to consider.
        out_json_file=None - a URI to where an output json file with this data
            should be written.
"""

    utils.assert_files_exist([municipalities_vector, impacts_vector])

    LOGGER.debug('Opening municipalities vector %s', municipalities_vector)
    muni_vector = ogr.Open(municipalities_vector)
    muni_layer = muni_vector.GetLayer()

    LOGGER.debug('Opening impacts vector: %s', impacts_vector)
    impact_index, impact_dict = preprocessing.build_spatial_index(impacts_vector)
    impacts_vector = ogr.Open(impacts_vector)
    impacts_layer = impacts_vector.GetLayer()

    services = service_mitrat.keys()
    LOGGER.debug('Considering services %s', services)

    # preprocess impacts so we don't have to retrieve information repeatedly
    # later on.
    impact_features = {}
    for impact_feature in impacts_layer:
        impact_fid = impact_feature.GetFID()
        service_dict = {}

        for service_name in services:
            impact = impact_feature.GetField(service_name)
            if impact is None:
                LOGGER.debug('Impact %s has %s impact of None', impact_fid,
                    service_name)
                impact = 0.0
            service_dict[service_name] = sigfig(impact, 3)
        impact_features[impact_fid] = service_dict
    impacts_layer.ResetReading()

    per_muni_data = {}

    for muni_feature in muni_layer:
        muni_fid = muni_feature.GetFID()
        muni_geom = muni_feature.GetGeometryRef()
        LOGGER.debug('Processing municipality %s', muni_fid)
        muni_name = muni_feature.GetField(name_col)
        muni_population = muni_feature.GetField(pop_col)

        try:
            muni_polygon = offsets.build_shapely_polygon(muni_feature)
        except shapely.geos.ReadingError:
            LOGGER.debug('Muni %s (%s) has invalid geometry: "%s". Skipping',
                muni_fid, muni_name, shapely.validation.explain_validity())
            continue


        muni_data = {
            'pop': muni_population,
        }

        impacts = {}
        template = '%s impact'
        for service in services:
            if service == 'nutrient':
                service = 'nitrogen'
            impacts[template % service.capitalize()] = 0.0

        num_impacts = 0
        skipped_impacts = []
        for impact_fid in impact_index.intersection(muni_polygon.bounds):
            if sum(impact_features[impact_fid].values()) == 0:
                skipped_impacts.append(impact_fid)
                continue

            impact_feature = impacts_layer.GetFeature(impact_fid)
            impact_geom = impact_feature.GetGeometryRef()

            # get the intersection geometry and area.
            # if the area is 0, we know that there's no intersection.
            intersection = impact_geom.Intersection(muni_geom)
            intersection_area = intersection.Area()

            if intersection_area > 0:
                num_impacts += 1
                # Find the proportion of the impact site that is in this
                # municipality.
                prop_area = intersection_area / impact_geom.Area()

                impact_data = impact_features[impact_fid]

                for service in services:
                    if service == 'nutrient':
                        label = 'Nitrogen'
                    else:
                        label = service.capitalize()
                    impact_amt = impact_data[service] * prop_area
                    mit_ratio = service_mitrat[service]
                    impacts[template % label] += impact_amt * mit_ratio

        if len(skipped_impacts) > 0:
            LOGGER.debug('%s impact sites had not impacts and were skipped: %s',
                len(skipped_impacts), skipped_impacts)
        impacts_layer.ResetReading()

        # If at least one of the service impacts is not 0.0 (the default), then
        # we want to initialize the impacts.
        if True in map(lambda x: x != 0.0, impacts.values()):
            muni_data['impacts'] = impacts
        per_muni_data[muni_name] = muni_data
    muni_layer.ResetReading()

    LOGGER.debug('Per-municipality impacts: %s', json.dumps(per_muni_data,
        sort_keys=True, indent=4))

    if out_json_file is not None:
        LOGGER.debug('Saving per-muni data to %s', out_json_file)
        json.dump(per_muni_data, open(out_json_file, 'w'), sort_keys=True,
            indent=4)

    return per_muni_data

def build_parcel_table(per_offset_data, total_impacts, out_csv,
        dist=None, include_aoi_column=True, include_subzone_column=True,
        suggested_parcels=[]):
    """Build up a list of dictionaries with the following attributes per row:
        row['Sediment'] - sediment load offset by parcel
        row['distance (km)'] - shortest distance between offset site and the
            closest impact site
        row['Area (ha)'] - the area of the offset site (in ha)
        row['Ecosystem type'] - a string containing the ecosystem name
        row['Nitrogen'] - nitrogen load offset by parcel
        row['Carbon'] - Carbon offset by the parcel
        row['% Impact (Sediment)'] - the % of total sediment impact offset by
            the parcel
        row['% Impact (Nitrogen)'] - the % of total nutrient impact offset by
            the parcel
        row['% Impact (Carbon)'] - the % of total carbon impact offset by
            the parcel
        row['parcel_id'] - the parcel ID of the offset parcel.
        row['Richness'] - the Richness score (if it's provided)
        row['Threat'] - the threat score (if it's provided)

        Parameters:
        per_offset_data - a python dictionary where the key is the parcel ID of
        the offset parcel in question, and the value is a dictionary with the
        following attributes:
            'Sediment' - the sediment load offset by the parcel
            'Distance' - the minimum distance (in m) from the offset site to
                the closest impact site.
            'Area' - the area of the offset parcel (in square m)
            'Ecosystem' - the full name of the ecosystem type of the offset
                parcel
            'Nitrogen' - the amount of Nitrogen load offset by the parcel
            'Carbon' - the amount of carbon offset by the parcel

        total_impacts - a python dictionary with the following values:
            'sediment' - a float, the total sediment impact
            'nutrient' - a float, the total nitrogen impact
            'carbon' - a float, the total carbon impact.
            'custom' - (optional) a float, the total custom ES impact.
        out_csv - the file to which the parcel table information should be
        saved.
        dist - a string, either natcap.opal.adept_core.DIST_OPAL or
            natcap.opal.adept_core.DIST_MAFE.  Changes the rendering of a
            cuople strings.
        include_aoi_column=True - Boolean.  Indicate whether to include the AOI
        column in the output tables.
        include_subzone_column=True (Boolean): Indicate whether to include the
        subzone column in the output table.
        suggested_parcels=[] (List of integers): integer feature indices indicate which
        parcels are recommended.  These parcel rows will have a 1 or 0 in them
        indicating whether they are required.

        Writes a dictionary to the URI at out_csv.
"""
    LOGGER.debug('Total impacts: %s', total_impacts)

    if dist is None:
        dist = adept_core.DIST_OPAL

    def percent(num, denom):
        """Calculate num/denom as a percentage between 0 and 100.
            num - some number.
            denom - some number.  If denom is 0, it will be converted to 1 to
                avoide a ZeroDivisionError.

            Returns a number."""
        if denom == 0:
            denom = 1.0

        # if the denominator (impact) is positive, no offsets are needed, so
        # the percentage returned should be 0.0
        if denom > 0:
            return 0.0
        elif num < 0.0 and denom < 0.0:
            # if BOTH the denominator (impact) AND the numerator (offset) are
            # negative, the returned percentage should be negative.
            num = float(num) * -1
            return num / denom * 100.0
        else:
            # If none of these special cases are met, return the absolute value
            # of the actual percentage.
            return abs(float(num) / denom) * 100

    fieldname_map = {
        'parcel_id': _('Potential offset patch ID code'),
        'ecosystem_type': _('Ecosystem type'),
        'sediment': _('Sediment retention offset'),
        'nitrogen': _('Nitrogen retention offset'),
        'carbon': _('Carbon storage offset'),
        '%_impact_sed': _('Percent of total impact offset (sediment)'),
        '%_impact_nut': _('Percent of total impact offset (nitrogen)'),
        '%_impact_car': _('Percent of total impact offset (carbon)'),
        'distance': _('Distance from impact site (km)'),
        'area': _('Total patch area (ha)'),
        'custom': _('Custom ecosystem service offset'),
        '%_impact_custom': _('Percent of total impact offset (custom ES)'),
        'lci': _('Landscape context index (LCI)'),
        'recommended': _('Suggested offset parcel'),
    }

    fieldnames = [
        fieldname_map['parcel_id'],
        fieldname_map['ecosystem_type'],
        fieldname_map['distance'],
        fieldname_map['area'],
    ]

    services = total_impacts.keys()[:]  # make a copy
    if 'custom' in services:
        services.remove('custom')

    num_services = 0
    for service_name in services:
        if service_name == 'nutrient':
            service_key = 'nitrogen'
        else:
            service_key = service_name
        field_name = fieldname_map[service_key]
        field_percent = fieldname_map['%s_impact_%s' % ('%',
            service_name[0:3].lower())]
        fieldnames.insert(2 + num_services, field_name)
        fieldnames.insert(3 + (2 * num_services), field_percent)
        num_services += 1

    # mapping parcel_data keys to column names.
    # If the parcel_data keys are present, they should be included in the
    # offset row.
    fields_to_check = {
        'City': _('Soft Boundary 3'),
        'Avoidance Areas': _('Avoidance Areas'),
        'Conservation Portfolio': _('Conservation Portfolio'),
        'Richness': _('Richness'),
        'Threat': _('Threat'),
        'Lci': fieldname_map['lci'],
    }

    if include_aoi_column:
        fields_to_check['Aoi'] = _('Soft Boundary 2')

    if include_subzone_column:
        fields_to_check['Subzone'] = _('Soft Boundary 1')

    # Assume we're running OPAL unless we specify otherwise.
    if dist == adept_core.DIST_MAFE:
        fields_to_check['Subzone'] = _('Hydrographic sub-zone')
        fields_to_check['Aoi'] = _('AOI (area of influence)')
        fields_to_check['City'] = _('Municipality')

    first_offset = per_offset_data.items()[0][1]  # 2nd item of 1st tuple in list
    LOGGER.debug('Checking for additional fields in  %s', first_offset)
    fields_to_copy = []
    for json_fieldname, csv_fieldname in fields_to_check.iteritems():
        if json_fieldname in first_offset:
            fieldnames.append(csv_fieldname)
            fields_to_copy.append((json_fieldname, csv_fieldname))

    # If we're also considering custom ecosystem services, add the correct
    # fields to the fieldnames list
    if 'Custom' in first_offset:
        fieldnames.insert(2 + len(services), fieldname_map['custom']) #5
        fieldnames.insert(3 + (2 * len(services)), fieldname_map['%_impact_custom']) #9

    LOGGER.debug('Also including fields (json, csv) %s', fields_to_copy)
    LOGGER.debug('Fieldnames: %s', fieldnames)

    suggested_parcels_set = set(suggested_parcels)
    rows = []
    for parcel_id, parcel_data in per_offset_data.iteritems():
        LOGGER.debug('parcel_data %s', parcel_data)

        data = {
            fieldname_map['distance']: sigfig(parcel_data['Distance'] / 1000.0, 3),
            fieldname_map['area']: parcel_data['Area'] / 10000.0,
            fieldname_map['ecosystem_type']: _recode(parcel_data['Ecosystem']),
            fieldname_map['parcel_id']: parcel_id,
            fieldname_map['recommended']: int(parcel_id in suggested_parcels_set),
        }
        for es_key in ['Sediment', 'Nitrogen', 'Carbon', 'Custom']:
            if es_key not in parcel_data:
                LOGGER.debug('key %s not in parcel_data', es_key)
                continue

            fieldname_key = es_key.lower()
            if es_key == 'Custom':
                shortened_name = es_key.lower()
            else:
                if es_key == 'Nitrogen':
                    shortened_name = 'nut'
                else:
                    shortened_name = es_key[0:3].lower()
            percent_key = '%s_impact_%s' % ('%', shortened_name)
            data[fieldname_map[fieldname_key]] = sigfig(parcel_data[es_key], 3)

            if fieldname_key == 'nitrogen':
                fieldname_key = 'nutrient'
            data[fieldname_map[percent_key]] = percent(parcel_data[es_key],
                total_impacts[fieldname_key])

        for key in [_('Threat'), _('Richness')]:
            try:
                data[key] = parcel_data[key]
            except KeyError:
                pass

        # copy over fields that we now know to exist.
        for json_field, csv_field in fields_to_copy:
            data[csv_field] = sigfig(parcel_data[json_field], 3)

        rows.append(data)

    utils.write_csv(out_csv, fieldnames, rows)

    columns = [
        {'name': fieldname_map['parcel_id'], 'total': False,
            'attr': {'class': 'parcel_id'}},
        {'name': fieldname_map['recommended'], 'total': False,
            'attr': {'class': 'tdcenter'}},
        {'name': fieldname_map['sediment'], 'total': True,
            'attr': {'class': 'round2'}} if 'sediment' in services else None,
        {'name': fieldname_map['nitrogen'], 'total': True,
            'attr': {'class': 'round2'}} if 'nutrient' in services else None,
        {'name': fieldname_map['carbon'], 'total': True,
            'attr': {'class': _('Carbon').lower() + ' round2'}} if 'carbon' in services else None,
        {'name': fieldname_map['%_impact_sed'], 'total': True,
            'attr': {'class': 'round2'}} if 'sediment' in services else None,
        {'name': fieldname_map['%_impact_nut'], 'total': True,
            'attr': {'class': 'round2'}} if 'nutrient' in services else None,
        {'name': fieldname_map['%_impact_car'], 'total': True,
            'attr': {'class': 'round2'}} if 'carbon' in services else None,
        {'name': fieldname_map['area'], 'total': True,
            'attr': {'class': 'area round2'}},
        {'name': fieldname_map['ecosystem_type'], 'total': False,
            'attr': {'class': 'eco_type'}},
        {'name': fieldname_map['distance'], 'total': False,
            'attr': {'class': 'round2'}},
    ]
    new_columns = []
    for col in columns:
        if col is None:
            continue
        new_columns.append(col)
    columns = new_columns

    if 'Custom' in first_offset:
        columns.insert(4, {'name': fieldname_map['custom'],
            'total': True, 'attr': {'class': _('Custom').lower() + ' round2'}})
        columns.insert(8, {'name': fieldname_map['%_impact_custom'],
            'total': True, 'attr': {'class': 'round2'}})

    # some fields should be ints.  If the current field isn't one of these
    # fields, it should be rounded to 2 digits.
    fields = [fields_to_check['Subzone'], fields_to_check['City']]
    if 'Aoi' in fields_to_check:
        fields.insert(0, fields_to_check['Aoi'])

    for json_field, csv_field in fields_to_copy:
        if csv_field in fields:
            round_digit = '0'
            center_class = 'tdcenter'
        else:
            round_digit = '2'
            center_class = ''

        column_data = {
            'name': csv_field,
            'total': False,
            'attr': {'class': 'round%s %s' % (round_digit, center_class)},
        }
        columns.append(column_data)

    reporting_config = {
        'type': 'table',
        'section': 'body',
        'sortable': True,
        'checkbox': True,
        'totals': True,
        'attributes': {'id': 'parcel_table'},
        'data_type': 'dictionary',
        'columns': columns,
        'key': fieldname_map['parcel_id'],
        'data': rows,
    }
    return reporting_config

def impacted_parcels_table(impact_sites, natural_parcels, csv_uri):
    """Determine which natural parcels have been impacted and build a
    reporting table based on the results.

        impact_sites - a URI to an OGR vector with impact sites
        natural_parcels - a URI to an OGR vector with natural parcels.
            Must have vegetation type and LCI, but may also have Threat and
            Richness columns.  If threat and richness are provided, they will
            be included in the resulting table.
        csv_uri - a URI to an output CSV.

    Returns a reporting args dictionary with appropriate data."""

    # create a temp folder
    # build column names
    # locate intersecting natural polygons, saving them to the temp dir.
    # for natural polygon in intersecting polygons,
    #    build up a row with relevant data from the current natural polygon
    # remove the temp folder.
    # Write the row/column data to a CSV
    # return an appropriate dictionary for reporting.

    utils.assert_files_exist([impact_sites])

    temp_dir = tempfile.mkdtemp()

    impacted_natural_parcels = os.path.join(temp_dir, 'impact_parcels.shp')
    preprocessing.locate_intersecting_polygons(natural_parcels, impact_sites,
        impacted_natural_parcels)

    parcels_vector = ogr.Open(impacted_natural_parcels)
    parcels_layer = parcels_vector.GetLayer()

    layer_fields = map(lambda f: f.GetName(), parcels_layer.schema)
    LOGGER.debug('Found fields %s', layer_fields)

    field_functions = {
        _('Impacted patch code'): lambda p: p.GetFID(),
        _('Ecosystem type'): lambda p: p.GetField('ecosystem'),
        _('Mitigation ratio'): lambda p: p.GetField('mit_ratio'),
    }

    if 'LCI' in layer_fields:
        field_functions[_('Landscape Context Index (LCI)')] = lambda p: round(
            p.GetField('LCI'), 2)

    if 'Richness' in layer_fields:
        field_functions['Richness score'] = lambda p: round(
            p.GetField('Richness'), 2)

    if 'Threat' in layer_fields:
        field_functions['Threat score'] = lambda p: round(p.GetField('Threat'),
            2)

    LOGGER.debug('Buliding up shapely impact geometries')
    # build up a list of prepared shapely geometries for fast intersections.
    impacts_vector = ogr.Open(impact_sites)
    impacts_layer = impacts_vector.GetLayer()
    shapely_impacts = [offsets.build_shapely_polygon(f) for f in impacts_layer]

    rows = []
    for natural_parcel in parcels_layer:
        # get the columns we know exist, based on our earlier tests
        row_data = {}
        for label, value_func in field_functions.iteritems():
            _data_value = value_func(natural_parcel)
            row_data[label] = _recode(_data_value)

        # now, add in the impacted area.  This is the sum of (area of the
        # intersection of each impact geometry with the natural parcel).
        offset_polygon = offsets.build_shapely_polygon(natural_parcel)
        prep_offset_polygon = shapely.prepared.prep(offset_polygon)
        intersection_area = 0.0
        for impact_polygon in shapely_impacts:
            if prep_offset_polygon.intersects(impact_polygon):
                intersection_area += offset_polygon.intersection(impact_polygon).area

        # convert from m^2 to ha.
        intersection_area /= 10000.0

        row_data[_('Patch area impacted (ha)')] = sigfig(round(intersection_area, 2), 3)
        row_data[_('Required offset area (ha)')] = sigfig(round(intersection_area *
            natural_parcel.GetField('mit_ratio'), 2), 3)

        rows.append(row_data)

    # order the fieldnames
    fieldnames = [
        _('Impacted patch code'),
        _('Patch area impacted (ha)'),
        _('Mitigation ratio'),
        _('Required offset area (ha)'),
        _('Ecosystem type'),
    ]
    if 'LCI' in layer_fields:
        fieldnames.insert(1, _('Landscape Context Index (LCI)'))

    for key in field_functions.keys():
        if key not in fieldnames:
            fieldnames.insert(-1, key)

    utils.write_csv(csv_uri, fieldnames, rows)

    # start off the html columns by getting the names
    html_columns = [{'name': c, 'total': False} for c in fieldnames]

    reporting_dict = {
        'type': 'table',
        'section': 'body',
        'sortable': True,
        'checkbox': False,
        'total': False,
        'data_type': 'dictionary',
        'key': 'FID',
        'columns': html_columns,
        'data': rows,
    }
    return reporting_dict

def es_benefits_table(services):
    """Generate a reporting dictionary for the Ecosystem Services Benefits
    table (formerly called the "municipaities table").

        services - a list of services, a combination of 'sediment',
            'nutrient', and/or 'custom' (case-sensitive)

    returns a reporting table configuration dictionary."""

    do_nutrient = 'nutrient' in services
    do_sediment = 'sediment' in services
    do_custom = 'custom' in services

    columns = [
        {
            'name': _('Population center'),
            'attr': {'class': 'services_pop_name'},
            'total':False
        },
        {
            'name': _('Population size'),
            'attr': {'class': 'services_pop_count'},
            'total': False
        },
        {
            'name': _('Sediment impact'),
            'total': False,
            'attr': {'class':'services_impact_sediment impacts round2'}
        } if do_sediment else None,
        {
            'name': _('Nitrogen impact'),
            'total': False,
            'attr':{'class':'services_impact_nitrogen impacts round2'}
        } if do_nutrient else None,
        {
            'name': _('Custom impact'),
            'total': True,
            'attr': {'class': 'services_impact_custom impacts round2'}
        } if do_custom else None,
        {
            'name': _('Sediment offset'),
            'total': False,
            'attr':{'class':'services_offset_sediment offsets round2'}
        } if do_sediment else None,
        {
            'name': _('Nitrogen offset'),
            'total': False,
            'attr':{'class':'services_offset_nitrogen offsets round2'}
        } if do_nutrient else None,
        {
            'name': _('Custom offset'),
            'total': True,
            'attr': {'class': 'services_offset_custom offsets round2'}
        } if do_custom else None,
        {
            'name': _('Net sediment retention benefits'),
            'total': False,
            'attr':{'class':'services_net_sediment net round2'}
        } if do_sediment else None,
        {
            'name': _('Net nitrogen retention benefits'),
            'total': False,
            'attr':{'class':'services_net_nitrogen net round2'}
        } if do_nutrient else None,
        {
            'name': _('Net custom ES benefits'),
            'total': True,
            'attr': {'class': 'services_net_custom net round2'}
        } if do_custom else None,
        {
            'name': _('Net sediment x population'),
            'total': False,
            'attr': {'class': 'services_netadj_sediment population round2'}
        } if do_sediment else None,
        {
            'name': _('Net nitrogen x population'),
            'total': False,
            'attr': {'class': 'services_netadj_nitrogen population round2'}
        } if do_nutrient else None,
        {
            'name': _('Net custom ES x population'),
            'total': False,
            'attr': {'class': 'services_netadj_custom population round2'}
        } if do_custom else None
    ]

    # build a list of columns based on whether those columns should be included
    # Column value is None if we should not.
    included_columns = []
    for possible_column in columns:
        if possible_column is not None:
            included_columns.append(possible_column)

    report_dict = {
        'type': 'table',
        'section': 'body',
        'sortable': False,
        'checkbox': False,
        'total': False,
        'attributes': {'id': 'muni_table'},
        'data_type': 'dictionary',
        'columns': included_columns,
        'data': [],
        'key': 'pop_group',
    }

    return report_dict

def global_benefits_table(add_custom, total_impacts):
    """Build the global benefits table, adding in custom ES columns if
    indicated.

    add_custom - a boolean indicating whether to add custom ES columns.
    total_impacts - a python dictionary containing at least these entries:
        'carbon' - (required) a float.
        'custom' - (required if add_custom is True) a float.

    Returns an invest_natcap.reporting compatible table dictionary.
    """

    benefits_table = {
        'type': 'table',
        'section': 'body',
        'sortable': True,
        'total': False,
        'attributes': {'id': 'global_benefits_table'},
        'data_type': 'dictionary',
        'key': _('Carbon impact'),
        'columns': [
            {
                'name': _('Service type'),
                'total': False,
                'attr': {'class': 'service_name'}
            },
            {
                'name': _('Impacts to service'),
                'total': True,
                'attr': {'class': 'impact round2'}
            },
            {
                'name': _('Selected offset'),
                'total': False,
                'attr': {'class': 'required_offset round2'}
            },
            {
                'name': _('Net service'),
                'total': False,
                'attr': {'class': 'net round2'}
            },
        ],
        'data': []
    }
    if 'carbon' in total_impacts:
        benefits_table['data'].append(
            {
                _('Service type'): _('Carbon'),
                _('Impacts to service'): sigfig(total_impacts['carbon'], 3),
                _('Selected offset'): 0.0,
                _('Net service'): sigfig(total_impacts['carbon'], 3),
            }
        )

    if add_custom is True:
        benefits_table['data'].append({
            _('Service type'): _('Custom'),
            _('Impacts to service'): sigfig(total_impacts['custom'], 3),
            _('Selected offset'): 0.0,
            _('Net service'): sigfig(0.0 - total_impacts['custom'], 3)
        })

    return benefits_table

def write_per_offset_csv(per_offset_data, out_csv):
    """Create a CSV documenting the benefits of each hydrological service
    granted to each serviceshed.

    per_offset_data - a dictionary with integer keys (representing a parcel ID)
        mapping to dictionaries of values containing at least the following
        entries:
            "Nitrogen" - a float (the nitrogen offset of this parcel)
            "Sediment" - a float (the sediment offset of this parcel)
            "municipalities" - a dictionary, with string keys indicating the
                names of affected servicesheds and values being a float between
                0.0 and 1.0.
    out_csv - a URI to where the csv should be saved."""

    if len(per_offset_data) == 0:
        LOGGER.debug('No offset parcels to calculate with.  Returning')
        return


    csv_file = codecs.open(out_csv, 'w', 'utf-8')
    def _write(row_data):
        row_string = ','.join(row_data)
        csv_file.write(row_string + '\n')

    fieldnames = ['Offset parcel ID', 'Serviceshed name']

    # check which services are included so we known which columns to use
    known_services = []
    sample_offset = per_offset_data.values()[0]
    for fieldname in ['Sediment', 'Nitrogen', 'Custom']:
        if fieldname in sample_offset:
            fieldnames.append(fieldname)
            known_services.append(fieldname)
    _write(fieldnames)

    for parcel_key, parcel_data in per_offset_data.iteritems():
        servicesheds = parcel_data['municipalities']
        for serviceshed_name, percent_overlap in servicesheds.iteritems():

            row_data = [parcel_key, serviceshed_name]
            for service_name in known_services:
                service_amt = percent_overlap * parcel_data[service_name]
                row_data.append(sigfig(service_amt, 3))

            def _smart_cast(string):
                """Cast to UTF-8 if the string is not already UTF-8"""
                if type(string) in [IntType, FloatType]:
                    return str(string)

                if type(string) is not UnicodeType:
                    return unicode(string, 'utf-8')
                return string

            _write(map(_smart_cast, row_data))

    csv_file.close()

def es_impacts_table(service_impacts, service_mitrat):
    """Create the ES impacts table for the report.

    service_impacts - a python dict mapping service names (any of 'carbon',
        'nutrient', 'sediment', or 'custom') to numeric service impact
        quantities.
    service_mitrat - a python dict mapping service names (any of those
        mentioned for the service_impacts input) to numeric service mitigation
        ratios.

    Returns a reporting-compatible dictionary representing the table"""

    table_strings = {
        'service_name': _('Service name'),
        'service_impact': _('Impact to service'),
        'mit_ratio': _('Mitigation ratio'),
        'required_offset': _('Required offset value'),
        'carbon': _('Carbon'),
        'nutrient': _('Nutrient'),
        'sediment': _('Sediment'),
        'custom': _('Custom ecosystem service'),
    }

    table_columns = [
        {
            'name': table_strings['service_name'],
            'total': False,
        },
        {
            'name': table_strings['service_impact'],
            'total': False,
            'attr': {'class': 'round2'},
        },
        {
            'name': table_strings['mit_ratio'],
            'total': False,
            'attr': {'class': 'round2'},
        },
        {
            'name': table_strings['required_offset'],
            'total': False,
            'attr': {'class': 'round2'},
        },
    ]

    def _calc_req_offset(service_impact, mit_ratio):
        if service_impact > 0:
            return 0.0
        return abs(service_impact * mit_ratio)

    table_rows = []
    for service_name, service_impact in service_impacts.iteritems():
        mit_ratio = service_mitrat[service_name]
        required_offset = _calc_req_offset(service_impact, mit_ratio)
        row_data = {
            table_strings['service_name']: table_strings[service_name],
            table_strings['service_impact']: sigfig(service_impact, 3),
            table_strings['mit_ratio']: mit_ratio,
            table_strings['required_offset']: sigfig(required_offset, 3),
        }
        table_rows.append(row_data)

    # sort the table rows based on the translated service name
    table_rows = sorted(table_rows,
        key=lambda x: x[table_strings['service_name']])

    reporting_dict = {
        'type': 'table',
        'section': 'body',
        'sortable': True,
        'checkbox': False,
        'total': False,
        'data_type': 'dictionary',
        'columns': table_columns,
        'data': table_rows,
        'position': 1,
    }
    return reporting_dict

