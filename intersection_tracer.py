import ogr
import osr
import logging
import os

logging.basicConfig(format='%(asctime)s %(name)-18s %(levelname)-8s \
    %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')


LOGGER = logging.getLogger('raster_utils')

def clip_shape(shape_to_clip_uri, binding_shape_uri, output_path):
    """Copies a polygon or point geometry shapefile, only keeping the features
        that intersect or are within a binding polygon shape.

        shape_to_clip_uri - A uri to a point or polygon shapefile to clip
        binding_shape_uri - A uri to a polygon shapefile indicating the
            bounds for the shape_to_clip features
        output_path  - The path for the clipped output shapefile

        returns - Nothing"""
    shape_to_clip = ogr.Open(shape_to_clip_uri)
    binding_shape = ogr.Open(binding_shape_uri)

    shape_source = output_path
    # If the output_path is already a file, remove it
    if os.path.isfile(shape_source):
        os.remove(shape_source)
    # Get the layer of points from the current point geometry shape
    in_layer = shape_to_clip.GetLayer(0)
    # Get the layer definition which holds needed attribute values
    in_defn = in_layer.GetLayerDefn()
    # Get the layer of the polygon (binding) geometry shape
    clip_layer = binding_shape.GetLayer(0)
    # Create a new shapefile with similar properties of the
    # current point geometry shape
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    shp_ds = shp_driver.CreateDataSource(shape_source)
    shp_layer = shp_ds.CreateLayer(in_defn.GetName(), in_layer.GetSpatialRef(),
                                   in_defn.GetGeomType())
    # Get the number of fields in the current point shapefile
    in_field_count = in_defn.GetFieldCount()
    # For every field, create a duplicate field and add it to the
    # new shapefiles layer
    for fld_index in range(in_field_count):
        src_fd = in_defn.GetFieldDefn(fld_index)
        fd_def = ogr.FieldDefn(src_fd.GetName(), src_fd.GetType())
        fd_def.SetWidth(src_fd.GetWidth())
        fd_def.SetPrecision(src_fd.GetPrecision())
        shp_layer.CreateField(fd_def)
    LOGGER.debug('Binding Shapes Feature Count : %s',
                 clip_layer.GetFeatureCount())
    LOGGER.debug('Shape to be Bounds Feature Count : %s',
                 in_layer.GetFeatureCount())
    # Retrieve all the binding polygon features and save their cloned
    # geometry references to a list
    clip_feat = clip_layer.GetNextFeature()
    clip_geom_list = []
    while clip_feat is not None:
        clip_geom = clip_feat.GetGeometryRef()
        # Get the spatial reference of the geometry to use in transforming
        source_sr = clip_geom.GetSpatialReference()
        # Retrieve the current point shapes feature and get it's
        # geometry reference
        in_layer.ResetReading()
        in_feat = in_layer.GetNextFeature()
        geom = in_feat.GetGeometryRef()
        # Get the spatial reference of the geometry to use in transforming
        target_sr = geom.GetSpatialReference()
        geom = None
        in_feat = None
        # Create a coordinate transformation
        coord_trans = osr.CoordinateTransformation(source_sr, target_sr)
        # Transform the polygon geometry into the same format as the
        # point shape geometry
        clip_geom.Transform(coord_trans)
        # Add geometry to list
        clip_geom_list.append(clip_geom.Clone())
        clip_feat = clip_layer.GetNextFeature()

    in_layer.ResetReading()
    in_feat = in_layer.GetNextFeature()
    # For all the features in the current point shape (for all the points)
    # Check to see if they Intersect with any of the binding polygons geometry
    # and if they do, copy that point and it's fields to the new shape
    while in_feat is not None:
        # Check to see if the point falls in any of the polygons
        for index, clip_geom in enumerate(clip_geom_list):
            print index
            geom = in_feat.GetGeometryRef()
            # Intersection returns a new geometry if they intersect, null
            # otherwise.
            geom = geom.Intersection(clip_geom)
            if(geom.GetGeometryCount() + geom.GetPointCount()) != 0:
                # Create a new feature from the input feature and set
                # its geometry
                out_feat = ogr.Feature(feature_def=shp_layer.GetLayerDefn())
                out_feat.SetFrom(in_feat)
                out_feat.SetGeometryDirectly(geom)
                # For all the fields in the feature set the field values from
                # the source field
                for fld_index2 in range(out_feat.GetFieldCount()):
                    src_field = in_feat.GetField(fld_index2)
                    out_feat.SetField(fld_index2, src_field)

                shp_layer.CreateFeature(out_feat)
                out_feat = None
                break
        in_feat = in_layer.GetNextFeature()

        
        
impact_ds_uri = './data/colombia_tool_data/Example permitting footprints/Example_mining_projects.shp'
ecosystems_ds_uri = ('./data/colombia_tool_data/Ecosystems_Colombia.shp')
clipped_uri = 'impact_areas'

impact_ds = ogr.Open(impact_ds_uri)

impact_ds_layer = impact_ds.GetLayer(0)
    # Get the layer definition which holds needed attribute values
impact_ds_defn = impact_ds_layer.GetLayerDefn()
    # Get the layer of the polygon (binding) geometry shape

clipped_ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(clipped_uri)
clipped_layer = clipped_ds.CreateLayer(
    clipped_uri, impact_ds_layer.GetSpatialRef(), impact_ds_defn.GetGeomType())

for field_index in xrange(impact_ds_defn.GetFieldCount()):
    current_field = impact_ds_defn.GetFieldDefn(field_index)
    current_def = ogr.FieldDefn(current_field.GetName(), current_field.GetType())
    current_def.SetWidth(current_field.GetWidth())
    current_def.SetPrecision(current_field.GetPrecision())
    clipped_layer.CreateField(current_def)




#clip_shape(ds_bio_uri, ds_impact_uri, clipped_uri)
