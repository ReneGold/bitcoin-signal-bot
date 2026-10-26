import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_v4_telegram import new_signals,message
T=datetime(2026,10,26,8,0,tzinfo=timezone.utc)
def row(asym="1",closed=None):
    return {"signal_open_utc":(T-timedelta(minutes=15)).isoformat(),
        "signal_closed_utc":(closed or T).isoformat(),"side":"LONG",
        "baseline_accepted":"1","asymmetric_accepted":asym,
        "score":"60","entry_reference_usd":"80000","stop_usd":"79000"}
class BitcoinTelegramTests(unittest.TestCase):
    def test_new_signal(self):self.assertEqual(len(new_signals([row()],set(),T)),1)
    def test_baseline_only_still_notified(self):
        self.assertEqual(len(new_signals([row("0")],set(),T)),1)
    def test_dedup(self):
        seen=set();new_signals([row()],seen,T)
        self.assertEqual(new_signals([row()],seen,T),[])
    def test_stale_not_sent(self):
        self.assertEqual(new_signals([row(closed=T-timedelta(hours=2))],set(),T),[])
    def test_test_label(self):
        msg=message(row("0"))
        self.assertIn("TESTSIGNAL",msg);self.assertIn("abgelehnt",msg)
        self.assertIn("keine automatische Order",msg)
if __name__=="__main__":unittest.main()
