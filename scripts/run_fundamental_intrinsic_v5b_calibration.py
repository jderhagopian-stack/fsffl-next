from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

DISCOUNT = 0.85
HORIZON = 3
REALIZED_HORIZON = 6
POSITIONS = ("QB", "RB", "WR", "TE")
MIN_TRAIN_EXAMPLES = 400
MIN_CELL_EXAMPLES = 30
EPS = 1e-9
GLOBAL_CONDITIONING_SCALE = 500.0
MODEL_VERSION = "fundamental-intrinsic-shared-career-v5b"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(values):
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def q(values, p):
    xs = sorted(values)
    if not xs:
        return 0.0
    x = p * (len(xs) - 1)
    lo, hi = int(math.floor(x)), int(math.ceil(x))
    if lo == hi:
        return xs[lo]
    f = x - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def age_band(position: str, age: int | None) -> str:
    if age is None:
        return "unknown"
    if position == "QB":
        if age <= 25: return "young"
        if age <= 29: return "prime"
        if age <= 33: return "veteran"
        return "late"
    if age <= 23: return "young"
    if age <= 26: return "prime"
    if age <= 29: return "veteran"
    return "late"


def three(e):
    return sum((DISCOUNT**i) * m for i, m in enumerate(e.means))


def xterm(e):
    return (DISCOUNT**HORIZON) * max(0.0, e.means[2])


def slope(subset):
    xs = [xterm(e) for e in subset]
    ys = [max(0.0, e.realized - three(e)) for e in subset]
    denom = sum(x*x for x in xs)
    return max(0.0, sum(x*y for x, y in zip(xs, ys, strict=True)) / denom) if denom > EPS else 0.0


def fit_continuation(training):
    parent = {p: slope([e for e in training if e.position == p]) for p in POSITIONS}
    cells = {}
    counts = {}
    for p in POSITIONS:
        for band in ("young", "prime", "veteran", "late", "unknown"):
            subset = [e for e in training if e.position == p and age_band(p, e.age) == band]
            counts[f"{p}:{band}"] = len(subset)
            if len(subset) >= MIN_CELL_EXAMPLES:
                cells[f"{p}:{band}"] = slope(subset)
    return {"parent": parent, "cells": cells, "counts": counts}


def continuation(e, params):
    factor = params["cells"].get(f"{e.position}:{age_band(e.position, e.age)}", params["parent"][e.position])
    return xterm(e) * factor


def baseline(e, params):
    return three(e) + continuation(e, params)


def conditioning(e):
    pos = [1.0 if e.position == p else 0.0 for p in POSITIONS[1:]]
    return [1.0, *(m/GLOBAL_CONDITIONING_SCALE for m in e.means), *(s/GLOBAL_CONDITIONING_SCALE for s in e.sds), *pos]


def fit_pedigree(training, continuation_params, legacy):
    X = [conditioning(e) for e in training]
    r = legacy.solve_ridge(X, [e.pedigree for e in training], ridge=1e-6)
    pres = [e.pedigree - legacy.dot(conditioning(e), r) for e in training]
    targets = [e.realized - baseline(e, continuation_params) for e in training]
    c = legacy.solve_ridge([[1.0, v] for v in pres], targets, ridge=1e-3)
    return r, c


def predict(e, cont, resid, coeff, legacy):
    b = baseline(e, cont)
    p = e.pedigree - legacy.dot(conditioning(e), resid)
    rv = coeff[0] + coeff[1]*p
    return b, rv, max(0.0, b+rv)


def fit_legacy_raw(training, legacy):
    anchors = legacy.position_anchors(training)
    cont = legacy.fit_continuation(training, anchors)
    residualizers, coeffs = legacy.fit_residual_model(training, anchors, cont, ("pedigree",))
    return anchors, cont, residualizers, coeffs


def predict_legacy_raw(e, fitted, legacy):
    anchors, cont, residualizers, coeffs = fitted
    _b, _r, f = legacy.predict(e, anchors, cont, ("pedigree",), residualizers, coeffs)
    return f * anchors[e.position] / 100.0


