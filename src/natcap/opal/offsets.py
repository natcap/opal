"""The python file for offset portfolio calculation."""
import logging
import math
import os
import json

from osgeo import ogr
import shapely
import shapely.speedups
import shapely.wkb
import shapely.prepared
import shapely.geometry
import shapely.geos

import adept_core

LOGGER = logging.getLogger('natcap.opal.offsets')

# offset schemes
OFFSET_SCHEME_ES = 0
OFFSET_SCHEME_BIODIV = 1
OFFSET_SCHEME_BIO_ES = 2

def build_shapely_polygon(ogr_feature, prep=False, fix=False):
    geometry = ogr_feature.GetGeometryRef()
    try:
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
    except shapely.geos.ReadingError:
        LOGGER.debug('Attempting to close geometry rings')
        # If the geometry does not form a closed circle, try to connect the
        # rings with the OGR function.
        geometry.CloseRings()
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
        LOGGER.debug('Geometry fixed')

    if fix:
        polygon = polygon.buffer(0)
    if prep:
        polygon = shapely.prepared.prep(polygon)
    return polygon

def distance_between_points(point_a, point_b):
    x1, y1 = point_a
    x2, y2 = point_b
    return math.hypot(math.fabs(x2 - x1), math.fabs(y2 - y1))

def poly_intersects_vector(polygon, vector_uri):
    """Simple function to check if a polygon intersects any polygon in the
    input vector.  Returns a boolean True or False.

        polygon - a shapely polygon
        vector_uri - a URI to an OGR vector.

    Returns True or False."""

    vector = ogr.Open(vector_uri)
    layer = vector.GetLayer()

    for feature in layer:
        shapely_feature = build_shapely_polygon(feature, prep=True)
        if shapely_feature.intersects(polygon):
            return True
    return False


def locate_parcels(possible_parcels, selection_area, impact_sites):
    """This function will iterate through all polygons in the possible_parcels
    vector that are within the selection area.

        possible_parcels - a URI to an OGR vector of polygons.
        selection_area - a URI to an OGR vector of the area to consider.
        impact_sites - a URI to an OGR vector of impact sites.

    #TODO: What should this function return?
    Returns something ... not yet sure what."""

    # TODO: need a way to prioritize polygons.  Factors to consider:
    #  - distance of offset parcel centroid from the impact parcel. (prefer nearer)
    #  - whether the patch contributes to biodiversity (prefer if yes)
    #    - if biodiversity parcel < 5ha, biodiversity from this parcel is not
    #      counted towards the total biodiversity offset.
    #  - parcel size.

    # TODO: start out with just selecting all the parcels completely contained
    # within the selection area.

    if shapely.speedups.available:
        LOGGER.debug('Enabling shapely speedups')
        shapely.speedups.enable()

    LOGGER.debug('Extracting selection area polygon')
    sa_vector = ogr.Open(selection_area)
    sa_layer = sa_vector.GetLayer()
    sa_feature = sa_layer.GetFeature(0)
    sa_geometry = sa_feature.GetGeometryRef()
    sa_polygon = shapely.wkb.loads(sa_geometry.ExportToWkb())
    #selection_area = shapely.geometry.polygon.Polygon(sa_polygon)

    # Open the impact sites vector
    LOGGER.debug('Opening the impact sites vector')
    impact_vector = ogr.Open(impact_sites)
    impact_layer = impact_vector.GetLayer()

    # create a data structure that allows me to prioritize possible polygons.
    parcels = []

    LOGGER.debug('Opening the parcels vector')
    ecosystems_vector = ogr.Open(possible_parcels)
    ecosystems_layer = ecosystems_vector.GetLayer()
    for possible_parcel in ecosystems_layer:
        # see if the parcel intersect with the selection_area
        polygon = build_shapely_polygon(possible_parcel)
        prepared_polygon = shapely.prepared.prep(polygon)
        if prepared_polygon.intersects(sa_polygon):
            LOGGER.debug('Possible offset area intersects.')

            distances = {}
            for impact_id, ogr_impact_site in enumerate(impact_layer):
                impact_site = build_shapely_polygon(ogr_impact_site)
                key = 'impact_%s' % impact_id

                # currently accessing the minimum distance between polygons.  If we
                # want the distance between centroids, get the point's coordinates
                # like so:
                # impact_site.centroid.coords[0] and pass it to the
                # distance_between_points function, above.
                distance = impact_site.distance(polygon)
                distances[key] = distance
            impact_layer.ResetReading()

            offset_parcel_data = {
                'polygon': polygon,
                'area': polygon.area,
                'distances':  distances,
            }
            parcels.append(offset_parcel_data)

    #print parcels

