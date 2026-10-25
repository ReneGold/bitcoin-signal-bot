import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_entry_timer import Candle,assess_entry
T=datetime(2026,10,26,12,15,tzinfo=timezone.utc)
class HistoricalConfirmationTests(unittest.TestCase):
    def test_confirm_only_after_closed_candle(self):
        b=Candle(T,80000,80200,79900,80150)
        self.assertEqual(assess_entry(signal_close_utc=T,side="LONG",trigger=80100,invalid_level=79500,five_minute_bars=[b],now_utc=T+timedelta(minutes=4))["status"],"WAITING")
    def test_completed_five_minute_confirms(self):
        b=Candle(T,80000,80200,79900,80150)
        self.assertEqual(assess_entry(signal_close_utc=T,side="LONG",trigger=80100,invalid_level=79500,five_minute_bars=[b],now_utc=T+timedelta(minutes=5))["status"],"CONFIRMED")
if __name__=="__main__":unittest.main()
