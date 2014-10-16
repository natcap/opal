import glob
import os

from invest_natcap import raster_utils

def main(simulations_dir, csv_uri, base_sdr_raster):
    watershed_data = {}  # map watershed IDs to dictionaries of impact data
    watershed_glob = os.path.join(simulations_dir, 'watershed_[0-9]*')
    for ws_dirname in glob.glob(watershed_glob):
        watershed_number = int(os.path.basename(ws_dirname).split('_')[-1])
        watershed_data[watershed_number] = {}

        impacts_glob = os.path.join(ws_dirname, 'random_impact_[0-9]*')
        for impact_dirname in glob.glob(impacts_glob):
            impact_number = os.path.basename(impact_dirname).split('_')[-1]
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

            watershed_data[watershed_number][impact_number] = {
                'mean_current_sdr': current_sdr,
                'mean_converted_sdr': converted_sdr
            }

    csv_file = open(csv_uri, 'w')
    labels = ['ws_id', 'Impact ID', 'Mean current SDR under impact',
        'Mean converted SDR under impact']
    first_elem = lambda x: x[0]
    csv_file.write("%s\n" % ','.join(labels))
    for ws_id, impacts_dict in sorted(watershed_data.iteritems(), key=first_elem):
        for impact_id, impact_data in sorted(impacts_dict.iteritems(), key=first_elem):
            line_data = [ws_id + 1, impact_id,
                impact_data['mean_current_sdr'],
                impact_data['mean_converted_sdr']]
            csv_file.write("%s\n" % ','.join(line_data))
    csv_file.close()
    print 'done!'

if __name__ == '__main__':
    sdr_raster = '/colossus/colombia_sdr/paved/paved_converted/intermediate/sdr_factor.tif'
    simulations_dir = '/colossus/colombia_sdr/paved/simulations'
    csv_file = os.path.join(os.getcwd(), 'extracted_sdr_values.csv')
    main(simulations_dir, csv_file, sdr_raster)
