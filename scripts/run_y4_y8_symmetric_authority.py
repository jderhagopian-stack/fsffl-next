from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

POLICIES=("baseline","hard_router","soft_stack","blanket_75_25")
AGE_VARIANTS=("base_linear","exposure_ablation","target_exposure_histgb","target_poly","target_poly_exposure")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)
SEED=20260927
REPS=2500


def stable_seed(*parts):
    raw="|".join(map(str,parts)).encode()
    return SEED+int(hashlib.sha256(raw).hexdigest()[:8],16)


def two_way_codes(g:pd.DataFrame):
    origin=pd.Categorical(g.base_season).codes
    player=pd.Categorical(g.player_id.astype(str)).codes
    return origin,player,int(origin.max()+1),int(player.max()+1)


def bootstrap_additive(g:pd.DataFrame, d:np.ndarray, *, seed_parts, reps=REPS):
    origin,player,no,np_=two_way_codes(g)
    rng=np.random.default_rng(stable_seed(*seed_parts))
    vals=np.empty(reps,float)
    for i in range(reps):
        w=rng.exponential(1,no)[origin]*rng.exponential(1,np_)[player]
        vals[i]=float(np.sum(w*d)/np.sum(w))
    lo,hi=np.quantile(vals,[.025,.975])
    return float(np.mean(d)),float(lo),float(hi)


def bootstrap_nonadditive(g:pd.DataFrame, fn, *, seed_parts, reps=REPS):
    origin,player,no,np_=two_way_codes(g)
    rng=np.random.default_rng(stable_seed(*seed_parts))
    vals=np.empty(reps,float)
    for i in range(reps):
        w=rng.exponential(1,no)[origin]*rng.exponential(1,np_)[player]
        vals[i]=float(fn(w))
    point=float(fn(np.ones(len(g),float)))
    lo,hi=np.quantile(vals,[.025,.975])
    return point,float(lo),float(hi)


def routing_wide(raw:pd.DataFrame):
    keys=["row_id","base_season","horizon","position","player_id","actual"]
    frames=[]
    for p in POLICIES:
        q=raw[raw.policy==p][keys+["pred","covered80","covered90"]].copy()
        q=q.rename(columns={
            "pred":f"{p}_pred","covered80":f"{p}_cov80","covered90":f"{p}_cov90"
        })
        frames.append(q)
    out=frames[0]
    for q in frames[1:]:
        out=out.merge(q,on=keys,how="inner",validate="one_to_one")
    expected=raw[keys].drop_duplicates().shape[0]
    if len(out)!=expected:
        raise RuntimeError(f"routing common-row mismatch {len(out)} != {expected}")
    return out


def routing_metric_rows(w:pd.DataFrame):
    rows=[]
    for (h,pos),g in w.groupby(["horizon","position"]):
        y=g.actual.to_numpy(float);cut=float(np.quantile(y,.90));tail=y>=cut
        for p in POLICIES:
            pred=g[f"{p}_pred"].to_numpy(float);e=pred-y
            rows.append({
                "horizon":int(h),"position":str(pos),"policy":p,"n":len(g),
                "outer_origin_count":int(g.base_season.nunique()),
                "rmse":float(np.sqrt(np.mean(e*e))),
                "mae":float(np.mean(np.abs(e))),
                "bias":float(np.mean(e)),
                "abs_bias":float(abs(np.mean(e))),
                "spearman":float(pd.Series(pred).corr(pd.Series(y),method="spearman")),
                "tail_rmse":float(np.sqrt(np.mean(e[tail]*e[tail]))),
                "coverage80":float(g[f"{p}_cov80"].mean()),
                "coverage90":float(g[f"{p}_cov90"].mean()),
                "coverage80_gap":float(abs(g[f"{p}_cov80"].mean()-.80)),
                "coverage90_gap":float(abs(g[f"{p}_cov90"].mean()-.90)),
            })
    return pd.DataFrame(rows)


