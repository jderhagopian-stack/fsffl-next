from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from fsffl.forecast.current_runtime import build_current_live_forecasts
from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

TARGETS={
 'Josh Allen','Drake Maye','Lamar Jackson','Dak Prescott','Sam Darnold',
 'Bijan Robinson','Quinshon Judkins','Derrick Henry','Jonathon Brooks','Rhamondre Stevenson','Tyler Allgeier',
 'Jaxon Smith-Njigba','CeeDee Lamb','Zay Flowers','Tee Higgins','DeVonta Smith','KC Concepcion','Troy Franklin',
 'Brock Bowers','Trey McBride','Kyle Pitts','Dallas Goedert',"Ja'Tavion Sanders"
}


def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--calibration-json',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
    cal=load(root/'run_forecast_career_state_calibration.py','current_state_cal');marg=load(root/'run_intrinsic_marginal_franchise_challenge.py','current_state_marg');legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','current_state_legacy');parity=load(root/'run_fundamental_intrinsic_production_parity.py','current_state_parity');current=load(root/'_tmp_current_marginal_franchise_sanity.py','current_state_helper')
    panel=cal.load_rows(a.career_panel);tax=json.loads(a.calibration_json.read_text())['selected_taxonomy'];bounds=cal.taxonomy_boundaries(panel,2026,tax);tm=cal.TransitionModel(panel,2026,bounds);samples=cal.state_samples(panel,2026,bounds)
    examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);hist_qb=parity.load_qb_probabilities(a.qb_results);bykey={(r.player_id,r.season):r for r in panel};_,actual_baselines=marg.contexts_from_actual(legacy.load_rows(a.career_panel))

    state=current.build_state();live=build_current_live_forecasts(state,minimum_independent_sources=2);state=state.model_copy(update={'as_of':live.evaluation_as_of,'player_states':tuple(ps.model_copy(update={'as_of':live.evaluation_as_of}) for ps in state.player_states)})
    bounded=build_non_qb_bounded_paths(state,season_forecasts=live.fantasy_point_forecasts);qbstates=build_qb_career_state_forecasts(state,season_forecasts=live.fantasy_point_forecasts);inc=build_current_intrinsic_values_v2(state,season_forecasts=live.fantasy_point_forecasts,base_forecast_model_version=live.model_version,bounded_paths=bounded,qb_career_states=qbstates)
    players={p.player_id:p for p in state.players};pstates={p.player_id:p for p in state.player_states};est={e.player_id:e for e in inc.estimates}
    pools={p.value:tuple(sorted(max(0.0,e.horizons[0].forecast_mean) for e in inc.estimates if e.position.value==p.value)) for p in current.Position}
    baseline,_=marg.baselines_from_pools({current.Position(k):v for k,v in pools.items()})
    baseline={k.value:v for k,v in baseline.items()}

    def c2_x(x,pos,b=baseline):return (12.0*marg.marginal_at_x(max(0.0,x),b[pos])+0.5*max(0.0,x))/13.0
    state_values={(p,s):(0.0 if s=='out' else cal.mean(c2_x(v,p) for v in samples.get((p,s),()))) for p in cal.POSITIONS for s in cal.STATE_NAMES}
    state_prod={(p,s):(0.0 if s=='out' else cal.mean(samples.get((p,s),()))) for p in cal.POSITIONS for s in cal.STATE_NAMES}

    # Fit unchanged D2 continuation coordinate on all historical PIT examples using repaired Forecast states.
    target={id(e):sum((cal.DISCOUNT**off)*((12.0*marg.marginal_at_x(max(0.0,nr.points),actual_baselines[yr][e.position])+0.5*max(0.0,nr.points))/13.0) for off in range(6) if (nr:=bykey.get((e.player_id,(yr:=e.season+off)))) is not None and yr in actual_baselines) for e in examples}
    parents={};cells={}
    def hist_value(e):
        bb=cal.taxonomy_boundaries(panel,e.season,tax);tt=cal.TransitionModel(panel,e.season,bb);ss=cal.state_samples(panel,e.season,bb);fb={p:baseline[p] for p in cal.POSITIONS}
        sv={(p,s):(0.0 if s=='out' else cal.mean((12.0*marg.marginal_at_x(max(0.0,v),fb[p])+0.5*max(0.0,v))/13.0 for v in ss.get((p,s),()))) for p in cal.POSITIONS for s in cal.STATE_NAMES}
        r=cal.Row(e.player_id,e.season,e.position,e.means[0],0,e.age,e.experience,None,None);p2=cal.propagate(tt,r,bb,1,hist_qb.get((e.season,e.player_id)));p3=cal.propagate(tt,r,bb,2,hist_qb.get((e.season,e.player_id)));v=(12.0*marg.marginal_at_x(max(0.0,e.means[0]),fb[e.position])+0.5*max(0.0,e.means[0]))/13.0;v+=cal.DISCOUNT*sum(p2[s]*sv[(e.position,s)] for s in cal.STATE_NAMES)+(cal.DISCOUNT**2)*sum(p3[s]*sv[(e.position,s)] for s in cal.STATE_NAMES);term=(cal.DISCOUNT**3)*sum(p3[s]*sv[(e.position,s)] for s in cal.STATE_NAMES);return v,term
    # To keep current sanity fast and parity-shaped, use position-level continuation only.
    cache=[]
    for e in examples:
        if e.season<2018:continue
        try:v,t=hist_value(e)
        except Exception:continue
        cache.append((e,v,t))
    for pos in cal.POSITIONS:
        xs=[(e,v,t) for e,v,t in cache if e.position==pos];den=sum(t*t for e,v,t in xs);parents[pos]=0.0 if den<cal.EPS else max(0.0,sum(t*max(0.0,target[id(e)]-v) for e,v,t in xs)/den)

    rows=[];values={};t0=time.perf_counter()
    qb_live={pid:(q.year2_probability,q.year3_probability) for pid,q in qbstates.items()}
    for pid,e in est.items():
        ps=pstates.get(pid);pos=e.position.value;draft=None if ps is None else ps.draft_number;age=None if ps is None else ps.age_years;exp=None if ps is None else ps.experience_years
        r=cal.Row(pid,2026,pos,e.horizons[0].forecast_mean,0,age,exp,draft,None);cur=cal.state_for(r.points,bounds[pos]);p2=cal.propagate(tm,r,bounds,1,qb_live.get(pid));p3=cal.propagate(tm,r,bounds,2,qb_live.get(pid));v=c2_x(r.points,pos)+cal.DISCOUNT*sum(p2[s]*state_values[(pos,s)] for s in cal.STATE_NAMES)+(cal.DISCOUNT**2)*sum(p3[s]*state_values[(pos,s)] for s in cal.STATE_NAMES);v+=(cal.DISCOUNT**3)*sum(p3[s]*state_values[(pos,s)] for s in cal.STATE_NAMES)*parents[pos];values[pid]=v
        name=players[pid].full_name
        if name in TARGETS:
            ci=cal.sidx(cur);rows.append({'player':name,'position':pos,'current_state':cur,'means':[h.forecast_mean for h in e.horizons],'y2_state_probs':p2,'y3_state_probs':p3,'upward_y2':sum(x for s,x in p2.items() if cal.sidx(s)>ci),'downward_y2':sum(x for s,x in p2.items() if cal.sidx(s)<ci),'survival_y2':1-p2['out'],'state_conditioned_expected_production_y2':sum(p2[s]*state_prod[(pos,s)] for s in cal.STATE_NAMES),'state_conditioned_expected_production_y3':sum(p3[s]*state_prod[(pos,s)] for s in cal.STATE_NAMES),'A_raw':e.fundamental_value,'repaired_D2_raw':v})
    elapsed=time.perf_counter()-t0
    rank={pid:i+1 for i,(pid,v) in enumerate(sorted(values.items(),key=lambda kv:(-kv[1],kv[0])))};arank={e.player_id:i+1 for i,e in enumerate(sorted(inc.estimates,key=lambda x:(-x.fundamental_value,x.player_id)))}
    for r in rows:
        pid=next(pid for pid,p in players.items() if p.full_name==r['player'] and pid in values);r['D2_rank']=rank[pid];r['A_rank']=arank[pid]
    rows.sort(key=lambda r:r['D2_rank'])
    output={'evaluation_as_of':live.evaluation_as_of.isoformat(),'successful_sources':list(live.successful_source_ids),'failed_sources':list(live.failed_sources),'selected_taxonomy':tax,'current_players':rows,'runtime':{'full_pool_n':len(values),'full_pool_seconds':elapsed,'per_player_ms':elapsed*1000/max(1,len(values)),'roster18_estimated_ms':elapsed*1000/max(1,len(values))*18}}
    (a.output_dir/'forecast_career_state_current_sanity.json').write_text(json.dumps(output,indent=2,sort_keys=True));print(json.dumps({'sources':output['successful_sources'],'failed':output['failed_sources'],'current_count':len(rows),'runtime':output['runtime'],'headlines':[{k:r[k] for k in ('player','current_state','A_raw','repaired_D2_raw','A_rank','D2_rank')} for r in rows]},indent=2))

if __name__=='__main__':main()