def _select_offsets(offset_parcels_uri, impact_sites_uri, biodiversity_impacts, output_vector,
        output_json, comparison_vectors={}, services=['carbon', 'nutrient', 'sediment'],
        offset_factors={'carbon': 1.0, 'nutrient': 1.0,'sediment': 1.0, 'biodiversity': 1.0},
        offset_scheme=OFFSET_SCHEME_BIODIV):
    """Determine which parcels to return, where parcels returned meet
    appropriate criteria defined in the inputs.

    offset_parcels_uri - a URI to a vector containing polygons.  Parcels
        provided here are the parcels available for use as offsets.  Parcels
        must have the following attributes:
            ecosystem - a string with the ecosystem name
            LCI - the Landscape Context Index for the parcel (float)
            carbon - (float) only required if carbon in services input.
            nutrient - (float) only required if nutrient in services input.
            sediment - (float) only required if sediment in services input.
    impact_sites_uri - a URI to a vector containing polygons.  Parcels provided
        here are those that have been analyzed as impacts to the landscape.
        Parcels must have these columns:
            carbon - (float) only required if carbon in services input.
            nutrient - (float) only required if nutrient in services input.
            sediment - (float) only required if sediment in services input.
            Threat - (float) required if an ecosystem has threat data.
            Richness - (float) required if an ecosystem has richness data.
    biodiversity_impacts - Dict mapping string ecosystem names to dicts with
        the following key-value pairs:
            min_impacted_parcel_area - (number) The area (in Ha) of the smallest
                impacted natural parcel of this ecosystem type.
            min_lci - (number between 0, 1) The lowest LCI of all impacted
                parcels of this ecosystem type.
            max_threat - (number) The max threat value of all impacted natural
                parcels of this ecosystem type.  This will be None if there is
                no threat data.
            min_richness - (number) The min richness value of all impacted
                natural parcels of this ecosystem type.  This will be None if
                there is no richness data.
            mitigation_area - (number) The area (in ha) required for mitigating
                the impacts to this ecosystem type.
    output_vector - a URI to where an output vector should be written.  This
        vector will contain a subset of the parcels provided in the vector at
        offset_parcels_uri, where subset parcels are those that have been
        'selected' by this function.
    output_json - a URI to where an output JSON object should be written.  This
        JSON object will contain detailed information about the parcels that
        have been selected by this function.
    comparison_vectors - a dict mapping string keys to URIs representing OGR
        vectors on disk.  These vectors are used to determine whether offset
        polygons intersect these vectors.  The resulting binary information is
        recorded using the string key in the output vector and JSON object.
    services - a list of string ecosystem service names.  Any strings in this
        list must also exist in the impact_sites_uri vector as columns, where
        the column data is numeric (usually a float).
    offset_factor - a number (float or int) indicating the proportion of the
        the total required offsets that the set of offset parcels selected
        should offset.  Default: 1.0.
    offset_scheme - a number, one of OFFSET_SCHEME_ES, OFFSET_SCHEME_BIODIV, or
        OFFSET_SCHEME_BIO_ES.  Indicates which offset scheme should be used.

    Returns a tuple.  The first tuple element is a list of all integer parcel
    indices selected.  The second tuple element is a set of recommended parcels
    based on known impacts/offsets.
    """

#        offset_factor=1.0 - an int or float.  Offset parcels will be selected
#            for each ecosystem type until the ecosystem type's
#            mitigation_area*offset_factor is met or we run out of parcels to
#            select.
    # comparison_vectors should have string keys mapping to URIs.
    LOGGER.debug('Opening impacts sites vector %s', impact_sites_uri)
    impact_vector = ogr.Open(impact_sites_uri)
    impact_layer = impact_vector.GetLayer()
    impact_schema = map(lambda d: d.GetName(), impact_layer.schema)

    # check that all fields passed in via services parameter are found in the
    # impact sites vector.  It's an error if not.
    for service_name in services:
        if service_name not in impact_schema:
            raise RuntimeError('Service %s not defined in impact schema' %
                service_name)

    # Get information about which offset parcels we can actually use for
    # mitigation.
    LOGGER.debug('Getting possible offset parcels')
    if len(biodiversity_impacts) == 0 or\
        offset_scheme in [OFFSET_SCHEME_ES, OFFSET_SCHEME_BIO_ES]:
        include_all_ecosystems = True
    else:
        include_all_ecosystems = False
    bio_offsets = locate_biodiversity_offsets(offset_parcels_uri,
        biodiversity_impacts, include_all_ecosystems)

    # loop through the impact sites and get a list of centroid coordinates
    impact_polygons = [build_shapely_polygon(site).centroid for site in impact_layer]

