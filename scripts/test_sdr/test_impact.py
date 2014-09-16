import os
import random
import logging
import shutil
from types import UnicodeType

from osgeo import ogr
from osgeo import gdal

from invest_natcap import raster_utils

LOGGER = logging.getLogger('test_impact')

def make_random_impact_vector(new_vector, base_vector, side_length):
    """Create a new vector with a single, squarish polygon.  This polygon will
    be created within the spatial envelope of the first polygon in base_vector.
    The new squarish polygon will have a side length of side_length.

        new_vector - a URI to the new vector to be created. The new vector will
            be an ESRI Shapefile.
        base_vector - a URI to the vector we'll use as a base (for its spatial
            information).
        side_length - a python int or float describing the side length of the
            new polygon to be created.

        Returns nothing."""
    base_datasource = ogr.Open(base_vector)
    base_layer = base_datasource.GetLayer()
    base_feature = base_layer.GetFeature(0)
    base_geometry = base_feature.GetGeometryRef()
    spat_ref = base_layer.GetSpatialRef()

    #feature_extent = [xmin, xmax, ymin, ymax]
    feature_extent = base_geometry.GetEnvelope()
    print feature_extent

    driver = ogr.GetDriverByName('ESRI Shapefile')
    datasource = driver.CreateDataSource(new_vector)
    uri_basename = os.path.basename(new_vector)
    layer_name = str(os.path.splitext(uri_basename)[0])
    layer = datasource.CreateLayer(layer_name, spat_ref, ogr.wkbPolygon)

    # Add a single ID field
    field = ogr.FieldDefn('id', ogr.OFTInteger)
    layer.CreateField(field)

    while True:
        poly_ring = ogr.Geometry(type=ogr.wkbLinearRing)
        bbox_width = feature_extent[1]-feature_extent[0]
        bbox_height = feature_extent[3]-feature_extent[2]

        rand_width_percent = random.random()
        xmin = feature_extent[0] + bbox_width * rand_width_percent
        xmax = xmin + side_length

        #Make it squarish
        rand_height_percent = random.random()
        ymin = feature_extent[2] + bbox_height * rand_height_percent
        ymax = ymin + side_length

        print feature_extent
        print xmin, xmax, ymin, ymax

        poly_ring.AddPoint(xmin, ymin)
        poly_ring.AddPoint(xmin, ymax)
        poly_ring.AddPoint(xmax, ymax)
        poly_ring.AddPoint(xmax, ymin)
        poly_ring.AddPoint(xmin, ymin)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(poly_ring)

        #See if the watershed contains the permitting polygon
        contained = base_geometry.Contains(polygon)
        print contained
        if contained:
            break

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    feature.SetField(0, 1)
    layer.CreateFeature(feature)

    feature = None
    layer = None

