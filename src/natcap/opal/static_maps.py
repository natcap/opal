import os
import json
import hashlib
import logging
from types import UnicodeType
from types import DictType
import multiprocessing
import shutil
import random
import tempfile
import sys
import distutils.sysconfig
import zipfile

from osgeo import gdal
from osgeo import ogr
from natcap.invest.sdr import sdr
from natcap.invest.nutrient import nutrient
from natcap.invest.carbon import carbon_combined as carbon
import pygeoprocessing
import numpy
import scipy

import preprocessing
import utils

LOGGER = logging.getLogger('natcap.opal.static_maps')
NODATA = 999999.0

COLOMBIA_BARE_LUCODE = 301
COLOMBIA_PAVED_LUCODE = 89

MODELS = {
    'carbon': {
        'module': carbon,
        'landcover_key': 'lulc_cur_uri',
        'target_raster': os.path.join('output', 'tot_C_cur.tif'),
        'watersheds_key': None,
    },
    'sediment': {
        'module': sdr,
        'landcover_key': 'lulc_uri',
        'target_raster': os.path.join('output', 'sed_export.tif'),
        'watersheds_key': 'watersheds_uri',
    },
    'nutrient': {
        'module': nutrient,
        'landcover_key': 'lulc_uri',
        'target_raster': os.path.join('output', 'n_export.tif'),
        'watersheds_key': 'watersheds_uri',
    }
}


def _write_future_json(workspace, future_type):
    """Write the future type to a json object at workspace/future_type.json.

        workspace - a URI to the static maps workspace.
        future_type - a string indicating the future type.  One of 'protection'
            or 'restoration'

    Returns nothing."""

    json_uri = os.path.join(workspace, 'future_type.json')
    json.dumps({'future_type': future_type}, open(json_uri, 'w'), indent=4,
               sort_keys=True)


