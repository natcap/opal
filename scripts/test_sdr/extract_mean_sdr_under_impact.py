import glob
import os

def main(simulations_dir, csv_uri):
    csv_file = open(csv_uri, 'w')
    labels = ['ws_id', 'Impact ID', 'Mean current SDR under impact',
        'Mean converted SDR under impact']

    watershed_data = {}  # map watershed IDs to dictionaries of impact data
    watershed_glob = os.path.join(simulations_dir, 'watershed_[0-9]*')
    for ws_dirname in glob.glob(watershed_glob):
        watershed_number = os.path.basename(ws_dirname).split('_')[-1]
        print 'WATERSHED', watershed_number
        impacts_glob = os.path.join(ws_dirname, 'random_impact_[0-9]*')
        for impact_dirname in glob.glob(impacts_glob):
            impact_number = os.path.basename(impact_dirname).split('_')[-1]
            print 'impact', impact_number
            impact_shp = os.path.join(impact_dirname, 'impact_%s.shp' %
                impact_number)
            print impact_shp


if __name__ == '__main__':
    simulations_dir = '/colossus/colombia_sdr/paved/simulations'
    csv_file = os.path.join(os.getcwd(), 'extracted_sdr_values.csv')
    main(simulations_dir, csv_file)
