import sys
import os
import imp

import faulthandler
faulthandler.enable()  # enable for the ENTIRE adept package.
import natcap.versioner

__version__ = natcap.versioner.get_version('natcap.opal')

def test():
    """Autodiscover and run all tests in the adept package."""
    # use run() here, because it won't automatically quit the python interpreter
    # if we're running it within the interpreter.
    import natcap.opal.tests
    import unittest

    test_runner = unittest.TextTestRunner(verbosity=2)
    test_runner.run(natcap.opal.tests.test_suite())

def execute(args):
    import adept_core
    execute.__doc__ = adept_core.execute.__doc__
    adept_core.execute(args)

def is_frozen():
    if getattr(sys, 'frozen', False):
        # we are running in a |PyInstaller| bundle
        return True
        #basedir = os.path.dirname(sys.executable)
    else:
        return False
        #basedir = os.path.dirname(__file__)

def get_frozen_dir():
    return os.path.dirname(sys.executable)

def local_dir(file_path):
    if getattr(sys, 'frozen', False):
        # we are running in a |PyInstaller| bundle
        # get the folder containing the natcap folder.
        relpath = os.path.relpath(file_path, os.path.dirname(__file__))
        pkg_path = os.path.join('natcap', 'opal', relpath)
        return os.path.join(os.path.dirname(sys.executable), os.path.dirname(pkg_path))
    return os.path.dirname(file_path)


