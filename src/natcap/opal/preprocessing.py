"""Module for preprocessing operations."""

import os
import logging
import tempfile
import shutil
import json
import glob
import time

from osgeo import ogr
from osgeo import gdal
from osgeo import osr
import shapely
import shapely.ops
import shapely.speedups
import shapely.geos
import shapely.prepared
import shapely.validation
import shapely.geometry
import rtree
import pygeoprocessing

import offsets
import utils


LOGGER = logging.getLogger('natcap.opal.preprocessing')

def rm_shapefile(uri):
    """Delete all files associated with the user-defined ESRI Shapefile.

    uri - a URI to an ESRI shapefile on disk.

    Returns nothing."""
    shapefile_base = os.path.splitext(uri)[0]

    for filename in glob.glob(shapefile_base + '.*'):
        LOGGER.debug('Removing %s', filename)
        os.remove(filename)

def build_spatial_index(vector):
    """Build an rtree spatial index mapping the parcel index to the bounds of
    each polygon in the input vector.  Returns a tuple of (Index, dict), where
    Index is an instance of rtree.index.Index and dict is a python dictionary
    mapping parcel index to shapely polygon of the parcel."""

    utils.assert_files_exist([vector])
    LOGGER.debug('Building spatial index for vector %s', vector)
    parcels_vector = ogr.Open(vector)
    parcels_layer = parcels_vector.GetLayer()

    spatial_index = rtree.index.Index()
    parcel_dict = {}
    for parcel in parcels_layer:
        parcel_index = parcel.GetFID()
        parcel_polygon = offsets.build_shapely_polygon(parcel)
        spatial_index.insert(parcel_index, parcel_polygon.bounds)
        parcel_dict[parcel_index] = parcel_polygon

    return (spatial_index, parcel_dict)

def split_multipolygons(in_vector_uri, out_vector_uri, include_fields=None):
    """Create a new ESRI shapefile with a single layer in it, where this layer
    contains only polygons.  Any multipolygons encountered are split into
    separate polygons.  If the user specifies any string fields via
    include_fields, those fields will be copied over from the old
    polygon/multipolygon to the new feature.

        in_vector_uri - a URI to an OGR vector on disk.  This must contain a
            single layer with polygons and/or multipolygons.
        out_vector_uri - a URI to where the output vector will be saved.  Must
            not exist on disk.
        include_fields=None - Either a list of string fieldnames or None.  If
            None, no fields will be copied.  If a list of string fieldnames,
            only these fields will be copied from the old vector to the new
            one.

        Returns nothing."""

    utils.assert_files_exist([in_vector_uri])
    LOGGER.debug('Opening input vector %s', in_vector_uri)

    in_vector = ogr.Open(in_vector_uri)
    in_layer = in_vector.GetLayer()
    in_layer_srs = in_layer.GetSpatialRef()
    in_layer_defn = in_layer.GetLayerDefn()

    if in_layer.GetFeatureCount() == 0:
        raise ValueError('Vector has no features: %s' % in_vector_uri)

    if os.path.exists(out_vector_uri):
        LOGGER.warning('%s already exists on disk', out_vector_uri)
        rm_shapefile(out_vector_uri)

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

    # create an FID column because I want it for later for aggregating raster
    # stats.
    LOGGER.debug('Creating new field FID')
    fid_field_defn = ogr.FieldDefn('FID', ogr.OFTInteger)
    out_layer.CreateField(fid_field_defn)
    out_layer_defn = out_layer.GetLayerDefn()
    fid_index = out_layer_defn.GetFieldIndex('FID')
    LOGGER.debug('FID index: %s', fid_index)

    if shapely.speedups.available:
        LOGGER.debug('Speedups are available')
        shapely.speedups.enable()
        LOGGER.debug('Speedups enabled')

    polygon_count = 0
    num_invalid = 0
    num_fixed = 0
    polygons = []
    for feature in in_layer:
        index = feature.GetFID()
        feature_defn = feature.GetDefnRef()

        # add the FID column
        feature_defn.AddFieldDefn(fid_field_defn)

        geometry = feature.GetGeometryRef()
        feature_type = geometry.GetGeometryType()

        polygons_in_feature = []
        if feature_type == ogr.wkbMultiPolygon:
            shapely_multipolygon = offsets.build_shapely_polygon(feature)
            multiparts_fixed = 0
            for shapely_geometry in shapely_multipolygon.geoms:
                ogr_geom = ogr.CreateGeometryFromWkb(shapely_geometry.wkb)
                if not ogr_geom.IsValid():
                    ogr_geom = ogr_geom.Buffer(0)
                    if ogr_geom.IsValid():
                        wkb = ogr_geom.ExportToWkb()
                        polygons.append(wkb)
                        polygons_in_feature.append(wkb)
                        num_fixed += 1
                        multiparts_fixed += 1
                    else:
                        num_invalid += 1
                else:
                    polygons.append(shapely_geometry.wkb)
                    polygons_in_feature.append(shapely_geometry.wkb)
            if multiparts_fixed > 0:
                LOGGER.debug('Fixed %s polygons in feature %s',
                    multiparts_fixed, index)
        elif feature_type == ogr.wkbPolygon:
            if not geometry.IsValid():
                LOGGER.warn('Invalid polygon found. Skipping')
                num_invalid += 1
            else:
                polygons.append(geometry.ExportToWkb())
                polygons_in_feature.append(geometry.ExportToWkb())
        else:
            feature_type_label = geometry.ExportToWkt().split()[0]
            raise ValueError(_(
                'Features provided must be polygons, but found '
                '%s instead') % feature_type_label)

        for polygon_wkb in polygons_in_feature:
            # new_geometry = ogr.CreateGeometryFromWkb()
            new_geometry = ogr.CreateGeometryFromWkb(polygon_wkb)
            if new_geometry.IsValid():
                # create feature with geometry
                new_feature = ogr.Feature(feature_defn)
                new_feature.SetGeometry(new_geometry)
                for old_index, new_index in field_indices.iteritems():
                    old_value = feature.GetField(old_index)
                    new_feature.SetField(new_index, old_value)

                # <add field data to feature, as necessary>
                # create the feature in the layer.
                new_feature.SetField('FID', polygon_count)
                out_layer.CreateFeature(new_feature)
                polygon_count += 1
    LOGGER.debug('Fixed %s invalid polygons while processing', num_fixed)
    LOGGER.debug('Found %s invalid polygons.', num_invalid)

    out_layer = None
    ogr.DataSource.__swig_destroy__(out_vector)
    out_vector = None
    out_driver = None
    in_layer_defn = None
    in_layer_srs = None
    in_layer = None
    ogr.DataSource.__swig_destroy__(in_vector)
    in_vector = None