def routing_pairwise(w:pd.DataFrame):
    rows=[]
    origins=[]
    for (h,pos),g in w.groupby(["horizon","position"]):
        g=g.reset_index(drop=True)
        y=g.actual.to_numpy(float)
        tail=y>=float(np.quantile(y,.90))
        for a,b in itertools.combinations(POLICIES,2):
            ea=g[f"{a}_pred"].to_numpy(float)-y
            eb=g[f"{b}_pred"].to_numpy(float)-y
            additive={
                "mae":np.abs(eb)-np.abs(ea),
                "mse":eb*eb-ea*ea,
            }
            for metric,d in additive.items():
                point,lo,hi=bootstrap_additive(g,d,seed_parts=("route",h,pos,a,b,metric))
                rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":metric,
                             "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})
            gt=g.loc[tail].reset_index(drop=True)
            yt=gt.actual.to_numpy(float)
            eat=gt[f"{a}_pred"].to_numpy(float)-yt
            ebt=gt[f"{b}_pred"].to_numpy(float)-yt
            point,lo,hi=bootstrap_additive(gt,ebt*ebt-eat*eat,seed_parts=("route",h,pos,a,b,"tail_mse"))
            rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":"tail_mse",
                         "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})
            for metric,nom in (("coverage80_gap",.80),("coverage90_gap",.90)):
                ca=g[f"{a}_cov80" if nom==.80 else f"{a}_cov90"].astype(float).to_numpy()
                cb=g[f"{b}_cov80" if nom==.80 else f"{b}_cov90"].astype(float).to_numpy()
                fn=lambda ww,ca=ca,cb=cb,nom=nom: abs(np.sum(ww*cb)/np.sum(ww)-nom)-abs(np.sum(ww*ca)/np.sum(ww)-nom)
                point,lo,hi=bootstrap_nonadditive(g,fn,seed_parts=("route",h,pos,a,b,metric))
                rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":metric,
                             "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})
            fn=lambda ww,ea=ea,eb=eb: abs(np.sum(ww*eb)/np.sum(ww))-abs(np.sum(ww*ea)/np.sum(ww))
            point,lo,hi=bootstrap_nonadditive(g,fn,seed_parts=("route",h,pos,a,b,"abs_bias"))
            rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":"abs_bias",
                         "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})

            for T,og in g.groupby("base_season"):
                yy=og.actual.to_numpy(float)
                cut=float(np.quantile(yy,.90));tm=yy>=cut
                pa=og[f"{a}_pred"].to_numpy(float);pb=og[f"{b}_pred"].to_numpy(float)
                eaa=pa-yy;ebb=pb-yy
                origins.append({
                    "horizon":int(h),"position":pos,"origin":int(T),"a":a,"b":b,
                    "mae_gain_a_over_b":float(np.mean(np.abs(ebb))-np.mean(np.abs(eaa))),
                    "mse_gain_a_over_b":float(np.mean(ebb*ebb)-np.mean(eaa*eaa)),
                    "tail_mse_gain_a_over_b":float(np.mean(ebb[tm]*ebb[tm])-np.mean(eaa[tm]*eaa[tm])),
                    "abs_bias_gain_a_over_b":float(abs(np.mean(ebb))-abs(np.mean(eaa))),
                    "spearman_gain_a_over_b":float(pd.Series(pa).corr(pd.Series(yy),method="spearman")-pd.Series(pb).corr(pd.Series(yy),method="spearman")),
                })
    return pd.DataFrame(rows),pd.DataFrame(origins)


def oriented(pair:pd.DataFrame,h,pos,a,b,metric):
    q=pair[(pair.horizon==h)&(pair.position==pos)&(pair.metric==metric)&
           (((pair.a==a)&(pair.b==b))|((pair.a==b)&(pair.b==a)))]
    if len(q)!=1:
        raise RuntimeError(f"pair missing {h} {pos} {a} {b} {metric}")
    r=q.iloc[0]
    if r.a==a:
        return float(r.gain_a_over_b),float(r.ci_low),float(r.ci_high)
    return -float(r.gain_a_over_b),-float(r.ci_high),-float(r.ci_low)


