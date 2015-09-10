import unittest
import tempfile
import os

from osgeo import gdal
from osgeo import osr
import numpy
from invest_natcap.testing import GISTest
import pygeoprocessing

from adept import static_maps

def raster(numpy_matrix, nodata):
    out_uri = pygeoprocessing.temporary_filename()
    datatype = gdal.GDT_Float32
    n_rows, n_cols = numpy_matrix.shape
    driver = gdal.GetDriverByName('GTiff')
    new_raster = driver.Create(out_uri, n_cols, n_rows, 1, datatype)

    # create some projection information based on the GDAL tutorial at
    # http://www.gdal.org/gdal_tutorial.html
    srs = osr.SpatialReference()
    srs.SetUTM(11, 1)
    srs.SetWellKnownGeogCS('NAD27')
    new_raster.SetProjection(srs.ExportToWkt())
    new_raster.SetGeoTransform([444720, 30, 0, 3751320, 0, -30])

    band = new_raster.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    band.WriteArray(numpy_matrix, 0, 0)

    band = None
    new_raster = None
    return out_uri

def get_matrix(raster_uri):
    dataset = gdal.Open(raster_uri)
    band = dataset.GetRasterBand(1)
    matrix = band.ReadAsArray()

    band = None
    dataset = None
    return matrix

class StaticMapsTest(GISTest):
    def setUp(self):
        self._temp_files = []

    def tearDown(self):
        for file_uri in self._temp_files:
            try:
                os.remove(file_uri)
            except OSError:
                # This happens if the file doesn't exist.  This is usually okay,
                # since it may have been deleted by another method.
                pass

    def temporary_filename(self):
        """Create a new temporary file on disk in the system's temp location.
        This test class tracks the temp files created, removing them at the end
        of the test run."""
        file_handle, path = tempfile.mkstemp()
        os.close(file_handle)
        self._temp_files.append(path)
        return path

    def test_convert_lulc(self):
        lulc_matrix = numpy.matrix([
            [5, 5, 5],
            [4, 3, 1],
            [6, 4, 1]])
        lulc_uri = raster(lulc_matrix, 5)

        out_uri = self.temporary_filename()
        static_maps.convert_lulc(lulc_uri, 7, out_uri)

        expected_matrix = numpy.matrix([
            [5, 5, 5],
            [7, 7, 7],
            [7, 7, 7]])
        self.assertMatrixes(get_matrix(out_uri), expected_matrix)

    @unittest.skip('sediment takes forever')
    def test_execute_sediment_smoke(self):
        lulc_matrix = numpy.matrix([
            [5, 5, 5],
            [4, 3, 1],
            [6, 4, 1]])
        lulc_uri = raster(lulc_matrix, 5)

        dem_matrix = numpy.matrix([
            [5, 5, 5],
            [5, 4, 5],
            [4, 3, 2]])
        dem_uri = raster(dem_matrix, -1)

        workspace_folder = pygeoprocessing.temporary_folder()
        static_maps.execute_model('sediment', lulc_uri, workspace_folder)

    def test_execute_carbon_smoke(self):
        lulc_matrix = numpy.matrix([
            [5, 5, 5],
            [4, 3, 1],
            [6, 4, 1]])
        lulc_uri = raster(lulc_matrix, 5)

        workspace_folder = pygeoprocessing.temporary_folder()
        static_maps.execute_model('carbon', lulc_uri, workspace_folder)
