import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_v4_historical_fetch import parse,summarize
T=datetime(2026,10,25,19,0,tzinfo=timezone.utc)
def payload(n=300):
    return {"values":[{"datetime":(T+timedelta(minutes=15*i)).isoformat(),
        "open":"80000","high":"80100","low":"79900","close":"80020"} for i in range(n)]}
class HistoricalFetchTests(unittest.TestCase):
    def test_300_closed_bars(self):
        x=parse(payload(),"15min",T+timedelta(minutes=15*301))
        self.assertEqual(len(x),300)
        self.assertEqual(summarize(x,"15min")["gaps"],0)
    def test_unclosed_excluded(self):
        x=parse(payload(),"15min",T+timedelta(minutes=15*299))
        self.assertLess(len(x),300)
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):parse({"values":[]},"15min",T)
    def test_provider_error(self):
        with self.assertRaises(ValueError):parse({"status":"error","message":"limit"},"15min",T)
    def test_gaps_identified(self):
        x=parse(payload(),"15min",T+timedelta(days=5))
        self.assertEqual(summarize(x[:100]+x[102:],"15min")["gaps"],1)
if __name__=="__main__":unittest.main()
