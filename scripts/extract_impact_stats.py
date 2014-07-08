"""Script to extract stats from random impacts that have already been analyzed."""


import glob
import os
import multiprocessing

from adept import static_maps
from invest_natcap import raster_utils

def extract_impact_data(service, scenario_dir, base_export_raster):
    base_watersheds = os.path.join(os.getcwd(), 'data', 'colombia_tool_data',
        'watersheds_cuencas.shp')

    model_name = service
    scenario = scenario_dir.split('/')[-1].lower()

    base_static_map = os.path.join(os.getcwd(), 'data', 'colombia_static_data',
            '%s_%s_static_map_lzw.tif' % (model_name, scenario))
    base_stats = raster_utils.aggregate_raster_values_uri(base_export_raster,
        base_watersheds, 'ws_id', 'sum').total

    logfile_uri = os.path.join(scenario_dir,
        '%s_%s_scraped_sims.csv' % (model_name, scenario))
    logfile = open(logfile_uri, 'w')
    labels = ['ws_id', 'Impact ID', 'Impact area', 'Static estimate',
        'InVEST estimate', 'Estimate ratio']
    logfile.write('%s\n' % ','.join(labels))

    for watershed_id in range(54):
        watershed_dir = os.path.join(scenario_dir, 'watershed_%s' %
            watershed_id)
        watershed_vector = os.path.join(scenario_dir, 'watershed_vectors',
            'feature_%s.shp' % watershed_id)

        glob_pattern = os.path.join(watershed_dir, 'random_impact_*')
        for impact_dir in glob.glob(glob_pattern):
            run_number = impact_dir.split('_')[-1]  # get the impact index
            impact_stats = static_maps.compute_impact_stats(impact_dir,
                model_name, watershed_vector, base_stats[watershed_id + 1],
                base_static_map)

            stats_to_write = [watershed_id, run_number,
                impact_stats['impact_site_area'],
                impact_stats['static_estimate'],
                impact_stats['invest_estimate'],
                impact_stats['export_ratio'],
            ]
            logfile.write('%s\n' % ','.join(map(str, stats_to_write)))
    logfile.close()

    out_png = os.path.join(scenario_dir, '%s_%s_plot.png' % (model_name,
        scenario))
    static_maps.graph_it(logfile_uri, out_png)

if __name__ == '__main__':
    #watershed_base_dir = 'F:/sediment_map_quality_backup/Bare'
    #watershed_base_dir = '/home/jadoug06/workspace/invest-natcap.permitting/ignore_me/sediment_map_quality/bare'
    processes = []
    watershed_base_dir = '/colossus'
    for service in ['nutrient', 'sediment']:
        service_dir = os.path.join(watershed_base_dir, '%s_simulations' % service)
        base_export_raster = os.path.join(service_dir, 'base_run',
            static_maps.MODELS[service]['target_raster'])
        for scenario in ['bare', 'paved']:
            scenario_dir = os.path.join(service_dir, scenario)
            print scenario_dir
            p = multiprocessing.Process(target=extract_impact_data,
                args=(service, scenario_dir, base_export_raster))
            p.start()
            processes.append(p)


    for p in processes:
        p.join()