#    for offset_index in xrange(num_offset_parcels):
#        offset_feature = offsets_layer.GetFeature(offset_index)
#        offset_polygon = build_shapely_polygon(offset_feature)
#        ecosystem_impacted = offset_feature.GetField('ecosystem')
#        parcel_area = offset_feature.GetGeometryRef().Area()
#        parcel_lci = offset_feature.GetField('LCI')
#

    LOGGER.debug('Calculating distance from offset to impact sites')
    offsets_vector = ogr.Open(offset_parcels_uri)
    offsets_layer = offsets_vector.GetLayer()

    for offset_index, offset_data in bio_offsets.iteritems():
        offset_parcel = offsets_layer.GetFeature(offset_index)
        offset_polygon = build_shapely_polygon(offset_parcel)

        # figure out if our offset polygon intersects any of the comparison
        # vectors.
        for comp_name, comp_vector in comparison_vectors.iteritems():
            intersects = poly_intersects_vector(offset_polygon, comp_vector)
            bio_offsets[offset_index][comp_name] = intersects

        offset_polygon = offset_polygon.centroid

        min_distance = min(map(lambda x: offset_polygon.distance(x),
            impact_polygons))
        bio_offsets[offset_index]['distance'] = min_distance

    # for now, just sort based on distance from impact parcel.
    sorted_offset_parcels = sorted(bio_offsets.keys(),
        key=lambda k: bio_offsets[k]['distance'])
    LOGGER.debug('Sorted offset parcels: %s', sorted_offset_parcels)

    # select enough parcels to offset the impact requirements and still meet
    # the minimum number of parcels required.

    # impact_offsets tracks the amt of area offset per ecosystem type.
    # initialize all the ecosystems tracked to 0.
    impact_offsets = dict((e_n, 0.0) for e_n in list(set(map(
        lambda x: bio_offsets[x]['ecosystem'], bio_offsets.keys()))))
    LOGGER.debug('impact_offsets: %s', impact_offsets)

    min_parcels_to_select = 20
    min_offset_factor = offset_factors['biodiversity']
    parcels_selected = {}
    new_field_data = {}
    new_fields = ['distance'] + comparison_vectors.keys()
    recommendations = {}
    biodiversity_requirements = {}
    for ecosystem_name, offset_amt in impact_offsets.iteritems():
        # Richness and threat data are stored as None or Floats.
        # In python, None is less than -inf.
        ecosys_in_bio_impacts = ecosystem_name in biodiversity_impacts
        if len(biodiversity_impacts) > 0 and ecosys_in_bio_impacts:
            max_threat = biodiversity_impacts[ecosystem_name]['max_threat']
            min_richness = biodiversity_impacts[ecosystem_name]['min_richness']

            # required mitigation area is in ha, yet parcel areas are in m^2
            # multiply ha by 10,000 to get m^2
            required_mitigation_area = biodiversity_impacts[ecosystem_name]['mitigation_area']
            min_mitigation = (required_mitigation_area * 10000) * min_offset_factor
        else:
            # when there are no biodiversity impacts, we need to assume some
            # default values so that we only account for ecosystem services.
            max_threat = None
            min_richness = None
            required_mitigation_area = 0.0
            min_mitigation = 0.0

        LOGGER.debug('Locating offsets for ecosystem "%s"', ecosystem_name)
        parcels_in_ecosystem = []
        for possible_offset in sorted_offset_parcels:
            parcel_feature = offsets_layer.GetFeature(possible_offset)

            if parcel_feature.GetField('ecosystem') == ecosystem_name:
                # if we have Threat data, we need to enforce that all offset
                # parcels meet the minimum threat score requirement.
                if max_threat is not None:
                    parcel_threat = parcel_feature.GetField('Threat')
                    if parcel_threat > max_threat:
                        # if threat requirement is not met, skip this parcel
                        continue

                if min_richness is not None:
                    parcel_richness = parcel_feature.GetField('Richness')
                    if parcel_richness < min_richness:
                        # if the richness requirement is not met, skip this
                        # parcel
                        continue

                parcels_in_ecosystem.append(possible_offset)

                parcel_area = parcel_feature.GetGeometryRef().Area()
                parcels_selected[possible_offset] = parcel_area
                impact_offsets[ecosystem_name] += parcel_area

                parcel_data = {}
                for fieldname in new_fields:
                    new_field_value = bio_offsets[possible_offset][fieldname]
                    parcel_data[fieldname] = new_field_value

                new_field_data[possible_offset] = parcel_data
                new_field_data[possible_offset]['area'] = parcel_area
                new_field_data[possible_offset]['ecosystem_type'] = ecosystem_name
                new_field_data[possible_offset]['parcel_id'] = possible_offset

                for es_field in services:
                    es_value = parcel_feature.GetField(es_field)
                    new_field_data[possible_offset][es_field] = es_value

                # Uncomment these lines if you want to only show the minimum
                # number of parcels needed to meet the rules above.
#                if impact_offsets[ecosystem_name] >= min_mitigation and \
#                    len(parcels_selected) >= min_parcels_to_select:
#                    LOGGER.debug('Parcel requirements have been satisfied.')
#                    break

        # I only want those offsets that match this ecosystem name
        available_offset_parcels = {}
        for parcel in parcels_in_ecosystem:
            available_offset_parcels[parcel] = new_field_data[parcel]