def prepare_aoi(impact_sites_uri, hydro_subzones_uri, out_uri):
    """Create an AOI based on the hydro subzones and impact sites provided.
    The resulting AOI should be a vector containing a single polygon, which is
    the union of all hydro subzones that intersect any impact sites.

    impact_sites_uri - a URI to an OGR vector containing impact sites.
    hydro_subzones_uri - a URI to an OGR vector containing hydrographic
        subzones
    out_uri - a URI to an OGR vector to which the resulting vector will be
        saved.
    """
    LOGGER.debug('Preparing the AOI')
    utils.assert_files_exist([impact_sites_uri, hydro_subzones_uri])

    if os.path.exists(out_uri):
        LOGGER.debug('Cleaning up existing AOI')
        rm_shapefile(out_uri)

    temp_dir = tempfile.mkdtemp()
    intersecting_uri = os.path.join(temp_dir, 'intersecting_subzones.shp')
    LOGGER.debug('Saving intersecting subzones to %s', intersecting_uri)
    locate_intersecting_polygons(hydro_subzones_uri, impact_sites_uri,
        intersecting_uri)

    LOGGER.debug('Taking the union of intersecting subzones')
    union_of_vectors([intersecting_uri], out_uri)
    shutil.rmtree(temp_dir)

def prepare_impact_sites(impact_sites_uri, hydrozones, out_dir):
    """Clip impact sites by hydrozones, storing the resulting zones in out_dir.
    This function will also ensure that any multipolygon impacts are split into
    separate individual polygons.

        impact_sites_uri - a URI to an OGR vector with impact site polygons.
        hydrozones - a URI to an OGR vector with hydrozone polygons.
        out_dir - a URI to an output folder where the split impact sites should
            be stored.

    Returns a list of URIs to new impact site vectors stored within out_dir."""

    utils.assert_files_exist([impact_sites_uri, hydrozones])
    temp_dir = tempfile.mkdtemp()

    split_impacts_uri = os.path.join(temp_dir, 'split_multipolygons.shp')
    LOGGER.debug('Splitting multipolygons')
    split_multipolygons(impact_sites_uri, split_impacts_uri, 'all')

    LOGGER.debug('Splitting impacts into separate vectors by hydrozone')
    split_impact_data = split_impacts(split_impacts_uri, hydrozones, out_dir)

    LOGGER.debug('Removing temp files %s', temp_dir)
    shutil.rmtree(temp_dir)

    return split_impact_data

# assume that the AOI is completely contained within a single hydrozone
def prepare_offset_parcels(parcels_vector, max_search_vector,
        out_vector_uri, previous_offsets=None, previous_impacts=None,
        include_lci=True):
    """Prepare offset parcels.  This function takes in a vector of parcels and
    a max search area and writes out an OGR vector to out_vector_uri.

    This function:
        - Splits any multipolygons found in parcels_vector, writing out the
          results to a temporary vector.
        - Calculates the LCI for all parcels found within the max_search_vector
        - If previous_offsets or previous_impacts are included, they are cut
          out from the available parcels.
        - Restrict the set of output polygons to only those found in the max
          seach vector.

    Parameters:
        parcels_vector - an OGR vector of polygons and/or multipolygons.
        max_search_vector - an OGR vector with a single polygon.  Any polygons
            found in parcels_vector that are not in the max_search_vector are
            excluded.
        out_vector_uri - the URI to which the output vector should be written.
        previous_offsets - an OGR vector of polygons/multipolygons
        previous_impacts - an OGR vector of polygons/multipolygons
        include_lci=True - a boolean.  If False, LCI calculations will be
            skipped.

    Returns nothing.
    """

    utils.assert_files_exist([parcels_vector, max_search_vector])
    #temp_dir = pygeoprocessing.temporary_folder()
    temp_dir = tempfile.mkdtemp()

    # copy the impact site datasource so I can edit.
    LOGGER.debug('Splitting multipolygons')
    mp_split_uri = os.path.join(temp_dir, 'mp_split.shp')
    LOGGER.debug('Writing temp vector to %s', mp_split_uri)
    split_multipolygons(parcels_vector, mp_split_uri, 'all')

    if include_lci:
        # locate the parcels we'll use for calculating the LCI
        # This also restricts the number of parcels to be slightly more than just
        # those that intersect with the search vector.
        lci_parcels = os.path.join(temp_dir, 'lci_parcels.shp')
        _locate_lci_parcels(mp_split_uri, max_search_vector, 500, lci_parcels)
        prepared_parcels_uri = lci_parcels
    else:
        prepared_parcels_uri = mp_split_uri

    if previous_offsets is not None:
        LOGGER.info('Subtracting previous offsets from offset parcels')
        temp_prev_offsets = os.path.join(temp_dir, 'diff_prev_offsets.shp')
        subtract_vectors(prepared_parcels_uri, previous_offsets,
            temp_prev_offsets)
        prepared_parcels_uri = temp_prev_offsets

    if previous_impacts is not None:
        LOGGER.info('Subtracting previous impacts from offset parcels')
        temp_prev_impacts = os.path.join(temp_dir, 'diff_prev_impacts.shp')
        subtract_vectors(prepared_parcels_uri, previous_impacts,
            temp_prev_impacts)
        prepared_parcels_uri = temp_prev_impacts

    if include_lci:
        # Calculate the LCI based on the located parcels with the previous offsets
        # and previous impacts removed.
        calculated_lci = os.path.join(temp_dir, 'calculated_lci.shp')
        LOGGER.info('Calculating LCI: %s', calculated_lci)
        calculate_lci(prepared_parcels_uri, calculated_lci)

        # Now that we've calculated the LCI, restore the set of polygons to only
        # those that intersect the search area.  This discards any other polygons
        # that are completely outside the search area that we needed for
        # calculating the LCI.
        LOGGER.info('Limiting parcels to only intersecting the search area')
        locate_intersecting_polygons(calculated_lci, max_search_vector,
            out_vector_uri)
    else:
        locate_intersecting_polygons(prepared_parcels_uri, max_search_vector,
            out_vector_uri)

    LOGGER.debug('Cleaning up temp folder %s', temp_dir)
    shutil.rmtree(temp_dir)

