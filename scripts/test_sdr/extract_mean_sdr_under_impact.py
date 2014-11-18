import glob
import os

from osgeo import ogr

from invest_natcap import raster_utils

def main(simulations_dir, csv_uri, base_sdr_raster, base_sed_export, scenario_static_map_uri, flow_accumulation, scenario_usle_sm=None):
    watershed_data = {}  # map watershed IDs to dictionaries of impact data
    watershed_glob = os.path.join(simulations_dir, 'watershed_[0-9]*')
    watersheds = glob.glob(watershed_glob)
    loop_index = 0
    for ws_dirname in watersheds:
        watershed_number = int(os.path.basename(ws_dirname).split('_')[-1])
        watershed_vector = os.path.join(simulations_dir, 'watershed_vectors',
            'feature_%s.shp' % watershed_number)
        ws_id = watershed_number + 1
        watershed_data[watershed_number] = {}
        base_sed_exp_estimate_ws = raster_utils.aggregate_raster_values_uri(
            base_sed_export, watershed_vector, 'ws_id').total[ws_id]

        impacts_glob = os.path.join(ws_dirname, 'random_impact_[0-9]*')
        for impact_dirname in glob.glob(impacts_glob):
            impact_number = int(os.path.basename(impact_dirname).split('_')[-1])
            impact_shp = os.path.join(impact_dirname, 'impact_%s.shp' %
                impact_number)
            converted_sdr = os.path.join(impact_dirname, 'intermediate',
                'sdr_factor.tif')
            impact_sed_export = os.path.join(impact_dirname, 'output',
                'sed_export.tif')

            print watershed_number, impact_number, '%s of %s' % (loop_index,
                len(watersheds))
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
            impact_layer = impact_vector.GetLayer()
            impact_feature = impact_layer.GetFeature(0)
            impact_geom = impact_feature.GetGeometryRef()
            impact_area = impact_geom.Area()

            static_estimate = raster_utils.aggregate_raster_values_uri(
                scenario_static_map_uri, impact_shp, 'id').total[1]

            impact_sed_exp_estimate_ws = raster_utils.aggregate_raster_values_uri(
                impact_sed_export, watershed_vector, 'ws_id').total[ws_id]
            invest_estimate = base_sed_exp_estimate_ws - impact_sed_exp_estimate_ws

            base_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                base_sed_export, impact_shp, 'id').total[1]
            impact_sed_exp_estimate = raster_utils.aggregate_raster_values_uri(
                impact_sed_export, impact_shp, 'id').total[1]

            max_f_a_impact = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_shp, 'id').pixel_max[1]
            mean_f_a_impact = raster_utils.aggregate_raster_values_uri(
                flow_accumulation, impact_shp, 'id').pixel_mean[1]

            extracted_data = {
                'disk_ws_id': watershed_number,
                'impact_area': impact_area,
                'static_estimate': static_estimate,
                'invest_estimate': invest_estimate,
                'estimate_ratio': static_estimate / invest_estimate,
                'mean_current_sdr': current_sdr,
                'mean_converted_sdr': converted_sdr,
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
        loop_index += 1

    csv_file = open(csv_uri, 'w')
    labels = ['ws_id',
        'Impact ID',
        'Impact Area',
        'Static Estimate',
        'InVEST Estimate',
        'Estimate Ratio',
        'Sed_exp under impact current',
        'Sed_exp under impact converted',
        'Mean current SDR under impact',
        'Mean converted SDR under impact',
        'Mean flow accumulation under impact',
        'Max flow accumulation under impact']

    if scenario_usle_sm is not None:
        labels.append('Total delta-USLE*sdr')

    first_elem = lambda x: x[0]
    csv_file.write("%s\n" % ','.join(labels))
    for ws_id, impacts_dict in sorted(watershed_data.iteritems(), key=first_elem):
        for impact_id, impact_data in sorted(impacts_dict.iteritems(), key=first_elem):
            line_data = [ws_id + 1,
                impact_id,
                impact_data['impact_area'],
                impact_data['static_estimate'],
                impact_data['invest_estimate'],
                impact_data['estimate_ratio'],
                impact_data['mean_current_sed_exp'],
                impact_data['mean_converted_sed_exp'],
                impact_data['mean_current_sdr'],
                impact_data['mean_converted_sdr'],
                impact_data['mean_flow_accumulation'],
                impact_data['max_flow_accumulation'],
            ]

            if scenario_usle_sm is not None:
                line_data.append(impact_data['usle_sum'])

            csv_file.write("%s\n" % ','.join(map(str, line_data)))
    csv_file.close()
    print 'done!'

def align_impact_rasters(raster_list, output_dir):
    def _output_raster(in_raster):
        tif_name = os.path.basename(in_raster)
        return os.path.join(output_dir, 'aligned_%s' % tif_name)

    output_raster_list = map(_output_raster, raster_list)
    resample_mathod_list = ['nearest'] * len(output_raster_list)
    out_pixel_size = raster_utils.get_cell_size_from_uri(raster_list[0])
    dataset_to_align_index=0

    raster_utils.align_dataset_list(raster_list, output_raster_list,
        resample_method_list, out_pixel_size, 'intersection',
        dataset_to_align_index)

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


