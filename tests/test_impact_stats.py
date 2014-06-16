from adept import static_maps

if __name__ == '__main__':
    stats = static_maps.compute_impact_stats(
        '/home/jadoug06/workspace/invest-natcap.permitting/ignore_me/sediment_map_quality/bare/watershed_40/random_impact_0',
        'sediment',
        '/home/jadoug06/workspace/invest-natcap.permitting/ignore_me/sediment_map_quality/bare/watershed_vectors/feature_40.shp',
        5,
        '/home/jadoug06/workspace/invest-natcap.permitting/ignore_me/sediment_map_quality/bare/watershed_40/watershed_lulc.tif')

    print stats
