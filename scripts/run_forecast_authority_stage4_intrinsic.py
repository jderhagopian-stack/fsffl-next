from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fsffl.product.i1_player_scoring import translate_future_i1_result
from fsffl.product.p0_forecast_runtime import frozen_p0_standard_materialization
from fsffl.product.vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    _frozen_source_league_state,
    _frozen_source_year_one,
    build_future_state_probability_materialization,
    frozen_vnext_ratio_nodes,
    frozen_vnext_stage_d_state_means,
)
from fsffl.state.models import LeagueRules
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    STATE_NAMES,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)

STATES=tuple(STATE_NAMES)
POSITIVE=STATES[1:]
MODELS=("VNEXT_A2_BURR","D1","N1_histgb","N2_spline_two_part")
CUTS=(25,50,100,200)


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def current_test(source:pd.DataFrame,h:int)->pd.DataFrame:
    return pd.DataFrame({
        "source_season":2025,
        "player_id":source.current_player_id.astype(str),
        "position":source.position.astype(str),
        "horizon":int(h),
        "career_stage":source.career_stage.astype(str),
        "age":pd.to_numeric(source.age,errors="coerce"),
        "experience":pd.to_numeric(source.experience,errors="coerce").fillna(0).astype(int),
        "age_band":source.age_band.astype(str),
        "source_state":source.source_state.astype(str),
        "source_points":pd.to_numeric(source.y1_points,errors="coerce"),
        "source_percentile":pd.to_numeric(source.source_percentile,errors="coerce"),
        "state_percentile":pd.to_numeric(source.state_percentile,errors="coerce"),
        "prior1_points":pd.to_numeric(source.prior1_points,errors="coerce"),
        "prior1_coverage":pd.to_numeric(source.prior1_coverage,errors="coerce").fillna(0).astype(int),
        "prior_age_state_resid_z":pd.to_numeric(source.prior_age_state_resid_z,errors="coerce"),
        "prior2_mean_age_state_z":pd.to_numeric(source.prior2_mean_age_state_z,errors="coerce"),
        "prior2_gap_age_state_z":pd.to_numeric(source.prior2_gap_age_state_z,errors="coerce"),
        "prior2_coverage":pd.to_numeric(source.prior2_coverage,errors="coerce").fillna(0).astype(int),
        "source_role_band":source.source_role_band.fillna("unknown").astype(str),
        "games":pd.to_numeric(source.games,errors="coerce"),
        "opportunity_per_game":pd.to_numeric(source.opportunity_per_game,errors="coerce"),
    })


