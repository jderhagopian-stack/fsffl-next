from __future__ import annotations

import argparse, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path

POSITIONS=("QB","RB","WR","TE")
STATES=("out","depth","usable","starter","premium","elite")
USEFUL=set(STATES[2:]);STARTER=set(STATES[3:]);PREMIUM=set(STATES[4:])


def load(path:Path,name:str):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0

def q(xs,p):
    xs=sorted(xs)
    if not xs:return 0.0
    z=p*(len(xs)-1);lo=int(math.floor(z));hi=int(math.ceil(z));f=z-lo
    return xs[lo] if lo==hi else xs[lo]*(1-f)+xs[hi]*f

def brier(pr,out): return sum((pr[s]-(1.0 if s==out else 0.0))**2 for s in STATES)/len(STATES)
def logloss(pr,out): return -math.log(max(1e-12,pr[out]))
def age_band(base,pos,age): return base.age_band(pos,age)
def direction(base,current,out):
    a=base.state_index(current);b=base.state_index(out);return "up" if b>a else ("down" if b<a else "stable")
def dir_probs(base,current,pr):
    i=base.state_index(current);return {"up":sum(pr[s] for s in STATES if base.state_index(s)>i),"stable":pr[current],"down":sum(pr[s] for s in STATES if base.state_index(s)<i)}

def corrected_counts(base,panel,cutoff,boundaries,max_horizon=2):
    by={(r.player_id,r.season):r for r in panel if r.position in POSITIONS};detailed=defaultdict(lambda:defaultdict(float));ps=defaultdict(lambda:defaultdict(float));po=defaultdict(lambda:defaultdict(float));missing=0;eligible=0
    for r in panel:
        if r.season>=cutoff or r.position not in POSITIONS: continue
        current=base.state_for_points(r.points,boundaries[r.position]);band=base.age_band(r.position,r.age)
        for h in range(1,max_horizon+1):
            if r.season+h>=cutoff: continue
            eligible+=1;nxt=by.get((r.player_id,r.season+h))
            if nxt is None:
                ns="out";missing+=1
            else: ns=base.state_for_points(nxt.points,boundaries[r.position])
            detailed[(r.position,band,current,h)][ns]+=1;ps[(r.position,current,h)][ns]+=1;po[(r.position,h)][ns]+=1
    return (detailed,ps,po),{"eligible":eligible,"missing_as_out":missing,"missing_share":missing/eligible if eligible else 0.0}
def low_thresholds(panel,cutoff):
    out={}
    for p in POSITIONS:
        vals=[r.points for r in panel if r.position==p and r.season<cutoff and r.points>0]
        out[p]=q(vals,.25)
    return out

def actual_state(base,by,pid,season,pos,bounds):
    r=by.get((pid,season));return "out" if r is None else base.state_for_points(r.points,bounds[pos])
def with_qb(base,pr,e,qb_probs,h):
    if e.position=="QB":
        p=qb_probs.get((e.season,e.player_id))
        if p is not None:return base.enforce_qb_meaningful(pr,p[h-1])
    return pr

def probs(base,model,e,bounds,qb_probs,h):
    cur=base.state_for_points(e.means[0],bounds[e.position]);pr=base.transition_probs(model,e.position,base.age_band(e.position,e.age),cur,h);return cur,with_qb(base,pr,e,qb_probs,h)
def summarize(rows,key):
    if not rows:return {}
    return {"n":len(rows),"state_brier":mean(r[key+"brier"] for r in rows),"state_logloss":mean(r[key+"logloss"] for r in rows),"survival_brier":mean((r[key+"survival"]-r["survived"])**2 for r in rows),
            "useful_brier":mean((r[key+"useful"]-r["useful_obs"])**2 for r in rows),"starter_brier":mean((r[key+"starter"]-r["starter_obs"])**2 for r in rows),"premium_brier":mean((r[key+"premium"]-r["premium_obs"])**2 for r in rows),
            "production_mae":mean(r["production_abs_error"] for r in rows),"production_bias":mean(r["production_error"] for r in rows),
            "predicted_out":mean(1-r[key+"survival"] for r in rows),"realized_out":mean(1-r["survived"] for r in rows),
            "false_positive_developmental":mean(1.0 if r[key+"useful"]>=.5 and not r["useful_obs"] else 0.0 for r in rows),
            "false_negative_breakout":mean(1.0 if r[key+"useful"]<.5 and r["useful_obs"] else 0.0 for r in rows)}
