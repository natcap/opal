import os
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

