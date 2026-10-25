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


def load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
rc = load_registered(HERE / "run_career_calibration.py", "pr131_hier_career")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_hier_base")
audit = load_registered(HERE / "run_forecast_trajectory_shape_audit.py", "pr131_hier_audit")
chall = load_registered(HERE / "run_forecast_trajectory_challengers.py", "pr131_hier_chall")
repair = load_registered(HERE / "run_multiyear_intrinsic_model_a_repair.py", "pr131_hier_repair")

MIN_CELL_N = 100
MIN_DENOM = 1e-9


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


def source_state(row):
    return base.State(
        row.player_id, row.position, row.current, 0.0, row.age, row.experience,
        (row.production_quartile - 0.5) / 4,
    )


def source_meta(rows, season):
    by_sp = {(r.season, r.player_id): r for r in rows}
    out = {}
    for row in rows:
        if row.season != season - 1:
            continue
        prior = by_sp.get((season - 2, row.player_id))
        direction = "unknown"
        if prior is not None:
            d = row.current - prior.current
            direction = "improving" if d > 1e-9 else "declining" if d < -1e-9 else "flat"
        s = source_state(row)
        out[row.player_id] = {
            "position": row.position,
            "career_stage": audit.career_stage(row.experience),
            "production_tier": audit.tier(s.percentile),
            "prior_direction": direction,
            "age_band": audit.age_band(row.age),
            "experience": row.experience,
        }
    return out


def baseline_and_sticky(rows, seasons, carry_uncertainty=False):
    baselines, stickies, calibrations = {}, {}, {}
    for season in seasons:
        cal, bp = chall.forecast_paths_variant(
            rows, season, rc, carry_uncertainty=carry_uncertainty, preserve_percentile=False
        )
        _, sp = chall.forecast_paths_variant(
            rows, season, rc, carry_uncertainty=carry_uncertainty, preserve_percentile=True
        )
        calibrations[season] = cal
        baselines[season] = bp
        stickies[season] = sp
    return calibrations, baselines, stickies


def actual_map(rows):
    return {(r.season, r.player_id): r.current for r in rows}


def training_records(rows, seasons, baselines, stickies):
    actual = actual_map(rows)
    recs = []
    for season in seasons:
        meta = source_meta(rows, season)
        for horizon in (1, 2):
            bmap = {s.player_id: s for s in baselines[season][horizon]}
            smap = {s.player_id: s for s in stickies[season][horizon]}
            for pid in sorted(set(bmap) & set(smap) & set(meta)):
                target = actual.get((season + horizon, pid))
                if target is None:
                    target = 0.0
                b, s = bmap[pid], smap[pid]
                recs.append({
                    "forecast_fold": season,
                    "target_season": season + horizon,
                    "horizon": horizon + 1,
                    "player_id": pid,
                    **meta[pid],
                    "baseline_mean": b.mean,
                    "sticky_mean": s.mean,
                    "delta": s.mean - b.mean,
                    "target": target,
                    "needed_delta": target - b.mean,
                })
    return recs


def fit_weight(records):
    denom = sum(r["delta"] ** 2 for r in records)
    if denom <= MIN_DENOM:
        return 0.0
    raw = sum(r["delta"] * r["needed_delta"] for r in records) / denom
    # Structural convex mixture: 0 = current recursive cohort path; 1 = fully preserve
    # latest observed player-state percentile. This is not a fitted bonus/cap.
    return min(1.0, max(0.0, raw))


def hierarchy_keys(meta, horizon):
    return [
        ("cell", horizon, meta["position"], meta["career_stage"], meta["production_tier"], meta["prior_direction"]),
        ("position_stage_tier", horizon, meta["position"], meta["career_stage"], meta["production_tier"]),
        ("position_stage", horizon, meta["position"], meta["career_stage"]),
        ("position", horizon, meta["position"]),
        ("global", horizon),
    ]


def fit_hierarchy(records):
    buckets = defaultdict(list)
    for r in records:
        meta = r
        for key in hierarchy_keys(meta, r["horizon"]):
            buckets[key].append(r)
    fitted = {}
    for key, vals in buckets.items():
        fitted[key] = {"n": len(vals), "weight": fit_weight(vals)}
    return fitted


