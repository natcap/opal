import logging
import json
import os

from osgeo import ogr
import shapely
import shapely.ops
import shapely.speedups
import shapely.wkb
import shapely.prepared
import pygeoprocessing

import preprocessing
import offsets
import utils

LOGGER = logging.getLogger('natcap.opal.analysis')

#    # now, aggregate over the correct polygons.
#    LOGGER.debug('Aggregating impacts')
#    for service_name, impact_raster in services:
#        field_name = "%s_sum" % service_name
#        aggregate_stats(impact_raster, out_vector_uri, 'FID', field_name)

def aggregate_stats(raster_uri, aggregate_vector, id_field, target_field,
        percent_to_stream=None):
    # aggregate stats over impact raster
    # loop through the correct component of the stats object and set the value
    # of the correct field.

    utils.assert_files_exist([raster_uri, aggregate_vector])
    target_field = target_field[:8]

    # collect stats under the aggregate polygon
    raster_stats = pygeoprocessing.aggregate_raster_values_uri(raster_uri,
        aggregate_vector, id_field).total

    if percent_to_stream is not None:
        LOGGER.debug('Adjusting aggregates by percent_to_stream %s',
            percent_to_stream)
        pts_per_impacts = pygeoprocessing.aggregate_raster_values_uri(
            percent_to_stream, aggregate_vector, id_field).pixel_max
        LOGGER.debug('pts_per_impacts: %s', pts_per_impacts)

        #print pts_per_impacts
        #print raster_stats

        LOGGER.debug('adjusting by percent-to-stream')
        adjusted_stats = {}
        for fid, pixel_sum in raster_stats.iteritems():
            try:
                percent_contribution = pts_per_impacts[fid]
                if percent_contribution is None:
                    percent_contribution = 0.0
            except KeyError:
                print 'KeyError!!!'
                percent_contribution = 0.0

            adjusted_stats[fid] = pixel_sum * percent_contribution
        LOGGER.debug('Finished adjusting by percent-to-stream')
    else:
        # If we're not adjusting by percent-to-stream, just use existing
        # raster_stats dictionary instead.
        adjusted_stats = raster_stats


    LOGGER.debug('Opening aggregate vector for editing')
    # I'm assuming that a side effect is ok in this case.
    out_vector = ogr.Open(aggregate_vector, 1)
    out_layer = out_vector.GetLayer()

    # create a new field in the output vector for the target field.
    LOGGER.debug('Adding new field "%s"', target_field)
    new_field_defn = ogr.FieldDefn(target_field, ogr.OFTReal)
    out_layer.CreateField(new_field_defn)

    # map FID field value to polygon index
    fid_fields = {}
    num_features = out_layer.GetFeatureCount()
    for feature_id in xrange(num_features):
        feature = out_layer.GetFeature(feature_id)
        fid_field_value = feature.GetField('FID')
        fid_fields[fid_field_value] = feature_id

    # I only care about the sum under the polygons ('total' attribute)
    LOGGER.debug('Number of fields analyzed: %s', len(raster_stats))
    for field_id, pixel_sum in adjusted_stats.iteritems():
        # Assuming that the field ID is the feature ID.
        feature = out_layer.GetFeature(fid_fields[field_id])
        feature.SetField(target_field, pixel_sum)
        out_layer.SetFeature(feature)

    out_layer.SyncToDisk()
    out_layer = None
    ogr.DataSource.__swig_destroy__(out_vector)
    out_vector = None

    return adjusted_stats

