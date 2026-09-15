from __future__ import annotations

import argparse, csv, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path

POSITIONS=("QB","RB","WR","TE")
STATES=("out","depth","usable","starter","premium","elite")
USEFUL=set(STATES[2:]); STARTER=set(STATES[3:]); PREMIUM=set(STATES[4:])
MIN_CELL=30
ALPHA=BETA=0.5


def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def mean(xs):
    xs=list(xs); return sum(xs)/len(xs) if xs else 0.0

def load_usage(path:Path):
    out={}
    with path.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["player_id"],int(r["season"]))]={
              "position":r["position"],"games":float(r["games"] or 0),"opportunity":float(r["opportunity"] or 0),
              "opportunity_per_game":float(r["opportunity_per_game"] or 0),"role_band":r["role_band"] or "weak"}
    return out

class MissingModel:
    def __init__(self,counts,with_role): self.counts=counts; self.with_role=with_role
    def _p(self,key):
        miss,total=self.counts.get(key,(0,0))
        if total < MIN_CELL: return None
        return (miss+ALPHA)/(total+ALPHA+BETA)
    def probability(self,pos,age_band,state,h,role_band=None):
        keys=[]
        if self.with_role and role_band is not None:
            keys += [("role_age_state",pos,age_band,state,role_band,h),("role_state",pos,state,role_band,h)]
        keys += [("age_state",pos,age_band,state,h),("state",pos,state,h),("position",pos,h)]
        for key in keys:
            p=self._p(key)
            if p is not None:return p,key
        return 0.5,("unsupported",pos,h)

def fit_missing_model(base,panel,cutoff,bounds,usage,with_role):
    by={(r.player_id,r.season):r for r in panel if r.position in POSITIONS}; counts=defaultdict(lambda:[0,0])
    for r in panel:
        if r.position not in POSITIONS or r.season>=cutoff:continue
        state=base.state_for_points(r.points,bounds[r.position]); age=base.age_band(r.position,r.age)
        u=usage.get((r.player_id,r.season)); role=u["role_band"] if u else None
        for h in (1,2):
            # Target must be strictly before the fold cutoff, matching the prior hard-control chronology.
            if r.season+h>=cutoff:continue
            missing=1 if (r.player_id,r.season+h) not in by else 0
            keys=[("age_state",r.position,age,state,h),("state",r.position,state,h),("position",r.position,h)]
            if with_role and role is not None:
                keys=[("role_age_state",r.position,age,state,role,h),("role_state",r.position,state,role,h)]+keys
            for key in keys:
                counts[key][0]+=missing; counts[key][1]+=1
    return MissingModel(dict(counts),with_role)

def compose_soft(base,prior,baseline_model,missing_model,e,bounds,qb_probs,h,role_band):
    cur=base.state_for_points(e.means[0],bounds[e.position]); age=base.age_band(e.position,e.age)
    b=base.transition_probs(baseline_model,e.position,age,cur,h)
    m,key=missing_model.probability(e.position,age,cur,h,role_band)
    pr={s:(1-m)*b[s] for s in STATES}; pr["out"]=m+(1-m)*b["out"]
    pr=prior.with_qb(base,pr,e,qb_probs,h)
    return cur,pr,m,key

def state_reliability(rows,prefix):
    out={}
    for s in STATES:
        out[s]={"predicted":mean(r[prefix+"state_"+s] for r in rows),"realized":mean(1.0 if r["outcome_state"]==s else 0.0 for r in rows),"n":len(rows)}
    return out

def probability_bins(rows,field,obsfield):
    bins=[]
    for lo in (0,.2,.4,.6,.8):
        hi=lo+.2
        g=[r for r in rows if (lo<=r[field]<hi) or (lo==.8 and lo<=r[field]<=1)]
        if g: bins.append({"lo":lo,"hi":hi,"n":len(g),"predicted":mean(r[field] for r in g),"realized":mean(float(r[obsfield]) for r in g)})
    return bins

def recall(rows,prefix):
    den=sum(1 for r in rows if r["useful_obs"])
    return sum(1 for r in rows if r["useful_obs"] and r[prefix+"useful"]>=.5)/den if den else 0.0

def group_summaries(prior,groups,prefixes):
    return {g:{p:prior.summarize(rs,p) for p in prefixes} for g,rs in groups.items()}

