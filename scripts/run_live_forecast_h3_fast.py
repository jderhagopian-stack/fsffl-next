from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--career-panel', type=Path, required=True)
    ap.add_argument('--usage-panel', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args(); a.output_dir.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).parent
    ltc = load(here / 'run_live_forecast_horizon_research.py', 'h3_ltc')
    im = load(here / 'run_integrated_multivariate_forecast.py', 'h3_im')
    pf = load(here / 'run_persistence_first_forecast_calibration.py', 'h3_pf')
    prior = load(here / 'run_forecast_low_end_career_calibration.py', 'h3_prior')
    legacy = load(here / 'run_fundamental_intrinsic_residual_calibration.py', 'h3_legacy')
    base = load(here / 'run_intrinsic_explicit_state_challenge.py', 'h3_base')
    evt = load(here / 'reconstruct_event_time_absence_cause_evidence.py', 'h3_evt')

    panel = legacy.load_rows(a.career_panel)
    by = {(r.player_id, r.season): r for r in panel}
    usage = pf.load_usage(a.usage_panel)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))

    rows=[]; coverage=[]
    for y in ltc.SELECTION_SEASONS:
        r,cov=ltc.test_fold(im,pf,prior,base,panel,by,usage,ev,y,3)
        rows.extend(r); coverage.append(cov)

    pd.DataFrame(rows).to_csv(a.output_dir/'h3_selection_rows.csv', index=False)
    pd.DataFrame(coverage).to_csv(a.output_dir/'h3_selection_coverage.csv', index=False)
    result={
        'mode':'selection-h3-fast-shard',
        'architecture':'I1-direct-h3',
        'C':ltc.C,
        'source_seasons':list(ltc.SELECTION_SEASONS),
        'strict_cutoff':'training source + 3 < evaluation source season',
        'summary':ltc.summarize(rows),
        'fold_deltas':ltc.season_deltas(rows),
        'coverage':coverage,
        'candidate_paths':dict(Counter(r['i1_path'] for r in rows)),
        'baseline_paths':dict(Counter(r['baseline_path'] for r in rows)),
    }
    (a.output_dir/'h3_selection_results.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'baseline':result['summary']['baseline'], 'i1':result['summary']['i1'], 'fold_deltas':result['fold_deltas']}, indent=2))

if __name__ == '__main__': main()
