"""Research-only Bitcoin V4 5-minute entry confirmation; no orders/messages.
A signal is available only after its 15m candle has CLOSED. Confirmation uses
completed 5m candles after that time, and a close beyond trigger (not a wick).
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from math import isfinite

@dataclass(frozen=True)
class Candle:
    t:datetime  # UTC 5-minute candle OPEN time
    o:float
    h:float
    l:float
    c:float

def assess_entry(*,signal_close_utc,side,trigger,invalid_level,five_minute_bars,
                 now_utc,window_minutes=30):
    if side not in ("LONG","SHORT") or not isinstance(window_minutes,int) or window_minutes<=0 or window_minutes%5:
        return {"status":"INVALID","reason":"Invalid side or confirmation window"}
    if signal_close_utc.tzinfo is None or now_utc.tzinfo is None or now_utc<signal_close_utc:
        return {"status":"INVALID","reason":"Missing timezone or setup not closed"}
    if not all(isinstance(v,(int,float)) and isfinite(v) and v>0 for v in (trigger,invalid_level)):
        return {"status":"INVALID","reason":"Invalid price"}
    if (side=="LONG" and invalid_level>=trigger) or (side=="SHORT" and invalid_level<=trigger):
        return {"status":"INVALID","reason":"Invalid stop direction"}
    deadline=signal_close_utc+timedelta(minutes=window_minutes)
    for bar in sorted(five_minute_bars,key=lambda b:b.t):
        if bar.t.tzinfo is None:
            return {"status":"INVALID","reason":"Naive candle time"}
        if not all(isfinite(x) for x in (bar.o,bar.h,bar.l,bar.c)) or not(bar.l<=min(bar.o,bar.c)<=max(bar.o,bar.c)<=bar.h):
            return {"status":"INVALID","reason":"Invalid OHLC candle"}
        closed_at=bar.t+timedelta(minutes=5)
        if bar.t<signal_close_utc or closed_at>now_utc or closed_at>deadline:
            continue
        if (side=="LONG" and bar.c<=invalid_level) or (side=="SHORT" and bar.c>=invalid_level):
            return {"status":"INVALID","reason":"Setup invalidated","closed_at_utc":closed_at.isoformat()}
        if (side=="LONG" and bar.c>trigger) or (side=="SHORT" and bar.c<trigger):
            return {"status":"CONFIRMED","reason":"Closed 5-minute confirmation","closed_at_utc":closed_at.isoformat(),
                    "confirmation_close":bar.c}
    return {"status":"EXPIRED" if now_utc>=deadline else "WAITING",
            "reason":"Window expired" if now_utc>=deadline else "Waiting for completed candle"}