def execute(args):
    """Entry point for generating static sediment maps.

        args - a python dictionary with the following attributes:
            workspace_dir (required)
            landuse_uri (required)
            landcover_code (required)
            future_type (required) - either 'protection' or 'restoration'
            model_name (required) - either 'carbon' or 'sediment'
            do_parallelism (optional) - Boolean.  Assumed to be False.
            fut_landuse_uri (optional) - URI.  If not present, a future
                landcover scenario will not be calculated.

            If model_name is 'sediment', these keys may be provided.  If they
            are not provided, default values will be assumed.
            dem_uri (optional)
            erosivity_uri (optional)
            erodibility_uri(optional)
            watersheds_uri (optional)
            biophysical_table_uri (optional)
            threshold_flow_accumulation (optional)
            slope_threshold (optional)
            sediment_threshold_table_uri (optional)

            If model_name is either 'sediment' or 'nutrient', the following
            is optional:
            num_simulations - an int indicating the number of impact sites
                that should be simulated per watershed.  If this key is not
                provided, static map quality estimates will be skipped.
            """

    for key in ['workspace_dir', 'landuse_uri', 'paved_landcover_code',
                'bare_landcover_code', 'model_name']:
        assert key in args, "Args is missing a key: %s" % key

    assert args['model_name'] in ['carbon', 'sediment', 'nutrient'], (
        'Model name must be one of "carbon", "sediment", or "nutrient",'
        'not %s' % args['model_name'])

    if not os.path.exists(args['workspace_dir']):
        os.makedirs(args['workspace_dir'])
        LOGGER.debug('Creating new workspace: %s', args['workspace_dir'])

    # create a logging handler and write its contents out to the logfile.
    log_handler = logging.FileHandler(os.path.join(args['workspace_dir'],
                                                   'logfile.txt'))
    log_formatter = logging.Formatter(
        fmt=(
            '%(asctime)s %(name)-18s '
            '%(threadName)-10s %(levelname)-8s %(message)s'),
        datefmt='%m/%d/%Y %H:%M:%S ')
    log_handler.setFormatter(log_formatter)
    LOGGER.addHandler(log_handler)

    temp_dir = os.path.join(args['workspace_dir'], 'tmp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    tempfile.tempdir = temp_dir

    if args['model_name'] == 'carbon':
        args['lulc_cur_uri'] = args['landuse_uri']
    elif args['model_name'] in ['nutrient', 'sediment']:
        args['lulc_uri'] = args['landuse_uri']

    model_args = {}
    default_config = get_static_data_json(args['model_name'])
    for key, value in default_config.iteritems():
        if key in args:
            model_args[key] = args[key]
        else:
            model_args[key] = value

    if args['model_name'] == 'sediment':
        # we're ok with the landuse dictionary key.
        # clip the DEM to the landcover raster
        new_dem_uri = os.path.join(
            model_args['workspace_dir'],
            'clipped_dem.tif')
        LOGGER.debug('Current DEM: %s', model_args['dem_uri'])
        LOGGER.debug('Saving clipped DEM to %s', new_dem_uri)
        _clip_dem(model_args['dem_uri'], model_args['lulc_uri'], new_dem_uri)
        model_args['dem_uri'] = new_dem_uri
    elif args['model_name'] == 'nutrient':
        # filter the watersheds to just those that intersect with the LULC.
        new_watersheds_uri = os.path.join(model_args['workspace_dir'],
                                          'watersheds_filtered.shp')
        preprocessing.filter_by_raster(
            model_args['lulc_uri'],
            model_args['watersheds_uri'],
            new_watersheds_uri)
        model_args['watersheds_uri'] = new_watersheds_uri
        model_args['soil_depth_uri'] = model_args[
            'depth_to_root_rest_layer_uri']
        try:
            model_args['eto_uri'] = args['potential_evapotranspiration']
        except KeyError:
            # MAFE uses the internal eto_uri, so we can skip.
            LOGGER.debug('No key "potential_evapotranspiration"')

    LOGGER.debug(
        'Using these model args:\n%s',
        json.dumps(
            model_args,
            sort_keys=True,
            indent=4))

    # now, run the sediment model on the input landcover
    LOGGER.info('Running the model on the original landscape')
    original_workspace = os.path.join(args['workspace_dir'],
                                      '%s_base' % args['model_name'])
    if not os.path.exists(original_workspace):
        os.makedirs(original_workspace)
        LOGGER.debug('Making workspace for base scenario: %s',
                     original_workspace)

    LOGGER.debug('Original workspace: %s', original_workspace)
    execute_model(args['model_name'], args['landuse_uri'], original_workspace,
                  model_args)
    base_raster = os.path.join(original_workspace,
                               MODELS[args['model_name']]['target_raster'])

    try:
        do_parallelism = args['do_parallelism']
        LOGGER.debug('Process-based parallelism enabled')
    except KeyError:
        LOGGER.debug('Process-based parallelism disabled')
        do_parallelism = False

    try:
        num_simulations = int(args['num_simulations'])
        LOGGER.debug('User requested to do %s simulations per watershed',
                     num_simulations)
    except KeyError:
        num_simulations = None
        LOGGER.debug('Skipping impact simulations')

    processes = []
    for impact_type in ['paved', 'bare']:
        continue  # Only want to do the future scenario right now.
        LOGGER.debug('Starting calculations for impact %s', impact_type)
        impact_code = args['%s_landcover_code' % impact_type]

        impact_workspace = os.path.join(args['workspace_dir'], impact_type)
        static_map_uri = os.path.join(
            args['workspace_dir'], '%s_%s_static_map.tif' %
            (args['model_name'], impact_type))

        # Carbon is the only known ES that has inverted values.
        invert = True if args['model_name'] == 'carbon' else False

        if do_parallelism:
            process = multiprocessing.Process(
                target=build_static_map,
                args=(
                    args['model_name'],
                    args['landuse_uri'],
                    impact_code,
                    static_map_uri,
                    base_raster,
                    model_args,
                    impact_workspace),
                kwargs={
                    'num_simulations': num_simulations,
                    'invert': invert})
            processes.append(process)
            process.start()
        else:
            build_static_map(
                args['model_name'],
                args['landuse_uri'],
                impact_code,
                static_map_uri,
                base_raster,
                model_args,
                impact_workspace,
                num_simulations=num_simulations,
                invert=invert)

    # Build the static protection map if the user has provided a future
    # landcover scenario.
    LOGGER.info('Found a future landcover.  Building (%s) map.',
                args['future_type'])
    if 'fut_landuse_uri' not in args:
        LOGGER.debug('No custom future lulc found.  Clipping default.')
        # if the user has not provided a custom lulc, we should clip the
        # existing future lulc to the size of the user-defined current lulc.
        common_data = get_common_data_json()
        future_landuse_uri = os.path.join(
            args['workspace_dir'],
            'future_landuse.tif')
        _clip_dem(common_data['future_landcover'], args['landuse_uri'],
                  future_landuse_uri)
    else:
        future_landuse_uri = args['fut_landuse_uri']
    LOGGER.debug('Future landcover %s', future_landuse_uri)

    # determine whether the future, converted landcover should be inverted,
    # based on protection or restoration.
    _write_future_json(args['workspace_dir'], args['future_type'])
    if args['future_type'] == 'protection':
        invert = True
        future_tif_name = 'protect'
    else:
        invert = False
        future_tif_name = 'restore'

    # if we're building carbon static maps, the invert flag is opposite of what
    # other models would do, for all cases.
    if args['model_name'] == 'carbon':
        invert = not invert

    future_map_uri = os.path.join(
        args['workspace_dir'], '%s_%s_static_map.tif' %
        (args['model_name'], future_tif_name))
    future_workspace = os.path.join(args['workspace_dir'], future_tif_name)
    build_static_map(args['model_name'], args['landuse_uri'], future_landuse_uri,
                     future_map_uri, base_raster, model_args, future_workspace,
                     convert_landcover=False,  # just use the future landcover
                     num_simulations=num_simulations, invert=invert)
    LOGGER.info('Completed the future (%s) static map.', args['future_type'])

    # If we aren't doing parallelism, then this list has no elements in it.
    for process in processes:
        process.join()

    # If we just ran the nutrient model, we need to copy the appropriate
    # percent-to-stream rasters to the root static maps directory.
    # Do this copy by recompressing the GeoTiff using DEFLATE instead of LZW.
    # See issue 2910 (code.google.com/p/invest-natcap/issues/detail?id=2910)

    if args['model_name'] in ['nutrient']:
        fmt_string = os.path.join(args['workspace_dir'], '%s',
            '%s_converted' % args['model_name'], 'intermediate')
        pts_name = 'n_percent_to_stream.tif'
        fmt_string = os.path.join(fmt_string, pts_name)

        percent_to_streams = [
            (fmt_string % 'paved', '%s_paved_pts.tif' % args['model_name']),
            (fmt_string % 'bare', '%s_bare_pts.tif' % args['model_name']),
            (fmt_string % future_tif_name, '%s_%s_pts.tif' %
                (args['model_name'], future_tif_name)),
        ]
        for source_uri, dest_uri in percent_to_streams:
            dest_uri = os.path.join(args['workspace_dir'], dest_uri)
            LOGGER.debug('Copying %s to %s', source_uri, dest_uri)
            preprocessing.recompress_gtiff(source_uri, dest_uri, 'DEFLATE')

    LOGGER.debug('Completed creating the %s static maps', args['model_name'])


def raster_math(args):
    """Perform all of the raster math to create static maps from the input
    model run rasters.

    args - a python dictionary with the following attributes:
        workspace_dir - a URI to the output workspace
        name - a string name to be used in the filename of all output static maps
        base_uri - a URI to a GDAL raster of the base scenario's service values.
        paved_uri - a URI to a GDAL raster of the paved scenario's service values.
        bare_uri - a URI to a GDAL raster of the bare scenario's service values.
        future_uri - a URI to a GDAL raster of the future scenario's
            service values.
        future_type - a string, either 'protection' or 'restoration'

    Returns None, but writes the following files to disk:
        workspace/<name>_bare_static_map.tif
        workspace/<name>_paved_static_map.tif
        workspace/<name>_future_static_map.tif"""
    workspace = args['workspace_dir']
    name = args['name']
    base_uri = args['base_uri']
    paved_uri = args['paved_uri']
    bare_uri = args['bare_uri']
    future_uri = args['future_uri']
    future_scenario = args['future_type']
    _write_future_json(workspace, future_scenario)

    if not os.path.exists(workspace):
        LOGGER.debug('Creating output workspace %s', workspace)
        os.makedirs(workspace)

    def _ws_path(static_map_type):
        return os.path.join(workspace,
                            '%s_%s_static_map.tif' % (name, static_map_type))

    future_tif_base = 'protect' if future_scenario == 'protection' else 'restore'

    bare_sm_uri = _ws_path('bare')
    paved_sm_uri = _ws_path('paved')
    future_sm_uri = _ws_path(future_tif_base)

    # create the bare static map
    LOGGER.debug('Creating the bare static map %s', bare_sm_uri)
    subtract_rasters(bare_uri, base_uri, bare_sm_uri)

    # create the paved static map
    LOGGER.debug('Creating the paved static map %s', paved_sm_uri)
    subtract_rasters(paved_uri, base_uri, paved_sm_uri)

    # create the future static map
    LOGGER.debug(
        'Creating the %s static map %s',
        future_scenario,
        future_sm_uri)
    if future_scenario == 'protection':
        subtract_rasters(base_uri, future_uri, future_sm_uri)
    else:  # when args['future_type'] is 'restoration'
        subtract_rasters(future_uri, base_uri, future_sm_uri)

    LOGGER.debug('Finished creating the static maps')


def _clip_dem(dem_uri, lulc_uri, out_dem_uri):
    """Clip the input DEM to the LULC and save the resulting raster to the
    out_dem_uri."""
    utils.assert_files_exist([dem_uri, lulc_uri])
    nodata = pygeoprocessing.get_nodata_from_uri(dem_uri)
    pixel_size = pygeoprocessing.get_cell_size_from_uri(dem_uri)
    datatype = pygeoprocessing.get_datatype_from_uri(dem_uri)

    pygeoprocessing.vectorize_datasets([dem_uri, lulc_uri], lambda x, y: x,
        dataset_out_uri=out_dem_uri, datatype_out=datatype, nodata_out=nodata,
        pixel_size_out=pixel_size, bounding_box_mode='intersection',
        vectorize_op=False)

def convert_lulc(lulc_uri, new_code, out_uri):
    """Use vectorize_datasets to convert a land cover raster to a new landcover
    code and save it to an output dataset.

        lulc_uri - a uri to a GDAL landcover raster on disk.
        new_code - an integer landcover code
        out_uri - a uri to which the converted landcover will be written

        Returns nothing."""

    utils.assert_files_exist([lulc_uri])
    nodata = pygeoprocessing.get_nodata_from_uri(lulc_uri)

    # unless there's a nodata value, we want to change all pixels to the new
    # lulc code.
    def _convert(pixels):
        return numpy.where(pixels != nodata, new_code, nodata)

    pixel_size = pygeoprocessing.get_cell_size_from_uri(lulc_uri)
    datatype = pygeoprocessing.get_datatype_from_uri(lulc_uri)
    pygeoprocessing.vectorize_datasets([lulc_uri], _convert,
        dataset_out_uri=out_uri, datatype_out=datatype,
        nodata_out=nodata, pixel_size_out=pixel_size,
        bounding_box_mode='intersection', vectorize_op=False)

def unzip_static_zipfile(zipfile_uri):
    """Unzip the given file to the static maps folder."""

    utils.assert_files_exist([zipfile_uri])
    with zipfile.ZipFile('test.zip', 'r') as zip_archive:
        static_data_dir = os.path.join(os.getcwd(), 'data',
                                       'colombia_static_data')
        zip_archive.extractall(static_data_dir)


def execute_model(model_name, landcover_uri, workspace_uri, config=None):
    assert model_name in MODELS.keys()

    # if config is None, then we load the static_map parameters from the
    # correct internal json file.
    # if it's not None, then it must be a configuration dictionary.
    if config is None:
        config = get_static_data_json(model_name)
    else:
        assert isinstance(config, DictType), ("Found %s: %s" % (
            type(config), config))

    # - loop through each key in the configuration file.
    #    * if it's a path, make it relative to the CWD
    #    * if it's not a path, leave it alone.
    new_config = {}
    for key, value in config.iteritems():
        if isinstance(value, UnicodeType):
            try:
                new_value = float(value)
            except ValueError:
                if len(value) > 0:
                    if not os.path.exists(value):
                        new_value = os.path.join(os.getcwd(), '..', value)
                    else:
                        # if the user-defined file does exist, just use that.
                        new_value = value
                else:
                    new_value = value
        else:
            new_value = value
        new_config[key] = new_value

    # - add the new keys needed for the model run:
    #    * workspace_uri - use the URI passed in to this function.
    #    * landcover_uri - use the URI passed in to this function.
    new_config['workspace_dir'] = workspace_uri
    new_config[MODELS[model_name]['landcover_key']] = landcover_uri

    LOGGER.debug(
        'Executing model with arguments: %s',
        json.dumps(
            new_config,
            sort_keys=True,
            indent=4))
    MODELS[model_name]['module'].execute(new_config)


def build_static_map(
        model_name,
        landcover_uri,
        landcover_code,
        static_map_uri,
        base_run,
        config=None,
        workspace=None,
        convert_landcover=True,
        num_simulations=None,
        invert=False):
    """Build the static map for the target ecosystem service.  Currently assumes
    we're doing sediment only.

        model_name - a string.  Must be a key in MODELS.
        landcover_uri - a URI to the user's input landcover.  A raster.
        landcover_core - an integer landcover code to convert to.
        static_map_uri - a URI to where the output static map should be written
        base_run - a URI to the output map from a base run of the target model.
        config=None - a python dictionary with arguments for the target model.  If
            None, the defaults will be loaded from internal defaults.
        workspace=None - the output workspace to which the model runs should be
            written.  If None, they will be saved to a temporary folder and
            deleted at the end of the static map generation.
        base_run=None - A uri to a workspace of the target model.
        num_simulations=None - number of simulations to run per watershed.  If
            None, no simulations will be run.
        invert=False - whether to invert the subtraction.  When invert==False,
            the static map produced will be the difference of `base_run` -
            `converted`, where `converted` is the converted or input landcover.
            When invert==True, the static map produced will be the differece
            of `converted` - `base_run`.
    """
    assert invert in [True, False], '%s found instead' % type(invert)
    assert model_name in MODELS.keys()
    LOGGER.info('Building static map for the %s model', model_name)

    if workspace is not None:
        LOGGER.debug('Using workspace %s', workspace)
        if not os.path.exists(workspace):
            LOGGER.debug('Creating workspace folder %s', workspace)
            os.makedirs(workspace)
    else:
        workspace = pygeoprocessing.temporary_folder()
        LOGGER.debug('Writing model workspace data to %s', workspace)

    # convert the LULC to the correct landcover code
    if convert_landcover:
        converted_lulc = os.path.join(workspace, 'converted_lulc.tif')
        LOGGER.info('Creating converted landcover raster: %s', converted_lulc)
        convert_lulc(landcover_uri, landcover_code, converted_lulc)
        landcover_label = str(landcover_code)
    else:
        converted_lulc = landcover_uri
        landcover_label = 'transformed'

    LOGGER.info('Running the model on the converted landcover')
    # run the sediment model on the converted LULC
    target_raster = MODELS[model_name]['target_raster']
    converted_workspace = os.path.join(workspace, '%s_converted' % model_name)
    LOGGER.debug('Converted workspace: %s', converted_workspace)
    execute_model(model_name, converted_lulc, converted_workspace, config)
    converted_es_map = os.path.join(converted_workspace, target_raster)

    # subtract the two rasters.
    # If we're running the carbon model, the service we're measuring (carbon
    # storage) has positive values being 'good'  For sediment and nutrient,
    # however, positive values represent sediment/nutrient export to the steam,
    # which is 'bad'.  For sediment and nutrient, we want to invert the result.
    # This is done by just reversing the order of the subtraction.
    LOGGER.info('Subtracting the two rasters.  Invert=%s', invert)
    if invert is True:
        subtract_rasters(converted_es_map, base_run, static_map_uri)
    else:
        subtract_rasters(base_run, converted_es_map, static_map_uri)

    if num_simulations is not None:
        if workspace is None:
            # if the user created the workspace in a temporary folder, create a
            # folder in CWD for the quality workspace.
            workspace = os.getcwd()

        if config is None:
            # in case the user has not provided the config dictionary
            config = get_static_data_json(model_name)

        watersheds = config[MODELS[model_name]['watersheds_key']]

        simulation_workspace = os.path.join(workspace, 'simulations_%s' %
                                            landcover_label)
        test_static_map_quality(
            base_run,
            static_map_uri,
            landcover_uri,
            landcover_code,
            watersheds,
            model_name,
            simulation_workspace,
            config,
            num_simulations,
            invert=invert)

        simulations_csv = os.path.join(simulation_workspace,
                                       'impact_site_simulation.csv')
        out_png = os.path.join(simulation_workspace, 'simulations.png')
        graph_it(simulations_csv, out_png)
    LOGGER.info('Finished')


def subtract_rasters(raster_a, raster_b, out_uri):
    utils.assert_files_exist([raster_a, raster_b])
    LOGGER.debug('Subtracting rasters %s and %s', raster_a, raster_b)
    LOGGER.debug('Saving difference to %s', out_uri)
    pixel_size = pygeoprocessing.get_cell_size_from_uri(raster_a)
    nodata = pygeoprocessing.get_nodata_from_uri(raster_b)
    datatype = pygeoprocessing.get_datatype_from_uri(raster_b)
    LOGGER.debug('Output pixel size: %s', pixel_size)
    LOGGER.debug('Output nodata value: %s', nodata)
    LOGGER.debug('Output datatype: %s', datatype)

    pygeoprocessing.vectorize_datasets([raster_a, raster_b],
        lambda c, o: numpy.where(c != nodata, numpy.subtract(c, o), nodata),
        dataset_out_uri = out_uri,
        datatype_out=datatype, nodata_out=nodata,
        pixel_size_out=pixel_size, bounding_box_mode='intersection',
        vectorize_op=False)


def get_static_data_json(model_name):
    """Get the absolute path to the static data JSON file for the target model.

        model_name - a python string model name.  Must be a key in MODELS.

        Returns a python dictionary with the configuration."""
    assert model_name in MODELS.keys()

    if model_name == 'sediment':
        model_name = 'sdr'

    json_name = '%s_parameters.json' % model_name
    return _load_json(json_name)


def get_common_data_json(data_dir=None):
    """Return a dictionary with paths to common data (e.g. hydrozones, etc.).

        Returns a python dictionary"""
    common_data_name = 'common_data.json'
    config = _load_json(common_data_name)

    if data_dir is None:
        if getattr(sys, 'frozen', False):
            data_dir = os.path.dirname(sys.executable)
        else:
            data_dir = os.getcwd()

    def _render_dict(dictionary):
        output_dict = {}
        for key, item in dictionary.iteritems():
            if isinstance(item, DictType):
                rendered_item = _render_dict(item)
            else:
                rendered_item = os.path.join(data_dir, item)
            output_dict[key] = rendered_item
        return output_dict

    return _render_dict(config)


def _load_json(filename):
    """Fetch a json file from the adept package's static_data folder.

        Returns a python dictionary of the json data found in the target json
        file."""
    if getattr(sys, 'frozen', False):
        # we are running in a |PyInstaller| bundle
        # basedir = sys._MEIPASS  #suggested by pyinstaller
        basedir = os.path.join(sys._MEIPASS, 'natcap', 'opal')
    else:
        basedir = os.path.dirname(__file__)

    LOGGER.debug('__file__ == %s', __file__)
    LOGGER.debug('sys.executable == %s', sys.executable)
    LOGGER.debug('site-packages == %s', distutils.sysconfig.get_python_lib())
    LOGGER.debug('Looking for common static data in %s', basedir)
    config_file = os.path.join(basedir, 'static_data', filename)
    config = json.load(open(config_file))
    return config


def get_json_md5(json_uri):
    """Get an md5 hash for the python dictionary stored in a json file.  This
    function tries to be aware of whether a value points to a file on disk.
    When this happens, we fetch an MD5sum for the file and use that in the
    digest instead of the URI.

    Returns a python string with an MD5sum digest of the json object."""

    utils.assert_files_exist(json_uri)
    LOGGER.debug('Loading json from %s', json_uri)

    config = json.load(open(json_uri))
    config_md5sum = hashlib.md5()

    # assume that this is a flat dictionary.
    for key, value in config.iteritems():
        # if the value is a unicode string that is a URI to a file on disk, we
        # want to get the md5sum of the file and use that as the value in the
        # config's md5sum.  If it's not a URI to a file on disk, we'll just use
        # the value as is.
        if isinstance(value, UnicodeType):
            if os.path.exists(value):
                LOGGER.debug('Value %s is a URI', value)
                file_handler = open(value, 'rb')
                file_md5 = hashlib.md5()
                for chunk in iter(lambda: file_handler.read(2**20), ''):
                    file_md5.update(chunk)
                value = file_md5.hexdigest()

        LOGGER.debug('Updating digest with %s: %s', key, value)
        config_md5sum.update(key)
        config_md5sum.update(value)

    return config_md5sum.hexdigest()


def clip_raster_to_watershed(in_raster, ws_vector, out_uri, clip_raster=None):
    """Clip the input raster to ws_vector, saving the output raster to out_uri.
        in_raster - a URI to an input GDAL raster.
        ws_vector - a URI to an OGR vector that contains a single polygon of a
            watershed.
        out_uri - a URI to where the output raster should be saved.
    """
    datatype = pygeoprocessing.get_datatype_from_uri(in_raster)
    nodata = pygeoprocessing.get_nodata_from_uri(in_raster)
    pixel_size = pygeoprocessing.get_cell_size_from_uri(in_raster)

    if clip_raster is not None:
        rasters = [in_raster, clip_raster]
        clip_nodata = pygeoprocessing.get_nodata_from_uri(clip_raster)

        def operation(in_values, clip_values):
            return numpy.where(
                clip_values == clip_nodata,
                clip_nodata,
                in_values)
    else:
        rasters = [in_raster]
        operation = lambda x: x

    pygeoprocessing.vectorize_datasets(
        rasters,
        operation,
        out_uri,
        datatype,
        nodata,
        pixel_size,
        'intersection',
        dataset_to_align_index=0,
        aoi_uri=ws_vector,
        vectorize_op=False)


def make_random_impact_vector(new_vector, base_vector, side_length):
    """Create a new vector with a single, squarish polygon.  This polygon will
    be created within the spatial envelope of the first polygon in base_vector.
    The new squarish polygon will have a side length of side_length.

        new_vector - a URI to the new vector to be created. The new vector will
            be an ESRI Shapefile.
        base_vector - a URI to the vector we'll use as a base (for its spatial
            information).
        side_length - a python int or float describing the side length of the
            new polygon to be created.

        Returns nothing."""
    base_datasource = ogr.Open(base_vector)
    base_layer = base_datasource.GetLayer()
    base_feature = base_layer.GetFeature(0)
    base_geometry = base_feature.GetGeometryRef()
    spat_ref = base_layer.GetSpatialRef()

    # feature_extent = [xmin, xmax, ymin, ymax]
    feature_extent = base_geometry.GetEnvelope()
    print feature_extent

    driver = ogr.GetDriverByName('ESRI Shapefile')
    datasource = driver.CreateDataSource(new_vector)
    uri_basename = os.path.basename(new_vector)
    layer_name = str(os.path.splitext(uri_basename)[0])
    layer = datasource.CreateLayer(layer_name, spat_ref, ogr.wkbPolygon)

    # Add a single ID field
    field = ogr.FieldDefn('id', ogr.OFTInteger)
    layer.CreateField(field)

    while True:
        poly_ring = ogr.Geometry(type=ogr.wkbLinearRing)
        bbox_width = feature_extent[1]-feature_extent[0]
        bbox_height = feature_extent[3]-feature_extent[2]

        rand_width_percent = random.random()
        xmin = feature_extent[0] + bbox_width * rand_width_percent
        xmax = xmin + side_length

        # Make it squarish
        rand_height_percent = random.random()
        ymin = feature_extent[2] + bbox_height * rand_height_percent
        ymax = ymin + side_length

        print feature_extent
        print xmin, xmax, ymin, ymax

        poly_ring.AddPoint(xmin, ymin)
        poly_ring.AddPoint(xmin, ymax)
        poly_ring.AddPoint(xmax, ymax)
        poly_ring.AddPoint(xmax, ymin)
        poly_ring.AddPoint(xmin, ymin)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(poly_ring)

        # See if the watershed contains the permitting polygon
        contained = base_geometry.Contains(polygon)
        print contained
        if contained:
            break

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    feature.SetField(0, 1)
    layer.CreateFeature(feature)

    feature = None
    layer = None


def get_watershed_id(watershed_uri):
    """Get the ID from the watershed specified by the user.

        watershed_uri (string) - A String URI to the watershed vector.  This
            vector is assumed to have exactly one watershed polygon in it.

        Returns an int watershed ID."""

    # get this watershed's ws_id
    watershed_vector = ogr.Open(watershed_uri)
    watershed_layer = watershed_vector.GetLayer()
    watershed = watershed_layer.GetFeature(0)
    watershed_id = watershed.GetField('ws_id')
    LOGGER.debug('This watershed\'s ws_id: %s', watershed_id)
    return watershed_id


def test_static_map_quality(
        base_run,
        base_static_map,
        landuse_uri,
        impact_lucode,
        watersheds_uri,
        model_name,
        workspace,
        config,
        num_iterations=5,
        clean_workspaces=False,
        start_ws=0,
        start_impact=0,
        invert=None):
    """Test the quality of the provided static map.

    Args:
        base_run (filepath): The base run of the target model on the base lulc.
        base_static_map (filepath): The static map generated from the difference
            between the base_run raster and the entire landscape converted to the
            target impact type.
        landuse_uri (filepath): A URI to the LULC used for the base static map.
        impact_lucode (int or float): The numeric land use code to use to convert
            the underlying lulc raster to the target impact type.
        watersheds_uri (filepath): A filepath to the watersheds vector to use for
            testing.  Must have a column of integers in its attribute table
            labeled "ws_id".
        model_name (string): The string model name to run.
        workspace (filepath): The path to the folder to use as a workspace.  If
            this folder does not already exist, it will be created.
        config (dict): The arguments dictionary to use for running the model.
            See `static_maps.execute_model()` for details, or else
            `natcap/opal/static_data/<model_name>_parameters.json` for sample
            argument dictionaries (albeit serialized as JSON).
        num_iterations=5 (int, optional): The number of simulated impacts to run per
            watershed.
        clean_workspace=False (boolean, optional): Whether to remove the
            workspace before starting to test the inputs.
        start_ws=0 (int, optional): The watershed index to start on.  If 0, all
            watersheds will be tested.  Useful for resuming testing after
            failure (such as when running out of disk space).
        start_impact=0 (int, optional): The integer impact ID to start on.
            This must be less than `num_interations`.
        invert=None (boolean): Whether to invert the static map calculation.

    Returns:
        Nothing.
    """
    assert invert in [True, False], '%s found instead' % type(invert)
    old_tempdir = tempfile.tempdir
    temp_dir = os.path.join(workspace, 'tmp')  # for ALL tempfiles
    tempfile.tempdir = temp_dir  # all tempfiles will be saved here.

    # make a copy of the configuration dictionary so that we don't modify it
    # accidentally.
    config = config.copy()

    # make all the folders we know about at the moment
    pygeoprocessing.create_directories([workspace, temp_dir])

    # Open a logfile so we can incrementally write model data we care about
    logfile_uri = os.path.join(workspace, 'impact_site_simulation.csv')
    logfile = open(logfile_uri, 'a')
    labels = ['ws_id', 'Impact ID', 'Impact Area', 'Static Estimate',
              'InVEST Estimate', 'Estimate Ratio']
    logfile.write("%s\n" % ','.join(labels))
    logfile.close()

    lulc_nodata = pygeoprocessing.get_nodata_from_uri(landuse_uri)
    lulc_pixel_size = pygeoprocessing.get_cell_size_from_uri(landuse_uri)

    # limit the watersheds to just those that intersect the input lulc.
    current_watersheds = os.path.join(temp_dir, 'current_watersheds.shp')
    preprocessing.filter_by_raster(landuse_uri, watersheds_uri,
        current_watersheds, clip=True)

    # get the sediment export from the base raster, passed in from the user.
    # calculate for each watershed, so I can access these later.
    #base_export = pygeoprocessing.aggregate_raster_values_uri(
    #    base_run, current_watersheds, 'ws_id', 'sum').total
    #LOGGER.debug('All watershed ids: %s', base_export.keys())

    # split the watersheds so I can use each watershed as an AOI for the
    # correct model later on.
    watersheds_dir = os.path.join(workspace, 'watershed_vectors')
    split_watersheds = split_datasource(
        current_watersheds,
        watersheds_dir,
        ['ws_id'])

    for ws_index, watershed_uri in enumerate(split_watersheds):
        if ws_index < start_ws:
            LOGGER.debug(
                'Watershed %s is less than start index %s. skipping',
                ws_index, start_ws)
            continue

        watershed_workspace = os.path.join(
            workspace, 'watershed_%s' % ws_index)
        if not os.path.exists(watershed_workspace):
            os.makedirs(watershed_workspace)

        # get this watershed's ws_id
        watershed_vector = ogr.Open(watershed_uri)
        watershed_layer = watershed_vector.GetLayer()
        watershed = watershed_layer.GetFeature(0)
        watershed_id = watershed.GetField('ws_id')
        LOGGER.debug('This watershed\'s ws_id: %s', watershed_id)

        watershed_lulc = os.path.join(watershed_workspace,
            'watershed_lulc.tif')
        lulc_datatype = pygeoprocessing.get_datatype_from_uri(landuse_uri)
        pygeoprocessing.vectorize_datasets([landuse_uri], lambda x: x,
            watershed_lulc, lulc_datatype, lulc_nodata, lulc_pixel_size,
            'intersection', dataset_to_align_index=0, aoi_uri=watershed_uri,
            vectorize_op=False)

        ws_base_export_uri = os.path.join(watershed_workspace,
            'watershed_' + os.path.basename(base_run))
        base_nodata = pygeoprocessing.get_nodata_from_uri(base_run)
        base_pixel_size = pygeoprocessing.get_cell_size_from_uri(base_run)
        base_export_datatype = pygeoprocessing.get_datatype_from_uri(base_run)
        pygeoprocessing.vectorize_datasets([base_run], lambda x: x,
            ws_base_export_uri, base_export_datatype, base_nodata, base_pixel_size,
            'intersection', dataset_to_align_index=0, aoi_uri=watershed_uri,
            vectorize_op=False)
        base_ws_export = pygeoprocessing.aggregate_raster_values_uri(
            ws_base_export_uri, watershed_uri, 'ws_id',
            'sum').total[watershed_id]

        # if the model uses watersheds, we only want to run the model using
        # the one current watershed.
        watersheds_key = MODELS[model_name]['watersheds_key']
        if watersheds_key is not None:
            config[watersheds_key] = watershed_uri

        watershed_lulc = os.path.join(watershed_workspace,
                                      'watershed_lulc.tif')
        clip_raster_to_watershed(landuse_uri, watershed_uri, watershed_lulc)
        watershed_base_workspace = os.path.join(watershed_workspace, 'base')
        execute_model(model_name, watershed_lulc, watershed_base_workspace, config)

        ws_base_export_uri = os.path.join(watershed_base_workspace,
                                          MODELS[model_name]['target_raster'])
        ws_base_static_map = os.path.join(
            watershed_workspace, 'watershed_' + os.path.basename(base_static_map))
        clip_raster_to_watershed(base_static_map, watershed_uri, ws_base_static_map)

        # If we're not in the starting watershed, then reset the starting index
        # of the impact site.
        start_impact = 0 if ws_index != start_impact else start_impact

        for run_number in range(start_impact, num_iterations):
            impact_site_length = random.uniform(500, 3000)
            impact_workspace = os.path.join(watershed_workspace,
                                            'random_impact_%s' % run_number)

            if os.path.exists(impact_workspace):
                shutil.rmtree(impact_workspace)
            os.makedirs(impact_workspace)

            # make a random impact vector somewhere in the current watershed.
            impact_site = os.path.join(
                impact_workspace,
                'impact_%s.shp' %
                run_number)
            make_random_impact_vector(impact_site, watershed_uri,
                                      impact_site_length)

            # convert the area under the impact to the correct landcover
            # code(s), run the target model and analyze the outputs.
            converted_landcover = os.path.join(impact_workspace,
                                               'converted_lulc.tif')
            # If the landcover is a string, we convert to the area under the
            # impact.  If the landcover is a number, that's the conversion
            # type.
            convert_impact(impact_site, watershed_lulc, impact_lucode,
                           converted_landcover, impact_workspace)
            execute_model(model_name, converted_landcover, impact_workspace,
                          config)
            estimates = aggregate_test_results(
                impact_workspace,
                model_name,
                watershed_uri,
                impact_site,
                ws_base_static_map,
                ws_base_export_uri,
                invert=invert)

            # ability to sort based on area of impact site.
            # also record which watershed this run is in, impact site ID as well
            impact_site_area = get_polygon_area(impact_site)
            values_to_write = [
                watershed_id,
                run_number,
                impact_site_area,
                estimates['static_est'],
                estimates['invest_est'],
                estimates['export_ratio'],
            ]
            logfile = open(logfile_uri, 'a')
            logfile.write("%s\n" % ','.join(map(str, values_to_write)))
            logfile.close()

def compute_impact_stats(impact_dir, model_name, watershed_vector,
                         base_ws_export, base_static_map):
    """Take an impact directory and the target model name and extract the
    correct information from it.

    impact_dir - a URI to a folder that has been used as an impact workspace.
    model_name - the string name of the model we're using.
    watershed_vector - a URI to an OGR vector of the watershed this impact
        belongs to.
    base_ws_export - the base watershed export (a number)
    base_static_map - a URI to the static map generated from the difference
        between the base sediment model run and when the landscape is converted
        completely over to the target impact type.

    Returns a python dictionary containing extracted stats about the impact."""

    impact_vector = 'impact_%s.shp' % os.path.basename(
        impact_dir).split('_')[-1]
    impact_site = os.path.join(impact_dir, impact_vector)
    print impact_site
    impact_site_area = get_polygon_area(impact_site)

    export_raster = os.path.join(impact_dir,
                                 MODELS[model_name]['target_raster'])

    # aggregate this impact over the target watershed.
    impact_ws_export = pygeoprocessing.aggregate_raster_values_uri(export_raster,
        watershed_vector, 'ws_id').total.values()[0]  # just get the only ws

    # get the sediment export from the base static map under the impacted area.
    # only 1 feature in the impacted area, so we access this number with index
    # 1.
    static_estimate = pygeoprocessing.aggregate_raster_values_uri(
        base_static_map, impact_site, 'id').total[1]

    # If we're running the nutrient model, multiply the sum of the
    # sed_export by the max percent_to_stream under the impact site.
    if model_name in ['nutrient']:
        LOGGER.info('Adjusting export by the % to stream')

        # the percent-to-stream raster for Nitrogen is named
        # "n_percent_to_stream.tif", sediment is just "percent_to_stream.tif"
        # nutrient percent-to-stream is prefixed by 'n_'
        pts_prefix = 'n_'

        percent_to_stream = os.path.join(impact_dir,
            'intermediate', '%spercent_to_stream.tif' % pts_prefix)
        max_percent = pygeoprocessing.aggregate_raster_values_uri(
            percent_to_stream, impact_site,
            'id').pixel_max[1]
        if max_percent is None:
            LOGGER.debug('Max percent is None, setting to 0')
            max_percent = 0.0
        static_estimate = static_estimate * max_percent
    else:
        LOGGER.info('Not running a routed model, running %s', model_name)

    invest_estimate = impact_ws_export - base_ws_export
    #invest_estimate = base_ws_export - impact_ws_export

    export_ratio = static_estimate / invest_estimate

    return {
        'impact_dir': impact_dir,
        'impact_site_area': impact_site_area,
        'static_estimate': static_estimate,
        'invest_estimate': invest_estimate,
        'export_ratio': export_ratio,
        'impact_ws_export': impact_ws_export,
    }


def get_polygon_area(vector):
    # ONLY returns the area of the first polygon.
    datasource = ogr.Open(vector)
    layer = datasource.GetLayer()
    feature = layer.GetFeature(0)
    geometry = feature.GetGeometryRef()
    area = geometry.Area()

    geometry = None
    feature = None
    layer = None
    datasource = None
    return area


def graph_it(log_file, out_file):
    import matplotlib
    matplotlib.use('Agg')  # for rendering plots without $DISPLAY set.
    import matplotlib.pyplot as plt

    LOGGER.info('Creating graph from results at %s', log_file)
    LOGGER.debug('Saving image to %s', out_file)
    all_rows = []
    out_of_bounds = []
    opened_log_file = open(log_file)
    opened_log_file.next()  # skip the column headers.
    for line in opened_log_file:
        try:
            values = map(float, line.split(','))
        except ValueError as error:
            # when there's a column with string data that can't be cast to
            # a float (like a column header), skip the row.
            LOGGER.warn(error)
            continue

        ws_id, run_num, impact_area, static_est, invest_est, ratio = values

#        if ratio > 3 or ratio < -3:
#            out_of_bounds.append(ratio)
#        else:
#            all_rows.append((impact_area, ratio))
        all_rows.append((impact_area, ratio))

    # smoother with 95 % confidence intervals
    all_rows = sorted(all_rows, key=lambda x: x[0])
    areas = [r[0] for r in all_rows]
    ratios = [r[1] for r in all_rows]

#    LOGGER.debug('These values were outliers: %s', out_of_bounds)
    plt.plot(areas, ratios, 'ro')
    plt.xlabel('Impact Site Area (m^2)')
    plt.ylabel('(Static Est. / InVEST Est)')

    areas_np = numpy.array(areas)
    ratios_np = numpy.array(ratios)

    n = len(ratios_np)
    t = scipy.linspace(0, max(areas), n)

    # Linear regressison -polyfit - polyfit can be used other orders polys
    (ar, br) = scipy.polyfit(areas_np, ratios_np, 1)
    xr = scipy.polyval([ar, br], t)

    plt.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))

    plt.plot(t, xr, 'g--')  # plot the linear regression line.
    plt.savefig(out_file)