def build_future_packages(source:pd.DataFrame,rows:pd.DataFrame,fam):
    out={m:{} for m in MODELS}
    source_by={str(r.current_player_id):r for r in source.itertuples(index=False)}

    # Exact deployed vNext A2 probabilities + Stage-D means + frozen scoring multiplier.
    primitive=build_future_state_probability_materialization(
        league_state=_frozen_source_league_state(),
        standard_year_one=_frozen_source_year_one(),
    )
    if set(primitive.players)!=set(source.current_player_id.astype(str)):
        raise RuntimeError("current vNext source coverage mismatch")
    for pid,pf in primitive.players.items():
        src=source_by[pid]
        multiplier=float(src.league_y1_points)/float(src.y1_points)
        sleeper_external_id=pid.split(":")[-1]
        out["VNEXT_A2_BURR"][pid]={}
        for h in (2,3):
            probs={s:float(pf.probabilities_for(h)[s]) for s in STATES}
            base_means=frozen_vnext_stage_d_state_means(str(src.position),h,sleeper_external_id)
            means={"out":0.0,**{s:float(base_means[s])*multiplier for s in POSITIVE}}
            points=sum(probs[s]*means[s] for s in STATES)
            ratios=np.asarray(frozen_vnext_ratio_nodes(str(src.position),h),float)
            # Full deployed forecast variance includes within-state Burr/Gamma ratios.
            second=sum(
                probs[s]*float(np.mean((means[s]*ratios)**2))
                for s in POSITIVE
            )
            total_sd=math.sqrt(max(0.0,second-points*points))
            state_second=sum(probs[s]*means[s]*means[s] for s in STATES)
            state_sd=math.sqrt(max(0.0,state_second-points*points))
            within_var=max(0.0,total_sd*total_sd-state_sd*state_sd)
            out["VNEXT_A2_BURR"][pid][h]={
                "probs":probs,"means":means,"points":points,
                "forecast_state_sd":state_sd,
                "forecast_total_sd":total_sd,
                "forecast_within_state_sd_additive_variance_sqrt":math.sqrt(within_var),
                "within_state_uncertainty":"Burr XII M1" if str(src.position)=="QB" else "direct-Gamma M1",
            }

    # Exact D1/P0 current comparator; ancestor evidence is not used as vNext substitute.
    p0=frozen_p0_standard_materialization()
    if set(p0.players)!=set(source.current_player_id.astype(str)):
        raise RuntimeError("D1/P0 current source coverage mismatch")
    for pid,player in p0.players.items():
        src=source_by[pid]
        multiplier=float(src.league_y1_points)/float(src.y1_points)
        out["D1"][pid]={}
        for h in (2,3):
            r=translate_future_i1_result(player.result_for(h),multiplier=multiplier)
            probs={s:float(r.probabilities[s]) for s in STATES}
            means={s:float(r.state_means[s]) for s in STATES}
            points=float(r.anticipated_points)
            second=sum(probs[s]*means[s]*means[s] for s in STATES)
            state_sd=math.sqrt(max(0.0,second-points*points))
            out["D1"][pid][h]={
                "probs":probs,"means":means,"points":points,
                "forecast_state_sd":state_sd,"forecast_total_sd":state_sd,
                "forecast_within_state_sd_additive_variance_sqrt":None,
                "within_state_uncertainty":"not represented on this audited discrete-state comparator",
            }

    # Frozen N1/N2 family definitions; no hyperparameter search or current-board selection.
    for h in (2,3):
        st=fam.state_train_for(rows,2025,h)
        pt=fam.prod_train_for(rows,2025,h)
        test=current_test(source,h)
        if len(st)<500 or len(pt)<300:
            raise RuntimeError(f"insufficient frozen training support h={h}")
        for cls in (fam.N1,fam.N2):
            model=cls().fit(st,pt)
            probs,means=model.predict(test)
            for i,r in enumerate(test.itertuples(index=False)):
                pid=str(r.player_id);src=source_by[pid]
                multiplier=float(src.league_y1_points)/float(src.y1_points)
                pm={s:float(probs[i,j]) for j,s in enumerate(STATES)}
                mm={s:max(0.0,float(means[i,j])*multiplier) for j,s in enumerate(STATES)}
                points=sum(pm[s]*mm[s] for s in STATES)
                second=sum(pm[s]*mm[s]*mm[s] for s in STATES)
                state_sd=math.sqrt(max(0.0,second-points*points))
                out[model.name].setdefault(pid,{})[h]={
                    "probs":pm,"means":mm,"points":points,
                    "forecast_state_sd":state_sd,"forecast_total_sd":state_sd,
                    "forecast_within_state_sd_additive_variance_sqrt":None,
                    "within_state_uncertainty":"not represented on this audited discrete-state comparator",
                }
    return out


