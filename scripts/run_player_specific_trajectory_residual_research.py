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
rc = load_registered(HERE / "run_career_calibration.py", "pr131_player_resid_career")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_player_resid_base")
audit = load_registered(HERE / "run_forecast_trajectory_shape_audit.py", "pr131_player_resid_audit")
chall = load_registered(HERE / "run_forecast_trajectory_challengers.py", "pr131_player_resid_chall")
hier = load_registered(HERE / "run_hierarchical_trajectory_state_research.py", "pr131_player_resid_hier")

MIN_PLAYER_HISTORY = 2
MIN_COHORT_PLAYERS = 20
MIN_COHORT_RESIDUALS = 100
MIN_GAMMA_N = 100
STABLE_PERSISTENCE_MIN_MOVE = 10.0
MATERIAL_PERSISTENCE_CORR_GAIN = 0.05
ADJACENT_TOLERANCE = 0.01
AGING_RB_TOLERANCE = 0.02
EPS = 1e-9


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else math.nan


def variance(xs):
    xs = list(xs)
    if len(xs) < 2:
        return math.nan
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def corr(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 2:
        return math.nan
    xm, ym = mean(xs), mean(ys)
    xx = sum((x - xm) ** 2 for x in xs)
    yy = sum((y - ym) ** 2 for y in ys)
    if xx <= EPS or yy <= EPS:
        return 0.0
    return sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / math.sqrt(xx * yy)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + j - 1) / 2.0
        for k in range(i, j):
            out[order[k]] = r
        i = j
    return out


