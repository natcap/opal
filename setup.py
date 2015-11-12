import distutils
from setuptools import setup
from setuptools import Command
from distutils.command.build import build as _build
from distutils.command.build_py import build_py as _build_py
from distutils.command.install_data import install_data as _install_data
import platform
import imp
import os
import subprocess
import sys
import glob
import shutil
import json

import natcap.versioner
from natcap.versioner import versioning

CMD_CLASSES = {}
SITE_PACKAGES = distutils.sysconfig.get_python_lib()

# get specific sets of data files from the tool_data.
# first, get the vectors.
vectors = {
    'subzones': 'Hydrographic_subzones',
    'municipalities': 'Municipalities',
    'ecosystems': 'ecosys_dis_nat_comp_fac',
    'hydrozones': 'hydrozones',
    'sample_aoi': 'sample_aoi',
    'watersheds': 'watersheds_cuencas',
    'servicesheds_old': 'Servicesheds_Col',
    'servicesheds_new': 'ssheds_Col_new',
}

tool_data = glob.glob('data/colombia_tool_data/*.csv')
for vector_key, vector_base in vectors.iteritems():
    if vector_key in ['servicesheds_old']:
        continue
    glob_pattern = 'data/colombia_tool_data/%s.*' % vector_base
    tool_data += glob.glob(glob_pattern)

tif_rasters = ['DEM', 'Erodability', 'Erosivity',
    'Plant_available_water_content', 'Precipitation',
    'Ref_evapotranspiration', 'Soil_depth', 'converted_veg_deforest',
    'ecosystems']
for raster in tif_rasters:
    tool_data.append('data/colombia_tool_data/%s.tif' % raster)

class ToolDataColombia(Command):
    """Zip up colombia internal tool data"""
    description = "Custom command to gather up internal tool data for MAFE"
    user_options = [
        ('tool-data-zip=', None, 'Output zip for tool data')
    ]

    def initialize_options(self):
        self.tool_data_zip = None

    def finalize_options(self):
        pass

    def run(self):
        from natcap.opal import preprocessing
        tool_data_dir = os.path.join(os.getcwd(), 'build', 'co_tool_data')
        if not os.path.exists(tool_data_dir):
            os.makedirs(tool_data_dir)

        # copy relevant tool data into the tool_data folder.
        print '\nStarting to copy tool data'
        for tool_data_file in tool_data:
            new_uri = os.path.join(tool_data_dir,
                    os.path.basename(tool_data_file))

            if tool_data_file.endswith('.tif'):
                tif_basename = os.path.basename(tool_data_file)
                if 'protection' in tif_basename:
                    tif_basename = tif_basename.replace('protection', 'future')
                    new_uri = os.path.join(tool_data_dir, tif_basename)

                print 'Uncompressing %s -> %s' % (tool_data_file, new_uri)
                preprocessing.recompress_gtiff(tool_data_file, new_uri, 'NONE')
            else:
                print 'copying %s -> %s' % (tool_data_file, new_uri)
                shutil.copy(tool_data_file, new_uri)

        # make the data archives
        dist_dir = os.path.join(os.getcwd(), 'dist')
        tool_zip = os.path.join(dist_dir, 'tool_data')
        print "Building %s.zip" % tool_zip
        shutil.make_archive(tool_zip, 'zip', root_dir=tool_data_dir)
        print 'Finished %s.zip (%sMB)' % (tool_zip,
            os.path.getsize(tool_zip + '.zip') >> 20)