def select_weight(fitted, meta, horizon):
    keys = hierarchy_keys(meta, horizon)
    for key in keys[:-1]:
        item = fitted.get(key)
        if item and item["n"] >= MIN_CELL_N:
            return item["weight"], item["n"], key[0]
    item = fitted.get(keys[-1], {"n": 0, "weight": 0.0})
    return item["weight"], item["n"], "global"


def build_hierarchical_paths(rows, seasons, *, carry_uncertainty=False):
    calibrations, baselines, stickies = baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
    records = training_records(rows, seasons, baselines, stickies)
    paths = {}
    weight_rows = []
    for season in seasons:
        # A training forecast is resolved only when its target season is strictly before
        # the current preseason cutoff. This is stronger than merely requiring its fold
        # to be earlier and prevents future-outcome leakage.
        train = [r for r in records if r["target_season"] <= season - 1]
        fitted = fit_hierarchy(train)
        meta = source_meta(rows, season)
        variant = {}
        for offset in range(base.HORIZON):
            bstates = {s.player_id: s for s in baselines[season][offset]}
            sstates = {s.player_id: s for s in stickies[season][offset]}
            blended = []
            for pid, b in bstates.items():
                if offset == 0 or pid not in sstates or pid not in meta:
                    blended.append(b)
                    continue
                horizon = offset + 1
                w, n, scope = select_weight(fitted, meta[pid], horizon)
                s = sstates[pid]
                m = b.mean + w * (s.mean - b.mean)
                blended.append(replace(b, mean=max(0.0, m)))
                weight_rows.append({
                    "forecast_fold": season,
                    "player_id": pid,
                    "horizon": horizon,
                    **meta[pid],
                    "weight": w,
                    "evidence_n": n,
                    "scope": scope,
                    "baseline_mean": b.mean,
                    "player_state_anchor_mean": s.mean,
                    "blended_mean": m,
                    "carry_uncertainty": carry_uncertainty,
                })
            variant[offset] = blended
        paths[season] = variant
    return calibrations, paths, weight_rows


def horizon_mae(rows, seasons, paths):
    actual = actual_map(rows)
    out = {}
    for offset in range(base.HORIZON):
        errs = []
        for season in seasons:
            for s in paths[season][offset]:
                target = actual.get((season + offset, s.player_id), 0.0)
                errs.append(abs(s.mean - target))
        out[f"year_{offset+1}"] = mean(errs)
    return out


def survival_brier(pair_rows):
    return mean((r["near_survival"] - (1.0 if r["actual_near"] > 0 else 0.0)) ** 2 for r in pair_rows)


def direct_variant(rows, seasons, name, *, hierarchical=False, carry_uncertainty=False):
    if hierarchical:
        calibrations, paths, weights = build_hierarchical_paths(rows, seasons, carry_uncertainty=carry_uncertainty)
    else:
        calibrations, paths, _ = baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
        paths = paths
        weights = []
    pairs = audit.build_pair_rows(rows, seasons, calibrations, paths)
    return {
        "name": name,
        "overall": audit.path_metrics(pairs),
        "groups": audit.grouped(pairs),
        "horizon_mae": horizon_mae(rows, seasons, paths),
        "survival_brier": survival_brier(pairs),
    }, paths, weights


def group_lookup(result, dimension, value):
    for row in result["groups"]:
        if row["dimension"] == dimension and row["value"] == value:
            return row
    return None


def acceptance(baseline, candidate):
    b, c = baseline["overall"], candidate["overall"]
    # Frozen direct-target gate for this challenger: it must improve shape in both
    # absolute and correlational terms, improve player-specific persistence, and not
    # materially damage adjacent level/cumulative targets.
    return (
        c["new_slope_mae"] < b["new_slope_mae"]
        and c["slope_change_correlation"] > b["slope_change_correlation"]
        and c["far_revision_correlation"] > b["far_revision_correlation"]
        and c["persistence_correlation"] > b["persistence_correlation"]
        and c["persistence_mae"] < b["persistence_mae"]
        and c["near_revision_correlation"] >= b["near_revision_correlation"] - 0.01
        and c["new_cumulative_mae"] <= b["new_cumulative_mae"] * 1.01
    )


