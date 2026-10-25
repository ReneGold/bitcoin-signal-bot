"""BTC/USD research-only risk gate. No orders, no Telegram.
Assumes position quantity measured in BTC and account equity/PnL in USD.
If broker uses contracts, EUR account, or unknown fees, do not authorize.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class RiskPolicy:
    max_trade_risk_pct: float = 0.5
    max_daily_loss_pct: float = 2.0
    max_open_positions: int = 1
    min_reward_risk: float = 1.5

def check_trade(*, equity_usd, day_realized_pnl_usd, entry_usd, stop_usd,
                target_usd, quantity_btc, open_positions, trading_cost_usd,
                broker_units_confirmed=False, policy=RiskPolicy()):
    reasons=[]
    vals=(equity_usd,day_realized_pnl_usd,entry_usd,stop_usd,target_usd,
          quantity_btc,trading_cost_usd)
    if not all(isinstance(v,(int,float)) and isfinite(v) for v in vals):
        return {"approved":False,"reasons":["Missing or non-finite input"]}
    if not broker_units_confirmed:
        reasons.append("BTC contract units and USD account currency unverified")
    if equity_usd<=0 or entry_usd<=0 or stop_usd<=0 or target_usd<=0 or quantity_btc<=0:
        reasons.append("Equity, prices and BTC quantity must be positive")
    if trading_cost_usd<0:reasons.append("Trading costs cannot be negative")
    if (policy.max_trade_risk_pct<=0 or policy.max_daily_loss_pct<=0 or
        policy.max_open_positions<1 or policy.min_reward_risk<=0):
        reasons.append("Invalid risk policy")
    if not isinstance(open_positions,int) or open_positions<0 or open_positions>=policy.max_open_positions:
        reasons.append("Open position limit")
    direction=1 if target_usd>entry_usd else -1 if target_usd<entry_usd else 0
    stop_risk=(entry_usd-stop_usd)*direction
    reward=(target_usd-entry_usd)*direction
    if direction==0 or stop_risk<=0 or reward<=0:
        reasons.append("Invalid long/short stop or target")
    max_loss=(stop_risk*quantity_btc+trading_cost_usd) if stop_risk>0 else None
    net_reward=(reward*quantity_btc-trading_cost_usd) if reward>0 else None
    rr=(net_reward/max_loss if max_loss and max_loss>0 else None)
    if max_loss is not None and equity_usd>0 and max_loss>equity_usd*policy.max_trade_risk_pct/100:
        reasons.append("Per-trade loss limit exceeded")
    if equity_usd>0 and day_realized_pnl_usd<=-equity_usd*policy.max_daily_loss_pct/100:
        reasons.append("Daily realized loss limit reached")
    if rr is None or rr<policy.min_reward_risk:
        reasons.append("Net reward/risk below minimum")
    return {"approved":not reasons,"reasons":reasons,"estimated_loss_usd":max_loss,
            "estimated_net_reward_usd":net_reward,"net_reward_risk":rr,
            "warning":"Stops may slip; estimate does not guarantee maximum realized loss"}
