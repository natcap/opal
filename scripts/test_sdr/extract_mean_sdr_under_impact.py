import glob
import os

from invest_natcap import raster_utils

def main(simulations_dir, csv_uri, base_sdr_raster, scenario_usle_sm=None):
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

            extracted_data = {
                'mean_current_sdr': current_sdr,
                'mean_converted_sdr': converted_sdr
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
            line_data = [ws_id + 1, impact_id,
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
        sdr_raster = '/colossus/colombia_sdr/base_run/intermediate/sdr_factor.tif'
        simulations_dir = '/colossus/colombia_sdr/%s/simulations' % simulation
        usle_static_map = '/colossus/colombia_sdr/%s_usle_static_map.tif' % simulation
        csv_file = os.path.join(os.getcwd(), '%s_extracted_sdr_values.csv') % simulation
        main(simulations_dir, csv_file, sdr_raster, usle_static_map)


