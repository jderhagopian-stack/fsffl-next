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


def deterministic(baselines):
    return {
        season: {
            pos: ((sum(value * prob for value, prob in dist), 1.0),)
            for pos, dist in by_pos.items()
        }
        for season, by_pos in baselines.items()
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--career-panel', type=Path, required=True)
    ap.add_argument('--model-a-rows', type=Path, required=True)
    ap.add_argument('--qb-results', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args(); a.output_dir.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).parent
    ch = load(here/'run_intrinsic_marginal_franchise_challenge.py', 'frontier_challenge')
    parity = load(here/'run_fundamental_intrinsic_production_parity.py', 'frontier_parity')
    legacy = load(here/'run_fundamental_intrinsic_residual_calibration.py', 'frontier_legacy')
    v5c = load(here/'run_fundamental_intrinsic_v5c_calibration.py', 'frontier_v5c')
    structural = load(here/'run_intrinsic_structural_audit_fast.py', 'frontier_structural')
    examples, _ = parity.build_examples(panel_path=a.career_panel, model_rows_path=a.model_a_rows, qb_results_path=a.qb_results, legacy=legacy)
    pools, stochastic_forecast, _layers = ch.contexts_from_forecasts(parity, a.model_a_rows)
    forecast = deterministic(stochastic_forecast)
    econ = {}
    for season, season_pools in pools.items():
        _, e = structural.context_for_pools({season: season_pools}); econ[season] = e[season]
    panel = legacy.load_rows(a.career_panel); panel_by_key = {(r.player_id,r.season):r for r in panel}
    _, stochastic_actual = ch.contexts_from_actual(panel); actual = deterministic(stochastic_actual)
    targets = {id(e): ch.realized_marginal_target(e, panel_by_key, actual) for e in examples}
    rows = ch.evaluate(examples, pools, forecast, econ, targets, legacy, v5c)
    metrics = ch.compare_metrics(rows)
    payload = {
        'model_version':'intrinsic-format-normalized-marginal-frontier-followup-v1',
        'baseline':'expected neutral weakest-eligible starter frontier (single deterministic baseline per position-season)',
        'historical_validation':metrics,
        'example_count':len(examples),
        'holdout_rows':len(rows),
        'independence':{'market':False,'owner':False,'team_roster':False,'transactions':False},
    }
    out=a.output_dir/'intrinsic_marginal_frontier_followup.json';out.write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=='__main__':main()
