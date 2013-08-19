from distutils.core import setup
from distutils.core import Command
import platform
import imp
import os
import subprocess

import adept


py2exe_options = {}
if platform.system() == 'Windows':
    import py2exe
    dist_dir = 'adept_py2exe'
    py2exe_options['options'] ={
        'py2exe': {
            'dist_dir': dist_dir,
            'packages': ['adept'],
            'skip_archive': True,
            'excludes': ['Tkconstants', 'Tkinter', 'tcl'],
        },
        'build_installer': {'nsis_dir': dist_dir},
    }
    py2exe_options['console'] = ['run_adept.py']

DATA_FILES = [('.', 'adept.json')]

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


setup(
    name='adept',
    cmdclass={
        'win_installer': NSISCommand
    },
    version = adept.__version__,
    data_files = DATA_FILES,
    packages=['adept'],
    **py2exe_options)