def spearman(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 2:
        return math.nan
    return corr(ranks(xs), ranks(ys))


def one_step_residual_records(rows, seasons, baselines):
    actual = {(r.season, r.player_id): r.current for r in rows}
    out = []
    for season in seasons:
        meta = hier.source_meta(rows, season)
        states = {s.player_id: s for s in baselines[season][0]}
        for pid in sorted(set(states) & set(meta)):
            target = actual.get((season, pid), 0.0)
            s = states[pid]
            out.append({
                "forecast_fold": season,
                "target_season": season,
                "player_id": pid,
                **meta[pid],
                "forecast": s.mean,
                "actual": target,
                "residual": target - s.mean,
            })
    return out


def production_history(rows):
    out = defaultdict(list)
    for r in rows:
        out[r.player_id].append((r.season, r.current))
    for vals in out.values():
        vals.sort()
    return out


def latest_production_features(prod_hist, player_id, cutoff):
    vals = [(s, p) for s, p in prod_hist.get(player_id, []) if s <= cutoff - 1]
    recent = vals[-3:]
    points = [p for _, p in recent]
    if not points:
        return {
            "production_history_n": 0,
            "production_slope": math.nan,
            "production_volatility": math.nan,
            "production_pattern": "insufficient",
            "career_high_recency": math.nan,
        }
    slope = (points[-1] - points[0]) / (len(points) - 1) if len(points) >= 2 else 0.0
    vol = statistics.pstdev(points) if len(points) >= 2 else 0.0
    pattern = "mixed"
    if len(points) >= 3 and all(points[i] > points[i-1] for i in range(1, len(points))):
        pattern = "sustained_improvement"
    elif len(points) >= 3 and all(points[i] < points[i-1] for i in range(1, len(points))):
        pattern = "sustained_decline"
    elif len(points) >= 2 and points[-1] > points[-2]:
        pattern = "latest_improvement"
    elif len(points) >= 2 and points[-1] < points[-2]:
        pattern = "latest_decline"
    all_vals = [(s, p) for s, p in vals]
    career_high = max((p for _, p in all_vals), default=points[-1])
    high_seasons = [s for s, p in all_vals if abs(p - career_high) <= EPS]
    high_recency = (cutoff - 1 - max(high_seasons)) if high_seasons else math.nan
    return {
        "production_history_n": len(vals),
        "production_slope": slope,
        "production_volatility": vol,
        "production_pattern": pattern,
        "career_high_recency": high_recency,
    }


def cohort_keys(meta):
    return [
        ("position_stage_tier", meta["position"], meta["career_stage"], meta["production_tier"]),
        ("position_stage", meta["position"], meta["career_stage"]),
        ("position", meta["position"]),
        ("global",),
    ]


def raw_player_summaries(residual_rows, cutoff, active_meta):
    by_player = defaultdict(list)
    for r in residual_rows:
        if r["target_season"] <= cutoff - 1:
            by_player[r["player_id"]].append(r)
    out = {}
    for pid, meta in active_meta.items():
        hist = sorted(by_player.get(pid, []), key=lambda x: x["target_season"])
        residuals = [r["residual"] for r in hist]
        n = len(residuals)
        out[pid] = {
            "player_id": pid,
            **meta,
            "history_n": n,
            "residual_mean": mean(residuals) if residuals else 0.0,
            "residual_sd": statistics.stdev(residuals) if n >= 2 else math.nan,
            "residual_last": residuals[-1] if residuals else math.nan,
            "residuals": residuals,
        }
    return out


def fit_cohort_prior(items):
    eligible = [x for x in items if x["history_n"] >= MIN_PLAYER_HISTORY]
    if len(eligible) < MIN_COHORT_PLAYERS:
        return None
    total_residuals = sum(x["history_n"] for x in eligible)
    if total_residuals < MIN_COHORT_RESIDUALS:
        return None
    means = [x["residual_mean"] for x in eligible]
    prior_mean = mean(means)
    obs_var = variance(means)
    se_vars = []
    within_num = 0.0
    within_den = 0
    for x in eligible:
        if x["history_n"] >= 2 and math.isfinite(x["residual_sd"]):
            v = x["residual_sd"] ** 2
            se_vars.append(v / x["history_n"])
            within_num += (x["history_n"] - 1) * v
            within_den += x["history_n"] - 1
    pooled_within = within_num / within_den if within_den else 0.0
    mean_se = mean(se_vars) if se_vars else 0.0
    between = max(0.0, (obs_var if math.isfinite(obs_var) else 0.0) - mean_se)
    return {
        "player_n": len(eligible),
        "residual_n": total_residuals,
        "prior_mean": prior_mean,
        "between_variance": between,
        "pooled_within_variance": pooled_within,
    }


def build_cohort_priors(summaries):
    buckets = defaultdict(list)
    for x in summaries.values():
        for key in cohort_keys(x):
            buckets[key].append(x)
    return {key: fit_cohort_prior(vals) for key, vals in buckets.items()}


def select_prior(priors, meta):
    for key in cohort_keys(meta):
        item = priors.get(key)
        if item is not None:
            return item, key[0]
    return {
        "player_n": 0,
        "residual_n": 0,
        "prior_mean": 0.0,
        "between_variance": 0.0,
        "pooled_within_variance": 0.0,
    }, "none"


def residual_state_label(x, cohort_within):
    n = x["history_n"]
    if n < MIN_PLAYER_HISTORY:
        return "insufficient_history"
    rs = x["residuals"]
    if n >= 3 and all(v > 0 for v in rs[-3:]):
        return "stable_positive"
    if n >= 3 and all(v < 0 for v in rs[-3:]):
        return "stable_negative"
    prior_mean = mean(rs[:-1]) if n >= 2 else 0.0
    if n >= 2 and rs[-1] > 0 and prior_mean <= 0:
        return "one_year_spike"
    if n >= 2 and rs[-1] < 0 and prior_mean >= 0:
        return "one_year_collapse"
    player_var = x["residual_sd"] ** 2 if math.isfinite(x["residual_sd"]) else 0.0
    if player_var > cohort_within and cohort_within > 0:
        return "volatile_mixed"
    return "mixed_stable"


def build_player_states(rows, seasons, residual_rows):
    prod_hist = production_history(rows)
    states = {}
    diagnostics = []
    for season in seasons:
        meta = hier.source_meta(rows, season)
        summaries = raw_player_summaries(residual_rows, season, meta)
        priors = build_cohort_priors(summaries)
        season_states = {}
        for pid, x in summaries.items():
            prior, scope = select_prior(priors, x)
            n = x["history_n"]
            reliability = 0.0
            component = 0.0
            if n >= MIN_PLAYER_HISTORY:
                if math.isfinite(x["residual_sd"]):
                    sampling_var = (x["residual_sd"] ** 2) / n
                else:
                    sampling_var = prior["pooled_within_variance"] / max(1, n)
                between = prior["between_variance"]
                reliability = between / (between + sampling_var) if between + sampling_var > EPS else 0.0
                component = reliability * (x["residual_mean"] - prior["prior_mean"])
            pf = latest_production_features(prod_hist, pid, season)
            label = residual_state_label(x, prior["pooled_within_variance"])
            state = {
                **x,
                **pf,
                "prior_scope": scope,
                "prior_mean": prior["prior_mean"],
                "prior_player_n": prior["player_n"],
                "prior_residual_n": prior["residual_n"],
                "between_variance": prior["between_variance"],
                "pooled_within_variance": prior["pooled_within_variance"],
                "reliability": reliability,
                "player_residual_component": component,
                "trajectory_state": label,
            }
            season_states[pid] = state
            diagnostics.append({"forecast_fold": season, **{k: v for k, v in state.items() if k != "residuals"}})
        states[season] = season_states
    return states, diagnostics


def gamma_keys(state, horizon):
    return [
        ("cell", horizon, state["position"], state["career_stage"], state["production_tier"], state["trajectory_state"]),
        ("position_stage_tier", horizon, state["position"], state["career_stage"], state["production_tier"]),
        ("position_stage", horizon, state["position"], state["career_stage"]),
        ("position", horizon, state["position"]),
        ("global", horizon),
    ]


def fit_gamma(records):
    denom = sum(r["player_residual_component"] ** 2 for r in records)
    if denom <= EPS:
        return 0.0
    return sum(r["player_residual_component"] * r["needed_adjustment"] for r in records) / denom


def fit_gamma_hierarchy(records):
    buckets = defaultdict(list)
    for r in records:
        for key in gamma_keys(r, r["horizon"]):
            buckets[key].append(r)
    return {key: {"n": len(vals), "gamma": fit_gamma(vals)} for key, vals in buckets.items()}


def select_gamma(fitted, state, horizon):
    keys = gamma_keys(state, horizon)
    for key in keys[:-1]:
        item = fitted.get(key)
        if item and item["n"] >= MIN_GAMMA_N:
            return item["gamma"], item["n"], key[0]
    item = fitted.get(keys[-1], {"n": 0, "gamma": 0.0})
    return item["gamma"], item["n"], "global"


def application_records(rows, seasons, baselines, player_states):
    actual = {(r.season, r.player_id): r.current for r in rows}
    out = []
    for season in seasons:
        for offset in (1, 2):
            horizon = offset + 1
            bmap = {s.player_id: s for s in baselines[season][offset]}
            for pid in sorted(set(bmap) & set(player_states[season])):
                st = player_states[season][pid]
                if st["history_n"] < MIN_PLAYER_HISTORY:
                    continue
                target_season = season + offset
                target = actual.get((target_season, pid), 0.0)
                out.append({
                    "forecast_fold": season,
                    "target_season": target_season,
                    "horizon": horizon,
                    "player_id": pid,
                    **{k: v for k, v in st.items() if k != "residuals"},
                    "baseline_mean": bmap[pid].mean,
                    "target": target,
                    "needed_adjustment": target - bmap[pid].mean,
                })
    return out


def build_residual_paths(rows, seasons, *, carry_uncertainty=False):
    calibrations, baselines, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
    residual_rows = one_step_residual_records(rows, seasons, baselines)
    states, state_diag = build_player_states(rows, seasons, residual_rows)
    apps = application_records(rows, seasons, baselines, states)
    paths = {}
    adjustment_rows = []
    for season in seasons:
        train = [r for r in apps if r["target_season"] <= season - 1]
        fitted = fit_gamma_hierarchy(train)
        variant = {}
        for offset in range(base.HORIZON):
            blended = []
            for b in baselines[season][offset]:
                if offset == 0 or b.player_id not in states[season]:
                    blended.append(b)
                    continue
                st = states[season][b.player_id]
                if st["history_n"] < MIN_PLAYER_HISTORY:
                    blended.append(b)
                    continue
                horizon = offset + 1
                gamma, n, scope = select_gamma(fitted, st, horizon)
                adjustment = gamma * st["player_residual_component"]
                m = max(0.0, b.mean + adjustment)
                blended.append(replace(b, mean=m))
                adjustment_rows.append({
                    "forecast_fold": season,
                    "player_id": b.player_id,
                    "horizon": horizon,
                    "baseline_mean": b.mean,
                    "adjusted_mean": m,
                    "adjustment": adjustment,
                    "gamma": gamma,
                    "gamma_n": n,
                    "gamma_scope": scope,
                    **{k: v for k, v in st.items() if k != "residuals"},
                    "carry_uncertainty": carry_uncertainty,
                })
            variant[offset] = blended
        paths[season] = variant
    return calibrations, paths, state_diag, adjustment_rows, states


def enrich_pairs(pairs, states):
    out = []
    for r in pairs:
        st = states.get(r["new_fold"], {}).get(r["player_id"], {})
        x = dict(r)
        x["history_n"] = st.get("history_n", 0)
        x["trajectory_state"] = st.get("trajectory_state", "insufficient_history")
        x["production_pattern"] = st.get("production_pattern", "insufficient")
        x["player_residual_component"] = st.get("player_residual_component", 0.0)
        x["reliability"] = st.get("reliability", 0.0)
        if x["history_n"] < MIN_PLAYER_HISTORY:
            x["history_band"] = "0-1"
        elif x["history_n"] <= 3:
            x["history_band"] = "2-3"
        elif x["history_n"] <= 5:
            x["history_band"] = "4-5"
        else:
            x["history_band"] = "6+"
        out.append(x)
    return out


def persistence_metrics(pair_rows):
    valid = [r for r in pair_rows if math.isfinite(float(r["revision_persistence"])) and math.isfinite(float(r["needed_persistence"]))]
    stable = [
        r for r in valid
        if abs(float(r["near_revision"])) >= STABLE_PERSISTENCE_MIN_MOVE
        and abs(float(r["near_needed_revision"])) >= STABLE_PERSISTENCE_MIN_MOVE
    ]
    def calc(rows):
        if not rows:
            return {"n": 0}
        modeled = [float(r["revision_persistence"]) for r in rows]
        needed = [float(r["needed_persistence"]) for r in rows]
        return {
            "n": len(rows),
            "pearson": corr(modeled, needed),
            "spearman": spearman(modeled, needed),
            "mae": mean(abs(a-b) for a, b in zip(modeled, needed)),
        }
    result = {"legacy_all_finite": calc(valid), "stable_denominator": calc(stable)}
    if stable:
        ordered = sorted(stable, key=lambda r: float(r["revision_persistence"]))
        bins = []
        for q in range(4):
            lo = len(ordered) * q // 4
            hi = len(ordered) * (q + 1) // 4
            subset = ordered[lo:hi]
            bins.append({
                "quantile": q + 1,
                "n": len(subset),
                "modeled_mean": mean(float(r["revision_persistence"]) for r in subset),
                "needed_mean": mean(float(r["needed_persistence"]) for r in subset),
            })
        result["stable_quantiles"] = bins
        result["high_low_needed_gap"] = bins[-1]["needed_mean"] - bins[0]["needed_mean"]
    return result


def stratified(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[str(r.get(key))].append(r)
    return {name: {"path": audit.path_metrics(vals), "persistence": persistence_metrics(vals)} for name, vals in sorted(groups.items())}


def direct_variant(rows, seasons, name, *, residual=False, carry_uncertainty=False):
    if residual:
        cals, paths, state_diag, adjustments, states = build_residual_paths(rows, seasons, carry_uncertainty=carry_uncertainty)
    else:
        cals, paths, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=carry_uncertainty)
        state_diag, adjustments = [], []
        residual_rows = one_step_residual_records(rows, seasons, paths)
        states, _ = build_player_states(rows, seasons, residual_rows)
    pairs = audit.build_pair_rows(rows, seasons, cals, paths)
    enriched = enrich_pairs(pairs, states)
    return {
        "name": name,
        "overall": audit.path_metrics(pairs),
        "persistence": persistence_metrics(enriched),
        "horizon_mae": hier.horizon_mae(rows, seasons, paths),
        "survival_brier": hier.survival_brier(pairs),
        "subgroups": {
            "history_band": stratified(enriched, "history_band"),
            "trajectory_state": stratified(enriched, "trajectory_state"),
            "production_pattern": stratified(enriched, "production_pattern"),
        },
        "audit_groups": audit.grouped(pairs),
    }, paths, state_diag, adjustments


def group_lookup(result, dimension, value):
    for row in result["audit_groups"]:
        if row["dimension"] == dimension and row["value"] == value:
            return row
    return None


def accepted_gate(baseline, candidate):
    b, c = baseline["overall"], candidate["overall"]
    bp = baseline["persistence"]["legacy_all_finite"]
    cp = candidate["persistence"]["legacy_all_finite"]
    bs = baseline["persistence"]["stable_denominator"]
    cs = candidate["persistence"]["stable_denominator"]
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
        )
    return {
        "pass": (
            cp.get("pearson", math.nan) >= bp.get("pearson", math.nan) + MATERIAL_PERSISTENCE_CORR_GAIN
            and cp.get("mae", math.inf) < bp.get("mae", math.inf)
            and cs.get("spearman", math.nan) >= bs.get("spearman", math.nan) + MATERIAL_PERSISTENCE_CORR_GAIN
            and c["far_revision_correlation"] >= b["far_revision_correlation"]
            and c["slope_change_correlation"] >= b["slope_change_correlation"]
            and c["new_slope_mae"] <= b["new_slope_mae"]
            and c["near_revision_correlation"] >= b["near_revision_correlation"] - ADJACENT_TOLERANCE
            and c["new_cumulative_mae"] <= b["new_cumulative_mae"] * (1 + ADJACENT_TOLERANCE)
            and horizons_ok
            and aging_ok
        ),
        "material_persistence_corr_gain": MATERIAL_PERSISTENCE_CORR_GAIN,
        "stable_move_floor": STABLE_PERSISTENCE_MIN_MOVE,
        "year2_year3_within_1pct": horizons_ok,
        "aging_rb_guardrail": aging_ok,
    }


