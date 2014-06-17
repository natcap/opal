"""
python invert_raster.py filename

filename - a URI to a raster (probably a GeoTiff) whose values will be
inverted.

This script creates a new file from the base, where the new file is called
filename.tmp and has values that are inverted (multiplied by -1.0).  This
tempfile is then copied over on top of the source file and then removed.  The
only file remaining is the original (albeit modified) file.

"""


import sys
import os
import shutil

from osgeo import gdal
import numpy
from invest_natcap import raster_utils

if __name__ == '__main__':
    filename = sys.argv[1]
    print 'Updating file %s' % os.path.abspath(filename)

    temp_file = filename + '.tmp'
    nodata_out = raster_utils.get_nodata_from_uri(filename)
    pixel_size = raster_utils.get_cell_size_from_uri(filename)

    print 'Writing temp file %s' % temp_file
    raster_utils.vectorize_datasets([filename],
        lambda x: numpy.where(x != nodata_out, numpy.multiply(x, -1.0),
        nodata_out), temp_file, gdal.GDT_Float32, nodata_out, pixel_size,
        'intersection', vectorize_op=False)

    #print 'Moving back to original'
    #shutil.move(temp_file, filename)

