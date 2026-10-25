import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_entry_timer import Candle
from bitcoin_v4_pullback_timer import confirm_pullback
T=datetime(2026,10,26,12,15,tzinfo=timezone.utc)
def bar(i,c):return Candle(T+timedelta(minutes=5*i),80000,max(80000,c)+10,min(80000,c)-10,c)
def check(bars,now=30,side="LONG",stop=79000):
    return confirm_pullback(signal_close_utc=T,side=side,signal_price=80000,
        stop=stop,bars5=bars,now_utc=T+timedelta(minutes=now))
class PullbackTests(unittest.TestCase):
    def test_long(self):self.assertEqual(check([bar(0,79800),bar(1,80100)])["status"],"CONFIRMED")
    def test_short(self):self.assertEqual(check([bar(0,80200),bar(1,79900)],side="SHORT",stop=81000)["status"],"CONFIRMED")
    def test_no_recovery(self):self.assertEqual(check([bar(0,79800)])["status"],"EXPIRED")
    def test_no_pullback(self):self.assertEqual(check([bar(0,80200)])["status"],"EXPIRED")
    def test_unclosed(self):self.assertEqual(check([bar(0,79800),bar(1,80100)],now=8)["status"],"WAITING")
    def test_stop_invalidation(self):self.assertEqual(check([bar(0,78900)])["status"],"INVALIDATED")
    def test_old_bar(self):self.assertEqual(check([bar(-1,79800),bar(0,80100)])["status"],"EXPIRED")
if __name__=="__main__":unittest.main()
