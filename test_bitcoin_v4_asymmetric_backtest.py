import unittest
from bitcoin_v4_asymmetric_backtest import permitted
class BTCAsymmetryTests(unittest.TestCase):
    def test_shorts_not_filtered(self):
        self.assertTrue(permitted("SHORT",{"strong_pass":False},"ASYMMETRIC"))
    def test_long_requires_strength(self):
        self.assertFalse(permitted("LONG",{"strong_pass":False},"ASYMMETRIC"))
        self.assertTrue(permitted("LONG",{"strong_pass":True},"ASYMMETRIC"))
    def test_baseline_unchanged(self):
        self.assertTrue(permitted("LONG",{"strong_pass":False},"BASELINE"))
    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError):permitted("SHORT",{},"X")
if __name__=="__main__":unittest.main()