class ZipColombiaData(Command):
    """Zip up all colombia static and tool data."""
    description = "Custom command to gather up the various data"

    user_options = [
        ('static-data-zip=', None, 'Output zip for static data'),
    ]

    def initialize_options(self):
        self.static_data_zip = None

    def finalize_options(self):
        pass

    def run(self):
        from natcap.opal import preprocessing
        build_dir = os.path.join(os.getcwd(), 'build', 'permitting_data')
        dist_dir = os.path.join(os.getcwd(), 'dist')
        data_dir = os.path.join(build_dir, 'data')
        tool_data_dir = os.path.join(data_dir, 'colombia_tool_data')
        if os.path.exists(tool_data_dir):
            shutil.rmtree(tool_data_dir)
        os.makedirs(tool_data_dir)

        # copy all static map data into the static maps folder.
        print '\nStarting to copy static data'
        static_maps_dir = os.path.join(data_dir, 'colombia_static_data')

        static_files = [
            ('carbon', glob.glob('data/colombia_static_data/carbon*.tif')),
            ('nutrient', glob.glob('data/colombia_static_data/nutrient*lzw.tif')),
            ('nutrient_pts', glob.glob('data/colombia_static_data/nutrient*pts.tif')),
            ('sdr', glob.glob('data/colombia_static_data/sediment*lzw.tif')),
        ]
        for sm_name, static_rasters in static_files:
            print '\nCopying %s data' % sm_name
            sm_dir = os.path.join(static_maps_dir, sm_name)
            os.makedirs(sm_dir)

            for static_file in static_rasters:
                new_uri = os.path.join(sm_dir, os.path.basename(static_file))
                print 'Uncompressing %s -> %s' % (static_file, new_uri)
                preprocessing.recompress_gtiff(static_file, new_uri, 'NONE')

            static_data_zip = os.path.join(dist_dir, sm_name)
            print "Building %s.zip" % static_data_zip
            shutil.make_archive(static_data_zip, 'zip', root_dir=sm_dir)
            print 'Finished %s.zip (%sMB)' % (static_data_zip,
                    os.path.getsize(static_data_zip + '.zip') >> 20)

class SampleDataCommand(Command):
    description = "Prepares sample data for a single hydrozone"
    user_options = []
    scenarios = ['bare', 'paved', 'protection']

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _gather_single_hydrozone_data(self):
        from natcap.opal import preprocessing
        from natcap.opal import static_maps
        print ''
        print 'gathering single-hydrozone sample data'

        build_dir = os.path.join(os.getcwd(), 'build', 'permitting_data')
        dist_dir = os.path.join(os.getcwd(), 'dist')

        data_dir = os.path.join(build_dir, 'sample_data')
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
        os.makedirs(data_dir)

        print '\nDetermining active hydrozone'
        active_hydrozone = os.path.join(data_dir, 'active_hzone.shp')
        self.active_hydrozone = active_hydrozone
        hydrozones = os.path.join(os.getcwd(), 'data', 'colombia_tool_data',
            'hydrozones.shp')
        impacts = os.path.join(os.getcwd(), 'data', 'colombia_sample_data',
            'sogamoso_sample', 'mine_site.shp')

        # determine the active hydrozone.
        preprocessing.locate_intersecting_polygons(hydrozones, impacts,
            active_hydrozone)

        print '\nClipping static maps'
        service_dir = os.path.join(data_dir, 'services_static_data')
        static_maps_dir = os.path.join(os.getcwd(), 'data',
            'colombia_static_data')
        for service in ['sediment', 'nutrient', 'carbon']:
            service_out_dir = os.path.join(service_dir, service)
            os.makedirs(service_out_dir)
            for scenario in self.scenarios:
                map_name = '%s_%s_static_map_lzw.tif' % (service, scenario)
                new_map_name = map_name.replace('_lzw', '')
                src_static_map = os.path.join(static_maps_dir, map_name)

                # rename the sample protection static maps to 'future'
                if scenario == 'protection':
                    new_map_name = new_map_name.replace(scenario, 'protect')
                dst_static_map = os.path.join(service_out_dir, new_map_name)

                print 'Clipping %s' % new_map_name
                static_maps.clip_static_map(src_static_map, active_hydrozone,
                    dst_static_map)

                if service in ['sediment', 'nutrient']:
                    # same thing for pts rasters
                    map_name = '%s_%s_pts.tif' % (service, scenario)
                    src_raster = os.path.join(static_maps_dir, map_name)
                    if scenario == 'protection':
                        map_name = map_name.replace('protection', 'protect')
                    dst_raster = os.path.join(service_out_dir, map_name)

                    print 'Clipping %s' % map_name
                    static_maps.clip_static_map(src_raster, active_hydrozone,
                        dst_raster)

        print '\nCollecting sample vectors'
        vectors_to_copy = ['mine_site', 'power_line']
        for vector_base in vectors_to_copy:
            glob_pattern = 'data/colombia_sample_data/sogamoso_sample/%s.*' % vector_base
            for source_file in glob.glob(glob_pattern):
                dest_file = os.path.join(service_dir,
                    os.path.basename(source_file))
                print 'Copying %s -> %s' % (source_file, dest_file)
                shutil.copyfile(source_file, dest_file)


    def run(self, gather_hzone_data=True):
        if gather_hzone_data:
            self._gather_single_hydrozone_data()

        print ''
        print 'Zipping up single-hydrozone sample data'

        dist_dir = os.path.join(os.getcwd(), 'dist')
        build_dir = os.path.join(os.getcwd(), 'build', 'permitting_data')
        data_dir = os.path.join(build_dir, 'sample_data')
        service_dir = os.path.join(data_dir, 'services_static_data')

        sample_data_zip = os.path.join(dist_dir, 'sample_data')
        print "\nBuilding %s.zip" % sample_data_zip
        shutil.make_archive(sample_data_zip, 'zip', root_dir=service_dir)
        print 'Finished %s.zip (%sMB)' % (sample_data_zip,
                os.path.getsize(sample_data_zip + '.zip') >> 20)

