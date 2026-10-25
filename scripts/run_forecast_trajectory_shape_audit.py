from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
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
rc = load_registered(HERE / "run_career_calibration.py", "pr131_trajectory_career_calibration")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_trajectory_base")
update_audit = load_registered(HERE / "run_forecast_update_reliability_audit.py", "pr131_trajectory_update_audit")


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
    return sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / math.sqrt(xx * yy)


def sign(x):
    return 1 if x > 1e-9 else -1 if x < -1e-9 else 0


def mae(xs):
    xs = list(xs)
    return mean(abs(x) for x in xs)


def tier(percentile: float) -> str:
    if percentile >= 0.75:
        return "elite_tail"
    if percentile >= 0.25:
        return "middle"
    return "replacement_tail"


def age_band(age):
    if age is None:
        return "unknown"
    if age <= 23:
        return "<=23"
    if age <= 26:
        return "24-26"
    if age <= 29:
        return "27-29"
    if age <= 32:
        return "30-32"
    return "33+"


def career_stage(exp):
    if exp <= 1:
        return "rookie_or_year2"
    if exp <= 3:
        return "young"
    if exp <= 7:
        return "prime"
    return "veteran"


def uncertainty_band(sd, m):
    cv = sd / max(1.0, abs(m))
    if cv < 0.35:
        return "low"
    if cv < 0.70:
        return "medium"
    return "high"


def survival_band(p):
    if p >= 0.85:
        return "high_survival"
    if p >= 0.65:
        return "medium_survival"
    return "high_attrition"


def state_map(states):
    return {s.player_id: s for s in states}


def transition_meta(calibration, state):
    q = min(4, max(1, int(state.percentile * 4) + 1))
    item = calibration.cells.get((state.position, state.age, state.experience, q, False))
    fallback = item is None
    if item is None:
        item = calibration.parent[state.position]
    return {
        "quartile": q,
        "fallback": fallback,
        "survival": float(item["survival_probability"]),
        "multiplier": float(item["conditional_production_multiplier"]),
        "dispersion": float(item["conditional_multiplier_stddev"]),
        "sample_size": int(item["sample_size"]),
        "survivor_n": int(item["survivor_sample_size"]),
    }


def actual_points(by_season_player, season, player_id):
    row = by_season_player.get((season, player_id))
    return row.current if row is not None else 0.0


