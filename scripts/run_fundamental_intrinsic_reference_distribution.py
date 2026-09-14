from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position
from fsffl.value.intrinsic_v2 import intrinsic_display_value

SCENARIOS = ((10, 18), (12, 18), (12, 20), (14, 20))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def distribution(values):
    bands = {
        "below_1000": 0,
        "1000_2500": 0,
        "2500_4500": 0,
        "4500_6500": 0,
        "6500_8000": 0,
        "8000_9200": 0,
        "9200_plus": 0,
    }
    for value in values:
        if value < 1000:
            bands["below_1000"] += 1
        elif value < 2500:
            bands["1000_2500"] += 1
        elif value < 4500:
            bands["2500_4500"] += 1
        elif value < 6500:
            bands["4500_6500"] += 1
        elif value < 8000:
            bands["6500_8000"] += 1
        elif value < 9200:
            bands["8000_9200"] += 1
        else:
            bands["9200_plus"] += 1
    n = max(1, len(values))
    return {key: {"n": count, "share": count / n} for key, count in bands.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--model-a-rows", type=Path, required=True)
    parser.add_argument("--qb-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "intrinsic_reference_parity")
    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "intrinsic_reference_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "intrinsic_reference_v5c")
    examples, structural = parity.build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    fitted = v5c.old_fit(examples, legacy)
    tapers = v5c.fit_tapers(examples)
    by_season = defaultdict(list)
    all_displays = []
    for example in examples:
        _base, _residual, repaired = v5c.new_predict(example, fitted, tapers, legacy)
        factor = structural[example.season][Position(example.position)].relative_pressure
        raw = max(0.0, repaired * factor)
        display = intrinsic_display_value(raw)
        by_season[example.season].append((raw, display))
        all_displays.append(display)

    scenarios = {}
    for teams, roster_size in SCENARIOS:
        capacity = teams * roster_size
        cohort = []
        for season_rows in by_season.values():
            cohort.extend(display for _raw, display in sorted(season_rows, reverse=True)[:capacity])
        scenarios[f"{teams}x{roster_size}"] = {
            "team_count": teams,
            "active_roster_size": roster_size,
            "per_season_capacity": capacity,
            "distribution": distribution(cohort),
        }

    payload = {
        "model_version": "intrinsic-reference-distribution-v1",
        "reference_rule": "team_count * active roster_size; used only for league-specific diagnostic cohort, never to set the 0-10,000 scale",
        "full_population_distribution": distribution(all_displays),
        "league_capacity_scenarios": scenarios,
    }
    out = args.output_dir / "fundamental_intrinsic_reference_distribution.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
