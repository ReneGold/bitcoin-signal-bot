import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_news_volatility_filter import NewsEvent,assess
T=datetime(2026,10,26,12,30,tzinfo=timezone.utc)
class BitcoinNewsVolatilityTests(unittest.TestCase):
    def run_gate(self,**kwargs):
        p=dict(now_utc=T,events=[],calendar_verified=True,
               price_usd=80000,latest_closed_true_range=300,atr_15min=250)
        p.update(kwargs)
        return assess(**p)
    def test_normal(self):self.assertTrue(self.run_gate()["approved_for_research"])
    def test_unverified_calendar(self):self.assertFalse(self.run_gate(calendar_verified=False)["approved_for_research"])
    def test_before_us_news(self):
        x=self.run_gate(events=[NewsEvent(T+timedelta(minutes=30),"US CPI")])
        self.assertIn("HIGH_IMPACT_USD_EVENT",x["reasons"])
    def test_after_us_news(self):
        x=self.run_gate(events=[NewsEvent(T-timedelta(minutes=30),"US NFP")])
        self.assertFalse(x["approved_for_research"])
    def test_outside_window(self):
        x=self.run_gate(events=[NewsEvent(T+timedelta(minutes=31),"FOMC")])
        self.assertTrue(x["approved_for_research"])
    def test_low_impact_ignored(self):
        self.assertTrue(self.run_gate(events=[NewsEvent(T,"small release","LOW")])["approved_for_research"])
    def test_non_usd_ignored(self):
        self.assertTrue(self.run_gate(events=[NewsEvent(T,"EUR CPI","HIGH","EUR")])["approved_for_research"])
    def test_extreme_candle(self):
        self.assertIn("EXTREME_CANDLE_RANGE",self.run_gate(latest_closed_true_range=800)["reasons"])
    def test_low_volatility(self):
        self.assertIn("LOW_VOLATILITY",self.run_gate(atr_15min=50)["reasons"])
    def test_excessive_volatility(self):
        self.assertIn("EXCESSIVE_VOLATILITY",self.run_gate(atr_15min=1100)["reasons"])
    def test_naive_event_rejected(self):
        with self.assertRaises(ValueError):
            self.run_gate(events=[NewsEvent(T.replace(tzinfo=None),"bad")])
    def test_missing_atr_rejected(self):
        with self.assertRaises(ValueError):self.run_gate(atr_15min=0)
if __name__=="__main__":unittest.main()
