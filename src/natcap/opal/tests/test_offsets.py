import unittest
import os
import shutil

from shapely.geometry import Polygon

from natcap.opal.tests import vector, COLOMBIA_SRS
from natcap.opal.tests import test_smoke
from natcap.opal import offsets

class OffsetTest(unittest.TestCase):
    def test_select_set_multifactor_bio(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        bio_requirements = {
            'a': {
                'mitigation_area': 200,
            },
            'b': {
                'mitigation_area': 100,
            }
        }

        expected_results = [1, 3]  # largest parcels selected first
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            bio_requirements)
        self.assertEqual(selected_parcels, expected_results)

    def test_select_set_multifactor_bio_no_ecosystem(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        bio_requirements = {
            'a': {
                'mitigation_area': 200,
            },
            'b': {
                'mitigation_area': 100,
            },
            'c': {  # no available parcels for this ecosystem.
                'mitigation_area': 50,
            }
        }

        expected_results = [1, 3]  # largest parcels selected first
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            bio_requirements)
        self.assertEqual(selected_parcels, expected_results)

    def test_select_set_multifactor_bio_mega(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        bio_requirements = {
            'a': {
                'mitigation_area': 100,
            },
            'b': {
                'mitigation_area': 100,
            }
        }
        prop_offset = 2.0

        expected_results = [1, 3]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            bio_requirements, proportion_offset=prop_offset)
        self.assertEqual(selected_parcels, expected_results)

    def test_select_set_multifactor_bio_hydro(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        bio_requirements = {
            'a': {
                'mitigation_area': 200,
            },
            'b': {
                'mitigation_area': 100,
            }
        }

        es_requirements = {
            1: {
                'sediment': 2500,
                'parcels': [1, 2, 3],
            }
        }
        expected_results = [1, 2, 4]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            bio_requirements, es_requirements)

    def test_select_set_multifactor_hydro(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        es_requirements = {
            1: {
                'sediment': 4000,
                'parcels': [1, 2, 3],
            }
        }

        expected_parcels = [3]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            es_hydro_req=es_requirements)
        self.assertEqual(selected_parcels, expected_parcels)

    def test_select_set_multifactor_hydro_mega(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        es_requirements = {
            1: {
                'sediment': 4000,
                'parcels': [1, 2, 3],
            }
        }

        prop_offset = 4.75

        expected_parcels = [2, 3]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            es_hydro_req=es_requirements, proportion_offset=prop_offset)
        self.assertEqual(selected_parcels, expected_parcels)

    def test_select_set_multifactor_global(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        global_reqs = {
            'carbon': 4000,
            'sediment': 500,
        }

        expected_parcels = [1, 3]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            es_global_req=global_reqs)
        self.assertEqual(expected_parcels, selected_parcels)

    def test_select_set_multifactor_bio_hydro_global(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290, 'ecosystem': 'a'},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348, 'ecosystem': 'a'},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234, 'ecosystem': 'b'},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019, 'ecosystem': 'b'},
        }

        bio_requirements = {
            'a': {
                'mitigation_area': 200,
            },
            'b': {
                'mitigation_area': 100,
            }
        }

        es_requirements = {
            1: {
                'sediment': 2500,
                'parcels': [1, 2, 3],
            }
        }

        global_reqs = {
            'carbon': 4000,
            'sediment': 500,
        }

        expected_parcels = [1, 2, 3, 4]
        selected_parcels = offsets.select_set_multifactor(parcels_dict,
            bio_requirements, es_requirements, global_reqs)
        self.assertEqual(expected_parcels, selected_parcels)

    def test_select_set(self):
        parcels_dict = {
            1: {'area': 400, 'carbon': 3500, 'sediment': 290},
            2: {'area': 123, 'carbon': 382, 'sediment': 1348},
            3: {'area': 8392, 'carbon': 1910, 'sediment': 18234},
            4: {'area': 149, 'carbon': 192, 'sediment': 1019},
        }
        requirements = [
            ('area', 350),
            ('sediment', 2000),
            ('carbon', 100),
        ]

        selected_parcels = offsets.select_set(parcels_dict, requirements)

        # Parcel 3 meets all three requirements.
        self.assertEqual(selected_parcels, [3])

    def test_select_set_2(self):
        parcels = {
            1: {'area': 101, 'carbon': 201, 'sediment': 301},
            2: {'area': 102, 'carbon': 202, 'sediment': 302},
            3: {'area': 103, 'carbon': 203, 'sediment': 303},
            4: {'area': 104, 'carbon': 204, 'sediment': 304},
        }
        requirements = [
            ('area', 100),
            ('carbon', 400),
            ('sediment', 900),
        ]

        self.assertEqual(offsets.select_set(parcels, requirements), [2, 3, 4])

    def test_locate_biodiversity_offsets(self):
        eco_a = test_smoke.square((20, 20), 10)
        eco_b = test_smoke.square((60, 20), 10)
        fields = {
            'ecosystem': str,
            'LCI': float,
        }
        field_values = [
            {'ecosystem': 'eco_a', 'LCI': 0.3},
            {'ecosystem': 'eco_b', 'LCI': 0.2},
        ]
        natural_ecosystems = vector([eco_a, eco_b], COLOMBIA_SRS, fields,
            field_values, format='ESRI Shapefile')
        known_biodiversity_impacts = {
            'eco_a': {
                'min_impacted_parcel_area': 50,
                'min_lci': 0.1,
            },
        }


        expected_parcels = {
            0: {
                'ecosystem': 'eco_a',
                'area': 100.0,
                'lci': 0.3,
            },
        }
        self.assertEqual(offsets.locate_biodiversity_offsets(natural_ecosystems,
            known_biodiversity_impacts), expected_parcels)

    def test_locate_biodiversity_offsets_all(self):
        eco_a = test_smoke.square((20, 20), 10)
        eco_b = test_smoke.square((60, 20), 10)
        fields = {
            'ecosystem': str,
            'LCI': float,
        }
        field_values = [
            {'ecosystem': 'eco_a', 'LCI': 0.3},
            {'ecosystem': 'eco_b', 'LCI': 0.2},
        ]
        natural_ecosystems = vector([eco_a, eco_b], COLOMBIA_SRS, fields,
            field_values, format='ESRI Shapefile')

        expected_parcels = {
            0: {
                'ecosystem': 'eco_a',
                'area': 100.0,
                'lci': 0.3,
            },
            1: {
                'ecosystem': 'eco_b',
                'area': 100.0,
                'lci': 0.2,
            },
        }
        self.assertEqual(offsets.locate_biodiversity_offsets(natural_ecosystems,
            {}), expected_parcels)

    def test_locate_biodiversity_offsets_bio_and_all(self):
        eco_a = test_smoke.square((20, 20), 10)
        eco_b = test_smoke.square((60, 20), 10)
        fields = {
            'ecosystem': str,
            'LCI': float,
        }
        field_values = [
            {'ecosystem': 'eco_a', 'LCI': 0.3},
            {'ecosystem': 'eco_b', 'LCI': 0.2},
        ]
        natural_ecosystems = vector([eco_a, eco_b], COLOMBIA_SRS, fields,
            field_values, format='ESRI Shapefile')
        known_biodiversity_impacts = {
            'eco_a': {
                'min_impacted_parcel_area': 50,
                'min_lci': 0.1,
            },
        }


        expected_parcels = {
            0: {
                'ecosystem': 'eco_a',
                'area': 100.0,
                'lci': 0.3,
            },
            1: {
                'ecosystem': 'eco_b',
                'area': 100.0,
                'lci': 0.2,
            },
        }
        self.assertEqual(offsets.locate_biodiversity_offsets(natural_ecosystems,
            known_biodiversity_impacts, include_all_ecosystems=True),
            expected_parcels)

    def test_select_offsets(self):
        ecosystems_polygons = [test_smoke.square((x, 20), 10)
                               for x in [20, 60, 100, 140]]

        # Screening should screen out this parcel.
        ecosystems_polygons += [test_smoke.square((160, 20), 10)]
        ecosystems_fields = {
            'ecosystem': str,
            'LCI': float,
            'carbon': float,
            'nutrient': float,
            'sediment': float,
        }
        ecosystems_attributes = [
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 822.82,
                'nutrient': 357.12, 'sediment': 395.82},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 396.34,
                'nutrient': 934.77, 'sediment': 121.27},
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 831.61,
                'nutrient': 136.92, 'sediment': 379.30},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 402.12,
                'nutrient': 829.71, 'sediment': 571.09},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 123.42,
                'nutrient': 14.34, 'sediment': 592.01},
        ]
        ecosystems_vector = vector(ecosystems_polygons, COLOMBIA_SRS,
            ecosystems_fields, ecosystems_attributes, format='ESRI Shapefile')
        biodiversity_impacts = {
                'eco_a': {
                    'min_impacted_parcel_area': 50,
                    'min_lci': 0.1,
                    'max_threat': None,
                    'min_richness': None,
                    'mitigation_area': 125.0,
                }
            }

        impacts_polygons = map(lambda x: test_smoke.square((x, 50), 10), [40,
            80])
        impact_columns = {
            'carbon': float,
            'sediment': float,
            'nutrient': float,
        }
        impact_field_values = [
            {'carbon': 123.43, 'nutrient': 898.12, 'sediment': 901.23},
            {'carbon': 817.93, 'nutrient': 671.58, 'sediment': 173.61},
        ]
        impact_parcels_vector = vector(impacts_polygons, COLOMBIA_SRS,
            impact_columns, impact_field_values, format='ESRI Shapefile')

        output_workspace = os.path.join(os.getcwd(), 'test_select_offsets')
        output_vector = os.path.join(output_workspace, 'output_vector.shp')
        output_json = os.path.join(output_workspace, 'output_json.json')

        if os.path.exists(output_workspace):
            shutil.rmtree(output_workspace)
        os.makedirs(output_workspace)

        offset_tuple = offsets._select_offsets(ecosystems_vector,
            impact_parcels_vector, biodiversity_impacts, output_vector,
            output_json)

        self.assertEqual(offset_tuple, ([0, 2], {}))


    def test_select_offsets_no_impacts(self):
        ecosystems_polygons = map(lambda x: test_smoke.square((x, 20), 10), [20, 60,
            100, 140])
        ecosystems_fields = {
            'ecosystem': str,
            'LCI': float,
            'carbon': float,
            'nutrient': float,
            'sediment': float,
        }
        ecosystems_attributes = [
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 822.82,
                'nutrient': 357.12, 'sediment': 395.82},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 396.34,
                'nutrient': 934.77, 'sediment': 121.27},
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 831.61,
                'nutrient': 136.92, 'sediment': 379.30},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 402.12,
                'nutrient': 829.71, 'sediment': 571.09},
        ]
        ecosystems_vector = vector(ecosystems_polygons, COLOMBIA_SRS,
            ecosystems_fields, ecosystems_attributes, format='ESRI Shapefile')
        biodiversity_impacts = {
                'eco_a': {
                    'min_impacted_parcel_area': 0,
                    'min_lci': 0,
                    'max_threat': None,
                    'min_richness': None,
                    'mitigation_area': 0,
                },
                'eco_b': {
                    'min_impacted_parcel_area': 0,
                    'min_lci': 0,
                    'max_threat': None,
                    'min_richness': None,
                    'mitigation_area': 0,
                }
            }

        impacts_polygons = map(lambda x: test_smoke.square((x, 50), 10), [40,
            80])
        impact_columns = {
            'carbon': float,
            'sediment': float,
            'nutrient': float,
        }
        impact_field_values = [
            {'carbon': 0.0, 'nutrient': 0.0, 'sediment': 0.0},
            {'carbon': 0.0, 'nutrient': 0.0, 'sediment': 0.0},
        ]
        impact_parcels_vector = vector(impacts_polygons, COLOMBIA_SRS,
            impact_columns, impact_field_values, format='ESRI Shapefile')

        output_workspace = os.path.join(os.getcwd(), 'test_select_offsets')
        output_vector = os.path.join(output_workspace, 'output_vector.shp')
        output_json = os.path.join(output_workspace, 'output_json.json')

        if os.path.exists(output_workspace):
            shutil.rmtree(output_workspace)
        os.makedirs(output_workspace)

        offset_tuple = offsets._select_offsets(ecosystems_vector,
            impact_parcels_vector, biodiversity_impacts, output_vector,
            output_json)

        self.assertEqual(offset_tuple, ([0, 1, 2, 3], {}))

    def test_select_offsets_scheme_es_and_bio(self):
        ecosystems_polygons = map(lambda x: test_smoke.square((x, 20), 10), [20, 60,
            100, 140])
        ecosystems_fields = {
            'ecosystem': str,
            'LCI': float,
            'carbon': float,
            'nutrient': float,
            'sediment': float,
        }
        ecosystems_attributes = [
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 822.82,
                'nutrient': 357.12, 'sediment': 395.82},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 396.34,
                'nutrient': 934.77, 'sediment': 121.27},
            {'ecosystem': 'eco_a', 'LCI': 0.1, 'carbon': 831.61,
                'nutrient': 136.92, 'sediment': 379.30},
            {'ecosystem': 'eco_b', 'LCI': 0.1, 'carbon': 402.12,
                'nutrient': 829.71, 'sediment': 571.09},
        ]
        ecosystems_vector = vector(ecosystems_polygons, COLOMBIA_SRS,
            ecosystems_fields, ecosystems_attributes, format='ESRI Shapefile')
        biodiversity_impacts = {
                'eco_a': {
                    'min_impacted_parcel_area': 0,
                    'min_lci': 0,
                    'max_threat': None,
                    'min_richness': None,
                    'mitigation_area': 0,
                },
                'eco_b': {
                    'min_impacted_parcel_area': 0,
                    'min_lci': 0,
                    'max_threat': None,
                    'min_richness': None,
                    'mitigation_area': 0,
                }
            }

        impacts_polygons = map(lambda x: test_smoke.square((x, 50), 10), [40,
            80])
        impact_columns = {
            'carbon': float,
            'sediment': float,
            'nutrient': float,
        }
        impact_field_values = [
            {'carbon': 0.0, 'nutrient': 0.0, 'sediment': 0.0},
            {'carbon': 0.0, 'nutrient': 0.0, 'sediment': 0.0},
        ]
        impact_parcels_vector = vector(impacts_polygons, COLOMBIA_SRS,
            impact_columns, impact_field_values, format='ESRI Shapefile')

        output_workspace = os.path.join(os.getcwd(), 'test_select_offsets')
        output_vector = os.path.join(output_workspace, 'output_vector.shp')
        output_json = os.path.join(output_workspace, 'output_json.json')

        if os.path.exists(output_workspace):
            shutil.rmtree(output_workspace)
        os.makedirs(output_workspace)

        offset_tuple = offsets._select_offsets(ecosystems_vector,
            impact_parcels_vector, biodiversity_impacts, output_vector,
            output_json)

        self.assertEqual(offset_tuple, ([0, 1, 2, 3], {}))

    def translate_percent_overlap_to_sshed_data(self):
        sample_dict = {
            0: {
                "Aoi": 0.0,
                "Area": 24769554.721130043,
                "Carbon": 660488.5930480957,
                "City": 0.0,
                "Distance": 105299.1312844463,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.030022655251212,
                "Nitrogen": 15000.409298000042,
                "Sediment": 52037.28566128289,
                "municipalities": {
                    "CASABE_05893": 1.0,
                    "CONCORDIA_47205": 1.0,
                    "SAN LUIS_47798": 1.0
                }
            },
            4: {
                "Aoi": 0.0,
                "Area": 39053053.690533355,
                "Carbon": 1046098.0106658936,
                "City": 0.0,
                "Distance": 111860.43849765629,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.017458507801602,
                "Nitrogen": 22452.06991350127,
                "Sediment": 60673.52671940386,
                "municipalities": {
                    "CASABE_05893": 0.998,
                    "CONCORDIA_47205": 1.0,
                    "SAN PABLO_13670": 0.001,
                }
            },
        }

        expected_parcels = {
            0: {
                'carbon': 660488.5930480957,
                'nutrient': 15000.409298000042,
                'sediment': 52037.28566128289,
                'area': 24769554.721130043,
                'ecosystem': "Bosques naturales",
                'overlap': {
                    'CASABE_05893': 1.0,
                    'CONCORDIA_47205': 1.0,
                    'SAN LUIS_47798': 1.0,
                }
            },
            4: {
                "area": 39053053.690533355,
                "carbon": 1046098.0106658936,
                "nutrient": 22452.06991350127,
                "sediment": 60673.52671940386,
                "ecosystem": "Bosques naturales",
                'overlap': {
                    'CASABE_05893': 0.998,
                    'CONCORDIA_47205': 1.0,
                    'SAN PABLO_13670': 0.001,
                }
            },
        }

        returned_parcels = offsets.translate_parcel_data(sample_dict)

        self.assertEqual(expected_parcels, returned_parcels)

    def test_translate_es_impacts(self):
        sample_dict = {
            0: {
                "Aoi": 0.0,
                "Area": 24769554.721130043,
                "Carbon": 660488.5930480957,
                "City": 0.0,
                "Distance": 105299.1312844463,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.030022655251212,
                "Nitrogen": 15000.409298000042,
                "Sediment": 52037.28566128289,
                "municipalities": {
                    "CASABE_05893": 1.0,
                    "CONCORDIA_47205": 1.0,
                    "SAN LUIS_47798": 1.0
                }
            },
            4: {
                "Aoi": 0.0,
                "Area": 39053053.690533355,
                "Carbon": 1046098.0106658936,
                "City": 0.0,
                "Distance": 111860.43849765629,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.017458507801602,
                "Nitrogen": 22452.06991350127,
                "Sediment": 60673.52671940386,
                "municipalities": {
                    "CASABE_05893": 0.998,
                    "CONCORDIA_47205": 1.0,
                    "SAN PABLO_13670": 0.001,
                }
            },
        }

        expected_parcels = {
            'CASABE_05893': {
                'carbon': 1704494.4076926573,
                'sediment': 112589.46532724795,
                'nutrient': 37407.575071674306,
            },
            'CONCORDIA_47205': {
                'carbon': 1706586.6037139893,
                'sediment': 112710.81238068675,
                'nutrient': 37452.47921150131,
            },
            'SAN PABLO_13670': {
                'carbon': 1046.0980106658935,
                'sediment': 60.67352671940386,
                'nutrient': 22.45206991350127,
            },
            'SAN LUIS_47798': {
                'carbon': 660488.5930480957,
                'sediment': 52037.28566128289,
                'nutrient': 15000.409298000042,
            }
        }
        returned_parcels = offsets.translate_es_impacts(sample_dict)
        self.assertEqual(expected_parcels, returned_parcels)

    def test_group_offsets_by_sshed(self):
        sample_dict = {
            0: {
                "Aoi": 0.0,
                "Area": 24769554.721130043,
                "Carbon": 660488.5930480957,
                "City": 0.0,
                "Distance": 105299.1312844463,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.030022655251212,
                "Nitrogen": 15000.409298000042,
                "Sediment": 52037.28566128289,
                "municipalities": {
                    "CASABE_05893": 1.0,
                    "CONCORDIA_47205": 1.0,
                    "SAN LUIS_47798": 1.0
                }
            },
            4: {
                "Aoi": 0.0,
                "Area": 39053053.690533355,
                "Carbon": 1046098.0106658936,
                "City": 0.0,
                "Distance": 111860.43849765629,
                "Ecosystem": "Bosques naturales",
                "Hydrozone": 0.0,
                "Lci": 0.017458507801602,
                "Nitrogen": 22452.06991350127,
                "Sediment": 60673.52671940386,
                "municipalities": {
                    "CASABE_05893": 0.998,
                    "CONCORDIA_47205": 1.0,
                    "SAN PABLO_13670": 0.001,
                }
            },
        }

        expected_groupings = {
            "CASABE_05893": [0, 4],
            "CONCORDIA_47205": [0, 4],
            "SAN PABLO_13670": [4],
            "SAN LUIS_47798": [0],
        }
        returned_groupings = offsets.group_offset_parcels_by_sshed(sample_dict)
        self.assertEqual(returned_groupings, expected_groupings)

