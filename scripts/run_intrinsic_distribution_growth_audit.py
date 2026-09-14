from __future__ import annotations
import argparse, importlib.util, json, math, statistics, sys
from collections import defaultdict
from pathlib import Path
N=statistics.NormalDist()
POSITIONS=('QB','RB','WR','TE')

def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def prob_above(mu,sd,threshold):
 if sd<=1e-9:return 1.0 if mu>threshold else 0.0
 return 1.0-N.cdf((threshold-mu)/sd)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
 parity=load(Path(__file__).with_name('run_fundamental_intrinsic_production_parity.py'),'dg_parity');legacy=load(Path(__file__).with_name('run_fundamental_intrinsic_residual_calibration.py'),'dg_legacy')
 ex,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);panel=legacy.load_rows(a.career_panel);by={(r.player_id,r.season):r for r in panel}
 out={}
 for p in POSITIONS:
  rows=[e for e in ex if e.position==p and e.means[0]>0]
  d={}
  for label,mult in [('any',1.0),('10',1.1),('20',1.2),('30',1.3)]:
   probs=[prob_above(e.means[1],e.sds[1],e.means[0]*mult) for e in rows]
   realized=[1.0 if (by.get((e.player_id,e.season+1)).points if by.get((e.player_id,e.season+1)) else 0.0)>=e.means[0]*mult else 0.0 for e in rows]
   d[label]={'mean_forecast_probability':sum(probs)/len(probs),'realized_frequency':sum(realized)/len(realized),'absolute_calibration_gap':abs(sum(probs)/len(probs)-sum(realized)/len(realized))}
  out[p]={'n':len(rows),'y2_growth_probability':d}
 payload={'method':'Normal moment approximation to governed ForecastDistribution mean/std; diagnostic only, no new valuation input','positions':out,'market_inputs_used':False}
 (a.output_dir/'intrinsic_distribution_growth_audit.json').write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':main()
