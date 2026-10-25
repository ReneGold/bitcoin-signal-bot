import unittest
from bitcoin_time_machine import Bar,replay,analyze

class BitcoinTimeMachineTests(unittest.TestCase):
    def setUp(self):
        self.bars=[Bar(70000+i,70100+i,69900+i,70020+i) for i in range(160)]
    def test_target(self):
        rows=[Bar(70000,70000,70000,70000),Bar(70000,70800,69900,70700)]
        self.assertEqual(replay(rows,0,1,200,target_r=2,horizon=1)[1],"TARGET")
    def test_stop_first_same_bar(self):
        rows=[Bar(70000,70000,70000,70000),Bar(70000,70800,69600,70000)]
        self.assertEqual(replay(rows,0,1,200,horizon=1)[1],"STOP")
    def test_short_target(self):
        rows=[Bar(70000,70000,70000,70000),Bar(70000,70100,69300,69400)]
        self.assertEqual(replay(rows,0,-1,200,horizon=1)[1],"TARGET")
    def test_no_future_lookahead(self):
        old=analyze(self.bars,100,1,400)
        edited=self.bars[:101]+[Bar(99999,100099,99899,100000) for _ in range(59)]
        self.assertEqual(old,analyze(edited,100,1,400))
    def test_complete_window_required(self):
        with self.assertRaises(ValueError):replay(self.bars,159,1,400)
    def test_not_enough_history(self):
        self.assertEqual(analyze(self.bars,4,1,400)["sample_size"],0)
    def test_invalid_side(self):
        with self.assertRaises(ValueError):analyze(self.bars,100,0,400)
    def test_costs_reduce_result(self):
        no_cost=replay([Bar(70000,70000,70000,70000),Bar(70000,70700,69900,70500)],0,1,200,horizon=1)[0]
        cost=replay([Bar(70000,70000,70000,70000),Bar(70000,70700,69900,70500)],0,1,200,horizon=1,cost_per_btc_usd=20)[0]
        self.assertLess(cost,no_cost)
    def test_invalid_candle(self):
        bad=[Bar(70000,70000,70000,70000),Bar(70000,69000,71000,70000)]
        with self.assertRaises(ValueError):replay(bad,0,1,200,horizon=1)
if __name__=="__main__":unittest.main()
