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


def load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
rc = load_registered(HERE / "run_career_calibration.py", "pr131_innovation_career")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_innovation_base")
audit = load_registered(HERE / "run_forecast_trajectory_shape_audit.py", "pr131_innovation_audit")
hier = load_registered(HERE / "run_hierarchical_trajectory_state_research.py", "pr131_innovation_hier")
resid = load_registered(HERE / "run_player_specific_trajectory_residual_research.py", "pr131_innovation_resid")

MIN_RESIDUAL_HISTORY = 3
MIN_HIERARCHY_N = 100
VOLATILITY_RATIO_THRESHOLD = 1.0
STABLE_PERSISTENCE_MIN_MOVE = 10.0
MATERIAL_PERSISTENCE_GAIN = 0.05
ADJACENT_TOLERANCE = 0.01
AGING_RB_TOLERANCE = 0.02
EPS = 1e-9


def mean(xs):
    vals = list(xs)
    return sum(vals) / len(vals) if vals else math.nan


def variance(xs):
    vals = list(xs)
    if len(vals) < 2:
        return math.nan
    m = mean(vals)
    return sum((x - m) ** 2 for x in vals) / (len(vals) - 1)


def corr(xs, ys):
    return resid.corr(list(xs), list(ys))


def spearman(xs, ys):
    return resid.spearman(list(xs), list(ys))


def sign(x):
    return 1 if x > EPS else -1 if x < -EPS else 0


def trailing_same_sign(values):
    if not values:
        return 0
    s = sign(values[-1])
    if s == 0:
        return 0
    n = 0
    for value in reversed(values):
        if sign(value) != s:
            break
        n += 1
    return n


def innovation_state_label(latest, innovations, z):
    if not innovations:
        return "insufficient_history"
    s = sign(latest)
    run = trailing_same_sign(innovations)
    prev_s = sign(innovations[-2]) if len(innovations) >= 2 else 0
    if s > 0 and run >= 2:
        return "repeated_positive"
    if s < 0 and run >= 2:
        return "repeated_negative"
    if s > 0 and prev_s < 0:
        return "positive_reversal"
    if s < 0 and prev_s > 0:
        return "negative_reversal"
    if s > 0 and abs(z) >= VOLATILITY_RATIO_THRESHOLD:
        return "positive_shock"
    if s < 0 and abs(z) >= VOLATILITY_RATIO_THRESHOLD:
        return "negative_shock"
    if s > 0:
        return "positive_oneoff"
    if s < 0:
        return "negative_oneoff"
    return "flat"


