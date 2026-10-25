import csv,json
from bisect import bisect_left
from datetime import datetime,timedelta
from pathlib import Path
from bitcoin_v4_score_backtest import load,replay,summarize,COST_PER_BTC_USD
from bitcoin_entry_timer import Candle,assess_entry
from bitcoin_v4_pullback_timer import confirm_pullback
from bitcoin_exit_planner import ExitPlan,new_state,update
import bitcoin_signal_bot as bot

def compare_one(trade,method,c,c5,times):
    time=datetime.fromisoformat(trade["signal_time"]);close=time+timedelta(minutes=15)
    idx=bisect_left(times,time)
    five=[Candle(b.t,b.o,b.h,b.l,b.c) for b in c5 if close<=b.t<close+timedelta(minutes=30)]
    if len(five)!=6 or any(b.t!=close+timedelta(minutes=5*i) for i,b in enumerate(five)):
        return {"status":"MISSING_5M_COVERAGE"}
    if method=="BREAKOUT":
        dec=assess_entry(signal_close_utc=close,side=trade["side"],trigger=c[idx].c,
            invalid_level=trade["stop"],five_minute_bars=five,now_utc=close+timedelta(minutes=30))
    else:
        dec=confirm_pullback(signal_close_utc=close,side=trade["side"],signal_price=c[idx].c,
            stop=trade["stop"],bars5=five,now_utc=close+timedelta(minutes=30))
    if dec["status"]!="CONFIRMED":return {"status":dec["status"]}
    start=bisect_left(times,datetime.fromisoformat(dec["closed_at_utc"]))
    if start>=len(c):return {"status":"NO_EXIT_HISTORY"}
    direction=1 if trade["side"]=="LONG" else -1
    entry=c[start].o
    if (entry-trade["stop"])*direction<=0:return {"status":"INVALID_RISK"}
    plan=ExitPlan(entry,trade["stop"],direction);state=new_state()
    for j in range(start,len(c)):
        b=c[j];update(plan,state,open_price=b.o,high=b.h,low=b.l,close=b.c)
        if state["status"]=="CLOSED":
            return {"status":"CONFIRMED","entry_time":c[start].t.isoformat(),
                "exit_time":c[j].t.isoformat(),"net_R":round(state["gross_R"]-COST_PER_BTC_USD/plan.risk,5)}
    return {"status":"NO_EXIT_HISTORY"}

def main():
    c=load("15min");h=load("1h");c5=load("5min")
    ef,es,atr=bot.indicators(c)
    base=[x for x in replay(c,ef,es,atr,h,60) if x["allocation"]=="ORIGINAL"]
    times=[b.t for b in c];out=[];summary=[]
    for method in ("BREAKOUT","PULLBACK"):
        results=[];counts={}
        for trade in base:
            decision=compare_one(trade,method,c,c5,times)
            counts[decision["status"]]=counts.get(decision["status"],0)+1
            out.append({"method":method,"signal_time":trade["signal_time"],"baseline_R":trade["net_R"],**decision})
            if decision["status"]=="CONFIRMED":results.append(decision)
        matched={r["signal_time"] for r in out if r["method"]==method and r["status"]=="CONFIRMED"}
        report={"method":method,"status_counts":counts,"confirmed":summarize(results),
            "same_cohort_original":summarize([b for b in base if b["signal_time"] in matched])}
        print(json.dumps(report),flush=True);summary.append(report)
    with open("bitcoin_v4_pullback_trades.csv","w",newline="",encoding="utf-8") as f:
        keys=["method","signal_time","baseline_R","status","entry_time","exit_time","net_R"]
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(out)
    Path("bitcoin_v4_pullback_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print("LIMITATIONS: in-sample selected cohorts; exits can overlap; no real fills/news/out-of-sample validation.")
if __name__=="__main__":main()
