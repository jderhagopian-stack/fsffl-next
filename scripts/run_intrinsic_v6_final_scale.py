from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position

POSITIONS = ("QB", "RB", "WR", "TE")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def q(values, p: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def display(raw: float, apex: float) -> int:
    if raw <= 0.0:
        return 0
    if raw <= apex:
        return min(9500, round(9500.0 * math.sqrt(raw / apex)))
    return min(9999, round(9500.0 + 500.0 * (1.0 - math.exp(-(raw - apex) / apex))))


def bands(values):
    out = {"below_1000": 0, "1000_2500": 0, "2500_4500": 0, "4500_6500": 0, "6500_8000": 0, "8000_9200": 0, "9200_plus": 0}
    for value in values:
        if value < 1000:
            out["below_1000"] += 1
        elif value < 2500:
            out["1000_2500"] += 1
        elif value < 4500:
            out["2500_4500"] += 1
        elif value < 6500:
            out["4500_6500"] += 1
        elif value < 8000:
            out["6500_8000"] += 1
        elif value < 9200:
            out["8000_9200"] += 1
        else:
            out["9200_plus"] += 1
    n = max(1, len(values))
    return {key: {"n": count, "share": count / n} for key, count in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).parent
    parity = load_module(here / "run_fundamental_intrinsic_production_parity.py", "final_scale_parity")
    legacy = load_module(here / "run_fundamental_intrinsic_residual_calibration.py", "final_scale_legacy")
    v5c = load_module(here / "run_fundamental_intrinsic_v5c_calibration.py", "final_scale_v5c")
    audit = load_module(here / "run_intrinsic_structural_audit_fast.py", "final_scale_structural")

    examples, _ = parity.build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    _model, raw_pools = parity.load_model_a(args.model_a_rows)
    forecast_pools, forecast_econ = audit.context_for_pools(raw_pools)
    fitted = v5c.old_fit(examples, legacy)
    tapers = v5c.fit_tapers(examples)

    rows = []
    for e in examples:
        if e.season not in forecast_pools:
            continue
        _base, residual, _repaired = v5c.new_predict(e, fitted, tapers, legacy)
        pos = Position(e.position)
        pool = forecast_pools[e.season][pos]
        demand = forecast_econ[e.season][pos].selected_starters
        cf = v5c.factor(e, tapers)
        plain = max(1e-9, audit.plain_explicit(e, cf))
        residual_ratio = residual / plain
        structural_core = audit.structural_explicit(e, cf, pool, demand, False)
        raw = max(0.0, structural_core * (1.0 + residual_ratio))
        rows.append({"season": e.season, "position": e.position, "raw": raw})

    positive = [row["raw"] for row in rows if row["raw"] > 0.0]
    apex = q(positive, 0.99)
    displayed = [display(row["raw"], apex) for row in rows]
    by_position = {
        position: {
            "n": len([r for r in rows if r["position"] == position]),
            "raw_p50": q([r["raw"] for r in rows if r["position"] == position and r["raw"] > 0], 0.50),
            "raw_p90": q([r["raw"] for r in rows if r["position"] == position and r["raw"] > 0], 0.90),
            "raw_p99": q([r["raw"] for r in rows if r["position"] == position and r["raw"] > 0], 0.99),
        }
        for position in POSITIONS
    }

    by_season = defaultdict(list)
    for row in rows:
        by_season[row["season"]].append(row["raw"])
    reference = {}
    for teams, roster_size in ((10, 18), (12, 18), (12, 20), (14, 20)):
        capacity = teams * roster_size
        cohort = []
        for season_values in by_season.values():
            cohort.extend(sorted(season_values, reverse=True)[:capacity])
        reference[f"{teams}x{roster_size}"] = {
            "capacity": capacity,
            "n": len(cohort),
            "display_distribution": bands([display(raw, apex) for raw in cohort]),
        }

    payload = {
        "model_version": "intrinsic-v6-final-nonlinear-scale-v1",
        "example_count": len(rows),
        "positive_count": len(positive),
        "raw_quantiles": {str(p): q(positive, p) for p in (0.05, 0.20, 0.50, 0.75, 0.90, 0.95, 0.97, 0.99, 0.995, 0.999)},
        "display_apex_raw_p99": apex,
        "display_rule": "9500 * sqrt(raw / positive PIT p99), asymptotic tail to 10000 above p99",
        "full_display_distribution": bands(displayed),
        "league_reference_diagnostics": reference,
        "position_raw_diagnostics": by_position,
        "market_inputs_used": False,
        "league_market_inputs_used": False,
        "team_utility_inputs_used": False,
        "replacement_inputs_used": False,
        "owner_inputs_used": False,
        "transaction_inputs_used": False,
    }
    (args.output_dir / "intrinsic_v6_final_scale.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
