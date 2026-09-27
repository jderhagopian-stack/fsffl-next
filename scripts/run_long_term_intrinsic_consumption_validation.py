from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np, pandas as pd

from fsffl.state.models import LeagueRules
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)

POLICIES=("baseline","hard_router","soft_stack","blanket_75_25")
HORIZONS=(4,5,6,7)

def sh(g, weight_col, caps, *, scenarios=None, seed):
    players=[(str(r.player_id),str(r.position),max(0.0,float(getattr(r,weight_col)))) for r in g.itertuples()]
    if scenarios is None:
        scenarios={pid:(w,) for pid,_p,w in players}
    return monte_carlo_shapley_scenarios(
        players, scenarios, caps,
        permutations=FROZEN_SHAPLEY_PERMUTATIONS, seed=seed,
    )

def metrics(g,pred="lt_pred",actual="lt_actual"):
    e=g[pred].to_numpy(float)-g[actual].to_numpy(float)
    return {
        "n":int(len(g)),
        "mae":float(np.mean(np.abs(e))),
        "rmse":float(np.sqrt(np.mean(e*e))),
        "bias":float(np.mean(e)),
        "spearman":float(g[pred].corr(g[actual],method="spearman")),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rolling",type=Path,required=True)
    ap.add_argument("--authority-map",type=Path,required=True)
    ap.add_argument("--league-rules",type=Path,required=True)
    ap.add_argument("--current-shadow",type=Path,required=True)
    ap.add_argument("--current-intrinsic",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)

    raw=pd.read_csv(args.rolling)
    raw=raw[raw.horizon.isin(HORIZONS)].copy()
    rules=LeagueRules.model_validate(json.loads(args.league_rules.read_text()))
    caps=subset_caps_from_rules(rules)

    # Only origins with complete Y4-Y7 target windows can validate the four-year consumer.
    by_origin=raw[["base_season","horizon"]].drop_duplicates().groupby("base_season").horizon.nunique()
    complete=tuple(int(x) for x in by_origin[by_origin==4].index)
    work=raw[raw.base_season.isin(complete)].copy()

    rec=[]
    efficiency=[]
    for (origin,h),gg in work.groupby(["base_season","horizon"]):
        actual_g=gg[gg.policy=="baseline"].copy()
        actual=sh(actual_g,"actual",caps,seed=FROZEN_SHAPLEY_SEED+100+int(h))
        efficiency.append({"origin":int(origin),"horizon":int(h),"kind":"actual","residual":actual.efficiency_residual})
        for pol in POLICIES:
            g=gg[gg.policy==pol].copy()
            scenarios={}
            for r in g.itertuples():
                p=max(0.0,float(r.pred));q80=max(0.0,float(r.q80));q90=max(0.0,float(r.q90))
                scenarios[str(r.player_id)]=(p,max(0.0,p-q80),p+q80,max(0.0,p-q90),p+q90)
            pred=sh(g,"pred",caps,scenarios=scenarios,seed=FROZEN_SHAPLEY_SEED+int(h))
            efficiency.append({"origin":int(origin),"horizon":int(h),"kind":pol,"residual":pred.efficiency_residual})
            for r in g.itertuples():
                vals=pred.estimates[str(r.player_id)]
                rec.append({
                    "base_season":int(origin),"horizon":int(h),"position":str(r.position),
                    "player_id":str(r.player_id),"policy":pol,
                    "phi":float(vals[0]),"phi_lo80":float(vals[1]),"phi_hi80":float(vals[2]),
                    "phi_lo90":float(vals[3]),"phi_hi90":float(vals[4]),
                    "actual_phi":float(actual.estimates[str(r.player_id)][0]),
                    "pred_points":float(r.pred),"actual_points":float(r.actual),
                })
    annual=pd.DataFrame(rec)
    annual.to_csv(args.output_dir/"LONG_TERM_HISTORICAL_ANNUAL_SHAPLEY.csv",index=False)

    agg=annual.groupby(["base_season","player_id","position","policy"]).agg(
        lt_pred=("phi","mean"),lt_lo80=("phi_lo80","mean"),lt_hi80=("phi_hi80","mean"),
        lt_lo90=("phi_lo90","mean"),lt_hi90=("phi_hi90","mean"),
        lt_actual=("actual_phi","mean"),mean_pred_points=("pred_points","mean"),
        horizons=("horizon","nunique"),
    ).reset_index()
    agg=agg[agg.horizons==4].copy()

    summary=[]
    origin_rows=[]
    shortcut=[]
    annual_pivot=annual.pivot_table(
        index=["base_season","player_id","position","policy"],
        columns="horizon",values="phi",aggfunc="first"
    ).reset_index()
    for pol in POLICIES:
        g=agg[agg.policy==pol].copy()
        m=metrics(g);m.update({"scope":"pooled","origin":"ALL","policy":pol})
        m["coverage80"]=float(((g.lt_actual>=g.lt_lo80)&(g.lt_actual<=g.lt_hi80)).mean())
        m["coverage90"]=float(((g.lt_actual>=g.lt_lo90)&(g.lt_actual<=g.lt_hi90)).mean())
        summary.append(m)
        for origin,og in g.groupby("base_season"):
            mm=metrics(og);mm.update({"scope":"origin","origin":int(origin),"policy":pol})
            mm["coverage80"]=float(((og.lt_actual>=og.lt_lo80)&(og.lt_actual<=og.lt_hi80)).mean())
            mm["coverage90"]=float(((og.lt_actual>=og.lt_lo90)&(og.lt_actual<=og.lt_hi90)).mean())
            origin_rows.append(mm)
        w=g.merge(annual_pivot[annual_pivot.policy==pol],on=["base_season","player_id","position","policy"])
        for label,col in (("continuous_y4_y7","lt_pred"),("h5_only",5),("h7_only",7)):
            pred=w[col] if isinstance(col,int) else w[col]
            z=w.copy();z["candidate"]=pred
            mm=metrics(z,pred="candidate")
            shortcut.append({"policy":pol,"candidate":label,**mm})
        shortcut.append({
            "policy":pol,"candidate":"mean_raw_points_rank_only","n":int(len(g)),
            "mae":None,"rmse":None,"bias":None,
            "spearman":float(g.mean_pred_points.corr(g.lt_actual,method="spearman")),
        })
    pd.DataFrame(summary+origin_rows).to_csv(args.output_dir/"LONG_TERM_HISTORICAL_METRICS.csv",index=False)
    pd.DataFrame(shortcut).to_csv(args.output_dir/"LONG_TERM_SHORTCUT_COMPARISON.csv",index=False)

    # Preserve the symmetric set-valued Forecast authority exactly.
    amap=pd.read_csv(args.authority_map)
    amap=amap[amap.horizon.isin(HORIZONS)]
    support={(str(r.position),int(r.horizon)):str(r.best_supported_or_tied).split("|") for r in amap.itertuples()}
    wide=annual.pivot_table(
        index=["base_season","horizon","position","player_id","actual_phi"],
        columns="policy",
        values=["phi","phi_lo80","phi_hi80","phi_lo90","phi_hi90"],aggfunc="first"
    )
    wide.columns=[f"{a}__{b}" for a,b in wide.columns];wide=wide.reset_index()
    ar=[]
    for r in wide.itertuples(index=False):
        ss=support[(str(r.position),int(r.horizon))]
        cv=[getattr(r,f"phi__{p}") for p in ss]
        lo80=[getattr(r,f"phi_lo80__{p}") for p in ss]; hi80=[getattr(r,f"phi_hi80__{p}") for p in ss]
        lo90=[getattr(r,f"phi_lo90__{p}") for p in ss]; hi90=[getattr(r,f"phi_hi90__{p}") for p in ss]
        ar.append({
            "base_season":r.base_season,"horizon":r.horizon,"position":r.position,"player_id":r.player_id,
            "actual_phi":r.actual_phi,"policy_count":len(ss),
            "authority_low":min(cv),"authority_high":max(cv),
            "combined_lo80":min(lo80),"combined_hi80":max(hi80),
            "combined_lo90":min(lo90),"combined_hi90":max(hi90),
        })
    auth=pd.DataFrame(ar)
    authlt=auth.groupby(["base_season","player_id","position"]).agg(
        lt_actual=("actual_phi","mean"),authority_low=("authority_low","mean"),authority_high=("authority_high","mean"),
        combined_lo80=("combined_lo80","mean"),combined_hi80=("combined_hi80","mean"),
        combined_lo90=("combined_lo90","mean"),combined_hi90=("combined_hi90","mean"),
        horizons=("horizon","nunique"),
    ).reset_index()
    authlt=authlt[authlt.horizons==4].copy()
    authlt["display_midpoint"]=(authlt.authority_low+authlt.authority_high)/2
    authlt.to_csv(args.output_dir/"LONG_TERM_AUTHORITY_ENVELOPE_VALIDATION.csv",index=False)

    # Historical reference knots for a separate long-term display ruler.
    qs=(0,.05,.10,.25,.50,.75,.90,.95,.99,1.0)
    ref=authlt.lt_actual.to_numpy(float)
    scale=pd.DataFrame({"quantile":qs,"realized_long_term_raw_shapley":np.quantile(ref,qs)})
    scale.to_csv(args.output_dir/"LONG_TERM_HISTORICAL_SCALE_KNOTS.csv",index=False)

    # Current shadow comparison is impact-only; it is not used to choose the consumer.
    cur=pd.read_csv(args.current_shadow)
    cur["long_term_reference_raw"]=cur[[f"y{h}_shapley" for h in HORIZONS]].mean(axis=1)
    current_ref=json.loads(args.current_intrinsic.read_text())["values"]
    cur["current_intrinsic_raw"]=cur.player_id.map(current_ref).astype(float)
    cur["current_rank"]=cur.current_intrinsic_raw.rank(ascending=False,method="min")
    cur["long_term_rank"]=cur.long_term_reference_raw.rank(ascending=False,method="min")
    cur["rank_delta_current_to_long"]=cur.current_rank-cur.long_term_rank
    cur[[
        "player_id","position","age","experience","age_band","current_intrinsic_raw",
        "long_term_reference_raw","current_rank","long_term_rank","rank_delta_current_to_long"
    ]].to_csv(args.output_dir/"CURRENT_VS_LONG_TERM_REFERENCE.csv",index=False)

    pos=[]
    for p,g in cur.groupby("position"):
        pos.append({
            "group_type":"position","position":p,"age_band":"ALL","n":len(g),
            "median_current_raw":float(g.current_intrinsic_raw.median()),
            "median_long_term_raw":float(g.long_term_reference_raw.median()),
            "spearman":float(g.current_intrinsic_raw.corr(g.long_term_reference_raw,method="spearman")),
            "median_rank_delta":float(g.rank_delta_current_to_long.median()),
            "median_abs_rank_delta":float(g.rank_delta_current_to_long.abs().median()),
            "share_abs_rank_delta_ge20":float((g.rank_delta_current_to_long.abs()>=20).mean()),
        })
    for (p,ab),g in cur.groupby(["position","age_band"]):
        pos.append({
            "group_type":"position_age","position":p,"age_band":ab,"n":len(g),
            "median_current_raw":float(g.current_intrinsic_raw.median()),
            "median_long_term_raw":float(g.long_term_reference_raw.median()),
            "spearman":float(g.current_intrinsic_raw.corr(g.long_term_reference_raw,method="spearman")) if len(g)>=3 else None,
            "median_rank_delta":float(g.rank_delta_current_to_long.median()),
            "median_abs_rank_delta":float(g.rank_delta_current_to_long.abs().median()),
            "share_abs_rank_delta_ge20":float((g.rank_delta_current_to_long.abs()>=20).mean()),
        })
    pd.DataFrame(pos).to_csv(args.output_dir/"CURRENT_LONG_TERM_ARCHETYPE_COMPARISON.csv",index=False)

    result={
        "study":"long-term-intrinsic-consumption-contract",
        "authority":"research_only_no_production_change",
        "consumer":"mean annual horizon-specific Shapley marginal lineup capacity over Y4-Y7",
        "formula":"(phi4+phi5+phi6+phi7)/4",
        "complete_historical_origins":list(complete),
        "complete_historical_player_origin_rows":int(len(authlt)),
        "permutations":FROZEN_SHAPLEY_PERMUTATIONS,
        "historical_policy_metrics":summary,
        "authority_envelope":{
            "median_width":float((authlt.authority_high-authlt.authority_low).median()),
            "p90_width":float((authlt.authority_high-authlt.authority_low).quantile(.9)),
            "central_envelope_realized_target_coverage":float(((authlt.lt_actual>=authlt.authority_low)&(authlt.lt_actual<=authlt.authority_high)).mean()),
            "combined_80_realized_target_coverage":float(((authlt.lt_actual>=authlt.combined_lo80)&(authlt.lt_actual<=authlt.combined_hi80)).mean()),
            "combined_90_realized_target_coverage":float(((authlt.lt_actual>=authlt.combined_lo90)&(authlt.lt_actual<=authlt.combined_hi90)).mean()),
        },
        "current_reference":{
            "n":int(len(cur)),
            "spearman_current_vs_long_term":float(cur.current_intrinsic_raw.corr(cur.long_term_reference_raw,method="spearman")),
            "median_abs_rank_delta":float(cur.rank_delta_current_to_long.abs().median()),
            "p90_abs_rank_delta":float(cur.rank_delta_current_to_long.abs().quantile(.9)),
            "share_abs_rank_delta_ge20":float((cur.rank_delta_current_to_long.abs()>=20).mean()),
        },
        "shapley_efficiency_max_abs_residual":float(pd.DataFrame(efficiency).residual.abs().max()),
        "monotonic_scenario_violations":int(((annual.phi_lo80>annual.phi)|(annual.phi>annual.phi_hi80)|(annual.phi_lo90>annual.phi)|(annual.phi>annual.phi_hi90)).sum()),
        "limitations":{
            "full_y4_y7_complete_outer_origins":len(complete),
            "cross_horizon_covariance_validated":False,
            "current_shadow_is_single_prior_architecture_not_authority_envelope":True,
            "career_stage_historical_validation_recoverable_from_rolling_rows":False,
            "pristine_new_final_holdout":False,
        },
        "guards":{
            "forecast_family_search_run":False,"forecast_refit":False,"y8_included":False,
            "market_input_used":False,"team_utility_used":False,"production_changed":False,
        }
    }
    (args.output_dir/"LONG_TERM_INTRINSIC_VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
