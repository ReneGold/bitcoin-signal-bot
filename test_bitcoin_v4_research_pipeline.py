import unittest
from datetime import datetime,timedelta,timezone
from bitcoin_v4_research_pipeline import evaluate
from bitcoin_time_machine import Bar
from bitcoin_entry_timer import Candle
from bitcoin_news_volatility_filter import NewsEvent
T=datetime(2026,10,26,12,15,tzinfo=timezone.utc)
class BitcoinV4IntegrationTests(unittest.TestCase):
    def params(self,**override):
        bars=[Bar(80000,80200,79800,80000) for _ in range(130)]
        c5=[Candle(T,80000,80250,79980,80200)]
        p=dict(side="LONG",score=65,entry_usd=80100,stop_usd=79700,
               signal_close_utc=T,now_utc=T+timedelta(minutes=5),
               bars15=bars,bars5=c5,atr15_usd=220,news_events=[],
               calendar_verified=True,equity_usd=5000,
               day_realized_pnl_usd=0,quantity_btc=0.02,trading_cost_usd=2,
               open_positions=0,broker_units_confirmed=True,allocation="ORIGINAL")
        p.update(override)
        return evaluate(**p)
    def test_integrated_candidate(self):
        r=self.params()
        self.assertEqual(r["status"],"RESEARCH_CANDIDATE")
        self.assertEqual(len(r["targets_usd"]),3)
    def test_20_80_candidate(self):
        self.assertEqual(self.params(allocation="20_80")["exit_allocation"],"20_80")
    def test_missing_calendar_fail_closed(self):
        self.assertEqual(self.params(calendar_verified=False)["status"],"NOT_READY")
    def test_unverified_broker_fail_closed(self):
        self.assertEqual(self.params(broker_units_confirmed=False)["status"],"NOT_READY")
    def test_risk_rejects_excess_size(self):
        self.assertEqual(self.params(quantity_btc=0.1)["stage"],"RISK")
    def test_news_blocks(self):
        self.assertEqual(self.params(news_events=[NewsEvent(T,"US CPI")])["stage"],"NEWS_VOL")
    def test_volatility_blocks(self):
        self.assertEqual(self.params(atr15_usd=20)["stage"],"NEWS_VOL")
    def test_entry_waits(self):
        self.assertEqual(self.params(bars5=[])["status"],"WAITING")
    def test_entry_expiry(self):
        self.assertEqual(self.params(bars5=[],now_utc=T+timedelta(minutes=31))["stage"],"ENTRY_TIMER")
    def test_score_rejects(self):
        self.assertEqual(self.params(score=60)["stage"],"SIGNAL")
if __name__=="__main__":unittest.main()
