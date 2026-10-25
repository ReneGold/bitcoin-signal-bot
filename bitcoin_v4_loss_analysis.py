"""Detailed diagnostic for score-60 ORIGINAL BTC backtest trades.
Reuses historical bars and backtest replay; no trade execution.
"""
import csv,statistics
from collections import defaultdict,Counter
from bitcoin_v4_score_backtest import load,replay,COST_PER_BTC_USD
import bitcoin_signal_bot as bot

def analyze():
    c=load("15min");h=load("1h");ef,es,atr=bot.indicators(c)
    trades=[t for t in replay(c,ef,es,atr,h,60) if t["allocation"]=="ORIGINAL"]
    lookup={x.t.isoformat():i for i,x in enumerate(c)}
    enriched=[]
    for t in trades:
        i=lookup[t["signal_time"]];j=lookup[t["entry_time"]];k=lookup[t["exit_time"]]
        side=1 if t["side"]=="LONG" else -1
        stopdist=(t["entry"]-t["stop"])*side
        a=atr[i]
        # Price excursion during the ACTUAL simulated trade lifetime, not before entry.
        favorable=max(((b.h-t["entry"])*side if side==1 else (t["entry"]-b.l)) for b in c[j:k+1])
        adverse=max(((t["entry"]-b.l) if side==1 else (b.h-t["entry"])) for b in c[j:k+1])
        result={**t,"outcome":"WIN" if t["net_R"]>0 else "LOSS_OR_FLAT",
             "entry_stop_usd":round(stopdist,4),
             "stop_atr":round(stopdist/a,3) if a else None,
             "duration_15m":k-j+1,
             "max_favorable_R":round(favorable/stopdist,3),
             "max_adverse_R":round(adverse/stopdist,3),
             "entry_gap_vs_signal_usd":round((t["entry"]-c[i].c)*side,4),
             "hour_utc":c[i].t.hour,"weekday_utc":c[i].t.strftime("%A")}
        enriched.append(result)
    if not enriched:raise RuntimeError("No score-60 trades")
    with open("bitcoin_v4_loss_analysis_trades.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(enriched[0]));w.writeheader();w.writerows(enriched)
    print("BTC Score 60 original exits, USD/BTC assumed roundtrip cost:",COST_PER_BTC_USD)
    print("Trades:",len(enriched),"Winners:",sum(x["outcome"]=="WIN" for x in enriched),
          "Loss or flat:",sum(x["outcome"]!="WIN" for x in enriched))
    groups=defaultdict(list)
    for x in enriched:
        for group in (x["outcome"],x["side"],x["outcome"]+" "+x["side"]):
            groups[group].append(x)
    summary=[]
    for name,rows in sorted(groups.items()):
        record={"group":name,"trades":len(rows),"sum_R":round(sum(t["net_R"] for t in rows),3),
                "mean_R":round(statistics.mean(t["net_R"] for t in rows),3),
                "median_stop_atr":round(statistics.median(t["stop_atr"] for t in rows if t["stop_atr"] is not None),3),
                "median_duration_bars":statistics.median(t["duration_15m"] for t in rows),
                "median_max_favorable_R":round(statistics.median(t["max_favorable_R"] for t in rows),3),
                "median_max_adverse_R":round(statistics.median(t["max_adverse_R"] for t in rows),3)}
        summary.append(record);print(record)
    with open("bitcoin_v4_loss_analysis_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    print("Caution: intrabar extremes in same candle have unknown order; raw MFE/MAE are descriptive,")
    print("not evidence that alternate stop/entry filters would improve returns. No 5m/news/broker fill data.")
if __name__=="__main__":analyze()
