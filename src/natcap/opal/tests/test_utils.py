import unittest
import time

from adept import utils

class UtilsTest(unittest.TestCase):
    def test_sigfig(self):
        self.assertEqual(utils.sigfig(123456.1234, 3), 123000.0)
        self.assertEqual(utils.sigfig(1.12345, 3), 1.12)
        self.assertEqual(utils.sigfig(1234, 3), 1230)

