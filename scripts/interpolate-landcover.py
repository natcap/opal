"""
Take in a vector of natural ecosystems and a sample raster (to use for
extracting the sample pixel size and projection), and simulate the
expansion of natural landcover classes across the space between natural
parcels.  This outputs a single raster file with the selected landcover codes.

Inputs:
    Ecosystems vector
    Sample LULC raster
    Sigma for the gaussian filter

The output raster will be masked to the nodata values of the input raster.

Prodecure:
    Loop through the ecosystems parcels to determine which parcels are of
    the same landcover type.

    For each parcel type:
        create a new polygon layer from just those polygons
        Rasterize the layer to a new raster based on the sample raster.
        Apply a gaussian filter to the dataset with the specified sigma

    Given this pixel stack, apply the following operation and write it to
    the output raster:
        if pixel_value[0] == nodata:
            return nodata
        else:
            return max(pixel_values)

"""
import os
import tempfile
import logging
import glob

import numpy
from osgeo import ogr
from osgeo import gdal
from adept import static_maps
from adept import preprocessing
from invest_natcap.pollination import pollination_core
import pygeoprocessing

_VECTOR_URI = os.path.join(os.path.dirname(__file__), '..', 'data',
                          'colombia_tool_data', 'ecosys_dis_nat_comp_fac.shp')
_RASTER_URI = os.path.join(os.path.dirname(__file__), '..', 'data',
                           'OPAL_symposium', 'ecosystems.tif')

ADEPT_LOGGER = logging.getLogger('adept.static_maps')
ADEPT_LOGGER.setLevel(logging.WARNING)
LOGGER = logging.getLogger('interpolate-landcover')


def _test_polytons_in_ecosystem():

    found_ecosystems = polygons_in_ecosystem(_VECTOR_URI)
    print found_ecosystems
    assert(len(found_ecosystems) == 455)


def features_in_vector(vector_uri):
    vector = ogr.Open(vector_uri)
    layer = vector.GetLayer()
    return layer.GetFeatureCount()


def polygons_in_ecosystem(vector_uri):
    ecosystem_fieldname = 'ecosystem'

    fids_in_ecosystem = {}

    vector = ogr.Open(vector_uri)
    layer = vector.GetLayer()

    for feature in layer:
        fid = feature.GetFID()
        ecosystem = feature.GetField(ecosystem_fieldname)
        try:
            fids_in_ecosystem[ecosystem].append(fid)
        except KeyError:
            fids_in_ecosystem[ecosystem] = [fid]

    return fids_in_ecosystem


def _get_lucode(vector_uri):
    # assume there's only one layer and one polygon in this vector.
    datasource = ogr.Open(vector_uri)
    layer = datasource.GetLayer()
    feature = layer.GetFeature(0)
    return feature.GetField('lucode')


