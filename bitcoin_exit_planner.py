"""BTC/USD research-only exit simulations. No broker orders or Telegram.
Position units are fractions of an initial BTC quantity; R is initial USD/BTC
stop distance. Same-bar stop/target collisions are resolved STOP first.
Costs and slippage are NOT included; research comparisons must add them.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class ExitPlan:
    entry:float
    stop:float
    direction:int
    # 20/80 is experimental, NOT a recommendation based on Gold results.
    allocation:str="ORIGINAL"
    def __post_init__(self):
        if self.direction not in (-1,1) or self.allocation not in ("ORIGINAL","20_80"):
            raise ValueError("Invalid direction/allocation")
        if not all(isfinite(x) and x>0 for x in (self.entry,self.stop)):
            raise ValueError("Invalid entry/stop")
        if (self.entry-self.stop)*self.direction<=0:
            raise ValueError("Protective stop on incorrect side")
    @property
    def risk(self):return (self.entry-self.stop)*self.direction
    @property
    def tps(self):
        return (self.entry+self.direction*self.risk*.75,
                self.entry+self.direction*self.risk*1.5,
                self.entry+self.direction*self.risk*2.25)

def new_state():
    return dict(stage=0,remaining=1.0,gross_R=0.0,status="OPEN",events=[])

def update(plan,state,*,open_price,high,low,close):
    if state["status"]=="CLOSED":return state
    if not all(isfinite(x) and x>0 for x in (open_price,high,low,close)) or not low<=min(open_price,close)<=max(open_price,close)<=high:
        raise ValueError("Invalid candle")
    direction=plan.direction;stage=state["stage"]
    # ORIGINAL mirrors existing trailing-protection logic, with a single full TP3 exit.
    protection=(plan.stop,plan.entry,plan.tps[0])[min(stage,2)] if plan.allocation=="ORIGINAL" else (plan.stop if stage==0 else plan.entry)
    stop_hit=low<=protection if direction==1 else high>=protection
    gap=open_price<=protection if direction==1 else open_price>=protection
    if stop_hit:
        px=open_price if gap else protection
        state["gross_R"]+=state["remaining"]*(px-plan.entry)*direction/plan.risk
        state["remaining"]=0.0
        state["status"]="CLOSED"
        state["events"].append("GAP_STOP" if gap else "STOP")
        return state
    tp1,tp2,tp3=plan.tps
    hit1=high>=tp1 if direction==1 else low<=tp1
    hit2=high>=tp2 if direction==1 else low<=tp2
    hit3=high>=tp3 if direction==1 else low<=tp3
    if plan.allocation=="ORIGINAL":
        if hit3:
            state["gross_R"]+=state["remaining"]*2.25
            state["remaining"]=0.0
            state["status"]="CLOSED"
            state["events"].append("TP3_FULL")
        elif hit2:state["stage"]=2;state["events"].append("TP2_PROTECTION")
        elif hit1 and stage==0:state["stage"]=1;state["events"].append("TP1_PROTECTION")
    else:
        if hit1 and stage==0:
            state["gross_R"]+=.20*.75
            state["remaining"]=.80
            state["stage"]=1
            state["events"].append("TP1_20PCT")
        if hit3:
            state["gross_R"]+=state["remaining"]*2.25
            state["remaining"]=0.0
            state["status"]="CLOSED"
            state["events"].append("TP3_REST")
    return state
