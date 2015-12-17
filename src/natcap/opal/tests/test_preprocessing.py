import unittest
import tempfile
import shutil
import os
import glob

import shapely.wkt
import shapely.ops
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
import rtree
from osgeo import ogr

import natcap.opal.tests
from natcap.opal import preprocessing
from natcap.opal import utils

class PreprocessingTest(unittest.TestCase):
    def test_rm_shapefile(self):
        # Verify that all files are removed correctly.
        # first, build up a temp dir with mock files.
        temp_dir = tempfile.mkdtemp()
        def make_file(filename):
            uri = os.path.join(temp_dir, filename)
            new_file = open(uri, 'w')
            #new_file.write('')
            new_file.close()
            return uri

        files = [make_file("vector.%s" % ext) for ext in ['shp', 'shx', 'dbf']]
        keep = make_file('not_a_vector.csv') # should not be deleted

        preprocessing.rm_shapefile(files[0])  # remove vector.shp
        for vector_file in files:
            self.assertEqual(os.path.exists(vector_file), False)
        self.assertEqual(os.path.exists(keep), True)

        shutil.rmtree(temp_dir)

    def test_build_spatial_index(self):
        polygon_a = Polygon([(1, 1), (5, 1), (5, 5), (1, 5),
            (1, 1)])
        polygon_b = Polygon([(3, 3), (9, 3), (9, 9), (3, 9),
            (3, 3)])
        polygon_c = Polygon([(8, 1), (11, 1), (11, 4), (8, 4),
            (8, 1)])

        vector_uri = natcap.opal.tests.vector([polygon_a, polygon_b, polygon_c],
            natcap.opal.tests.COLOMBIA_SRS)

        spat_index, parcels = preprocessing.build_spatial_index(vector_uri)

        # verify that the number of parcels is correct
        self.assertEqual(len(parcels), 3)
        self.assertEqual(isinstance(spat_index, rtree.index.Index), True)

        natcap.opal.tests.cleanup(vector_uri)

    def test_split_multipolygons(self):
        base_coords = [(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]
        def translate(x, y):
            return [(a + x, b + y) for (a, b) in base_coords]

        polygon_a = Polygon(base_coords)
        polygon_b = Polygon(translate(4, 0))
        polygon_c = Polygon(translate(0, 4))
        polygon_d = Polygon(translate(4, 4))
        polygon_e = Polygon(translate(8, 2))

        multipoly_a = MultiPolygon([polygon_a, polygon_b])
        multipoly_b = MultiPolygon([polygon_c, polygon_d])

        multi_vec = natcap.opal.tests.vector([multipoly_a, multipoly_b, polygon_e],
            natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile')

        out_dir = tempfile.mkdtemp()
        out_vector_uri = os.path.join(out_dir, 'split.shp')
        preprocessing.split_multipolygons(multi_vec, out_vector_uri)

        # Check the split vector for contents.
        out_vector = ogr.Open(out_vector_uri)
        out_layer = out_vector.GetLayer()
        self.assertEqual(out_layer.GetFeatureCount(), 5)

        out_layer = None
        out_vector = None
        shutil.rmtree(out_dir)

    def test_split_multipolygons_line(self):
        """
        Split_multipolygons() should skip over features that are not polygons
        """
        base_coords = [(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]
        def translate(x, y):
            return [(a + x, b + y) for (a, b) in base_coords]

        linestring_a = LineString(base_coords)
        linestring_b = LineString(translate(4, 0))
        linestring_c = LineString(translate(0, 4))
        linestring_d = LineString(translate(4, 4))
        linestring_e = LineString(translate(8, 2))

        multilinestring_a = MultiLineString([linestring_a, linestring_b])
        multilinestring_b = MultiLineString([linestring_c, linestring_d])

        multi_vec = natcap.opal.tests.vector(
            [multilinestring_a, multilinestring_b, linestring_e],
            natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile')

        out_dir = tempfile.mkdtemp()
        out_vector_uri = os.path.join(out_dir, 'split.shp')
        self.assertRaises(ValueError,  preprocessing.split_multipolygons, multi_vec, out_vector_uri)

        shutil.rmtree(out_dir)


    def test_prepare_aoi(self):
        # create an impact sites vector.
        impact_a = Polygon([(5, 3), (10, 3), (10, 5), (5, 5), (5, 3)])
        impact_b = Polygon([(4, 9), (6, 9), (6, 11), (4, 11), (4, 9)])
        impacts_vector = natcap.opal.tests.vector([impact_a, impact_b],
            natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile')

        # create a sample hydrozubsones vector
        subzone_a = Polygon([(1, 1), (8, 1), (8, 7), (1, 7), (1, 1)])
        subzone_b = Polygon([(8, 1), (14, 1), (14, 8), (8, 8), (8, 1)])
        subzone_c = Polygon([(8, 8), (15, 8), (15, 14), (8, 14), (8, 8)])
        subzone_d = Polygon([(1, 7), (8, 7), (8, 14), (1, 14), (1, 7)])
        subzones_vector = natcap.opal.tests.vector([subzone_a, subzone_b, subzone_c,
            subzone_d], natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile')

        temp_dir = tempfile.mkdtemp()
        out_uri = os.path.join(temp_dir, 'aoi.shp')
        preprocessing.prepare_aoi(impacts_vector, subzones_vector, out_uri)

        out_vector = ogr.Open(out_uri)
        out_layer = out_vector.GetLayer()
        self.assertEqual(out_layer.GetFeatureCount(), 1)

        # take the union of the three subzone polygons that we expect.
        expected_geom = shapely.ops.cascaded_union([subzone_a, subzone_b,
            subzone_d])

        # get the wkt of the feature in out_layer.
        feature = out_layer.GetFeature(0)
        geometry = feature.GetGeometryRef()

        # convert to shapely geometry
        found_geom = shapely.wkt.loads(geometry.ExportToWkt())

        # assert that the areas are the same
        self.assertEqual(found_geom.area, expected_geom.area)

        # take the difference of the two polygons, assert that the resulting
        # area is 0.
        difference = expected_geom.difference(found_geom)
        self.assertEqual(difference.area, 0)

    def test_prepare_impact_sites(self):
        # build an impact sites vector.
        impact_a = Polygon([(5, 3), (10, 3), (10, 5), (5, 5), (5, 3)])
        impact_b = Polygon([(4, 9), (6, 9), (6, 11), (4, 11), (4, 9)])
        impacts_vector = natcap.opal.tests.vector([impact_a, impact_b],
            natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile')

        # build a hydrozones vector where two hydrozones intersect the same
        # impact polygon.
        subzone_a = Polygon([(1, 1), (8, 1), (8, 7), (1, 7), (1, 1)])
        subzone_b = Polygon([(8, 1), (14, 1), (14, 8), (8, 8), (8, 1)])
        subzone_c = Polygon([(8, 8), (15, 8), (15, 14), (8, 14), (8, 8)])
        subzone_d = Polygon([(1, 7), (8, 7), (8, 14), (1, 14), (1, 7)])
        fields = {
            'zone': str,
        }
        field_values = [
            {'zone': 'A'},
            {'zone': 'B'},
            {'zone': 'C'},
            {'zone': 'D'},
        ]
        subzones_vector = natcap.opal.tests.vector([subzone_a, subzone_b, subzone_c,
            subzone_d], natcap.opal.tests.COLOMBIA_SRS, format='ESRI Shapefile',
            fields=fields, features=field_values)

        temp_dir = tempfile.mkdtemp()

        preprocessing.prepare_impact_sites(impacts_vector, subzones_vector,
            temp_dir)

        # prepare_impact_sites creates a folder with output vectors.  There
        # should be 3 of them.
        geom_a = Polygon([(5, 3), (8, 3), (8, 5), (5, 5), (5, 3)])
        geom_b = Polygon([(8, 3), (10, 3), (10, 5), (8, 5), (8, 3)])
        geom_d = impact_b  # this impact should not have changed.
        for zone, impact_geom in [('A', geom_a), ('B', geom_b), ('D', geom_d)]:
            impact_filename = os.path.join(temp_dir,
                'impacts_%s.shp' % zone)
            self.assertTrue(os.path.exists(impact_filename))

            impact_vector = ogr.Open(impact_filename)
            impact_layer = impact_vector.GetLayer()
            self.assertEqual(impact_layer.GetFeatureCount(), 1)

            feature = impact_layer.GetFeature(0)
            shapely_feature = utils.build_shapely_polygon(feature)
            self.assertEqual(impact_geom.union(shapely_feature).area,
                impact_geom.area)
            self.assertEqual(impact_geom.difference(shapely_feature).area, 0.0)

        shutil.rmtree(temp_dir)

    def test_union_by_attribute(self):
        # build a sample vector
        polygon_a = Polygon([(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)])
        polygon_b = Polygon([(2, 1), (3, 1), (3, 2), (2, 2), (2, 1)])
        polygon_c = Polygon([(3, 1), (4, 1), (4, 2), (3, 2), (3, 1)])

        fields = {
            'zone': str
        }
        field_values = [
            {'zone': 'first'},
            {'zone': 'first'},
            {'zone': 'second'},
        ]
        sample_vector = natcap.opal.tests.vector([polygon_a, polygon_b, polygon_c],
            natcap.opal.tests.COLOMBIA_SRS, fields, field_values)

        temp_dir = tempfile.mkdtemp()
        out_file = os.path.join(temp_dir, 'union_by_attribute.shp')
        preprocessing.union_by_attribute(sample_vector, 'zone', out_file)

        out_vector = ogr.Open(out_file)
        out_layer = out_vector.GetLayer()
        self.assertEqual(out_layer.GetFeatureCount(), 2)

        expected_geom = Polygon([(1, 1), (3, 1), (3, 2), (1, 2), (1, 1)])
        first_ogr_feature = out_layer.GetFeature(1)
        first_feature = utils.build_shapely_polygon(first_ogr_feature)
        self.assertEqual(expected_geom.area,
            expected_geom.union(first_feature).area)
        self.assertEqual(expected_geom.difference(first_feature).area, 0.0)

        # assert that the field was created in the layer and that the field
        # value was set for the first field..
        fieldnames = map(lambda x: x.GetName(), out_layer.schema)
        self.assertTrue('zone' in fieldnames)
        self.assertEqual(first_ogr_feature.GetField('zone'), 'first')

        shutil.rmtree(temp_dir)


    def test_locate_intersecting_polygons(self):
        polygon_a = Polygon([(1, 1), (5, 1), (5, 5), (1, 5),
            (1, 1)])
        polygon_b = Polygon([(3, 3), (9, 3), (9, 9), (3, 9),
            (3, 3)])
        polygon_c = Polygon([(8, 1), (11, 1), (11, 4), (8, 4),
            (8, 1)])

        vector_uri = natcap.opal.tests.vector([polygon_a, polygon_b, polygon_c],
            natcap.opal.tests.COLOMBIA_SRS)

        comparison_polygon = Polygon([(0, 0), (4, 0), (4, 4), (4, 0), (0, 0)])
        comp_vector_uri = natcap.opal.tests.vector([comparison_polygon],
                                                   natcap.opal.tests.COLOMBIA_SRS)

        out_dir = tempfile.mkdtemp()
        out_vector_uri = os.path.join(out_dir, 'out_vector.shp')
        preprocessing.locate_intersecting_polygons(vector_uri, comp_vector_uri,
                                                   out_vector_uri)

        # TODO: use this test (or even better, a test on real sample data)
        # to compare OGR layer operations against per-polygon operations.