def model_a_retest(rows, seasons, dyn_repo, hierarchical_paths_builder):
    repair_base = repair.load_base()
    repair.install_repair_candidate(repair_base)

    def patched(rows_arg, season, rc_arg):
        cal, paths, _ = hierarchical_paths_builder(rows_arg, seasons=[season], carry_uncertainty=True)
        return cal[season], paths[season]

    # For point-in-time hierarchy weights we need the full historical fold set, not a
    # single-fold call. Precompute once and serve the requested fold from the closure.
    cals, all_paths, _ = hierarchical_paths_builder(rows, seasons=seasons, carry_uncertainty=True)
    def patched_cached(rows_arg, season, rc_arg):
        return cals[season], all_paths[season]
    repair_base.forecast_paths = patched_cached

    candidate = "marginal_lineup_opportunity"
    all_fold_rows, fold_rows, fold_metrics, prior_rows = [], {}, [], []
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
    scored = {s: fold_rows[s] for s in seasons[1:] if s in fold_rows}
    checks = repair.scenario_checks(repair_base, all_fold_rows, scored, scarcity)
    n = sum(int(f["n"]) for f in fold_metrics)
    def wavg(k):
        return sum(float(f[k]) * int(f["n"]) for f in fold_metrics) / n if n else math.nan
    ma, af = wavg("model_a_mae"), wavg("affine_mae")
    return {
        "n": n,
        "model_a_mae": ma,
        "affine_mae": af,
        "mae_improvement": (af - ma) / af if af else math.nan,
        "coverage": wavg("model_a_coverage"),
        "scarcity": scarcity,
        "economic_checks": checks,
        "economic_checks_passed": sum(1 for x in checks.values() if x.get("pass")),
        "market_independence_note": "Market rules remain unchanged; no market target enters Forecast or Value. Full market diagnostic remains the canonical repair benchmark unless a production candidate is proposed.",
    }