#        TODO: add requirements to the requirements list depending on whether
#        we want to include biodiversity and/or ES restrictions when selecting
#        a set of parcels.
#        recommended_parcels = select_set(available_offset_parcels,
#            [('area', min_mitigation)])
#        recommendations[ecosystem_name] = recommended_parcels
#        LOGGER.debug('Recommended parcels for %s: %s', ecosystem_name,
#            recommended_parcels)
#
#    LOGGER.debug('Found %s offset parcels to meet requirements',
#            len(parcels_selected))

    offset_parcels_schema = map(lambda d: d.GetName(), offsets_layer.schema)
    output_fields = ['ecosystem'] + services
    new_fields += ['parcel_id', 'area']
    field_types = {
        'parcel_id': ogr.OFTInteger,
        'Subzone': ogr.OFTInteger,
        'AOI': ogr.OFTInteger,
        'City': ogr.OFTInteger,
        'distance': ogr.OFTReal,
        'area': ogr.OFTReal,
    }
    for key in ['LCI', 'Threat', 'Richness', 'custom']:
        if key in offset_parcels_schema:
            output_fields.append(key)

    index_map = adept_core.write_vector(offset_parcels_uri, parcels_selected.keys(),
        output_vector, output_fields, new_fields, new_field_data, field_types)

    updated_recommendations = {}
    for ecosystem_name, suggested_fid in recommendations.iteritems():
        new_fids = []
        for fid in suggested_fid:
            new_fids.append(index_map[fid])

        updated_recommendations[ecosystem_name] = new_fids

    json.dump({'field_data': new_field_data,
        'parcel_sets': updated_recommendations},
        open(output_json, 'w'), sort_keys=True, indent=4)

    return (parcels_selected.keys(), updated_recommendations)

def locate_biodiversity_offsets(offset_parcels_uri, biodiversity_impacts,
        include_all_ecosystems=False):
    """Given a vector of possible offset parcels and a set of known impacts,
    determine which offset parcels can be considered.  An offset parcel will be
    considered if its ecosystem type is in the set of known, impacted ecosystem
    types.

        offset_parcels_uri - a URI to an OGR vector containing offset parcels.
            This vector must include the following attributes:
                ecosystem - A string ecosystem name
                LCI - the Landscape Context Index for this parcel (float, 0-1)
        biodiversity_impacts - a dict with keys being string ecosystem names
            that may be found in the ecosystem column of the offset parcels
            vector.  Values are dicts with at least these attributes:
                'min_impacted_parcel_area' - a number
                'min_lci' - a number
        include_all_ecosystems=False - a boolean.  If True, the resulting
            dictionary will include all ecosystems encountered.  Biodiversity
            offsets will still be reported as normal, but the output dictionary
            will include ecosystems that are not valid biodiversity offsets.
            These parcels that are not valid biodiversity offsets will have
            values of 0 or None.

    Under normal conditions, this function will only look at ecosystem types
    that are found in the biosiversity_impacts dict.  In the case where
    biodiversity_impacts contains no entries, ALL ecosystem types will be
    considered.

    Returns a dict mapping integer parcel indices to dict values with the
    following attributes:
        ecosystem - the string ecosystem name of the offset parcel
        area - the area of the offset parcel
        lci - the Landscape Context Index of the offset parcel"""

    LOGGER.debug('Opening parcels vector %s', offset_parcels_uri)
    offsets_vector = ogr.Open(offset_parcels_uri)
    offsets_layer = offsets_vector.GetLayer()
    offsets_srs = offsets_layer.GetSpatialRef()
    offsets_schema = set(map(lambda d: d.GetName(), offsets_layer.schema))
    LOGGER.debug(offsets_schema)

    service_funcs = {}
    known_services = {
        'carbon': lambda f: f.GetField('carbon'),
        'sediment': lambda f: f.GetField('sediment'),
        'nutrient': lambda f: f.GetField('nutrient'),
        'custom': lambda f: f.GetField('custom'),
    }
    for service_name, service_field_func in known_services.iteritems():
        if service_name in offsets_schema:
            service_funcs[service_name] = service_field_func

    LOGGER.debug(service_funcs.keys())

    valid_offset_parcels = {}

    # if we aren't doing any biodiversity restrictions, allow parcels from ANY
    # ecosystem to be included.
    use_any_ecosystem = len(biodiversity_impacts) == 0 or include_all_ecosystems

    num_offset_parcels = offsets_layer.GetFeatureCount()
    LOGGER.debug('Examining %s possible offset parcels', num_offset_parcels)
    for offset_index in xrange(num_offset_parcels):
        offset_feature = offsets_layer.GetFeature(offset_index)
        ecosystem_impacted = offset_feature.GetField('ecosystem')

        # Convert parcel area to Ha.
        # eco_impact_data['min_impacted_parcel_area'] is also in Ha.
        parcel_area = offset_feature.GetGeometryRef().Area() / 10000.0

        try:
            parcel_lci = offset_feature.GetField('LCI')
        except ValueError:
            parcel_lci = None

        print "%s, %s" % (parcel_area, parcel_lci)

        if ecosystem_impacted in biodiversity_impacts:
            eco_impact_data = biodiversity_impacts[ecosystem_impacted]
            min_area = eco_impact_data['min_impacted_parcel_area']
            min_lci = eco_impact_data['min_lci']
            if parcel_area >= min_area and parcel_lci >= min_lci:
                offset_parcel_data = {
                    'ecosystem': ecosystem_impacted,
                    'area': parcel_area,
                    'lci': parcel_lci,
                }
                valid_offset_parcels[offset_index] = offset_parcel_data
        elif use_any_ecosystem is True:
            valid_offset_parcels[offset_index] = {
                'ecosystem': ecosystem_impacted,
                'area': parcel_area,
                'lci': parcel_lci,
            }

    LOGGER.debug('Found %s possible offset parcels out of %s provided',
        len(valid_offset_parcels), num_offset_parcels)

    LOGGER.debug(json.dumps(valid_offset_parcels, indent=4, sort_keys=True))
    return valid_offset_parcels

