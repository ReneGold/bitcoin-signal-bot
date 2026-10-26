"""BTC V4 experimental direction-specific filter with full sequential re-simulation.
Only completed candles used; historical in-sample, NOT independent validation.
No orders, Telegram, broker login, or modification of running V3.9 bot.
"""
import contextlib,csv,io,json
from datetime import timedelta
import bitcoin_signal_bot as bot
from bitcoin_v4_score_backtest import load,summarize,COST_PER_BTC_USD,WINDOW
from bitcoin_v4_market_phase_compare import classify
from bitcoin_exit_planner import ExitPlan,new_state,update

def permitted(side,context,variant):
    if variant=="BASELINE":return True
    if variant=="ASYMMETRIC":
        return side=="SHORT" or (side=="LONG" and context["strong_pass"])
    raise ValueError("unknown variant")

def backtest(c,h,variant):
    bot.MIN_SCORE=60;bot.OBSERVE_SCORE=60
    ef,es,atr=bot.indicators(c)
    rows=[];last_exit=-1;denied=0;signals=0
    for i in range(max(85,len(c)-WINDOW),len(c)-1):
        if i<=last_exit:continue
        closed_at=c[i].t+timedelta(minutes=15)
        available=[x for x in h if x.t+timedelta(hours=1)<=closed_at]
        if len(available)<55:continue
        with contextlib.redirect_stdout(io.StringIO()):
            candidate=bot.signal(c[:i+1],ef[:i+1],es[:i+1],atr[:i+1],available,i)
        if candidate is None:continue
        direction=candidate[0];side="LONG" if direction==1 else "SHORT"
        signals+=1
        ctx=classify(side=side,signal_open=c[i].t,closed_at=closed_at,
                     h=available,fast=ef[i],slow=es[i],atr=atr[i])
        if not permitted(side,ctx,variant):
            denied+=1;continue
        start=i+1;entry=c[start].o;stop=candidate[2]
        if (entry-stop)*direction<=0:continue
        plan=ExitPlan(entry,stop,direction,"ORIGINAL")
        state=new_state()
        for j in range(start,len(c)):
            bar=c[j]
            update(plan,state,open_price=bar.o,high=bar.h,low=bar.l,close=bar.c)
            if state["status"]=="CLOSED":
                rows.append({"variant":variant,"side":side,"signal_time":c[i].t.isoformat(),
                    "entry_time":c[start].t.isoformat(),"exit_time":c[j].t.isoformat(),
                    "net_R":round(state["gross_R"]-COST_PER_BTC_USD/plan.risk,5),
                    "strength":ctx["strength"],"trend":ctx["trend"]})
                last_exit=j;break
    return rows,{"signals_reviewed":signals,"filtered_out":denied}

def main():
    c=load("15min");h=load("1h")
    records=[];summaries=[]
    for variant in ("BASELINE","ASYMMETRIC"):
        rows,counts=backtest(c,h,variant);records.extend(rows)
        result={"variant":variant,**counts,**summarize(rows)}
        summaries.append(result);print(json.dumps(result),flush=True)
        for side in ("LONG","SHORT"):
            print(json.dumps({"variant":variant,"side":side,
                **summarize([x for x in rows if x["side"]==side])}),flush=True)
    with open("bitcoin_v4_asymmetric_trades.csv","w",newline="",encoding="utf-8") as f:
        fields=["variant","side","signal_time","entry_time","exit_time","net_R","strength","trend"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
    with open("bitcoin_v4_asymmetric_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    print("LIMITS: in-sample 1200 bars, original exit strategy only; no 5m/news/broker execution, illustrative costs; future out-of-sample test required.")
if __name__=="__main__":main()
