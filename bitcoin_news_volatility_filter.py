"""BTC/USD research-only news and volatility gate. No orders or Telegram.
Bitcoin trades 24/7. High-impact USD events are optional contextual flags,
not complete coverage of BTC market-moving events. Missing calendar data must
never be interpreted as an all-clear. ATR uses CLOSED 15-minute candles.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

@dataclass(frozen=True)
class NewsEvent:
    timestamp_utc: datetime
    title: str
    impact: str = "HIGH"
    currency: str = "USD"

@dataclass(frozen=True)
class Policy:
    before_minutes: int = 30
    after_minutes: int = 30
    max_candle_range_atr: float = 2.5
    min_atr_percent: float = 0.10
    max_atr_percent: float = 1.25

def assess(*, now_utc, events, calendar_verified, price_usd,
           latest_closed_true_range, atr_15min, policy=Policy()):
    if now_utc.tzinfo is None:
        raise ValueError("UTC-aware time required")
    nums=(price_usd,latest_closed_true_range,atr_15min)
    if not all(isinstance(x,(int,float)) and isfinite(x) for x in nums):
        raise ValueError("Missing or invalid volatility data")
    if price_usd<=0 or latest_closed_true_range<0 or atr_15min<=0:
        raise ValueError("Non-positive price/ATR")
    if (policy.before_minutes<0 or policy.after_minutes<0 or
        policy.max_candle_range_atr<=0 or policy.min_atr_percent<=0 or
        policy.max_atr_percent<=policy.min_atr_percent):
        raise ValueError("Invalid policy")
    if not isinstance(calendar_verified,bool):
        raise ValueError("Calendar verification must be explicit")
    reasons=[]
    if not calendar_verified: reasons.append("CALENDAR_UNVERIFIED")
    nearby=[]
    for event in events:
        if event.timestamp_utc.tzinfo is None:
            raise ValueError("News event timestamp must include timezone")
        if event.impact.upper()!="HIGH" or event.currency.upper()!="USD":
            continue
        delta_minutes=(event.timestamp_utc-now_utc).total_seconds()/60
        if -policy.after_minutes<=delta_minutes<=policy.before_minutes:
            nearby.append(event.title)
    if nearby:reasons.append("HIGH_IMPACT_USD_EVENT")
    relative_range=latest_closed_true_range/atr_15min
    atr_percent=100*atr_15min/price_usd
    if relative_range>policy.max_candle_range_atr:
        reasons.append("EXTREME_CANDLE_RANGE")
    if atr_percent<policy.min_atr_percent:
        reasons.append("LOW_VOLATILITY")
    if atr_percent>policy.max_atr_percent:
        reasons.append("EXCESSIVE_VOLATILITY")
    return {"approved_for_research":not reasons,"reasons":reasons,
            "nearby_high_impact_events":nearby,
            "atr_percent":round(atr_percent,4),
            "closed_candle_range_to_atr":round(relative_range,4),
            "warning":"No broker authorization; verify BTC-specific events separately"}
