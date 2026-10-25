"""Exploratory BTC 15m score 60/65/70 backtest, V3.9 rules.
No orders or Telegram. Uses next-bar OPEN entry, original trailing exit
logic, stop-first on any same-bar collision, assumed USD-per-BTC fees.
No 5m timer/news/true broker spread/slippage; NOT full V4.
"""
import contextlib,csv,io
from datetime import datetime,timedelta
from pathlib import Path
import bitcoin_signal_bot as bot
from bitcoin_exit_planner import ExitPlan,new_state,update

DATA=Path("bitcoin_v4_history")
COST_PER_BTC_USD=80.0 # illustrative combined roundtrip cost; must validate broker
WINDOW=1200
THRESHOLDS=(60,65,70)

def load(interval):
    path=DATA/("btc_usd_"+interval+".csv")
    with path.open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
    return [bot.Candle(datetime.fromisoformat(v["datetime_utc"]),*[float(v[k]) for k in ("open","high","low","close")]) for v in r]

def replay(c,ef,es,atr,h,score):
    bot.MIN_SCORE=score
    bot.OBSERVE_SCORE=min(score,60)
    trades=[];last_exit=-1
    # Disallow overlapping positions within each strategy.
    for i in range(max(85,len(c)-WINDOW),len(c)-1):
        if i<=last_exit:continue
        h_allowed=[v for v in h if v.t+timedelta(hours=1)<=c[i].t+timedelta(minutes=15)]
        if len(h_allowed)<55:continue
        # Trim higher time frame to what was closed by this signal candle.
        with contextlib.redirect_stdout(io.StringIO()):
            sig=bot.signal(c[:i+1],ef[:i+1],es[:i+1],atr[:i+1],h_allowed,i)
        if sig is None:continue
        direction=sig[0];start=i+1;entry=c[start].o;sl=sig[2]
        if (entry-sl)*direction<=0:continue
        for alloc in ("ORIGINAL","20_80"):
            plan=ExitPlan(entry,sl,direction,alloc)
            state=new_state()
            exit_index=None
            for j in range(start,len(c)):
                b=c[j]
                update(plan,state,open_price=b.o,high=b.h,low=b.l,close=b.c)
                if state["status"]=="CLOSED":
                    exit_index=j;break
            if exit_index is None:continue
            trades.append(dict(score=score,allocation=alloc,side="LONG" if direction==1 else "SHORT",
                signal_time=c[i].t.isoformat(),entry_time=c[start].t.isoformat(),
                exit_time=c[exit_index].t.isoformat(),entry=entry,stop=sl,
                net_R=round(state["gross_R"]-COST_PER_BTC_USD/plan.risk,5)))
            if alloc=="ORIGINAL":last_exit=exit_index
    return trades

def summarize(rows):
    values=[r["net_R"] for r in sorted(rows,key=lambda r:r["exit_time"])]
    gain=sum(x for x in values if x>0);loss=-sum(x for x in values if x<0)
    equity=peak=dd=0.
    for v in values:
        equity+=v;peak=max(peak,equity);dd=max(dd,peak-equity)
    return dict(trades=len(values),sum_R=round(sum(values),4),
        win_pct=round(100*sum(v>0 for v in values)/len(values),2) if values else 0,
        profit_factor=round(gain/loss,3) if loss else None,
        max_closed_drawdown_R=round(dd,4))

def run():
    c=load("15min");h=load("1h")
    if len(c)<1300 or len(h)<200:raise RuntimeError("Insufficient history")
    ef,es,atr=bot.indicators(c)
    results=[]
    for score in THRESHOLDS:
        group=replay(c,ef,es,atr,h,score)
        results.extend(group)
        print("Score",score,"signals simulated",sum(x["allocation"]=="ORIGINAL" for x in group))
    with open("bitcoin_v4_score_trades.csv","w",newline="",encoding="utf-8") as f:
        fields=["score","allocation","side","signal_time","entry_time","exit_time","entry","stop","net_R"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(results)
    summary=[]
    for score in THRESHOLDS:
        for alloc in ("ORIGINAL","20_80"):
            group=[r for r in results if r["score"]==score and r["allocation"]==alloc]
            record={"score":score,"allocation":alloc,**summarize(group)}
            summary.append(record);print(record,flush=True)
    with open("bitcoin_v4_score_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    print("LIMITATIONS: Exploratory trailing-1200-candle sample, no 5m confirmation, news, real broker costs, slippage or out-of-sample validation.")
    print("20/80 shares ORIGINAL entry cohort; exit durations can overlap subsequent candidate trades and are not a separate portfolio.")
if __name__=="__main__":run()
