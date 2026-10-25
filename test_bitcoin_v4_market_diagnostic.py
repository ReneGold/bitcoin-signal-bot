import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_v4_market_diagnostic import parse_bars,diagnose
from bitcoin_entry_timer import Candle
T=datetime(2026,10,26,16,0,tzinfo=timezone.utc)
def payload(t):
    return {"values":[{"datetime":t.isoformat(),"open":"80000","high":"80200",
                       "low":"79800","close":"80100"}]}
class BTCMarketDiagnosticTests(unittest.TestCase):
    def test_finished_candle(self):
        self.assertEqual(len(parse_bars(payload(T),"15min",T+timedelta(minutes=16))),1)
    def test_incomplete_candle_excluded(self):
        self.assertEqual(parse_bars(payload(T),"15min",T+timedelta(minutes=10)),[])
    def test_bad_feed(self):
        with self.assertRaises(ValueError):parse_bars({"status":"error"},"15min",T)
    def test_no_duplicates(self):
        p=payload(T);p["values"].append(p["values"][0])
        with self.assertRaises(ValueError):parse_bars(p,"5min",T+timedelta(minutes=20))
    def test_fail_closed_with_real_candle_shapes(self):
        c15=[Candle(T+timedelta(minutes=15*i),80000,80200,79800,80100) for i in range(120)]
        c5=[Candle(T+timedelta(minutes=5*i),80000,80200,79800,80100) for i in range(360)]
        r=diagnose(c15,c5,T+timedelta(minutes=1805))
        self.assertEqual(r["v4_safety_status"],"NOT_READY")
        self.assertFalse(r["calendar_verified"])
if __name__=="__main__":unittest.main()
