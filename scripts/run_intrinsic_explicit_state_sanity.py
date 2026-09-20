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
from fsffl.state.models import Position
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

TARGETS = {
    "Josh Allen", "Drake Maye", "Lamar Jackson", "Dak Prescott", "Sam Darnold",
    "Bijan Robinson", "Quinshon Judkins", "Derrick Henry", "Rhamondre Stevenson", "Tyler Allgeier", "Jonathon Brooks",
    "CeeDee Lamb", "Jaxon Smith-Njigba", "Tee Higgins", "Zay Flowers", "DeVonta Smith", "KC Concepcion", "Troy Franklin",
    "Brock Bowers", "Trey McBride", "Kyle Pitts", "Dallas Goedert", "Ja'Tavion Sanders",
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


def state_mean_contribution(d, marginal, position, state, samples, baseline):
    vals = samples.get((position, state), ())
    if not vals or state == "out": return 0.0
    return marginal.marginal_at_x(d.mean(vals), baseline[position])


def direct_d_value(d, marginal, position, current_state, y2, y3, state_values, continuation):
    total = state_values[(position, current_state)]
    e2 = sum(y2[s] * state_values[(position, s)] for s in d.STATE_NAMES)
    e3 = sum(y3[s] * state_values[(position, s)] for s in d.STATE_NAMES)
    return total + d.DISCOUNT * e2 + (d.DISCOUNT ** 2) * e3 + (d.DISCOUNT ** 3) * e3 * continuation


def probs(**kwargs):
    out = {s: 0.0 for s in ("out","depth","usable","starter","premium","elite")}
    out.update(kwargs)
    assert abs(sum(out.values()) - 1.0) < 1e-9
    return out


def rank_map(values):
    rows = sorted(values.items(), key=lambda kv:(kv[1],kv[0])); n=len(rows)
    return {pid:(i+.5)/n for i,(pid,_v) in enumerate(rows)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--career-panel',type=Path,required=True)
    ap.add_argument('--model-a-rows',type=Path,required=True)
    ap.add_argument('--qb-results',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).parent
    d=load(root/'run_intrinsic_explicit_state_challenge.py','d_sanity')
    marginal=load(root/'run_intrinsic_marginal_franchise_challenge.py','d_sanity_marginal')
    legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','d_sanity_legacy')
    parity=load(root/'run_fundamental_intrinsic_production_parity.py','d_sanity_parity')
    current=load(root/'_tmp_current_marginal_franchise_sanity.py','d_sanity_current')

    d.state_contribution=lambda position,state,samples,baseline,marginal_module: state_mean_contribution(d,marginal_module,position,state,samples,baseline)

    panel=legacy.load_rows(args.career_panel)
    examples,_=parity.build_examples(panel_path=args.career_panel,model_rows_path=args.model_a_rows,qb_results_path=args.qb_results,legacy=legacy)
    historical_qb=parity.load_qb_probabilities(args.qb_results)
    _pools,hist_baselines,_=marginal.contexts_from_forecasts(parity,args.model_a_rows)
    _,actual_baselines=marginal.contexts_from_actual(panel)
    seasons=sorted({e.season for e in examples if e.season in hist_baselines})
    contexts=d.build_fold_contexts(panel,hist_baselines,seasons)
    targets=d.hard_targets(examples,panel,actual_baselines,marginal)
    parents,cells=d.fit_d_continuation(examples,targets,contexts,historical_qb,marginal)

    state=current.build_state(); live=build_current_live_forecasts(state,minimum_independent_sources=2)
    state=state.model_copy(update={'as_of':live.evaluation_as_of,'player_states':tuple(ps.model_copy(update={'as_of':live.evaluation_as_of}) for ps in state.player_states)})
    bounded=build_non_qb_bounded_paths(state,season_forecasts=live.fantasy_point_forecasts)
    qb_states=build_qb_career_state_forecasts(state,season_forecasts=live.fantasy_point_forecasts)
    inc=build_current_intrinsic_values_v2(state,season_forecasts=live.fantasy_point_forecasts,base_forecast_model_version=live.model_version,bounded_paths=bounded,qb_career_states=qb_states)
    est={e.player_id:e for e in inc.estimates}; players={p.player_id:p for p in state.players}; pstates={s.player_id:s for s in state.player_states}
    pools={p:tuple(sorted(max(0.0,e.horizons[0].forecast_mean) for e in inc.estimates if e.position==p)) for p in (Position.QB,Position.RB,Position.WR,Position.TE)}
    baseline,_=marginal.baselines_from_pools(pools)
    boundaries=d.fit_state_boundaries(panel,2026); transitions=d.fit_transition_counts(panel,2026,boundaries); samples=d.empirical_state_samples(panel,2026,boundaries)
    current_context={2026:(boundaries,transitions,samples,baseline)}
    qbp={(2026,pid):(q.year2_probability,q.year3_probability) for pid,q in qb_states.items()}

    dvals={}; rows=[]
    t0=time.perf_counter()
    for pid,e in est.items():
        ps=pstates.get(pid); pos=e.position.value
        ex=SimpleNamespace(season=2026,player_id=pid,position=pos,age=None if ps is None else ps.age_years,experience=None if ps is None else ps.experience_years,means=tuple(h.forecast_mean for h in e.horizons),sds=tuple(h.forecast_stddev for h in e.horizons))
        val,state_probs=d.d_predict(ex,current_context,qbp,marginal,parents,cells); dvals[pid]=val
        if players[pid].full_name in TARGETS:
            cur=d.state_for_points(ex.means[0],boundaries[pos]); ci=d.state_index(cur)
            up2=sum(p for s,p in state_probs[2].items() if d.state_index(s)>ci); down2=sum(p for s,p in state_probs[2].items() if d.state_index(s)<ci)
            starter2=sum(state_probs[2][s] for s in d.MEANINGFUL_STATES); starter3=sum(state_probs[3][s] for s in d.MEANINGFUL_STATES)
            rows.append({'player':players[pid].full_name,'position':pos,'current_state':cur,'means':ex.means,'sds':ex.sds,'y2_state_probs':state_probs[2],'y3_state_probs':state_probs[3],'upward_y2':up2,'role_loss_y2':down2,'meaningful_occupancy_y2':starter2,'meaningful_occupancy_y3':starter3,'A_raw':e.fundamental_value,'D_raw':val})
    elapsed=time.perf_counter()-t0
    dr=rank_map(dvals); ar=rank_map({pid:e.fundamental_value for pid,e in est.items()})
    for r in rows:
        pid=next(pid for pid,p in players.items() if p.full_name==r['player'] and pid in est)
        r['A_rank_percentile']=ar[pid]; r['D_rank_percentile']=dr[pid]
    rows.sort(key=lambda r:(-r['D_raw'],r['player']))

    state_values={(pos,s):state_mean_contribution(d,marginal,pos,s,samples,baseline) for pos in d.POSITIONS for s in d.STATE_NAMES}
    qbcf=parents['QB']; wrcf=parents['WR']; tecf=parents['TE']; rbcf=parents['RB']
    synth={
      'stable_starting_qb':direct_d_value(d,marginal,'QB','starter',probs(out=.05,depth=.05,usable=.10,starter=.45,premium=.25,elite=.10),probs(out=.08,depth=.07,usable=.10,starter=.43,premium=.22,elite=.10),state_values,qbcf),
      'high_variance_backup_weak_path':direct_d_value(d,marginal,'QB','depth',probs(out=.35,depth=.35,usable=.20,starter=.08,premium=.015,elite=.005),probs(out=.40,depth=.30,usable=.15,starter=.11,premium=.03,elite=.01),state_values,qbcf),
      'developmental_qb_real_path':direct_d_value(d,marginal,'QB','depth',probs(out=.15,depth=.20,usable=.15,starter=.25,premium=.17,elite=.08),probs(out=.12,depth=.13,usable=.10,starter=.25,premium=.25,elite=.15),state_values,qbcf),
      'wr_strong_upward_path':direct_d_value(d,marginal,'WR','usable',probs(out=.10,depth=.12,usable=.20,starter=.28,premium=.20,elite=.10),probs(out=.10,depth=.10,usable=.15,starter=.25,premium=.25,elite=.15),state_values,wrcf),
      'wr_weak_upward_path':direct_d_value(d,marginal,'WR','usable',probs(out=.25,depth=.30,usable=.30,starter=.12,premium=.025,elite=.005),probs(out=.30,depth=.30,usable=.25,starter=.12,premium=.025,elite=.005),state_values,wrcf),
      'elite_young_te':direct_d_value(d,marginal,'TE','elite',probs(out=.03,depth=.02,usable=.05,starter=.15,premium=.25,elite=.50),probs(out=.05,depth=.03,usable=.07,starter=.15,premium=.25,elite=.45),state_values,tecf),
      'fringe_te':direct_d_value(d,marginal,'TE','depth',probs(out=.60,depth=.28,usable=.09,starter=.025,premium=.004,elite=.001),probs(out=.68,depth=.22,usable=.075,starter=.02,premium=.004,elite=.001),state_values,tecf),
      'aging_productive_rb':direct_d_value(d,marginal,'RB','premium',probs(out=.12,depth=.08,usable=.12,starter=.25,premium=.30,elite=.13),probs(out=.25,depth=.12,usable=.15,starter=.25,premium=.18,elite=.05),state_values,rbcf),
    }

    def format_probe(team_count,direct,flex,sf,pos,state_name):
        b,_=marginal.baselines_from_pools(pools,team_count=team_count,direct=direct,flex=flex,superflex=sf)
        return state_mean_contribution(d,marginal,pos,state_name,samples,b)
    standard={Position.QB:1,Position.RB:2,Position.WR:3,Position.TE:1}; two_te=dict(standard);two_te[Position.TE]=2
    fmt={
      'elite_qb_1qb_12':format_probe(12,standard,1,0,'QB','elite'),
      'elite_qb_sf_12':format_probe(12,standard,1,1,'QB','elite'),
      'elite_qb_sf_10':format_probe(10,standard,1,1,'QB','elite'),
      'elite_qb_sf_14':format_probe(14,standard,1,1,'QB','elite'),
      'elite_te_1te':format_probe(12,standard,1,1,'TE','elite'),
      'elite_te_2te':format_probe(12,two_te,1,1,'TE','elite'),
    }
    payload={'evaluation_as_of':live.evaluation_as_of.isoformat(),'sources':list(live.successful_source_ids),'failed_sources':list(live.failed_sources),'full_pool_n':len(inc.estimates),'current_players':rows,'synthetic_D':synth,'format_sensitivity_D':fmt,'runtime':{'full_pool_seconds':elapsed,'per_player_ms':1000*elapsed/max(1,len(inc.estimates)),'roster18_estimated_ms':1000*elapsed/max(1,len(inc.estimates))*18},'continuation':{'parents':parents,'cells':{f'{p}:{b}':v for (p,b),v in cells.items()}},'state_values':{f'{p}:{s}':v for (p,s),v in state_values.items()}}
    (args.output_dir/'intrinsic_explicit_state_sanity.json').write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'synthetic_D':synth,'runtime':payload['runtime'],'format_sensitivity_D':fmt,'current_count':len(rows)},indent=2,sort_keys=True))

if __name__=='__main__': main()