#    # now, aggregate over the correct polygons.
#    LOGGER.debug('Aggregating offsets')
#    for service_name, impact_raster in services:
#        field_name = "%s_sum" % service_name
#        aggregate_stats(impact_raster, out_vector_uri, 'FID', field_name)

def _locate_lci_parcels(parcels_vector_uri, max_search_vector, buffer, out_vector):
    """Locate all parcels required for the correct calculation of the Landscape
    Context Index.  This function selects all parcels within buffer distance
    from any parcels intersecting wth the max_search_vector.  Selected parcels
    are written to the out_vector uri.

        parcels_vector_uri - an OGR vector from which we select parcels.
        max_search_vector - an OGR vector.
        buffer - a python int or float.  This is the buffer distance.
        out_vector - a URI to an OGR vector on disk.

    This function returns nothing."""

    utils.assert_files_exist([parcels_vector_uri, max_search_vector])
    temp_dir = tempfile.mkdtemp()

    # get the set of all parcels that intersect with the max_search_vector.
    LOGGER.debug('Locating parcels intersecting search area')
    parcels_in_ssa = os.path.join(temp_dir, 'intersect_ssa.shp')
    locate_intersecting_polygons(parcels_vector_uri, max_search_vector,
        parcels_in_ssa)

    # Take the cascaded union of all the parcels that intersect with the
    #   max_search_vector and all parcels in the max_search_vector.
    LOGGER.debug('Taking union of parcels outside search area and search area')
    parcels_union_ssa = os.path.join(temp_dir, 'ssa_union_parcels.shp')
    union_of_vectors([parcels_in_ssa, max_search_vector], parcels_union_ssa)

    # Buffer the new max_search_vector by 500m.
    LOGGER.debug('Buffering max search vector')
    buffered_search_area = os.path.join(temp_dir, 'buffered_ssa.shp')
    buffer_vector(parcels_union_ssa, 500, buffered_search_area)

    # get all the parcels that intersect with the buffered max search area.
    # create a new vector based on the max_search vector.
    # Write these parcels to the output vector.
    # we'll use these output parcels as the possible parcels from which to
    # calculate the LCI.
    LOGGER.debug('Locating intersecting polygons near search vector')
    locate_intersecting_polygons(parcels_vector_uri, buffered_search_area,
        out_vector)



def buffer_vector(in_vector_uri, buffer_dist, out_vector_uri):
    """Buffer all features in the input vector by the specified distance.

        in_vector_uri - a URI to an OGR vector.
        buffer_dist - a numeric buffer distance, in the units of the layer.
        out_vector_uri - a URI to an output OGR vector to which all output
        geometry will saved.

    This function returns nothing."""

    utils.assert_files_exist([in_vector_uri])
    LOGGER.debug('Opening input vector %s', os.path.abspath(in_vector_uri))
    in_vector = ogr.Open(in_vector_uri)
    in_layer = in_vector.GetLayer()
    in_layer_srs = in_layer.GetSpatialRef()
    in_layer_defn = in_layer.GetLayerDefn()

    if os.path.exists(out_vector_uri):
        LOGGER.debug('Removing preexisting output vector: %s', out_vector_uri)
        rm_shapefile(out_vector_uri)

    LOGGER.debug('Creating buffered vector at %s',
            os.path.abspath(out_vector_uri))
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = out_driver.CreateDataSource(out_vector_uri)
    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    out_layer = out_vector.CreateLayer(layer_name, srs=in_layer_srs)
    LOGGER.debug('New layer name: %s', layer_name)

    # create all the same fields in the output vector
    field_indices = {}
    for field_index in xrange(in_layer_defn.GetFieldCount()):
        # get the old field definition, create a new field in the new layer
        old_field_defn = in_layer_defn.GetFieldDefn(field_index)
        out_layer.CreateField(old_field_defn)
        field_name = old_field_defn.GetName()
        out_layer_defn = out_layer.GetLayerDefn()
        out_field_index = out_layer_defn.GetFieldIndex(field_name)
        field_indices[field_index] = out_field_index

    num_features = in_layer.GetFeatureCount()
    LOGGER.debug('Buffering %s features by %s', num_features, buffer_dist)
    #for feature_index in xrange(num_features):
    for old_feature in in_layer:
        #print old_feature
        #old_feature = in_layer.GetFeature(feature_index)
        old_geom = old_feature.GetGeometryRef()
        #print old_geom
        geometry = old_geom.Buffer(buffer_dist)
        #feature = offsets.build_shapely_polygon(old_feature)
        #buffered_feature = feature.buffer(buffer_dist)
        #geometry = ogr.CreateGeometryFromWkb(buffered_feature.wkb)

        new_feature = ogr.Feature(in_layer_defn)
        new_feature.SetGeometry(geometry)

        for old_index, new_index in field_indices.iteritems():
            old_value = old_feature.GetField(old_index)
            new_feature.SetField(new_index, old_value)

        out_layer.CreateFeature(new_feature)

    ogr.DataSource.__swig_destroy__(in_vector)
    ogr.DataSource.__swig_destroy__(out_vector)
    in_vector = None
    out_vector = None

def locate_intersecting_polygons(source_vector_uri, comparison_vector_uri,
        out_vector_uri, clip=False):
    """ Locate all polygons in source_vector_uri that intersect with any polygons
    in comparison_vector_uri.  If any intersecting polygons are found, the
    geometry, fields and field values are all copied to the output vector.

        source_vector_uri - a URI to an OGR vector on disk containing
            polygons.
        comparison_vector_uri - a URI to an OGR vector on disk containing polygons.
        out_vector_uri - a URI to where the output OGR vector should be saved.
            This file must not already exist on disk.
        clip - a boolean to indicate whether the output geometry should be
            clipped to the comparison vector.

    Returns nothing."""

    utils.assert_files_exist([source_vector_uri, comparison_vector_uri])
    utils.assert_ogr_projections_equal([source_vector_uri,
        comparison_vector_uri])
    out_driver = ogr.GetDriverByName('ESRI Shapefile')

    LOGGER.debug('Opening input vector %s', os.path.abspath(source_vector_uri))
    in_vector = ogr.Open(source_vector_uri)
    in_layer = in_vector.GetLayer()
    in_layer_srs = in_layer.GetSpatialRef()
    in_layer_defn = in_layer.GetLayerDefn()

    # extracting AOI vector and translating to shapely polygon.
    LOGGER.debug('Opening impact vector %s',
            os.path.abspath(comparison_vector_uri))
    impact_vector = ogr.Open(comparison_vector_uri)
    impact_layer = impact_vector.GetLayer()
