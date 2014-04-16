from distutils.core import setup
from distutils.core import Command
import platform
import imp
import os
import subprocess
import sys
import glob
import shutil

import matplotlib
import palisades
import adept
from adept import preprocessing

print 'Adept package version: %s' % adept.__version__
print 'Palisades package version: %s' % palisades.__version__

py2exe_options = {}

CMD_CLASSES = {}
DATA_FILES = [('.', ['adept.json',
                        'msvcp90.dll'])]

# Use the determined virtualenv site-packages path to add all files in the
# IUI resources directory to our setup.py data files.
directory = 'invest-natcap.invest-3/invest_natcap/iui/iui_resources'
for root_dir, sub_folders, file_list in os.walk(directory):
    destination = root_dir.replace('invest-natcap.invest-3/', '')
    DATA_FILES.append((destination, map(lambda x:
        os.path.join(root_dir, x), file_list)))

iui_dir = os.path.join('invest-natcap.invest-3', 'invest_natcap', 'iui')
icon_names = ['dialog-close', 'dialog-ok', 'document-open', 'edit-undo',
              'info', 'natcap_logo', 'validate-pass', 'validate-fail',
              'dialog-warning', 'dialog-warning-big', 'dialog-information-2',
              'dialog-error', 'list-remove']
iui_icons = []
for name in icon_names:
    iui_icons.append(os.path.join(iui_dir, '%s.png' % name))

DATA_FILES.append(('invest_natcap/iui', iui_icons))

if platform.system() == 'Windows':
    import py2exe
    dist_dir = 'adept_py2exe'
    py2exe_options['options'] ={
        'py2exe': {
            'dist_dir': dist_dir,
            'packages': ['adept'],
            'skip_archive': True,
            'includes': [
                'sip',
                'adept',
                'scipy.sparse.csgraph._validation',
                'matplotlib',
                'distutils',
            ],
            'excludes': ['Tkconstants', 'Tkinter', 'tcl', '_gtkagg', '_tkagg',
                '_qt4agg'],
            'xref': True,
        },
        'build_installer': {'nsis_dir': dist_dir},
    }
    py2exe_options['console'] = ['run_adept.py']
    DATA_FILES += matplotlib.get_py2exe_datafiles()
    DATA_FILES += palisades.get_py2exe_datafiles()

else:
    python_version = 'python%s' % '.'.join([str(r) for r in
        sys.version_info[:2]])
    lib_path = os.path.join('lib', python_version, 'site-packages')
    iui_icon_path = os.path.join(lib_path, 'invest_natcap', 'iui')
    DATA_FILES.append((iui_icon_path, iui_icons))

# Since this repo is not for specific packages, I'm assuming that this
# section is for py2exe ONLY.
DATA_FILES.append(('invest_natcap/iui', iui_icons))
DATA_FILES.append(('src/adept/report_data',
    glob.glob('src/adept/adept/report_data/*')))
#    DATA_FILES.append(('data/colombia_static_data',
#        glob.glob('data/colombia_static_data/*')))

# get specific sets of data files from the tool_data.
# first, get the vectors.
tool_data = []
vectors = ['Hydrographic_subzones',
    'Municipalities', 'ecosys_dis_nat_comp_fac', 'hydrozones',
    'sample_aoi', 'watersheds_cuencas']
for vector_base in vectors:
    glob_pattern = 'data/colombia_tool_data/%s.*' % vector_base
    tool_data += glob.glob(glob_pattern)

tif_rasters = ['DEM', 'Erodability', 'Erosivity',
    'Plant_available_water_content', 'Precipitation',
    'Ref_evapotranspiration', 'Soil_depth']
for raster in tif_rasters:
    tool_data.append('data/colombia_tool_data/%s.tif' % raster)
#    DATA_FILES.append(('data/colombia_tool_data', tool_data))

png_rasters = ['ecosystems']
for raster in png_rasters:
    tool_data.append('data/colombia_tool_data/%s.png' % raster)


class ZipDataCommand(Command):
    """Zips up all the data required for distribution."""
    description = "Custom command to gather up the various data"

    user_options = [
        ('static-data-zip=', None, 'Output zip for static data'),
        ('tool-data-zip=', None, 'Output zip for tool data'),
    ]

    def initialize_options(self):
        self.static_data_zip = None
        self.tool_data_zip = None

    def finalize_options(self):
        pass

    def run(self):
        build_dir = os.path.join(os.getcwd(), 'build', 'permitting_data')
        dist_dir = os.path.join(os.getcwd(), 'dist')
        data_dir = os.path.join(build_dir, 'data')
        tool_data_dir = os.path.join(data_dir, 'colombia_tool_data')
        if os.path.exists(tool_data_dir):
            shutil.rmtree(tool_data_dir)
        os.makedirs(tool_data_dir)

        # copy relevant tool data into the tool_data folder.
        print '\nStarting to copy tool data'
        for tool_data_file in tool_data:
            new_uri = os.path.join(tool_data_dir,
                    os.path.basename(tool_data_file))
            if tool_data_file.endswith('.tif'):
                print 'Uncompressing %s -> %s' % (tool_data_file, new_uri)
                preprocessing.uncompress_gtiff(tool_data_file, new_uri)
            else:
                print 'copying %s -> %s' % (tool_data_file, new_uri)
                shutil.copy(tool_data_file, new_uri)

        # copy all static map data into the static maps folder.
        print '\nStarting to copy static data'
        static_maps_dir = os.path.join(data_dir, 'colombia_static_data')
        os.makedirs(static_maps_dir)
        static_files = glob.glob('data/colombia_static_data/*.tif')
        for static_file in static_files:
            new_uri = os.path.join(static_maps_dir,
                os.path.basename(static_file))
            print 'Uncompressing %s -> %s' % (static_file, new_uri)
            preprocessing.uncompress_gtiff(static_file, new_uri)

        # make the data archives
        tool_zip = os.path.join(dist_dir, 'tool_data')
        print "Building %s.zip" % tool_zip
        shutil.make_archive(tool_zip, 'zip', root_dir=tool_data_dir)

        static_data_zip = os.path.join(dist_dir, 'static_data')
        print "Building %s.zip" % static_data_zip
        shutil.make_archive(static_data_zip, 'zip', root_dir=static_maps_dir)

