import unittest
from bitcoin_risk_manager import check_trade

class BitcoinRiskTests(unittest.TestCase):
    def check(self,**updates):
        args=dict(equity_usd=5000,day_realized_pnl_usd=0,entry_usd=70000,
                  stop_usd=69500,target_usd=71000,quantity_btc=0.02,
                  open_positions=0,trading_cost_usd=2,
                  broker_units_confirmed=True)
        args.update(updates)
        return check_trade(**args)
    def test_allow_long(self):self.assertTrue(self.check()["approved"])
    def test_allow_short(self):self.assertTrue(self.check(stop_usd=70500,target_usd=69000)["approved"])
    def test_reject_large_position(self):self.assertFalse(self.check(quantity_btc=0.1)["approved"])
    def test_reject_daily_loss(self):self.assertFalse(self.check(day_realized_pnl_usd=-101)["approved"])
    def test_reject_open_position(self):self.assertFalse(self.check(open_positions=1)["approved"])
    def test_reject_bad_stop(self):self.assertFalse(self.check(stop_usd=70500)["approved"])
    def test_reject_low_reward(self):self.assertFalse(self.check(target_usd=70400)["approved"])
    def test_reject_unverified_contract(self):self.assertFalse(self.check(broker_units_confirmed=False)["approved"])
    def test_reject_high_costs(self):self.assertFalse(self.check(trading_cost_usd=24)["approved"])
    def test_reject_missing_costs(self):self.assertFalse(self.check(trading_cost_usd=float("nan"))["approved"])
if __name__=="__main__":unittest.main()
