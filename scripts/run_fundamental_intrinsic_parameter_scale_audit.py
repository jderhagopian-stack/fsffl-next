from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position

REALIZED_HORIZON = 6
MIN_TRAIN_EXAMPLES = 400
MIN_CELL_EXAMPLES = 30
POSITIONS = ("QB", "RB", "WR", "TE")
DISCOUNT_CHALLENGERS = (0.80, 0.85, 0.90)
AGE_SCHEMES = {
    "earlier": (22, 25, 28),
    "current": (23, 26, 29),
    "later": (24, 27, 30),
}


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


def band_for(age: float | None, scheme: tuple[int, int, int]) -> str:
    if age is None:
        return "unknown"
    young_max, prime_max, veteran_max = scheme
    if age <= young_max:
        return "young"
    if age <= prime_max:
        return "prime"
    if age <= veteran_max:
        return "veteran"
    return "late"


def three(example, discount: float) -> float:
    return sum((discount**i) * max(0.0, m) for i, m in enumerate(example.means))


def xterm(example, discount: float) -> float:
    return (discount**3) * max(0.0, example.means[2])


def realized(example, discount: float, points_by_key) -> float:
    return sum(
        (discount**offset) * points_by_key.get((example.player_id, example.season + offset), 0.0)
        for offset in range(REALIZED_HORIZON)
    )


def slope(examples, discount: float, points_by_key) -> float:
    xs = [xterm(e, discount) for e in examples]
    ys = [max(0.0, realized(e, discount, points_by_key) - three(e, discount)) for e in examples]
    denominator = sum(x * x for x in xs)
    if denominator <= 1e-9:
        return 0.0
    return max(0.0, sum(x * y for x, y in zip(xs, ys, strict=True)) / denominator)


def fit_bucket_factors(training, discount: float, scheme, points_by_key):
    parent = {p: slope([e for e in training if e.position == p], discount, points_by_key) for p in POSITIONS}
    cells = {}
    counts = {}
    for position in ("RB", "WR", "TE"):
        for band in ("veteran", "late"):
            subset = [e for e in training if e.position == position and band_for(e.age, scheme) == band]
            counts[f"{position}:{band}"] = len(subset)
            if len(subset) >= MIN_CELL_EXAMPLES:
                cells[f"{position}:{band}"] = slope(subset, discount, points_by_key)
    return parent, cells, counts


def bucket_factor(example, fitted, scheme):
    parent, cells, _counts = fitted
    if example.position in ("RB", "WR", "TE"):
        key = f"{example.position}:{band_for(example.age, scheme)}"
        if key in cells:
            return cells[key]
    return parent[example.position]


def fit_smooth_factors(training, discount: float, points_by_key):
    parent = {p: slope([e for e in training if e.position == p], discount, points_by_key) for p in POSITIONS}
    smooth = {}
    for position in ("RB", "WR", "TE"):
        rows = [e for e in training if e.position == position and e.age is not None and xterm(e, discount) > 0.0]
        s00 = s01 = s11 = t0 = t1 = 0.0
        for e in rows:
            x = xterm(e, discount)
            z = max(0.0, float(e.age) - 26.0)
            y = max(0.0, realized(e, discount, points_by_key) - three(e, discount))
            a0, a1 = x, x * z
            s00 += a0 * a0
            s01 += a0 * a1
            s11 += a1 * a1
            t0 += a0 * y
            t1 += a1 * y
        ridge = 1e-6
        determinant = (s00 + ridge) * (s11 + ridge) - s01 * s01
        if determinant <= 1e-9:
            smooth[position] = (parent[position], 0.0)
        else:
            intercept = (t0 * (s11 + ridge) - t1 * s01) / determinant
            age_slope = ((s00 + ridge) * t1 - s01 * t0) / determinant
            smooth[position] = (max(0.0, intercept), age_slope)
    return parent, smooth


def smooth_factor(example, fitted):
    parent, smooth = fitted
    if example.position == "QB" or example.age is None:
        return parent[example.position]
    intercept, age_slope = smooth[example.position]
    return max(0.0, intercept + age_slope * max(0.0, float(example.age) - 26.0))


