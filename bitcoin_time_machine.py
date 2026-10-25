"""Bitcoin V4 historical analogy research, no orders or Telegram.
Outcomes use only completed historical windows before the evaluated signal.
Price distances and costs are USD per BTC (not USD account trade totals).
Historical examples may overlap and are NOT calibrated win probabilities.
"""
from dataclasses import dataclass
from math import isfinite
from statistics import median

@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float

def _check_bar(b):
    return (all(isfinite(v) and v>0 for v in (b.open,b.high,b.low,b.close))
            and b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high)

def features(bars,i):
    if i<3:return None
    b=bars[i];p=bars[i-1]
    scale=max(b.high-b.low,1e-8)
    return ((b.close-b.open)/scale,
            (b.close-p.close)/p.close,
            (b.high-b.low)/b.close)

def replay(bars,signal_i,side,stop_distance,target_r=2.0,horizon=12,
           cost_per_btc_usd=0.0):
    if side not in (-1,1) or stop_distance<=0 or target_r<=0 or horizon<1 or cost_per_btc_usd<0:
        raise ValueError("Invalid replay parameters")
    if signal_i<0 or signal_i+1+horizon>len(bars):
        raise ValueError("Complete subsequent closed candles required")
    entry=bars[signal_i+1].open
    stop=entry-side*stop_distance
    target=entry+side*stop_distance*target_r
    if stop<=0:raise ValueError("Stop below zero")
    for k in range(signal_i+1,signal_i+1+horizon):
        bar=bars[k]
        if not _check_bar(bar):raise ValueError("Invalid historical candle")
        stop_hit=bar.low<=stop if side==1 else bar.high>=stop
        target_hit=bar.high>=target if side==1 else bar.low<=target
        gap=bar.open<=stop if side==1 else bar.open>=stop
        if stop_hit:
            px=bar.open if gap else stop
            return round(((px-entry)*side-cost_per_btc_usd)/stop_distance,6),"STOP"
        if target_hit:
            return round((target_r*stop_distance-cost_per_btc_usd)/stop_distance,6),"TARGET"
    px=bars[signal_i+horizon].close
    return round(((px-entry)*side-cost_per_btc_usd)/stop_distance,6),"TIMEOUT"

def analyze(bars,signal_i,side,stop_distance,target_r=2.0,horizon=12,
            lookback=1200,max_examples=100,cost_per_btc_usd=0.0):
    if side not in (-1,1) or stop_distance<=0 or target_r<=0 or horizon<1 or lookback<1 or max_examples<1 or cost_per_btc_usd<0:
        raise ValueError("Invalid parameters")
    if signal_i<4 or signal_i>=len(bars):raise ValueError("Invalid signal index")
    if not all(_check_bar(b) for b in bars[:signal_i+1]):
        raise ValueError("Invalid OHLC history")
    target=features(bars,signal_i)
    # Every historical replay ends before current signal; avoid look-ahead.
    upper=signal_i-horizon
    candidates=[]
    for j in range(max(3,signal_i-lookback),upper):
        f=features(bars,j)
        if f[0]*target[0]<0:continue
        distance=abs(f[0]-target[0])+100*abs(f[1]-target[1])+100*abs(f[2]-target[2])
        candidates.append((distance,j))
    chosen=sorted(candidates)[:max_examples]
    if not chosen:
        return dict(sample_size=0,mean_net_r=None,median_net_r=None,
                    stop_count=0,target_count=0,timeout_count=0,
                    warning="Not enough completed historical comparison windows")
    results=[replay(bars,j,side,stop_distance,target_r,horizon,cost_per_btc_usd) for _,j in chosen]
    values=[x for x,_ in results]
    return dict(sample_size=len(values),mean_net_r=round(sum(values)/len(values),4),
                median_net_r=round(median(values),4),
                stop_count=sum(e=="STOP" for _,e in results),
                target_count=sum(e=="TARGET" for _,e in results),
                timeout_count=sum(e=="TIMEOUT" for _,e in results),
                warning="Historical analogs are exploratory, overlap, and are not calibrated odds")
