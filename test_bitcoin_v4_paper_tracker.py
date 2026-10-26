import unittest,json
from datetime import datetime,timedelta,timezone
from bitcoin_v4_paper_tracker import make_rows,advance
from bitcoin_signal_bot import Candle
T=datetime(2026,10,26,7,0,tzinfo=timezone.utc)
def sig():
    return dict(signal_open_utc=T.isoformat(),side="LONG",stop_usd="79000",
                baseline_accepted="1",asymmetric_accepted="0")
def bar(t,o=80000,h=80100,l=79900,c=80000):
    return Candle(t,o,h,l,c)
class PaperTrackerTests(unittest.TestCase):
    def test_variants_isolated(self):
        x=make_rows([sig()],[])
        self.assertEqual(len(x),1)
    def test_closed_bar_enters_and_advances(self):
        x=make_rows([sig()],[])
        advance(x,[bar(T+timedelta(minutes=15))])
        self.assertEqual(list(x.values())[0]["status"],"OPEN")
    def test_target_closes(self):
        x=make_rows([sig()],[])
        advance(x,[bar(T+timedelta(minutes=15),h=83000)])
        self.assertEqual(list(x.values())[0]["status"],"CLOSED")
    def test_stop_has_priority(self):
        x=make_rows([sig()],[])
        advance(x,[bar(T+timedelta(minutes=15),h=83000,l=78000)])
        r=list(x.values())[0]
        self.assertEqual(r["status"],"CLOSED")
        self.assertLess(float(r["net_R"]),0)
    def test_idempotent(self):
        x=make_rows([sig()],[]);b=[bar(T+timedelta(minutes=15))]
        advance(x,b);original=json.dumps(x,sort_keys=True)
        advance(x,b)
        self.assertEqual(json.dumps(x,sort_keys=True),original)
    def test_no_backfilled_missing_entry(self):
        x=make_rows([sig()],[])
        advance(x,[bar(T+timedelta(minutes=30))])
        self.assertEqual(list(x.values())[0]["status"],"INSUFFICIENT_HISTORY")
if __name__=="__main__":unittest.main()