def shapley_model(source:pd.DataFrame,future:dict,rules:LeagueRules):
    caps=subset_caps_from_rules(rules)
    base=[(str(r.current_player_id),str(r.position),float(r.league_y1_points)) for r in source.itertuples(index=False)]
    res={}
    for h in (1,2,3):
        if h==1:
            players=base
            scenarios={pid:(pts,) for pid,_pos,pts in base}
        else:
            players=[];scenarios={}
            for r in source.itertuples(index=False):
                pid=str(r.current_player_id);f=future[pid][h]
                players.append((pid,str(r.position),float(f["points"])))
                scenarios[pid]=(float(f["points"]),*(float(f["means"][s]) for s in STATES))
        res[h]=monte_carlo_shapley_scenarios(
            players,scenarios,caps,
            permutations=FROZEN_SHAPLEY_PERMUTATIONS,
            seed=FROZEN_SHAPLEY_SEED+(h-1),
        )
    rows=[]
    for r in source.itertuples(index=False):
        pid=str(r.current_player_id)
        y1=float(res[1].estimates[pid][0])
        rec={
            "player_id":pid,"canonical_player_id":str(r.player_id),"player_name":str(r.player_name),
            "position":str(r.position),"age":float(r.age),"age_band":str(r.age_band),
            "career_stage":str(r.career_stage),"y1_points":float(r.league_y1_points),
            "y1_shapley":y1,
        }
        total=y1;state_sd_terms=[];mc_rss_terms=[];mc_upper_terms=[]
        for h,disc in ((2,FROZEN_INTRINSIC_DISCOUNT),(3,FROZEN_INTRINSIC_DISCOUNT**2)):
            f=future[pid][h]
            values=np.asarray(res[h].estimates[pid][1:],float)
            ses=np.asarray(res[h].standard_errors[pid][1:],float)
            probs=np.asarray([f["probs"][s] for s in STATES],float)
            expected=float(np.sum(probs*values))
            state_value_sd=math.sqrt(max(0.0,float(np.sum(probs*(values-expected)**2))))
            mc_rss=math.sqrt(float(np.sum((probs*ses)**2)))
            mc_upper=float(np.sum(probs*ses))
            rec[f"y{h}_anticipated_points"]=float(f["points"])
            rec[f"y{h}_persistence"]=1-float(f["probs"]["out"])
            rec[f"y{h}_expected_shapley"]=expected
            rec[f"y{h}_state_value_sd"]=state_value_sd
            rec[f"y{h}_forecast_state_sd_points"]=float(f["forecast_state_sd"])
            rec[f"y{h}_forecast_total_sd_points"]=float(f["forecast_total_sd"])
            extra=f["forecast_within_state_sd_additive_variance_sqrt"]
            rec[f"y{h}_forecast_within_state_sd_points"]=None if extra is None else float(extra)
            rec[f"y{h}_within_state_uncertainty"]=f["within_state_uncertainty"]
            rec[f"y{h}_mc_se_rss_proxy"]=mc_rss
            rec[f"y{h}_mc_se_upper_bound"]=mc_upper
            for s in STATES:
                rec[f"y{h}_p_{s}"]=float(f["probs"][s])
                rec[f"y{h}_mean_{s}"]=float(f["means"][s])
            total+=disc*expected
            state_sd_terms.append(disc*state_value_sd)
            mc_rss_terms.append(disc*mc_rss);mc_upper_terms.append(disc*mc_upper)
        a,b=state_sd_terms
        rec["intrinsic_raw"]=float(total)
        rec["state_value_sd_zero_cov_proxy"]=math.sqrt(a*a+b*b)
        rec["state_value_sd_covariance_lower"]=abs(a-b)
        rec["state_value_sd_perfect_positive_upper"]=a+b
        rec["mc_se_rss_proxy"]=math.sqrt(sum(x*x for x in mc_rss_terms))
        rec["mc_se_upper_bound"]=sum(mc_upper_terms)
        rec["cross_horizon_covariance_status"]="unvalidated_no_exact_total_intrinsic_sd"
        rec["within_state_value_uncertainty_status"]=(
            "forecast_uncertainty_preserved_but_not_consumed_by_current_value"
            if future[pid][2]["forecast_within_state_sd_additive_variance_sqrt"] is not None
            else "not_represented_by_candidate"
        )
        rows.append(rec)
    return pd.DataFrame(rows)


def rank_frame(df):
    z=df.copy()
    z["rank"]=z.intrinsic_raw.rank(method="min",ascending=False).astype(int)
    return z