def build_innovation_states(rows, seasons, baselines):
    residual_rows = resid.one_step_residual_records(rows, seasons, baselines)
    level_states, _ = resid.build_player_states(rows, seasons, residual_rows)
    by_player = defaultdict(list)
    for row in residual_rows:
        by_player[row["player_id"]].append(row)
    for vals in by_player.values():
        vals.sort(key=lambda x: x["target_season"])

    states = {}
    diagnostics = []
    for season in seasons:
        active_meta = hier.source_meta(rows, season)
        season_states = {}
        for pid, meta in active_meta.items():
            hist = [r for r in by_player.get(pid, []) if r["target_season"] <= season - 1]
            hist.sort(key=lambda x: x["target_season"])
            residuals = [float(r["residual"]) for r in hist]
            n = len(residuals)
            level = level_states.get(season, {}).get(pid, {})
            state = {
                "player_id": pid,
                **meta,
                "history_n": n,
                "stable_level_baseline": mean(residuals[:-1]) if n >= 2 else 0.0,
                "latest_residual": residuals[-1] if residuals else math.nan,
                "latest_innovation": math.nan,
                "innovation_slope": math.nan,
                "innovation_acceleration": math.nan,
                "innovation_autocorrelation": math.nan,
                "innovation_volatility": math.nan,
                "innovation_z": math.nan,
                "same_sign_count": 0,
                "signed_same_sign_count": 0,
                "innovation_state": "insufficient_history",
                "volatility_ratio": math.nan,
                "volatility_band": "insufficient_history",
                "level_component": float(level.get("player_residual_component", 0.0)),
            }
            if n >= MIN_RESIDUAL_HISTORY:
                innovations = []
                for idx in range(2, n):
                    innovations.append(residuals[idx] - mean(residuals[:idx]))
                latest = innovations[-1]
                prior_innov = innovations[:-1]
                prior_residual_sd = statistics.stdev(residuals[:-1]) if len(residuals[:-1]) >= 2 else 0.0
                innov_vol = statistics.stdev(prior_innov) if len(prior_innov) >= 2 else prior_residual_sd
                scale = innov_vol if innov_vol > EPS else prior_residual_sd if prior_residual_sd > EPS else 1.0
                z = latest / scale
                slope = innovations[-1] - innovations[-2] if len(innovations) >= 2 else 0.0
                acceleration = (
                    (innovations[-1] - innovations[-2]) - (innovations[-2] - innovations[-3])
                    if len(innovations) >= 3 else 0.0
                )
                ac = corr(innovations[:-1], innovations[1:]) if len(innovations) >= 3 else 0.0
                run = trailing_same_sign(innovations)
                cohort_sd = math.sqrt(max(0.0, float(level.get("pooled_within_variance", 0.0))))
                vol_ratio = innov_vol / cohort_sd if cohort_sd > EPS else math.nan
                vol_band = (
                    "high" if math.isfinite(vol_ratio) and vol_ratio >= VOLATILITY_RATIO_THRESHOLD
                    else "low" if math.isfinite(vol_ratio) else "unknown"
                )
                state.update({
                    "latest_innovation": latest,
                    "innovation_slope": slope,
                    "innovation_acceleration": acceleration,
                    "innovation_autocorrelation": ac,
                    "innovation_volatility": innov_vol,
                    "innovation_z": z,
                    "same_sign_count": run,
                    "signed_same_sign_count": sign(latest) * run,
                    "innovation_state": innovation_state_label(latest, innovations, z),
                    "volatility_ratio": vol_ratio,
                    "volatility_band": vol_band,
                })
            if n < MIN_RESIDUAL_HISTORY:
                state["history_band"] = "0-2"
            elif n <= 4:
                state["history_band"] = "3-4"
            elif n <= 6:
                state["history_band"] = "5-6"
            else:
                state["history_band"] = "7+"
            if state["same_sign_count"] <= 1:
                state["same_sign_band"] = "0-1"
            elif state["same_sign_count"] == 2:
                state["same_sign_band"] = "2"
            else:
                state["same_sign_band"] = "3+"
            season_states[pid] = state
            diagnostics.append({"forecast_fold": season, **state})
        states[season] = season_states
    return states, diagnostics


def correction_records(rows, seasons, calibrations, anchor_paths, states):
    pairs = audit.build_pair_rows(rows, seasons, calibrations, anchor_paths)
    out = []
    for pair in pairs:
        state = states.get(pair["new_fold"], {}).get(pair["player_id"])
        if not state or state["history_n"] < MIN_RESIDUAL_HISTORY:
            continue
        if not math.isfinite(float(pair["revision_persistence"])) or not math.isfinite(float(pair["needed_persistence"])):
            continue
        if abs(float(pair["near_revision"])) < STABLE_PERSISTENCE_MIN_MOVE:
            continue
        if abs(float(pair["near_needed_revision"])) < STABLE_PERSISTENCE_MIN_MOVE:
            continue
        out.append({
            **pair,
            **state,
            "persistence_correction_target": float(pair["needed_persistence"]) - float(pair["revision_persistence"]),
        })
    return out


def level_key(record, level):
    if level == 0:
        return ("global",)
    if level == 1:
        return (record["position"],)
    if level == 2:
        return (record["position"], record["career_stage"])
    if level == 3:
        return (record["position"], record["career_stage"], record["innovation_state"])
    return (
        record["position"], record["career_stage"], record["production_tier"],
        record["innovation_state"], record["volatility_band"],
    )


def parent_key(record, level):
    return level_key(record, max(0, level - 1))


