import os
import shutil

from invest_natcap import raster_utils
from osgeo import ogr
import shapely
import shapely.geometry
import shapely.wkb
import shapely.speedups
import shapely.prepared
import shapely.ops

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

    # Create the ZH, NOMZH columns in the output shapefile.
    for field_name in ['ZH', 'NOMZH']:
        source_field_index = in_defn.GetFieldIndex(field_name)
        source_field = in_defn.GetFieldDefn(source_field_index)
        new_field = ogr.FieldDefn(source_field.GetName(),
            source_field.GetType())
        new_field.SetWidth(source_field.GetWidth())
        new_field.SetPrecision(source_field.GetPrecision())
        out_layer.CreateField(new_field)

    # loop through all features and determine which hydrozone they belong to.
    hydrozones = {}
    hydrozone_names = {}
    for feature_index in xrange(in_layer.GetFeatureCount()):
        # get the ZH value
        feature = in_layer.GetFeature(feature_index)
        zh_value = feature.GetField('ZH')
        nomzh_value = feature.GetField('NOMZH')

        # if the ZH value is not in hydrozones, add the key and create a new
        # list of geometries.
        # if the ZH value _is_ in hydrozones, append the feature to the correct
        # list of geometries.
        geometry = feature.GetGeometryRef()
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
        try:
            hydrozones[zh_value].append(polygon)
        except KeyError:
            hydrozones[zh_value] = [polygon]
            hydrozone_names[zh_value] = nomzh_value

    if shapely.speedups.available:
        shapely.speedups.enable()

    out_defn = out_layer.GetLayerDefn()
    for key, contained_subzones in hydrozones.iteritems():
        print key, len(contained_subzones)

        # get the union
        union_polygon = shapely.ops.cascaded_union(contained_subzones)

        # make a new OGR feature for the union polygon.
        feature = ogr.Feature(out_defn)
        feature.SetField('ZH', key)
        feature.SetField('NOMZH', hydrozone_names[key])

        # write the new polygon to the new shapefile.
        geom = ogr.CreateGeometryFromWkb(union_polygon.wkb)
        feature.SetGeometry(geom)

        out_layer.CreateFeature(feature)
        feature = None
        geom = None
        union_polygon = None

    in_layer = None
    in_vector = None
    out_layer = None
    out_vector = None


if __name__ == '__main__':
    workspace = os.path.join(os.getcwd(), 'grouped_hydrozones')

    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    raster_utils.create_directories([workspace])

    in_vector = os.path.join(os.getcwd(), 'data', 'colombia_tool_data',
        'Hydrographic_subzones.shp')
    out_vector = os.path.join(workspace, 'hydrozones.shp')

    group_by_attribute(in_vector, out_vector)