def build_pair_rows(rows, seasons, calibrations, paths):
    by_sp = {(r.season, r.player_id): r for r in rows}
    out = []
    for old_fold, new_fold in zip(seasons, seasons[1:]):
        if new_fold != old_fold + 1:
            continue
        # Common path is old offsets 1/2 versus new offsets 0/1.
        old_near = state_map(paths[old_fold][1])
        old_far = state_map(paths[old_fold][2])
        new_near = state_map(paths[new_fold][0])
        new_far = state_map(paths[new_fold][1])
        new_source = {
            r.player_id: base.State(
                r.player_id, r.position, r.current, 0.0, r.age, r.experience,
                (r.production_quartile - 0.5) / 4,
            )
            for r in rows if r.season == new_fold - 1
        }
        common = sorted(set(old_near) & set(old_far) & set(new_near) & set(new_far) & set(new_source))
        for pid in common:
            on, of, nn, nf, src = old_near[pid], old_far[pid], new_near[pid], new_far[pid], new_source[pid]
            a_near = actual_points(by_sp, new_fold, pid)
            a_far = actual_points(by_sp, new_fold + 1, pid)
            rev_near = nn.mean - on.mean
            rev_far = nf.mean - of.mean
            need_near = a_near - on.mean
            need_far = a_far - of.mean
            old_slope = of.mean - on.mean
            new_slope = nf.mean - nn.mean
            actual_slope = a_far - a_near
            old_cum = on.mean + of.mean
            new_cum = nn.mean + nf.mean
            actual_cum = a_near + a_far
            persistence = rev_far / rev_near if abs(rev_near) > 1e-9 else math.nan
            needed_persistence = need_far / need_near if abs(need_near) > 1e-9 else math.nan
            slope_change = new_slope - old_slope
            needed_slope_change = actual_slope - old_slope
            m0 = transition_meta(calibrations[new_fold], src)
            m1 = transition_meta(calibrations[new_fold], nn)
            prior_row = by_sp.get((old_fold - 1, pid))
            latest_row = by_sp.get((new_fold - 1, pid))
            prod_direction = "unknown"
            if prior_row is not None and latest_row is not None:
                delta = latest_row.current - prior_row.current
                prod_direction = "improving" if delta > 1e-9 else "declining" if delta < -1e-9 else "flat"
            out.append({
                "old_fold": old_fold,
                "new_fold": new_fold,
                "player_id": pid,
                "position": nn.position,
                "age": src.age,
                "age_band": age_band(src.age),
                "experience": src.experience,
                "career_stage": career_stage(src.experience),
                "production_tier": tier(src.percentile),
                "prior_direction": prod_direction,
                "uncertainty_band": uncertainty_band(nn.sd, nn.mean),
                "survival_risk_band": survival_band(m0["survival"]),
                "is_elite_qb": nn.position == "QB" and src.percentile >= 0.75 and (src.age or 0) <= 33,
                "is_young_breakout_wr": nn.position == "WR" and src.experience <= 3 and prod_direction == "improving" and src.percentile >= 0.50,
                "is_young_te": nn.position == "TE" and src.experience <= 3,
                "is_aging_rb": nn.position == "RB" and (src.age or 0) >= 27,
                "old_near_mean": on.mean,
                "old_far_mean": of.mean,
                "new_near_mean": nn.mean,
                "new_far_mean": nf.mean,
                "actual_near": a_near,
                "actual_far": a_far,
                "near_revision": rev_near,
                "far_revision": rev_far,
                "near_needed_revision": need_near,
                "far_needed_revision": need_far,
                "revision_persistence": persistence,
                "needed_persistence": needed_persistence,
                "persistence_error": persistence - needed_persistence if math.isfinite(persistence) and math.isfinite(needed_persistence) else math.nan,
                "old_slope": old_slope,
                "new_slope": new_slope,
                "actual_slope": actual_slope,
                "slope_change": slope_change,
                "needed_slope_change": needed_slope_change,
                "old_slope_error": abs(old_slope - actual_slope),
                "new_slope_error": abs(new_slope - actual_slope),
                "old_cumulative": old_cum,
                "new_cumulative": new_cum,
                "actual_cumulative": actual_cum,
                "old_cumulative_error": abs(old_cum - actual_cum),
                "new_cumulative_error": abs(new_cum - actual_cum),
                "old_near_sd": on.sd,
                "old_far_sd": of.sd,
                "new_near_sd": nn.sd,
                "new_far_sd": nf.sd,
                "near_covered": nn.mean - Z80 * nn.sd <= a_near <= nn.mean + Z80 * nn.sd,
                "far_covered": nf.mean - Z80 * nf.sd <= a_far <= nf.mean + Z80 * nf.sd,
                "horizon_sd_ratio": nf.sd / nn.sd if nn.sd > 1e-9 else math.nan,
                "near_survival": m0["survival"],
                "far_survival": m1["survival"],
                "survival_compound_ratio": m1["survival"],
                "near_multiplier": m0["multiplier"],
                "far_multiplier": m1["multiplier"],
                "multiplier_ratio": m1["multiplier"] / m0["multiplier"] if m0["multiplier"] > 1e-9 else math.nan,
                "near_quartile": m0["quartile"],
                "far_quartile": m1["quartile"],
                "quartile_changed": m0["quartile"] != m1["quartile"],
                "near_fallback": m0["fallback"],
                "far_fallback": m1["fallback"],
                "fallback_changed_within_path": m0["fallback"] != m1["fallback"],
                "near_transition_n": m0["sample_size"],
                "far_transition_n": m1["sample_size"],
                "provenance": (
                    f"old preseason={old_fold}, calibration through transition season {old_fold-2}; "
                    f"new preseason={new_fold}, calibration through transition season {new_fold-2}; "
                    f"common targets={new_fold},{new_fold+1}"
                ),
            })
    return out


