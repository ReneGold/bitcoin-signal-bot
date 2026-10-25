import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_entry_timer import Candle,assess_entry
T=datetime(2026,10,26,12,15,tzinfo=timezone.utc)
def b(minutes,close,high=None,low=None):
    o=70000
    return Candle(T+timedelta(minutes=minutes),o,high if high is not None else max(o,close)+100,
                  low if low is not None else min(o,close)-100,close)
def run(bars,minutes=10,**kw):
    x=dict(signal_close_utc=T,side="LONG",trigger=70100,invalid_level=69500,
           five_minute_bars=bars,now_utc=T+timedelta(minutes=minutes))
    x.update(kw)
    return assess_entry(**x)
class BitcoinEntryTimerTests(unittest.TestCase):
    def test_confirm_long(self):self.assertEqual(run([b(0,70200)],5)["status"],"CONFIRMED")
    def test_confirm_short(self):self.assertEqual(run([b(0,69800)],5,side="SHORT",trigger=69900,invalid_level=70500)["status"],"CONFIRMED")
    def test_unclosed_5min_no_confirmation(self):self.assertEqual(run([b(5,70300)],8)["status"],"WAITING")
    def test_wick_not_enough(self):self.assertEqual(run([b(0,70000,high=71000)],5)["status"],"WAITING")
    def test_stop_invalidation(self):self.assertEqual(run([b(0,69400)],5)["status"],"INVALID")
    def test_expired(self):self.assertEqual(run([],30)["status"],"EXPIRED")
    def test_old_bar_ignored(self):self.assertEqual(run([b(-5,70400)],5)["status"],"WAITING")
    def test_future_bar_ignored(self):self.assertEqual(run([b(15,70400)],10)["status"],"WAITING")
    def test_naive_timezone_rejected(self):self.assertEqual(run([],signal_close_utc=T.replace(tzinfo=None))["status"],"INVALID")
    def test_invalid_stop_rejected(self):self.assertEqual(run([],invalid_level=70200)["status"],"INVALID")
    def test_invalid_ohlc(self):self.assertEqual(run([b(0,70200,high=70000)],5)["status"],"INVALID")
if __name__=="__main__":unittest.main()
