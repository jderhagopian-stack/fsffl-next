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
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--career-panel', type=Path, required=True)
    ap.add_argument('--model-a-rows', type=Path, required=True)
    ap.add_argument('--qb-results', type=Path, required=True)
    ap.add_argument('--calibration-json', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent
    cal = load(root / 'run_forecast_career_state_calibration.py', 'strict_cal')
    legacy = load(root / 'run_fundamental_intrinsic_residual_calibration.py', 'strict_legacy')
    parity = load(root / 'run_fundamental_intrinsic_production_parity.py', 'strict_parity')
    rows = cal.load_rows(args.career_panel)
    examples, _ = parity.build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    qb_probs = parity.load_qb_probabilities(args.qb_results)
    selected = json.loads(args.calibration_json.read_text(encoding='utf-8'))['selected_taxonomy']
    by_key = {(r.player_id, r.season): r for r in rows}
    strict_preds = []
    per_position = {p: [] for p in cal.POSITIONS}
    per_age = {'young': [], 'prime': [], 'aging': []}
    per_exp = {'rookie': [], '1-2': [], '3-5': [], '6+': []}
    folds = {}
    for season in cal.FOLDS:
        train = [e for e in examples if e.season <= season - 6]
        test = [e for e in examples if e.season == season]
        if len(train) < 400 or not test:
            continue
        bounds = cal.taxonomy_boundaries(rows, season, selected)
        model = cal.TransitionModel(rows, season, bounds)
        fold_preds = []
        for e in test:
            actual = by_key.get((e.player_id, e.season + 1))
            if actual is None:
                continue
            # Use the exact D2 evaluation population but retain PIT player metadata
            # for Forecast calibration features where available.
            hist = by_key.get((e.player_id, e.season))
            r = cal.Row(
                e.player_id,
                e.season,
                e.position,
                e.means[0],
                actual.points,
                e.age,
                e.experience,
                None if hist is None else hist.draft_pick,
                None if hist is None else hist.prior_pct,
            )
            p = cal.propagate(model, r, bounds, 1, qb_probs.get((e.season, e.player_id)))
            item = (r, p, bounds)
            strict_preds.append(item)
            fold_preds.append(item)
            per_position[e.position].append(item)
            per_age[cal.age_band(e.position, e.age)].append(item)
            per_exp[cal.exp_band(e.experience)].append(item)
        folds[str(season)] = cal.calibration([x[0] for x in fold_preds], fold_preds)
    overall = cal.calibration([x[0] for x in strict_preds], strict_preds)
    output = {
        'selected_taxonomy': selected,
        'strict_population': 'exact chronological D2 evaluation examples with observed next-season state',
        'overall': overall,
        'by_position': {k: cal.calibration([x[0] for x in v], v) for k, v in per_position.items() if v},
        'by_age': {k: cal.calibration([x[0] for x in v], v) for k, v in per_age.items() if v},
        'by_experience': {k: cal.calibration([x[0] for x in v], v) for k, v in per_exp.items() if v},
        'folds': folds,
    }
    (args.output_dir / 'forecast_career_state_strict_compare.json').write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding='utf-8'
    )
    print(json.dumps({
        'n': overall['n'],
        'brier': overall['brier'],
        'log_loss': overall['log_loss'],
        'up_pred': overall['up_pred'],
        'up_obs': overall['up_obs'],
        'down_pred': overall['down_pred'],
        'down_obs': overall['down_obs'],
        'persist_pred': overall['persist_pred'],
        'persist_obs': overall['persist_obs'],
        'by_position': {k: {'n': v['n'], 'up_pred': v['up_pred'], 'up_obs': v['up_obs'], 'down_pred': v['down_pred'], 'down_obs': v['down_obs']} for k, v in output['by_position'].items()},
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
