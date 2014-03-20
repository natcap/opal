import gdal
from invest_natcap import raster_utils

lulc_vector = 'data/colombia_clipped/ecosystems_colombia.shp'
target_raster = 'data/colombia_clipped/ecosystems.tif'
sample_raster = 'data/colombia_clipped/dem.tif'

raster_utils.new_raster_from_base_uri(sample_raster, target_raster, 'GTiff', -1,
        gdal.GDT_Int16)
raster_utils.rasterize_layer_uri(target_raster, lulc_vector,
        option_list=["ATTRIBUTE=lucode"])