def focus_groups(result):
    return {
        "elite_qb": group_lookup(result, "is_elite_qb", "True"),
        "young_breakout_wr": group_lookup(result, "is_young_breakout_wr", "True"),
        "young_te": group_lookup(result, "is_young_te", "True"),
        "aging_rb": group_lookup(result, "is_aging_rb", "True"),
    }


def report_text(payload):
    b = payload["variants"]["baseline_mean_baseline_uncertainty"]
    c = payload["variants"]["player_residual_mean_baseline_uncertainty"]
    cu = payload["variants"]["player_residual_mean_repaired_uncertainty"]
    bp, cp = b["persistence"]["legacy_all_finite"], c["persistence"]["legacy_all_finite"]
    bs, cs = b["persistence"]["stable_denominator"], c["persistence"]["stable_denominator"]
    bo, co = b["overall"], c["overall"]
    lines = [
        "# Player-Specific Multi-Season Trajectory Residual Research — PR #131", "",
        "**Status:** research-only, non-authoritative. Production Forecast/Value unchanged. Model B not fitted.", "",
        "## Player-state definition", "",
        "The player-specific state is built from multiple resolved one-step Forecast residuals: realized production minus the point-in-time cohort Forecast that existed before that season. At least two resolved residuals are required before a player-specific component can act. The player mean residual is empirical-Bayes shrunk toward a position/career-stage/production-tier hierarchy using chronologically available between-player variance and the player's own sampling variance. This makes longer, more stable histories earn more player-specific weight while sparse/volatile histories shrink toward cohort evidence.", "",
        f"Declared sufficiency: player history >= **{MIN_PLAYER_HISTORY}** seasons; cohort prior >= **{MIN_COHORT_PLAYERS}** players and **{MIN_COHORT_RESIDUALS}** residuals; horizon translation cell >= **{MIN_GAMMA_N}** resolved applications.", "",
        "The challenger leaves Year 1 unchanged. For Years 2-3, a chronologically fitted hierarchy estimates how much of the shrunken player-specific residual historically persists at that horizon. No QB bonus, elite override, market input, Value patch, or universal persistence multiplier is used.", "",
        "## Primary persistence target", "",
        "| Metric | Baseline | Player residual |", "|---|---:|---:|",
        f"| Legacy persistence Pearson | {bp.get('pearson', math.nan):.3f} | {cp.get('pearson', math.nan):.3f} |",
        f"| Legacy persistence MAE | {bp.get('mae', math.nan):.3f} | {cp.get('mae', math.nan):.3f} |",
        f"| Stable-denominator persistence Pearson | {bs.get('pearson', math.nan):.3f} | {cs.get('pearson', math.nan):.3f} |",
        f"| Stable-denominator persistence Spearman | {bs.get('spearman', math.nan):.3f} | {cs.get('spearman', math.nan):.3f} |",
        f"| Stable-denominator persistence MAE | {bs.get('mae', math.nan):.3f} | {cs.get('mae', math.nan):.3f} |", "",
        "## Adjacent Forecast targets", "",
        "| Metric | Baseline | Player residual |", "|---|---:|---:|",
        f"| Far revision correlation | {bo['far_revision_correlation']:.3f} | {co['far_revision_correlation']:.3f} |",
        f"| Slope correlation | {bo['slope_change_correlation']:.3f} | {co['slope_change_correlation']:.3f} |",
        f"| Slope MAE | {bo['new_slope_mae']:.3f} | {co['new_slope_mae']:.3f} |",
        f"| Cumulative MAE | {bo['new_cumulative_mae']:.3f} | {co['new_cumulative_mae']:.3f} |",
        f"| Year 1 MAE | {b['horizon_mae']['year_1']:.3f} | {c['horizon_mae']['year_1']:.3f} |",
        f"| Year 2 MAE | {b['horizon_mae']['year_2']:.3f} | {c['horizon_mae']['year_2']:.3f} |",
        f"| Year 3 MAE | {b['horizon_mae']['year_3']:.3f} | {c['horizon_mae']['year_3']:.3f} |",
        f"| Near/far 80% coverage | {bo['near_80_coverage']:.1%}/{bo['far_80_coverage']:.1%} | {co['near_80_coverage']:.1%}/{co['far_80_coverage']:.1%} |",
        f"| With repaired uncertainty far coverage | — | {cu['overall']['far_80_coverage']:.1%} |", "",
        f"Direct player-residual gate: **{'PASS' if payload['gate']['pass'] else 'FAIL'}**.", "",
        "## Guardrails", "",
        "- Every personal residual and every fitted horizon translation uses only outcomes resolved before the historical cutoff.",
        "- Single-season history cannot activate a player-specific component.",
        "- Market Value, Team Utility, owner behavior, roster need, and Value outputs are excluded.",
        "- Recursive uncertainty carry-forward remains a separate research-only component.",
        "- No production authority changes and Model B remains blocked unless the direct Forecast gate clears.",
    ]
    if payload.get("model_a_retest"):
        x = payload["model_a_retest"]
        lines += ["", "## Model A unchanged-economics retest", "",
                  f"- MAE: **{x['model_a_mae']:.3f}** vs affine **{x['affine_mae']:.3f}** ({x['mae_improvement']:.1%} improvement).",
                  f"- Calibrated nominal-80% coverage: **{x['coverage']:.1%}**.",
                  f"- Economic checks passed: **{x['economic_checks_passed']}/6**.",
                  f"- Elite-QB longevity: `{json.dumps(x['economic_checks']['elite_qb_longevity'], sort_keys=True)}`",
                  f"- Appreciation/decline: `{json.dumps(x['economic_checks']['expected_appreciation_decline'], sort_keys=True)}`"]
    else:
        lines += ["", "## Model A retest", "", "Not run: the player-specific residual mean challenger did not clear the direct Forecast gate."]
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

    b0, _, _, _ = direct_variant(rows, seasons, "baseline_mean_baseline_uncertainty")
    bu, _, _, _ = direct_variant(rows, seasons, "baseline_mean_repaired_uncertainty", carry_uncertainty=True)
    c0, _, states, adjustments = direct_variant(rows, seasons, "player_residual_mean_baseline_uncertainty", residual=True)
    cu, _, states_u, adjustments_u = direct_variant(rows, seasons, "player_residual_mean_repaired_uncertainty", residual=True, carry_uncertainty=True)
    gate = accepted_gate(b0, c0)

    variants = {x["name"]: x for x in (b0, bu, c0, cu)}
    focus = {name: focus_groups(result) for name, result in variants.items()}

    def builder(rows_arg, seasons, carry_uncertainty=False):
        cals, paths, _, _, _ = build_residual_paths(rows_arg, seasons, carry_uncertainty=carry_uncertainty)
        return cals, paths, []

    payload = {
        "research_only": True,
        "production_forecast_changed": False,
        "production_value_changed": False,
        "uncertainty_repair_promoted": False,
        "model_b_fitted": False,
        "min_player_history": MIN_PLAYER_HISTORY,
        "min_cohort_players": MIN_COHORT_PLAYERS,
        "min_cohort_residuals": MIN_COHORT_RESIDUALS,
        "min_gamma_n": MIN_GAMMA_N,
        "hierarchy": ["position×career_stage×production_tier", "position×career_stage", "position", "global"],
        "variants": variants,
        "focus_groups": focus,
        "gate": gate,
        "model_a_retest": hier.model_a_retest(rows, seasons, args.dynastyprocess_repo, builder) if gate["pass"] else None,
    }
    (args.output_dir / "player_specific_trajectory_residual_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    text = report_text(payload)
    (args.output_dir / "player_specific_trajectory_residual_report.md").write_text(text, encoding="utf-8")
    if states:
        with (args.output_dir / "player_specific_trajectory_residual_states.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(states[0].keys()))
            w.writeheader(); w.writerows(states)
    if adjustments:
        with (args.output_dir / "player_specific_trajectory_residual_adjustments.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(adjustments[0].keys()))
            w.writeheader(); w.writerows(adjustments)
    print(text)


if __name__ == "__main__":
    main()