def path_metrics(rows):
    if not rows:
        return {"n": 0}
    valid_p = [r for r in rows if math.isfinite(float(r["revision_persistence"])) and math.isfinite(float(r["needed_persistence"])) and abs(float(r["near_revision"])) > 1e-9]
    return {
        "n": len(rows),
        "near_direction": mean(sign(r["near_revision"]) == sign(r["near_needed_revision"]) and sign(r["near_revision"]) != 0 for r in rows),
        "far_direction": mean(sign(r["far_revision"]) == sign(r["far_needed_revision"]) and sign(r["far_revision"]) != 0 for r in rows),
        "near_revision_correlation": corr([r["near_revision"] for r in rows], [r["near_needed_revision"] for r in rows]),
        "far_revision_correlation": corr([r["far_revision"] for r in rows], [r["far_needed_revision"] for r in rows]),
        "near_revision_mae": mean(abs(r["near_revision"] - r["near_needed_revision"]) for r in rows),
        "far_revision_mae": mean(abs(r["far_revision"] - r["far_needed_revision"]) for r in rows),
        "slope_direction": mean(sign(r["slope_change"]) == sign(r["needed_slope_change"]) and sign(r["slope_change"]) != 0 for r in rows),
        "slope_change_correlation": corr([r["slope_change"] for r in rows], [r["needed_slope_change"] for r in rows]),
        "old_slope_mae": mean(r["old_slope_error"] for r in rows),
        "new_slope_mae": mean(r["new_slope_error"] for r in rows),
        "slope_error_improvement": mean(r["old_slope_error"] - r["new_slope_error"] for r in rows),
        "old_cumulative_mae": mean(r["old_cumulative_error"] for r in rows),
        "new_cumulative_mae": mean(r["new_cumulative_error"] for r in rows),
        "cumulative_error_improvement": mean(r["old_cumulative_error"] - r["new_cumulative_error"] for r in rows),
        "near_80_coverage": mean(r["near_covered"] for r in rows),
        "far_80_coverage": mean(r["far_covered"] for r in rows),
        "mean_horizon_sd_ratio": mean(r["horizon_sd_ratio"] for r in rows if math.isfinite(float(r["horizon_sd_ratio"]))),
        "mean_revision_persistence": mean(r["revision_persistence"] for r in valid_p),
        "mean_needed_persistence": mean(r["needed_persistence"] for r in valid_p),
        "median_revision_persistence": statistics.median([r["revision_persistence"] for r in valid_p]) if valid_p else math.nan,
        "median_needed_persistence": statistics.median([r["needed_persistence"] for r in valid_p]) if valid_p else math.nan,
        "persistence_correlation": corr([r["revision_persistence"] for r in valid_p], [r["needed_persistence"] for r in valid_p]),
        "persistence_mae": mean(abs(r["revision_persistence"] - r["needed_persistence"]) for r in valid_p),
        "quartile_change_rate": mean(r["quartile_changed"] for r in rows),
        "fallback_change_rate": mean(r["fallback_changed_within_path"] for r in rows),
        "mean_far_vs_near_multiplier_ratio": mean(r["multiplier_ratio"] for r in rows if math.isfinite(float(r["multiplier_ratio"]))),
        "mean_far_survival": mean(r["far_survival"] for r in rows),
    }


def grouped(rows):
    dimensions = [
        "position", "age_band", "career_stage", "production_tier", "prior_direction",
        "uncertainty_band", "survival_risk_band", "quartile_changed",
        "fallback_changed_within_path", "is_elite_qb", "is_young_breakout_wr",
        "is_young_te", "is_aging_rb",
    ]
    out = []
    for dim in dimensions:
        groups = defaultdict(list)
        for row in rows:
            groups[str(row[dim])].append(row)
        for value, subset in sorted(groups.items()):
            out.append({"dimension": dim, "value": value, **path_metrics(subset)})
    return out


