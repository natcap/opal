import unittest
import glob
import tempfile
import os
import shutil
import inspect

from shapely.geometry import Polygon
import invest_natcap.testing
import numpy

import natcap.opal.i18n
from natcap.opal.tests import vector, raster, COLOMBIA_SRS, COLOMBIA_GEOTRANSFORM
from natcap.opal import adept_core

def square(center_coords, side_len):
    x, y = center_coords
    half_len = side_len / 2.0
    bl = (x - half_len, y - half_len)
    br = (x + half_len, y - half_len)
    tr = (x + half_len, y + half_len)
    tl = (x - half_len, y + half_len)

    return Polygon([bl, br, tr, tl, bl])

def subdivide(polygon, square_side_len):
    # polygon - a shapely polygon
    subzones = []
    polygon_x_min = int(min(map(lambda x: x[0], polygon.exterior.coords)))
    polygon_x_max = int(max(map(lambda x: x[0], polygon.exterior.coords)))
    polygon_y_min = int(min(map(lambda x: x[1], polygon.exterior.coords)))
    polygon_y_max = int(max(map(lambda x: x[1], polygon.exterior.coords)))

    for x in range(polygon_x_min, polygon_x_max, square_side_len):
        for y in range(polygon_y_min, polygon_y_max, square_side_len):
            x_center = x + square_side_len / 2
            y_center = y + square_side_len / 2
            subzone = square((x_center, y_center), square_side_len)
            subzones.append(subzone)

    return subzones

def named_workspace(clean=True, index=1):
    """Create a folder that is the same name as the function that called this
    function.  The new directory is created in the CWD.

        clean=True - a boolean.  If True, the workspace folder, if it already
            exists on disk, will be recursively removed before returning.
        index=1 - an integer, representing the call stack depth to query for
            the function name for the workspace. 0 would be named_workspace, 1
            would be the function that called named_workspace.

    Returns a string URI to the new, named folder.
"""
    dir_name = os.path.join(os.getcwd(), inspect.stack()[index][3])
    if clean and os.path.exists(dir_name):
        shutil.rmtree(dir_name)
    return dir_name

