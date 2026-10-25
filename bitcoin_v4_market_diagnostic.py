"""BTC V4 research-only real candle diagnostics via Twelve Data.
No trading signals, no orders, no Telegram; V3.9 main is untouched.
The risk/news/broker gates remain unverified (fail-closed). 
"""
import json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
from bitcoin_time_machine import Bar
from bitcoin_entry_timer import Candle
from bitcoin_v4_research_pipeline import evaluate

INTERVALS={"15min":timedelta(minutes=15),"5min":timedelta(minutes=5)}
OUTPUT=Path("bitcoin_v4_market_diagnostic.json")

def parse_bars(payload,interval,now):
    if not isinstance(payload,dict) or payload.get("status")=="error":
        raise ValueError("Provider error / malformed response")
    vals=payload.get("values")
    if not isinstance(vals,list):raise ValueError("Provider candle list missing")
    result=[]
    for x in vals:
        t=datetime.fromisoformat(str(x["datetime"]).replace(" ","T"))
        if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
        else:t=t.astimezone(timezone.utc)
        o,h,l,c=(float(x[k]) for k in ("open","high","low","close"))
        if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):
            raise ValueError("Invalid OHLC from provider")
        if t+INTERVALS[interval]+timedelta(seconds=20)<=now:
            result.append(Candle(t,o,h,l,c))
    result.sort(key=lambda x:x.t)
    if len({x.t for x in result})!=len(result):raise ValueError("Duplicate candle timestamps")
    return result

def fetch(interval,now,key,session=requests):
    if interval not in INTERVALS:raise ValueError("Invalid interval")
    if not key:raise ValueError("TWELVE_DATA_API_KEY missing")
    response=session.get("https://api.twelvedata.com/time_series",
        params={"symbol":"BTC/USD","interval":interval,"outputsize":300,
                "timezone":"UTC","format":"JSON","apikey":key},timeout=30)
    response.raise_for_status()
    bars=parse_bars(response.json(),interval,now)
    if len(bars)<100:raise ValueError("Too few completed BTC candles")
    return bars

def diagnose(c15,c5,now):
    if not c15 or not c5:raise ValueError("Empty real-market feeds")
    latest=c15[-1]
    bars15=[Bar(v.o,v.h,v.l,v.c) for v in c15]
    # Use only completed 5m candles AFTER the 15m signal close.
    signal_close=latest.t+timedelta(minutes=15)
    after=[v for v in c5 if v.t>=signal_close]
    # Diagnostic hypothetical trigger/stop, NOT a real V3.9 trading signal.
    result=evaluate(side="LONG",score=65,entry_usd=latest.c,
        stop_usd=latest.c*.995,signal_close_utc=signal_close,
        now_utc=now,bars15=bars15,bars5=after,
        atr15_usd=max(latest.h-latest.l,0.01),
        news_events=[],calendar_verified=False,
        equity_usd=5000,day_realized_pnl_usd=0,quantity_btc=.01,
        trading_cost_usd=0,open_positions=0,
        broker_units_confirmed=False)
    if result["status"]=="RESEARCH_CANDIDATE":
        raise RuntimeError("Unverified diagnostic must never approve")
    gaps15=sum(b.t-a.t!=INTERVALS["15min"] for a,b in zip(c15,c15[1:]))
    gaps5=sum(b.t-a.t!=INTERVALS["5min"] for a,b in zip(c5,c5[1:]))
    return {"symbol":"BTC/USD","mode":"DIAGNOSTIC_NO_SIGNALS_NO_ORDERS",
       "checked_utc":now.isoformat(),"15m_closed_bars":len(c15),"5m_closed_bars":len(c5),
       "15m_last_open_utc":latest.t.isoformat(),"5m_last_open_utc":c5[-1].t.isoformat(),
       "15m_gaps":gaps15,"5m_gaps":gaps5,
       "v4_safety_status":result["status"],"v4_safety_stage":result["stage"],
       "calendar_verified":False,"broker_units_verified":False}

def main():
    now=datetime.now(timezone.utc)
    key=os.getenv("TWELVE_DATA_API_KEY","")
    c15=fetch("15min",now,key)
    c5=fetch("5min",now,key)
    outcome=diagnose(c15,c5,now)
    OUTPUT.write_text(json.dumps(outcome,indent=2),encoding="utf-8")
    print(json.dumps(outcome,ensure_ascii=False))
if __name__=="__main__":main()
