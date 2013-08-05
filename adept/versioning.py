import subprocess
import logging
import platform
import collections
import shutil
import os

from invest_natcap import raster_utils

HG_CALL = 'hg log -r . --config ui.report_untrusted=False'

LOGGER = logging.getLogger('versioning')
LOGGER.setLevel(logging.ERROR)


BuildInfo = collections.namedtuple(
    'BuildInfo', ['release', 'build_id', 'py_arch', 'version_str'])

def build_data():
    data = BuildInfo(
        release=get_latest_tag(),
        build_id=get_build_id(),
        py_arch=get_py_arch(),
        version_str=version())
    return data

def write_build_info(source_file_uri):
    """Write the build information to the file specified as `source_file_uri`.
    """
    temp_file_uri = raster_utils.temporary_filename()
    temp_file = open(temp_file_uri, 'w+')

    source_file = open(os.path.abspath(source_file_uri))
    for line in source_file:
        if line == "__version__ = 'dev'\n":
            temp_file.write("__version__ = '%s'\n" % version())
        elif line == "build_data = None\n":
            temp_file.write("build_data = versioning.%s\n" % str(build_data()))
        else:
            temp_file.write(line)
    temp_file.flush()
    temp_file.close()

    source_file.close()
    os.remove(source_file_uri)
    shutil.copyfile(temp_file_uri, source_file_uri)

def get_py_arch():
    """This function gets the python architecture string.  Returns a string."""
    return platform.architecture()[0]

def get_release_version():
    """This function gets the release version.  Returns either the latest tag
    (if we're on a release tag) or None, if we're on a dev changeset."""
    if get_tag_distance() == 0:
        return get_latest_tag()
    return None

def version():
    """This function gets the module's version string.  This will be either the
    dev build ID (if we're on a dev build) or the current tag if we're on a
    known tag.  Either way, the return type is a string."""
    release_version = get_release_version()
    if release_version == None:
        return build_dev_id(get_build_id())
    return release_version

def build_dev_id(build_id=None):
    """This function builds the dev version string.  Returns a string."""
    if build_id == None:
        build_id = get_build_id()
    return 'dev%s' % (build_id)

def get_architecture_string():
    """Return a string representing the operating system and the python
    architecture on which this python installation is operating (which may be
    different than the native processor architecture.."""
    return '%s%s' % (platform.system().lower(),
        platform.architecture()[0][0:2])

def get_version_from_hg():
    """Get the version from mercurial.  If we're on a tag, return that.
    Otherwise, build the dev id and return that instead."""
    # TODO: Test that Hg exists before getting this information.
    if get_tag_distance() == 0:
        return get_latest_tag()
    else:
        return build_dev_id()

def get_build_id():
    """Call mercurial with a template argument to get the build ID.  Returns a
    python bytestring."""
    cmd = HG_CALL + ' --template "{latesttagdistance}:{latesttag} [{node|short}]"'
    return run_command(cmd)

def get_tag_distance():
    """Call mercurial with a template argument to get the distance to the latest
    tag.  Returns an int."""
    cmd = HG_CALL + ' --template "{latesttagdistance}"'
    return int(run_command(cmd))

def get_latest_tag():
    """Call mercurial with a template argument to get the latest tag.  Returns a
    python bytestring."""
    cmd = HG_CALL + ' --template "{latesttag}"'
    return run_command(cmd)

def run_command(cmd):
    """Run a subprocess.Popen command.  This function is intended for internal
    use only and ensures a certain degree of uniformity across the various
    subprocess calls made in this module.

    cmd - a python string to be executed in the shell.

    Returns a python bytestring of the output of the input command."""
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.read()