def calibration(rows,key):
    bins=[]
    for lo in [0,.2,.4,.6,.8]:
        g=[r for r in rows if lo<=r[key+"useful"]<lo+.2 or (lo==.8 and r[key+"useful"]<=1)]
        if g:bins.append({"lo":lo,"hi":lo+.2,"n":len(g),"pred":mean(r[key+"useful"] for r in g),"obs":mean(r["useful_obs"] for r in g)})
    return bins

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--model-a-rows",type=Path,required=True);ap.add_argument("--qb-results",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    here=Path(__file__).parent;legacy=load(here/"run_fundamental_intrinsic_residual_calibration.py","cal_legacy");parity=load(here/"run_fundamental_intrinsic_production_parity.py","cal_parity");base=load(here/"run_intrinsic_explicit_state_challenge.py","cal_base")
    examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);panel=legacy.load_rows(a.career_panel);qb_probs=parity.load_qb_probabilities(a.qb_results);by={(r.player_id,r.season):r for r in panel}
    folds=sorted({e.season for e in examples});rows=[];audit={};fold_metrics={}
    for season in folds:
        test=[e for e in examples if e.season==season and (e.player_id,season) in by]
        if not test:continue
        bounds=base.fit_state_boundaries(panel,season);baseline=base.fit_transition_counts(panel,season,bounds);challenger,diag=corrected_counts(base,panel,season,bounds);thr=low_thresholds(panel,season);audit[str(season)]=diag
        foldrows=[]
        for e in test:
            source=by[(e.player_id,season)];low=source.points>0 and source.points<=thr[e.position];young=base.age_band(e.position,e.age)=="young";aging=base.age_band(e.position,e.age)=="aging"
            for h in (1,2):
                if season+h>max(r.season for r in panel):continue
                cur,pb=probs(base,baseline,e,bounds,qb_probs,h);_,pc=probs(base,challenger,e,bounds,qb_probs,h);out=actual_state(base,by,e.player_id,season+h,e.position,bounds);dpb=dir_probs(base,cur,pb);dpc=dir_probs(base,cur,pc);dobs=direction(base,cur,out)
                actual=by.get((e.player_id,season+h));actual_points=max(0.0,actual.points) if actual else 0.0;pred=max(0.0,e.means[h])
                r={"season":season,"horizon":h,"position":e.position,"age_band":base.age_band(e.position,e.age),"current_state":cur,"outcome_state":out,"low_end":low,"young_low":low and young,"older_fringe":low and aging,"disappear":out=="out","depth_only":out=="depth","true_developmental":low and young and out in USEFUL,
                   "survived":0.0 if out=="out" else 1.0,"useful_obs":out in USEFUL,"starter_obs":out in STARTER,"premium_obs":out in PREMIUM,"production_forecast":pred,"production_actual":actual_points,"production_error":pred-actual_points,"production_abs_error":abs(pred-actual_points),"direction_obs":dobs}
                for k,pr,dp in (("base_",pb,dpb),("chal_",pc,dpc)):
                    r[k+"brier"]=brier(pr,out);r[k+"logloss"]=logloss(pr,out);r[k+"survival"]=1-pr["out"];r[k+"useful"]=sum(pr[s] for s in USEFUL);r[k+"starter"]=sum(pr[s] for s in STARTER);r[k+"premium"]=sum(pr[s] for s in PREMIUM);r[k+"direction_probability"]=dp[dobs]
                rows.append(r);foldrows.append(r)
        lowrows=[r for r in foldrows if r["low_end"]];fold_metrics[str(season)]={"n":len(foldrows),"low_n":len(lowrows),"base_low_brier":mean(r["base_brier"] for r in lowrows),"chal_low_brier":mean(r["chal_brier"] for r in lowrows)}
    groups={"overall":rows,"low_end":[r for r in rows if r["low_end"]],"true_developmental":[r for r in rows if r["true_developmental"]],"disappear":[r for r in rows if r["disappear"]],"depth_only":[r for r in rows if r["depth_only"]],"young_low":[r for r in rows if r["young_low"]],"older_fringe":[r for r in rows if r["older_fringe"]]}
    for p in POSITIONS:groups[p]=[r for r in rows if r["position"]==p];groups[p+"_low"]=[r for r in rows if r["position"]==p and r["low_end"]]
    summaries={g:{"baseline":summarize(rs,"base_"),"challenger":summarize(rs,"chal_")} for g,rs in groups.items()}
    low=groups["low_end"];ov=groups["overall"];dev=groups["true_developmental"]
    base_low=summaries["low_end"]["baseline"];chal_low=summaries["low_end"]["challenger"];base_ov=summaries["overall"]["baseline"];chal_ov=summaries["overall"]["challenger"]
    rel_low=(base_low["state_brier"]-chal_low["state_brier"])/base_low["state_brier"] if base_low.get("state_brier") else 0;rel_surv=(base_low["survival_brier"]-chal_low["survival_brier"])/base_low["survival_brier"] if base_low.get("survival_brier") else 0;overall_deg=(chal_ov["state_brier"]-base_ov["state_brier"])/base_ov["state_brier"] if base_ov.get("state_brier") else 0
    def recall(rs,key):
        den=sum(1 for r in rs if r["useful_obs"]);return sum(1 for r in rs if r["useful_obs"] and r[key+"useful"]>=.5)/den if den else 0.0
    base_rec=recall(dev,"base_");chal_rec=recall(dev,"chal_");rec_drop=base_rec-chal_rec
    pos_guard={};pos_ok=True
    for p in POSITIONS:
        b=summaries[p+"_low"]["baseline"].get("state_brier",0);c=summaries[p+"_low"]["challenger"].get("state_brier",0);deg=(c-b)/b if b else 0;pos_guard[p]=deg;pos_ok=pos_ok and deg<=.05
    scored=[v for v in fold_metrics.values() if v["low_n"]>0];fold_nonworse=sum(1 for v in scored if v["chal_low_brier"]<=v["base_low_brier"]);fold_ok=fold_nonworse>=math.ceil((2/3)*len(scored)) if scored else False
    fp_base=base_low["false_positive_developmental"];fp_chal=chal_low["false_positive_developmental"];fn_base=base_low["false_negative_breakout"];fn_chal=chal_low["false_negative_breakout"]
    defect_missing=mean(v["missing_share"] for v in audit.values());out_gap_base=abs(base_low["predicted_out"]-base_low["realized_out"]);out_gap_chal=abs(chal_low["predicted_out"]-chal_low["realized_out"]);defect_confirmed=defect_missing>.05 and out_gap_chal<out_gap_base
    guard1=rel_low>=.10 or rel_surv>=.15;guard2=overall_deg<=.02;guard3=rec_drop<=.03;guard6=(fn_chal-fn_base)<=.03 and fp_chal<=fp_base+1e-12;promising=defect_confirmed and guard1 and guard2 and guard3 and pos_ok and fold_ok and guard6
    conclusion="B1. IDENTIFIED FORECAST DEFECT + PROMISING BOUNDED CORRECTION" if promising else ("B2. FORECAST DEFECT CONFIRMED BUT NO CURRENT CORRECTION IS PROMOTABLE" if defect_confirmed else "B4. INSUFFICIENT EVIDENCE TO IDENTIFY THE FORECAST DEFECT")
    payload={"study":"forecast-low-end-career-calibration-v1","cohort_protocol":"artifacts/research/forecast_low_end_calibration_protocol.md","role_opportunity_stratification":"unavailable in career_transition_panel.csv; no proxy invented","baseline_defect_hypothesis":"missing future rows skipped by frozen transition fit condition on future-row presence and can understate out/disappearance probability","audit":audit,"summaries":summaries,"folds":fold_metrics,"calibration":{"baseline_low_useful":calibration(low,"base_"),"challenger_low_useful":calibration(low,"chal_")},"guardrails":{"low_state_brier_relative_improvement":rel_low,"low_survival_brier_relative_improvement":rel_surv,"overall_state_brier_relative_degradation":overall_deg,"true_developmental_recall_baseline":base_rec,"true_developmental_recall_challenger":chal_rec,"recall_drop":rec_drop,"position_low_brier_relative_degradation":pos_guard,"fold_nonworse":fold_nonworse,"fold_scored":len(scored),"false_positive_baseline":fp_base,"false_positive_challenger":fp_chal,"false_negative_baseline":fn_base,"false_negative_challenger":fn_chal,"guard1":guard1,"guard2":guard2,"guard3":guard3,"position_guard":pos_ok,"fold_guard":fold_ok,"error_balance_guard":guard6},"defect":{"mean_missing_transition_share":defect_missing,"low_end_out_gap_baseline":out_gap_base,"low_end_out_gap_challenger":out_gap_chal,"confirmed":defect_confirmed},"conclusion":conclusion,"downstream_shapley_diagnostic":"not used to fit/select correction; full state-specific 2048 Shapley rerun intentionally omitted because Forecast evidence is authoritative for this track and prompt makes Value pass-through optional","leakage":{"value_feedback":False,"market":False,"owner":False,"transactions":False,"named_tuning":False}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps({"conclusion":conclusion,"defect":payload["defect"],"guardrails":payload["guardrails"],"low_end":summaries["low_end"],"true_developmental":summaries["true_developmental"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
