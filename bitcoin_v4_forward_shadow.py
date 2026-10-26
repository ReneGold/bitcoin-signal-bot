"""BTC V4 shadow forward entry ledger, research only; NEVER sends or trades.
Hourly job can be delayed; inspect latest 16 fully closed 15m candles.
Deduplicate by signal UTC opening timestamp and side in test-branch CSV.
Both strategies observe the SAME score-60 setup cohort.
No historical PnL claim; simulated exits are a separate future task.
"""
import contextlib,csv,io,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import bitcoin_signal_bot as bot
from bitcoin_v4_market_phase_compare import classify

LEDGER=Path("bitcoin_v4_forward_signals.csv")
FIELDS=["signal_open_utc","signal_closed_utc","side","score","entry_reference_usd",
        "stop_usd","baseline_accepted","asymmetric_accepted","trend_1h",
        "ema_spread_over_atr","mode"]

def observe(c,h,now,existing):
    if len(c)<100 or len(h)<60:raise ValueError("Missing sufficient BTC candle history")
    ef,es,atr=bot.indicators(c)
    bot.MIN_SCORE=60;bot.OBSERVE_SCORE=60
    fresh=[]
    for i in range(max(85,len(c)-16),len(c)):
        closed_at=c[i].t+timedelta(minutes=15)
        if closed_at>now or now-closed_at>timedelta(hours=5):continue
        eligible=[b for b in h if b.t+timedelta(hours=1)<=closed_at]
        if len(eligible)<55:continue
        with contextlib.redirect_stdout(io.StringIO()):
            sig=bot.signal(c[:i+1],ef[:i+1],es[:i+1],atr[:i+1],eligible,i)
        if not sig:continue
        side="LONG" if sig[0]==1 else "SHORT"
        key=(c[i].t.isoformat(),side)
        if key in existing:continue
        ctx=classify(side=side,signal_open=c[i].t,closed_at=closed_at,h=eligible,
            fast=ef[i],slow=es[i],atr=atr[i])
        fresh.append({
            "signal_open_utc":key[0],"signal_closed_utc":closed_at.isoformat(),
            "side":side,"score":sig[8],"entry_reference_usd":sig[1],
            "stop_usd":sig[2],"baseline_accepted":"1",
            "asymmetric_accepted":"1" if (side=="SHORT" or ctx["strong_pass"]) else "0",
            "trend_1h":ctx["trend"],"ema_spread_over_atr":ctx["strength"],
            "mode":"SHADOW_NO_ORDERS_NO_TELEGRAM"})
        existing.add(key)
    return fresh

def main():
    now=datetime.now(timezone.utc)
    old=[]
    if LEDGER.exists():
        with LEDGER.open(newline="",encoding="utf-8") as f:old=list(csv.DictReader(f))
    existing={(r["signal_open_utc"],r["side"]) for r in old}
    c=bot.candles("15min",320)
    h=bot.candles("1h",220)
    new=observe(c,h,now,existing)
    rows=sorted(old+new,key=lambda r:(r["signal_open_utc"],r["side"]))
    with LEDGER.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    print(f"BTC V4 SHADOW: {len(new)} new signals, {len(rows)} cumulative; "
          f"baseline={sum(r['baseline_accepted']=='1' for r in rows)}, "
          f"asymmetric={sum(r['asymmetric_accepted']=='1' for r in rows)}")
    print("Research only: no live broker/Telegram, no exits/PnL, no calendar clearance.")
    for r in new:print(r["signal_open_utc"],r["side"],"score",r["score"],
                       "asymmetric",r["asymmetric_accepted"])
if __name__=="__main__":main()