def evaluate_scheme(examples, *, discount: float, points_by_key, scheme_name: str):
    rows = []
    scheme = AGE_SCHEMES.get(scheme_name)
    for holdout in sorted({e.season for e in examples}):
        training = [e for e in examples if e.season <= holdout - REALIZED_HORIZON]
        test = [e for e in examples if e.season == holdout]
        if len(training) < MIN_TRAIN_EXAMPLES or not test:
            continue
        if scheme_name == "smooth":
            fitted = fit_smooth_factors(training, discount, points_by_key)
        else:
            fitted = fit_bucket_factors(training, discount, scheme, points_by_key)
        for e in test:
            factor = smooth_factor(e, fitted) if scheme_name == "smooth" else bucket_factor(e, fitted, scheme)
            prediction = three(e, discount) + xterm(e, discount) * factor
            target = realized(e, discount, points_by_key)
            rows.append((holdout, e.position, abs(prediction - target), target))
    by_fold = defaultdict(list)
    by_position = defaultdict(list)
    for season, position, error, target in rows:
        by_fold[season].append((error, target))
        by_position[position].append((error, target))
    mae = mean(error for _season, _position, error, _target in rows)
    mean_target = mean(target for _season, _position, _error, target in rows)
    return {
        "n": len(rows),
        "folds": len(by_fold),
        "mae": mae,
        "normalized_mae": mae / mean_target if mean_target > 0 else math.nan,
        "position": {
            p: {
                "mae": mean(error for error, _target in by_position[p]),
                "normalized_mae": mean(error for error, _target in by_position[p]) / mean(target for _error, target in by_position[p]),
            }
            for p in POSITIONS if by_position[p]
        },
        "fold_normalized_mae": {
            str(season): mean(error for error, _target in vals) / mean(target for _error, target in vals)
            for season, vals in by_fold.items()
        },
    }


def fold_wins(challenger, incumbent):
    common = sorted(set(challenger["fold_normalized_mae"]) & set(incumbent["fold_normalized_mae"]))
    return sum(challenger["fold_normalized_mae"][fold] < incumbent["fold_normalized_mae"][fold] for fold in common), len(common)


def display_piecewise(raw: float, anchors) -> int:
    if raw <= 0.0:
        return 0
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if raw <= x1:
            return round(y0 + (raw - x0) / (x1 - x0) * (y1 - y0))
    x0, y0 = anchors[-1]
    return min(9999, round(y0 + (10000 - y0) * (1.0 - math.exp(-(raw - x0) / max(1.0, x0)))))


def display_linear_apex(raw: float, apex_raw: float) -> int:
    if raw <= 0.0 or apex_raw <= 0.0:
        return 0
    if raw <= apex_raw:
        return min(9500, round(9500.0 * raw / apex_raw))
    return min(9999, round(9500 + 500 * (1.0 - math.exp(-(raw - apex_raw) / apex_raw))))