def fit_hierarchical_corrections(records):
    fitted = {0: {("global",): {
        "n": len(records),
        "raw": mean(r["persistence_correction_target"] for r in records) if records else 0.0,
        "estimate": mean(r["persistence_correction_target"] for r in records) if records else 0.0,
        "reliability": 1.0 if records else 0.0,
        "between_variance": 0.0,
    }}}
    for level in range(1, 5):
        groups = defaultdict(list)
        representative = {}
        for record in records:
            key = level_key(record, level)
            groups[key].append(record)
            representative[key] = record
        raw_stats = {}
        parent_children = defaultdict(list)
        for key, vals in groups.items():
            targets = [r["persistence_correction_target"] for r in vals]
            raw = mean(targets)
            within = variance(targets)
            se_var = (within / len(vals)) if len(vals) >= 2 and math.isfinite(within) else 0.0
            parent = parent_key(representative[key], level)
            parent_est = fitted[level - 1].get(parent, {}).get("estimate", fitted[0][("global",)]["estimate"])
            raw_stats[key] = {"n": len(vals), "raw": raw, "se_var": se_var, "parent": parent, "parent_est": parent_est}
            parent_children[parent].append(key)
        between_by_parent = {}
        for parent, keys in parent_children.items():
            deviations = [raw_stats[k]["raw"] - raw_stats[k]["parent_est"] for k in keys]
            observed = variance(deviations)
            mean_se = mean(raw_stats[k]["se_var"] for k in keys)
            between_by_parent[parent] = max(0.0, (observed if math.isfinite(observed) else 0.0) - (mean_se if math.isfinite(mean_se) else 0.0))
        fitted[level] = {}
        for key, item in raw_stats.items():
            between = between_by_parent.get(item["parent"], 0.0)
            reliability = (
                between / (between + item["se_var"])
                if item["n"] >= MIN_HIERARCHY_N and between + item["se_var"] > EPS
                else 0.0
            )
            estimate = item["parent_est"] + reliability * (item["raw"] - item["parent_est"])
            fitted[level][key] = {
                **item,
                "estimate": estimate,
                "reliability": reliability,
                "between_variance": between,
            }
    return fitted


def select_correction(fitted, state):
    for level in range(4, 0, -1):
        key = level_key(state, level)
        item = fitted.get(level, {}).get(key)
        if item and item["reliability"] > 0:
            return item["estimate"], item["n"], item["reliability"], level
    item = fitted[0][("global",)]
    return item["estimate"], item["n"], item["reliability"], 0


def build_innovation_paths(rows, seasons, *, anchor="baseline", carry_uncertainty=False):
    calibrations, baseline_paths, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
    states, state_diag = build_innovation_states(rows, seasons, baseline_paths)
    if anchor == "player_residual":
        _, anchor_paths, _, level_adjustments, _ = resid.build_residual_paths(
            rows, seasons, carry_uncertainty=carry_uncertainty
        )
    else:
        anchor_paths = baseline_paths
        level_adjustments = []
    records = correction_records(rows, seasons, calibrations, anchor_paths, states)
    paths = {}
    adjustments = []
    for season in seasons:
        train = [r for r in records if int(r["new_fold"]) <= season - 2]
        fitted = fit_hierarchical_corrections(train)
        variant = {offset: list(anchor_paths[season][offset]) for offset in range(base.HORIZON)}
        if season - 1 in anchor_paths:
            old_y3 = {s.player_id: s for s in anchor_paths[season - 1][2]}
            current_y1 = {s.player_id: s for s in anchor_paths[season][0]}
            adjusted_y2 = []
            for state_y2 in anchor_paths[season][1]:
                pid = state_y2.player_id
                state = states.get(season, {}).get(pid)
                if not state or state["history_n"] < MIN_RESIDUAL_HISTORY or pid not in old_y3 or pid not in current_y1:
                    adjusted_y2.append(state_y2)
                    continue
                correction, n, reliability, level = select_correction(fitted, state)
                near_revision = current_y1[pid].mean - ({s.player_id: s for s in anchor_paths[season - 1][1]}).get(pid, current_y1[pid]).mean
                adjustment = near_revision * correction
                new_mean = max(0.0, state_y2.mean + adjustment)
                adjusted_y2.append(replace(state_y2, mean=new_mean))
                adjustments.append({
                    "forecast_fold": season,
                    "player_id": pid,
                    "anchor": anchor,
                    "near_revision": near_revision,
                    "persistence_correction": correction,
                    "adjustment": adjustment,
                    "anchor_year2_mean": state_y2.mean,
                    "adjusted_year2_mean": new_mean,
                    "fit_n": n,
                    "fit_reliability": reliability,
                    "fit_level": level,
                    **state,
                })
            variant[1] = adjusted_y2
        paths[season] = variant
    return calibrations, paths, states, state_diag, adjustments, records, level_adjustments


