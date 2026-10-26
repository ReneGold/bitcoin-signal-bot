"""BTC score-60 1h trend and 15m market-strength diagnostic.
Same ORIGINAL baseline trade cohort, not an independent portfolio backtest.
No future candles, no orders, no Telegram; no tuning on this sample.
"""
import csv,json
from bisect import bisect_right
from datetime import timedelta,datetime
from pathlib import Path
import bitcoin_signal_bot as bot
from bitcoin_v4_score_backtest import load,replay,summarize

STRENGTH_THRESHOLD=0.5
def trend_context(h,closed_at):
    eligible=[b for b in h if b.t+timedelta(hours=1)<=closed_at]
    if len(eligible)<55:return None
    close=[x.c for x in eligible]
    fast=bot.ema(close,20)[-1];slow=bot.ema(close,50)[-1]
    if close[-1]>fast>slow:return "LONG"
    if close[-1]<fast<slow:return "SHORT"
    return "NEUTRAL"

def classify(*,side,signal_open,closed_at,h,fast,slow,atr):
    if closed_at<signal_open+timedelta(minutes=15):
        raise ValueError("Signal candle has not closed")
    if atr is None or atr<=0:return {"trend":"UNKNOWN","strength":None,"trend_pass":False,"strong_pass":False}
    trend=trend_context(h,closed_at)
    strength=abs(fast-slow)/atr
    return {"trend":trend or "UNKNOWN","strength":round(strength,6),
        "trend_pass":trend==side,
        "strong_pass":trend==side and strength>=STRENGTH_THRESHOLD}

def main():
    c=load("15min");h=load("1h")
    ef,es,atr=bot.indicators(c)
    base=[t for t in replay(c,ef,es,atr,h,60) if t["allocation"]=="ORIGINAL"]
    by_time={x.t.isoformat():i for i,x in enumerate(c)}
    records=[]
    for t in base:
        i=by_time[t["signal_time"]]
        b=c[i]
        context=classify(side=t["side"],signal_open=b.t,
            closed_at=b.t+timedelta(minutes=15),h=h,fast=ef[i],slow=es[i],atr=atr[i])
        records.append({**t,**context})
    if not records:raise RuntimeError("No baseline trades")
    variants={
        "BASELINE":records,
        "1H_TREND":[x for x in records if x["trend_pass"]],
        "1H_TREND_AND_STRENGTH":[x for x in records if x["strong_pass"]],
    }
    output=[]
    for name,rows in variants.items():
        result={"variant":name,**summarize(rows)}
        output.append(result);print(json.dumps(result),flush=True)
    for side in ("LONG","SHORT"):
        for name,rows in variants.items():
            selected=[x for x in rows if x["side"]==side]
            print(json.dumps({"side":side,"variant":name,**summarize(selected)}),flush=True)
    with open("bitcoin_v4_market_phase_trades.csv","w",newline="",encoding="utf-8") as f:
        keys=list(records[0]);w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
    with open("bitcoin_v4_market_phase_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    print("CAUTION: selected score60 baseline cohort; removing trades does NOT recalculate new entries after shorter exits. No 5m/news/real broker execution or independent validation.")
if __name__=="__main__":main()
