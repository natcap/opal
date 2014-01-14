import os
import logging
import cProfile
import pstats

from osgeo import gdal
from invest_natcap import raster_utils

LOGGER = logging.getLogger('neighborhood_analysis')

def neighborhood_analysis(ecosystems_vector, sample_raster):
    # create a new raster for the ecosystems vector to be burned to.
    # burn the ecosystems vector into the new raster
    # reclassify: bin desired lucodes into lucode groups
    # gaussian filter each lucode  # later on, we'll add an expansion factor
    # Vectorize this stack of filtered lucode groups, picking the highest val.

    workspace = os.path.join(os.getcwd(), 'neighborhood_analysis')
    raster_utils.create_directories([workspace])

    es_raster_raw = os.path.join(workspace, 'es_raw.tif')

    LOGGER.debug('Creating new raster from base')
    raster_utils.new_raster_from_base_uri(sample_raster, es_raster_raw,
        'GTiff', -1, gdal.GDT_Int32)
    es_raster_nodata = raster_utils.get_nodata_from_uri(es_raster_raw)
    es_raster_pixel_size = raster_utils.get_cell_size_from_uri(es_raster_raw)

    LOGGER.debug('Rasterizing ecosystems vector')
    raster_utils.rasterize_layer_uri(es_raster_raw, ecosystems_vector,
            option_list=["ATTRIBUTE=lucode"])

    lucode_bins = [
        range(51, 81),  # we want values from 51-80, inclusive.
        range(138, 149),
        range(149, 168),
        range(168, 187),
        range(244, 272),
    ]
    filtered_rasters = []
    for lu_bin in lucode_bins:
        min_lucode = lu_bin[0]
        reclass_map = dict((code, 1.0) for code in lu_bin)

        LOGGER.debug('Binning lucode %s', min_lucode)
        binned_raster = os.path.join(workspace, "%s_bin.tif" % min_lucode)
        raster_utils.reclassify_by_dictionary(gdal.Open(es_raster_raw), reclass_map,
            binned_raster, 'GTiff', es_raster_nodata, gdal.GDT_Int32, 0.0)

        LOGGER.debug('Starting gaussian filter for bin %s', min_lucode)
        filtered_raster = os.path.join(workspace, "%s_bin_filtered.tif" %
            min_lucode)
        raster_utils.gaussian_filter_dataset_uri(binned_raster, 5, filtered_raster,
            es_raster_nodata)

        filtered_rasters.append(filtered_raster)

    # Objective: prevent plantations from expanding to natural forest.
    #
    # Take the plantation landcover (workspace/138_bin.tif) and mask out all
    # the pixels where there is natural forest in the original landcover.
    # Then, use this new raster instead of the 138_bin.tif raster in the
    # filtered_rasters list.
    plantation_raster = os.path.join(workspace, "%s_bin_filtered.tif" % 138)
    plantation_no_forest = os.path.join(workspace, "%s_bin_filtered_no_forest.tif" % 138)
    plantation_index = filtered_rasters.index(plantation_raster)
    filtered_rasters[plantation_index] = plantation_no_forest
    natural_forest = range(110, 138)

    def mask_out_natural_forest(orig_lulc, expansion_index):
        if orig_lulc in natural_forest:
            return 0.0
        return expansion_index

    raster_utils.vectorize_datasets([es_raster_raw, plantation_raster],
        mask_out_natural_forest, plantation_no_forest, gdal.GDT_Float32,
        es_raster_nodata, es_raster_pixel_size, 'intersection')


    expanding_landcovers = []
    for expanding_bin in lucode_bins:
        expanding_landcovers += expanding_bin

    persistent_landcover_groups = [
        range(1, 4),  # [1-3], Aflorametes rocoscos
        range(4, 9),  # [4-9], Aguas continentales artificiales
        range(10, 29),  #[10-29], Aguas continentales naturales
        range(81, 88),  #[81-88], (A)reas mayormente alteradas
        range(89, 109), #[89-109], (a)reas urbanas
        range(187, 188), #[187-188], Glaciares y nieves
        range(236, 240), #[236-240], Lagunas costeras
        range(301, 314)  #[301-314], Zonas desnudas, sin o con poca vegetaci(o)n
    ]
    landcovers_that_persist = []
    for persistent_landcover in persistent_landcover_groups:
        landcovers_that_persist += persistent_landcover

    def pick_values(starting_lulc, *filtered_pixels):
        if starting_lulc in landcovers_that_persist:
            return starting_lulc

        if starting_lulc not in expanding_landcovers:
            return starting_lulc

        max_value = max(filtered_pixels)
        max_index = filtered_pixels.index(max_value)
        return lucode_bins[max_index][0]

    LOGGER.debug('Picking the final raster')
    expanded_raster = os.path.join(workspace, 'es_complete.tif')
    raster_utils.vectorize_datasets([es_raster_raw] + filtered_rasters, pick_values,
        expanded_raster, gdal.GDT_Float32, es_raster_nodata,
        es_raster_pixel_size, 'intersection')

if __name__ == '__main__':
#    tool_data_dir = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
#    ecosystems_vector = os.path.join(tool_data_dir, 'Ecosystems_Colombia.shp')
#    dem_raster = os.path.join(tool_data_dir, 'DEM.tif')

    tool_data_dir = os.path.join(os.getcwd(), 'data', 'colombia_clipped')
    ecosystems_vector = os.path.join(tool_data_dir, 'ecosystems_colombia.shp')
    dem_raster = os.path.join(tool_data_dir, 'dem.tif')

    neighborhood_analysis(ecosystems_vector, dem_raster)

