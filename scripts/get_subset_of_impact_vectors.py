import os
import glob
import shutil

if __name__ == '__main__':
    source_file_uri = os.path.join(os.path.dirname(__file__), '..',
        'positive_sdr_simulations.csv')

    scenario = 'bare'
    dest_dir = '%s_positive_simulations' % scenario
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)

    filepath_pattern = os.path.join('/colossus', 'colombia_sdr',
        scenario,
        'simulations',
        'watershed_%s',
        'random_impact_%s',
        'impact_%s.*'
    )

    source_file = open(source_file_uri)
    line_index = 0
    for line in source_file:
        if line_index == 0:
            line_index += 1
            continue

        ws_index, impact_index = line.split(',')[:2]
        ws_index = int(ws_index)
        impact_index = int(impact_index)

        complete_pattern = filepath_pattern % (ws_index - 1, impact_index,
            impact_index)
        for file_uri in glob.glob(complete_pattern):
            base, ext = os.path.splitext(os.path.basename(file_uri))

            new_filename = 'ws%s_impact%s%s' % (ws_index, impact_index, ext)
            new_uri = os.path.join(dest_dir, new_filename)
            shutil.copyfile(file_uri, new_uri)