#    impact_features = [offsets.build_shapely_polygon(impact_layer.GetFeature(fid))
#            for fid in xrange(impact_layer.GetFeatureCount())]

    impact_features = []
    for impact_feature in impact_layer:
        try:
            feat = offsets.build_shapely_polygon(impact_feature)
            impact_features.append(feat)
        except shapely.geos.ReadingError:
            fid = impact_feature.GetFID()
            LOGGER.debug('Feature %s has invalid geometry: "%s"', fid,
                shapely.validation.explain_validity())

    if os.path.exists(out_vector_uri):
        rm_shapefile(out_vector_uri)

    LOGGER.debug('Creating a new vector at %s', out_vector_uri)
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = out_driver.CreateDataSource(out_vector_uri)
    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    out_layer = out_vector.CreateLayer(layer_name, srs=in_layer_srs)

    # create all the same fields in the output vector
    field_indices = {}
    for field_index in xrange(in_layer_defn.GetFieldCount()):
        # get the old field definition, create a new field in the new layer
        old_field_defn = in_layer_defn.GetFieldDefn(field_index)
        out_layer.CreateField(old_field_defn)
        field_name = old_field_defn.GetName()
        out_layer_defn = out_layer.GetLayerDefn()
        out_field_index = out_layer_defn.GetFieldIndex(field_name)
        field_indices[field_index] = out_field_index

    LOGGER.debug('Locating intersecting polygons')
    found_features = {}
    last_time = time.time()
    num_features = 0
    for feature in in_layer:
        index = feature.GetFID()
        feature_defn = feature.GetDefnRef()
        geometry = feature.GetGeometryRef()
        num_features += 1

        try:
            polygon = offsets.build_shapely_polygon(feature)
            skip = False
        except shapely.geos.ReadingError:
            try:
                polygon = offsets.build_shapely_polygon(feature, fix=True)
            except shapely.geos.ReadingError:
                skip = True

        prep_polygon = shapely.prepared.prep(polygon)

        if not skip:
            if not clip:
                for impact_site in impact_features:
                    if index not in found_features:
                        if prep_polygon.intersects(impact_site):
                            if polygon.intersection(impact_site).area > 0:
                                found_features[index] = [polygon.wkb]
            else:
                for impact_site in impact_features:
                    if prep_polygon.intersects(impact_site):
                        intersection = polygon.intersection(impact_site)
                        if intersection.area > 0:
                            try:
                                found_features[index].append(intersection.wkb)
                            except KeyError:
                                found_features[index] = [intersection.wkb]
        else:
            LOGGER.warn('Feature %s is invalid and could not be fixed.', index)

        current_time = time.time()
        if (current_time - last_time) > 5.:
            last_time = current_time
            percent_complete = round((float(num_features) /
                                      in_layer.GetFeatureCount()) * 100, 2)
            LOGGER.info('Locating polygons %s%% complete', percent_complete)

    LOGGER.info('Locating polygons %s%% complete', 100)

    last_time = time.time()
    LOGGER.debug('Creating %s new geometries', len(found_features))
    for index, binary_geometries in found_features.iteritems():
        old_feature = in_layer.GetFeature(index)
        for binary_geometry in binary_geometries:
            new_geometry = ogr.CreateGeometryFromWkb(binary_geometry)
            new_feature = ogr.Feature(feature_defn)
            new_feature.SetGeometry(new_geometry)

            for old_index, new_index in field_indices.iteritems():
                old_value = old_feature.GetField(old_index)
                new_feature.SetField(new_index, old_value)

            out_layer.CreateFeature(new_feature)

            # Sometimes, this progress logging show up and I have no idea why
            # it doesn't.  Need to debug later.
            # https://bitbucket.org/natcap/opal/issues/3371
            current_time = time.time()
            if (current_time - last_time) > 5.:
                last_time = current_time
                percent_complete = round((float(num_features) /
                                        in_layer.GetFeatureCount()) * 100, 2)
                LOGGER.info('Creating geometries %s%% complete', percent_complete)
            print "%s %s" % (current_time, last_time)

    LOGGER.debug('Creating geometries 100%% complete')
    out_vector.SyncToDisk()

    ogr.DataSource.__swig_destroy__(in_vector)
    ogr.DataSource.__swig_destroy__(out_vector)

def union_of_vectors(input_vector_uris, out_vector_uri):
    """Find the union of all features in the provided input vectors and write
    them out to a single geometry in out_vector_uri.  All vectors are assumed
    to be in the same projection.

        input_vector_uris - a list of python string URIs to OGR vectors on disk
        out_vector_uri - a python string URI.  The output OGR vector will be
            written to this location.

    Returns nothing."""

    utils.assert_files_exist(input_vector_uris)
    source_vector_uri = input_vector_uris[0]
    LOGGER.debug('Opening input vector[0] %s', os.path.abspath(source_vector_uri))
    in_vector = ogr.Open(source_vector_uri)
    in_layer = in_vector.GetLayer()
    in_layer_srs = in_layer.GetSpatialRef()

    if os.path.exists(out_vector_uri):
        rm_shapefile(out_vector_uri)

    LOGGER.debug('Creating a new vector at %s', out_vector_uri)
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = out_driver.CreateDataSource(out_vector_uri)
    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    new_srs = osr.SpatialReference(wkt=in_layer_srs.ExportToWkt())
    out_layer = out_vector.CreateLayer(layer_name, new_srs, ogr.wkbPolygon)
    ogr.DataSource.__swig_destroy__(in_vector)

    LOGGER.debug('Building shapely geometries')
    all_features = []

    for in_vector in input_vector_uris:
        LOGGER.debug('Processing %s', in_vector)
        vector = ogr.Open(in_vector)
        layer = vector.GetLayer()

        for feature in layer:
            polygon = offsets.build_shapely_polygon(feature)
            all_features.append(polygon)

        # clean up the input vector.
        ogr.DataSource.__swig_destroy__(vector)

    sorted_features = sorted(all_features, key=lambda x: x.area, reverse=True)

    biggest_feature = sorted_features[0]
    features_to_test = sorted_features[1:]

    union_features = [biggest_feature]
    for feature in features_to_test:
        if biggest_feature.contains(feature):
            continue
        else:
            union_features.append(feature)

    LOGGER.debug('Taking union of %s features', len(union_features))
    biggest_feature = shapely.ops.cascaded_union(union_features)

    union_polygon = biggest_feature