def calculate_biodiversity_impact(permitting_area_ds_uri, ecosystems_ds_uri):
    """Generates a dictionary indexed by ecosystem name that has both the
        impacted area and required offset area for mitigation.

        permitting_area_ds_uri -

        ecosystems_ds_uri -

        returns a dictionary of the format
            {
                ecosystem_name_1: {
                    'area': impacted area (float),
                    'mitigation_area'; required_mitigation area (float)
                    }
                ecosystem_name_2...
            }
        """


    utils.assert_files_exist([permitting_area_ds_uri, ecosystems_ds_uri])

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
        raise IOError('Permitting area is not a valid polygon')


    #2) Make a spatial index?
    if shapely.speedups.available:
        LOGGER.debug('Enabling shapely speedups')
        shapely.speedups.enable()

    impacts_schema = [f.GetName() for f in permitting_area_layer.schema]

    #3) Loop through each feature in permitting_area ds and build a polygon out of it
    biodiversity_impacts = {}
    ecosystems_ds = ogr.Open(ecosystems_ds_uri)
    ecosystems_ds_layer = ecosystems_ds.GetLayer()

    # determine if we want to also record ES impacts.
    ecosystems_schema = set(map(lambda f: f.GetName(),
        ecosystems_ds_layer.schema))
    _services_map = {
        'mitrat_c': 'carbon',
        'mitrat_s': 'sediment',
        'mitrat_n': 'nitrogen',
        'mitrat_cus': 'custom'
    }
    services = []
    for column_name, service_name in _services_map.iteritems():
        if column_name in ecosystems_schema:
            services.append(service_name)
    services = sorted(services)

    for feature_index in xrange(ecosystems_ds_layer.GetFeatureCount()):
        feature = ecosystems_ds_layer.GetFeature(feature_index)
        _get = lambda x: feature.GetField(x)
        ecosystem_type = _get('ecosystem')
        impact_factor = _get('mit_ratio')
        try:
            parcel_lci = _get('LCI')
        except ValueError:
            parcel_lci = None

        try:
            threat_score = _get('Threat')
        except ValueError:
            threat_score = None

        try:
            richness_score = _get('Richness')
        except ValueError:
            richness_score = None

        geometry = feature.GetGeometryRef()
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
        prepared_polygon = shapely.prepared.prep(polygon)
        if prepared_polygon.intersects(permitting_area_polygon):
            LOGGER.debug('Permitting area intersects.  Calculating area overlap')
            intersection = permitting_area_polygon.intersection(polygon)

            # dividing by 10,000 gives us ha.
            impacted_area = intersection.area / 10000.0
            mitigation_area = impacted_area * impact_factor
            impacted_parcel_area = (polygon.area / 10000.0)
            try:
                # If we have already found a parcel with this ecosystem type,
                # then we want to update the tracked amounts of biodiversity
                # that has been impacted and is required for offsets.
                ecosystem_impacts = biodiversity_impacts[ecosystem_type]
                ecosystem_impacts['impacted_area'] += impacted_area
                ecosystem_impacts['mitigation_area'] += mitigation_area

                previous_min = ecosystem_impacts['min_impacted_parcel_area']
                if previous_min > impacted_parcel_area:
                    ecosystem_impacts['min_impacted_parcel_area'] = impacted_parcel_area

                ecosystem_impacts['min_lci'] = max(
                    ecosystem_impacts['min_lci'], parcel_lci)

                ecosystem_impacts['max_threat'] = max(
                    ecosystem_impacts['max_threat'], threat_score)

                ecosystem_impacts['min_richness'] = min(
                    ecosystem_impacts['min_richness'], richness_score)

                ecosystem_impacts['patches_impacted'] += 1

            except KeyError:
                # If we have not yet impacted a parcel with this ecosystem
                # type, then create a new dictionary for tracking its relevant
                # information.
                ecosystem_impacts = {
                    'impacted_area': impacted_area,
                    'mitigation_ratio': impact_factor,
                    'mitigation_area': mitigation_area,
                    'min_impacted_parcel_area': impacted_parcel_area,
                    'min_lci': parcel_lci,
                    'max_threat': threat_score,
                    'min_richness': richness_score,
                    'patches_impacted': 1,
                }

            # Use the mean mitigation ratio.
            impacted_area = ecosystem_impacts['impacted_area']
            if impacted_area == 0:
                impacted_area = 1.0

            ecosystem_impacts['mitigation_ratio'] = (
                float(ecosystem_impacts['mitigation_area']) / float(impacted_area))

            biodiversity_impacts[ecosystem_type] = ecosystem_impacts

            LOGGER.debug('Overlaps: %s',
                biodiversity_impacts[ecosystem_type]['impacted_area'])
            LOGGER.debug('Required offset: %s Ha',
                biodiversity_impacts[ecosystem_type]['mitigation_area'])
    LOGGER.debug('Done.')
    return biodiversity_impacts

