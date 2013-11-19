import ogr
import osr
import logging
import os
import shapely.wkb

logging.basicConfig(format='%(asctime)s %(name)-18s %(levelname)-8s \
    %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('intersection_tracer')
        
impact_ds_uri = './data/colombia_tool_data/Example permitting footprints/Example_mining_projects.shp'
ecosystems_ds_uri = ('./data/colombia_tool_data/ecosys_dis_nat_comp_fac.shp')
clipped_uri = 'impact_areas'

ecosystems_ds = ogr.Open(ecosystems_ds_uri)
print ecosystems_ds
ecosystems_ds_layer = ecosystems_ds.GetLayer(0)
    # Get the layer definition which holds needed attribute values
ecosystems_ds_defn = ecosystems_ds_layer.GetLayerDefn()
    # Get the layer of the polygon (binding) geometry shape
print ecosystems_ds_defn
clipped_ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(clipped_uri)
clipped_layer = clipped_ds.CreateLayer(
    clipped_uri, ecosystems_ds_layer.GetSpatialRef(), ecosystems_ds_defn.GetGeomType())

print ecosystems_ds_defn

#for field_index in xrange(ecosystems_ds_defn.GetFieldCount()):
for field_name in ['FACTOR_DE', 'Ecos_dis']:
    field_index = ecosystems_ds_defn.GetFieldIndex(field_name)
    print field_index, field_name
    current_field = ecosystems_ds_defn.GetFieldDefn(field_index)
    current_def = ogr.FieldDefn(field_name, current_field.GetType())
    current_def.SetWidth(current_field.GetWidth())
    current_def.SetPrecision(current_field.GetPrecision())
    clipped_layer.CreateField(current_def)


impact_ds = ogr.Open(impact_ds_uri)
impact_layer = impact_ds.GetLayer()
for feature_index in xrange(impact_layer.GetFeatureCount()):
    feature = impact_layer.GetFeature(feature_index)
    geometry = feature.GetGeometryRef()
    polygon = shapely.wkb.loads(geometry.ExportToWkb())
    print polygon

#1) Load the impact dataset into a shapely multipolygon



#2) Make a spatial index?


#3) Loop through each feature in impact ds and build a polygon out of it
#3a) intersect that polygon with the impact multipolygon
#3b) if non-empty intersection, add the intersection to clipped_layer with features from ecosystems's feature



#clip_shape(ds_bio_uri, ds_ecosystems_uri, clipped_uri)