def band_distribution(values):
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

    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "intrinsic_parameter_audit_parity")
    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "intrinsic_parameter_audit_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "intrinsic_parameter_audit_v5c")
    examples, structural = parity.build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    panel = legacy.load_rows(args.career_panel)
    points_by_key = {(row.player_id, row.season): row.points for row in panel}

    discount_results = {
        str(discount): evaluate_scheme(examples, discount=discount, points_by_key=points_by_key, scheme_name="current")
        for discount in DISCOUNT_CHALLENGERS
    }
    incumbent_discount = discount_results["0.85"]
    discount_fold_wins = {
        key: {"wins_vs_0.85": fold_wins(value, incumbent_discount)[0], "folds": fold_wins(value, incumbent_discount)[1]}
        for key, value in discount_results.items()
        if key != "0.85"
    }

    age_results = {
        name: evaluate_scheme(examples, discount=0.85, points_by_key=points_by_key, scheme_name=name)
        for name in ("earlier", "current", "later", "smooth")
    }
    incumbent_age = age_results["current"]
    age_fold_wins = {
        name: {"wins_vs_current": fold_wins(result, incumbent_age)[0], "folds": fold_wins(result, incumbent_age)[1]}
        for name, result in age_results.items()
        if name != "current"
    }

    fitted = v5c.old_fit(examples, legacy)
    tapers = v5c.fit_tapers(examples)
    records = []
    by_season = defaultdict(list)
    for e in examples:
        _base, _residual, repaired = v5c.new_predict(e, fitted, tapers, legacy)
        structural_factor = structural[e.season][Position(e.position)].relative_pressure
        raw = max(0.0, repaired * structural_factor)
        records.append((e.season, e.position, raw))
        by_season[e.season].append(raw)

    # Existing policy is included only as the incumbent comparator. Its 216-player
    # reference is intentionally audited rather than treated as universal truth.
    old_reference = []
    for season_rows in by_season.values():
        old_reference.extend(sorted(season_rows, reverse=True)[:216])
    old_anchors = [
        (0.0, 0),
        (q(old_reference, 0.05), 1000),
        (q(old_reference, 0.20), 3000),
        (q(old_reference, 0.50), 5000),
        (q(old_reference, 0.75), 6500),
        (q(old_reference, 0.90), 8000),
        (q(old_reference, 0.97), 9000),
        (q(old_reference, 0.99), 9500),
    ]

    positive = [raw for _season, _position, raw in records if raw > 0.0]
    apex_p99 = q(positive, 0.99)
    apex_p995 = q(positive, 0.995)
    scale_candidates = {
        "incumbent_quantile_policy": {
            "definition": "top 216 PIT economic assets per season mapped by presentation quantiles",
            "distribution_full": band_distribution([display_piecewise(raw, old_anchors) for _season, _position, raw in records]),
            "distribution_incumbent_reference": band_distribution([display_piecewise(raw, old_anchors) for raw in old_reference]),
        },
        "linear_all_positive_p99": {
            "definition": "linear economic magnitude: 9,500 equals all-positive PIT economic-raw p99; asymptotic tail above",
            "apex_raw": apex_p99,
            "distribution_full": band_distribution([display_linear_apex(raw, apex_p99) for _season, _position, raw in records]),
        },
        "linear_all_positive_p995": {
            "definition": "linear economic magnitude: 9,500 equals all-positive PIT economic-raw p99.5; asymptotic tail above",
            "apex_raw": apex_p995,
            "distribution_full": band_distribution([display_linear_apex(raw, apex_p995) for _season, _position, raw in records]),
        },
    }

    # Reference-size sensitivity is diagnostic only. It demonstrates how the
    # old percentile policy changes merely because roster capacity changes.
    capacity_scenarios = {}
    for teams, roster_size in ((10, 18), (12, 18), (12, 20), (14, 20)):
        reference = []
        capacity = teams * roster_size
        for season_rows in by_season.values():
            reference.extend(sorted(season_rows, reverse=True)[:capacity])
        capacity_scenarios[f"{teams}x{roster_size}"] = {
            "capacity": capacity,
            "raw_p20": q(reference, 0.20),
            "raw_p50": q(reference, 0.50),
            "raw_p90": q(reference, 0.90),
            "raw_p99": q(reference, 0.99),
        }

    payload = {
        "audit_version": "fundamental-intrinsic-v6-parameter-scale-audit-v1",
        "example_count": len(examples),
        "discount": {
            "classification": "policy-defined; not identifiable as a time-preference coefficient from football outcomes alone",
            "challengers": discount_results,
            "fold_wins": discount_fold_wins,
        },
        "age_boundaries": {
            "classification": "modeling structure challenged on chronological football evidence",
            "schemes": {name: AGE_SCHEMES.get(name, "continuous from age 26") for name in age_results},
            "results": age_results,
            "fold_wins": age_fold_wins,
        },
        "display_scale": {
            "classification": "presentation-only monotonic translation of final economic raw",
            "positive_pit_count": len(positive),
            "all_positive_raw_quantiles": {str(p): q(positive, p) for p in (0.05, 0.20, 0.50, 0.75, 0.90, 0.95, 0.97, 0.99, 0.995, 0.999)},
            "candidates": scale_candidates,
            "old_reference_capacity_sensitivity": capacity_scenarios,
        },
        "input_classification": {
            "empirically_fitted": ["post-Y3 continuation slopes", "pedigree residualizer/coefficient", "non-QB career-transition evidence upstream in Forecast"],
            "rule_formula_derived": ["lineup starter demand", "FLEX/SUPERFLEX eligibility", "production-concentration effective supply", "relative starter pressure structural factor"],
            "policy_defined": ["0.85 future discount", "age-band breakpoint structure unless challenger promoted"],
            "presentation_only": ["0-10,000 mapping"],
        },
        "market_inputs_used": False,
        "league_market_inputs_used": False,
        "replacement_inputs_used": False,
        "team_utility_inputs_used": False,
        "owner_inputs_used": False,
        "transaction_inputs_used": False,
    }
    output = args.output_dir / "fundamental_intrinsic_parameter_scale_audit.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
