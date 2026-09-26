from __future__ import annotations

import argparse
import importlib.util
import json
import random
import bisect
from pathlib import Path

import numpy as np
import pandas as pd

OUT=Path("artifacts/research/intrinsic_comprehensive_y4_y8_20260926")
BOARD=Path("artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_STANDARD_COORDINATE_BOARD_335.csv")
H3REF=OUT/"CURRENT_PRODUCTION_H3_REFERENCE.json"
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)
DISCOUNT=0.85
SHAPLEY_SEED=20260915
SHAPLEY_PERMUTATIONS=2048

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def build_history(dev,args):
    m=pd.read_csv(args.model_a_rows)
    qb=json.loads(Path(args.qb_results).read_text())
    raw=dev.prep_raw(pd.read_csv(args.raw_seasons))
    players=pd.read_csv(args.players)
    residual=pd.read_csv(args.residual_states)
    innovation=pd.read_csv(args.innovation_states)
    m=dev.add_qb_governed_path(m,qb)
    base=dev.build_forecast_base(m)
    base=dev.merge_lags(base,raw)
    base=dev.add_engineered_features(base,players)
    base=dev.merge_trajectory(base,residual,innovation)
    long=dev.build_long(base,raw)
    return long,raw

def build_current(board,raw):
    x=board.copy()
    x=x[x.position.isin(POSITIONS)].copy()
    if len(x)!=335: raise SystemExit(f"expected 335 current players, got {len(x)}")
    x["player_id"]=x["player_id"].astype(str)
    x["gsis_id"]=x["historical_gsis_id"].astype(str).replace({"nan":np.nan,"None":np.nan})
    x["y1"]=pd.to_numeric(x["standard_y1_points"],errors="coerce").fillna(0).clip(lower=0)
    x["y2"]=pd.to_numeric(x["y2_standard_expected_points"],errors="coerce").fillna(0).clip(lower=0)
    x["y3"]=pd.to_numeric(x["y3_standard_expected_points"],errors="coerce").fillna(0).clip(lower=0)
    x["age"]=pd.to_numeric(x["age"],errors="coerce")
    x["experience"]=pd.to_numeric(x["experience"],errors="coerce")
    x["scoring_multiplier"]=pd.to_numeric(x["player_specific_scoring_multiplier"],errors="coerce").fillna(1.0)

    prior=raw[raw.season==2025][["player_id","position","fantasy_target","fp_pct"]].copy()
    prior=prior.rename(columns={"player_id":"gsis_id","fantasy_target":"prior_points","fp_pct":"prior_pct"})
    prior["gsis_id"]=prior["gsis_id"].astype(str)
    x=x.merge(prior,on=["gsis_id","position"],how="left")
    x["log_prior_points"]=np.log1p(x["prior_points"].clip(lower=0))
    x["log_y1"]=np.log1p(x["y1"].clip(lower=0))
    x["y1_pct"]=x.groupby("position")["y1"].rank(pct=True,method="average")
    denom=x["y1"].abs().clip(lower=25.0)
    x["y2_ratio"]=(x.y2/x.y1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    x["y3_ratio"]=(x.y3/x.y1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    x["y2_delta"]=((x.y2-x.y1)/denom).clip(-3,3)
    x["y3_delta"]=((x.y3-x.y1)/denom).clip(-3,3)
    x["base_season"]=2026
    return x

def forecast_current(dev,long,current):
    x=current.copy()
    for h in HORIZONS:
        x[f"y{h}"]=0.0
        x[f"y{h}_p_active"]=np.nan
        for pos in POSITIONS:
            mask=x.position==pos
            ev=x.loc[mask].copy()
            tr=long[(long.horizon==h)&(long.position==pos)&(long.target_season<2026)].copy()
            pred,pa=dev.fit_predict(tr,ev,"forecast10","two_part_ridge","specialist")
            x.loc[mask,f"y{h}"]=pred
            x.loc[mask,f"y{h}_p_active"]=pa
    return x

POSIDX={p:i for i,p in enumerate(POSITIONS)}
def cap_rules():
    direct={"QB":12,"RB":24,"WR":36,"TE":12}; out=[]
    for mask in range(1,1<<4):
        cap=sum(direct[POSITIONS[i]] for i in range(4) if mask&(1<<i))
        if any(mask&(1<<POSIDX[p]) for p in ("RB","WR","TE")): cap+=12
        cap+=12
        out.append((tuple(i for i in range(4) if mask&(1<<i)),cap))
    return tuple(out)
CAPS=cap_rules()

class Basis:
    def __init__(self):
        self.count=[0]*4; self.by=[[] for _ in range(4)]
    def valid(self,c): return all(sum(c[i] for i in inds)<=cap for inds,cap in CAPS)
    def plan(self,pos):
        inc=POSIDX[pos]; a=self.count.copy(); a[inc]+=1
        if self.valid(a): return (None,None,None)
        best=None
        for o in range(4):
            if self.count[o]<=0: continue
            s=self.count.copy(); s[o]-=1; s[inc]+=1
            if self.valid(s):
                ow,oid=self.by[o][0]; z=(ow,oid,o)
                if best is None or z<best: best=z
        if best is None:return None
        ow,oid,o=best; return (o,ow,oid)
    def marginal(self,pos,w,plan):
        w=max(0,float(w))
        if w<=0 or plan is None:return 0,None
        if plan[0] is None:return w,plan
        o,ow,oid=plan
        if w<=ow+1e-12:return 0,None
        return w-ow,plan
    def add(self,pid,pos,w,plan):
        _,r=self.marginal(pos,w,plan); w=max(0,float(w)); inc=POSIDX[pos]
        if r is None:return
        if r[0] is None:
            bisect.insort(self.by[inc],(w,pid)); self.count[inc]+=1
        else:
            o,ow,oid=r; self.by[o].pop(0); self.count[o]-=1
            bisect.insort(self.by[inc],(w,pid)); self.count[inc]+=1

def shapley(rows,seed):
    ids=[x[0] for x in rows]; by={x[0]:(x[1],float(x[2])) for x in rows}
    sums={i:0.0 for i in ids}; rng=random.Random(seed)
    for _ in range(SHAPLEY_PERMUTATIONS):
        order=ids[:]; rng.shuffle(order); b=Basis()
        for pid in order:
            pos,w=by[pid]; plan=b.plan(pos); d,_=b.marginal(pos,w,plan)
            sums[pid]+=d; b.add(pid,pos,w,plan)
    return {pid:sums[pid]/SHAPLEY_PERMUTATIONS for pid in ids}

def add_shapley_values(x):
    phi={}
    for h in range(1,9):
        rows=[(str(r.player_id),str(r.position),float(getattr(r,f"y{h}"))*float(r.scoring_multiplier)) for r in x.itertuples()]
        phi[h]=shapley(rows,SHAPLEY_SEED+h-1)
        x[f"y{h}_shapley"]=x.player_id.map(phi[h]).fillna(0.0)
    for H in (1,3,4,5,6,7,8):
        vals={pid:sum((DISCOUNT**(h-1))*phi[h].get(pid,0.0) for h in range(1,H+1)) for pid in phi[1]}
        x[f"h{H}_value"]=x.player_id.map(vals).fillna(0.0)
        x[f"h{H}_rank"]=x[f"h{H}_value"].rank(method="min",ascending=False)
    return x

def attach_uncertainty(x,path):
    u=pd.read_csv(path)
    for h in HORIZONS:
        x[f"y{h}_q80"]=np.nan; x[f"y{h}_q90"]=np.nan
        x[f"y{h}_lo80"]=np.nan; x[f"y{h}_hi80"]=np.nan
        x[f"y{h}_lo90"]=np.nan; x[f"y{h}_hi90"]=np.nan
        for pos in POSITIONS:
            row=u[(u.position==pos)&(u.horizon==h)]
            if row.empty: continue
            q80=float(row.iloc[0].q80); q90=float(row.iloc[0].q90)
            mask=x.position==pos
            x.loc[mask,f"y{h}_q80"]=q80
            x.loc[mask,f"y{h}_q90"]=q90
            x.loc[mask,f"y{h}_lo80"]=(x.loc[mask,f"y{h}"]-q80).clip(lower=0)
            x.loc[mask,f"y{h}_hi80"]=x.loc[mask,f"y{h}"]+q80
            x.loc[mask,f"y{h}_lo90"]=(x.loc[mask,f"y{h}"]-q90).clip(lower=0)
            x.loc[mask,f"y{h}_hi90"]=x.loc[mask,f"y{h}"]+q90
    return x

def h3_reference(x):
    ref=json.loads(H3REF.read_text())
    vals={k:float(v) for k,v in ref["values"].items()}
    x["production_h3_value"]=x.player_id.map(vals)
    x["production_h3_rank"]=x.production_h3_value.rank(method="min",ascending=False)
    z=x.dropna(subset=["production_h3_value"])
    return {
        "artifact_id":ref["artifact_id"],"computed_at":ref["computed_at"],"matched_players":len(z),
        "spearman":float(z.h3_rank.corr(z.production_h3_rank,method="spearman")),
        "mean_absolute_rank_gap":float((z.h3_rank-z.production_h3_rank).abs().mean()),
        "mean_absolute_value_gap":float((z.h3_value-z.production_h3_value).abs().mean()),
    }

def distributions(x):
    rows=[]
    for H in (3,4,5,6,7,8):
        for pos in POSITIONS:
            g=x[x.position==pos]
            rows.append({
                "horizon":H,"position":pos,"n":len(g),
                "top25_share":float((g[f"h{H}_rank"]<=25).sum()/25),
                "top50_share":float((g[f"h{H}_rank"]<=50).sum()/50),
                "top100_share":float((g[f"h{H}_rank"]<=100).sum()/100),
                "median_value":float(g[f"h{H}_value"].median()),
                "p90_value":float(g[f"h{H}_value"].quantile(.9)),
            })
    return pd.DataFrame(rows)

def rank_movement(x):
    rows=[]
    for H in HORIZONS:
        d=x.h3_rank-x[f"h{H}_rank"]
        rows.append({
            "horizon":H,"h3_vs_h_rank_spearman":float(x.h3_rank.corr(x[f"h{H}_rank"],method="spearman")),
            "median_abs_move":float(d.abs().median()),"p90_abs_move":float(d.abs().quantile(.9)),
            "max_abs_move":float(d.abs().max()),"share_abs_ge_10":float((d.abs()>=10).mean()),
            "share_abs_ge_20":float((d.abs()>=20).mean()),
        })
    return pd.DataFrame(rows)

def age_effects(x):
    rows=[]
    for pos in POSITIONS:
        for band,g in x.groupby(["position","age_band"],dropna=False):
            if band[0]!=pos: continue
            rows.append({
                "position":pos,"age_band":str(band[1]),"n":len(g),"median_age":float(g.age.median()) if g.age.notna().any() else np.nan,
                "mean_h3_to_h5_rank_delta":float((g.h3_rank-g.h5_rank).mean()),
                "mean_h3_to_h8_rank_delta":float((g.h3_rank-g.h8_rank).mean()),
            })
    return pd.DataFrame(rows)

def representatives(x):
    d=x.copy()
    d["move5"]=d.h3_rank-d.h5_rank; d["move8"]=d.h3_rank-d.h8_rank
    ids=[]
    for col in ("move5","move8"):
        for asc in (False,True):
            for pid in d.sort_values(col,ascending=asc).player_id:
                if pid not in ids: ids.append(pid)
                if len(ids)>=12: break
            if len(ids)>=12: break
        if len(ids)>=12: break
    return d[d.player_id.isin(ids)][["player_id","player_name","position","age","h3_rank","h4_rank","h5_rank","h6_rank","h7_rank","h8_rank","move5","move8"]].sort_values("move8",ascending=False)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--development-module",default="scripts/run_intrinsic_comprehensive_development.py")
    ap.add_argument("--final-architecture",required=True)
    ap.add_argument("--uncertainty",required=True)
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--raw-seasons",required=True)
    ap.add_argument("--players",required=True)
    ap.add_argument("--residual-states",required=True)
    ap.add_argument("--innovation-states",required=True)
    args=ap.parse_args()

    final=json.loads(Path(args.final_architecture).read_text())
    eff=final["effective_architecture"]
    if eff!={"type":"fixed","candidate":"specialist|forecast10|two_part_ridge"}:
        raise SystemExit(f"unexpected final architecture: {eff}")
    dev=load_module("dev",args.development_module)
    long,raw=build_history(dev,args)
    current=build_current(pd.read_csv(BOARD),raw)
    current=forecast_current(dev,long,current)
    current=attach_uncertainty(current,args.uncertainty)
    current=add_shapley_values(current)
    prod=h3_reference(current)

    move=rank_movement(current); dist=distributions(current); age=age_effects(current); reps=representatives(current)
    keep=["player_id","current_player_id","historical_gsis_id","gsis_id","player_name","position","age","experience","age_band",
          "mapping_status","history_status","prior_points","prior_pct","scoring_multiplier","production_h3_value","production_h3_rank"]
    for h in range(1,9):
        keep += [f"y{h}",f"y{h}_shapley"]
        if h>=4: keep += [f"y{h}_p_active",f"y{h}_q80",f"y{h}_q90",f"y{h}_lo80",f"y{h}_hi80",f"y{h}_lo90",f"y{h}_hi90"]
    for H in (1,3,4,5,6,7,8): keep += [f"h{H}_value",f"h{H}_rank"]
    current[keep].to_csv(OUT/"CURRENT_FINAL_ARCHITECTURE_SHADOWS.csv",index=False)
    move.to_csv(OUT/"CURRENT_RANK_MOVEMENT.csv",index=False)
    dist.to_csv(OUT/"CURRENT_POSITION_DISTRIBUTIONS.csv",index=False)
    age.to_csv(OUT/"CURRENT_AGE_EFFECTS.csv",index=False)
    reps.to_csv(OUT/"CURRENT_REPRESENTATIVE_CROSSOVERS.csv",index=False)

    summary={
        "authority":"research_shadow_only_no_production_change",
        "historical_architecture_frozen_before_current_inspection":True,
        "effective_architecture":eff,
        "current_player_count":len(current),
        "current_prior_2025_coverage":int(current.prior_points.notna().sum()),
        "current_prior_2025_missing":int(current.prior_points.isna().sum()),
        "production_h3_comparison":prod,
        "rank_movement":move.to_dict("records"),
        "position_distributions":dist.to_dict("records"),
        "uncertainty_semantics":"annual standard-fantasy-point conformal residual bands; cumulative H4-H8 covariance not inferred",
        "discount":DISCOUNT,
        "shapley_permutations":SHAPLEY_PERMUTATIONS,
        "named_player_tuning":False,
    }
    (OUT/"CURRENT_SHADOW_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