class SampleDataGlobalCommand(SampleDataCommand):
    description = "Zip up required tool and static data for OPAL"
    user_options = ['no-zip']

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from natcap.opal import preprocessing
        self._gather_single_hydrozone_data()
        # active hydrozone URI saved to self.active_hydrozone
        dest_dir = os.path.join('build', 'permitting_data', 'sample_data',
            'services_static_data')

        opal_vectors = [
            (vectors['ecosystems'], 'natural_ecosystems'),
            (vectors['servicesheds_old'], 'servicesheds'),
            (vectors['subzones'], 'hydrographic_subzones')
        ]
        for vector_base, new_base in opal_vectors:
            vector_uri = os.path.join('data', 'colombia_tool_data',
                vector_base + '.shp')
            new_uri = os.path.join(dest_dir, new_base + '.shp')

            print 'Copying %s -> %s' % (vector_uri, new_uri)
            preprocessing.locate_intersecting_polygons(vector_uri,
                self.active_hydrozone, new_uri, clip=True)

        SampleDataCommand.run(self, False)

class NSISCommand(Command):
    """Uses two options: "version" : the rios version; "nsis_dir" : the
    installation directory containing the py2exe executeables to be packaged
    up."""
    description = "Custom command to build our NSIS installer."

    # This list of tuples allows for command-line options for this distutils
    # command.
    user_options = [
        ('genesis-config=', None, 'Genesis-compatible configuration file'),
        ('nsis-dir=', None, 'Folder with executeables to compress.'),
        ('nsis-install=', None, 'Location of the NSIS installation on disk'),
    ]

    def initialize_options(self):
        self.build_dir = os.path.join(os.getcwd(), 'build',
            'nsis-%s' % self.dist_name)

        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)
        os.makedirs(self.build_dir)

        self.nsis_dir = os.path.expanduser(self.nsis_dir)
        if not os.path.exists(self.nsis_dir):
            print self.nsis_dir, 'does not exist'
            raise IOError('%s does not exist' % self.nsis_dir)

        if not os.path.isdir(self.nsis_dir):
            self.nsis_dir = self.nsis_dir[:-1]

        self.nsis_install = None

    def finalize_options(self):
        pass

    def write_dist_data(self, dist_name):
        dist_data = versioning.build_data()
        dist_data['dist_name'] = dist_name

        data_file = os.path.join(self.nsis_dir, 'dist_version.json')
        json.dump(dist_data, open(data_file, 'w+'))

    def remove_dist_data(self):
        dist_file = os.path.join(self.nsis_dir, 'dist_version.json')
        if os.path.exists(dist_file):
            os.remove(dist_file)

    def run(self):
        print ''
        print 'Starting NSIS installer build'

        # copy the natcap icon/logo to the nsis_dir
        _icon_name = 'natcap_logo.ico'
        source_file = os.path.join(os.getcwd(), 'windows_build', _icon_name)
        dest_file = os.path.join(self.nsis_dir, _icon_name)
        shutil.copyfile(source_file, dest_file)

        if not os.path.abspath(self.genesis_config):
            self.genesis_config = os.path.abspath(self.genesis_config)

        print 'Genesis configuration', self.genesis_config
        print 'Distribution name', self.dist_name
        print 'Build dir', self.build_dir

        target_dir = os.path.join(self.build_dir, os.path.basename(self.nsis_dir))
        if os.path.exists(target_dir):
            print 'Removing existing folder %s' % target_dir
            shutil.rmtree(target_dir)

        print 'Copying %s -> %s' % (self.nsis_dir, target_dir)
        shutil.copytree(self.nsis_dir, target_dir)

        cwd = os.getcwd()
        os.chdir('installer')  # CD into the installer folder to build it.

        installer_path = os.path.join('%s_installer.nsi' % self.dist_name)
        genesis = imp.load_source('genesis', 'genesis.py')
        genesis.build_installer_script(os.path.relpath(self.genesis_config),
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

        # determine the version string, based on the tag of the permitting repo
        # if we're at the tag, then that's the version.  Otherwise, get the
        # build ID, which includes relevant revision information.
        if versioning.get_tag_distance() > 0:
            version_string = versioning.get_build_id()
        else:
            # if we're on a master branch, we only want the version num.
            # If we're not on a master branch, just use the latest tag.
            version_string = versioning.get_latest_tag()
            branchname = versioning.get_branch()
            if branchname.startswith('master/'):
                dist = branchname.replace('master/', '')
                version_string = version_string.replace(dist + '-', '')

        # sanitize the version string
        version_string = version_string.replace(':', '_').replace(' ', '_')
        version_string = version_string.replace('[', '').replace(']', '')
        command = ['/DVERSION=%s' % version_string,
                   '/DPY2EXE_FOLDER=%s' % build_dir.replace('/', '\\'),
                   '/DARCHITECTURE=%s' % architecture,
                   installer_path]

        print 'Program path', program_path
        print 'Makensis path', makensis_path
        print 'Executing with arguments: %s' % command
        subprocess.call(program_path + [makensis_path] + command,
            stdout=sys.stdout)
        os.chdir(cwd)

class ColombiaDistribution(NSISCommand):
    description = "Build the Colombia installer"

    # This list of tuples allows for command-line options for this distutils
    # command.
    user_options = [
        ('genesis-config=', None, 'Genesis-compatible configuration file'),
        ('nsis-dir=', None, 'Folder with executeables to compress.'),
        ('nsis-install=', None, 'Location of the NSIS installation on disk'),
    ]

    def initialize_options(self):
        self.genesis_config = os.path.abspath('installer/mafe_installer.json')
        self.dist_name = 'colombia'
        self.nsis_dir = os.path.abspath('dist/total_coll_mafe')

        mafe_name_src = os.path.join(os.getcwd(), 'windows_build',
            'MAFE', 'MAFE-T_NAME.txt')
        mafe_name_dest = os.path.join(self.nsis_dir, 'ASCII_NAME.txt')
        shutil.copyfile(mafe_name_src, mafe_name_dest)

        NSISCommand.initialize_options(self)

    def finalize_options(self):
        pass

    def run(self):
        self.run_command('sample_data')
        self.run_command('tool_data_colombia')
        self.write_dist_data('MAFE-T')

        # copy documentation to the nsis_dir
        source_file = glob.glob(os.path.join(os.getcwd(), 'windows_build', 'MAFE',
            '*.pdf'))
        if len(source_file) > 1:
            raise Exception('Which MAFE-T pdf did you want to grab?')
        else:
            source_file = source_file[0]

        dest_file = os.path.join(self.nsis_dir, 'MAFE-T-user-guide.pdf')
        shutil.copyfile(source_file, dest_file)

        # copy the zipfiles we need into the right place.
        target_dir = os.path.join(self.build_dir, os.path.basename(self.nsis_dir))
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # copy the distribution UI config file to the pyinstaller dist folder.
        source_file = os.path.join('windows_build', 'MAFE', 'dist_config.json')
        dest_dist_config_file = os.path.join(self.nsis_dir, 'dist_config.json')
        print 'Copying %s -> %s' % (source_file, dest_dist_config_file)
        shutil.copyfile(source_file, dest_dist_config_file)

        mafe_splash_src = os.path.join(os.getcwd(), 'windows_build',
            'MAFE', 'MAFE-T.png')
        mafe_splash_dest = os.path.join(self.nsis_dir, 'splash.png')
        print 'Copying %s -> %s' % (mafe_splash_src, mafe_splash_dest)
        shutil.copyfile(mafe_splash_src, mafe_splash_dest)

        mafe_json_src = os.path.join(os.getcwd(), 'adept.json')
        mafe_json_dest = os.path.join(self.nsis_dir, 'opal.json')
        shutil.copyfile(mafe_json_src, mafe_json_dest)

        for filename in ['tool_data.zip']:
            source_file = os.path.join('dist', filename)
            dest_file = os.path.join(target_dir, filename)
            print 'Copying %s -> %s' % (source_file, dest_file)
            shutil.copyfile(source_file, dest_file)

        NSISCommand.run(self)
        self.remove_dist_data()
        os.remove(dest_dist_config_file)  # remove MAFE dist_config file.


class GlobalDistribution(NSISCommand):
    description = "Build the Global OPAL installer"

    # This list of tuples allows for command-line options for this distutils
    # command.
    user_options = [
        ('genesis-config=', None, 'Genesis-compatible configuration file'),
        ('nsis-dir=', None, 'Folder with executeables to compress.'),
        ('nsis-install=', None, 'Location of the NSIS installation on disk')
    ]

    def initialize_options(self):
        self.genesis_config = os.path.abspath('installer/opal_installer.json')
        self.nsis_dir = os.path.abspath('dist/total_coll')
        self.dist_name = 'global'

        opal_name_src = os.path.join(os.getcwd(), 'windows_build',
            'OPAL_NAME.txt')
        opal_name_dest = os.path.join(self.nsis_dir, 'ASCII_NAME.txt')
        shutil.copyfile(opal_name_src, opal_name_dest)

        opal_splash_src = os.path.join(os.getcwd(), 'windows_build',
            'OPAL.png')
        opal_splash_dest = os.path.join(self.nsis_dir, 'splash.png')
        print 'Copying %s -> %s' % (opal_splash_src, opal_splash_dest)
        shutil.copyfile(opal_splash_src, opal_splash_dest)

        opal_logo_src = os.path.join(os.getcwd(), 'windows_build',
            'opal-logo-alone.png')
        opal_logo_dst = os.path.join(self.nsis_dir, 'app-window-logo.png')
        print 'Copying %s -> %s' % (opal_logo_src, opal_logo_dst)
        shutil.copyfile(opal_logo_src, opal_logo_dst)

        full_opal_logo_src = os.path.join(os.getcwd(), 'installer',
            'opal_images', 'opal-logo-small.png')
        full_opal_logo_dst = os.path.join(self.nsis_dir, 'opal-logo-small.png')
        print 'Copying %s -> %s' % (full_opal_logo_src, full_opal_logo_dst)
        shutil.copyfile(full_opal_logo_src, full_opal_logo_dst)

        mafe_json_src = os.path.join(os.getcwd(), 'opal.json')
        mafe_json_dest = os.path.join(self.nsis_dir, 'opal.json')
        shutil.copyfile(mafe_json_src, mafe_json_dest)

        NSISCommand.initialize_options(self)

    def finalize_options(self):
        pass

    def run(self):
        version = versioning.build_data()['version_str']
        self.run_command('sample_data_global')
        self.write_dist_data('OPAL')

        # Build the documentation.  Installer expects the PDFs to be in the
        # repo root, which is where the makefile will leave it.
        cwd = os.getcwd()
        os.chdir('doc/users-guide')
        subprocess.call(['make', 'all', 'VERSION="%s"' % version])
        os.chdir(cwd)

        # copy the distribution UI config file to the pyinstaller dist folder.
        source_file = os.path.join('windows_build', 'dist_config.json')
        dest_dist_config_file = os.path.join(self.nsis_dir, 'dist_config.json')
        print 'Copying %s -> %s' % (source_file, dest_dist_config_file)
        shutil.copyfile(source_file, dest_dist_config_file)

        NSISCommand.run(self)

try:
    from natcap.opal.i18n import msgfmt as opal_i18n_msgfmt
except ImportError:
    opal_i18n_msgfmt = imp.load_source('i18n', 'src/natcap/opal/i18n/msgfmt.py')

class build(_build):
    """Custom python build step for distutils.  Builds the OPAL translations
    as part of the build step."""
    sub_commands = _build.sub_commands + [('build_trans', None)]
    def run(self):
        _build.run(self)

class build_translations(Command):
    """Custom distutions command to compile translation files for installation."""
    description = 'Compile .po files to .mo files'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        po_dir = os.path.join(os.path.dirname(os.curdir), 'i18n')
        for path, names, filenames in os.walk(po_dir):
            for filepath in filenames:
                if filepath.endswith('.po'):
                    lang_code = filepath[:-3]
                    src = os.path.join(path, filepath)
                    dest_path = os.path.join('build', 'locale', lang_code,
                            'LC_MESSAGES')
                    dest = os.path.join(dest_path, 'adept.mo')
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)

                    # I always want to recompile.
                    print 'Compiling %s to %s' % (src, dest)
                    opal_i18n_msgfmt.make(src, dest)

