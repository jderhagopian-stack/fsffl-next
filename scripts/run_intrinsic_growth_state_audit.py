from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position

POSITIONS = ("RB", "WR", "TE")
MIN_TRAIN = 400


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


def age_band(age):
    if age is None: return "unknown"
    if age <= 23: return "<=23"
    if age <= 26: return "24-26"
    if age <= 29: return "27-29"
    if age <= 32: return "30-32"
    return "33+"


def exp_state(exp):
    if exp <= 1: return "0-1"
    if exp <= 3: return "2-3"
    return "4+"


def quartile(value, pool):
    xs = sorted(pool)
    if not xs: return 1
    pct = bisect_right(xs, value) / len(xs)
    return min(4, max(1, int(min(.999999, pct) * 4) + 1))


def slope(rows):
    d = sum(x*x for x,y in rows)
    return max(0.0, sum(x*y for x,y in rows)/d) if d > 1e-9 else 0.0


def fit(training, pools, panel_by_key):
    grand = defaultdict(list); parent = defaultdict(list); cells = defaultdict(list)
    for e in training:
        if e.position not in POSITIONS or e.age is None or e.season not in pools: continue
        y1=max(0.0,e.means[0]); nxt=panel_by_key.get((e.player_id,e.season+1)); y2=nxt.points if nxt else 0.0
        qt=quartile(y1,pools[e.season][Position(e.position)])
        ab=age_band(e.age); es=exp_state(e.experience)
        grand[(e.position,ab)].append((y1,y2))
        parent[(e.position,ab,qt)].append((y1,y2))
        cells[(e.position,ab,es,qt)].append((y1,y2))
    gs={k:slope(v) for k,v in grand.items()}
    ps={}
    for k,v in parent.items():
        raw=slope(v); base=gs[(k[0],k[1])]; n=len(v); w=n/(n+75.0); ps[k]=w*raw+(1-w)*base
    cs={}
    for k,v in cells.items():
        raw=slope(v); base=ps.get((k[0],k[1],k[3]),gs[(k[0],k[1])]); n=len(v); w=n/(n+50.0); cs[k]=w*raw+(1-w)*base
    return gs,ps,cs


def growth_counts(pairs):
    vals=[(a,b) for a,b in pairs if a>0]; n=len(vals)
    return {"n":n,"any_growth":sum(b>a for a,b in vals)/n if n else 0,"growth_10":sum(b>=a*1.1 for a,b in vals)/n if n else 0,"growth_20":sum(b>=a*1.2 for a,b in vals)/n if n else 0,"growth_30":sum(b>=a*1.3 for a,b in vals)/n if n else 0}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--career-panel',type=Path,required=True); ap.add_argument('--model-a-rows',type=Path,required=True); ap.add_argument('--qb-results',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    parity=load_module(Path(__file__).with_name('run_fundamental_intrinsic_production_parity.py'),'growth_state_parity')
    legacy=load_module(Path(__file__).with_name('run_fundamental_intrinsic_residual_calibration.py'),'growth_state_legacy')
    examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy)
    _model,rawp=parity.load_model_a(a.model_a_rows); pools={s:{p:tuple(vals) for p,vals in ps.items()} for s,ps in rawp.items()}
    panel=legacy.load_rows(a.career_panel); by={(r.player_id,r.season):r for r in panel}
    rows=[]
    for holdout in sorted({e.season for e in examples}):
        train=[e for e in examples if e.season<=holdout-1]
        test=[e for e in examples if e.season==holdout and e.position in POSITIONS and e.age is not None and e.season in pools]
        if len(train)<MIN_TRAIN or not test: continue
        gs,ps,cs=fit(train,pools,by)
        for e in test:
            y1=max(0.0,e.means[0]); nxt=by.get((e.player_id,e.season+1)); target=nxt.points if nxt else 0.0
            qt=quartile(y1,pools[e.season][Position(e.position)]); ab=age_band(e.age); es=exp_state(e.experience)
            mult=cs.get((e.position,ab,es,qt),ps.get((e.position,ab,qt),gs.get((e.position,ab),1.0)))
            pred=y1*mult
            rows.append({'season':holdout,'position':e.position,'age':e.age,'experience':e.experience,'y1':y1,'current':max(0.0,e.means[1]),'challenger':pred,'target':target})
    out={}
    for key in ('current','challenger'):
        folds=defaultdict(list); pos=defaultdict(list); young=[]; dev=[]
        for r in rows:
            er=abs(r[key]-r['target']); folds[r['season']].append(er); pos[r['position']].append(er)
            if r['age']<=24: young.append(er)
            if r['experience']<=2: dev.append(er)
        out[key]={'mae':mean(abs(r[key]-r['target']) for r in rows),'position_mae':{p:mean(v) for p,v in pos.items()},'young_mae':mean(young),'experience_le2_mae':mean(dev),'fold_mae':{str(s):mean(v) for s,v in folds.items()}}
    common=sorted(set(out['current']['fold_mae'])&set(out['challenger']['fold_mae'])); out['challenger']['fold_wins_vs_current']=sum(out['challenger']['fold_mae'][s]<out['current']['fold_mae'][s] for s in common);out['challenger']['folds']=len(common)
    out['growth_frequency']={'current':growth_counts((r['y1'],r['current']) for r in rows),'challenger':growth_counts((r['y1'],r['challenger']) for r in rows),'realized':growth_counts((r['y1'],r['target']) for r in rows)}
    payload={'definition':'hierarchical football-only non-QB transition keyed by governed age band, experience state, and Y1 Forecast production quartile; no market or youth bonus','validation':out,'market_inputs_used':False,'team_utility_inputs_used':False,'replacement_inputs_used':False}
    (a.output_dir/'intrinsic_growth_state_audit.json').write_text(json.dumps(payload,indent=2,sort_keys=True)); print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=='__main__': main()