#    LOGGER.debug('Taking the union of %s features', len(all_features))
#    union_polygon = shapely.ops.cascaded_union(all_features)
#    print union_polygon.wkt
#    union_polygon = shapely.geometry.MultiPolygon(union_polygon)
#    print union_polygon.wkt
    LOGGER.debug('Creating new feature from empty definition')
    new_feature = ogr.Feature(ogr.FeatureDefn())
    new_geometry = ogr.CreateGeometryFromWkb(union_polygon.wkb)
    LOGGER.debug('Setting geometry from union_polygon with len(wkt)=%s',
        len(union_polygon.wkt))
    new_feature.SetGeometry(new_geometry)

    LOGGER.debug('Creating new feature')
    out_layer.CreateFeature(new_feature)

    LOGGER.debug('Cleaning up')
    new_feature = None
    out_layer = None
    out_vector = None
    out_driver = None
    LOGGER.debug('Finished cleanup of new vector')

def subtract_vectors(minuend_uri, subtrahend_uri, difference_uri):
    """Subtract the subtrahend vector from the minuend vector, writing the
    output geometries tothe difference vector.

        minuend_uri - a URI to an OGR vector on disk.
        subtrahend_uri - a URI to an OGR vector on disk.
        difference_uri - a URI to where the difference vector should be saved
            This file must not already exist on disk.

    Returns nothing."""

    utils.assert_files_exist([minuend_uri, subtrahend_uri])
    LOGGER.debug('Opening minuend %s', os.path.abspath(minuend_uri))
    minuend_vector = ogr.Open(minuend_uri)
    minuend_layer = minuend_vector.GetLayer()
    minuend_layer_srs = minuend_layer.GetSpatialRef()
    minuend_layer_defn = minuend_layer.GetLayerDefn()

    LOGGER.debug('Opening subtrahend %s', os.path.abspath(subtrahend_uri))
    subtrahend_vector = ogr.Open(subtrahend_uri)
    subtrahend_layer = subtrahend_vector.GetLayer()

    if os.path.exists(difference_uri):
        rm_shapefile(difference_uri)

    LOGGER.debug('Creating difference vector at %s', difference_uri)
    difference_driver = ogr.GetDriverByName('ESRI Shapefile')
    difference_vector = difference_driver.CreateDataSource(difference_uri)
    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(difference_uri)[0]))
    difference_layer = difference_vector.CreateLayer(layer_name,
        srs=minuend_layer_srs)

    # create all the same fields in the output vector
    field_indices = {}
    for field_index in xrange(minuend_layer_defn.GetFieldCount()):
        # get the old field definition, create a new field in the new layer
        old_field_defn = minuend_layer_defn.GetFieldDefn(field_index)
        difference_layer.CreateField(old_field_defn)
        field_name = old_field_defn.GetName()
        difference_layer_defn = difference_layer.GetLayerDefn()
        difference_field_index = difference_layer_defn.GetFieldIndex(field_name)
        field_indices[field_index] = difference_field_index

    LOGGER.debug('Field map: %s', field_indices)

    for minuend_feature in minuend_layer:
        minuend_polygon = offsets.build_shapely_polygon(minuend_feature)
        minuend_defn = minuend_feature.GetDefnRef()

        for subtrahend_feature in subtrahend_layer:
            subtrahend_polygon = offsets.build_shapely_polygon(subtrahend_feature)
            if minuend_polygon.intersects(subtrahend_polygon):
                minuend_polygon = minuend_polygon.difference(subtrahend_polygon)

        subtrahend_layer.ResetReading()

        if minuend_polygon.area > 0:
            new_feature = ogr.Feature(minuend_defn)
            new_geometry = ogr.CreateGeometryFromWkb(minuend_polygon.wkb)
            new_feature.SetGeometry(new_geometry)

            for old_index, new_index in field_indices.iteritems():
                old_value = minuend_feature.GetField(old_index)
                new_feature.SetField(new_index, old_value)

            difference_layer.CreateFeature(new_feature)
        else:
            fid = minuend_feature.GetFID()
            LOGGER.debug('Difference removed feature %s', fid)
    ogr.DataSource.__swig_destroy__(minuend_vector)
    ogr.DataSource.__swig_destroy__(subtrahend_vector)
    ogr.DataSource.__swig_destroy__(difference_vector)