def interpolate_landcover(vector_uri, lulc_uri, sigma, out_dir=None, rerasterize=True):

    if out_dir is None:
        workspace = tempfile.mkdtemp(dir=os.getcwd())
    else:
        workspace = out_dir

    paths = {
        'split_ecosys_dir': os.path.join(workspace, 'split_ecosystems'),
        'ecosystems': os.path.join(workspace, 'ecosystems.shp'),
        'ecosys_rasters_dir': os.path.join(workspace, 'ecosys_rasters'),
        'raster_bbox': os.path.join(workspace, 'lulc_bbox.shp'),
        'ecosys_in_raster': os.path.join(workspace, 'ecosystems_in_raster.shp'),
        'kernel': os.path.join(workspace, 'kernel.tif'),
        'out_lulc_raster': os.path.join(workspace, 'out_lulc_.tif'),
        'reclass_lulc': os.path.join(workspace, 'final_lulc.tif'),
    }

    pygeoprocessing.create_directories([paths['ecosys_rasters_dir']])

    # clip the ecosystems vector to the bounding box of the raster
    preprocessing.raster_extents_to_vector(lulc_uri, paths['raster_bbox'])

    # clip the ecosystems vector by the raster bounding box
    preprocessing.locate_intersecting_polygons(vector_uri,
        paths['raster_bbox'], paths['ecosys_in_raster'], clip=True)

    if len(polygons_in_ecosystem(vector_uri)) != features_in_vector(vector_uri):
        preprocessing.union_by_attribute(paths['ecosys_in_raster'], 'ecosystem',
            paths['ecosystems'])
    else:
        paths['ecosystems'] = paths['ecosys_in_raster']

    # split the vector into one vector per ecosystem.
    ecosystem_vectors = static_maps.split_datasource(paths['ecosystems'],
        paths['split_ecosys_dir'], ['FID'])

    LOGGER.debug('Creating decay kernel')
    pollination_core.make_exponential_decay_kernel_uri(
        sigma,
        paths['kernel']
    )

    rasters_list = []
    reclass_dict = {}  # map raster_id: actual lucode
    for raster_id, ecosystem_vector_uri in enumerate(ecosystem_vectors):
        new_raster = os.path.join(paths['ecosys_rasters_dir'],
            str(raster_id) + '_base.tif')
        filtered_raster = os.path.join(paths['ecosys_rasters_dir'],
            str(raster_id) + '_filtered.tif')
        rasters_list.append(filtered_raster)

        reclass_dict[raster_id] = _get_lucode(ecosystem_vector_uri)

        # Setting nodata value to -1.0 so this will never be reached from the gaussian filter.
        pygeoprocessing.make_constant_raster_from_base_uri(lulc_uri, 0.0, new_raster, nodata_value=-1.0)

        LOGGER.debug('Filtering raster #%s of %s', raster_id, len(ecosystem_vectors))
        # make the initial rasterization, gaussian filter and re-rasterize
        pygeoprocessing.rasterize_layer_uri(new_raster, ecosystem_vector_uri, [1.0])
        pygeoprocessing.convolve_2d_uri(new_raster, paths['kernel'], filtered_raster)

        if rerasterize:
            pygeoprocessing.rasterize_layer_uri(filtered_raster, ecosystem_vector_uri, [1.0])

    calc_max(rasters_list, lulc_uri, paths['out_lulc_raster'])

    pygeoprocessing.reclassify_dataset_uri(
        dataset_uri=paths['out_lulc_raster'],
        value_map=reclass_dict,
        raster_out_uri=paths['reclass_lulc'],
        out_datatype=gdal.GDT_Int32,
        out_nodata=-1
    )


def calc_max(rasters_list, lulc_uri, out_lulc_uri):
    def _max_pixels(*matrix_stack):
        # Stack up all the matrices into a 3-D matrix, return the 3rd dimension
        # index of the highest pixel value.
        dstack = numpy.dstack(matrix_stack)
        amax = numpy.argmax(dstack, axis=2)
        return amax

    pygeoprocessing.vectorize_datasets(
        rasters_list,
        _max_pixels,
        dataset_out_uri=out_lulc_uri,
        datatype_out=gdal.GDT_Int32,
        nodata_out=-1,
        pixel_size_out=pygeoprocessing.get_cell_size_from_uri(lulc_uri),
        bounding_box_mode='intersection',
        vectorize_op=False,
        datasets_are_pre_aligned=True
    )


def _reclassify_existing_lulc(folder):
    """
    Take an existing expansion folder and reclassify the out_lulc_.tif therein.
    Also builds up the needed reclassification mapping from the split ecosystems.

    Params:
        folder (string): the filepath to the simulation folder to run.

    Returns:
        None.
    """
    reclass_dict = {}
    all_vectors = glob.glob(os.path.join(folder, 'split_ecosystems', '*.shp'))
    sorted_vectors = \
        sorted(all_vectors, key = lambda x: int(os.path.splitext(os.path.basename(x))[0].split('_')[-1]))
    for raster_id, vector_uri in enumerate(sorted_vectors):
        print raster_id, vector_uri
        reclass_dict[raster_id] = _get_lucode(vector_uri)

    pygeoprocessing.reclassify_dataset_uri(
        dataset_uri=os.path.join(folder, 'out_lulc_.tif'),
        value_map=reclass_dict,
        raster_out_uri=os.path.join(folder, 'lulc_reclass.tif'),
        out_datatype=gdal.GDT_Int32,
        out_nodata=-1
    )

if __name__ == '__main__':
    interpolate_landcover(_VECTOR_URI, _RASTER_URI, sigma=100, rerasterize=True)
