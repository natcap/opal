
from adept import static_maps

if __name__ == '__main__':
    ws_vector = '/colossus/colombia_sdr/bare/simulations/watershed_vectors/feature_7.shp'

    for scenario in ['base', 'bare']:
        big_raster = '/home/jadoug06/ws7/%s_sdr_factor.tif' % scenario
        small_raster = '/home/jadoug06/ws7/ws7_%s_sdr_factor.tif' % scenario

        print 'clipping ', scenario
        static_maps.clip_static_map(big_raster, ws_vector, small_raster)
