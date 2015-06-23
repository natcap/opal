import unittest
import time
import os
import sys

import natcap.opal
from natcap.opal import utils

class UtilsTest(unittest.TestCase):
    def test_sigfig(self):
        self.assertEqual(utils.sigfig(123456.1234, 3), 123000.0)
        self.assertEqual(utils.sigfig(1.12345, 3), 1.12)
        self.assertEqual(utils.sigfig(1234, 3), 1230)


class InitTest(unittest.TestCase):
    def test_local_dir_frozen(self):
        sys.frozen = True

        # simulate executable in src directory
        sys.executable = os.path.abspath(os.path.join(
            os.path.dirname(natcap.opal.__file__), '..', '..'))
        filepath = os.path.join(os.path.dirname(natcap.opal.__file__),
                                'report_data', 'table_style.css')
        self.assertEqual(natcap.opal.local_dir(filepath),
                         '/var/natcap/opal/dir')

