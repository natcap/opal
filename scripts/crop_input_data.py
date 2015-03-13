import os
import glob
import adept
from adept import static_maps
from adept import preprocessing

RASTER_EXCLUDE = ['sample_static_impact_map.tif']
VECTOR_EXCLUDE = ['Single_rivers.shp', 'Double_rivers.shp', 'Lagoons.shp',
        'Municipalities.shp', 'Population_centers_and_size.shp',
        'Protected_areas.shp', 'Reservoirs.shp', 'sample_aoi.shp']

def crop(tool_dir, watershed, dest_dir):
    for geotiff in glob.glob(os.path.join(tool_dir, "*.tif")):
        if os.path.basename(geotiff) in RASTER_EXCLUDE:
            continue
        print geotiff
        new_tiff = os.path.join(dest_dir, os.path.basename(geotiff))
        static_maps.clip_raster_to_watershed(geotiff, watershed, new_tiff)

    for shapefile in glob.glob(os.path.join(tool_dir, "*.shp")):
        if os.path.basename(shapefile) in VECTOR_EXCLUDE:
            continue
        new_shp = os.path.join(dest_dir, os.path.basename(shapefile))
        preprocessing.locate_intersecting_polygons(shapefile, watershed,
            new_shp, clip=True)

if __name__ == '__main__':
    IMPACT = '../colombia_sample_data/sogamoso_sample/mine_site.shp'
    WATERSHEDS = '../colombia_tool_data/hydrozones.shp'
    TOOL_DIR = '../colombia_tool_data'
    OUT_DIR = '../OPAL_symposium'

    # Determine the active watershed
    NEW_WATERSHED = os.path.join(OUT_DIR, 'watershed.shp')
    preprocessing.locate_intersecting_polygons(WATERSHEDS, IMPACT,
        NEW_WATERSHED)

    # Crop relevant rasters and vectors to the active watershed
    crop(TOOL_DIR, NEW_WATERSHED, OUT_DIR)