class NSISCommand(Command):
    """Uses two options: "version" : the rios version; "nsis_dir" : the
    installation directory containing the py2exe executeables to be packaged
    up."""
    description = "Custom command to build our NSIS installer."

    # This list of tuples allows for command-line options for this distutils
    # command.
    user_options = [
        ('nsis-dir=', None, 'Folder with executeables to compress.'),
        ('nsis-install=', None, 'Location of the NSIS installation on disk')]

    def initialize_options(self):
        self.nsis_dir = None
        self.nsis_install = None

    def finalize_options(self):
        pass

    def run(self):
        print ''
        print 'Starting NSIS installer build'

        build_dir = os.path.join(os.getcwd(), 'build', 'nsis-build')
        os.makedirs(build_dir)

        self.nsis_dir = os.path.expanduser(self.nsis_dir)
        if not os.path.isdir(self.nsis_dir):
            self.nsis_dir = self.nsis_dir[:-1]

        target_dir = os.path.join(build_dir, os.path.basename(self.nsis_dir))
        print 'Copying %s -> %s' % (self.nsis_dir, target_dir)
        shutil.copytree(self.nsis_dir, target_dir)

        # copy the zipfiles we need into the right place.
        for filename in ['static_data.zip', 'tool_data.zip']:
            source_file = os.path.join('dist', filename)
            dest_file = os.path.join(target_dir, filename)
            print 'Copying %s -> %s' % (source_file, dest_file)
            shutil.copyfile(source_file, dest_file)

        cwd = os.getcwd()
        os.chdir('installer')  # CD into the installer folder to build it.

        installer_path = os.path.join('adept_installer.nsi')
        genesis = imp.load_source('genesis', 'genesis.py')
        genesis.build_installer_script('permitting_installer.json',
            installer_path)
        #installer_path = os.path.join('adept_installer_zipdata.nsi')

        program_path = []

        # If the user provided a local NSIS install path, check that it exists
        # before using it.  If it doesn't exist, check the usual places,
        # according to the OS.
        if self.nsis_install != None:
            if os.path.exists(self.nsis_install):
                makensis_path = self.nsis_install
            else:
                makensis_path = ''
                print str('ERROR: "%s" does not exist.' % self.nsis_install +
                    ' Checking the usual place(s) on this computer instead')
        else:
            makensis_path = self.nsis_install

        if program_path == []:
            if platform.system() == 'Windows':
                possible_paths = ['C:/Program Files/NSIS/makensis.exe',
                                  'C:/Program Files (x86)/NSIS/makensis.exe']
                for path in possible_paths:
                    if os.path.isfile(path):
                        makensis_path = path
                        break
            else:
                program_path = ['wine']

                # The call to makensis requires that the user path be fully
                # qualified and that the program files path be un-escaped.
                makensis_path = \
                    os.path.expanduser('~/.wine/drive_c/Program Files/NSIS/makensis.exe')

        if platform.architecture()[0].startswith('64'):
            architecture = 'x64'
        else:
            architecture = 'x86'

        # make the build dir (which should be relative to __file__), relative
        # to the installer dir (cwd).
        build_dir = os.path.join('..', self.nsis_dir)

        version_string = adept.__version__.replace(':', '_').replace(' ', '_')
        version_string = version_string.replace('[', '').replace(']', '')
        command = ['/DVERSION=%s' % version_string,
                   '/DPY2EXE_FOLDER=%s' % build_dir.replace('/', '\\'),
                   '/DARCHITECTURE=%s' % architecture,
                   installer_path]

        print 'Executing command: %s' % command
        subprocess.call(program_path + [makensis_path] + command)
        os.chdir(cwd)
CMD_CLASSES['win_installer'] = NSISCommand
CMD_CLASSES['zip_data'] = ZipDataCommand

print 'DATA_FILES'
print DATA_FILES

setup(
    name='adept',
    cmdclass=CMD_CLASSES,
    version = adept.__version__,
    data_files = DATA_FILES,
    **py2exe_options)