def select_offsets(offset_parcels_uri, impact_sites_uri, output_dir):
    """select offset sites for each impact site.  All sites in the offset
    parcels are available for consideration.

    This function will create one new OGR vector per impact site.  Each of
    these offset vectors will contain the selected geometries that offset the
    impact.  An offset parcel may not offset more than one impact site.

    offset vectors will be saved to the output_dir.

    Returns a dictionary with this structure:
        {
            impact site ID: {
                service_name_1: service mitigated
                service_name_2: service mitigated
            }
            ...
        }"""

    if shapely.speedups.available:
        LOGGER.debug('Enabling shapely speedups')
        shapely.speedups.enable()

    LOGGER.debug('Opening parcels vector %s', offset_parcels_uri)
    parcels_vector = ogr.Open(offset_parcels_uri)
    parcels_layer = parcels_vector.GetLayer()
    parcels_srs = parcels_layer.GetSpatialRef()

    LOGGER.debug('Opening impact vector %s', impact_sites_uri)
    impact_vector = ogr.Open(impact_sites_uri)
    impact_layer = impact_vector.GetLayer()

    if not os.path.exists(output_dir):
        LOGGER.debug('Creating output folder %s', output_dir)
        os.makedirs(output_dir)

    # build up a data structure to represent the available offset polygons
    # any parcels represented in available_parcels are available for selection.
    all_parcels = {}
    for parcel in parcels_layer:
        parcel_fid = parcel.GetFID()  # feature identifier
        parcel_data = {
            'polygon': build_shapely_polygon(parcel),
            'sediment': parcel.GetField('sediment'),
            'nutrient': parcel.GetField('nutrient'),
            'carbon': parcel.GetField('carbon'),
            'offsets': None,  # if this is an int, that's the impact site fid
        }
        all_parcels[parcel_fid] = parcel_data

    offsets_record = {}
    for impact_site in impact_layer:
        # get the impact site's geometry and convert to a shapely polygon.
        impact_polygon = build_shapely_polygon(impact_site)
        impact_site_fid = impact_site.GetFID()
        impact_quantity = impact_site.GetField('sediment')
        quantity_offset = 0.0
        out_vector_uri = None  # if None, no file written with portfolio

        if impact_quantity == 0:
            LOGGER.info('Impact site %s has nothing to offset.',
                    impact_site_fid)
        else:
            available_parcels = []
            for parcel_fid, parcel_data in all_parcels.iteritems():
                if parcel_data['offsets'] is None:  # parcel doesn't offset something
                    available_parcels.append({
                        'fid': parcel_fid,
                        'sediment': parcel_data['sediment'],
                        'nutrient': parcel_data['nutrient'],
                        'carbon': parcel_data['carbon'],
                        'distance': impact_polygon.distance(parcel_data['polygon']),
                    })

            # sort the available offset parcels.  This could easily be replaced by
            # a more sophisticated way of prioritizing offset parcels.  For now,
            # I'm relying solely on the minimum distance between impact and offset
            # sites.
            sorted_offset_parcels = sorted(available_parcels, key=lambda p:
                    p['distance'])
            LOGGER.debug('Evaluating %s parcels', len(sorted_offset_parcels))
            parcels_selected = []  # bookkeeping list

            # select offset parcels for this impact site.
            for offset_parcel in sorted_offset_parcels:
                if quantity_offset >= impact_quantity:
                    LOGGER.debug('Impact site %s offsets met.', impact_site_fid)
                    break  # we've offset everything we want/need

                # we can only select the parcel if it doesn't intersect with the
                # impact parcel.
                # get the parcel's geometry, see if it intersects impact_polygon.
                #offset_polygon = build_shapely_polygon(
                #    parcels_layer.GetFeature(offset_parcel['fid']))
                if offset_parcel['distance'] > 0:  # does not intersect
                #if not offset_polygon.intersects(impact_polygon):
                    # mark the parcel as selected
                    offset_parcel_fid = offset_parcel['fid']
                    all_parcels[offset_parcel_fid]['offsets'] = impact_site_fid
                    parcels_selected.append(offset_parcel_fid)

                    # increase the per-impact service that's been offset
                    quantity_offset += offset_parcel['sediment']

            LOGGER.debug('Finished evaluating impact site %s', impact_site_fid)
            if quantity_offset < impact_quantity:
                if quantity_offset == 0.:
                    percent_offset = 0
                else:
                    percent_offset = impact_quantity/quantity_offset
                LOGGER.warn('Impact site %s only offset %s percent of its impact',
                    impact_site_fid, percent_offset)

            # once we've selected all of our parcels in the previous loop, write
            # these new polygons to a new vector in the user's defined output
            # folder.  If no offser parcels have been selected for this impact
            # site, don't create an output vector for it.
            if len(parcels_selected) == 0:
                LOGGER.debug('Impact site %s has no offsets', impact_site_fid)
            else:
                new_vector_name = "site_%s_offsets.shp" % impact_site_fid
                layer_name = str(new_vector_name[:8])  # shapefile requires ASCII
                out_vector_uri = os.path.join(output_dir, new_vector_name)

                out_driver = ogr.GetDriverByName('ESRI Shapefile')
                out_vector = out_driver.CreateDataSource(out_vector_uri)

                out_layer = out_vector.CreateLayer(layer_name, srs=parcels_srs)
                # create a new offset field for each ES.
                es_fields = ['sediment', 'nutrient', 'carbon']
                for field_name in es_fields:
                    field_defn = ogr.FieldDefn(field_name, ogr.OFTReal)
                    out_layer.CreateField(field_defn)
                out_layer_defn = out_layer.GetLayerDefn()

                for parcel_fid in parcels_selected:
                    parcel_feature = parcels_layer.GetFeature(parcel_fid)
                    parcel_geom = parcel_feature.GetGeometryRef()
                    parcel_defn = parcel_feature.GetDefnRef()

                    new_feature = ogr.Feature(parcel_defn)
                    new_feature.SetGeometry(parcel_geom)

                    # fetch the ES data from the parcel and copy it over.
                    for field_name in es_fields:
                        parcel_data = parcel_feature.GetField(field_name)
                        field_index = out_layer_defn.GetFieldIndex(field_name)
                        new_feature.SetField(field_index, parcel_data)

                    out_layer.CreateFeature(new_feature)

                out_layer.SyncToDisk()
                out_layer = None
                out_vector = None
                out_driver = None

        # For the sake of consistency, check if the impact quantity has not
        # been set.  If this is the case, set the impact quantity to 0.0
        if impact_quantity is None:
            impact_quantity = 0.0

        offsets_record[impact_site_fid] = {
                'offset_portfolio': out_vector_uri,
                'services': {
                    'sediment': {
                        'impact': impact_quantity,
                        'offset_sum': quantity_offset,
                    },
                }
            }
    offsets_json_uri = os.path.join(output_dir, 'offsets.json')
    LOGGER.debug('Saving offset summary to %s', offsets_json_uri)
    json.dump(offsets_record, open(offsets_json_uri, 'w'), sort_keys=True, indent=4)
    return offsets_record

