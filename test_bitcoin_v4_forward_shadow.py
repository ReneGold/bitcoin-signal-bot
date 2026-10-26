import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from bitcoin_v4_forward_shadow import observe
from bitcoin_signal_bot import Candle
T=datetime(2026,10,26,8,tzinfo=timezone.utc)
class ForwardShadowTests(unittest.TestCase):
    def test_insufficient_data_fails(self):
        with self.assertRaises(ValueError):observe([],[],T,set())
    def test_empty_signal_no_orders(self):
        bars=[Candle(T+timedelta(minutes=15*i),80000,80100,79900,80000) for i in range(110)]
        h=[Candle(T+timedelta(hours=i),80000,80100,79900,80000) for i in range(100)]
        with patch("bitcoin_v4_forward_shadow.bot.signal",return_value=None):
            result=observe(bars,h,bars[-1].t+timedelta(minutes=16),set())
        self.assertEqual(result,[])
if __name__=="__main__":unittest.main()