def evaluate(examples, legacy):
    rows=[]
    for holdout in sorted({e.season for e in examples}):
        train=[e for e in examples if e.season <= holdout-REALIZED_HORIZON]
        test=[e for e in examples if e.season == holdout]
        if len(train)<MIN_TRAIN_EXAMPLES or not test: continue
        oldfit=fit_legacy_raw(train, legacy)
        cont=fit_continuation(train)
        resid, coeff=fit_pedigree(train, cont, legacy)
        for e in test:
            old=predict_legacy_raw(e, oldfit, legacy)
            b,rv,new=predict(e,cont,resid,coeff,legacy)
            rows.append({"season":e.season,"position":e.position,"age":e.age,"target":e.realized,"old":old,"new":new,"base":b,"resid":rv,"oe":abs(old-e.realized),"ne":abs(new-e.realized)})
    oldmae=mean(r["oe"] for r in rows); newmae=mean(r["ne"] for r in rows)
    folds=defaultdict(list); bypos=defaultdict(list)
    for r in rows: folds[r["season"]].append(r); bypos[r["position"]].append(r)
    position={}
    for p in POSITIONS:
        vals=bypos[p]; om=mean(r["oe"] for r in vals); nm=mean(r["ne"] for r in vals)
        position[p]={"old_mae":om,"new_mae":nm,"mae_gain":(om-nm)/om}
    aging={}
    for p in ("RB","TE"):
        vals=[r for r in rows if r["position"]==p and r["age"] is not None and r["age"]>=30]
        aging[p]={"n":len(vals),"old_mae":mean(r["oe"] for r in vals),"new_mae":mean(r["ne"] for r in vals),"old_prediction":mean(r["old"] for r in vals),"new_prediction":mean(r["new"] for r in vals),"target":mean(r["target"] for r in vals)}
    oc=q([r["old"] for r in rows],.9); nc=q([r["new"] for r in rows],.9)
    return {"n":len(rows),"folds":len(folds),"old_raw_mae":oldmae,"new_raw_mae":newmae,"raw_mae_gain":(oldmae-newmae)/oldmae,"fold_wins":sum(mean(r["ne"] for r in v)<mean(r["oe"] for r in v) for v in folds.values()),"position":position,"aging_30_plus":aging,"old_top_decile_mae":mean(r["oe"] for r in rows if r["old"]>=oc),"new_top_decile_mae":mean(r["ne"] for r in rows if r["new"]>=nc)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--career-panel",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    legacy=load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"),"intrinsic_v4_for_v5b")
    rc=legacy.load_module(Path(__file__).with_name("run_career_calibration.py"),"career_for_v5b")
    examples=legacy.build_examples(legacy.load_rows(a.career_panel),rc)
    validation=evaluate(examples,legacy)
    cont=fit_continuation(examples); resid,coeff=fit_pedigree(examples,cont,legacy)
    vals=[]
    for e in examples:
        vals.append(predict(e,cont,resid,coeff,legacy)[2])
    cutoff=q(vals,.5); relevant=[v for v in vals if v>=cutoff]
    final={"continuation":cont,"conditioning_scale":GLOBAL_CONDITIONING_SCALE,"pedigree_residualizer":resid,"pedigree_residual_coefficients":coeff,"raw_quantiles":{str(p):q(vals,p) for p in (.05,.1,.25,.5,.75,.9,.95,.97,.99)},"display_reference_rule":"repaired predicted shared career value >= historical pooled median repaired prediction","display_reference_cutoff":cutoff,"display_reference_quantiles":{str(p):q(relevant,p) for p in (.05,.1,.25,.5,.75,.9,.95,.97,.99)},"raw_min":min(vals),"raw_max":max(vals)}
    payload={"model_version":MODEL_VERSION,"example_count":len(examples),"season_range":[min(e.season for e in examples),max(e.season for e in examples)],"target":"shared-unit six-season discounted realized football production","validation":validation,"final_parameters":final,"market_inputs_used":False,"replacement_inputs_used":False,"team_utility_inputs_used":False,"owner_inputs_used":False}
    (a.output_dir/"fundamental_intrinsic_v5b_calibration.json").write_text(json.dumps(payload,indent=2,sort_keys=True))
    print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=="__main__": main()