class SmokeTest(invest_natcap.testing.GISTest):
    def setUp(self):
        natcap.opal.i18n.language.set('en')
        # make directories on disk in which to store internal data
        self._data_base_dir = tempfile.mkdtemp()
        internal_static_data = os.path.join(self._data_base_dir, 'data',
            'colombia_static_data')
        internal_tool_data = os.path.join(self._data_base_dir, 'data',
            'colombia_tool_data')
        for dirname in [internal_static_data, internal_tool_data]:
            os.makedirs(dirname)

        # servicesheds
        servicesheds = []
        for x in range(0, 20000, 10000):
            for y in range(0, 40000, 10000):
                bl = (x, y)
                br = (x + 10000, y)
                ur = (x + 10000, y + 10000)
                ul = (x, y + 10000)
                servicesheds.append(Polygon([bl, br, ur, ul, bl]))
        fields = {
            'pop_center': str,
            'pop_size': int,
        }
        field_values = [{'pop_center': str(i), 'pop_size': i * 1000} for i in range(len(servicesheds))]
        servicesheds_filename = os.path.join(internal_tool_data,
            'ssheds_Col_new.shp')
        self.servicesheds = vector(servicesheds, COLOMBIA_SRS, fields,
            field_values, format='ESRI Shapefile', filename=servicesheds_filename)

        # municipalities
        municipalities = []
        for x in range(0, 20000, 5000):
            bl = (x, 0)
            br = (x + 5000, 0)
            ur = (x + 5000, 40000)
            ul = (x, 40000)
            municipalities.append(Polygon([bl, br, ur, ul, bl]))
        municipalities_filename = os.path.join(internal_tool_data,
            'Municipalities.shp')
        self.municipalities = vector(municipalities, COLOMBIA_SRS,
            format='ESRI Shapefile',
            filename=municipalities_filename)

        # make max search area (hydrozone) polygon
        max_search_area = Polygon([(0, 0), (0, 40000), (20000, 40000), (20000, 0), (0, 0)])
        fields = {'zone': str}
        field_values = [{'zone': 'Hydrozone_A'}]
        self.search_vector = vector([max_search_area], COLOMBIA_SRS,
            fields=fields, features=field_values, format='ESRI Shapefile')

        # make a series of polygons to make up hydrosubzones
        subzones = subdivide(max_search_area, 5000)
        field_values = field_values*len(subzones)
        self.hydro_subzones = vector(subzones, COLOMBIA_SRS, fields,
            field_values, format='ESRI Shapefile')

        # make a sample impacts set of polygons
        impact_data = [
            ((12500, 32500), 2000),
            ((14500, 34500), 2000),
            ((12500, 27500), 1000),
            ((13000, 29500), 1000),
            ((10000, 26500), 1500),
            ((9000, 28000), 1000),
        ]
        impacts = []
        for impact_center, side_len in impact_data:
            impact_site = square(impact_center, side_len)
            impacts.append(impact_site)
        fields = {
            'FID': int,
        }
        field_values = [{'FID': i} for i in range(len(impact_data))]
        self.impacts = vector(impacts, COLOMBIA_SRS, fields, field_values,
            format='ESRI Shapefile')

        # make a natural ecosystems vector.
        # this need not be especially complex, but it should probably go outside the
        # bounds of the hydrozone to exercise the LCI parcel aggregation functionality
        # and should definitely intersect at least one of the impact sites.
        ecosystems = []
        new_width = 2000
        half_width = new_width / 2
        for subzone in subzones:
            polygon_x_min = int(min(map(lambda x: x[0], subzone.exterior.coords)))
            polygon_x_max = int(max(map(lambda x: x[0], subzone.exterior.coords)))
            polygon_y_min = int(min(map(lambda x: x[1], subzone.exterior.coords)))
            polygon_y_max = int(max(map(lambda x: x[1], subzone.exterior.coords)))

            x_med = (polygon_x_max - polygon_x_min) / 2 + polygon_x_min
            y_med = (polygon_y_max - polygon_y_min) / 2 + polygon_y_min

            new_coords = []
            for x_coord, y_coord in subzone.exterior.coords:
                if x_coord < x_med:
                    out_x_coord = x_med - half_width
                else:
                    out_x_coord = x_med + half_width

                if y_coord < y_med:
                    out_y_coord = y_med - half_width
                else:
                    out_y_coord = y_med + half_width

                new_coords.append((out_x_coord, out_y_coord))

            ecosys_polygon = Polygon(new_coords)
            ecosystems.append(ecosys_polygon)

        ecosystem_fields = {
            'ecosystem': str,
            'mit_ratio': float
        }
        ecosystem_field_values = [{'ecosystem': 'Eco_A',
            'mit_ratio': 4.5}] * len(ecosystems)
        self.ecosystems = vector(ecosystems, COLOMBIA_SRS, ecosystem_fields,
            ecosystem_field_values, format='ESRI Shapefile')

        # make a user-defined example AOI.
        area_of_influence = Polygon([(10000, 25000), (17500, 27500),
            (17500, 36000), (10000, 36000), (6000, 27250), (10000, 25000)])
        self.aoi = vector([area_of_influence], COLOMBIA_SRS, format='ESRI Shapefile')

        # avoidance areas
        avoid_a = Polygon([(14500, 35000), (17500, 36000), (15000, 37000),
            (14500, 35000)])
        self.avoidance_areas = vector([avoid_a], COLOMBIA_SRS, format='ESRI Shapefile')

        # conservation portfolio
        conserve_a = Polygon([(5000, 20000), (15000, 20000), (10000, 26500),
            (5000, 20000)])
        self.conservation_portfolio = vector([conserve_a], COLOMBIA_SRS,
            format='ESRI Shapefile')

        # previously granted impact
        prev_impact = square((13000, 29500), 750)
        self.previous_impact = vector([prev_impact], COLOMBIA_SRS,
            format='ESRI Shapefile')

        # Threat data
        # hydrozone is 20000 pixels wide, 40000 pixels tall
        # Filling with a constant value is OK ... the offset selection will
        # accept parcels with a threat score of at least the same as the
        # impacted parcel.
        zero_matrix = numpy.zeros((400, 200))
        zero_matrix.fill(1)
        self.threat = raster(zero_matrix, COLOMBIA_SRS,
            COLOMBIA_GEOTRANSFORM(100, 100, (0, 0)), -1)

        # Richness data
        # hydrozone is 20000 pixels wide, 40000 pixels tall
        # Filling with a constant value is OK ... the offset selection will
        # accept parcels with a threat score of at least the same as the
        # impacted parcel.
        self.richness = raster(zero_matrix, COLOMBIA_SRS,
            COLOMBIA_GEOTRANSFORM(100, 100, (0, 0)), -1)

        # Sediment static data.
        ones_matrix = numpy.zeros((400, 200))
        ones_matrix.fill(1)

        # make directories on disk for storing 'user-defined' static data.
        self.sediment_static_data = tempfile.mkdtemp()
        self.nutrient_static_data = tempfile.mkdtemp()
        self.carbon_static_data = tempfile.mkdtemp()
        self.custom_static_data = tempfile.mkdtemp()

        static_datas = [
            ('sediment', self.sediment_static_data, True),
            ('nutrient', self.nutrient_static_data, True),
            ('carbon', self.carbon_static_data, False),
            ('custom', self.custom_static_data, True),
        ]
        for model_name, data_dir, routed in static_datas:
            for scenario in ['paved', 'bare', 'protection']:
                sc_filename = lambda x: "%s_%s_static_map%s.tif" % (model_name,
                    scenario, x)

                user_uri = os.path.join(data_dir, sc_filename(''))
                internal_uri = os.path.join(internal_static_data,
                    sc_filename('_lzw'))
                for uri in [user_uri, internal_uri]:
                    raster(ones_matrix, COLOMBIA_SRS, COLOMBIA_GEOTRANSFORM(100,
                        100, (0, 0)), -1, filename=uri)

                # if this is a routed model, make a percent-to-stream raster.
                # But opnly do this if we're running nutrient.
                if routed and model_name in ['nutrient']:
                    pts_filename = "%s_%s_pts.tif" % (model_name, scenario)
                    user_uri = os.path.join(data_dir, pts_filename)
                    internal_uri = os.path.join(internal_static_data,
                        pts_filename)
                    for uri in [user_uri, internal_uri]:
                        raster(ones_matrix, COLOMBIA_SRS,
                            COLOMBIA_GEOTRANSFORM(100, 100, (0, 0)), -1,
                            filename=uri)

        self.workspace = tempfile.mkdtemp()

        self.args = {
            'workspace_dir': self.workspace,
            'project_footprint_uri': self.impacts,
            'impact_type': 'Road/Paved',
            'ecosystems_map_uri': self.ecosystems,
            'search_areas_uri': self.hydro_subzones,
            'data_dir': self._data_base_dir,
        }

    def tearDown(self):
        md5sum_logfile = self.__class__.__name__ + '-' + self._testMethodName + '.log'
        natcap.opal.tests.record_workspace_md5sums(self.workspace, md5sum_logfile)

        folders_to_rm = [
            self.sediment_static_data,
            self.nutrient_static_data,
            self.carbon_static_data,
            self.custom_static_data,
            self.workspace,
            self._data_base_dir,
        ]
        for folder_uri in folders_to_rm:
            try:
                shutil.rmtree(folder_uri)
            except OSError:
                pass

    def test_smoke(self):
        self.args['workspace_dir'] = 'smoke_test_workspace'
        adept_core.execute(self.args)

    def test_smoke_es(self):
        natcap.opal.i18n.language.set('es')
        self.test_smoke()
        if os.path.exists('es_workspace'):
            shutil.rmtree('es_workspace')
        shutil.copytree(self.workspace, 'es_workspace')
        print natcap.opal.i18n.language.available_langs
        print natcap.opal.i18n.LOCALE_DIR

    def test_smoke_custom_es(self):
        self.args['custom_static_maps'] = self.custom_static_data
        self.assertRaises(KeyError, adept_core.execute, self.args)

        self.args['custom_servicesheds'] = 'unknown'
        self.assertRaises(AssertionError, adept_core.execute, self.args)

        self.args['custom_servicesheds'] = 'global'
        adept_core.execute(self.args)

    def test_smoke_user_es(self):
        self.args['carbon_static_maps'] = self.carbon_static_data
        self.args['sediment_static_maps'] = self.sediment_static_data
        self.args['nutrient_static_maps'] = self.nutrient_static_data

        adept_core.execute(self.args)

    def test_smoke_wrong_impact(self):
        self.args['impact_type'] = 'something'
        self.assertRaises(AssertionError, adept_core.execute, self.args)

    def test_smoke_no_services(self):
        self.args['do_carbon'] = False
        self.args['do_sediment'] = False
        self.args['do_nutrient'] = False
        self.assertRaises(RuntimeError, adept_core.execute, self.args)

    def test_smoke_sed_only(self):
        self.args['do_carbon'] = False
        self.args['do_sediment'] = True
        self.args['do_nutrient'] = False
        adept_core.execute(self.args)

    def test_smoke_carbon_only(self):
        self.args['do_carbon'] = True
        self.args['do_sediment'] = False
        self.args['do_nutrient'] = False
        adept_core.execute(self.args)

    def test_smoke_carbon_custom(self):
        self.args['do_carbon'] = True
        self.args['do_sediment'] = False
        self.args['do_nutrient'] = False
        self.args['custom_static_maps'] = self.custom_static_data
        self.args['custom_servicesheds'] = 'global'
        adept_core.execute(self.args)

    def test_smoke_sediment_custom(self):
        self.args['do_carbon'] = False
        self.args['do_sediment'] = True
        self.args['do_nutrient'] = False
        self.args['custom_static_maps'] = self.custom_static_data
        self.args['custom_servicesheds'] = 'hydrological'
        adept_core.execute(self.args)

    def test_smoke_sediment_custom_global(self):
        self.args['do_carbon'] = False
        self.args['do_sediment'] = True
        self.args['do_nutrient'] = False
        self.args['custom_static_maps'] = self.custom_static_data
        self.args['custom_servicesheds'] = 'global'
        adept_core.execute(self.args)

    def test_smoke_threat_richness(self):
        self.args['threat_map'] = self.threat
        self.args['species_richness_map'] = self.threat
        self.args['do_carbon'] = True
        self.args['do_sediment'] = True
        self.args['do_nutrient'] = True
        adept_core.execute(self.args)

    def test_user_municipalities(self):
        # assert failure when bad municpalities provided.
        self.args['municipalities_uri'] = 'does_not_exist_ljhkslfg'
        self.assertRaises(RuntimeError, adept_core.execute, self.args)

        # remove the workspace.  Files have been written to this URI, so we
        # need to clean this up before running this again.
        try:
            shutil.rmtree(self.workspace)
        except OSError:
            pass

        # assert failure when neither the internal municipalities nor the
        # user-defined municipalities exist on disk.
        # This means moving the Municipalities vector to a known location so
        # that it's not in the internal tool data dir.
        temp_dir = tempfile.mkdtemp()
        moved_files = []
        municipalities_base = os.path.splitext(self.municipalities)[0]
        for src_filename in glob.glob('%s.*' % municipalities_base):
            dest_filename = os.path.join(temp_dir,
                os.path.basename(src_filename))
            shutil.move(src_filename, dest_filename)
            moved_files.append((src_filename, dest_filename))

        # remove the user-provided municipalities args entry to force the
        # fetching of internal municipalities
        del self.args['municipalities_uri']
        self.assertRaises(RuntimeError, adept_core.execute, self.args)

        # remove the workspace.  Files have been written to this URI, so we
        # need to clean this up before running this again.
        try:
            shutil.rmtree(self.workspace)
        except OSError:
            pass

        # now, move the files back to their correct location and provide the
        # correct municipalities URI.
        for orig_uri, moved_uri in moved_files:
            shutil.move(moved_uri, orig_uri)

        self.args['municipalities_uri'] = self.municipalities
        adept_core.execute(self.args)

    def test_invalid_impacts(self):
        invalid_impacts_vector = vector([
            Polygon([(-100, 0), (-100, -100), (-200, -100), (-200, 0),
                (-100, 0)])],
            COLOMBIA_SRS, format='ESRI Shapefile')

        self.args['project_footprint_uri'] = invalid_impacts_vector
        self.assertRaises(adept_core.InvalidImpactsVector, adept_core.execute, self.args)

    def test_impacts_without_biodiversity(self):
        impacts_without_natural_parcels = vector([
            Polygon([(4000, 4000), (6000, 4000), (6000, 6000), (4000, 6000),
                (4000, 4000)])], COLOMBIA_SRS, fields={'FID': int},
            features=[{'FID': 1}], format='ESRI Shapefile')
        self.args['project_footprint_uri'] = impacts_without_natural_parcels
        adept_core.execute(self.args)

class SmokeTestOPAL(SmokeTest):
    def setUp(self):
        SmokeTest.setUp(self)
        self.args['distribution'] = adept_core.DIST_OPAL

    def test_no_aoi(self):
        try:
            del self.args['area_of_influence_uri']
        except KeyError:
            # Key not in args dict anyways
            pass
        adept_core.execute(self.args)

class SmokeTest_ES(SmokeTest):
    def setUp(self):
        natcap.opal.i18n.language.set('es')
        SmokeTest.setUp(self)