# TODO: make temp_file optional
def percent_overlap(offset_sites, municipalities, temp_file, pop_col):
    utils.assert_files_exist([offset_sites, municipalities])

    # first, get a set of municipalities polygons that intersect
    preprocessing.locate_intersecting_polygons(municipalities, offset_sites,
        temp_file)

    offset_vector = ogr.Open(offset_sites)
    offset_layer = offset_vector.GetLayer()
    offset_schema = [f.GetName() for f in offset_layer.schema]

    # These are columns in the vector that we want to skip, probably because we
    # want the offset_data dictionary key to be something custom.
    known_columns = ['ecosystem']

    all_offsets = {}
    for offset_feature in offset_layer:
        offset_fid = offset_feature.GetFID()
        offset_geometry = offset_feature.GetGeometryRef()
        offset_area = offset_geometry.Area()
        shapely_polygon = offsets.build_shapely_polygon(offset_feature)
        offset_data = {
#            'sediment': offset_feature.GetField('sediment'),
#            'nutrient': offset_feature.GetField('nutrient'),
#            'carbon': offset_feature.GetField('carbon'),
#            'distance': offset_feature.GetField('distance'),
            'area': offset_area,
            'polygon': shapely_polygon,
            'prep_polygon': shapely.prepared.prep(shapely_polygon),
        }
        if 'ecosystem' in offset_schema:
            offset_data['ecosystem'] = offset_feature.GetField('ecosystem')

        for field_name, field_value in offset_feature.items().iteritems():
            if field_name not in known_columns:
                offset_data[field_name] = field_value

        all_offsets[offset_fid] = offset_data

    temp_vector = ogr.Open(temp_file)
    temp_layer = temp_vector.GetLayer()


    final_data = {}
    for offset_fid, offset_data in all_offsets.iteritems():
        offset_area = offset_data['polygon'].area
        final_offset_data = {
#            'Sediment': offset_data['sediment'],
#            'Nitrogen': offset_data['nutrient'],
#            'Carbon': offset_data['carbon'],
#            'distance': offset_data['distance'],
#            'ecosystem': offset_data['ecosystem'],
#            'area': offset_data['area'],
            'municipalities': {}
        }

        for offset_key, offset_value in offset_data.iteritems():
            if offset_key in ['polygon', 'prep_polygon']:
                continue

            if offset_key.lower() == 'nutrient':
                offset_key = 'nitrogen'

            final_offset_data[offset_key.capitalize()] = offset_value

        for municipality in temp_layer:
            m_polygon = offsets.build_shapely_polygon(municipality)
            m_name = municipality.GetField(pop_col)

            # check to see if there's overlap.
            if offset_data['prep_polygon'].intersects(m_polygon):
                inter_area = offset_data['polygon'].intersection(m_polygon).area

                overlap_ratio = inter_area / offset_area

                if overlap_ratio > 0:
                    final_offset_data['municipalities'][m_name] = overlap_ratio
        temp_layer.ResetReading()
        final_data[offset_fid] = final_offset_data
    return final_data

def vectors_intersect(vector_1_uri, vector_2_uri):
    """Take in two OGR vectors (we're assuming that they're in the same
    projection) and test to see if their geometries intersect.  Return True of
    so, False if not.

    vector_1_uri - a URI to an OGR vector
    vector_2_uri - a URI to an OGR vector

    Returns True or False"""

    utils.assert_files_exist([vector_1_uri, vector_2_uri])

    LOGGER.debug('Opening vector %s', vector_1_uri)
    basename_1 = os.path.basename(vector_1_uri)
    vector_1 = ogr.Open(vector_1_uri)
    layer_1 = vector_1.GetLayer()

    LOGGER.debug('Opening vector %s', vector_2_uri)
    basename_2 = os.path.basename(vector_2_uri)
    vector_2 = ogr.Open(vector_2_uri)
    layer_2 = vector_2.GetLayer()

    for feature_1 in layer_1:
        prep_polygon = offsets.build_shapely_polygon(feature_1, prep=True)

        for feature_2 in layer_2:
            polygon = offsets.build_shapely_polygon(feature_2)
            if prep_polygon.intersects(polygon):
                fid_1 = feature_1.GetFID()
                fid_2 = feature_2.GetFID()
                LOGGER.debug('%s (fid %s) and %s (fid %s) intersect',
                    basename_1, fid_1, basename_2, fid_2)
                return True
        layer_2.ResetReading()
    LOGGER.debug('No Features intersect.')
    return False

def features_in_vector(vector_uri):
    """Get the number of features in this vector.

    Args:
        vector_uri (string): The string filepath of the OGR vector to query

    Returns:
        The integer number of features in the vector."""

    vector = ogr.Open(vector_uri)
    layer = vector.GetLayer()
    num_features = int(layer.GetFeatureCount())
    return num_features