def select_set(parcels_dict, requirements):
    """Select a set of parcels that together meet a set of minimum
    requirements, outlined in the `requirements` input.

        parcels_dict - a dictionary describing the available parcels and the
            various attributes we're considering in parcel selection.
            example:
                parcels_dict = {
                    1: {'area': 400, 'carbon': 3500, 'sediment': 290},
                    2: {'area': 123, 'carbon': 382, 'sediment': 1348},
                    3: {'area': 8392, 'carbon': 1910, 'sediment': 18234},
                    4: {'area': 149, 'carbon': 192, 'sediment': 1019},
                }
            The key is the parcel identifier.  It can be of any type.
            The keys of the parcel dictionary ('area', 'carbon', 'sediment')
            can be any keys, so long as they match the service names in the
            requirements list.  The values of the parcel dictionary MUST be
            numeric.  They represent the service value for this parcel.
        requirements - a list of tuples.
            example:
                requirements = [
                    ('area', 350),
                    ('sediment', 2000),
                    ('carbon', 100),
                ]
            The first element of the tuple is the service name.  It must match
            the one of the service names found in the parcels_dict.
            The second element is the minimum required amount of this service
            for parcel selection.

        In the examples given, Parcel 3 meets all three requirements, so it is
        the only parcel returned from this function.

        Returns a sorted list of parcel identifiers meeting the above
        requirements."""

    # use sets because a parcel ID can only appear once and order doesn't
    # matter, and constant-time accesses are useful.
    available_parcels = set(parcels_dict.keys())
    recommended_parcels = set()

    for rule_key, rule_min in requirements:
        # sort parcels from max to min.  We want a minimum number of parcels
        # that meets this requirement.
        # available_parcels contains only those parcels that have not been
        # selected.
        sorted_parcels = sorted(available_parcels,
            key=lambda pid: parcels_dict[pid][rule_key], reverse=True)

        rule_sum = 0
        if len(recommended_parcels) > 0:
            # If we already have selected parcels, we need to first check if
            # they already satisfy this requirement.
            rule_sum = sum([parcels_dict[x][rule_key] for x in recommended_parcels])
            if rule_sum >= rule_min:
                LOGGER.debug(('Rule %s already met with existing parcel set'
                    ' (min=%s, sum=%s)'), rule_key, rule_min, rule_sum)
                continue

        for parcel_id in sorted_parcels:
            if rule_sum >= rule_min:
                LOGGER.debug('Met rule %s >= %s with %s', rule_key, rule_min,
                    rule_sum)
                break
            rule_sum += parcels_dict[parcel_id][rule_key]
            recommended_parcels.add(parcel_id)
            available_parcels.remove(parcel_id)
        LOGGER.debug('Parcel set so far: %s', recommended_parcels)

    LOGGER.debug('Found %s parcels to recommend', len(recommended_parcels))
    return sorted(recommended_parcels)


