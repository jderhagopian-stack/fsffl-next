from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

DISCOUNT = 0.85
HORIZON = 3
REALIZED_HORIZON = 6
POSITIONS = ("QB", "RB", "WR", "TE")
MIN_TRAIN_EXAMPLES = 400
RIDGE = 1e-4
EPS = 1e-9
MODEL_VERSION = "fundamental-intrinsic-shared-career-v5"
CONTINUATION_VERSION = "state-conditioned-continuation-v1"
GLOBAL_CONDITIONING_SCALE = 500.0


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(values) -> float:
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def q(values: list[float], quantile: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    p = quantile * (len(xs) - 1)
    lo, hi = int(math.floor(p)), int(math.ceil(p))
    if lo == hi:
        return xs[lo]
    f = p - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def solve_ridge(X: list[list[float]], y: list[float], ridge: float = RIDGE) -> list[float]:
    if not X:
        return []
    p = len(X[0])
    A = [[sum(row[i] * row[j] for row in X) for j in range(p)] for i in range(p)]
    b = [sum(row[i] * target for row, target in zip(X, y, strict=True)) for i in range(p)]
    for i in range(1, p):
        A[i][i] += ridge
    for i in range(p):
        pivot = max(range(i, p), key=lambda k: abs(A[k][i]))
        A[i], A[pivot] = A[pivot], A[i]
        b[i], b[pivot] = b[pivot], b[i]
        if abs(A[i][i]) < 1e-12:
            A[i][i] = 1e-12
        div = A[i][i]
        A[i] = [v / div for v in A[i]]
        b[i] /= div
        for k in range(p):
            if k == i:
                continue
            factor = A[k][i]
            A[k] = [v - factor * w for v, w in zip(A[k], A[i], strict=True)]
            b[k] -= factor * b[i]
    return b


def discounted_three_year(e) -> float:
    return sum((DISCOUNT**i) * m for i, m in enumerate(e.means))


def terminal_input(e) -> float:
    return (DISCOUNT**HORIZON) * max(0.0, e.means[2])


def continuation_features(e) -> list[float]:
    """Shared-football-unit state-conditioned continuation features.

    The position basis preserves different football career shapes. Age and
    experience only modulate the amount of Y3 production expected to remain after
    Year 3; they are not standalone youth bonuses.
    """
    x = terminal_input(e)
    age = float(e.age if e.age is not None else 27.0)
    exp = float(e.experience)
    age_c = (age - 27.0) / 10.0
    exp_c = (exp - 5.0) / 10.0
    out: list[float] = []
    for pos in POSITIONS:
        active = 1.0 if e.position == pos else 0.0
        out.extend((active * x, active * x * age_c, active * x * exp_c))
    return out


def fit_continuation(training) -> list[float]:
    X = [continuation_features(e) for e in training]
    y = [max(0.0, e.realized - discounted_three_year(e)) for e in training]
    return solve_ridge(X, y, ridge=1e-3)


def continuation_value(e, coeffs: list[float]) -> float:
    return max(0.0, dot(continuation_features(e), coeffs))


def shared_baseline(e, coeffs: list[float]) -> float:
    return discounted_three_year(e) + continuation_value(e, coeffs)


def conditioning_vector(e) -> list[float]:
    pos = [1.0 if e.position == p else 0.0 for p in POSITIONS[1:]]
    return [
        1.0,
        *(m / GLOBAL_CONDITIONING_SCALE for m in e.means),
        *(s / GLOBAL_CONDITIONING_SCALE for s in e.sds),
        *pos,
    ]


def fit_pedigree(training, continuation_coeffs: list[float]):
    X = [conditioning_vector(e) for e in training]
    pedigree_residualizer = solve_ridge(X, [e.pedigree for e in training], ridge=1e-6)
    pedigree_residuals = [e.pedigree - dot(conditioning_vector(e), pedigree_residualizer) for e in training]
    target_residuals = [e.realized - shared_baseline(e, continuation_coeffs) for e in training]
    residual_coeffs = solve_ridge(
        [[1.0, p] for p in pedigree_residuals],
        target_residuals,
        ridge=1e-3,
    )
    return pedigree_residualizer, residual_coeffs


def predict_new(e, continuation_coeffs, pedigree_residualizer, residual_coeffs):
    base = shared_baseline(e, continuation_coeffs)
    p_resid = e.pedigree - dot(conditioning_vector(e), pedigree_residualizer)
    residual = residual_coeffs[0] + residual_coeffs[1] * p_resid
    return base, residual, max(0.0, base + residual)


def fit_legacy_raw(training, legacy):
    anchors = legacy.position_anchors(training)
    continuation = legacy.fit_continuation(training, anchors)
    residualizers, residual_coeffs = legacy.fit_residual_model(training, anchors, continuation, ("pedigree",))
    return anchors, continuation, residualizers, residual_coeffs


def predict_legacy_raw(e, fitted, legacy):
    anchors, continuation, residualizers, residual_coeffs = fitted
    _base_norm, _resid_norm, final_norm = legacy.predict(
        e,
        anchors,
        continuation,
        ("pedigree",),
        residualizers,
        residual_coeffs,
    )
    return final_norm * anchors[e.position] / 100.0


def evaluate(examples, legacy):
    seasons = sorted({e.season for e in examples})
    rows = []
    for holdout_season in seasons:
        training = [e for e in examples if e.season <= holdout_season - REALIZED_HORIZON]
        holdout = [e for e in examples if e.season == holdout_season]
        if len(training) < MIN_TRAIN_EXAMPLES or not holdout:
            continue
        legacy_fit = fit_legacy_raw(training, legacy)
        continuation = fit_continuation(training)
        pedigree_residualizer, pedigree_coeffs = fit_pedigree(training, continuation)
        for e in holdout:
            old = predict_legacy_raw(e, legacy_fit, legacy)
            new_base, new_residual, new = predict_new(e, continuation, pedigree_residualizer, pedigree_coeffs)
            rows.append({
                "season": e.season,
                "position": e.position,
                "age": e.age,
                "target": e.realized,
                "old": old,
                "new_base": new_base,
                "new_residual": new_residual,
                "new": new,
                "old_error": abs(old - e.realized),
                "new_error": abs(new - e.realized),
            })
    old_mae = mean(r["old_error"] for r in rows)
    new_mae = mean(r["new_error"] for r in rows)
    by_fold = defaultdict(list)
    by_pos = defaultdict(list)
    for r in rows:
        by_fold[r["season"]].append(r)
        by_pos[r["position"]].append(r)
    fold_wins = sum(
        mean(x["new_error"] for x in vals) < mean(x["old_error"] for x in vals)
        for vals in by_fold.values()
    )
    pos = {}
    for p in POSITIONS:
        vals = by_pos[p]
        if vals:
            om = mean(x["old_error"] for x in vals)
            nm = mean(x["new_error"] for x in vals)
            pos[p] = {
                "old_mae": om,
                "new_mae": nm,
                "mae_gain": (om - nm) / om if om > EPS else 0.0,
            }
    aging = {}
    for p in ("RB", "TE"):
        vals = [r for r in rows if r["position"] == p and r["age"] is not None and r["age"] >= 30]
        if vals:
            aging[p] = {
                "n": len(vals),
                "old_mae": mean(r["old_error"] for r in vals),
                "new_mae": mean(r["new_error"] for r in vals),
                "mean_old_prediction": mean(r["old"] for r in vals),
                "mean_new_prediction": mean(r["new"] for r in vals),
                "mean_target": mean(r["target"] for r in vals),
            }
    # Compare top decile by each model prediction; the new model must not buy an
    # aggregate gain by destroying premium-player accuracy.
    old_cut = q([r["old"] for r in rows], 0.90)
    new_cut = q([r["new"] for r in rows], 0.90)
    old_tail = [r for r in rows if r["old"] >= old_cut]
    new_tail = [r for r in rows if r["new"] >= new_cut]
    return {
        "n": len(rows),
        "folds": len(by_fold),
        "old_raw_mae": old_mae,
        "new_raw_mae": new_mae,
        "raw_mae_gain": (old_mae - new_mae) / old_mae if old_mae > EPS else 0.0,
        "new_fold_wins": fold_wins,
        "new_fold_win_rate": fold_wins / len(by_fold) if by_fold else 0.0,
        "position": pos,
        "aging_30_plus": aging,
        "old_top_decile_mae": mean(r["old_error"] for r in old_tail),
        "new_top_decile_mae": mean(r["new_error"] for r in new_tail),
    }


def final_fit(examples):
    continuation = fit_continuation(examples)
    pedigree_residualizer, pedigree_coeffs = fit_pedigree(examples, continuation)
    values = []
    baselines = []
    for e in examples:
        base, _residual, final = predict_new(e, continuation, pedigree_residualizer, pedigree_coeffs)
        baselines.append(base)
        values.append(final)
    quantiles = {str(p): q(values, p) for p in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.97, 0.99)}
    # Stable football-only display reference universe: examples at or above the
    # historical median shared-scale predicted career magnitude. This excludes the
    # fringe half of positive NFL player-seasons without position quotas, roster
    # rules, market prices, or named-player tuning.
    cutoff = q(values, 0.50)
    relevant = [v for v in values if v >= cutoff]
    relevant_quantiles = {str(p): q(relevant, p) for p in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.97, 0.99)}
    return {
        "continuation_feature_order": [
            f"{p}:{feature}" for p in POSITIONS for feature in ("y3_terminal", "y3_terminal_x_age", "y3_terminal_x_experience")
        ],
        "continuation_coefficients": continuation,
        "conditioning_scale": GLOBAL_CONDITIONING_SCALE,
        "pedigree_residualizer": pedigree_residualizer,
        "pedigree_residual_coefficients": pedigree_coeffs,
        "raw_value_quantiles": quantiles,
        "display_reference_rule": "repaired predicted shared career value >= historical pooled median repaired prediction",
        "display_reference_cutoff": cutoff,
        "display_reference_quantiles": relevant_quantiles,
        "raw_min": min(values),
        "raw_max": max(values),
        "raw_mean": mean(values),
        "raw_sd": statistics.pstdev(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    legacy_path = Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py")
    legacy = load_module(legacy_path, "fundamental_intrinsic_legacy_v4")
    rc = legacy.load_module(Path(__file__).with_name("run_career_calibration.py"), "fundamental_intrinsic_career_v5")
    rows = legacy.load_rows(args.career_panel)
    examples = legacy.build_examples(rows, rc)
    if len(examples) < 1000:
        raise SystemExit(f"insufficient PIT examples: {len(examples)}")

    validation = evaluate(examples, legacy)
    final = final_fit(examples)
    payload = {
        "model_version": MODEL_VERSION,
        "continuation_version": CONTINUATION_VERSION,
        "discount_factor": DISCOUNT,
        "forecast_horizon": HORIZON,
        "realized_validation_horizon": REALIZED_HORIZON,
        "target": "shared-unit six-season discounted realized football production",
        "example_count": len(examples),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
        "repair": {
            "continuation": "post-Y3 expected football value is Y3-terminal production modulated by position-specific age and experience interactions fitted chronologically",
            "cross_position": "one pooled football-production magnitude; no position-specific normalization anchor",
            "pedigree": "same residual-only methodology, re-estimated in shared football-production units",
        },
        "validation": validation,
        "final_parameters": final,
        "market_inputs_used": False,
        "replacement_inputs_used": False,
        "team_utility_inputs_used": False,
        "owner_inputs_used": False,
    }
    out_json = args.output_dir / "fundamental_intrinsic_v5_calibration.json"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Fundamental Intrinsic v5 bounded repair calibration",
        "",
        f"Examples: **{len(examples)}** ({payload['season_range'][0]}-{payload['season_range'][1]})",
        "",
        "No market, replacement, Team Utility, roster, owner, or transaction-price inputs are used.",
        "",
        "## Chronological old-vs-repaired validation (shared football units)",
        "",
        f"- Old raw MAE: **{validation['old_raw_mae']:.4f}**",
        f"- Repaired raw MAE: **{validation['new_raw_mae']:.4f}**",
        f"- MAE gain: **{validation['raw_mae_gain']:.2%}**",
        f"- Fold wins: **{validation['new_fold_wins']}/{validation['folds']}** ({validation['new_fold_win_rate']:.1%})",
        f"- Old top-decile MAE: **{validation['old_top_decile_mae']:.4f}**",
        f"- Repaired top-decile MAE: **{validation['new_top_decile_mae']:.4f}**",
        "",
        "### Position diagnostics",
        "",
        "```json",
        json.dumps(validation["position"], indent=2, sort_keys=True),
        "```",
        "",
        "### Aging RB/TE diagnostics",
        "",
        "```json",
        json.dumps(validation["aging_30_plus"], indent=2, sort_keys=True),
        "```",
        "",
        "## Frozen production parameters",
        "",
        "```json",
        json.dumps(final, indent=2, sort_keys=True),
        "```",
    ]
    out_md = args.output_dir / "fundamental_intrinsic_v5_calibration.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