def split_datasource(ds_uri, workspace, include_fields=[],
                     template_str='feature_%s.shp'):
    """Split the input OGR datasource into a list of datasources, each with a
    single layer containing a single feature.
        ds_uri - a URI to an OGR datasource.
        workspace - a folder to which the output vectors should be saved.
        include_fields=[] - a list of string fields to be copied from the source
            datsource to the destination datasources.
        template_str - a template string with a placeholder for a single value.
            All file uris will be named according to this pattern.
    Returns a list of URIs, one for each new vector created."""

    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    os.makedirs(workspace)

    LOGGER.debug('Opening vector at %s', ds_uri)
    ds = ogr.Open(ds_uri)
    driver_string = 'ESRI Shapefile'

    LOGGER.debug('Splitting datasource into separate shapefiles')
    LOGGER.debug('Vectors will be saved to %s', workspace)
    output_vectors = []
    for layer in ds:
        layer_defn = layer.GetLayerDefn()
        for feature in layer:
            print 'starting new feature'
            uri_index = feature.GetFID()
            new_vector_uri = os.path.join(workspace, template_str %
                                          uri_index)
            output_vectors.append(new_vector_uri)

            LOGGER.debug('Creating new shapefile at %s' % new_vector_uri)
            ogr_driver = ogr.GetDriverByName(driver_string)
            temp_shapefile = ogr_driver.CreateDataSource(new_vector_uri)
            LOGGER.debug('SRS: %s, %s', layer.GetSpatialRef(),
                         type(layer.GetSpatialRef()))

            layer_name = os.path.splitext(os.path.basename(
                new_vector_uri))[0]
            if isinstance(layer_name, UnicodeType):
                LOGGER.debug('Decoding layer name %s to ASCII', layer_name)
                #layer_name = layer_name.decode('utf-8')
                layer_name = str(layer_name)

            LOGGER.debug('Layer name: %s', layer_name)

            temp_layer = temp_shapefile.CreateLayer(
                layer_name, layer.GetSpatialRef())
            temp_layer_defn = temp_layer.GetLayerDefn()

            for field_index in range(layer_defn.GetFieldCount()):
                original_field = layer_defn.GetFieldDefn(field_index)
                output_field = ogr.FieldDefn(original_field.GetName(),
                                             original_field.GetType())
                temp_layer.CreateField(output_field)

            # Create the obligatory ID field.
            # If I don't create the ID field, I can't properly select other
            # fields later on, when I need to set their values.
            id_field = ogr.FieldDefn('id', ogr.OFTInteger)
            temp_layer.CreateField(id_field)

            # Create the new feature with all of the characteristics of the old
            # field except for the fields.  Those are brought along separately.
            LOGGER.debug('Creating new feature with duplicate geometry')
            feature_geom = feature.GetGeometryRef()
            temp_feature = ogr.Feature(temp_layer_defn)
            temp_feature.SetFrom(feature)

            # Since there's only one feature in this shapefile, set id to 0.
            id_field_index = temp_feature.GetFieldIndex('id')
            temp_feature.SetField(id_field_index, 0)

            LOGGER.debug('Copying over fields %s', include_fields)
            for field_index in range(layer_defn.GetFieldCount()):
                field_defn = layer_defn.GetFieldDefn(field_index)
                field = field_defn.GetName()
                LOGGER.debug('Adding field "%s"', field)

                # Create the new field in the temp feature
                field_type = field_defn.GetType()
                LOGGER.debug('Field type=%s', field_type)

                LOGGER.debug('Copying field "%s" value to new feature',
                             field)
                temp_feature.SetField(field, feature.GetField(field))

            temp_layer.CreateFeature(temp_feature)
            temp_layer.SyncToDisk()

            temp_layer = None
            temp_shapefile = None

    layer.ResetReading()
    layer = None
    ds = None
    ogr_driver = None

    LOGGER.debug('Finished creating the new shapefiles')
    return output_vectors