# quick function to convert from m to ha
Ha = lambda m: m / 10000.0

def select_set_multifactor(parcels, biodiversity_req=None, es_hydro_req=None,
        es_global_req=None, proportion_offset=1.0):
    """Multifactor parcel selection.  Selects offset parcels based on
    biodiversity, hydrological ES and global ES requirements.

    parcels - a dict mapping integer offset parcel IDs to dictionaries with
        offset parcel information:
            'area' - a numberic value, the parcel's area.  Required if
                biodiversity_req is provided.
            'ecosystem' - a string ecosystem name for this offset parcel.
                Required if biodiversity_req is provided.
    biodversity_req - a dictionary mapping string ecosystem names to a
        dictionary with the following entrie(s):
            'mitigation_area' - the numeric area required to offset impacts to
                this ecosystem type.
    proportion_offset=1.0 - a number indicating the proportion of
        impacts/requirements to offset.
"""
    if biodiversity_req is None and es_hydro_req is None and es_global_req is None:
        raise Exception('No requirements specified')
    proportion_offset = float(proportion_offset)
    LOGGER.debug('Offsetting with proportion = %s', proportion_offset)

    selected_parcels = set([])
    if biodiversity_req is not None:
        # determine which parcels are in which ecosystem.
        ecosystems = {}
        for parcel_key, parcel_data in parcels.iteritems():
            ecosystem_id = parcel_data['ecosystem']
            try:
                ecosystems[ecosystem_id].append(parcel_key)
            except:
                ecosystems[ecosystem_id] = [parcel_key]

        for impacted_ecosystem, ecosys_data in biodiversity_req.iteritems():
            required_area = ecosys_data['mitigation_area']
            ecosys_selected_area = 0
            ecosystem_selected_parcels = []
            try:
                possible_parcels = ecosystems[impacted_ecosystem]
            except KeyError:
                LOGGER.warn(('Impacted ecosystem "%s" does not have any '
                    'available offset parcels') % impacted_ecosystem)
                continue

            # sort so that largest parcel areas are first.
            sorted_parcels = sorted(possible_parcels,
                key=lambda p: parcels[p]['area'], reverse=True)

            for parcel_key in sorted_parcels:
                if ecosys_selected_area >= (required_area * proportion_offset):
                    LOGGER.debug('Ecosystem %s area req. (%s*%s) met with (%s)',
                        impacted_ecosystem, proportion_offset, required_area,
                        ecosys_selected_area)
                    break

                parcel_data = parcels[parcel_key]

                # select the parcel.
                ecosystem_selected_parcels.append(parcel_key)
                ecosys_selected_area += parcel_data['area']

            # add the newly selected parcels to the running set
            selected_parcels.update(ecosystem_selected_parcels)
        LOGGER.debug('Parcels selected after biodiversity: %s',
            selected_parcels)

    if es_hydro_req is not None:
        hydro_selected_parcels = set([])
        for serviceshed_id, serviceshed_data in es_hydro_req.iteritems():
            try:
                sshed_parcels = serviceshed_data['parcels']
            except KeyError:
                # If there are no parcels in this serviceshed, skip
                # the serviceshed.  Related to adept_core.py, line 667.
                continue

            # Figure out which hydrological services have impacts and if we
            # have selected parcels, we want to know the service offset values
            # of those parcels.
            services = {}
            for service_key in ['sediment', 'nutrient', 'custom']:
                try:
                     sshed_service_data = {
                        'required_amt': serviceshed_data[service_key],
                        'offset': 0
                    }
                except KeyError:
                    # when the service is not in serviceshed_data, we're not
                    # trying to meet that service's requrements.
                    continue

                for sshed_parcel in sshed_parcels:
                    if sshed_parcel in selected_parcels:
                        service_offset = parcels[sshed_parcel][service_key]
                        sshed_service_data['offset'] += service_offset
                LOGGER.debug('sshed %s %s: %s', serviceshed_id, service_key,
                    sshed_service_data['offset'])

                # keep track of the service data for this serviceshed.
                services[service_key] = sshed_service_data

            # select available parcels until requirements have been met.
            remaining_parcels = set(serviceshed_data['parcels']).difference(
                selected_parcels)
            LOGGER.debug('Remaining parcels: %s', remaining_parcels)
            if len(remaining_parcels) == 0:
                continue

            # iterate through the provided services in alphabetical order.
            for service, service_data in sorted(services.iteritems(),
                    key=lambda x: x[0]):
                # get a list of available parcels, sorted in increasing order
                offset_parcels = sorted(remaining_parcels, key=lambda x:
                    parcels[x][service], reverse=True)
                LOGGER.debug('Offset parcels: %s', offset_parcels)
                service_offset = service_data['offset']
                required_amt = service_data['required_amt'] * proportion_offset

                for offset_parcel in offset_parcels:
                    if service_offset > required_amt:
                        break

                    # if we've already picked the parcel, skip it.
                    if offset_parcel in hydro_selected_parcels:
                        continue

                    parcel_data = parcels[offset_parcel]
                    service_offset += parcel_data[service]

                    # account for all of the services that parcel provides
                    for _service in services.keys():
                        services[_service]['offset'] += parcel_data[_service]
                    remaining_parcels.remove(offset_parcel)
                    hydro_selected_parcels.add(offset_parcel)
                    selected_parcels.add(offset_parcel)
                    LOGGER.debug('selected parcels: %s', selected_parcels)

    if es_global_req is not None:
        # Determine the service offsets for any parcels we've already selected.
        service_totals = {}
        for service in es_global_req.keys():
            if len(selected_parcels) > 0:
                service_init = 0
            else:
                service_init = sum(map(lambda pid:
                    parcels[pid][service], selected_parcels))
            service_totals[service] = service_init

        available_parcels = set(parcels.keys()).difference(selected_parcels)
        global_es_selected_parcels = set([])
        for service in sorted(es_global_req.keys()):
            # sort available parcels in decreasing order of service offset
            service_sort = lambda pid: parcels[pid][service]
            for parcel_id in sorted(available_parcels, key=service_sort,
                reverse=True):
                amt_required = es_global_req[service] * proportion_offset
                if service_totals[service] >= amt_required:
                    break

                available_parcels.remove(parcel_id)
                global_es_selected_parcels.add(parcel_id)
                for _service in es_global_req.keys():
                    service_totals[_service] += parcels[parcel_id][_service]

        LOGGER.debug('Global selected parcels: %s', global_es_selected_parcels)
        selected_parcels.update(global_es_selected_parcels)

    return sorted(selected_parcels)