def summarize_pairs(frames):
    rows=[];stats=[]
    for i,a in enumerate(MODELS):
        A=rank_frame(frames[a]).set_index("player_id")
        for b in MODELS[i+1:]:
            B=rank_frame(frames[b]).set_index("player_id")
            ids=sorted(set(A.index)&set(B.index))
            delta=[]
            for pid in ids:
                av=float(A.loc[pid,"intrinsic_raw"]);bv=float(B.loc[pid,"intrinsic_raw"])
                ar=int(A.loc[pid,"rank"]);br=int(B.loc[pid,"rank"])
                cross="|".join(str(c) for c in CUTS if (ar<=c)!=(br<=c))
                rows.append({
                    "a":a,"b":b,"player_id":pid,"player_name":A.loc[pid,"player_name"],
                    "position":A.loc[pid,"position"],"a_value":av,"b_value":bv,"a_minus_b":av-bv,
                    "a_rank":ar,"b_rank":br,"rank_delta_a_minus_b":ar-br,
                    "abs_rank_delta":abs(ar-br),"cutoff_crossings":cross,
                })
                delta.append(abs(ar-br))
            x=pd.DataFrame(rows)
            q=x[(x.a==a)&(x.b==b)]
            rho=float(pd.Series(q.a_value).corr(pd.Series(q.b_value),method="spearman"))
            stats.append({
                "a":a,"b":b,"n":len(q),"spearman":rho,
                "median_abs_rank_delta":float(np.median(q.abs_rank_delta)),
                "p90_abs_rank_delta":float(np.quantile(q.abs_rank_delta,.9)),
                "max_abs_rank_delta":int(q.abs_rank_delta.max()),
                "share_abs_rank_ge_10":float(np.mean(q.abs_rank_delta>=10)),
                "share_abs_rank_ge_20":float(np.mean(q.abs_rank_delta>=20)),
                **{f"cross_top_{c}":int(q.cutoff_crossings.str.contains(fr"(^|\|){c}(\||$)",regex=True).sum()) for c in CUTS},
                "median_abs_value_delta":float(np.median(np.abs(q.a_minus_b))),
                "p90_abs_value_delta":float(np.quantile(np.abs(q.a_minus_b),.9)),
                "max_abs_value_delta":float(np.max(np.abs(q.a_minus_b))),
            })
    return pd.DataFrame(rows),pd.DataFrame(stats)


def material_reversals(frames):
    ranked={m:rank_frame(frames[m]).set_index("player_id") for m in MODELS}
    ids=sorted(set.intersection(*(set(x.index) for x in ranked.values())))
    rows=[]
    for pid in ids:
        vals=np.asarray([float(ranked[m].loc[pid,"intrinsic_raw"]) for m in MODELS])
        ranks=np.asarray([int(ranked[m].loc[pid,"rank"]) for m in MODELS])
        median=float(np.median(vals));env=float(vals.max()-vals.min());rank_env=int(ranks.max()-ranks.min())
        crossings=[c for c in CUTS if len({int(rank<=c) for rank in ranks})>1]
        material=rank_env>=20 or bool(crossings) or (env>=25 and env>=.15*max(1e-12,median))
        base=ranked[MODELS[0]].loc[pid]
        rows.append({
            "player_id":pid,"canonical_player_id":base.canonical_player_id,"player_name":base.player_name,
            "position":base.position,"age":float(base.age),"age_band":base.age_band,"career_stage":base.career_stage,
            "min_rank":int(ranks.min()),"max_rank":int(ranks.max()),"rank_envelope":rank_env,
            "min_intrinsic":float(vals.min()),"max_intrinsic":float(vals.max()),"intrinsic_envelope":env,
            "median_intrinsic":median,"intrinsic_envelope_share_of_median":env/max(1e-12,median),
            "cutoff_crossings":"|".join(map(str,crossings)),"material_reversal":bool(material),
            **{f"{m}_rank":int(ranked[m].loc[pid,"rank"]) for m in MODELS},
            **{f"{m}_intrinsic":float(ranked[m].loc[pid,"intrinsic_raw"]) for m in MODELS},
        })
    return pd.DataFrame(rows)


def archetypes(player):
    rows=[]
    for (pos,stage,age_band),g in player.groupby(["position","career_stage","age_band"]):
        if len(g)<10:continue
        med_env=float(g.intrinsic_envelope.median())
        med_value=float(g.median_intrinsic.median())
        share=float(g.material_reversal.mean())
        material=share>=.20 or med_env>=.10*max(1e-12,med_value)
        rows.append({
            "position":pos,"career_stage":stage,"age_band":age_band,"n":len(g),
            "material_reversal_share":share,"median_intrinsic_envelope":med_env,
            "median_four_model_intrinsic":med_value,
            "median_envelope_share":med_env/max(1e-12,med_value),
            "material_archetype_reversal":bool(material),
        })
    return pd.DataFrame(rows)