def enrich_pairs(pairs, states):
    out = []
    for pair in pairs:
        state = states.get(pair["new_fold"], {}).get(pair["player_id"], {})
        row = dict(pair)
        for key in (
            "history_n", "history_band", "innovation_state", "volatility_band", "volatility_ratio",
            "latest_innovation", "innovation_slope", "innovation_acceleration", "innovation_autocorrelation",
            "innovation_z", "same_sign_count", "same_sign_band", "signed_same_sign_count", "level_component",
        ):
            row[key] = state.get(key, math.nan if key not in {"history_band", "innovation_state", "volatility_band", "same_sign_band"} else "insufficient_history")
        out.append(row)
    return out


def persistence_metrics(rows):
    return resid.persistence_metrics(rows)


def stratified(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    return {name: {"path": audit.path_metrics(vals), "persistence": persistence_metrics(vals)} for name, vals in sorted(groups.items())}


def direct_result(rows, seasons, name, *, anchor="baseline", innovation=False, carry_uncertainty=False):
    if innovation:
        cals, paths, states, state_diag, adjustments, records, level_adjustments = build_innovation_paths(
            rows, seasons, anchor=anchor, carry_uncertainty=carry_uncertainty
        )
    elif anchor == "player_residual":
        cals, paths, state_diag, level_adjustments, _ = resid.build_residual_paths(
            rows, seasons, carry_uncertainty=carry_uncertainty
        )
        states, _ = build_innovation_states(rows, seasons, hier.baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)[1])
        adjustments, records = [], []
    else:
        cals, paths, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
        states, state_diag = build_innovation_states(rows, seasons, paths)
        adjustments, records, level_adjustments = [], [], []
    pairs = audit.build_pair_rows(rows, seasons, cals, paths)
    enriched = enrich_pairs(pairs, states)
    return {
        "name": name,
        "overall": audit.path_metrics(pairs),
        "persistence": persistence_metrics(enriched),
        "horizon_mae": hier.horizon_mae(rows, seasons, paths),
        "survival_brier": hier.survival_brier(pairs),
        "audit_groups": audit.grouped(pairs),
        "subgroups": {
            "history_band": stratified(enriched, "history_band"),
            "innovation_state": stratified(enriched, "innovation_state"),
            "volatility_band": stratified(enriched, "volatility_band"),
            "same_sign_band": stratified(enriched, "same_sign_band"),
        },
    }, paths, states, state_diag, adjustments, records, level_adjustments


def group_lookup(result, dimension, value):
    for row in result["audit_groups"]:
        if row["dimension"] == dimension and row["value"] == value:
            return row
    return None


def feature_diagnostics(records):
    if not records:
        return {}
    target = [r["persistence_correction_target"] for r in records]
    features = [
        "latest_innovation", "innovation_z", "innovation_slope", "innovation_acceleration",
        "innovation_autocorrelation", "signed_same_sign_count", "volatility_ratio",
    ]
    out = {}
    for feature in features:
        pairs = [(float(r[feature]), float(r["persistence_correction_target"])) for r in records if math.isfinite(float(r.get(feature, math.nan)))]
        out[feature] = {
            "n": len(pairs),
            "pearson": corr([x for x, _ in pairs], [y for _, y in pairs]) if pairs else math.nan,
            "spearman": spearman([x for x, _ in pairs], [y for _, y in pairs]) if pairs else math.nan,
        }
    return out