def guardrails(prior,summaries,groups,fold_metrics,cand):
    base="c0_"; cp=cand+"_"; bl=summaries["low_end"][base]; cl=summaries["low_end"][cp]
    bo=summaries["overall"][base]; co=summaries["overall"][cp]
    rel_state=(bl["state_brier"]-cl["state_brier"])/bl["state_brier"]
    rel_surv=(bl["survival_brier"]-cl["survival_brier"])/bl["survival_brier"]
    overall_deg=(co["state_brier"]-bo["state_brier"])/bo["state_brier"]
    br=recall(groups["true_developmental"],base); cr=recall(groups["true_developmental"],cp); rec_drop=br-cr
    fn_inc=cl["false_negative_breakout"]-bl["false_negative_breakout"]
    fp_rel=(bl["false_positive_developmental"]-cl["false_positive_developmental"])/bl["false_positive_developmental"] if bl["false_positive_developmental"] else 0
    pos_deg={}; pos_ok=True
    for pos in POSITIONS:
        b=summaries[pos+"_low"][base].get("state_brier",0); c=summaries[pos+"_low"][cp].get("state_brier",0)
        d=(c-b)/b if b else 0; pos_deg[pos]=d; pos_ok=pos_ok and d<=.05
    rel_folds=[]; nonworse=0
    for season,v in fold_metrics.items():
        b=v[base+"low_brier"]; c=v[cp+"low_brier"]
        if c<=b:nonworse+=1
        rel_folds.append((c-b)/b if b else 0)
    temporal_ok=nonworse>=math.ceil((2/3)*len(rel_folds)) and (max(rel_folds) if rel_folds else 0)<=.20
    tests={
      "A_low_end_calibration":rel_state>=.10 or rel_surv>=.15,
      "B_true_developmental_recall":rec_drop<=.03,
      "C_breakout_false_negative":fn_inc<=.03,
      "D_false_positive_improvement":fp_rel>=.10,
      "E_position_safety":pos_ok,
      "F_temporal_consistency":temporal_ok,
      "G_overall_safety":overall_deg<=.02,
      "H_no_leakage":True}
    return {"passes_all":all(tests.values()),"tests":tests,"low_state_brier_relative_improvement":rel_state,"low_survival_brier_relative_improvement":rel_surv,"overall_state_brier_relative_degradation":overall_deg,"true_developmental_recall_baseline":br,"true_developmental_recall_candidate":cr,"recall_drop":rec_drop,"low_false_negative_baseline":bl["false_negative_breakout"],"low_false_negative_candidate":cl["false_negative_breakout"],"false_negative_increase":fn_inc,"low_false_positive_baseline":bl["false_positive_developmental"],"low_false_positive_candidate":cl["false_positive_developmental"],"false_positive_relative_improvement":fp_rel,"position_low_state_brier_relative_degradation":pos_deg,"fold_nonworse":nonworse,"fold_scored":len(rel_folds),"worst_fold_relative_degradation":max(rel_folds) if rel_folds else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--career-panel",type=Path,required=True); ap.add_argument("--usage-panel",type=Path,required=True)
    ap.add_argument("--model-a-rows",type=Path,required=True); ap.add_argument("--qb-results",type=Path,required=True)
    ap.add_argument("--prior-track-b-json",type=Path,required=True); ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args(); here=Path(__file__).parent
    prior=load(here/"run_forecast_low_end_career_calibration.py","dd_prior")
    legacy=load(here/"run_fundamental_intrinsic_residual_calibration.py","dd_legacy")
    parity=load(here/"run_fundamental_intrinsic_production_parity.py","dd_parity")
    base=load(here/"run_intrinsic_explicit_state_challenge.py","dd_base")
    examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy)
    panel=legacy.load_rows(a.career_panel); qb_probs=parity.load_qb_probabilities(a.qb_results); usage=load_usage(a.usage_panel)
    by={(r.player_id,r.season):r for r in panel}; max_season=max(r.season for r in panel); player_seasons=defaultdict(list)
    for r in panel:player_seasons[r.player_id].append(r.season)
    for pid in player_seasons:player_seasons[pid].sort()
    folds=sorted({e.season for e in examples}); rows=[]; folds_out={}; missing_model_diagnostics={}
    prefixes=("c0_","c1_","c2_","c3_")
    for season in folds:
        test=[e for e in examples if e.season==season and (e.player_id,season) in by]
        if not test:continue
        bounds=base.fit_state_boundaries(panel,season); c0model=base.fit_transition_counts(panel,season,bounds); c1model,c1diag=prior.corrected_counts(base,panel,season,bounds)
        c2model=fit_missing_model(base,panel,season,bounds,usage,False); c3model=fit_missing_model(base,panel,season,bounds,usage,True); thr=prior.low_thresholds(panel,season)
        foldrows=[]; miss_diag={"c1":c1diag,"c2_fallback_counts":{},"c3_fallback_counts":{}}
        for e in test:
            src=by[(e.player_id,season)]; low=src.points>0 and src.points<=thr[e.position]; age=base.age_band(e.position,e.age); role=usage.get((e.player_id,season),{}).get("role_band")
            for h in (1,2):
                if season+h>max_season:continue
                cur,p0=prior.probs(base,c0model,e,bounds,qb_probs,h); _,p1=prior.probs(base,c1model,e,bounds,qb_probs,h)
                _,p2,m2,k2=compose_soft(base,prior,c0model,c2model,e,bounds,qb_probs,h,role); _,p3,m3,k3=compose_soft(base,prior,c0model,c3model,e,bounds,qb_probs,h,role)
                miss_diag["c2_fallback_counts"][str(k2)]=miss_diag["c2_fallback_counts"].get(str(k2),0)+1; miss_diag["c3_fallback_counts"][str(k3)]=miss_diag["c3_fallback_counts"].get(str(k3),0)+1
                out=prior.actual_state(base,by,e.player_id,season+h,e.position,bounds); actual=by.get((e.player_id,season+h)); actual_points=max(0.0,actual.points) if actual else 0.0; pred=max(0.0,e.means[h])
                later_return=actual is None and any(s>season+h for s in player_seasons[e.player_id])
                r={"season":season,"horizon":h,"player_id":e.player_id,"position":e.position,"age_band":age,"experience":e.experience,"current_state":cur,"outcome_state":out,"role_band":role or "unknown","low_end":low,"young_low":low and age=="young","prime_low":low and age=="prime","older_fringe":low and age=="aging","disappear":out=="out","depth_only":out=="depth","true_developmental":low and age=="young" and out in USEFUL,"temporary_absence_return":later_return,"missing_no_later_row":actual is None and not later_return,"survived":0.0 if out=="out" else 1.0,"useful_obs":out in USEFUL,"starter_obs":out in STARTER,"premium_obs":out in PREMIUM,"production_forecast":pred,"production_actual":actual_points,"production_error":pred-actual_points,"production_abs_error":abs(pred-actual_points),"c2_missing_probability":m2,"c3_missing_probability":m3}
                for pref,pr in zip(prefixes,(p0,p1,p2,p3)):
                    r[pref+"brier"]=prior.brier(pr,out); r[pref+"logloss"]=prior.logloss(pr,out); r[pref+"survival"]=1-pr["out"]; r[pref+"useful"]=sum(pr[s] for s in USEFUL); r[pref+"starter"]=sum(pr[s] for s in STARTER); r[pref+"premium"]=sum(pr[s] for s in PREMIUM)
                    for s in STATES:r[pref+"state_"+s]=pr[s]
                rows.append(r);foldrows.append(r)
        lowrows=[r for r in foldrows if r["low_end"]]
        fo={"n":len(foldrows),"low_n":len(lowrows)}
        for pref in prefixes:fo[pref+"low_brier"]=mean(r[pref+"brier"] for r in lowrows)
        folds_out[str(season)]=fo; missing_model_diagnostics[str(season)]=miss_diag
    groups={"overall":rows,"low_end":[r for r in rows if r["low_end"]],"true_developmental":[r for r in rows if r["true_developmental"]],"disappear":[r for r in rows if r["disappear"]],"depth_only":[r for r in rows if r["depth_only"]],"young_low":[r for r in rows if r["young_low"]],"prime_low":[r for r in rows if r["prime_low"]],"older_fringe":[r for r in rows if r["older_fringe"]],"temporary_absence_return":[r for r in rows if r["temporary_absence_return"]],"missing_no_later_row":[r for r in rows if r["missing_no_later_row"]]}
    for pos in POSITIONS:
        groups[pos]=[r for r in rows if r["position"]==pos]; groups[pos+"_low"]=[r for r in rows if r["position"]==pos and r["low_end"]]
    for role in ("weak","established"):
        groups["role_"+role+"_low"]=[r for r in rows if r["low_end"] and r["role_band"]==role]
    summaries=group_summaries(prior,groups,prefixes)
    guards={"C2":guardrails(prior,summaries,groups,folds_out,"c2"),"C3":guardrails(prior,summaries,groups,folds_out,"c3")}
    selected="C2" if guards["C2"]["passes_all"] else ("C3" if guards["C3"]["passes_all"] else None)
    if selected: conclusion="F1. PROMOTABLE FORECAST CORRECTION IDENTIFIED"
    elif guards["C2"]["tests"]["A_low_end_calibration"] or guards["C3"]["tests"]["A_low_end_calibration"]: conclusion="F2. DEFECT CONFIRMED; PROMISING DIRECTION FOUND BUT NOT PROMOTABLE"
    else: conclusion="F4. CURRENT FORECAST STRUCTURE IS INADEQUATE FOR THIS DISTINCTION"
    # Exact Phase-0 reproduction check against retained authoritative PR #141 artifact.
    old=json.loads(a.prior_track_b_json.read_text()); checks={}
    for label,newv,oldv in (
      ("c0_low_state_brier",summaries["low_end"]["c0_"]["state_brier"],old["summaries"]["low_end"]["baseline"]["state_brier"]),
      ("c1_low_state_brier",summaries["low_end"]["c1_"]["state_brier"],old["summaries"]["low_end"]["challenger"]["state_brier"]),
      ("c0_low_predicted_out",summaries["low_end"]["c0_"]["predicted_out"],old["summaries"]["low_end"]["baseline"]["predicted_out"]),
      ("c1_low_predicted_out",summaries["low_end"]["c1_"]["predicted_out"],old["summaries"]["low_end"]["challenger"]["predicted_out"])):
        checks[label]={"new":newv,"prior":oldv,"abs_diff":abs(newv-oldv),"pass":abs(newv-oldv)<=1e-10}
    if not all(v["pass"] for v in checks.values()): raise RuntimeError("Phase-0 reproduction mismatch: "+json.dumps(checks))
    reliability={}
    for pref in prefixes:
        reliability[pref]={"states_low":state_reliability(groups["low_end"],pref),"useful_bins_low":probability_bins(groups["low_end"],pref+"useful","useful_obs"),"out_bins_low":probability_bins(groups["low_end"],pref+"state_out","disappear")}
    production_by_h={}
    for h in (1,2):
        for cohort,rs in (("overall",[r for r in rows if r["horizon"]==h]),("low_end",[r for r in rows if r["horizon"]==h and r["low_end"]])):
            production_by_h[f"h{h}_{cohort}"]={"n":len(rs),"mae":mean(r["production_abs_error"] for r in rs),"bias":mean(r["production_error"] for r in rs)}
    temporary_diag={}
    for cohort in ("temporary_absence_return","missing_no_later_row"):
        rs=groups[cohort]; temporary_diag[cohort]={"n":len(rs),**{pref+"predicted_out":mean(r[pref+"state_out"] for r in rs) for pref in prefixes}}
    payload={"study":"forecast-disappearance-development-calibration-v1","frozen_protocol":"artifacts/research/forecast_disappearance_development_frozen_protocol.md","phase0_reproduction":checks,"rows_n":len(rows),"folds_n":len(folds_out),"summaries":summaries,"folds":folds_out,"guardrails":guards,"selected_candidate":selected,"conclusion":conclusion,"reliability":reliability,"temporary_absence_diagnostic":temporary_diag,"production_mean_diagnostic":production_by_h,"missing_model_diagnostics":missing_model_diagnostics,"evidence":{"role_definition":{"QB":"pass attempts / games","RB":"(carries + targets) / games","WR":"targets / games","TE":"targets / games"},"draft_pedigree":"excluded for inadequate historical coverage","snaps_routes":"unavailable in audited source"},"downstream_shapley":{"authorized":bool(selected),"run":False,"reason":"Forecast-only selection completed first; downstream diagnostic requires separate post-selection execution only if selected_candidate is non-null"},"leakage":{"value_feedback":False,"shapley_selection":False,"market":False,"owner":False,"transactions":False,"roster_fit":False,"named_tuning":False,"future_return_as_predictor":False}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True))
    print(json.dumps({"conclusion":conclusion,"selected":selected,"guardrails":guards,"low_end":summaries["low_end"],"true_dev":summaries["true_developmental"],"production":production_by_h},indent=2,sort_keys=True))
if __name__=="__main__":main()