def route_authority_map(metrics:pd.DataFrame,pair:pd.DataFrame,origin:pd.DataFrame):
    primary=("mse","mae","tail_mse")
    rows=[]
    for h in HORIZONS:
        for pos in POSITIONS:
            dominated=set()
            evidence=[]
            for a,b in itertools.permutations(POLICIES,2):
                gains=[oriented(pair,h,pos,a,b,m) for m in primary]
                any_better=any(lo>0 for _g,lo,_hi in gains)
                any_worse=any(hi<0 for _g,_lo,hi in gains)
                if any_better and not any_worse:
                    dominated.add(b)
            supported=[p for p in POLICIES if p not in dominated]
            if not supported:
                supported=list(POLICIES)

            tradeoff=False
            for a,b in itertools.combinations(supported,2):
                signs=[]
                for m in primary:
                    _g,lo,hi=oriented(pair,h,pos,a,b,m)
                    if lo>0: signs.append(1)
                    elif hi<0: signs.append(-1)
                if 1 in signs and -1 in signs:
                    tradeoff=True

            central=metrics[(metrics.horizon==h)&(metrics.position==pos)].set_index("policy")
            origin_n=int(central.outer_origin_count.iloc[0])
            if h==8:
                classification="insufficient_outer_evidence_tradeoff" if tradeoff else "insufficient_outer_evidence_tie_or_direction"
                exact=False
            elif len(supported)==1:
                classification="best_supported_policy"
                exact=True
            elif tradeoff:
                classification="multi_objective_tradeoff"
                exact=False
            else:
                classification="practical_tie_or_uncertain"
                exact=False

            # compact evidence against baseline plus best central metrics
            winners={
                "rmse":str(central.rmse.idxmin()),
                "mae":str(central.mae.idxmin()),
                "tail_rmse":str(central.tail_rmse.idxmin()),
                "abs_bias":str(central.abs_bias.idxmin()),
                "spearman":str(central.spearman.idxmax()),
            }
            rows.append({
                "position":pos,"horizon":h,"outer_origin_count":origin_n,
                "best_supported_or_tied":"|".join(supported),
                "classification":classification,
                "exact_cardinal_policy_authority":bool(exact),
                "central_rmse_leader":winners["rmse"],
                "central_mae_leader":winners["mae"],
                "central_tail_leader":winners["tail_rmse"],
                "central_bias_leader":winners["abs_bias"],
                "central_rank_leader":winners["spearman"],
                "y8_evidence_ceiling":bool(h==8),
            })
    return pd.DataFrame(rows)


def age_metric_rows(raw:pd.DataFrame):
    rows=[]
    for (h,pos,var),g in raw.groupby(["horizon","position","variant"]):
        y=g.actual.to_numpy(float);p=g.pred.to_numpy(float);e=p-y
        active=y>0;tail=y>=float(np.quantile(y,.90))
        pa=g.p_active.to_numpy(float)
        cond=g.conditional_pred.to_numpy(float)
        ce=cond[active]-y[active]
        rows.append({
            "horizon":int(h),"position":pos,"variant":var,"n":len(g),
            "outer_origin_count":int(g.base_season.nunique()),
            "rmse":float(np.sqrt(np.mean(e*e))),"mae":float(np.mean(np.abs(e))),
            "bias":float(np.mean(e)),"tail_rmse":float(np.sqrt(np.mean(e[tail]*e[tail]))),
            "spearman":float(pd.Series(p).corr(pd.Series(y),method="spearman")),
            "survival_brier":float(np.mean((pa-active.astype(float))**2)),
            "survival_calibration_gap":float(abs(pa.mean()-active.mean())),
            "conditional_n":int(active.sum()),
            "conditional_rmse":float(np.sqrt(np.mean(ce*ce))),
            "conditional_mae":float(np.mean(np.abs(ce))),
            "conditional_bias":float(np.mean(ce)),
        })
    return pd.DataFrame(rows)


def age_pairwise(raw:pd.DataFrame):
    rows=[]
    for (h,pos),cell in raw.groupby(["horizon","position"]):
        keys=["base_season","horizon","position","player_id","actual"]
        wide=None
        for v in AGE_VARIANTS:
            q=cell[cell.variant==v][keys+["pred","p_active","conditional_pred"]].copy()
            q=q.rename(columns={"pred":f"{v}_pred","p_active":f"{v}_pactive","conditional_pred":f"{v}_cond"})
            wide=q if wide is None else wide.merge(q,on=keys,how="inner",validate="one_to_one")
        for a,b in itertools.combinations(AGE_VARIANTS,2):
            y=wide.actual.to_numpy(float);active=y>0
            ea=wide[f"{a}_pred"].to_numpy(float)-y;eb=wide[f"{b}_pred"].to_numpy(float)-y
            items={
                "mae":np.abs(eb)-np.abs(ea),
                "mse":eb*eb-ea*ea,
                "survival_brier":(wide[f"{b}_pactive"].to_numpy(float)-active.astype(float))**2-(wide[f"{a}_pactive"].to_numpy(float)-active.astype(float))**2,
            }
            for metric,d in items.items():
                point,lo,hi=bootstrap_additive(wide,d,seed_parts=("age",h,pos,a,b,metric))
                rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":metric,
                             "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})
            wa=wide.loc[active].reset_index(drop=True)
            yy=wa.actual.to_numpy(float)
            ca=wa[f"{a}_cond"].to_numpy(float)-yy;cb=wa[f"{b}_cond"].to_numpy(float)-yy
            for metric,d in (("conditional_mae",np.abs(cb)-np.abs(ca)),("conditional_mse",cb*cb-ca*ca)):
                point,lo,hi=bootstrap_additive(wa,d,seed_parts=("age",h,pos,a,b,metric))
                rows.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":metric,
                             "gain_a_over_b":point,"ci_low":lo,"ci_high":hi,"reps":REPS})
    return pd.DataFrame(rows)


