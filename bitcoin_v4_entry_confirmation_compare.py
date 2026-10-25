"""BTC score-60 research comparison: previous entries vs completed 5m confirmation.
Only same entry cohorts; not full independent portfolio, no real broker fills.
Entry after confirmed 5m close uses NEXT 15m open (causal, conservative delay).
"""
import csv
from bisect import bisect_left
from datetime import datetime,timedelta
from pathlib import Path
from bitcoin_v4_score_backtest import load,replay,summarize,COST_PER_BTC_USD
from bitcoin_entry_timer import Candle,assess_entry
from bitcoin_exit_planner import ExitPlan,new_state,update
import bitcoin_signal_bot as bot

def compare(c,h,c5,score=60):
    ef,es,atr=bot.indicators(c)
    baseline=[x for x in replay(c,ef,es,atr,h,score) if x["allocation"]=="ORIGINAL"]
    times=[b.t for b in c]
    five=[Candle(b.t,b.o,b.h,b.l,b.c) for b in c5]
    checks=[];confirmed=[]
    for trade in baseline:
        signal_t=datetime.fromisoformat(trade["signal_time"])
        setup_close=signal_t+timedelta(minutes=15)
        direction=1 if trade["side"]=="LONG" else -1
        signal_index=bisect_left(times,signal_t)
        trigger=c[signal_index].c
        relevant=[b for b in five if setup_close<=b.t<setup_close+timedelta(minutes=30)]
        if not relevant or relevant[-1].t+timedelta(minutes=5)<setup_close+timedelta(minutes=30):
            checks.append({"signal_time":trade["signal_time"],"status":"MISSING_5M_COVERAGE","baseline_R":trade["net_R"]})
            continue
        decision=assess_entry(signal_close_utc=setup_close,side=trade["side"],
            trigger=trigger,invalid_level=trade["stop"],
            five_minute_bars=relevant,now_utc=setup_close+timedelta(minutes=30))
        item={"signal_time":trade["signal_time"],"status":decision["status"],"baseline_R":trade["net_R"]}
        if decision["status"]=="CONFIRMED":
            confirm_t=datetime.fromisoformat(decision["closed_at_utc"])
            # The 15m entry bar must start no earlier than the confirm CLOSE.
            start=bisect_left(times,confirm_t)
            if start>=len(c):
                item["status"]="INSUFFICIENT_EXIT_HISTORY"
            else:
                entry=c[start].o;stop=trade["stop"]
                if (entry-stop)*direction<=0:item["status"]="INVALID_RISK_AFTER_DELAY"
                else:
                    plan=ExitPlan(entry,stop,direction)
                    state=new_state()
                    for j in range(start,len(c)):
                        b=c[j];update(plan,state,open_price=b.o,high=b.h,low=b.l,close=b.c)
                        if state["status"]=="CLOSED":
                            item.update(entry_time=c[start].t.isoformat(),
                                net_R=round(state["gross_R"]-COST_PER_BTC_USD/plan.risk,5),
                                exit_time=c[j].t.isoformat())
                            confirmed.append(item)
                            break
                    if "net_R" not in item:item["status"]="INSUFFICIENT_EXIT_HISTORY"
        checks.append(item)
    return baseline,checks,confirmed

def main():
    c=load("15min");h=load("1h");c5=load("5min")
    if c5[0].t>c[max(85,len(c)-1200)].t:
        print("NOTICE: 5m coverage shorter than baseline historical interval; uncovered candidates excluded.")
    baseline,checks,confirmed=compare(c,h,c5)
    if not baseline:raise RuntimeError("No baseline trades to compare")
    with open("bitcoin_v4_entry_confirm_trades.csv","w",newline="",encoding="utf-8") as f:
        keys=["signal_time","status","baseline_R","entry_time","exit_time","net_R"]
        w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore");w.writeheader();w.writerows(checks)
    counts={x:sum(row["status"]==x for row in checks) for x in sorted({row["status"] for row in checks})}
    report={"baseline_all":summarize(baseline),
        "historically_covered":len(baseline)-counts.get("MISSING_5M_COVERAGE",0),
        "confirmed_completed":summarize(confirmed),
        "baseline_of_confirmed_cohort":summarize(
            [b for b in baseline if b["signal_time"] in {x["signal_time"] for x in confirmed}]),
        "status_counts":counts,
        "limitations":"Selected cohort only; confirmation delayed, 15m candle execution, assumed fees; no true fills, calendar or independent portfolio simulation"}
    import json
    Path("bitcoin_v4_entry_confirm_summary.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