def convert_impact(impact_uri, base_lulc, impacted_value, converted_lulc_uri,
                   workspace):
    """Convert the area under the impact vector to be the value of
        impact_value.

        impact_uri (string) - a filepath to an impact site vector on disk.
        base_lulc (string) - a filepath to the base lulc on disk.
        impacted_value (string or int) - The value to convert to.  If an int,
            the value under the impact site will be this landcover code.  If
            a string, the value under the impact site will be the pixel values
            of this raster under the impact site.
        converted_lulc_uri (string) - a filepath to where the converted raster
            should be stored.
        workspace (string) - a filepath to a folder where some output rasters
            will be written.

        Returns nothing."""

    # Create a raster mask for the randomized impact site.
    # Any non-nodata pixels underneath the impact site are marked by 1.
    impact_mask = os.path.join(workspace, 'impact_mask.tif')
    lulc_nodata = pygeoprocessing.get_nodata_from_uri(base_lulc)
    lulc_pixel_size = pygeoprocessing.get_cell_size_from_uri(base_lulc)
    lulc_datatype = pygeoprocessing.get_datatype_from_uri(base_lulc)

    def mask_op(values):
        return numpy.where(values != lulc_nodata, 1.0,
                           lulc_nodata)

    pygeoprocessing.vectorize_datasets(
        [base_lulc],
        mask_op,
        impact_mask,
        lulc_datatype,
        lulc_nodata,
        lulc_pixel_size,
        'intersection',
        dataset_to_align_index=0,
        aoi_uri=impact_uri,
        vectorize_op=False)


    if isinstance(impacted_value, basestring):
        LOGGER.debug('Converting values to those of %s', impacted_value)
        def _convert_impact(mask_values, lulc_values, impacted_lulc_values):
            """Convert values under the mask to the future lulc values."""
            return numpy.where(mask_values == 1, impacted_lulc_values,
                               lulc_values)
        rasters_list = [impact_mask, base_lulc, impacted_value]
    else:
        LOGGER.debug('Converting values to scalar: %s', impacted_value)
        def _convert_impact(mask_values, lulc_values):
            """Convert values under the mask to the scalar impacted value."""
            return numpy.where(mask_values == 1, impacted_value,
                               lulc_values)
        rasters_list = [impact_mask, base_lulc]

    pygeoprocessing.vectorize_datasets(
        rasters_list, _convert_impact, converted_lulc_uri,
        lulc_datatype, lulc_nodata, lulc_pixel_size, 'union',
        dataset_to_align_index=0, vectorize_op=False)


