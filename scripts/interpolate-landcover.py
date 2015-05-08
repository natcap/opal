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
from osgeo import ogr

def _test_polytons_in_ecosystem(vector_uri):
    vector_uri = os.path.join(os.path.dirname(__file__), '..', 'data',
        'colombia_tool_data', 'ecosys_dis_nat_comp_fac.shp')

    found_ecosystems = polygons_in_ecosystem(vector_uri)
    assert(len(found_ecosystems) == 455)

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




if __name__ == '__main__':
    pass