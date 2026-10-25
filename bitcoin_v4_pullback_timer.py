"""Experimental BTC 5m pullback -> recovery confirmation.
Only completed 5m bars after closed 15m signal. No orders.
Pullback defined as a candle CLOSE beyond signal price opposite direction
by at least 0.10*initial risk, then a later candle CLOSE back beyond
signal price in signal direction; both before expiry. Stop invalidates.
"""
from datetime import timedelta
from math import isfinite

def confirm_pullback(*,signal_close_utc,side,signal_price,stop,
                     bars5,now_utc,window_minutes=30,pullback_r=0.10):
    if side not in ("LONG","SHORT") or signal_close_utc.tzinfo is None or now_utc.tzinfo is None:
        return {"status":"INVALID"}
    direction=1 if side=="LONG" else -1
    risk=(signal_price-stop)*direction
    if not all(isfinite(x) for x in (signal_price,stop,pullback_r)) or risk<=0 or pullback_r<=0:
        return {"status":"INVALID"}
    deadline=signal_close_utc+timedelta(minutes=window_minutes)
    saw_pullback=False
    previous=None
    for b in sorted(bars5,key=lambda x:x.t):
        if b.t.tzinfo is None or not all(isfinite(v) for v in (b.o,b.h,b.l,b.c)):
            return {"status":"INVALID"}
        if not b.l<=min(b.o,b.c)<=max(b.o,b.c)<=b.h:
            return {"status":"INVALID"}
        close_time=b.t+timedelta(minutes=5)
        if b.t<signal_close_utc or close_time>now_utc or close_time>deadline:continue
        if (b.c-stop)*direction<=0:
            return {"status":"INVALIDATED","closed_at_utc":close_time.isoformat()}
        if not saw_pullback:
            if (b.c-signal_price)*direction<=-pullback_r*risk:
                saw_pullback=True
        elif (b.c-signal_price)*direction>0:
            return {"status":"CONFIRMED","closed_at_utc":close_time.isoformat(),
                    "confirmation_close":b.c}
    return {"status":"EXPIRED" if now_utc>=deadline else "WAITING"}