def age_summary(age_metrics:pd.DataFrame,age_pair:pd.DataFrame):
    rows=[]
    comparisons=[
        ("target_poly","base_linear","target_age_nonlinearity"),
        ("target_poly_exposure","exposure_ablation","incremental_cumulative_exposure"),
        ("target_exposure_histgb","base_linear","nonlinear_age_exposure_histgb"),
    ]
    for pos in POSITIONS:
        for h in HORIZONS:
            for a,b,label in comparisons:
                rec={"position":pos,"horizon":h,"comparison":label,"a":a,"b":b}
                for metric in ("mse","mae","survival_brier","conditional_mse","conditional_mae"):
                    g,lo,hi=oriented(age_pair,h,pos,a,b,metric)
                    rec[metric+"_gain"]=g;rec[metric+"_ci_low"]=lo;rec[metric+"_ci_high"]=hi
                    rec[metric+"_supported_a_better"]=bool(lo>0)
                    rec[metric+"_supported_a_worse"]=bool(hi<0)
                rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--routing-predictions",type=Path,required=True)
    ap.add_argument("--age-predictions",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)

    route_raw=pd.read_csv(args.routing_predictions)
    age_raw=pd.read_csv(args.age_predictions)
    if len(route_raw)!=47760:
        raise RuntimeError(f"routing row count mismatch {len(route_raw)}")
    if len(age_raw)!=59700:
        raise RuntimeError(f"age row count mismatch {len(age_raw)}")

    wide=routing_wide(route_raw)
    route_metrics=routing_metric_rows(wide)
    route_pair,route_origin=routing_pairwise(wide)
    amap=route_authority_map(route_metrics,route_pair,route_origin)

    age_metrics=age_metric_rows(age_raw)
    age_pair=age_pairwise(age_raw)
    age_comp=age_summary(age_metrics,age_pair)

    route_metrics.to_csv(args.output_dir/"Y4_Y8_SYMMETRIC_POLICY_SUMMARY.csv",index=False)
    route_pair.to_csv(args.output_dir/"Y4_Y8_PAIRWISE_UNCERTAINTY.csv",index=False)
    route_origin.to_csv(args.output_dir/"Y4_Y8_ORIGIN_DIRECTION.csv",index=False)
    amap.to_csv(args.output_dir/"Y4_Y8_CELL_AUTHORITY_MAP.csv",index=False)
    age_metrics.to_csv(args.output_dir/"Y4_Y8_AGE_EXPOSURE_METRICS.csv",index=False)
    age_pair.to_csv(args.output_dir/"Y4_Y8_AGE_EXPOSURE_PAIRWISE.csv",index=False)
    age_comp.to_csv(args.output_dir/"Y4_Y8_AGE_EXPOSURE_COMPARISONS.csv",index=False)

    result={
        "study":"y4-y8-symmetric-long-horizon-authority",
        "authority":"research_only_no_production_change",
        "routing_common_player_origin_rows":int(len(wide)),
        "routing_policy_prediction_rows":int(len(route_raw)),
        "age_exposure_prediction_rows":int(len(age_raw)),
        "policy_set":list(POLICIES),
        "age_variant_set":list(AGE_VARIANTS),
        "cell_classification_counts":amap.classification.value_counts().to_dict(),
        "exact_policy_cells":amap.loc[amap.exact_cardinal_policy_authority,["position","horizon","best_supported_or_tied"]].to_dict("records"),
        "y8_exact_authority_cells":int(amap.loc[amap.horizon==8,"exact_cardinal_policy_authority"].sum()),
        "y8_outer_origins":sorted(int(x) for x in wide.loc[wide.horizon==8,"base_season"].unique()),
        "guards":{
            "production_h3_changed":False,
            "production_forecast_changed":False,
            "intrinsic_changed":False,
            "current_named_players_used":False,
            "models_refit":False,
            "new_family_added":False,
            "prior_soft_stack_privilege":False,
        },
    }
    (args.output_dir/"Y4_Y8_SYMMETRIC_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
