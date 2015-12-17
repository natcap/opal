import unittest

from natcap.opal import reporting

class SigFigTest(unittest.TestCase):
    """
    Tests for significant figure calculations on various numbers.
    """
    def test_sigfig_integer(self):
        output_num = reporting.sigfig(12345, 3)
        self.assertEqual(output_num, 12300)

    def test_sigfig_ceiling(self):
        output_num = reporting.sigfig(12369, 3)
        self.assertEqual(output_num, 12400)

    def test_sigfig_float(self):
        output_num = reporting.sigfig(1.1234, 3)
        self.assertEqual(output_num, 1.12)

    def test_sigfig_largefloat(self):
        output_num = reporting.sigfig(12345.5678, 4)
        self.assertEqual(output_num, 12350.0)

    def test_sigfig_large_negative(self):
        output_num = reporting.sigfig(-12345.34, 3)
        self.assertEqual(output_num, -12300.0)

