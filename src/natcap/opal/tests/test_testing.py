import unittest
import json
import tempfile
import os

import shapely
import shapely.geometry
import numpy
from osgeo import gdal

import adept.tests

class TestUtilsVectorTest(unittest.TestCase):
    def test_vector(self):
        polygon_a = shapely.geometry.Polygon([(1,1), (4,1), (4,4), (1,4)])

        fields = {
            'field_int': int,
            'field_str': str,
            'field_float': float
        }
        field_values = {
            'field_int': 1,
            'field_str': 'hello',
            'field_float': 3.14159
        }

        # writes to a geojson file for easy parsing.
        uri = adept.tests.vector([polygon_a], adept.tests.COLOMBIA_SRS, fields,
            [field_values])

        json_vector = json.load(open(uri))
        self.assertEqual(len(json_vector['features']), 1)
        self.assertEqual(json_vector['features'][0]['properties'], field_values)

        adept.tests.cleanup(uri)

    def test_raster(self):
        matrix = numpy.array([
            [1.0, 1.0, 1.0],
            [2.0, 2.0, 2.0],
            [3.0, 3.0, 3.0],
        ], dtype=numpy.float32)
        raster_uri = adept.tests.raster(matrix, adept.tests.COLOMBIA_SRS,
                adept.tests.COLOMBIA_GEOTRANSFORM(30, -30), 1.0)

        ds = gdal.Open(raster_uri)
        ds_band = ds.GetRasterBand(1)
        ds_type = ds_band.DataType
        self.assertEqual(ds_type, gdal.GDT_Float32)

        # get the output matrix, verify it's equal to the matrix we input.
        out_array = ds.ReadAsArray()
        numpy.testing.assert_array_equal(matrix, out_array)

        adept.tests.cleanup(raster_uri)

        # Verify that the raster can be written to a known path.
        temp_dir = tempfile.mkdtemp()
        out_file = os.path.join(temp_dir, 'new_file.tif')
        adept.tests.raster(matrix, adept.tests.COLOMBIA_SRS,
            adept.tests.COLOMBIA_GEOTRANSFORM(30, -30), 1.0, filename=out_file)

        self.assertTrue(os.path.exists(out_file))
        ds = gdal.Open(out_file)
        ds_band = ds.GetRasterBand(1)
        ds_type = ds_band.DataType
        self.assertEqual(ds_type, gdal.GDT_Float32)
        numpy.testing.assert_array_equal(matrix, ds_band.ReadAsArray())
        adept.tests.cleanup(temp_dir)


    def test_colombia_geotransform(self):
        expected_gt = [444720, 30, 0, 3751320, 0, -30]
        self.assertEqual(adept.tests.COLOMBIA_GEOTRANSFORM(30, -30),
            expected_gt)

