"""The python file for offset portfolio calculation."""
import logging
import os
import json
import sys
import codecs
from types import StringType
import time
import platform
import hashlib
import locale
import threading

import natcap.opal
import natcap.invest
from natcap.invest.iui import executor as invest_executor
import shapely
import shapely.speedups
import shapely.wkb
import shapely.prepared
import shapely.geometry
import shapely.geos
from osgeo import ogr

LOGGER = logging.getLogger('natcap.opal.offsets')

# create a logging filter
class TimedLogFilter(logging.Filter):
    # only print a single log message if the time passed since last log message
    # >= the user-defined interval
    def __init__(self, interval):
        logging.Filter.__init__(self)
        self.interval = interval
        self._last_record_time = None

    def filter(self, record):
        current_time = time.time()
        if self._last_record_time is None:
            # if we've never printed a message since starting the filter, print
            # the message.
            self._last_record_time = current_time
            return True
        else:
            # Only log a message if more than <interval> seconds have passed
            # since the last record was logged.
            if current_time - self._last_record_time >= 5.0:
                self._last_record_time = current_time
                return True
            return False


def build_shapely_polygon(ogr_feature, prep=False, fix=False):
    geometry = ogr_feature.GetGeometryRef()
    try:
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
    except shapely.geos.ReadingError:
        LOGGER.debug('Attempting to close geometry rings')
        # If the geometry does not form a closed circle, try to connect the
        # rings with the OGR function.
        geometry.CloseRings()
        polygon = shapely.wkb.loads(geometry.ExportToWkb())
        LOGGER.debug('Geometry fixed')

    if fix:
        polygon = polygon.buffer(0)
    if prep:
        polygon = shapely.prepared.prep(polygon)
    return polygon


def assert_files_exist(files):
    """Assert that all input files exist.

        files - a list of URIs to files on disk.

    This function raises IOError when a file is not found."""

    for file_uri in files:
        if not os.path.exists(file_uri):
            raise IOError('File not found: %s' % file_uri)


def _log_model(model_name, model_args, session_id=None):
    """Log information about a model run to a remote server.

    Parameters:
        model_name (string): a python string of the package version.
        model_args (dict): the traditional InVEST argument dictionary.

    Returns:
        None
    """

    logger = logging.getLogger('natcap.opal.utils._log_model')

    string = model_name[:]  # make a copy
    if 'palisades' in globals().keys() or 'palisades' in sys.modules:
        string += '.gui'
    else:
        string += '.cli'

    # if we're in a frozen environment, fetch the build information about the
    # distribution.
    if natcap.opal.is_frozen():
        # read build information from the local configuration file.
        # distribution_name
        # distribution_build_id
        #
        # Build a full model name and version string out of this info
        dist_data_file = os.path.join(natcap.opal.get_frozen_dir(),
            'dist_version.json')
        dist_data = json.load(open(dist_data_file))

        model_name = "%s.%s" % (dist_data['dist_name'], string)
        model_version = dist_data['build_id']
    else:
        # we're not in a built distribution, so we someone must be running this
        # from the command line.  In this case, we're obviously not in a
        # distribution, but we may be in the permitting repo, not just as a
        # standalone natcap.opal repo.
        model_name = string
        model_version = natcap.opal.__version__

    def _node_hash():
        """Returns a hash for the current computational node."""
        data = {
            'os': platform.platform(),
            'hostname': platform.node(),
            'userdir': os.path.expanduser('~')
        }
        md5 = hashlib.md5()
        # a json dump will handle non-ascii encodings
        md5.update(json.dumps(data))
        return md5.hexdigest()

    try:
        bounding_box_intersection, bounding_box_union = (
            invest_executor._calculate_args_bounding_box(model_args))

        payload = {
            'model_name': model_name,
            'invest_release': model_version,
            'node_hash': _node_hash(),
            'system_full_platform_string': platform.platform(),
            'system_preferred_encoding': locale.getdefaultlocale()[1],
            'system_default_language': locale.getdefaultlocale()[0],
            'bounding_box_intersection': str(bounding_box_intersection),
            'bounding_box_union': str(bounding_box_union),
            'session_id': session_id,
        }

        logging_server = invest_executor._get_logging_server()
        logging_server.log_invest_run(payload)
    except Exception as exception:
        # An exception was thrown, we don't care.
        logger.warn(
            'an exception encountered when logging %s', str(exception))

class VectorUnprojected(Exception):
    """An Exception in case a vector is unprojected"""
    pass

class DifferentProjections(Exception):
    """An exception in cast a set of dataets are not in the same projection."""
    pass

def assert_ogr_projections_equal(vector_uri_list):
    """Assert that all projections of the input OGR-compatible vectors are
    identical.

    Raises VectorUnprojected if a vector is inprojected.
    Raises DifferentProjections if projections differ."""

    vector_list = [(ogr.Open(v_uri), v_uri) for v_uri in vector_uri_list]
    vector_projections = []

    unprojected_vectors = set()

    for vector, vector_uri in vector_list:
        layer = vector.GetLayer()
        srs = layer.GetSpatialRef()
        if not srs.IsProjected():
            unprojected_vectors.add(vector_uri)
        vector_projections.append((srs, vector_uri))

    if len(unprojected_vectors) > 0:
        raise VectorUnprojected(
            "These vectors are unprojected: %s" % (unprojected_vectors))

    for index in range(len(vector_projections) - 1):
        if not vector_projections[index][0].IsSame(
                vector_projections[index + 1][0]):
            LOGGER.warn(
                "These two datasets might not be in the same projection."
                " The different projections are:\n\n'filename: %s'\n%s\n\n"
                "and:\n\n'filename:%s'\n%s\n\n",
                vector_projections[index][1],
                vector_projections[index][0].ExportToPrettyWkt(),
                vector_projections[index+1][1],
                vector_projections[index+1][0].ExportToPrettyWkt())

    for vector in vector_list:
        #Make sure the vector is closed and cleaned up
        vector = None
    vector_list = None
    return True

def write_csv(uri, fields, rows):
    """Write a utf-8 encoded CSV to URI.
        fields - a list of strings
        rows - a list of dictionaries, pointing fieldname to value"""

    def _cast_if_str(string):
        if type(string) is StringType:
            return unicode(string, 'utf-8')
        return string

    # write the rows to a CSV
    LOGGER.debug('Writing output CSV: %s', uri)
    csv_file_obj = codecs.open(uri, 'w', 'utf-8')

    # write the header
    sanitized_fieldnames = ['"%s"' % _cast_if_str(f) for f in fields]
    csv_file_obj.write("%s\n" % ','.join(sanitized_fieldnames))

    # write the rows
    for row in rows:
        row_fields = ['"%s"' % _cast_if_str(row[f]) for f in fields]
        csv_file_obj.write("%s\n" % ','.join(row_fields))
    csv_file_obj.close()

def sigfig(number, digits=3):
    """
    Round a number to the given number of significant digits.
    Example:
        >>> sigfig(1234, 3)
        1230

    number (int or float): The number to adjust
    digits=3 (int): The number of siginficant figures to retain

    Returns a number."""

    input_type = type(number)
    output_num = ''
    digit_count = 0
    period_found = False
    for digit in str(float(number)):
        if digit == '.':
            period_found = True
            output_num += '.'
        elif digit_count < digits:
            output_num += digit
            digit_count += 1
        else:
            output_num += '0'

    return input_type(float(output_num))


