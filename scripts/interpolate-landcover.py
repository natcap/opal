import argparse

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


if __name__ == '__main__':
    pass