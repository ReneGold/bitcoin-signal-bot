"""Fetch and validate research-only BTC historical candles from Twelve Data.
No trading, Telegram, account state or live bot imports.
"""
import csv,json,os,requests
from datetime import datetime,timedelta,timezone
from pathlib import Path

INTERVALS={"15min":timedelta(minutes=15),"1h":timedelta(hours=1)}
ROOT=Path("bitcoin_v4_history")
def parse(payload,interval,now):
    if not isinstance(payload,dict) or payload.get("status")=="error":
        raise ValueError("Provider error: "+str(payload.get("message","invalid response")))
    values=payload.get("values")
    if not isinstance(values,list) or not values:
        raise ValueError("Empty or invalid BTC data")
    records=[]
    for item in values:
        t=datetime.fromisoformat(str(item["datetime"]).replace(" ","T"))
        if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
        else:t=t.astimezone(timezone.utc)
        o,h,l,c=[float(item[k]) for k in ("open","high","low","close")]
        if min(o,h,l,c)<=0 or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError("Invalid historical OHLC")
        if t+INTERVALS[interval]+timedelta(seconds=20)<=now:
            records.append((t,o,h,l,c))
    records.sort()
    if len({r[0] for r in records})!=len(records):raise ValueError("Duplicate historical candle")
    if len(records)<250:raise ValueError("Insufficient historical candles")
    return records

def fetch(interval,apikey,now=None,limit=5000):
    if interval not in INTERVALS or not apikey:raise ValueError("Invalid interval or missing key")
    now=now or datetime.now(timezone.utc)
    response=requests.get("https://api.twelvedata.com/time_series",
        params={"symbol":"BTC/USD","interval":interval,"outputsize":limit,"timezone":"UTC",
                "format":"JSON","apikey":apikey},timeout=40)
    response.raise_for_status()
    return parse(response.json(),interval,now)

def summarize(records,interval):
    expected=INTERVALS[interval]
    gaps=[(a[0].isoformat(),b[0].isoformat()) for a,b in zip(records,records[1:])
          if b[0]-a[0]!=expected]
    return {"bars":len(records),"first":records[0][0].isoformat(),
            "last":records[-1][0].isoformat(),"gaps":len(gaps),
            "gap_examples":gaps[:5]}

def main():
    apikey=os.getenv("TWELVE_DATA_API_KEY","")
    ROOT.mkdir(exist_ok=True)
    summaries={}
    for interval,limit in (("15min",5000),("1h",1600)):
        data=fetch(interval,apikey,limit=limit)
        fn=ROOT/("btc_usd_"+interval+".csv")
        with fn.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f);w.writerow(["datetime_utc","open","high","low","close"])
            for t,o,h,l,c in data:w.writerow([t.isoformat(),o,h,l,c])
        summaries[interval]=summarize(data,interval)
        print(interval,json.dumps(summaries[interval]))
    (ROOT/"coverage.json").write_text(json.dumps(summaries,indent=2),encoding="utf-8")
    print("Historical data acquisition only. No backtest profitability calculated.")
if __name__=="__main__":main()
