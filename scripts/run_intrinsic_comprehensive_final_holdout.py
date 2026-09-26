from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import bisect
from pathlib import Path

import numpy as np
import pandas as pd

OUT=Path("artifacts/research/intrinsic_comprehensive_y4_y8_20260926")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)
SEED=20260926
SHAPLEY_PERMUTATIONS=256

def load_module(path):
    spec=importlib.util.spec_from_file_location("dev",path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def build_inputs(dev,args):
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
    return base,long,raw

def parse_candidate(cand):
    arch,fs,model=cand.split("|")
    return arch,fs,model

def candidate_predict(dev,long,cand,T,h,pos,ev):
    arch,fs,model=parse_candidate(cand)
    if arch=="specialist":
        tr=long[(long.horizon==h)&(long.position==pos)&(long.target_season<T)]
    elif arch=="shared_horizon":
        tr=long[(long.horizon==h)&(long.target_season<T)]
    elif arch=="position_continuous":
        tr=long[(long.position==pos)&(long.target_season<T)]
    elif arch=="global_continuous":
        tr=long[long.target_season<T]
    else:
        raise KeyError(arch)
    return dev.fit_predict(tr,ev,fs,model,arch)

def arch_predict(dev,long,spec,T,h,pos,ev):
    typ=spec["type"]
    if typ=="fixed":
        return candidate_predict(dev,long,spec["candidate"],T,h,pos,ev)
    if typ=="specialist_route":
        cand=spec["route"][f"{pos}|Y{h}"]
        return candidate_predict(dev,long,cand,T,h,pos,ev)
    if typ=="hierarchical_blend":
        cand_route=spec["route"][f"{pos}|Y{h}"]
        p1,a1=candidate_predict(dev,long,cand_route,T,h,pos,ev)
        p2,a2=candidate_predict(dev,long,spec["shared_candidate"],T,h,pos,ev)
        w=float(spec["specialist_weight"])
        pred=w*p1+(1-w)*p2
        if np.isfinite(a1).any() and np.isfinite(a2).any():
            pa=w*np.nan_to_num(a1,nan=np.nanmean(a1))+(1-w)*np.nan_to_num(a2,nan=np.nanmean(a2))
        elif np.isfinite(a1).any(): pa=a1
        elif np.isfinite(a2).any(): pa=a2
        else: pa=np.full(len(ev),np.nan)
        return pred,pa
    raise KeyError(typ)

def predict_period(dev,long,spec,periods):
    rec=[]
    for h in HORIZONS:
        for T in periods[h]:
            evh=long[(long.horizon==h)&(long.base_season==T)]
            for pos in POSITIONS:
                ev=evh[evh.position==pos]
                if ev.empty: continue
                pred,pa=arch_predict(dev,long,spec,T,h,pos,ev)
                for i,r in enumerate(ev.itertuples()):
                    rec.append({
                        "row_id":r.row_id,"base_season":int(T),"horizon":h,"position":pos,
                        "player_id":r.player_id,"actual":float(r.actual),"pred":float(pred[i]),
                        "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan,
                    })
    return pd.DataFrame(rec)

def cell_metrics(dev,pred,label):
    rows=[]
    for (h,p),g in pred.groupby(["horizon","position"]):
        rows.append({"architecture":label,"horizon":int(h),"position":p,**dev.metric(g)})
    rows.append({"architecture":label,"horizon":"ALL","position":"ALL",**dev.metric(pred)})
    return pd.DataFrame(rows)

def uncertainty_from_calibration(cal):
    rows=[]
    for pos in POSITIONS:
        prev80=0.0; prev90=0.0
        for h in HORIZONS:
            g=cal[(cal.position==pos)&(cal.horizon==h)]
            if g.empty: continue
            e=np.abs(g.pred.to_numpy(float)-g.actual.to_numpy(float))
            q80=float(np.quantile(e,.80)); q90=float(np.quantile(e,.90))
            q80=max(prev80,q80); q90=max(prev90,q90,q80)
            prev80=q80; prev90=q90
            rows.append({"position":pos,"horizon":h,"calibration_n":len(g),"q80":q80,"q90":q90})
    return pd.DataFrame(rows)

def apply_uncertainty(pred,unc):
    z=pred.merge(unc,on=["position","horizon"],how="left")
    z["lo80"]=(z.pred-z.q80).clip(lower=0); z["hi80"]=z.pred+z.q80
    z["lo90"]=(z.pred-z.q90).clip(lower=0); z["hi90"]=z.pred+z.q90
    z["covered80"]=(z.actual>=z.lo80)&(z.actual<=z.hi80)
    z["covered90"]=(z.actual>=z.lo90)&(z.actual<=z.hi90)
    return z

def uncertainty_metrics(z,label):
    rows=[]
    for (h,p),g in z.groupby(["horizon","position"]):
        rows.append({"architecture":label,"horizon":h,"position":p,"n":len(g),
                     "coverage80":float(g.covered80.mean()),"coverage90":float(g.covered90.mean()),
                     "mean_width80":float((g.hi80-g.lo80).mean()),"mean_width90":float((g.hi90-g.lo90).mean())})
    rows.append({"architecture":label,"horizon":"ALL","position":"ALL","n":len(z),
                 "coverage80":float(z.covered80.mean()),"coverage90":float(z.covered90.mean()),
                 "mean_width80":float((z.hi80-z.lo80).mean()),"mean_width90":float((z.hi90-z.lo90).mean())})
    return pd.DataFrame(rows)

POSIDX={p:i for i,p in enumerate(POSITIONS)}
def caps():
    direct={"QB":12,"RB":24,"WR":36,"TE":12}; out=[]
    for mask in range(1,1<<4):
        cap=sum(direct[POSITIONS[i]] for i in range(4) if mask&(1<<i))
        if any(mask&(1<<POSIDX[p]) for p in ("RB","WR","TE")): cap+=12
        cap+=12
        out.append((tuple(i for i in range(4) if mask&(1<<i)),cap))
    return tuple(out)
CAPS=caps()

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
        if best is None: return None
        ow,oid,o=best; return (o,ow,oid)
    def marginal(self,pos,w,plan):
        w=max(0,float(w))
        if w<=0 or plan is None: return 0,None
        if plan[0] is None: return w,plan
        o,ow,oid=plan
        if w<=ow+1e-12: return 0,None
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
    ids=[x[0] for x in rows]; by={x[0]:(x[1],float(x[2])) for x in rows}; sums={i:0.0 for i in ids}
    rng=random.Random(seed)
    for _ in range(SHAPLEY_PERMUTATIONS):
        order=ids[:]; rng.shuffle(order); b=Basis()
        for pid in order:
            pos,w=by[pid]; pl=b.plan(pos); d,_=b.marginal(pos,w,pl); sums[pid]+=d; b.add(pid,pos,w,pl)
    return {i:sums[i]/SHAPLEY_PERMUTATIONS for i in ids}

def economic_bridge(pred,label):
    rows=[]
    for (T,h),g in pred.groupby(["base_season","horizon"]):
        pr=shapley([(str(r.player_id),str(r.position),float(r.pred)) for r in g.itertuples()],SEED+int(T)*20+int(h))
        ac=shapley([(str(r.player_id),str(r.position),float(r.actual)) for r in g.itertuples()],SEED+int(T)*20+100+int(h))
        z=pd.DataFrame({"player_id":list(pr),"pred":[pr[x] for x in pr],"actual":[ac.get(x,0.0) for x in pr]})
        e=z.pred-z.actual
        rows.append({"architecture":label,"base_season":T,"horizon":h,"n":len(z),
                     "shapley_mae":float(np.mean(np.abs(e))),"shapley_rmse":float(np.sqrt(np.mean(e*e))),
                     "shapley_spearman":float(z.pred.corr(z.actual,method="spearman"))})
    return pd.DataFrame(rows)

def confirmation(dev,selected,fallback,freeze):
    sm=dev.metric(selected); bm=dev.metric(fallback)
    rules=freeze["final_confirmation_rules"]
    ratios={"rmse":sm["rmse"]/bm["rmse"],"mae":sm["mae"]/bm["mae"],"tail_rmse":sm["tail_rmse"]/bm["tail_rmse"]}
    wins=[
        sm["rmse"]<bm["rmse"],sm["mae"]<bm["mae"],sm["tail_rmse"]<bm["tail_rmse"],sm["spearman"]>bm["spearman"]
    ]
    reasons=[]
    if ratios["rmse"]>rules["aggregate_rmse_max_ratio_vs_fallback"]: reasons.append("aggregate_rmse_regression")
    if ratios["tail_rmse"]>rules["aggregate_tail_rmse_max_ratio_vs_fallback"]: reasons.append("aggregate_tail_regression")
    if sum(wins)<2: reasons.append("insufficient_aggregate_metric_wins")
    for (h,p),g in selected.groupby(["horizon","position"]):
        b=fallback[(fallback.horizon==h)&(fallback.position==p)]
        if b.empty: continue
        a=dev.metric(g); bb=dev.metric(b)
        if a["rmse"]/bb["rmse"]>rules["cell_catastrophic_rmse_ratio"]:
            reasons.append(f"cell_rmse_{p}_Y{h}")
        if a["tail_rmse"]/bb["tail_rmse"]>rules["cell_catastrophic_tail_rmse_ratio"]:
            reasons.append(f"cell_tail_{p}_Y{h}")
    return len(reasons)==0,{"selected":sm,"fallback":bm,"ratios":ratios,"wins":sum(wins),"reasons":sorted(set(reasons))}

def missingness_diag(dev,long,spec,periods):
    # Diagnose selected feature-set availability without changing the frozen architecture.
    candidates=[]
    if spec["type"]=="fixed": candidates=[spec["candidate"]]
    elif spec["type"]=="specialist_route": candidates=list(spec["route"].values())
    else: candidates=list(spec["route"].values())+[spec["shared_candidate"]]
    fs=sorted(set(dev.parse_candidate(c)[1] if hasattr(dev,"parse_candidate") else c.split("|")[1] for c in candidates))
    feats=sorted(set(x for s in fs for x in dev.FEATURE_SETS[s] if x not in dev.CATEGORICAL))
    rows=[]
    for h in HORIZONS:
        z=long[(long.horizon==h)&(long.base_season.isin(periods[h]))]
        for p in POSITIONS:
            g=z[z.position==p]
            if g.empty: continue
            avail=[f for f in feats if f in g.columns]
            miss=float(g[avail].isna().mean().mean()) if avail else 0.0
            rows.append({"horizon":h,"position":p,"n":len(g),"selected_feature_sets":";".join(fs),"mean_numeric_missingness":miss})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--development-module",default="scripts/run_intrinsic_comprehensive_development.py")
    ap.add_argument("--freeze",required=True)
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--raw-seasons",required=True)
    ap.add_argument("--players",required=True)
    ap.add_argument("--residual-states",required=True)
    ap.add_argument("--innovation-states",required=True)
    args=ap.parse_args()
    dev=load_module(args.development_module)
    base,long,raw=build_inputs(dev,args)
    freeze=json.loads(Path(args.freeze).read_text())
    holds={int(h):tuple(v) for h,v in freeze["final_holdout_by_horizon"].items()}
    inner={int(h):tuple(v) for h,v in freeze["inner_validation_folds"].items()}
    if holds!=dev.final_holdouts(long):
        raise SystemExit("final holdout contract changed; refusing evaluation")

    selected_spec=freeze["selected_architecture"]
    fallback_spec=freeze["fallback_if_final_rejected"]

    # Calibration predictions are generated first from development folds; final outcomes remain untouched until after uncertainty is frozen.
    selected_cal=predict_period(dev,long,selected_spec,inner)
    fallback_cal=predict_period(dev,long,fallback_spec,inner)
    selected_unc=uncertainty_from_calibration(selected_cal)
    fallback_unc=uncertainty_from_calibration(fallback_cal)

    selected=predict_period(dev,long,selected_spec,holds)
    fallback=predict_period(dev,long,fallback_spec,holds)
    selected_u=apply_uncertainty(selected,selected_unc)
    fallback_u=apply_uncertainty(fallback,fallback_unc)

    same=selected_spec==fallback_spec
    if same:
        passed=True
        decision={"selected":dev.metric(selected),"fallback":dev.metric(fallback),"ratios":{"rmse":1.0,"mae":1.0,"tail_rmse":1.0},"wins":0,"reasons":[]}
        status="CONFIRMED_SIMPLER_BASELINE"
    else:
        passed,decision=confirmation(dev,selected,fallback,freeze)
        status="CONFIRMED_FROZEN_CANDIDATE" if passed else "FINAL_HOLDOUT_REJECTED_FALLBACK_PRESERVED"

    effective_spec=selected_spec if passed else fallback_spec
    effective=selected if passed else fallback
    effective_u=selected_u if passed else fallback_u
    effective_unc=selected_unc if passed else fallback_unc

    cell=pd.concat([cell_metrics(dev,selected,"selected"),cell_metrics(dev,fallback,"fallback")],ignore_index=True)
    um=pd.concat([uncertainty_metrics(selected_u,"selected"),uncertainty_metrics(fallback_u,"fallback")],ignore_index=True)
    eco=pd.concat([economic_bridge(selected,"selected"),economic_bridge(fallback,"fallback")],ignore_index=True)
    miss=missingness_diag(dev,long,effective_spec,holds)

    selected_u.assign(architecture="selected").to_csv(OUT/"FINAL_HOLDOUT_PREDICTIONS.csv",index=False)
    fallback_u.assign(architecture="fallback").to_csv(OUT/"FINAL_HOLDOUT_FALLBACK_PREDICTIONS.csv",index=False)
    cell.to_csv(OUT/"FINAL_HOLDOUT_CELL_METRICS.csv",index=False)
    um.to_csv(OUT/"FINAL_HOLDOUT_UNCERTAINTY.csv",index=False)
    eco.to_csv(OUT/"FINAL_HOLDOUT_ECONOMIC_BRIDGE.csv",index=False)
    miss.to_csv(OUT/"FINAL_HOLDOUT_MISSINGNESS.csv",index=False)
    effective_unc.to_csv(OUT/"EFFECTIVE_UNCERTAINTY_CONTRACT.csv",index=False)

    result={
        "state":"HISTORICAL_ARCHITECTURE_FINALIZED_BEFORE_CURRENT_PLAYER_INSPECTION",
        "authority":"research_only_no_production_change",
        "freeze_source":str(args.freeze),
        "holdout_status":status,
        "frozen_selected_architecture":selected_spec,
        "effective_architecture":effective_spec,
        "fallback":fallback_spec,
        "confirmation":decision,
        "untouched_final_holdout_by_horizon":{str(h):list(v) for h,v in holds.items()},
        "uncertainty":{
            "method":"development OOF absolute-residual conformal bands by position/horizon with monotone horizon floor",
            "effective_overall_coverage80":float(effective_u.covered80.mean()),
            "effective_overall_coverage90":float(effective_u.covered90.mean()),
        },
        "economic_bridge":{
            "method":"same lineup-capacity Shapley annual deployment game, 256 deterministic permutations",
            "selected_mean_shapley_mae":float(eco[eco.architecture=="selected"].shapley_mae.mean()),
            "fallback_mean_shapley_mae":float(eco[eco.architecture=="fallback"].shapley_mae.mean()),
            "selected_mean_shapley_spearman":float(eco[eco.architecture=="selected"].shapley_spearman.mean()),
            "fallback_mean_shapley_spearman":float(eco[eco.architecture=="fallback"].shapley_spearman.mean()),
        },
        "guards":{
            "current_players_inspected":False,
            "candidate_definitions_changed_after_holdout":False,
            "production_h3_changed":False,
            "market_owner_team_utility_inputs":False,
        }
    }
    (OUT/"FINAL_HOLDOUT_DECISION.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    lines=[
        "# Comprehensive Y4-Y8 Untouched Final Holdout",
        "",
        f"Status: **{status}**",
        "",
        "The architecture was frozen before this workflow scored the final holdout. No candidate definition or route was changed after final outcomes were exposed.",
        "",
        f"Effective architecture: {json.dumps(effective_spec,sort_keys=True)}",
        "",
        f"Overall 80% interval coverage: {result['uncertainty']['effective_overall_coverage80']:.3f}",
        f"Overall 90% interval coverage: {result['uncertainty']['effective_overall_coverage90']:.3f}",
        "",
        "Current named-player shadows remain prohibited until this result is persisted as the historical freeze."
    ]
    (OUT/"FINAL_HOLDOUT_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print((OUT/"FINAL_HOLDOUT_REPORT.md").read_text())
    print("FINAL_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("FINAL_JSON_END")

if __name__=="__main__":
    main()
