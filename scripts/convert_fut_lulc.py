import os

from invest_natcap import raster_utils
from osgeo import gdal
import numpy

ecosystems_raster = os.path.join('data', 'colombia_tool_data', 'es_comp_rd.tif')
out_raster = 'es_comp_rd_0.tif'

old_nodata = raster_utils.get_nodata_from_uri(ecosystems_raster)
new_nodata = 0
def nodata_op(x):
    return numpy.where(x == old_nodata, new_nodata, x)

pixel_size = raster_utils.get_cell_size_from_uri(ecosystems_raster)
raster_utils.vectorize_datasets(
    [ecosystems_raster], nodata_op, out_raster, gdal.GDT_Int32, new_nodata,
    pixel_size, 'intersection', vectorize_op=False)

