"""BTC V4 paper-only exits for recorded shadow signals.
Incremental closed-15m processing, durable CSV. No real trades or messages.
Assumption: fill at next 15m open, stop-first same candle, zero spread/slippage;
cost fixed 80 USD per BTC. States do not imply broker execution.
"""
import csv,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from bitcoin_exit_planner import ExitPlan,new_state,update

SIGNALS=Path("bitcoin_v4_forward_signals.csv")
LEDGER=Path("bitcoin_v4_paper_trades.csv")
FIELDS=["signal_open_utc","variant","side","status","entry_utc","entry_usd",
        "stop_usd","last_bar_utc","state_json","exit_utc","net_R","reason"]
COST_USD_PER_BTC=80.0

def make_rows(signals,existing):
    records={(r["signal_open_utc"],r["variant"]):r for r in existing}
    for sig in signals:
        for variant,field in [("BASELINE","baseline_accepted"),("ASYMMETRIC","asymmetric_accepted")]:
            if sig[field]!="1":continue
            key=(sig["signal_open_utc"],variant)
            if key not in records:
                records[key]={k:"" for k in FIELDS}
                records[key].update(signal_open_utc=key[0],variant=variant,side=sig["side"],
                    status="PENDING",stop_usd=sig["stop_usd"],state_json=json.dumps(new_state()),
                    reason="AWAIT_NEXT_15M_OPEN")
    return records

def advance(rows,candles):
    # Only completed, sorted 15-minute bars passed by caller.
    bars=sorted(candles,key=lambda b:b.t)
    if not bars:return rows
    for rec in rows.values():
        if rec["status"] in ("CLOSED","INSUFFICIENT_HISTORY","INVALID"):continue
        signal_close=datetime.fromisoformat(rec["signal_open_utc"])+timedelta(minutes=15)
        if rec["status"]=="PENDING":
            possible=[b for b in bars if b.t>=signal_close]
            if not possible:continue
            if possible[0].t!=signal_close:
                rec["status"]="INSUFFICIENT_HISTORY";rec["reason"]="MISSING_ENTRY_BAR";continue
            entry=possible[0].o
            side=1 if rec["side"]=="LONG" else -1
            if (entry-float(rec["stop_usd"]))*side<=0:
                rec["status"]="INVALID";rec["reason"]="INVALID_RISK_ON_ENTRY";continue
            rec["entry_utc"]=possible[0].t.isoformat();rec["entry_usd"]=str(entry)
            rec["status"]="OPEN";rec["reason"]="PAPER_ONLY"
        plan=ExitPlan(float(rec["entry_usd"]),float(rec["stop_usd"]),1 if rec["side"]=="LONG" else -1)
        state=json.loads(rec["state_json"])
        beginning=datetime.fromisoformat(rec["entry_utc"])
        if rec["last_bar_utc"]:
            beginning=datetime.fromisoformat(rec["last_bar_utc"])+timedelta(minutes=15)
        todo=[b for b in bars if b.t>=beginning]
        expected=beginning
        for b in todo:
            if b.t!=expected:
                # Do not jump over unobserved bars or guess outcome.
                rec["reason"]="GAP_IN_15M_FEED";break
            update(plan,state,open_price=b.o,high=b.h,low=b.l,close=b.c)
            rec["last_bar_utc"]=b.t.isoformat()
            expected+=timedelta(minutes=15)
            if state["status"]=="CLOSED":
                rec["status"]="CLOSED";rec["exit_utc"]=(b.t+timedelta(minutes=15)).isoformat()
                rec["net_R"]=str(round(state["gross_R"]-COST_USD_PER_BTC/plan.risk,5))
                rec["reason"]=state["events"][-1];break
        rec["state_json"]=json.dumps(state,separators=(",",":"))
    return rows

def run():
    if not SIGNALS.exists():raise RuntimeError("Missing shadow signal ledger")
    with SIGNALS.open(newline="",encoding="utf-8") as f:signals=list(csv.DictReader(f))
    existing=[]
    if LEDGER.exists():
        with LEDGER.open(newline="",encoding="utf-8") as f:existing=list(csv.DictReader(f))
    from bitcoin_v4_forward_shadow import bot
    now=datetime.now(timezone.utc)
    bars=[b for b in bot.candles("15min",320)
          if b.t+timedelta(minutes=15,seconds=20)<=now]
    if len(bars)<100:raise RuntimeError("Not enough completed BTC candles")
    records=advance(make_rows(signals,existing),bars)
    with LEDGER.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        w.writerows(sorted(records.values(),key=lambda r:(r["signal_open_utc"],r["variant"])))
    for variant in ("BASELINE","ASYMMETRIC"):
        group=[r for r in records.values() if r["variant"]==variant]
        closed=[float(r["net_R"]) for r in group if r["status"]=="CLOSED"]
        print(f"BTC PAPER {variant}: records={len(group)}, closed={len(closed)}, "
              f"open={sum(r['status']=='OPEN' for r in group)}, "
              f"pending={sum(r['status']=='PENDING' for r in group)}, "
              f"sum_net_R={sum(closed):.4f}")
    print("Only simulated fills, no broker spreads/slippage, no order execution.")
if __name__=="__main__":run()