def aggregate_test_results(impact_workspace, model_name, watershed_uri,
                           impact_site, base_static_map, base_export, invert):
    # get the target raster for the selected ecosystem service.
    export = os.path.join(impact_workspace,
                          MODELS[model_name]['target_raster'])

    def _mask_out_pixels(in_raster, comp_raster, out_raster):
        comp_nodata = pygeoprocessing.get_nodata_from_uri(comp_raster)
        pixel_size = pygeoprocessing.get_cell_size_from_uri(comp_raster)

        def _pixel_mask(_in_values, _out_values):
            return numpy.where(_in_values == comp_nodata,
                comp_nodata, _out_values)

        pygeoprocessing.vectorize_datasets([comp_raster, in_raster],
            _pixel_mask, out_raster, gdal.GDT_Float32, comp_nodata,
            pixel_size, 'union', dataset_to_align_index=0,
            vectorize_op=False)

    # mutually mask out the impacted/base export rasters.
    masked_impact_export = os.path.join(impact_workspace,
                                        'masked_impacted_export.tif')
    masked_base_export = os.path.join(impact_workspace,
                                      'masked_base_export.tif')
    _mask_out_pixels(export, base_export, masked_impact_export)
    _mask_out_pixels(base_export, export, masked_base_export)

    # Aggregate the sediment export from this impact simulation over
    # the target watershed
    impact_ws_export = pygeoprocessing.aggregate_raster_values_uri(
        masked_impact_export, watershed_uri, 'ws_id').total.values()[0]

    # Get the sediment export from the static map under the impacted area.
    # only 1 feature in the impactd area, so we access that number with
    # index 1.
    static_estimate = pygeoprocessing.aggregate_raster_values_uri(
        base_static_map, impact_site, 'id').total[1]

    # Get the watershed's base export from the masked version of the
    # watershed's export raster.
    watershed_id = get_watershed_id(watershed_uri)
    base_ws_export = pygeoprocessing.aggregate_raster_values_uri(
        masked_base_export, watershed_uri, 'ws_id').total[watershed_id]

    LOGGER.warning('NOT adjusting by %%-to-stream. model=%s', model_name)
    # This conditional makes the outputs all
    # represent the same thing: positive values are desireable,
    # negative values are not desireable.
    if invert:
        invest_estimate = impact_ws_export - base_ws_export
    else:
        invest_estimate = base_ws_export - impact_ws_export


    export_ratio = static_estimate / invest_estimate

    return {
        'static_est': static_estimate,
        'invest_est': invest_estimate,
        'export_ratio': export_ratio,
        'base_export': base_ws_export,
        'impacted_export': impact_ws_export,
    }


def clip_static_map(map_uri, aoi_uri, out_uri):
    """Clip the input static map by the single polygon in aoi_uri.  Saves the
    output raster to out_uri.  Values outside of the aoi will be set to nodata.

    map_uri - a URI to a GDAL raster.
    aoi_uri - a URI to an OGR vector.  May only contain one polygon.
    out_uri - the URI to which the output raster should be saved.

    Returns nothing."""

    nodata = pygeoprocessing.get_nodata_from_uri(map_uri)
    pixel_size = pygeoprocessing.get_cell_size_from_uri(map_uri)

    pygeoprocessing.vectorize_datasets([map_uri], lambda x: x, out_uri,
        gdal.GDT_Float32, nodata, pixel_size, 'intersection', aoi_uri=aoi_uri,
        vectorize_op=False)
