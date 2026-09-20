from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

DISCOUNT=0.85
HORIZON=3
REALIZED_HORIZON=6
POSITIONS=("QB","RB","WR","TE")
MIN_TRAIN_EXAMPLES=400
MIN_CELL_EXAMPLES=30
EPS=1e-9
MODEL_VERSION="fundamental-intrinsic-shared-career-v5c"


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m


def mean(vals):
    xs=list(vals); return sum(xs)/len(xs) if xs else math.nan


def q(vals,p):
    xs=sorted(vals)
    if not xs:return 0.0
    z=p*(len(xs)-1); lo=int(math.floor(z)); hi=int(math.ceil(z))
    if lo==hi:return xs[lo]
    f=z-lo; return xs[lo]*(1-f)+xs[hi]*f


def age_band(position,age):
    if age is None:return "unknown"
    if position=="QB":
        if age<=25:return "young"
        if age<=29:return "prime"
        if age<=33:return "veteran"
        return "late"
    if age<=23:return "young"
    if age<=26:return "prime"
    if age<=29:return "veteran"
    return "late"


def three(e):return sum((DISCOUNT**i)*m for i,m in enumerate(e.means))
def xterm(e):return (DISCOUNT**HORIZON)*max(0.0,e.means[2])

def slope(sub):
    xs=[xterm(e) for e in sub]; ys=[max(0.0,e.realized-three(e)) for e in sub]; d=sum(x*x for x in xs)
    return max(0.0,sum(x*y for x,y in zip(xs,ys,strict=True))/d) if d>EPS else 0.0


def fit_tapers(training):
    parent={p:slope([e for e in training if e.position==p]) for p in POSITIONS}
    cells={}; counts={}
    for p in ("RB","WR","TE"):
        for band in ("veteran","late"):
            sub=[e for e in training if e.position==p and age_band(p,e.age)==band]
            counts[f"{p}:{band}"]=len(sub)
            if len(sub)>=MIN_CELL_EXAMPLES: cells[f"{p}:{band}"]=slope(sub)
    return {"parent":parent,"aging_cells":cells,"counts":counts}


def factor(e,tapers):
    # QB already receives governed career-state probabilities in Y2/Y3. Keep its
    # validated parent tail. For non-QBs only the veteran/late bands receive the
    # empirically fitted taper; young/prime retain the validated parent tail.
    if e.position in ("RB","WR","TE"):
        key=f"{e.position}:{age_band(e.position,e.age)}"
        if key in tapers["aging_cells"]: return tapers["aging_cells"][key]
    return tapers["parent"][e.position]


def old_fit(training,legacy):
    anchors=legacy.position_anchors(training); cont=legacy.fit_continuation(training,anchors); r,c=legacy.fit_residual_model(training,anchors,cont,("pedigree",)); return anchors,cont,r,c


def old_parts_raw(e,fitted,legacy):
    anchors,cont,r,c=fitted
    bnorm,rnorm,fnorm=legacy.predict(e,anchors,cont,("pedigree",),r,c)
    scale=anchors[e.position]/100.0
    return bnorm*scale,rnorm*scale,fnorm*scale


def new_predict(e,fitted,tapers,legacy):
    _oldbase,residual,_old=old_parts_raw(e,fitted,legacy)
    base=three(e)+xterm(e)*factor(e,tapers)
    return base,residual,max(0.0,base+residual)


def evaluate(examples,legacy):
    rows=[]
    for holdout in sorted({e.season for e in examples}):
        train=[e for e in examples if e.season<=holdout-REALIZED_HORIZON]; test=[e for e in examples if e.season==holdout]
        if len(train)<MIN_TRAIN_EXAMPLES or not test:continue
        fitted=old_fit(train,legacy); tapers=fit_tapers(train)
        for e in test:
            _ob,_or,old=old_parts_raw(e,fitted,legacy); nb,nr,new=new_predict(e,fitted,tapers,legacy)
            rows.append({"season":e.season,"position":e.position,"age":e.age,"target":e.realized,"old":old,"new":new,"new_base":nb,"residual":nr,"oe":abs(old-e.realized),"ne":abs(new-e.realized)})
    om=mean(r["oe"] for r in rows); nm=mean(r["ne"] for r in rows); folds=defaultdict(list); bypos=defaultdict(list)
    for r in rows:folds[r["season"]].append(r);bypos[r["position"]].append(r)
    pos={}
    for p in POSITIONS:
        vals=bypos[p]; po=mean(r["oe"] for r in vals);pn=mean(r["ne"] for r in vals);pos[p]={"old_mae":po,"new_mae":pn,"mae_gain":(po-pn)/po}
    aging={}
    for p in ("RB","WR","TE"):
        vals=[r for r in rows if r["position"]==p and r["age"] is not None and (r["age"]>=30)]
        if vals:aging[p]={"n":len(vals),"old_mae":mean(r["oe"] for r in vals),"new_mae":mean(r["ne"] for r in vals),"old_prediction":mean(r["old"] for r in vals),"new_prediction":mean(r["new"] for r in vals),"target":mean(r["target"] for r in vals)}
    oc=q([r["old"] for r in rows],.9);nc=q([r["new"] for r in rows],.9)
    return {"n":len(rows),"folds":len(folds),"fold_wins":sum(mean(r["ne"] for r in v)<mean(r["oe"] for r in v) for v in folds.values()),"old_raw_mae":om,"new_raw_mae":nm,"raw_mae_gain":(om-nm)/om,"position":pos,"aging_30_plus":aging,"old_top_decile_mae":mean(r["oe"] for r in rows if r["old"]>=oc),"new_top_decile_mae":mean(r["ne"] for r in rows if r["new"]>=nc)}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    legacy=load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"),"intrinsic_v4_for_v5c");rc=legacy.load_module(Path(__file__).with_name("run_career_calibration.py"),"career_for_v5c")
    examples=legacy.build_examples(legacy.load_rows(a.career_panel),rc);validation=evaluate(examples,legacy)
    fitted=old_fit(examples,legacy);tapers=fit_tapers(examples);vals=[]
    for e in examples: vals.append(new_predict(e,fitted,tapers,legacy)[2])
    cutoff=q(vals,.5);relevant=[v for v in vals if v>=cutoff]
    anchors=fitted[0]; residualizers=fitted[2]; residual_coeffs=fitted[3]
    final={"legacy_position_anchors_used_only_to_convert_residual_to_shared_units":anchors,"continuation":tapers,"pedigree_residualizer":residualizers["pedigree"],"pedigree_residual_coefficients_normalized":residual_coeffs,"raw_quantiles":{str(p):q(vals,p) for p in (.05,.1,.25,.5,.75,.9,.95,.97,.99)},"display_reference_rule":"repaired predicted shared career value >= historical pooled median repaired prediction","display_reference_cutoff":cutoff,"display_reference_quantiles":{str(p):q(relevant,p) for p in (.05,.1,.25,.5,.75,.9,.95,.97,.99)},"raw_min":min(vals),"raw_max":max(vals)}
    payload={"model_version":MODEL_VERSION,"example_count":len(examples),"season_range":[min(e.season for e in examples),max(e.season for e in examples)],"target":"shared-unit six-season discounted realized football production","repair":"remove position normalization from final coordinate; preserve validated pedigree residual economics converted to shared football units; taper only aging non-QB continuation cells","validation":validation,"final_parameters":final,"market_inputs_used":False,"replacement_inputs_used":False,"team_utility_inputs_used":False,"owner_inputs_used":False}
    (a.output_dir/"fundamental_intrinsic_v5c_calibration.json").write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=="__main__":main()
