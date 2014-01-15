from osgeo import ogr
import shapely

def group_by_attribute(in_vector_uri, out_vector_uri):
    # create a new vector at out_vector_uri
    # Select all the features in the input vector with matching attribute
    # values.
    # take the union of those matching features and write the geometry to the
    # output vector.
    # close the datasources.

    in_vector = ogr.Open(in_vector_uri)
    in_layer = in_vector.GetLayer(0)
    in_defn = in_layer.GetLayerDefn()

    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    out_vector = shp_driver.CreateDataSource(out_vector_uri)
    out_layer = out_vector.CreateLayer(in_defn.GetName(),
        in_layer.GetSpatialRef(), in_defn.GetGeomType())

    # Create the ZH, NOMZH columns
    for field_name in ['ZH', 'NOMZ']:
        source_field_index = in_defn.GetFieldIndex(field_name)
        source_field = in_defn.GetField(source_field_index)
        new_field = ogr.FieldDefn(source_field_index.GetName(),
            source_field_index.GetType())
        new_field.SetWidth(source_field.GetWidth())
        new_field.SetPrecision(source_field.GetPrecision())
        out_layer.CreateField(new_field)


if __name__ == '__main__':
    print 'done'
