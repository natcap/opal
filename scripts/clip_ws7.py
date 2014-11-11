
from adept import static_maps

if __name__ == '__main__':
    ws_vector = '/colossus/colombia_sdr/bare/simulations/watershed_vectors/feature_7.shp'

    raster_name = 'usle'

    for scenario in ['base', 'bare']:
        big_raster = '/home/jadoug06/ws7/%s_%s.tif' % (scenario, raster_name)
        small_raster = '/home/jadoug06/ws7/ws7_%s_%s.tif' % (scenario, raster_name)

        print 'clipping ', scenario
        static_maps.clip_static_map(big_raster, ws_vector, small_raster)
