import unittest
from bitcoin_exit_planner import ExitPlan,new_state,update
class BitcoinExitPlannerTests(unittest.TestCase):
    def runbar(self,p,state,lo,hi,op=70000,cl=70000):
        return update(p,state,open_price=op,high=hi,low=lo,close=cl)
    def test_original_tp3(self):
        p=ExitPlan(70000,69000,1);s=self.runbar(p,new_state(),69500,72500)
        self.assertEqual(s["status"],"CLOSED");self.assertAlmostEqual(s["gross_R"],2.25)
    def test_original_tp2_protect(self):
        p=ExitPlan(70000,69000,1);s=self.runbar(p,new_state(),69500,71700)
        self.assertEqual(s["stage"],2)
        s=self.runbar(p,s,70700,71000,op=70900,cl=70900)
        self.assertEqual(s["status"],"CLOSED");self.assertAlmostEqual(s["gross_R"],.75)
    def test_original_tp1_protect(self):
        p=ExitPlan(70000,69000,1);s=self.runbar(p,new_state(),69500,70900)
        self.assertEqual(s["stage"],1)
        s=self.runbar(p,s,69900,70400)
        self.assertEqual(s["gross_R"],0)
    def test_20_80_first_target(self):
        p=ExitPlan(70000,69000,1,"20_80");s=self.runbar(p,new_state(),69500,70900)
        self.assertAlmostEqual(s["gross_R"],.15);self.assertAlmostEqual(s["remaining"],.8)
    def test_20_80_full_target(self):
        p=ExitPlan(70000,69000,1,"20_80");s=self.runbar(p,new_state(),69500,72300)
        self.assertEqual(s["status"],"CLOSED");self.assertAlmostEqual(s["gross_R"],1.95)
    def test_stop_first(self):
        p=ExitPlan(70000,69000,1,"20_80");s=self.runbar(p,new_state(),68500,73000)
        self.assertAlmostEqual(s["gross_R"],-1)
    def test_short(self):
        p=ExitPlan(70000,71000,-1,"20_80");s=self.runbar(p,new_state(),67700,70500)
        self.assertAlmostEqual(s["gross_R"],1.95)
    def test_gap_beyond_stop(self):
        p=ExitPlan(70000,69000,1);s=self.runbar(p,new_state(),67000,68200,op=68000,cl=68000)
        self.assertAlmostEqual(s["gross_R"],-2)
    def test_invalid_stop(self):
        with self.assertRaises(ValueError):ExitPlan(70000,71000,1)
    def test_invalid_ohlc(self):
        p=ExitPlan(70000,69000,1)
        with self.assertRaises(ValueError):self.runbar(p,new_state(),71000,69000)
if __name__=="__main__":unittest.main()
