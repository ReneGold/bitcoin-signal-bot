"""Send new BTC V4 research shadow signals to Telegram, never orders.
Durable test-branch delivery log; report status distinguishes baseline and
asymmetric acceptance. Does not send stale signals at initial enablement.
"""
import csv,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"bitcoin_v4_forward_signals.csv"
SENT=ROOT/"bitcoin_v4_telegram_sent.csv"
FIELDS=["signal_open_utc","side","sent_at_utc"]

def read(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def new_signals(rows,seen,now):
    fresh=[]
    for r in rows:
        if r.get("side") not in ("LONG","SHORT") or r.get("baseline_accepted")!="1":continue
        key=(r["signal_open_utc"],r["side"])
        if key in seen:continue
        close=datetime.fromisoformat(r["signal_closed_utc"])
        if close.tzinfo is None or not timedelta(0)<=now-close<=timedelta(minutes=35):continue
        fresh.append(r);seen.add(key)
    return fresh

def message(r):
    def price(value):
        try:return f"{float(value):,.2f}"
        except (TypeError,ValueError):return "nicht vorhanden"
    side="KAUF / LONG" if r["side"]=="LONG" else "VERKAUF / SHORT"
    asym=r.get("asymmetric_accepted")=="1"
    return ("🟠 BITCOIN BTC/USD – NEUES V4-TESTSIGNAL\n"
            f"Richtung: {side}\n"
            f"Score: {r.get('score','?')}\n"
            "Strategie A (Basis): angenommen\n"
            f"Strategie B (Long/Short): {'angenommen' if asym else 'abgelehnt'}\n"
            f"Signalschluss (UTC): {r['signal_closed_utc']}\n"
            f"Referenzkurs: {price(r.get('entry_reference_usd'))} USD\n"
            f"Stop-Loss: {price(r.get('stop_usd'))} USD\n"
            "TP1 / TP2 / TP3: noch nicht im Signalprotokoll\n\n"
            "⚠️ Ausschließlich Demo-/Forschungssignal. Kein bestätigter Einstieg, "
            "keine Handelsfreigabe, keine automatische Order.")

def main():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:raise RuntimeError("Bitcoin V4 Telegram secrets missing")
    sent=read(SENT)
    already={(x["signal_open_utc"],x["side"]) for x in sent}
    pending=new_signals(read(SOURCE),already,datetime.now(timezone.utc))
    for r in pending:
        reply=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id":chat,"text":message(r)},timeout=20)
        reply.raise_for_status()
        if not reply.json().get("ok"):raise RuntimeError("Telegram API refused message")
        sent.append({"signal_open_utc":r["signal_open_utc"],
                     "side":r["side"],"sent_at_utc":datetime.now(timezone.utc).isoformat()})
        with SENT.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(sent)
    print(f"Bitcoin V4 Telegram: sent={len(pending)} cumulative={len(sent)}")
    if not pending:print("No new qualifying BTC test signal; no test notification sent.")
if __name__=="__main__":main()
