from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.forecast.career import build_multi_year_forecast
from fsffl.forecast.models import ForecastDistribution
from fsffl.forecast.non_qb_career_state import _transition
from fsffl.state.models import Position
from fsffl.value.intrinsic_economics import structural_position_economics

DISCOUNT = 0.85
REALIZED_HORIZON = 6
MIN_TRAIN_EXAMPLES = 400
POSITIONS = ("QB", "RB", "WR", "TE")
MODEL_VERSION = "fundamental-intrinsic-production-parity-v1"
CANONICAL_TEAM_COUNT = 12
CANONICAL_ROSTER_SIZE = 18
CANONICAL_DIRECT = {Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1}
CANONICAL_FLEX = 1
CANONICAL_SUPERFLEX = 1


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def q(values, p):
    xs = sorted(values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def mean(values):
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def load_model_a(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    grouped = defaultdict(dict)
    pools = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = (int(row["target_season"]), row["asset_id"])
        offset = int(row["season_offset"])
        grouped[key][offset] = row
        if offset == 0 and row["position"] in POSITIONS:
            pools[int(row["target_season"])][Position(row["position"])].append(max(0.0, float(row["player_forecast_mean"])))
    return grouped, pools


def load_qb_probabilities(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in payload.get("records", []):
        result[(int(row["source_season"]), row["player_id"])] = (float(row["prob_y2"]), float(row["prob_y3"]))
    return result


def build_examples(*, panel_path: Path, model_rows_path: Path, qb_results_path: Path, legacy):
    panel = legacy.load_rows(panel_path)
    by_key = {(row.player_id, row.season): row for row in panel}
    model, pools = load_model_a(model_rows_path)
    qb_probs = load_qb_probabilities(qb_results_path)
    examples = []
    structural_by_season = {}

    for season, position_pools in pools.items():
        structural_by_season[season] = structural_position_economics(
            team_count=CANONICAL_TEAM_COUNT,
            direct_slots=CANONICAL_DIRECT,
            flex_slots=CANONICAL_FLEX,
            superflex_slots=CANONICAL_SUPERFLEX,
            forecast_means=position_pools,
        )

    for (season, player_id), horizons in sorted(model.items()):
        if 0 not in horizons or horizons[0]["position"] not in POSITIONS:
            continue
        prior = by_key.get((player_id, season - 1))
        if prior is None:
            continue
        base = ForecastDistribution(
            mean=max(0.0, float(horizons[0]["player_forecast_mean"])),
            stddev=max(0.0, float(horizons[0]["player_forecast_stddev"])),
        )
        position = Position(horizons[0]["position"])
        age = None if prior.age is None else prior.age + 1
        experience = prior.experience + 1
        means = [base.mean]
        sds = [base.stddev]
        survival = 1.0

        if position == Position.QB:
            probs = qb_probs.get((season, player_id))
            if probs is None:
                means.extend((base.mean, base.mean))
                sds.extend((base.stddev, base.stddev))
            else:
                p2, p3 = probs
                means.extend((base.mean * p2, base.mean * p3))
                sds.extend((base.stddev, base.stddev))
                survival = p2
        else:
            if age is None:
                continue
            bounded = build_multi_year_forecast(base, (_transition(position, float(age)), _transition(position, float(age) + 1.0)))
            b2, b3 = bounded
            survival = b2.cumulative_survival_probability
            if position == Position.WR:
                means.extend((base.mean, b3.distribution.mean))
                sds.extend((max(base.stddev, b2.distribution.stddev), b3.distribution.stddev))
            else:
                means.extend((b2.distribution.mean, b3.distribution.mean))
                sds.extend((b2.distribution.stddev, b3.distribution.stddev))

        realized = 0.0
        for offset in range(REALIZED_HORIZON):
            actual = by_key.get((player_id, season + offset))
            realized += (DISCOUNT**offset) * (actual.points if actual is not None else 0.0)
        examples.append(
            legacy.Example(
                season=season,
                player_id=player_id,
                position=position.value,
                age=age,
                experience=experience,
                pedigree=legacy.pedigree_score(prior.draft_pick),
                survival=survival,
                means=tuple(means),
                sds=tuple(sds),
                realized=realized,
            )
        )
    return examples, structural_by_season


def economic_validation(examples, structural_by_season, legacy, v5c):
    rows = []
    for holdout in sorted({e.season for e in examples}):
        training = [e for e in examples if e.season <= holdout - REALIZED_HORIZON]
        test = [e for e in examples if e.season == holdout]
        if len(training) < MIN_TRAIN_EXAMPLES or not test:
            continue
        fitted = v5c.old_fit(training, legacy)
        tapers = v5c.fit_tapers(training)
        factors = structural_by_season[holdout]
        for e in test:
            _old_base, _old_residual, old_raw = v5c.old_parts_raw(e, fitted, legacy)
            _new_base, _new_residual, new_raw = v5c.new_predict(e, fitted, tapers, legacy)
            factor = factors[Position(e.position)].relative_pressure
            target = e.realized * factor
            rows.append({
                "season": holdout,
                "position": e.position,
                "old": old_raw * factor,
                "new": new_raw * factor,
                "target": target,
                "old_error": abs(old_raw * factor - target),
                "new_error": abs(new_raw * factor - target),
            })
    folds = defaultdict(list)
    by_pos = defaultdict(list)
    for row in rows:
        folds[row["season"]].append(row)
        by_pos[row["position"]].append(row)
    old_mae = mean(row["old_error"] for row in rows)
    new_mae = mean(row["new_error"] for row in rows)
    return {
        "n": len(rows),
        "folds": len(folds),
        "fold_wins": sum(mean(r["new_error"] for r in fold) < mean(r["old_error"] for r in fold) for fold in folds.values()),
        "old_mae": old_mae,
        "new_mae": new_mae,
        "mae_gain": (old_mae - new_mae) / old_mae if old_mae > 0 else 0.0,
        "position": {
            p: {
                "old_mae": mean(r["old_error"] for r in by_pos[p]),
                "new_mae": mean(r["new_error"] for r in by_pos[p]),
            }
            for p in POSITIONS if by_pos[p]
        },
    }


def continuation_diagnostics(examples, v5c):
    output = {}
    for position in ("RB", "WR", "TE"):
        for band in ("young", "prime", "veteran", "late"):
            subset = [e for e in examples if e.position == position and v5c.age_band(position, e.age) == band]
            if not subset:
                continue
            weighted = [e for e in subset if v5c.xterm(e) > 0.0]
            output[f"{position}:{band}"] = {
                "n": len(subset),
                "positive_y3_n": len(weighted),
                "mean_y3": mean(e.means[2] for e in subset),
                "mean_realized_tail": mean(max(0.0, e.realized - v5c.three(e)) for e in subset),
                "continuation_slope": v5c.slope(subset),
            }
    return output


def display_value(raw: float, anchors):
    if raw <= 0.0:
        return 0
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if raw <= x1:
            return round(y0 + (raw - x0) / (x1 - x0) * (y1 - y0))
    x0, y0 = anchors[-1]
    tail = y0 + (10000 - y0) * (1.0 - math.exp(-(raw - x0) / max(1.0, x0)))
    return min(9999, round(tail))


def distribution(values):
    bands = {"below_2000": 0, "2000_4500": 0, "4500_6500": 0, "6500_8000": 0, "8000_9200": 0, "9200_plus": 0}
    for value in values:
        if value < 2000: bands["below_2000"] += 1
        elif value < 4500: bands["2000_4500"] += 1
        elif value < 6500: bands["4500_6500"] += 1
        elif value < 8000: bands["6500_8000"] += 1
        elif value < 9200: bands["8000_9200"] += 1
        else: bands["9200_plus"] += 1
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

    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "intrinsic_parity_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "intrinsic_parity_v5c")
    examples, structural = build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    if len(examples) < 1000:
        raise SystemExit(f"insufficient production-parity examples: {len(examples)}")

    bundles = [()]
    for size in range(1, len(legacy.FACTOR_NAMES) + 1):
        bundles.extend(itertools.combinations(legacy.FACTOR_NAMES, size))
    residual_results = [legacy.evaluate_bundle(examples, bundle) for bundle in bundles]
    selected = legacy.choose_bundle(residual_results)
    if list(selected.get("factors", [])) != ["pedigree"]:
        raise SystemExit(f"production-parity residual selection changed: {selected.get('factors')}")

    football_validation = v5c.evaluate(examples, legacy)
    economic = economic_validation(examples, structural, legacy, v5c)
    fitted = v5c.old_fit(examples, legacy)
    tapers = v5c.fit_tapers(examples)
    anchors, _cont, residualizers, residual_coeffs = fitted

    records = []
    by_season = defaultdict(list)
    for e in examples:
        _base, residual, repaired = v5c.new_predict(e, fitted, tapers, legacy)
        sf = structural[e.season][Position(e.position)].relative_pressure
        economic_raw = max(0.0, repaired * sf)
        record = {"season": e.season, "position": e.position, "football_raw": repaired, "structural_factor": sf, "economic_raw": economic_raw}
        records.append(record)
        by_season[e.season].append(record)

    reference = []
    for season, season_rows in by_season.items():
        reference.extend(sorted((r["economic_raw"] for r in season_rows), reverse=True)[: CANONICAL_TEAM_COUNT * CANONICAL_ROSTER_SIZE])
    display_anchors = [
        (0.0, 0),
        (q(reference, 0.05), 2000),
        (q(reference, 0.20), 4500),
        (q(reference, 0.50), 6500),
        (q(reference, 0.75), 8000),
        (q(reference, 0.90), 9000),
        (q(reference, 0.97), 9400),
        (q(reference, 0.99), 9700),
    ]
    displays = [display_value(r["economic_raw"], display_anchors) for r in records]
    relevant_displays = [display_value(v, display_anchors) for v in reference]
    by_position = {
        position: distribution([display_value(r["economic_raw"], display_anchors) for r in records if r["position"] == position])
        for position in POSITIONS
    }

    structural_summary = {}
    for season, factors in structural.items():
        structural_summary[str(season)] = {
            p.value: {
                "selected_starters": factors[p].selected_starters,
                "effective_supply": factors[p].effective_supply,
                "starter_pressure": factors[p].starter_pressure,
                "relative_pressure": factors[p].relative_pressure,
            }
            for p in (Position.QB, Position.RB, Position.WR, Position.TE)
        }

    payload = {
        "model_version": MODEL_VERSION,
        "example_count": len(examples),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
        "forecast_path": "PIT Model-A Y1; production Intrinsic policy for Y2/Y3: QB career-state when frozen PIT evidence exists else carry-forward, RB/TE bounded age transitions, WR Y2 carry-forward and Y3 bounded",
        "residual_selection": selected,
        "residual_candidates": residual_results,
        "football_validation": football_validation,
        "economic_validation": economic,
        "final_parameters": {
            "legacy_position_anchors_used_only_for_residual_units": anchors,
            "continuation": tapers,
            "pedigree_residualizer": residualizers["pedigree"],
            "pedigree_residual_coefficients_normalized": residual_coeffs,
            "display_reference": "top 216 predicted economic assets per PIT season (12 teams x 18 active roster), position-agnostic, football/rules only",
            "display_anchors": display_anchors,
            "display_tail_scale": display_anchors[-1][0],
        },
        "continuation_diagnostics": continuation_diagnostics(examples, v5c),
        "structural_economics": {
            "definition": "position starter pressure / pooled starter pressure; starter pressure = neutral league-wide selected starters / production-concentration effective Y1 supply",
            "version": "intrinsic-structural-starter-pressure-v1",
            "by_season": structural_summary,
        },
        "display_distribution_full_population": distribution(displays),
        "display_distribution_dynasty_reference": distribution(relevant_displays),
        "display_distribution_by_position": by_position,
        "market_inputs_used": False,
        "league_market_inputs_used": False,
        "replacement_inputs_used": False,
        "team_utility_inputs_used": False,
        "owner_inputs_used": False,
        "transaction_inputs_used": False,
    }
    out = args.output_dir / "fundamental_intrinsic_production_parity.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
