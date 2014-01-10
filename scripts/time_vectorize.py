"""This script is built to find an execution time function based on the number
of pixels in a sample raster given a single computer's architeture.  If such a
factor could be found, we would be able to provide some crude time estimates in
the Palisades UI for indicating model progress (where the UI JSON file would
specify a function in terms of this factor).

This script assumes that we have three rasters in the cwd:
    ecosystems_10.tif
    ecosystems_30.tif
    ecosystems_90.tif

These are upsampled rasters based on the clipped ecosystems raster found at
    invest_natcap.permitting/data/permitting_clipped/ecosystems.tif

To create these rasters, I used gdalwarp, specifying the -tr option to be the
correct resolution (e.g. "-tr 30 -30" for ecosystems_30.tif).
"""

import time
import os

from osgeo import gdal
import invest_natcap
from invest_natcap import raster_utils


# time one each of 10, 30, 90m rasters, running a simple vectorize 1000 times
# each and taking the mean.
def vectorize_raster(raster_uri, num_samples):

    start_time = time.time()
    times = []
    for i in xrange(num_samples):
        start_time = time.time()
        output_raster_uri = "%s_copy%s" % os.path.splitext(raster_uri)
        nodata = raster_utils.get_nodata_from_uri(raster_uri)
        pixel_size = raster_utils.get_cell_size_from_uri(raster_uri)

        raster_utils.vectorize_datasets([raster_uri],
        lambda x: x, dataset_out_uri=output_raster_uri,
        datatype_out=gdal.GDT_Float32, nodata_out=-9999, pixel_size_out=pixel_size,
        bounding_box_mode='intersection')

        end time = time.time()
        times.append(end_time - start_time)

    min_time = min(times)
    max_time = max(times)
    mean_time = sum(times) / float(len(times))

    return {
        'min': min_time,
        'max': max_time,
        'mean': mean_time
    }

if __name__ == '__main__':
    num_samples = 1000
    for pixel_size in ['10', '30', '90']:
        input_filename = "ecosystems_%s.tif" % pixel_size
        vectorize_raster(input_filename, num_samples)