def report(payload):
    b = payload["variants"]["baseline_mean_baseline_uncertainty"]["overall"]
    h = payload["variants"]["hierarchical_mean_baseline_uncertainty"]["overall"]
    hu = payload["variants"]["hierarchical_mean_repaired_uncertainty"]["overall"]
    lines = [
        "# Hierarchical Trajectory-State Forecast Research — PR #131", "",
        "**Status:** research-only, non-authoritative. Production Forecast/Value unchanged. Model B not fitted.", "",
        "## State definition", "",
        "Player-specific state is the latest point-in-time production percentile plus recent observed direction. Cohort state is position, career stage, production tier, and broader hierarchical parents. Horizon-specific evidence is learned separately for Year 2 and Year 3. Uncertainty remains a separate Forecast dimension and is tested both with baseline recursion and the already-accepted research-only carry-forward repair.", "",
        f"Evidence sufficiency floor: **{MIN_CELL_N} resolved observations** before a cell may act independently; otherwise the model falls back through position×stage×tier → position×stage → position → global.", "",
        "The learned parameter is a convex blend: 0 means use the current recursive cohort path; 1 means fully preserve the latest observed percentile-state path. It is estimated by least squares only from targets resolved before each historical preseason cutoff.", "",
        "## Direct Forecast result", "",
        "| Metric | Baseline | Hierarchical mean | Hierarchical + repaired uncertainty |", "|---|---:|---:|---:|",
        f"| Far revision correlation | {b['far_revision_correlation']:.3f} | {h['far_revision_correlation']:.3f} | {hu['far_revision_correlation']:.3f} |",
        f"| Slope correlation | {b['slope_change_correlation']:.3f} | {h['slope_change_correlation']:.3f} | {hu['slope_change_correlation']:.3f} |",
        f"| Slope MAE | {b['new_slope_mae']:.3f} | {h['new_slope_mae']:.3f} | {hu['new_slope_mae']:.3f} |",
        f"| Cumulative MAE | {b['new_cumulative_mae']:.3f} | {h['new_cumulative_mae']:.3f} | {hu['new_cumulative_mae']:.3f} |",
        f"| Persistence correlation | {b['persistence_correlation']:.3f} | {h['persistence_correlation']:.3f} | {hu['persistence_correlation']:.3f} |",
        f"| Persistence MAE | {b['persistence_mae']:.3f} | {h['persistence_mae']:.3f} | {hu['persistence_mae']:.3f} |",
        f"| Near / far 80% coverage | {b['near_80_coverage']:.1%}/{b['far_80_coverage']:.1%} | {h['near_80_coverage']:.1%}/{h['far_80_coverage']:.1%} | {hu['near_80_coverage']:.1%}/{hu['far_80_coverage']:.1%} |", "",
        f"Direct hierarchical mean gate: **{'PASS' if payload['hierarchical_mean_accepted'] else 'FAIL'}**.", "",
        "## Guardrails", "",
        "- Market Value is not a Forecast target.",
        "- Team Utility and owner preference are excluded.",
        "- No QB bonus, elite override, universal persistence multiplier, or Value compensation is used.",
        "- Every learned blend weight is chronological and hierarchy-backed.",
        "- Accepted recursive uncertainty carry-forward remains research-only.",
        "- No production behavior changed and Model B was not fitted.",
    ]
    if payload.get("model_a_retest"):
        x = payload["model_a_retest"]
        lines += ["", "## Model A unchanged-economics retest", "",
                  f"- MAE: **{x['model_a_mae']:.3f}** vs affine **{x['affine_mae']:.3f}** ({x['mae_improvement']:.1%} improvement).",
                  f"- Calibrated nominal-80% coverage: **{x['coverage']:.1%}**.",
                  f"- Economic checks: **{x['economic_checks_passed']}/6**.",
                  f"- Elite-QB longevity: `{json.dumps(x['economic_checks']['elite_qb_longevity'], sort_keys=True)}`",
                  f"- Appreciation/decline: `{json.dumps(x['economic_checks']['expected_appreciation_decline'], sort_keys=True)}`"]
    else:
        lines += ["", "## Model A retest", "", "Not run: the hierarchical mean challenger did not clear the direct Forecast gate."]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--career-panel", type=Path, required=True)
    p.add_argument("--dynastyprocess-repo", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = base.load_rows(args.career_panel, rc)
    seasons = audit.update_audit.supported_seasons(base, rows, rc)

    b0, _, _ = direct_variant(rows, seasons, "baseline_mean_baseline_uncertainty")
    bu, _, _ = direct_variant(rows, seasons, "baseline_mean_repaired_uncertainty", carry_uncertainty=True)
    h0, _, weights = direct_variant(rows, seasons, "hierarchical_mean_baseline_uncertainty", hierarchical=True)
    hu, _, weights_u = direct_variant(rows, seasons, "hierarchical_mean_repaired_uncertainty", hierarchical=True, carry_uncertainty=True)
    accepted = acceptance(b0, h0)

    variants = {x["name"]: x for x in (b0, bu, h0, hu)}
    focus = {}
    for name, result in variants.items():
        focus[name] = {
            "elite_qb": group_lookup(result, "is_elite_qb", "True"),
            "young_breakout_wr": group_lookup(result, "is_young_breakout_wr", "True"),
            "young_te": group_lookup(result, "is_young_te", "True"),
            "aging_rb": group_lookup(result, "is_aging_rb", "True"),
        }
    payload = {
        "research_only": True,
        "production_forecast_changed": False,
        "production_value_changed": False,
        "model_b_fitted": False,
        "min_cell_n": MIN_CELL_N,
        "hierarchy": ["position×career_stage×production_tier×recent_direction", "position×career_stage×production_tier", "position×career_stage", "position", "global"],
        "variants": variants,
        "subgroup_focus": focus,
        "hierarchical_mean_accepted": accepted,
        "model_a_retest": model_a_retest(rows, seasons, args.dynastyprocess_repo, build_hierarchical_paths) if accepted else None,
    }
    (args.output_dir / "hierarchical_trajectory_state_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    text = report(payload)
    (args.output_dir / "hierarchical_trajectory_state_report.md").write_text(text, encoding="utf-8")
    if weights:
        with (args.output_dir / "hierarchical_trajectory_state_weights.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(weights[0].keys()))
            w.writeheader(); w.writerows(weights)
    print(text)


if __name__ == "__main__":
    main()