def split_datasource(ds_uri, workspace, include_fields=[],
        template_str='feature_%s.shp'):
    """Split the input OGR datasource into a list of datasources, each with a
    single layer containing a single feature.
        ds_uri - a URI to an OGR datasource.
        workspace - a folder to which the output vectors should be saved.
        include_fields=[] - a list of string fields to be copied from the source
            datsource to the destination datasources.
        template_str - a template string with a placeholder for a single value.
            All file uris will be named according to this pattern.
    Returns a list of URIs, one for each new vector created."""

    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    os.makedirs(workspace)

    LOGGER.debug('Opening vector at %s', ds_uri)
    ds = ogr.Open(ds_uri)
    num_features = sum([l.GetFeatureCount() for l in ds])
    driver_string = 'ESRI Shapefile'

    LOGGER.debug('Splitting datasource into separate shapefiles')
    LOGGER.debug('Vectors will be saved to %s', workspace)
    output_vectors = []
    for layer in ds:
        layer_defn = layer.GetLayerDefn()
        for feature in layer:
            print 'starting new feature'
            uri_index = feature.GetFID()
            new_vector_uri = os.path.join(workspace, template_str %
                uri_index)
            output_vectors.append(new_vector_uri)

            LOGGER.debug('Creating new shapefile at %s' % new_vector_uri)
            ogr_driver = ogr.GetDriverByName(driver_string)
            temp_shapefile = ogr_driver.CreateDataSource(new_vector_uri)
            LOGGER.debug('SRS: %s, %s', layer.GetSpatialRef(),
                type(layer.GetSpatialRef()))

            layer_name = os.path.splitext(os.path.basename(
                new_vector_uri))[0]
            if type(layer_name) is UnicodeType:
                LOGGER.debug('Decoding layer name %s to ASCII', layer_name)
                #layer_name = layer_name.decode('utf-8')
                layer_name = str(layer_name)

            LOGGER.debug('Layer name: %s', layer_name)

            temp_layer = temp_shapefile.CreateLayer(
                layer_name, layer.GetSpatialRef())
            temp_layer_defn = temp_layer.GetLayerDefn()

            for field_index in range(layer_defn.GetFieldCount()):
                original_field = layer_defn.GetFieldDefn(field_index)
                output_field = ogr.FieldDefn(original_field.GetName(),
                    original_field.GetType())
                temp_layer.CreateField(output_field)

            # Create the obligatory ID field.
            # If I don't create the ID field, I can't properly select other
            # fields later on, when I need to set their values.
            id_field = ogr.FieldDefn('id', ogr.OFTInteger)
            temp_layer.CreateField(id_field)

            # Create the new feature with all of the characteristics of the old
            # field except for the fields.  Those are brought along separately.
            LOGGER.debug('Creating new feature with duplicate geometry')
            feature_geom = feature.GetGeometryRef()
            temp_feature = ogr.Feature(temp_layer_defn)
            temp_feature.SetFrom(feature)

            # Since there's only one feature in this shapefile, set id to 0.
            id_field_index = temp_feature.GetFieldIndex('id')
            temp_feature.SetField(id_field_index, 0)

            LOGGER.debug('Copying over fields %s', include_fields)
            for field_index in range(layer_defn.GetFieldCount()):
                field_defn = layer_defn.GetFieldDefn(field_index)
                field = field_defn.GetName()
                LOGGER.debug('Adding field "%s"', field)

                # Create the new field in the temp feature
                field_type = field_defn.GetType()
                LOGGER.debug('Field type=%s', field_type)

                LOGGER.debug('Copying field "%s" value to new feature',
                    field)
                temp_feature.SetField(field, feature.GetField(field))

            temp_layer.CreateFeature(temp_feature)
            temp_layer.SyncToDisk()

            temp_layer = None
            temp_shapefile = None

    layer.ResetReading()
    layer = None
    ds = None
    ogr_driver = None

    LOGGER.debug('Finished creating the new shapefiles')
    return output_vectors

STARTING_WATERSHEDS = ('invest-natcap.invest-3/test/invest-data/'
    'Base_Data/Freshwater/watersheds.shp')
LULC_URI = ('invest-natcap.invest-3/test/invest-data/Base_Data/'
    'Terrestrial/lulc_samp_cur')

def initial_procedure():
    lulc_pixel_size = raster_utils.get_cell_size_from_uri(LULC_URI)
    lulc_nodata = raster_utils.get_nodata_from_uri(LULC_URI)

    workspace_dir = 'test_fragmentation'
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)

    split_watersheds_dir = os.path.join(workspace_dir, 'split_watersheds')
    split_watersheds = split_datasource(STARTING_WATERSHEDS,
        split_watersheds_dir, ['ws_id'])

    # write an lulc for watershed_2
    watershed_lulc = os.path.join(workspace_dir, 'watershed_lulc.tif')
    raster_utils.vectorize_datasets([LULC_URI], lambda x: x,
        watershed_lulc, gdal.GDT_Float32, lulc_nodata, lulc_pixel_size,
        'intersection', dataset_to_align_index=0, aoi_uri=split_watersheds[2])

    impact_site = os.path.join(workspace_dir, 'impact_site.shp')
    make_random_impact_vector(impact_site, split_watersheds[2],
        random.uniform(500, 3000))

    impact_lucode = 19

    # Create a raster mask for the randomized impact site.
    # Any non-nodata pixels underneath the impact site are marked by 1.
    def mask_op(value):
        if value == lulc_nodata:
            return lulc_nodata
        return 1.0
    impact_mask = os.path.join(workspace_dir, 'impact_mask.tif')
    raster_utils.vectorize_datasets([watershed_lulc], mask_op, impact_mask,
        gdal.GDT_Float32, lulc_nodata, lulc_pixel_size, 'intersection',
        dataset_to_align_index=0, aoi_uri=impact_site)

    converted_landcover = os.path.join(workspace_dir, 'converted_lulc.tif')
    def convert_impact(mask_value, lulc_value):
        if mask_value == 1:
            return impact_lucode
        return lulc_value
    raster_utils.vectorize_datasets([impact_mask, watershed_lulc],
        convert_impact, converted_landcover, gdal.GDT_Float32, lulc_nodata,
        lulc_pixel_size, 'union', dataset_to_align_index=0)


if __name__ == '__main__':
    initial_procedure()

