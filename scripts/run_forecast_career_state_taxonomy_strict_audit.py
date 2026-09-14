from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
    cal=load(root/'run_forecast_career_state_calibration.py','tax_audit_cal');legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','tax_audit_legacy');parity=load(root/'run_fundamental_intrinsic_production_parity.py','tax_audit_parity')
    rows=cal.load_rows(a.career_panel);examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);qb=parity.load_qb_probabilities(a.qb_results);by={(r.player_id,r.season):r for r in rows}
    candidates=[]
    for taxonomy in ('kmeans','quantile_balanced','quantile_starter_tail'):
        all_preds=[];folds={}
        for season in cal.FOLDS:
            bounds=cal.taxonomy_boundaries(rows,season,taxonomy);model=cal.TransitionModel(rows,season,bounds);fp=[]
            for e in [x for x in examples if x.season==season]:
                nxt=by.get((e.player_id,e.season+1));hist=by.get((e.player_id,e.season))
                if nxt is None:continue
                r=cal.Row(e.player_id,e.season,e.position,e.means[0],nxt.points,e.age,e.experience,None if hist is None else hist.draft_pick,None if hist is None else hist.prior_pct)
                p=cal.propagate(model,r,bounds,1,qb.get((e.season,e.player_id)));item=(r,p,bounds);fp.append(item);all_preds.append(item)
            folds[str(season)]=cal.calibration([x[0] for x in fp],fp)
        m=cal.calibration([x[0] for x in all_preds],all_preds)
        score=m['brier']+m['ece_up']+m['ece_down']+abs(m['up_pred']-m['up_obs'])+abs(m['down_pred']-m['down_obs'])
        candidates.append({'taxonomy':taxonomy,'score':score,'metrics':m,'folds':folds})
    selected=min(candidates,key=lambda x:x['score'])
    out={'population':'D2 inference-aligned: current state from PIT Forecast Y1 mean, next state from realized next-season production','candidates':candidates,'selected_taxonomy':selected['taxonomy'],'selected_metrics':selected['metrics']}
    (a.output_dir/'forecast_career_state_taxonomy_strict_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'selected':selected['taxonomy'],'candidates':[{ 'taxonomy':c['taxonomy'],'score':c['score'],'n':c['metrics']['n'],'brier':c['metrics']['brier'],'up_pred':c['metrics']['up_pred'],'up_obs':c['metrics']['up_obs'],'down_pred':c['metrics']['down_pred'],'down_obs':c['metrics']['down_obs']} for c in candidates]},indent=2))

if __name__=='__main__':main()
