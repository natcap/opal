import os

from osgeo import gdal
from invest_natcap import raster_utils

def neighborhood_analysis(ecosystems_vector, sample_raster):
    # create a new raster for the ecosystems vector to be burned to.
    # burn the ecosystems vector into the new raster
    # reclassify: bin desired lucodes into lucode groups
    # gaussian filter each lucode  # later on, we'll add an expansion factor
    # Vectorize this stack of filtered lucode groups, picking the highest val.

    workspace = os.path.join(os.getcwd(), 'neighborhood_analysis')
    raster_utils.create_directories([workspace])

    es_raster_raw = os.path.join(workspace, 'es_raw.tif')

    raster_utils.new_raster_from_base_uri(sample_raster, es_raster_raw,
        'GTiff', -1, gdal.GDT_Int32)
    es_raster_nodata = raster_utils.get_nodata_from_uri(es_raster_raw)
    es_raster_pixel_size = raster_utils.get_cell_size_from_uri(es_raster_raw)

    raster_utils.rasterize_layer_uri(es_raster_raw, ecosystems_vector,
            option_list=["ATTRIBUTE=lucode"])

    lucode_bins = [
        range(51, 81),  # we want values from 50-80, inclusive.
        range(138, 149),
        range(149, 168),
        range(168, 187),
        range(244, 272),
    ]
    filtered_rasters = []
    for lu_bin in lucode_bins:
        min_lucode = lu_bin[0]
        reclass_map = dict((code, min_lucode) for code in lu_bin)

        binned_raster = os.path.join(workspace, "%s_bin.tif" % min_lucode)
        raster_utils.reclassify_by_dictionary(es_raster_raw, reclass_map,
            binned_raster, 'GTiff', es_raster_nodata, gdal.GDT_Int32, 0.0)

        filtered_raster = os.path.join(workspace, "%s_bin_filtered.tif" %
            min_lucode)
        raster_utils.gaussian_filter_dataset(binned_raster, 5, filtered_raster,
            es_raster_nodata)

        filtered_rasters.append(filtered_raster)

    def pick_values(*pixels):
        return max(pixels)

    expanded_raster = os.path.join(workspace, 'es_complete.tif')
    raster_utils.vectorize_datasets(filtered_rasters, pick_values,
        expanded_raster, gdal.GDT_Float32, es_raster_nodata,
        es_raster_pixel_size, 'intersection')

if __name__ == '__main__':
    tool_data_dir = os.path.join(os.getcwd(), 'data', 'colombia_tool_data')
    ecosystems_vector = os.path.join(tool_data_dir, 'Ecosystems_Colombia.shp')
    dem_raster = os.path.join(tool_data_dir, 'DEM.tif')
    neighborhood_analysis(ecosystems_vector, dem_raster)