def mechanic_correlations(rows):
    target = [r["far_revision"] - r["near_revision"] for r in rows]
    features = {
        "survival_change_across_path": [r["far_survival"] - r["near_survival"] for r in rows],
        "multiplier_change_across_path": [r["far_multiplier"] - r["near_multiplier"] for r in rows],
        "sd_change_across_path": [r["new_far_sd"] - r["new_near_sd"] for r in rows],
        "quartile_change": [1.0 if r["quartile_changed"] else 0.0 for r in rows],
        "fallback_change": [1.0 if r["fallback_changed_within_path"] else 0.0 for r in rows],
    }
    return {name: corr(values, target) for name, values in features.items()}


def report_text(payload):
    m = payload["overall"]
    lines = [
        "# Forecast Multi-Year Trajectory-Shape / Horizon-Consistency Audit — PR #131",
        "",
        "**Status:** research-only. Production Forecast and Value behavior are unchanged. Model B was not fitted.",
        "",
        "## Full common-path reliability",
        "",
        f"- Player-path observations: **{m['n']:,}**.",
        f"- Near common-year revision: direction **{m['near_direction']:.1%}**, correlation **{m['near_revision_correlation']:.3f}**, MAE **{m['near_revision_mae']:.3f}**.",
        f"- Far common-year revision: direction **{m['far_direction']:.1%}**, correlation **{m['far_revision_correlation']:.3f}**, MAE **{m['far_revision_mae']:.3f}**.",
        f"- Path-slope change: direction **{m['slope_direction']:.1%}**, correlation **{m['slope_change_correlation']:.3f}**.",
        f"- Common-path slope MAE old→new: **{m['old_slope_mae']:.3f} → {m['new_slope_mae']:.3f}**.",
        f"- Common-path cumulative MAE old→new: **{m['old_cumulative_mae']:.3f} → {m['new_cumulative_mae']:.3f}**.",
        f"- Nominal-80% coverage near/far: **{m['near_80_coverage']:.1%} / {m['far_80_coverage']:.1%}**.",
        f"- Mean Forecast SD far/near ratio: **{m['mean_horizon_sd_ratio']:.3f}**.",
        f"- Within-path production-quartile reclassification rate: **{m['quartile_change_rate']:.1%}**.",
        f"- Within-path fallback-status change rate: **{m['fallback_change_rate']:.1%}**.",
        "",
        "## Persistence diagnostics",
        "",
        f"- Median modeled far/near revision persistence: **{m['median_revision_persistence']:.3f}**.",
        f"- Median subsequently needed far/near persistence: **{m['median_needed_persistence']:.3f}**.",
        f"- Persistence correlation: **{m['persistence_correlation']:.3f}**; persistence MAE **{m['persistence_mae']:.3f}**.",
        "",
        "## Recursive-mechanics correlations with far-minus-near revision",
        "",
    ]
    for k, v in payload["mechanic_correlations"].items():
        lines.append(f"- {k}: **{v:.3f}**")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- This script audits Forecast paths only; it does not alter production Forecast or Value.",
        "- Fold calibration remains strictly pre-cutoff.",
        "- Market value is not used as a Forecast target.",
        "- No Model B is fitted.",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = base.load_rows(args.career_panel, rc)
    seasons = update_audit.supported_seasons(base, rows, rc)
    calibrations, paths = update_audit.build_raw_forecasts(base, rows, seasons, rc)
    pair_rows = build_pair_rows(rows, seasons, calibrations, paths)
    groups = grouped(pair_rows)
    payload = {
        "research_only": True,
        "model_b_fitted": False,
        "production_forecast_changed": False,
        "production_value_changed": False,
        "horizon": base.HORIZON,
        "supported_seasons": seasons,
        "overall": path_metrics(pair_rows),
        "mechanic_correlations": mechanic_correlations(pair_rows),
        "group_diagnostics": groups,
    }
    (args.output_dir / "forecast_trajectory_shape_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (args.output_dir / "forecast_trajectory_shape_report.md").write_text(report_text(payload), encoding="utf-8")
    if pair_rows:
        with (args.output_dir / "forecast_trajectory_shape_rows.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(pair_rows[0].keys()))
            writer.writeheader()
            writer.writerows(pair_rows)
    if groups:
        with (args.output_dir / "forecast_trajectory_shape_group_diagnostics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(groups[0].keys()))
            writer.writeheader()
            writer.writerows(groups)
    print(report_text(payload))


if __name__ == "__main__":
    main()
