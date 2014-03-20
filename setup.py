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

import adept


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
                'scipy.sparse.csgraph._validation',
            ],
            'excludes': ['Tkconstants', 'Tkinter', 'tcl'],
        },
        'build_installer': {'nsis_dir': dist_dir},
    }
    py2exe_options['console'] = ['run_adept.py']

    # Since this repo is not for specific packages, I'm assuming that this
    # section is for py2exe ONLY.
    DATA_FILES.append(('invest_natcap/iui', iui_icons))
    DATA_FILES.append(('adept/report_data',
        glob.glob('adept/adept/report_data/*')))
#    DATA_FILES.append(('data/colombia_static_data',
#        glob.glob('data/colombia_static_data/*')))

    # get specific sets of data files from the tool_data.
    # first, get the vectors.
    tool_data = []
    vectors = ['Ecosystems_Colombia', 'Hydrographic_subzones',
        'Municipalities', 'ecosys_dis_nat_comp_fac', 'hydrozones',
        'sample_aoi', 'watersheds_cuencas']
    for vector_base in vectors:
        glob_pattern = 'data/colombia_tool_data/%s.*' % vector_base
        tool_data += glob.glob(glob_pattern)

    rasters = ['DEM', 'Erodability', 'Erosivity',
        'Plant_available_water_content', 'Precipitation',
        'Ref_evapotranspiration', 'Soil_depth', 'ecosystems']
    for raster in rasters:
        tool_data.append('data/colombia_tool_data/%s.tif' % raster)
#    DATA_FILES.append(('data/colombia_tool_data', tool_data))

    from py2exe.build_exe import py2exe as py2exeCommand
    class CustomPy2exe(py2exeCommand):
        """This is a custom Py2exe command that allows us to define data files
        that are only used for the built executeables.  This is especially
        important now that we include 30MB or so of GDAL DLLs that we don't need
        for any other distribution scheme."""

        def create_binaries(self, py_files, extensions, dlls):
            if self.distribution.data_files == None:
                self.distribution.data_files = []


#            self.distribution.data_files += matplotlib.get_py2exe_datafiles()

            build_dir = os.path.join(os.getcwd(), 'build', 'permitting_data')
            data_dir = os.path.join(build_dir, 'data')
            tool_data_dir = os.path.join(data_dir, 'colombia_tool_data')
            if os.path.exists(tool_data_dir):
                shutil.rmtree(tool_data_dir)
            os.makedirs(tool_data_dir)

            # copy relevant tool data into the tool_data folder.
            for tool_data_file in tool_data:
                new_uri = os.path.join(tool_data_dir,
                        os.path.basename(tool_data_file))
                print 'copying %s -> %s' % (tool_data_file, new_uri)
                shutil.copy(tool_data_file, new_uri)

            # copy all static map data into the static maps folder.
            static_maps_dir = os.path.join(data_dir, 'colombia_static_data')
            os.makedirs(static_maps_dir)
            static_files = glob.glob('data/colombia_static_data/*')
            for static_file in static_files:
                new_uri = os.path.join(static_maps_dir,
                    os.path.basename(static_file))
                print 'copying %s -> %s' % (static_file, new_uri)
                shutil.copy(static_file, new_uri)

            # make the data archive.
            archive_path = os.path.join(build_dir, 'permitting_data')
            shutil.make_archive(archive_path, 'zip', root_dir=build_dir,
                base_dir=data_dir)
            archive_path += '.zip'
            print 'Saved archive %s' % archive_path

            self.distribution.data_files.append(('.', archive_path))

            # After we've defined all our custom data files, we can now add on
            # the data files provided by default in setup.py.
            py2exeCommand.create_binaries(self, py_files, extensions, dlls)

    CMD_CLASSES['py2exe'] = CustomPy2exe
else:
    python_version = 'python%s' % '.'.join([str(r) for r in
        sys.version_info[:2]])
    lib_path = os.path.join('lib', python_version, 'site-packages')
    iui_icon_path = os.path.join(lib_path, 'invest_natcap', 'iui')
    DATA_FILES.append((iui_icon_path, iui_icons))




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
        cwd = os.getcwd()
        os.chdir('installer')  # CD into the installer folder to build it.

        genesis = imp.load_source('genesis', 'genesis.py')
        genesis.build_installer_script('permitting_installer.json',
            'adept_installer.nsi')

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

        version_string = adept.__version__.replace(':', '_').replace(' ', '_')
        command = ['/DVERSION=%s' % version_string,
                   '/DPY2EXE_FOLDER=%s' % self.nsis_dir,
                   '/DARCHITECTURE=%s' % architecture,
                   'adept_installer.nsi']

        subprocess.call(program_path + [makensis_path] + command)
        os.chdir(cwd)
CMD_CLASSES['win_installer'] = NSISCommand

setup(
    name='adept',
    cmdclass=CMD_CLASSES,
    version = adept.__version__,
    data_files = DATA_FILES,
    **py2exe_options)
