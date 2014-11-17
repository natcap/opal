import glob
import os

from osgeo import ogr

from invest_natcap import raster_utils

def main(simulations_dir, csv_uri, base_sdr_raster, base_sed_export, scenario_static_map_uri, flow_accumulation, scenario_usle_sm=None):
    watershed_data = {}  # map watershed IDs to dictionaries of impact data
    watershed_glob = os.path.join(simulations_dir, 'watershed_[0-9]*')
    for ws_dirname in glob.glob(watershed_glob):
        watershed_number = int(os.path.basename(ws_dirname).split('_')[-1])
        watershed_data[watershed_number] = {}

        impacts_glob = os.path.join(ws_dirname, 'random_impact_[0-9]*')
        for impact_dirname in glob.glob(impacts_glob):
            impact_number = int(os.path.basename(impact_dirname).split('_')[-1])
            impact_shp = os.path.join(impact_dirname, 'impact_%s.shp' %
                impact_number)
            converted_sdr = os.path.join(impact_dirname, 'intermediate',
                'sdr_factor.tif')
            impact_sed_export = os.path.join(impact_dirname, 'output',
                'sed_export.tif')

            print watershed_number, impact_number
            current_sdr = raster_utils.aggregate_raster_values_uri(
                base_sdr_raster, impact_shp, 'id').pixel_mean[1]
            try:
                converted_sdr = raster_utils.aggregate_raster_values_uri(
                    converted_sdr, impact_shp, 'id').pixel_mean[1]
            except AttributeError:
                # when the converted scenario SDR raster does not yet exist, we
                # want to skip this whole impact.
                continue

            # get the impact site area
            impact_vector = ogr.Open(impact_shp)
            impact_layer = impact_vector.getLayer()
            impact_feature = impact_layer.getFeature(0)
            impact_geom = impact_feature.GetGeometryRef()
            impact_area = impact_geom.Area()

            static_estimate = raster_utils.aggregate_raster_values_uri(
                scenario_static_map_uri, impact_shp, 'id').total[1]

            base_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                base_sed_export, impact_shp, 'id').pixel_mean[1]
            impact_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                impact_sed_export, impact_shp, 'id').pixel_mean[1]
            invest_estimate = base_sed_exp_estimate - impact_sed_exp_estimate

            max_f_a_impact = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_shp, 'id').pixel_max[1]
            mean_f_a_impact = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_shp, 'id').pixel_mean[1]

            extracted_data = {
                'disk_ws_id': watershed_number - 1,
                'impact_area': impact_area,
                'mean_current_sdr': current_sdr,
                'mean_converted_sdr': converted_sdr,
                'static_estimate': static_estimate,
                'invest_estimate': invest_estimate,
                'estimate_ratio': static_estimate / invest_estimate,
                'mean_current_sed_exp': base_sed_exp_estimate,
                'mean_converted_sed_exp': impact_sed_exp_estimate,
                'max_flow_accumulation': max_f_a_impact,
                'mean_flow_accumulation': mean_f_a_impact,
            }

            if scenario_usle_sm is not None:
                usle_sum = raster_utils.aggregate_raster_values_uri(
                    scenario_usle_sm, impact_shp, 'id').total[1]
                extracted_data['usle_sum'] = usle_sum

            watershed_data[watershed_number][impact_number] = extracted_data

    csv_file = open(csv_uri, 'w')
    labels = ['ws_id', 'Impact ID', 'Mean current SDR under impact',
        'Mean converted SDR under impact']

    if scenario_usle_sm is not None:
        labels.append('Total delta-USLE*sdr')

    first_elem = lambda x: x[0]
    csv_file.write("%s\n" % ','.join(labels))
    for ws_id, impacts_dict in sorted(watershed_data.iteritems(), key=first_elem):
        for impact_id, impact_data in sorted(impacts_dict.iteritems(), key=first_elem):
            line_data = [
                ws_id + 1,
                impact_id,
                impact_data['mean_current_sdr'],
                impact_data['mean_converted_sdr']]

            if scenario_usle_sm is not None:
                line_data.append(impact_data['usle_sum'])

            csv_file.write("%s\n" % ','.join(map(str, line_data)))
    csv_file.close()
    print 'done!'

if __name__ == '__main__':
    for simulation in ['paved', 'bare']:
        #sdr_raster = '/colossus/colombia_sdr/%s/%s_converted/intermediate/sdr_factor.tif' % (simulation, simulation)
        col_sdr = '/colossus/colombia_sdr/'
        _current_sdr = col_sdr + 'base_run/intermediate/sdr_factor.tif'
        _simulations_dir = col_sdr + '%s/simulations' % simulation
        _usle_static_map = col_sdr + '%s_usle_static_map.tif' % simulation
        _sed_export_static_map = col_sdr + '%s_static_map.tif' % simulation
        _base_sed_export = col_sdr + 'base_run/output/sed_export.tif'
        _flow_accumulation = col_sdr + 'base_run/prepared_data/flow_accumulation.tif'
        _csv_file = os.path.join(os.getcwd(), '%s_extracted_sdr_values.csv') % simulation
        main(simulations_dir=_simulations_dir,
            csv_uri=_csv_file,
            base_sdr_raster=_current_sdr,
            base_sed_export=_base_sed_export,
            scenario_static_map_uri=_sed_export_static_map,
            flow_accumulation=_flow_accumulation,
            scenario_usle_sm=_usle_static_map)