def production_parity(frame,reference:dict):
    z=frame.set_index("canonical_player_id")
    ids=sorted(set(z.index)&set(reference))
    diffs=np.asarray([float(z.loc[x,"intrinsic_raw"])-float(reference[x]) for x in ids])
    return {
        "matched":len(ids),"reference_n":len(reference),"computed_n":len(z),
        "max_abs_delta":float(np.max(np.abs(diffs))) if len(diffs) else None,
        "mean_abs_delta":float(np.mean(np.abs(diffs))) if len(diffs) else None,
        "spearman":float(pd.Series([z.loc[x,"intrinsic_raw"] for x in ids]).corr(pd.Series([reference[x] for x in ids]),method="spearman")) if len(ids)>1 else None,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--rules",type=Path,required=True)
    ap.add_argument("--career-panel",type=Path,required=True)
    ap.add_argument("--redevelopment-code",type=Path,required=True)
    ap.add_argument("--family-code",type=Path,required=True)
    ap.add_argument("--production-reference",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)

    source=pd.read_csv(args.source)
    if len(source)!=335 or source.current_player_id.nunique()!=335:
        raise RuntimeError("governed current source must be exact 335-player coordinate")
    rules=LeagueRules.model_validate(json.loads(args.rules.read_text()))
    red=load_module(args.redevelopment_code,"stage4_red")
    fam=load_module(args.family_code,"stage4_family")
    panel=pd.read_csv(args.career_panel)
    rows=red.build_rows(panel,max_source_season=2023)
    futures=build_future_packages(source,rows,fam)

    frames={}
    for m in MODELS:
        frames[m]=shapley_model(source,futures[m],rules)
        frames[m]["model"]=m
    trajectory=pd.concat([frames[m] for m in MODELS],ignore_index=True)
    pairrows,pairstats=summarize_pairs(frames)
    players=material_reversals(frames)
    arch=archetypes(players)

    # Per-model uncertainty / authority envelope.
    uncertainty=trajectory[[
        "model","player_id","canonical_player_id","player_name","position",
        "y2_forecast_state_sd_points","y2_forecast_total_sd_points","y2_forecast_within_state_sd_points",
        "y3_forecast_state_sd_points","y3_forecast_total_sd_points","y3_forecast_within_state_sd_points",
        "y2_state_value_sd","y3_state_value_sd","state_value_sd_zero_cov_proxy",
        "state_value_sd_covariance_lower","state_value_sd_perfect_positive_upper",
        "mc_se_rss_proxy","mc_se_upper_bound","cross_horizon_covariance_status",
        "within_state_value_uncertainty_status",
    ]].copy()
    env=players[["player_id","intrinsic_envelope","rank_envelope"]]
    uncertainty=uncertainty.merge(env,on="player_id",how="left",validate="many_to_one")

    pref=json.loads(args.production_reference.read_text())
    parity=production_parity(frames["VNEXT_A2_BURR"],pref["values"])

    trajectory.to_csv(args.output_dir/"STAGE4_PLAYER_TRAJECTORY_AND_INTRINSIC.csv",index=False)
    pairrows.to_csv(args.output_dir/"STAGE4_PAIRWISE_RANK_VALUE.csv",index=False)
    pairstats.to_csv(args.output_dir/"STAGE4_PAIRWISE_SUMMARY.csv",index=False)
    uncertainty.to_csv(args.output_dir/"STAGE4_UNCERTAINTY.csv",index=False)
    players[players.material_reversal].sort_values(["rank_envelope","intrinsic_envelope"],ascending=False).to_csv(args.output_dir/"STAGE4_MATERIAL_PLAYER_REVERSALS.csv",index=False)
    arch.to_csv(args.output_dir/"STAGE4_ARCHETYPE_REVERSALS.csv",index=False)

    result={
        "study":"forecast-authority-stage4-intrinsic-impact",
        "authority":"research_only_no_production_change",
        "models":list(MODELS),"players":335,
        "material_player_reversal_count":int(players.material_reversal.sum()),
        "material_player_reversal_share":float(players.material_reversal.mean()),
        "material_archetype_count":int(arch.material_archetype_reversal.sum()),
        "archetype_count":int(len(arch)),
        "production_vnext_parity":parity,
        "pairwise_summary":pairstats.to_dict("records"),
        "uncertainty":{
            "current_value_consumes_within_state_burr_gamma":False,
            "vnext_forecast_within_state_uncertainty_preserved":True,
            "exact_cross_horizon_value_covariance_validated":False,
            "reported_value_uncertainty":"state-mixture lower/upper covariance envelope plus MC Shapley SE; vNext within-state Forecast SD separately",
        },
        "guards":{
            "forecast_tuned_from_intrinsic":False,"named_player_selection":False,
            "production_forecast_changed":False,"production_h3_changed":False,"intrinsic_changed":False,
        },
    }
    (args.output_dir/"STAGE4_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
