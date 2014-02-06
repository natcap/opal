import json
import os
import shutil

from invest_natcap.testing import GISTest
from invest_natcap import raster_utils

from adept import preprocessing

DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_tool_data')
TEST_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_testing')
CLIPPED_DATA = os.path.join(os.getcwd(), '..', 'data', 'colombia_clipped')

class PreprocessingTest(GISTest):
    def test_split_multipolygons(self):
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')

        workspace = os.path.join(os.getcwd(), 'test_split_workspace')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

        os.makedirs(workspace)
        out_vector = os.path.join(workspace, 'test_split.shp')

        preprocessing.split_multipolygons(ecosystems, out_vector, ['Ecos_dis',
            'Ecosistema', 'FACTOR_DE'])

#        raster_uri = os.path.join(DATA, 'ecosystems.tif')
#        raster_stats = raster_utils.aggregate_raster_values_uri(raster_uri, out_vector,
#            shapefile_field='FID')
#
#        json_file = open(os.path.join(workspace, 'raster_stats.json'), 'w')
#        raster_stats_dict = {
#            'total': raster_stats.total,
#            'pixel_mean': raster_stats.pixel_mean,
#            'hectare_mean': raster_stats.hectare_mean,
#            'n_pixels': raster_stats.n_pixels,
#            'pixel_min': raster_stats.pixel_min,
#            'pixel_max': raster_stats.pixel_max,
#        }
#        json.dump(raster_stats_dict, json_file, indent=4)
#        json_file.close()

    def test_locate_intersecting_polygons_all_parcels(self):
        workspace = os.path.join(os.getcwd(), 'test_split_workspace')
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        hydrozones_output_vector = os.path.join(workspace, 'focal_hydrozones.shp')
        impact_vector = os.path.join(TEST_DATA, 'multi_hydrozone_impacts.shp')
        ecosystems = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        crop_vector = os.path.join(DATA, 'hydrozones.shp')
        out_vector = os.path.join(workspace, 'test_crop.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        split_vector = os.path.join(workspace, 'split_ecosystems.shp')

        preprocessing.split_multipolygons(ecosystems, split_vector)
        preprocessing.locate_intersecting_polygons(hydrozones, impact_vector,
                hydrozones_output_vector)
        preprocessing.locate_intersecting_polygons(split_vector, hydrozones_output_vector,
                out_vector)

    def test_prepare_impact_sites(self):
        services = [
            ('sediment', os.path.join(DATA, 'ecosystems.tif'))
        ]
        workspace = os.path.join(os.getcwd(), 'output_ag_stats')
        impact_sites = os.path.join(DATA, 'Example permitting footprints',
            'Example_mining_projects.shp')
        out_vector = os.path.join(workspace, 'output.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        preprocessing.prepare_impact_sites(impact_sites, services,
            out_vector)

    def test_prepare_offset_parcels(self):
#        services = [
#            ('sediment', os.path.join(DATA, 'ecosystems.tif'))
#        ]
        workspace = os.path.join(os.getcwd(), 'output_ag_stats')
        offset_parcels = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        impact_vector = os.path.join(TEST_DATA, 'multi_hydrozone_impacts.shp')
        out_vector = os.path.join(workspace, 'offset_parcels.shp')

        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        sample_aoi = os.path.join(DATA, 'sample_aoi.shp')
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        focal_hydrozones = os.path.join(workspace, 'focal_hydrozone.shp')

        preprocessing.locate_intersecting_polygons(hydrozones, impact_vector,
                focal_hydrozones)

        preprocessing.prepare_offset_parcels(offset_parcels, focal_hydrozones,
            impact_vector, out_vector)

    def test_locate_intersecting_polygons(self):
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        impact_vector = os.path.join(TEST_DATA, 'multi_hydrozone_impacts.shp')
        workspace = os.path.join(os.getcwd(), 'output_hydrozone')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)
        output_vector = os.path.join(workspace, 'focal_hydrozones.shp')

        preprocessing.locate_intersecting_polygons(hydrozones, impact_vector, output_vector)

    def test_union(self):
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        impact_vector = os.path.join(TEST_DATA, 'multi_hydrozone_impacts.shp')
        workspace = os.path.join(os.getcwd(), 'output_hydrozone')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)
        output_vector = os.path.join(workspace, 'focal_hydrozones.shp')
        aoi_vector = os.path.join(TEST_DATA, 'multi_hydrozone_aoi.shp')
        aoi_and_hydrozones = os.path.join(workspace, 'union.shp')

        preprocessing.locate_intersecting_polygons(hydrozones, impact_vector, output_vector)
        preprocessing.union_of_vectors([output_vector, aoi_vector],
            aoi_and_hydrozones)

    def test_difference(self):
        hydrozones = os.path.join(DATA, 'hydrozones.shp')
        impact_vector = os.path.join(TEST_DATA, 'multi_hydrozone_impacts.shp')
        workspace = os.path.join(os.getcwd(), 'output_difference')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        output_vector = os.path.join(workspace, 'difference.shp')
        preprocessing.subtract_vectors(hydrozones, impact_vector,
                output_vector)

    def test_lci(self):
        natural_parcels = os.path.join(DATA, 'ecosys_dis_nat_comp_fac.shp')
        #natural_parcels = os.path.join(CLIPPED_DATA, 'ecosystems_colombia.shp')

        workspace = os.path.join(os.getcwd(), 'sample_lci')
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.makedirs(workspace)

        split_polygons = os.path.join(workspace, 'split_polygons.shp')
        preprocessing.split_multipolygons(natural_parcels, split_polygons)

        lci_dict = preprocessing.calculate_lci(split_polygons)

        print lci_dict

