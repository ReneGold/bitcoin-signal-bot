"""Bitcoin V4 research-only integration. No orders, Telegram or broker access.
Caller supplies confirmed 15m setup, fully closed historical 15m candles,
confirmed UTC 5m candles, verified calendar and USD/BTC broker units.
RESEARCH_CANDIDATE never means authorization to execute a trade.
"""
from datetime import timedelta
from bitcoin_risk_manager import check_trade
from bitcoin_time_machine import analyze,Bar
from bitcoin_entry_timer import assess_entry
from bitcoin_exit_planner import ExitPlan,new_state
from bitcoin_news_volatility_filter import assess as assess_news

def evaluate(*, side, score, entry_usd, stop_usd, signal_close_utc, now_utc,
             bars15, bars5, atr15_usd, news_events, calendar_verified,
             equity_usd, day_realized_pnl_usd, quantity_btc, trading_cost_usd,
             open_positions, broker_units_confirmed, allocation="ORIGINAL"):
    if side not in ("LONG","SHORT") or not isinstance(score,(int,float)) or score<65:
        return {"status":"REJECTED","stage":"SIGNAL","reasons":["Ineligible research setup"]}
    if not bars15 or len(bars15)<5 or signal_close_utc.tzinfo is None or now_utc.tzinfo is None:
        return {"status":"NOT_READY","stage":"DATA","reasons":["Missing historical bars or UTC timing"]}
    if not calendar_verified or not broker_units_confirmed:
        return {"status":"NOT_READY","stage":"VERIFICATION","reasons":["Calendar or broker units unverified"]}
    # The most recent 15m bar is the setup bar and must already have closed.
    if now_utc<signal_close_utc:
        return {"status":"NOT_READY","stage":"DATA","reasons":["Setup candle still open"]}
    try:
        direction=1 if side=="LONG" else -1
        plan=ExitPlan(entry_usd,stop_usd,direction,allocation)
        rr_target=plan.tps[-1]
        risk=check_trade(equity_usd=equity_usd,day_realized_pnl_usd=day_realized_pnl_usd,
                         entry_usd=entry_usd,stop_usd=stop_usd,target_usd=rr_target,
                         quantity_btc=quantity_btc,trading_cost_usd=trading_cost_usd,
                         open_positions=open_positions,broker_units_confirmed=broker_units_confirmed)
        if not risk["approved"]:
            return {"status":"REJECTED","stage":"RISK","reasons":risk["reasons"]}
        last=bars15[-1]
        prev=bars15[-2]
        tr=max(last.high-last.low,abs(last.high-prev.close),abs(last.low-prev.close))
        news=assess_news(now_utc=now_utc,events=news_events,calendar_verified=calendar_verified,
                         price_usd=last.close,latest_closed_true_range=tr,atr_15min=atr15_usd)
        if not news["approved_for_research"]:
            return {"status":"REJECTED","stage":"NEWS_VOL","reasons":news["reasons"]}
        timer=assess_entry(signal_close_utc=signal_close_utc,side=side,
                           trigger=entry_usd,invalid_level=stop_usd,
                           five_minute_bars=bars5,now_utc=now_utc)
        if timer["status"]!="CONFIRMED":
            return {"status":"WAITING" if timer["status"]=="WAITING" else "REJECTED",
                    "stage":"ENTRY_TIMER","reasons":[timer["reason"]]}
        analogs=analyze(bars15,len(bars15)-1,direction,plan.risk,
                        cost_per_btc_usd=trading_cost_usd/quantity_btc)
        return {"status":"RESEARCH_CANDIDATE","stage":"PAPER_ONLY",
                "exit_allocation":allocation,"targets_usd":plan.tps,
                "paper_exit_state":new_state(),"risk":risk,"news":news,
                "entry_confirmation":timer,"historical_analogs":analogs,
                "warning":"Research only; no trading orders or Telegram"}
    except (TypeError,ValueError,IndexError,ZeroDivisionError) as exc:
        return {"status":"NOT_READY","stage":"INVALID_INPUT","reasons":[type(exc).__name__+": "+str(exc)]}
