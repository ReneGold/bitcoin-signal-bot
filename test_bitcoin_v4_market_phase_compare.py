import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_v4_market_phase_compare import classify,trend_context
from bitcoin_signal_bot import Candle
T=datetime(2026,10,26,12,0,tzinfo=timezone.utc)
def history(up=True):
    return [Candle(T-timedelta(hours=100-i),100+i if up else 300-i,
                   101+i if up else 301-i,99+i if up else 299-i,
                   100+i if up else 300-i) for i in range(101)]
class BTCMarketPhaseTests(unittest.TestCase):
    def test_trend_long(self):
        h=history()
        self.assertEqual(trend_context(h,T+timedelta(hours=1)),"LONG")
    def test_trend_short(self):
        self.assertEqual(trend_context(history(False),T+timedelta(hours=1)),"SHORT")
    def test_future_hour_excluded(self):
        h=history()
        x=trend_context(h,T)
        h.append(Candle(T+timedelta(hours=2),10000,10001,9999,10000))
        self.assertEqual(trend_context(h,T),x)
    def test_closed_setup_required(self):
        with self.assertRaises(ValueError):
            classify(side="LONG",signal_open=T,closed_at=T+timedelta(minutes=10),
                h=history(),fast=10,slow=9,atr=1)
    def test_strength_blocks(self):
        r=classify(side="LONG",signal_open=T,closed_at=T+timedelta(minutes=15),
                   h=history(),fast=10,slow=9.7,atr=1)
        self.assertTrue(r["trend_pass"]);self.assertFalse(r["strong_pass"])
    def test_strength_accepts(self):
        r=classify(side="LONG",signal_open=T,closed_at=T+timedelta(minutes=15),
                   h=history(),fast=10,slow=9,atr=1)
        self.assertTrue(r["strong_pass"])
    def test_missing_atr_fails(self):
        r=classify(side="LONG",signal_open=T,closed_at=T+timedelta(minutes=15),
                   h=history(),fast=10,slow=9,atr=None)
        self.assertFalse(r["trend_pass"])
if __name__=="__main__":unittest.main()