def calculate_lci(natural_parcels_uri, output_uri):
    utils.assert_files_exist([natural_parcels_uri])
    LOGGER.debug('Opening the natural parcels vector %s', natural_parcels_uri)
    parcels_vector = ogr.Open(natural_parcels_uri)
    parcels_layer = parcels_vector.GetLayer()
    parcels_defn = parcels_layer.GetLayerDefn()
    parcels_srs = parcels_layer.GetSpatialRef()

    if os.path.exists(output_uri):
        rm_shapefile(output_uri)

    LOGGER.debug('Creating LCI vector at %s', output_uri)
    output_driver = ogr.GetDriverByName('ESRI Shapefile')
    output_vector = output_driver.CreateDataSource(output_uri)
    # Cast to str here because the ESRI shapefile expects it.
    layer_name = str(os.path.basename(os.path.splitext(output_uri)[0]))
    output_layer = output_vector.CreateLayer(layer_name,
        srs=parcels_srs)

    LOGGER.debug('Creating new field LCI')
    lci_field_defn = ogr.FieldDefn('LCI', ogr.OFTReal)
    output_layer.CreateField(lci_field_defn)
    output_layer_defn = output_layer.GetLayerDefn()
    lci_index = output_layer_defn.GetFieldIndex('LCI')
    LOGGER.debug('LCI field index: %s', lci_index)

    # create all the same fields in the output vector
    field_indices = {}
    for field_index in xrange(parcels_defn.GetFieldCount()):
        # get the old field definition, create a new field in the new layer
        old_field_defn = parcels_defn.GetFieldDefn(field_index)
        output_layer.CreateField(old_field_defn)
        field_name = old_field_defn.GetName()
        output_layer_defn = output_layer.GetLayerDefn()
        output_field_index = output_layer_defn.GetFieldIndex(field_name)
        field_indices[field_index] = output_field_index
        LOGGER.debug('Old field: %s|%s, new field: %s type:%s', field_name,
            field_index, output_field_index, old_field_defn.GetType())

    LOGGER.debug('Field map: %s', field_indices)

    if shapely.speedups.available:
        LOGGER.debug('Enabling shapely speedups')
        shapely.speedups.enable()

    LOGGER.debug('Preprocessing all parcels')
    parcel_dict = {}
    spat_index = rtree.index.Index()
    for parcel_index in xrange(parcels_layer.GetFeatureCount()):
        parcel_feature = parcels_layer.GetFeature(parcel_index)
        parcel_polygon = offsets.build_shapely_polygon(parcel_feature)
        spat_index.insert(parcel_index, parcel_polygon.bounds)
        parcel_dict[parcel_index] = parcel_polygon

    LOGGER.debug('Locating nearby parcels')
    lci_dict = {}
    index = 0
    num_parcels = len(parcel_dict)
    for parcel_index, parcel_polygon in parcel_dict.iteritems():
        minx, miny, maxx, maxy = parcel_polygon.bounds
        minx -= 500
        miny -= 500
        maxx += 500
        maxy += 500

        nearby_indices = spat_index.intersection((minx, miny, maxx, maxy))
        nearby_polygons = [parcel_dict[n_index] for n_index in nearby_indices]

        num_nearby_polygons = len(nearby_polygons)
        LOGGER.debug('Parcel %s of %s, %s nearby', parcel_index, num_parcels,
            num_nearby_polygons)
        if num_nearby_polygons > 0:
            lci = calculate_parcel_lci(parcel_polygon, nearby_polygons)
            lci_dict[index] = lci
        index += 1

        # create the feature in the output vector.
        old_feature = parcels_layer.GetFeature(parcel_index)
        new_feature = ogr.Feature(output_layer_defn)
        new_geometry = ogr.CreateGeometryFromWkb(parcel_polygon.wkb)
        new_feature.SetGeometry(new_geometry)
        new_feature.SetField('LCI', lci)

        for old_index, new_index in field_indices.iteritems():
            old_value = old_feature.GetField(old_index)
            new_feature.SetField(new_index, old_value)

        output_layer.CreateFeature(new_feature)
        new_feature = None
        old_feature = None
    LOGGER.info('Cleaning up from LCI calculations')
    parcels_vector = None
    output_layer.SyncToDisk()
    output_layer = None
    output_vector = None
    output_driver = None
    spat_index = None
    LOGGER.info('Finished calculating LCI')


def calculate_parcel_lci(parcel, nearby_polygons):
    """Calculate the landscape context index of a parcel given polygons that
    are in the neighborhood of the input parcel.  A polygon will be included
    in the LCI calculations if it's within 500m of the parcel.

        parcel - a shapely polygon.
        nearby_polygons - a list of shapely polygons to consider.

    Returns a float value of the Landscape Context Index (LCI)"""
    buffer_geom = parcel.buffer(500).difference(parcel)
    buffer_orig_area = buffer_geom.area

    try:
        for polygon in nearby_polygons:
            buffer_geom = buffer_geom.difference(polygon)
        buffer_difference_area = buffer_geom.area
    except shapely.geos.TopologicalError as error:
        # happens when there's nothing left to take away.
        LOGGER.warn('"%s"', error)
        LOGGER.debug('Using the original buffer area %s', buffer_orig_area)
        buffer_difference_area = buffer_orig_area

    if buffer_difference_area == 0.:
        return 0.
    return 1 - (buffer_difference_area / buffer_orig_area)

def recompress_gtiff(in_uri, out_uri, compression='NONE', callback=None):
    utils.assert_files_exist([in_uri])
    base_raster = gdal.Open(in_uri)
    driver = gdal.GetDriverByName('GTiff')

    if callback is None:
        callback = lambda x, y, z: None

    driver.CreateCopy(out_uri.encode('utf-8'), base_raster, True,
            ['COMPRESS=%s' % compression], callback=callback)