def accepted_gate(baseline, candidate):
    bp = baseline["persistence"]["legacy_all_finite"]
    cp = candidate["persistence"]["legacy_all_finite"]
    bs = baseline["persistence"]["stable_denominator"]
    cs = candidate["persistence"]["stable_denominator"]
    b = baseline["overall"]
    c = candidate["overall"]
    aging_b = group_lookup(baseline, "is_aging_rb", "True")
    aging_c = group_lookup(candidate, "is_aging_rb", "True")
    horizons_ok = (
        candidate["horizon_mae"]["year_2"] <= baseline["horizon_mae"]["year_2"] * (1 + ADJACENT_TOLERANCE)
        and candidate["horizon_mae"]["year_3"] <= baseline["horizon_mae"]["year_3"] * (1 + ADJACENT_TOLERANCE)
    )
    aging_ok = True
    if aging_b and aging_c:
        aging_ok = (
            aging_c["persistence_mae"] <= aging_b["persistence_mae"] * (1 + AGING_RB_TOLERANCE)
            and aging_c["new_slope_mae"] <= aging_b["new_slope_mae"] * (1 + AGING_RB_TOLERANCE)
            and aging_c["new_cumulative_mae"] <= aging_b["new_cumulative_mae"] * (1 + AGING_RB_TOLERANCE)
            and aging_c["far_direction"] >= aging_b["far_direction"] - AGING_RB_TOLERANCE
        )
    tests = {
        "legacy_pearson_gain": cp.get("pearson", math.nan) >= bp.get("pearson", math.nan) + MATERIAL_PERSISTENCE_GAIN,
        "legacy_mae_improves": cp.get("mae", math.inf) < bp.get("mae", math.inf),
        "stable_pearson_gain": cs.get("pearson", math.nan) >= bs.get("pearson", math.nan) + MATERIAL_PERSISTENCE_GAIN,
        "stable_spearman_gain": cs.get("spearman", math.nan) >= bs.get("spearman", math.nan) + MATERIAL_PERSISTENCE_GAIN,
        "stable_mae_improves": cs.get("mae", math.inf) < bs.get("mae", math.inf),
        "far_revision_not_worse": c["far_revision_correlation"] >= b["far_revision_correlation"],
        "slope_correlation_not_worse": c["slope_change_correlation"] >= b["slope_change_correlation"],
        "slope_mae_not_worse": c["new_slope_mae"] <= b["new_slope_mae"],
        "near_revision_within_tolerance": c["near_revision_correlation"] >= b["near_revision_correlation"] - ADJACENT_TOLERANCE,
        "cumulative_within_tolerance": c["new_cumulative_mae"] <= b["new_cumulative_mae"] * (1 + ADJACENT_TOLERANCE),
        "year2_year3_within_tolerance": horizons_ok,
        "aging_rb_guardrail": aging_ok,
    }
    return {
        "pass": all(tests.values()),
        "tests": tests,
        "material_persistence_gain": MATERIAL_PERSISTENCE_GAIN,
        "stable_move_floor": STABLE_PERSISTENCE_MIN_MOVE,
        "min_residual_history": MIN_RESIDUAL_HISTORY,
        "min_hierarchy_n": MIN_HIERARCHY_N,
        "volatility_ratio_threshold": VOLATILITY_RATIO_THRESHOLD,
    }


def focus_groups(result):
    return {
        "elite_qb": group_lookup(result, "is_elite_qb", "True"),
        "young_breakout_wr": group_lookup(result, "is_young_breakout_wr", "True"),
        "young_te": group_lookup(result, "is_young_te", "True"),
        "aging_rb": group_lookup(result, "is_aging_rb", "True"),
    }


def comparison_row(result):
    p = result["persistence"]["stable_denominator"]
    o = result["overall"]
    return {
        "far_revision_correlation": o["far_revision_correlation"],
        "slope_correlation": o["slope_change_correlation"],
        "slope_mae": o["new_slope_mae"],
        "cumulative_mae": o["new_cumulative_mae"],
        "legacy_persistence_correlation": o["persistence_correlation"],
        "legacy_persistence_mae": o["persistence_mae"],
        "stable_persistence_pearson": p.get("pearson", math.nan),
        "stable_persistence_spearman": p.get("spearman", math.nan),
        "stable_persistence_mae": p.get("mae", math.nan),
        "year_2_mae": result["horizon_mae"]["year_2"],
        "year_3_mae": result["horizon_mae"]["year_3"],
    }