class build_py(_build_py):
    def run(self):
        self.run_command('build_trans')
        _build_py.run(self)

class install_data(_install_data):
    def run(self):
        for lang in os.listdir('build/locale'):
            lang_dir = os.path.join('natcap', 'opal', 'i18n',
                'locale', lang, 'LC_MESSAGES')
            lang_file = os.path.join('build', 'locale', lang, 'LC_MESSAGES',
                'adept.mo')
            self.data_files.append((lang_dir, [lang_file]))
        _install_data.run(self)

CMD_CLASSES['dist_colombia'] = ColombiaDistribution
CMD_CLASSES['dist_global'] = GlobalDistribution
CMD_CLASSES['static_data_colombia'] = ZipColombiaData
CMD_CLASSES['sample_data'] = SampleDataCommand
CMD_CLASSES['sample_data_global'] = SampleDataGlobalCommand
CMD_CLASSES['tool_data_colombia'] = ToolDataColombia
CMD_CLASSES['build'] = build
CMD_CLASSES['build_py'] = build_py
CMD_CLASSES['build_trans'] = build_translations
CMD_CLASSES['install_data'] = install_data
CMD_CLASSES['build'] = build

README = open('README.rst').read()
CHANGES = open('CHANGES.txt').read()
LICENSE = open('LICENSE.txt').read()

def load_version():
    """
    Load the version string.

    If we're in a source tree, load the version from the opal __init__ file.
    If we're in an installed version of opal, use the __version__attribute.
    """
    try:
        import natcap.opal as opal
    except ImportError:
        import imp
        opal = imp.load_source('natcap.opal', 'src/natcap/opal/__init__.py')
    return opal.__version__

setup(
    name='natcap.opal',
    description="Decision support tool for mitigating development impacts to ecosystem services",
    long_description=README + '\n\n' + CHANGES,
    maintainer='James Douglass',
    maintainer_email='jdouglass@stanford.edu',
    url='https://bitbucket.org/natcap/opal',
    packages=[
        'natcap',
        'natcap.opal',
        'natcap.opal.i18n',
        'natcap.opal.tests'
    ],
    package_dir={
        'natcap': 'src/natcap',
    },
    requires=[
        'numpy',
        'scipy',
        'shapely',
        'GDAL',
        'pyyaml',
    ],
    version=natcap.versioner.parse_version(),
    natcap_version='src/natcap/opal/version.py',
    cmdclass=CMD_CLASSES,
    license=LICENSE,
    keywords='GIS',
    classifiers=[
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    package_data={
        'natcap.opal': ['report_data/*', 'static_data/*'],
    }
)