def raster_extents_to_vector(raster_uri, out_vector_uri):
    """Build a vector with 1 polygon that represents the raster's bounding box.

        raster_uri - a URI to a GDAL raster from which our output vector should
            be created
        sample_vector_uri - a URI to an OGR datasource that we will write on
            disk.  This output vector will be an ESRI Shapefile format.

        Returns Nothing."""

    raster = gdal.Open(raster_uri)
    raster_projection = raster.GetProjection()
    LOGGER.debug('Projection WKT=%s', raster_projection)
    raster_srs = osr.SpatialReference(wkt=raster_projection)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = driver.CreateDataSource(out_vector_uri)
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    out_layer = out_vector.CreateLayer(layer_name, srs=raster_srs)

    raster = gdal.Open(raster_uri)
    # feature extent = xmin, xmax, ymin, ymax
    gt = raster.GetGeoTransform()

    bounding_box = [
            gt[0],
            gt[0] + gt[1] * raster.RasterXSize,
            gt[3],
            gt[3] + gt[5] * raster.RasterYSize]
    xmin = bounding_box[0]
    xmax = bounding_box[1]
    ymin = bounding_box[2]
    ymax = bounding_box[3]

    poly_ring = ogr.Geometry(type=ogr.wkbLinearRing)

    # make a polygon for the bounding box
    poly_ring.AddPoint(xmin, ymin)
    poly_ring.AddPoint(xmin, ymax)
    poly_ring.AddPoint(xmax, ymax)
    poly_ring.AddPoint(xmax, ymin)
    poly_ring.AddPoint(xmin, ymin)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(poly_ring)

    feature = ogr.Feature(out_layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    out_layer.CreateFeature(feature)
    out_vector.SyncToDisk()

    ogr.DataSource.__swig_destroy__(out_vector)
    gdal.Dataset.__swig_destroy__(raster)
    feature = None
    out_layer = None
    out_vector = None

def filter_by_raster(raster_uri, sample_vector_uri, out_vector_uri, clip=False):
    """Locate polygons that intersect the bounding box of the input raster.

        raster_uri - a URI to a GDAL raster.
        sample_vector_uri - a URI to an OGR vector from which to query
            polygons.
        out_vector_uri - a URI to an OGR vector to which to save the located
            features.
        clip=False - whether to clip intersecting polygons to the bounding box.
        """
    utils.assert_files_exist([raster_uri, sample_vector_uri])

    temp_dir = tempfile.mkdtemp()
    bounding_box_uri = os.path.join(temp_dir, 'bbox.shp')

    raster_extents_to_vector(raster_uri, bounding_box_uri)

    # Now find all the polygons
    locate_intersecting_polygons(sample_vector_uri,
        bounding_box_uri, out_vector_uri, clip)

def split_impacts(impacts_vector_uri, zones_vector_uri, workspace, fieldname='fid'):
    """Split the impacts vector by the zones provided, saving the output
    geometries to the workspace.

    impacts_vector_uri = an OGR vector to be split
    zones_vector_uri = an OGR vector
    workspace = the folder to where the output vectors should be saved.

    Returns a list of dictionaries, one dictionary per new impact vector.  Each
    dictionary contains information about the impact vector."""

    utils.assert_files_exist([impacts_vector_uri, zones_vector_uri])

    if not os.path.exists(workspace):
        os.makedirs(workspace)

    impacts_vector = ogr.Open(impacts_vector_uri)
    impacts_layer = impacts_vector.GetLayer()
    impacts = dict((f.GetFID(), offsets.build_shapely_polygon(f)) for f in
        impacts_layer)

    # get the fields that should be created in the output impact vector.
    field_definitions = impacts_layer.schema

    # build up an index of impact polygons that we can query later on.
    LOGGER.debug('Building spatial index of impacts polygons')
    impacts_index = rtree.index.Index()
    for impact_fid, impact_polygon in impacts.iteritems():
        impacts_index.insert(impact_fid, impact_polygon.bounds)

    zones_vector = ogr.Open(zones_vector_uri)
    zones_layer = zones_vector.GetLayer()
    zones_layer_srs = zones_layer.GetSpatialRef()
    out_driver = ogr.GetDriverByName('ESRI Shapefile')

    # Keep track of per-hydrozone data so we can return this later on.
    output_data = []

    LOGGER.debug('Checking for intersections')
    for zone in zones_layer:
        zone_polygon = offsets.build_shapely_polygon(zone)
        impacts_in_zone = impacts_index.intersection(zone_polygon.bounds)

        # impacts_in_zone is a generator, so we can't just check the length of
        # it to see if there are any intersecting parcels.
        intersecting_impacts = []
        for impact_index in impacts_in_zone:
            impact_polygon = impacts[impact_index]
            intersection = impact_polygon.intersection(zone_polygon)
            if intersection.area == 0.0:
                continue
            else:
                intersecting_impacts.append((impact_index, intersection))

        if len(intersecting_impacts) > 0:
            # hydrozone name might not be ASCII.
            hydrozone_name = zone.GetField('zone')
            try:
                # if hydrozone_name is ASCII, it'll decode to ASCII.
                decoded_zone_name = hydrozone_name.decode('ascii')
            except UnicodeDecodeError:
                # Thrown when hydrozone_name contains characters that are not
                # ASCII.  If this happens, let's assume that we want the
                # characters to be UTF-8.  This should detect latin-1 (as will
                # be likely since we're probably mostly dealing with Windows
                # users) and convert to UTF-8.
                decoded_zone_name = hydrozone_name.decode('utf-8')

                # we also want to decode the workspace so that an os.path.join
                # should work as expected.
                workspace = workspace.decode('utf-8')

            hzone_impacts_uri = os.path.join(workspace, u'impacts_%s.shp' %
                decoded_zone_name)
            layer_name = os.path.basename(os.path.splitext(hzone_impacts_uri)[0])
            layer_name = layer_name.encode('utf-8')

            LOGGER.debug('Saving %s parcels to %s', len(intersecting_impacts),
                hzone_impacts_uri)

            if os.path.exists(hzone_impacts_uri):
                rm_shapefile(hzone_impacts_uri)

            out_vector = out_driver.CreateDataSource(hzone_impacts_uri)
            out_layer = out_vector.CreateLayer(layer_name, srs=zones_layer_srs)

            for field_defn in field_definitions:
                out_layer.CreateField(field_defn)

            for impact_index, intersection_polygon in intersecting_impacts:
                new_geometry = ogr.CreateGeometryFromWkb(intersection_polygon.wkb)
                new_feature = ogr.Feature(impacts_layer.GetLayerDefn())
                new_feature.SetGeometry(new_geometry)

                impact_ogr_feature = impacts_layer.GetFeature(impact_index)
                for field_name, field_value in impact_ogr_feature.items().iteritems():
                    new_feature.SetField(field_name, field_value)

                out_layer.CreateFeature(new_feature)

            output_data.append({
                'name': hydrozone_name,
                'fields': map(lambda f: f.GetName(), out_layer.schema),
                'layer_name': layer_name,
                'zone_fid': zone.GetFID(),
                'uri': hzone_impacts_uri,
                'num_impacts': len(intersecting_impacts),
            })
    json_file_uri = os.path.join(workspace, 'new_vectors.json')
    LOGGER.debug('Saving impact data to %s', json_file_uri)
    json.dump(output_data, open(json_file_uri, 'w'), sort_keys=True,
        indent=4)

    ogr.DataSource.__swig_destroy__(impacts_vector)
    ogr.DataSource.__swig_destroy__(zones_vector)
    impacts_layer = None
    zones_layer = None
    zones_layer_srs = None
    impacts_vector = None
    zones_vector = None

    return output_data

def union_by_attribute(in_vector_uri, attr_name, out_vector_uri):
    """Take the union of all geometries in the OGR vector at in_vector_uri
    where the value of the column named `attr_name` matches.  Writes the output
    geometries to out_vector_uri.

        in_vector_uri - a URI to an OGR vector on disk.
        attr_name - the string name of an attribute to join using.
        out_vector_uri - the URI to where the output vector should be written.

    Returns a dict mapping the value of attr_name from the hydrozone to the
    a list of feature IDs of the subzones that make up the hydrozone."""

    LOGGER.debug('Taking the union of %s by attribute %s', in_vector_uri,
        attr_name)
    in_vector = ogr.Open(in_vector_uri)
    in_layer = in_vector.GetLayer()
    in_srs = in_layer.GetSpatialRef()
    in_fields = dict((d.GetName(), d.GetType()) for d in in_layer.schema)

    attributes = {}
    for feature in in_layer:
        feature_id = feature.GetFID()
        attribute_value = feature.GetField(attr_name)
        try:
            attributes[attribute_value].append(feature_id)
        except KeyError:
            attributes[attribute_value] = [feature_id]

    LOGGER.debug('Found %s attribute(s) to aggregate by.', len(attributes))
    out_driver = ogr.GetDriverByName('ESRI Shapefile')

    LOGGER.debug('Creating out vector at %s', out_vector_uri)
    if os.path.exists(out_vector_uri):
        rm_shapefile(out_vector_uri)

    out_vector = out_driver.CreateDataSource(out_vector_uri)
    layer_name = str(os.path.basename(os.path.splitext(out_vector_uri)[0]))
    out_layer = out_vector.CreateLayer(layer_name, srs=in_srs)
    #TODO: create a feature for the attribute

    # create the target attribute.
    field_defn = ogr.FieldDefn(attr_name, in_fields[attr_name])
    out_layer.CreateField(field_defn)
    out_layer_defn = out_layer.GetLayerDefn()

    for name, feature_list in attributes.iteritems():
        LOGGER.debug('%s:%s has %s features: %s', attr_name, name,
            len(feature_list), feature_list)
        polygon_list = []
        for feature_id in feature_list:
            feature = in_layer.GetFeature(feature_id)
            polygon_list.append(offsets.build_shapely_polygon(feature))

        union = shapely.ops.cascaded_union(polygon_list)

        new_feature = ogr.Feature(out_layer_defn)
        new_geometry = ogr.CreateGeometryFromWkb(union.wkb)
        new_feature.SetGeometry(new_geometry)
        new_feature.SetField(attr_name, name)
        out_layer.CreateFeature(new_feature)

    ogr.DataSource.__swig_destroy__(in_vector)
    ogr.DataSource.__swig_destroy__(out_vector)
    in_layer = None
    out_layer = None
    in_vector = None
    out_vector = None

    LOGGER.debug('Finished taking union by attribute')
    return attributes

def union_of_raster_extents(rasters_list, out_vector_uri):
    """Build a vector of the union of a set of raster extents.  The resulting
    vector will have a single polygon.

        rasters_list - a list of GDAL rasters that must exist on disk.
        out_vector_uri - a URI to where the output vector should be written on
            disk.

    Returns nothing."""
    utils.assert_files_exist(rasters_list)

    temp_dir = tempfile.mkdtemp()
    bbox_vectors = []
    for index, raster_uri in enumerate(rasters_list):
        bbox_uri = os.path.join(temp_dir, '%s.shp' % index)
        bbox_vectors.append(bbox_uri)
        raster_extents_to_vector(raster_uri, bbox_uri)

    LOGGER.debug('Fetching union of vectors intersecting bounding box')
    union_of_vectors(bbox_vectors, out_vector_uri)

def impacts_in_static_maps(static_maps_list, impacts_uri):
    """Check to see if all impact polygons are inside the union of all extents
    of the static maps.
        static_maps_list - a list of URIs to GDAL rasters on disk
        impacts_uri - a URI to an OGR object on disk.

    Returns a boolean.  True if all impact polygons are within the raster
    extents, False if not."""

    temp_dir = tempfile.mkdtemp()
    raster_extents_vector = os.path.join(temp_dir, 'raster_extents.shp')
    union_of_raster_extents(static_maps_list, raster_extents_vector)

    def _polygon_from_vector_extents(vector_uri):
        _vector = ogr.Open(vector_uri)
        _layer = _vector.GetLayer()
        extent = _layer.GetExtent()

        return shapely.geometry.Polygon([
            (extent[0], extent[2]),
            (extent[1], extent[2]),
            (extent[1], extent[3]),
            (extent[0], extent[3]),
            (extent[0], extent[2]),
        ])

    def _cleanup_temp_dir():
        try:
            shutil.rmtree(temp_dir)
        except:
            LOGGER.warn('Could not remove %s', temp_dir)

    # first, check to see if the impacts vector's extents are contained within
    # the union of raster extents vector.
    raster_extents_polygon = _polygon_from_vector_extents(raster_extents_vector)
    impacts_extents_polygon = _polygon_from_vector_extents(impacts_uri)
    if impacts_extents_polygon.contains(raster_extents_polygon):
        LOGGER.debug('Impacts polygons extend beyond static map bounds')
        _cleanup_temp_dir()
        return False
    elif impacts_extents_polygon.disjoint(raster_extents_polygon):
        LOGGER.debug('Impacts and static maps are disjoint')
        _cleanup_temp_dir()
        return False

    # Verify that there are no polygons that only overlap nodata values.
    for raster_uri in static_maps_list:
        raster_nodata = pygeoprocessing.get_nodata_from_uri(raster_uri)
        raster_stats = pygeoprocessing.aggregate_raster_values_uri(raster_uri,
            impacts_uri, ignore_nodata=False)

        for parcel_id in raster_stats.pixel_min.keys():
            pixel_min = raster_stats.pixel_min[parcel_id]
            pixel_max = raster_stats.pixel_max[parcel_id]
            if pixel_min == pixel_max and pixel_min == raster_nodata:
                _cleanup_temp_dir()
                LOGGER.debug('At least one polygon only overlaps nodata')
                return False
    return True


# I want a function where I can provide a function to apply to the geometry of
# a single vector.  The function will take a shapely geometry object as input,
# and will either return None (indicating that the parcel should not be
# included in the output vector) or a new shapely object.
# all fields should be included when writing corresponding features.
# I should also be able to create new fields and modify existing fields in the
# output vector.
def vectorize_vector(vector_uri, op, out_vector_uri):
    pass
