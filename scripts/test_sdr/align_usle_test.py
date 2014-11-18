import os
import numpy
from osgeo import gdal
from invest_natcap import raster_utils

if __name__ == '__main__':
    base_usle = '/colossus/colombia_sdr/base_run/output/usle.tif'
    impact_usle = '/colossus/colombia_sdr/bare/simulations/watershed_7/random_impact_2/output/usle.tif'

    watershed_vector = '/colossus/colombia_sdr/bare/simulations/watershed_vectors/feature_7.shp'

    base_usle_stats = raster_utils.aggregate_raster_values_uri(base_usle,
        watershed_vector, 'ws_id')
    print 'base', base_usle_stats.pixel_mean[8], base_usle_stats.total[8]

    impact_usle_stats = raster_utils.aggregate_raster_values_uri(impact_usle,
        watershed_vector, 'ws_id')
    print 'impact', impact_usle_stats.pixel_mean[8], impact_usle_stats.total[8]

    # pixel sizes
    impact_usle_size = raster_utils.get_cell_size_from_uri(impact_usle)
    base_usle_size = raster_utils.get_cell_size_from_uri(base_usle)
    print 'pixel sizes:', base_usle_size, impact_usle_size

    in_raster_list = [base_usle, impact_usle]
    out_ws = os.path.join(os.getcwd(), 'ws7_aligned_usle')
    aligned_base_usle = os.path.join(out_ws, 'aligned_base_usle.tif')
    aligned_impact_usle = os.path.join(out_ws, 'aligned_impact_usle.tif')
    out_raster_list = [aligned_base_usle, aligned_impact_usle]

    print 'Aligned'
    resample_method_list = ['nearest'] * 2
    raster_utils.align_dataset_list(in_raster_list, out_raster_list,
        resample_method_list, base_usle_size, 'intersection', 1)

    base_usle_stats = raster_utils.aggregate_raster_values_uri(
        aligned_base_usle, watershed_vector, 'ws_id')
    print 'base', base_usle_stats.pixel_mean[8], base_usle_stats.total[8]

    impact_usle_stats = raster_utils.aggregate_raster_values_uri(
        aligned_impact_usle, watershed_vector, 'ws_id')
    print 'impact', impact_usle_stats.pixel_mean[8], impact_usle_stats.total[8]

    # clipping ws_7.
    base_nodata = raster_utils.get_nodata_from_uri(base_usle)
    impact_nodata = raster_utils.get_nodata_from_uri(impact_usle)
    def mask(a, b):
        return numpy.where(a == base_nodata, impact_nodata, b)

    masked_impact_usle = os.path.join(out_ws, 'aligned_masked_impact_usle.tif')
    raster_utils.vectorize_datasets([aligned_base_usle, aligned_impact_usle],
        mask, masked_impact_usle,
        gdal.GDT_Float32, impact_nodata, impact_usle_size,
        bounding_box_mode='intersection', vectorize_op=False)

    masked_base_usle = os.path.join(out_ws, 'aligned_masked_base_usle.tif')
    raster_utils.vectorize_datasets([aligned_impact_usle, aligned_base_usle],
        mask, masked_base_usle,
        gdal.GDT_Float32, base_nodata, base_usle_size,
        bounding_box_mode='intersection', vectorize_op=False)

    print 'Masked'
    base_usle_stats = raster_utils.aggregate_raster_values_uri(
        masked_base_usle, watershed_vector, 'ws_id')
    print 'base', base_usle_stats.pixel_mean[8], base_usle_stats.total[8]

    impact_usle_stats = raster_utils.aggregate_raster_values_uri(
        masked_impact_usle, watershed_vector, 'ws_id')
    print 'impact', impact_usle_stats.pixel_mean[8], impact_usle_stats.total[8]





