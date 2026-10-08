from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

Z80 = 1.2815515655446004


def load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
rc = load_registered(HERE / "run_career_calibration.py", "pr131_shape_challenger_career")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_shape_challenger_base")
audit = load_registered(HERE / "run_forecast_trajectory_shape_audit.py", "pr131_shape_challenger_audit")
repair = load_registered(HERE / "run_multiyear_intrinsic_model_a_repair.py", "pr131_shape_challenger_repair")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else math.nan


def corr(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 2:
        return math.nan
    xb, yb = mean(xs), mean(ys)
    xx = sum((x - xb) ** 2 for x in xs)
    yy = sum((y - yb) ** 2 for y in ys)
    if xx <= 0 or yy <= 0:
        return 0.0
    return sum((x-xb)*(y-yb) for x,y in zip(xs,ys)) / math.sqrt(xx*yy)


def propagated_forecast_one(state, calibration):
    """Baseline mean; carry incoming state uncertainty through the recursive step.

    This is the delta-method variance contribution implied by next_mean = s*m*X.
    It adds no fitted coefficient and does not alter the Forecast mean.
    """
    e = calibration.transition(state)
    conditional = state.mean * e["multiplier"]
    next_mean = e["survival"] * conditional
    conditional_sd = state.mean * e["dispersion"]
    variance = (
        (e["survival"] * e["multiplier"]) ** 2 * state.sd**2
        + e["survival"] * conditional_sd**2
        + e["survival"] * (1 - e["survival"]) * conditional**2
        + (state.mean * e["multiplier_se"] * e["survival"]) ** 2
        + (conditional * e["survival_se"]) ** 2
    )
    return base.State(
        state.player_id, state.position, max(0.0, next_mean), math.sqrt(max(0.0, variance)),
        None if state.age is None else state.age + 1, state.experience + 1, state.percentile,
    )


def forecast_paths_variant(rows, season, rc_module, *, carry_uncertainty=False, preserve_percentile=False):
    calibration = base.FoldCalibration(rows, season, rc_module)
    if not calibration.supported():
        return calibration, {}
    prior = [row for row in rows if row.season == season - 1]
    current = [
        base.State(row.player_id, row.position, row.current, 0.0, row.age, row.experience, (row.production_quartile - 0.5) / 4)
        for row in prior
    ]
    observed_pct = {s.player_id: s.percentile for s in current}
    paths = {}
    step = propagated_forecast_one if carry_uncertainty else base.forecast_one
    for offset in range(base.HORIZON):
        stepped = [step(state, calibration) for state in current]
        ranked = base.assign_percentiles(stepped)
        if preserve_percentile:
            ranked = [replace(s, percentile=observed_pct.get(s.player_id, s.percentile)) for s in ranked]
        current = ranked
        paths[offset] = current
    return calibration, paths


def direct_results(rows, seasons, variant_name, *, carry_uncertainty=False, preserve_percentile=False):
    calibrations, paths = {}, {}
    for season in seasons:
        cal, path = forecast_paths_variant(
            rows, season, rc,
            carry_uncertainty=carry_uncertainty,
            preserve_percentile=preserve_percentile,
        )
        calibrations[season], paths[season] = cal, path
    pair_rows = audit.build_pair_rows(rows, seasons, calibrations, paths)
    metrics = audit.path_metrics(pair_rows)
    groups = audit.grouped(pair_rows)
    return {"name": variant_name, "overall": metrics, "groups": groups}, paths


def group_lookup(result, dimension, value):
    for row in result["groups"]:
        if row["dimension"] == dimension and row["value"] == value:
            return row
    return None


def direct_acceptance(baseline, challenger):
    b, c = baseline["overall"], challenger["overall"]
    if challenger["name"] == "uncertainty_propagation":
        near_gap_b = abs(b["near_80_coverage"] - 0.80)
        far_gap_b = abs(b["far_80_coverage"] - 0.80)
        near_gap_c = abs(c["near_80_coverage"] - 0.80)
        far_gap_c = abs(c["far_80_coverage"] - 0.80)
        return near_gap_c <= near_gap_b and far_gap_c < far_gap_b
    return (
        c["new_slope_mae"] < b["new_slope_mae"]
        and c["slope_change_correlation"] > b["slope_change_correlation"]
        and c["far_revision_correlation"] >= b["far_revision_correlation"]
        and c["near_revision_correlation"] >= b["near_revision_correlation"] - 0.01
        and c["new_cumulative_mae"] <= b["new_cumulative_mae"]
    )


def model_a_with_uncertainty(rows, seasons, market_repo):
    """Retest Model A with means unchanged and structurally propagated Forecast SD only."""
    def patched(rows_arg, season, rc_arg):
        return forecast_paths_variant(rows_arg, season, rc_arg, carry_uncertainty=True, preserve_percentile=False)

    repair_base = repair.load_base()
    repair.install_repair_candidate(repair_base)
    repair_base.forecast_paths = patched
    candidate = "marginal_lineup_opportunity"
    all_fold_rows, fold_rows = [], {}
    fold_metrics = []
    prior_rows = []

    # Match the canonical repair benchmark exactly: the first supported fold seeds
    # the affine control and is not itself scored as an out-of-time holdout.
    for season in seasons:
        _, eval_rows, details = repair_base.evaluate_fold(rows, season, repair.PRIMARY_CONTEXT, candidate, rc)
        fold_rows[season] = eval_rows
        if prior_rows:
            affine = repair_base.fit_affine(prior_rows)
            parts = repair.component_variance(details)
            scale = repair.uncertainty_scale(prior_rows)
            fm = repair.fold_metrics(repair_base, eval_rows, affine, scale, parts)
            fm["season"] = season
            fold_metrics.append(fm)
            all_fold_rows.extend(eval_rows)
        prior_rows.extend(eval_rows)

    scarcity = repair.context_shift(repair_base, rows, seasons[1:], candidate, rc)
    scored_fold_rows = {season: fold_rows[season] for season in seasons[1:] if season in fold_rows}
    checks = repair.scenario_checks(repair_base, all_fold_rows, scored_fold_rows, scarcity)
    n = sum(int(f["n"]) for f in fold_metrics)
    def wavg(key):
        return sum(float(f[key]) * int(f["n"]) for f in fold_metrics) / n if n else math.nan
    model_a_mae = wavg("model_a_mae")
    affine_mae = wavg("affine_mae")
    return {
        "n": n,
        "model_a_mae": model_a_mae,
        "affine_mae": affine_mae,
        "mae_improvement": (affine_mae - model_a_mae) / affine_mae if affine_mae else math.nan,
        "coverage": wavg("model_a_coverage"),
        "economic_checks_passed": sum(1 for x in checks.values() if x.get("pass")),
        "economic_checks": checks,
        "note": "Model A means/economics unchanged; only Forecast SD recursion differs.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--dynastyprocess-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = base.load_rows(args.career_panel, rc)
    seasons = audit.update_audit.supported_seasons(base, rows, rc)

    baseline, _ = direct_results(rows, seasons, "baseline")
    uncertainty, _ = direct_results(rows, seasons, "uncertainty_propagation", carry_uncertainty=True)
    sticky, _ = direct_results(rows, seasons, "observed_percentile_persistence", preserve_percentile=True)
    combined, _ = direct_results(rows, seasons, "uncertainty_plus_observed_percentile", carry_uncertainty=True, preserve_percentile=True)
    challengers = [uncertainty, sticky, combined]
    decisions = {x["name"]: direct_acceptance(baseline, x) for x in challengers}

    payload = {
        "research_only": True,
        "production_forecast_changed": False,
        "production_value_changed": False,
        "model_b_fitted": False,
        "baseline": baseline,
        "challengers": challengers,
        "direct_acceptance": decisions,
        "subgroup_focus": {
            name: {
                "elite_qb": group_lookup(result, "is_elite_qb", "True"),
                "young_breakout_wr": group_lookup(result, "is_young_breakout_wr", "True"),
                "young_te": group_lookup(result, "is_young_te", "True"),
                "aging_rb": group_lookup(result, "is_aging_rb", "True"),
            }
            for name, result in [("baseline", baseline)] + [(x["name"], x) for x in challengers]
        },
    }
    if decisions["uncertainty_propagation"]:
        payload["model_a_uncertainty_retest"] = model_a_with_uncertainty(rows, seasons, args.dynastyprocess_repo)
    else:
        payload["model_a_uncertainty_retest"] = None

    path = args.output_dir / "forecast_trajectory_challengers_results.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Forecast Trajectory Challenger Validation — PR #131",
        "",
        "**Status:** research-only. No production Forecast/Value changes. Model B not fitted.",
        "",
        "## Direct Forecast comparison",
        "",
        "| Variant | Slope MAE | Slope corr | Far revision corr | Near/Far 80% coverage | Far/Near SD | Accepted? |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in [baseline] + challengers:
        m = result["overall"]
        accepted = "BASELINE" if result is baseline else ("YES" if decisions[result["name"]] else "NO")
        lines.append(
            f"| {result['name']} | {m['new_slope_mae']:.3f} | {m['slope_change_correlation']:.3f} | "
            f"{m['far_revision_correlation']:.3f} | {m['near_80_coverage']:.1%}/{m['far_80_coverage']:.1%} | "
            f"{m['mean_horizon_sd_ratio']:.3f} | {accepted} |"
        )
    if payload["model_a_uncertainty_retest"]:
        x = payload["model_a_uncertainty_retest"]
        lines.extend([
            "", "## Model A unchanged-economics retest for accepted uncertainty repair", "",
            f"- MAE: **{x['model_a_mae']:.3f}** vs affine **{x['affine_mae']:.3f}**.",
            f"- Relative MAE improvement: **{x['mae_improvement']:.1%}**.",
            f"- Calibrated nominal-80% coverage: **{x['coverage']:.1%}**.",
            f"- Economic checks passed: **{x['economic_checks_passed']}/6**.",
            f"- Appreciation/decline: `{json.dumps(x['economic_checks']['expected_appreciation_decline'], sort_keys=True)}`",
            f"- Elite-QB longevity: `{json.dumps(x['economic_checks']['elite_qb_longevity'], sort_keys=True)}`",
        ])
    lines.extend([
        "", "## Guardrails", "",
        "- Direct Forecast targets decide whether a challenger is accepted before Model A is considered.",
        "- No arbitrary coefficient is introduced.",
        "- The uncertainty challenger adds the mathematically implied carried state-variance term only.",
        "- The percentile-persistence challenger is structural and parameter-free; it tests whether recursive re-ranking is the path-shape defect.",
    ])
    report = "\n".join(lines) + "\n"
    (args.output_dir / "forecast_trajectory_challengers_report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