def report_text(payload):
    b = payload["variants"]["baseline"]
    i = payload["variants"]["innovation"]
    iu = payload["variants"]["innovation_plus_uncertainty"]
    li = payload["variants"]["level_plus_innovation"]
    bp, ip = b["persistence"]["stable_denominator"], i["persistence"]["stable_denominator"]
    lines = [
        "# Within-Player Trajectory Innovation Dynamics Research — PR #131", "",
        "**Status:** research-only, non-authoritative. Production Forecast/Value unchanged. Recursive uncertainty carry-forward remains research-only. Model B not fitted.", "",
        "## Predeclared design", "",
        f"A player needs at least **{MIN_RESIDUAL_HISTORY} resolved residual seasons**: earlier residuals establish the player's stable level baseline and the latest resolved residual supplies the innovation. A volatility-adjusted innovation is considered large at **{VOLATILITY_RATIO_THRESHOLD:.1f} player-history SD**. Narrow hierarchy cells require **{MIN_HIERARCHY_N} resolved persistence observations** before they may act independently.", "",
        "Innovation is defined after removing stable player-level bias. The challenger estimates only a correction to deeper-horizon revision persistence; Year 1 is never altered by innovation state. The fitted correction is hierarchically empirical-Bayes shrunk through global -> position -> position×career stage -> position×career stage×innovation state -> position×career stage×tier×innovation state×volatility.", "",
        "The frozen acceptance gate requires at least +0.05 improvement in legacy persistence Pearson, stable-denominator Pearson, and stable-denominator Spearman; lower persistence MAE; no degradation in far/slope correlation or slope MAE; Year-2/Year-3 and cumulative MAE within 1%; near correlation within 0.01; and aging-RB persistence/slope/cumulative/decline behavior within 2%.", "",
        "## Primary persistence result", "",
        "| Metric | Baseline | Innovation |", "|---|---:|---:|",
        f"| Legacy persistence Pearson | {b['persistence']['legacy_all_finite'].get('pearson', math.nan):.3f} | {i['persistence']['legacy_all_finite'].get('pearson', math.nan):.3f} |",
        f"| Legacy persistence MAE | {b['persistence']['legacy_all_finite'].get('mae', math.nan):.3f} | {i['persistence']['legacy_all_finite'].get('mae', math.nan):.3f} |",
        f"| Stable persistence Pearson | {bp.get('pearson', math.nan):.3f} | {ip.get('pearson', math.nan):.3f} |",
        f"| Stable persistence Spearman | {bp.get('spearman', math.nan):.3f} | {ip.get('spearman', math.nan):.3f} |",
        f"| Stable persistence MAE | {bp.get('mae', math.nan):.3f} | {ip.get('mae', math.nan):.3f} |", "",
        "## Direct Forecast comparison", "",
        "| Variant | Far corr | Slope corr | Slope MAE | Cumulative MAE | Y2 MAE | Y3 MAE | Far 80% coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in [
        ("baseline", "Current baseline"),
        ("hierarchical", "Hierarchical trajectory state"),
        ("player_residual", "Player average residual"),
        ("innovation", "Innovation dynamics"),
        ("level_plus_innovation", "Level + innovation"),
        ("innovation_plus_uncertainty", "Innovation + repaired uncertainty"),
    ]:
        r = payload["variants"][key]
        o = r["overall"]
        lines.append(
            f"| {label} | {o['far_revision_correlation']:.3f} | {o['slope_change_correlation']:.3f} | {o['new_slope_mae']:.3f} | {o['new_cumulative_mae']:.3f} | {r['horizon_mae']['year_2']:.3f} | {r['horizon_mae']['year_3']:.3f} | {o['far_80_coverage']:.1%} |"
        )
    lines += ["", f"Direct innovation gate: **{'PASS' if payload['gate']['pass'] else 'FAIL'}**.", ""]
    lines += [
        "## Stable-level bias separation", "",
        "The player-average residual and innovation state are evaluated separately and together. The combined variant is diagnostic only unless both components demonstrate independent out-of-time value; better uncertainty coverage cannot rescue a failed mean/persistence challenger.", "",
        "## Uncertainty separation", "",
        f"Innovation mean with baseline uncertainty has far coverage **{i['overall']['far_80_coverage']:.1%}**; the same innovation mean with the already validated research-only recursive variance carry-forward has far coverage **{iu['overall']['far_80_coverage']:.1%}**. The uncertainty result is reported separately from the mean gate.", "",
        "## Guardrails", "",
        "- Market Value, trade value, Team Utility, owner behavior, roster need, and Value outputs are excluded from Forecast fitting.",
        "- No QB bonus, elite override, arbitrary persistence multiplier, or black-box master score is used.",
        "- All innovation features, hierarchy estimates, and persistence targets are chronological and resolved before use.",
        "- Model A may be rerun only if the direct innovation gate passes.",
        "- Production Forecast/Value authority remains unchanged and Model B is not fitted.",
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
        lines += ["", "## Model A retest", "", "Not run: the innovation-dynamics challenger did not clear the direct Forecast gate."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--dynastyprocess-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = base.load_rows(args.career_panel, rc)
    seasons = audit.update_audit.supported_seasons(base, rows, rc)

    baseline, _, _, _, _, _, _ = direct_result(rows, seasons, "baseline")
    innovation, _, states, state_diag, adjustments, records, _ = direct_result(
        rows, seasons, "innovation", innovation=True
    )
    innovation_u, _, _, _, adjustments_u, _, _ = direct_result(
        rows, seasons, "innovation_plus_uncertainty", innovation=True, carry_uncertainty=True
    )
    player_residual, _, _, _, _, _, _ = direct_result(rows, seasons, "player_residual", anchor="player_residual")
    level_plus_innovation, _, _, _, level_innovation_adjustments, level_records, _ = direct_result(
        rows, seasons, "level_plus_innovation", anchor="player_residual", innovation=True
    )
    h_result, _, _ = hier.direct_variant(rows, seasons, "hierarchical", hierarchical=True)
    hierarchical = {
        "name": "hierarchical",
        "overall": h_result["overall"],
        "persistence": {
            "legacy_all_finite": {
                "n": h_result["overall"]["n"],
                "pearson": h_result["overall"]["persistence_correlation"],
                "mae": h_result["overall"]["persistence_mae"],
            },
            "stable_denominator": {"n": 0, "pearson": math.nan, "spearman": math.nan, "mae": math.nan},
        },
        "horizon_mae": h_result["horizon_mae"],
        "survival_brier": h_result["survival_brier"],
        "audit_groups": h_result["groups"],
        "subgroups": {},
    }

    gate = accepted_gate(baseline, innovation)
    variants = {
        "baseline": baseline,
        "hierarchical": hierarchical,
        "player_residual": player_residual,
        "innovation": innovation,
        "level_plus_innovation": level_plus_innovation,
        "innovation_plus_uncertainty": innovation_u,
    }

    def builder(rows_arg, seasons, carry_uncertainty=False):
        cals, paths, _, _, _, _, _ = build_innovation_paths(
            rows_arg, seasons, anchor="baseline", carry_uncertainty=carry_uncertainty
        )
        return cals, paths, []

    payload = {
        "research_only": True,
        "production_forecast_changed": False,
        "production_value_changed": False,
        "uncertainty_repair_promoted": False,
        "model_b_fitted": False,
        "predeclared": {
            "min_residual_history": MIN_RESIDUAL_HISTORY,
            "min_hierarchy_n": MIN_HIERARCHY_N,
            "volatility_ratio_threshold": VOLATILITY_RATIO_THRESHOLD,
            "stable_move_floor": STABLE_PERSISTENCE_MIN_MOVE,
            "material_persistence_gain": MATERIAL_PERSISTENCE_GAIN,
            "adjacent_tolerance": ADJACENT_TOLERANCE,
            "aging_rb_tolerance": AGING_RB_TOLERANCE,
        },
        "variants": variants,
        "comparison": {name: comparison_row(result) for name, result in variants.items()},
        "focus_groups": {name: focus_groups(result) for name, result in variants.items()},
        "feature_diagnostics": feature_diagnostics(records),
        "level_plus_innovation_feature_diagnostics": feature_diagnostics(level_records),
        "gate": gate,
        "model_a_retest": hier.model_a_retest(rows, seasons, args.dynastyprocess_repo, builder) if gate["pass"] else None,
    }

    (args.output_dir / "within_player_trajectory_innovation_results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    text = report_text(payload)
    (args.output_dir / "within_player_trajectory_innovation_report.md").write_text(text, encoding="utf-8")

    if state_diag:
        with (args.output_dir / "within_player_trajectory_innovation_states.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(state_diag[0].keys()))
            writer.writeheader(); writer.writerows(state_diag)
    if adjustments:
        with (args.output_dir / "within_player_trajectory_innovation_adjustments.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(adjustments[0].keys()))
            writer.writeheader(); writer.writerows(adjustments)
    if level_innovation_adjustments:
        with (args.output_dir / "within_player_trajectory_level_plus_innovation_adjustments.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(level_innovation_adjustments[0].keys()))
            writer.writeheader(); writer.writerows(level_innovation_adjustments)

    print(text)


if __name__ == "__main__":
    main()