def translate_parcel_data(per_offset_data):
    """Translate the per-offset parcel data dictionary returned from
    natcap.opal.analysis.percent_overlap() into the data structures required for
    multifactor parcel selection to take place."""
    output_parcels = {}
    output_ssheds = {}
    known_keys = {
        'Carbon': 'carbon',
        'Nitrogen': 'nutrient',
        'Sediment': 'sediment',
        'Custom': 'custom',
        'Area': 'area',
        'Ecosystem': 'ecosystem',
        'municipalities': 'overlap',
    }
    for parcel_id, parcel_data in per_offset_data.iteritems():
        output_parcel_data = {}
        for old_key, new_key in known_keys.iteritems():
            try:
                value = parcel_data[old_key]
                if new_key == 'area':
                    value = Ha(value)  # convert from m^2 to Ha
                output_parcel_data[new_key] = value
            except KeyError:
                # When old_key isn't in parcel_data
                pass
        output_parcels[parcel_id] = output_parcel_data

    return output_parcels

def translate_es_impacts(per_impact_data, custom_type='global'):
    """Translate the per-impact data dictionary returned from
    natcap.opal.analysis.percent_overlap() into the hydrological ES dictionary.

    Returns one dictionary for hydrological impacts, and another one for global
    impacts."""

    # structure:
    #  'sshed_name': {
    #    'service': required_service_value, ...}
    #
    output_hydro_impacts = {}
    output_global_impacts = {}
    known_keys = {
        'carbon': 'Carbon',
        'nutrient': 'Nitrogen',
        'sediment': 'Sediment',
        'custom': 'Custom',
    }
    services = set(['carbon', 'nutrient', 'sediment', 'custom'])
    for parcel_id, parcel_data in per_impact_data.iteritems():
        for sshed_name, sshed_overlap in parcel_data['municipalities'].iteritems():
            # initialize values if necessary
            if sshed_name not in output_hydro_impacts:
                sshed_services = {}
                for service in services:
                    if known_keys[service] not in parcel_data:
                        continue
                    sshed_services[service] = 0
                output_hydro_impacts[sshed_name] = sshed_services

            for service in services:
                try:
                    # TODO: if sshed_overlap < 1, allocate remaining impact to
                    # global requirements.
                    service_impact = parcel_data[known_keys[service]] * sshed_overlap
                except (KeyError, TypeError):
                    # KeyError when service is not in parcel_data
                    # TypeError when the parcel_data[service] value is None
                    # in all cases, skip it.
                    continue

                if sshed_name not in output_hydro_impacts:
                    output_hydro_impacts[sshed_name] = {}
                output_hydro_impacts[sshed_name][service] += service_impact

    return output_hydro_impacts

def group_offset_parcels_by_sshed(per_offset_data):
    """Return a dictionary mapping string serviceshed identifiers to lists of
    offset parcel IDs representing offset parcels that offset to that
    serviceshed."""
    output_sshed_data = {}
    for parcel_id, parcel_data in per_offset_data.iteritems():
        for sshed_name in parcel_data['municipalities'].keys():
            try:
                output_sshed_data[sshed_name].append(parcel_id)
            except KeyError:
                # if we haven't encountered this sshed name UNTIL NOW
                output_sshed_data[sshed_name] = [parcel_id]

    # now, loop through all the found ssheds and sort the parcel keys
    for sshed_name, offset_parcels in output_sshed_data.iteritems():
        output_sshed_data[sshed_name] = sorted(offset_parcels)

    return output_sshed_data


