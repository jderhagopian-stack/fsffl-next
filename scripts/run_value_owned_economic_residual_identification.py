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
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIMARY = "12t_sf_2rb_3wr_1te_1flex"
ONE_QB = "12t_1qb_2rb_3wr_1te_1flex"
CANDIDATE = "marginal_lineup_opportunity"
TAIL_Q = 0.90
MID_LO = 0.40
MID_HI = 0.80
MIN_TAIL_N = 20
MIN_FOLD_GAPS = 8
MATERIAL_NORMALIZED_GAP = 0.10
MIN_FOLD_T = 2.0
MIN_SIGN_STABILITY = 0.65
MIN_SENSITIVITY_RETENTION = 0.60
MIN_FORMAT_RETENTION = 0.50
MIN_POSITION_SIGN_COUNT = 3
MIN_MODEL_B_MAE_GAIN = 0.02
MIN_MODEL_B_FOLD_WIN_RATE = 0.60
TARGET_COVERAGE_LOW = 0.70
TARGET_COVERAGE_HIGH = 0.90
Z80 = 1.2815515655446004
EPS = 1e-9


def load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rcmod = load_registered(HERE / "run_career_calibration.py", "pr131_value_resid_career")
base = load_registered(HERE / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_value_resid_base")
repair = load_registered(HERE / "run_multiyear_intrinsic_model_a_repair.py", "pr131_value_resid_repair")
hier = load_registered(HERE / "run_hierarchical_trajectory_state_research.py", "pr131_value_resid_hier")
playerres = load_registered(HERE / "run_player_specific_trajectory_residual_research.py", "pr131_value_resid_player")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else math.nan


def sd(xs):
    xs = list(xs)
    return statistics.stdev(xs) if len(xs) >= 2 else math.nan


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
    values = list(values)
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def spearman(xs, ys):
    return corr(ranks(xs), ranks(ys)) if len(list(xs)) >= 2 else math.nan


def quantile(values, q):
    xs = sorted(values)
    if not xs:
        return math.nan
    if len(xs) == 1:
        return xs[0]
    p = q * (len(xs) - 1)
    lo, hi = int(math.floor(p)), int(math.ceil(p))
    if lo == hi:
        return xs[lo]
    f = p - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def sign(x):
    return 1 if x > EPS else -1 if x < -EPS else 0


def career_stage(experience):
    if experience <= 2:
        return "rookie_or_year2"
    if experience <= 4:
        return "young"
    if experience <= 8:
        return "prime"
    return "veteran"


def supported_seasons(rows):
    max_target = max(r.season for r in rows) - (base.HORIZON - 1)
    out = []
    for season in range(min(r.season for r in rows) + 1, max_target + 1):
        if base.FoldCalibration(rows, season, rcmod).supported():
            out.append(season)
    return out


def evaluate_from_paths(rows, season, context_id, paths):
    calibration = base.FoldCalibration(rows, season, rcmod)
    forecast_rep = {o: base.replacement_levels(paths[o], context_id, CANDIDATE) for o in range(base.HORIZON)}
    realized_rep = {o: base.replacement_levels(base.actual_states(rows, season + o), context_id, CANDIDATE) for o in range(base.HORIZON)}
    actual = {o: {r.player_id: r for r in rows if r.season == season + o} for o in range(base.HORIZON)}
    path = {o: {s.player_id: s for s in paths[o]} for o in range(base.HORIZON)}
    prior = {r.player_id: r for r in rows if r.season == season - 1}
    evals, diagnostics = [], []
    for player_id, first in path[0].items():
        if player_id not in prior:
            continue
        model_a = model_var = realized = 0.0
        forecast_surpluses, weighted_surpluses = [], []
        for offset, weight in enumerate(base.ANNUAL_WEIGHTS):
            state = path[offset][player_id]
            rep_mean, rep_sd = forecast_rep[offset][state.position]
            raw_surplus = max(0.0, state.mean - rep_mean)
            forecast_surpluses.append(raw_surplus)
            weighted_surpluses.append(weight * raw_surplus)
            model_a += weight * raw_surplus
            if state.mean > rep_mean:
                model_var += weight**2 * (state.sd**2 + rep_sd**2)
            actual_row = actual[offset].get(player_id)
            actual_points = actual_row.current if actual_row is not None else 0.0
            realized += weight * max(0.0, actual_points - realized_rep[offset][state.position][0])
        p = prior[player_id]
        source = base.State(p.player_id, p.position, p.current, 0.0, p.age, p.experience, (p.production_quartile - 0.5) / 4)
        survival = float(calibration.transition(source)["survival"])
        erow = base.EvalRow(
            player_id=player_id,
            position=first.position,
            season=season,
            model_a=model_a,
            model_a_sd=math.sqrt(max(0.0, model_var)),
            affine_feature=first.mean,
            realized=realized,
            age=first.age,
            experience=p.experience + 1,
        )
        evals.append(erow)
        total_raw = sum(forecast_surpluses)
        diagnostics.append({
            "season": season,
            "player_id": player_id,
            "position": first.position,
            "age": first.age,
            "experience": p.experience + 1,
            "career_stage": career_stage(p.experience + 1),
            "model_a": model_a,
            "model_a_sd": erow.model_a_sd,
            "realized": realized,
            "residual": realized - model_a,
            "affine_feature": first.mean,
            "raw_surplus_sum": total_raw,
            "y1_surplus": forecast_surpluses[0],
            "y2_surplus": forecast_surpluses[1],
            "y3_surplus": forecast_surpluses[2],
            "y1_weighted": weighted_surpluses[0],
            "y2_weighted": weighted_surpluses[1],
            "y3_weighted": weighted_surpluses[2],
            "surplus_concentration": max(weighted_surpluses) / model_a if model_a > EPS else 0.0,
            "terminal_share": weighted_surpluses[2] / model_a if model_a > EPS else 0.0,
            "uncertainty_ratio": erow.model_a_sd / max(1.0, model_a),
            "source_survival_probability": survival,
            "league_context": context_id,
        })
    return evals, diagnostics


def build_variant(rows, seasons, paths_by_season, context_id):
    fold_evals, all_rows = {}, []
    for season in seasons:
        evals, diag = evaluate_from_paths(rows, season, context_id, paths_by_season[season])
        fold_evals[season] = evals
        all_rows.extend(diag)
    add_rank_features(all_rows)
    return fold_evals, all_rows


def add_rank_features(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["season"], r["position"])].append(r)
    for group in groups.values():
        ordered = sorted(group, key=lambda r: (r["model_a"], r["player_id"]))
        n = len(ordered)
        vals = [r["model_a"] for r in ordered]
        knot = quantile(vals, TAIL_Q)
        for i, r in enumerate(ordered):
            r["surplus_percentile"] = (i + 0.5) / n if n else 0.5
            r["elite_tail"] = r["surplus_percentile"] >= TAIL_Q
            r["middle_reference"] = MID_LO <= r["surplus_percentile"] < MID_HI
            r["tail_knot"] = knot
            r["tail_hinge"] = max(0.0, r["model_a"] - knot)


def tail_stats(rows, residual_key="residual"):
    tail = [r for r in rows if r["elite_tail"]]
    mid = [r for r in rows if r["middle_reference"]]
    if len(tail) < MIN_TAIL_N or len(mid) < MIN_TAIL_N:
        return {"tail_n": len(tail), "middle_n": len(mid), "gap": math.nan, "normalized_gap": math.nan}
    gap = mean(r[residual_key] for r in tail) - mean(r[residual_key] for r in mid)
    realized_sd = statistics.pstdev([r["realized"] for r in rows]) or 1.0
    return {
        "tail_n": len(tail),
        "middle_n": len(mid),
        "tail_mean_residual": mean(r[residual_key] for r in tail),
        "middle_mean_residual": mean(r[residual_key] for r in mid),
        "gap": gap,
        "normalized_gap": gap / realized_sd,
    }


def fold_tail_stats(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["season"]].append(r)
    out = []
    for season, vals in sorted(by.items()):
        s = tail_stats(vals)
        if math.isfinite(s.get("gap", math.nan)):
            out.append({"season": season, **s})
    return out


def residual_summary(rows, label):
    t = tail_stats(rows)
    fold = fold_tail_stats(rows)
    gaps = [x["gap"] for x in fold]
    gap_mean = mean(gaps)
    gap_sd = sd(gaps)
    tstat = gap_mean / (gap_sd / math.sqrt(len(gaps))) if len(gaps) >= 2 and gap_sd > EPS else math.nan
    agg_sign = sign(t.get("gap", 0.0))
    stability = mean(sign(x) == agg_sign for x in gaps) if gaps and agg_sign else 0.0
    residuals = [r["residual"] for r in rows]
    lo, hi = quantile(residuals, 0.01), quantile(residuals, 0.99)
    wins = []
    for r in rows:
        x = dict(r)
        x["winsor_residual"] = min(hi, max(lo, r["residual"]))
        wins.append(x)
    wt = tail_stats(wins, "winsor_residual")
    pos = {}
    for position in base.POSITIONS:
        sub = [r for r in rows if r["position"] == position]
        pos[position] = tail_stats(sub)
    valid_pos = [v for v in pos.values() if math.isfinite(v.get("gap", math.nan))]
    pos_same = sum(1 for v in valid_pos if sign(v["gap"]) == agg_sign) if agg_sign else 0
    def grouped(key):
        groups = defaultdict(list)
        for r in rows:
            groups[str(r[key])].append(r)
        return {k: {"n": len(v), "mae": mean(abs(x["residual"]) for x in v), "bias": mean(x["residual"] for x in v)} for k, v in sorted(groups.items())}
    return {
        "label": label,
        "n": len(rows),
        "mae": mean(abs(r["residual"]) for r in rows),
        "bias": mean(r["residual"] for r in rows),
        "residual_vs_surplus_pearson": corr([r["model_a"] for r in rows], residuals),
        "residual_vs_surplus_spearman": spearman([r["model_a"] for r in rows], residuals),
        "residual_vs_within_position_rank_spearman": spearman([r["surplus_percentile"] for r in rows], residuals),
        "residual_vs_concentration_spearman": spearman([r["surplus_concentration"] for r in rows], residuals),
        "residual_vs_terminal_share_spearman": spearman([r["terminal_share"] for r in rows], residuals),
        "residual_vs_uncertainty_spearman": spearman([r["uncertainty_ratio"] for r in rows], residuals),
        "residual_vs_survival_spearman": spearman([r["source_survival_probability"] for r in rows], residuals),
        "tail": t,
        "fold_tail_gaps": fold,
        "fold_gap_t_like": tstat,
        "fold_sign_stability": stability,
        "winsorized_tail": wt,
        "position_tail": pos,
        "positions_same_sign": pos_same,
        "positions_with_evidence": len(valid_pos),
        "career_stage": grouped("career_stage"),
    }


def standardized_uncertainty_summary(rows):
    enriched = []
    for r in rows:
        x = dict(r)
        x["std_residual"] = r["residual"] / max(5.0, r["model_a_sd"])
        enriched.append(x)
    t = tail_stats(enriched, "std_residual")
    return {
        "tail": t,
        "coverage": mean((r["model_a"] - Z80*r["model_a_sd"] <= r["realized"] <= r["model_a"] + Z80*r["model_a_sd"]) for r in rows),
    }


def retention(candidate_gap, canonical_gap):
    return abs(candidate_gap) / max(EPS, abs(canonical_gap))


def residual_gate(canon, level, oneqb, repaired_unc):
    cg = canon["tail"]["gap"]
    lg = level["tail"]["gap"]
    qg = oneqb["tail"]["gap"]
    wg = canon["winsorized_tail"]["gap"]
    uz = repaired_unc["tail"]["gap"]
    canonical_sign = sign(cg)
    checks = {
        "material_tail_gap": abs(canon["tail"]["normalized_gap"]) >= MATERIAL_NORMALIZED_GAP,
        "chronological_t_like": abs(canon["fold_gap_t_like"]) >= MIN_FOLD_T if math.isfinite(canon["fold_gap_t_like"]) else False,
        "chronological_sign_stability": canon["fold_sign_stability"] >= MIN_SIGN_STABILITY and len(canon["fold_tail_gaps"]) >= MIN_FOLD_GAPS,
        "influence_robustness": sign(wg) == canonical_sign and retention(wg, cg) >= MIN_SENSITIVITY_RETENTION,
        "stable_level_sensitivity": sign(lg) == canonical_sign and retention(lg, cg) >= MIN_SENSITIVITY_RETENTION,
        "format_sensitivity": sign(qg) == canonical_sign and retention(oneqb["tail"]["normalized_gap"], canon["tail"]["normalized_gap"]) >= MIN_FORMAT_RETENTION,
        "position_stability": canon["positions_same_sign"] >= MIN_POSITION_SIGN_COUNT,
        "repaired_uncertainty_sensitivity": sign(uz) == canonical_sign and abs(uz) >= MATERIAL_NORMALIZED_GAP,
    }
    return {"pass": all(checks.values()), "checks": checks, "thresholds": {
        "tail_percentile": TAIL_Q,
        "middle_reference": [MID_LO, MID_HI],
        "material_normalized_gap": MATERIAL_NORMALIZED_GAP,
        "fold_t_like": MIN_FOLD_T,
        "fold_sign_stability": MIN_SIGN_STABILITY,
        "sensitivity_retention": MIN_SENSITIVITY_RETENTION,
        "format_retention": MIN_FORMAT_RETENTION,
        "positions_same_sign": MIN_POSITION_SIGN_COUNT,
    }}


def fit_gamma(training_rows):
    denom = sum(r["tail_hinge"] ** 2 for r in training_rows)
    if denom <= EPS:
        return 0.0
    raw = sum(r["tail_hinge"] * r["residual"] for r in training_rows) / denom
    return max(-1.0, raw)  # structural monotonicity: elite-tail slope cannot become negative


def model_b_evaluation(canonical_rows, oneqb_rows):
    sf_by_season = defaultdict(list)
    qb_by_season = defaultdict(list)
    for r in canonical_rows:
        sf_by_season[r["season"]].append(r)
    for r in oneqb_rows:
        qb_by_season[r["season"]].append(r)
    seasons = sorted(sf_by_season)
    out_sf, out_qb, gammas = [], [], []
    for season in seasons:
        # A three-year realized target from fold s is available before preseason T only when s <= T-3.
        train = [r for s in seasons if s <= season - 3 for r in sf_by_season[s]]
        resolved_folds = len({r["season"] for r in train})
        if len(train) < 200 or resolved_folds < 3:
            continue
        gamma = fit_gamma(train)
        gammas.append({"season": season, "gamma": gamma, "training_n": len(train), "resolved_folds": resolved_folds})
        for source, dest in ((sf_by_season[season], out_sf), (qb_by_season.get(season, []), out_qb)):
            for r in source:
                x = dict(r)
                x["gamma"] = gamma
                x["model_b"] = max(0.0, r["model_a"] + gamma * r["tail_hinge"])
                derivative = 1.0 + gamma if r["tail_hinge"] > 0 else 1.0
                x["model_b_sd"] = abs(derivative) * r["model_a_sd"]
                x["model_b_residual"] = r["realized"] - x["model_b"]
                dest.append(x)
    return out_sf, out_qb, gammas


def evalrow_from_dict(r, model_key="model_a", sd_key="model_a_sd"):
    return base.EvalRow(
        player_id=r["player_id"], position=r["position"], season=r["season"],
        model_a=r[model_key], model_a_sd=r[sd_key], affine_feature=r["affine_feature"],
        realized=r["realized"], age=r["age"], experience=r["experience"], market=None,
    )


def challenger_summary(sf_rows, qb_rows):
    if not sf_rows:
        return None
    control_mae = mean(abs(r["residual"]) for r in sf_rows)
    challenger_mae = mean(abs(r["model_b_residual"]) for r in sf_rows)
    by = defaultdict(list)
    for r in sf_rows:
        by[r["season"]].append(r)
    fold = []
    for season, vals in sorted(by.items()):
        cm = mean(abs(r["residual"]) for r in vals)
        bm = mean(abs(r["model_b_residual"]) for r in vals)
        fold.append({"season": season, "model_a_mae": cm, "model_b_mae": bm, "model_b_win": bm < cm})
    fold_win = mean(x["model_b_win"] for x in fold)
    coverage = mean((r["model_b"] - Z80*r["model_b_sd"] <= r["realized"] <= r["model_b"] + Z80*r["model_b_sd"]) for r in sf_rows)
    sf_eval = [evalrow_from_dict(r, "model_b", "model_b_sd") for r in sf_rows]
    fold_eval = defaultdict(list)
    for r in sf_eval:
        fold_eval[r.season].append(r)
    qb_map = {(r["season"], r["player_id"]): r for r in qb_rows}
    scarcity_folds = []
    for season in sorted(fold_eval):
        qbg, nong = [], []
        for r in sf_rows:
            if r["season"] != season:
                continue
            other = qb_map.get((season, r["player_id"]))
            if other is None:
                continue
            delta = r["model_b"] - other["model_b"]
            (qbg if r["position"] == "QB" else nong).append(delta)
        scarcity_folds.append({"season": season, "qb_relative_gain": mean(qbg) if qbg else 0.0, "non_qb_relative_gain": mean(nong) if nong else 0.0})
    scarcity = {
        "folds": scarcity_folds,
        "fold_count": len(scarcity_folds),
        "folds_with_positive_qb_gain": sum(x["qb_relative_gain"] > 0 for x in scarcity_folds),
        "qb_relative_gain": mean(x["qb_relative_gain"] for x in scarcity_folds),
        "non_qb_relative_gain": mean(x["non_qb_relative_gain"] for x in scarcity_folds),
    }
    scarcity["pass"] = bool(scarcity_folds) and scarcity["folds_with_positive_qb_gain"] == len(scarcity_folds) and scarcity["qb_relative_gain"] > 0 and abs(scarcity["non_qb_relative_gain"]) < abs(scarcity["qb_relative_gain"])
    checks = repair.scenario_checks(base, sf_eval, fold_eval, scarcity)
    economic_passes = sum(bool(v.get("pass")) for v in checks.values())
    existing_passes_preserved = all(checks[k]["pass"] for k in ("aging_rb_vs_young_rb", "developing_wr", "developing_te", "position_scarcity_shift"))
    current_fail_fixed = checks["elite_qb_longevity"]["pass"] or checks["expected_appreciation_decline"]["pass"]
    accept = (
        (control_mae - challenger_mae) / control_mae >= MIN_MODEL_B_MAE_GAIN
        and fold_win >= MIN_MODEL_B_FOLD_WIN_RATE
        and economic_passes >= 5
        and existing_passes_preserved
        and current_fail_fixed
        and TARGET_COVERAGE_LOW <= coverage <= TARGET_COVERAGE_HIGH
    )
    return {
        "model_a_mae": control_mae,
        "model_b_mae": challenger_mae,
        "relative_mae_gain": (control_mae - challenger_mae) / control_mae,
        "fold_win_rate": fold_win,
        "folds": fold,
        "coverage": coverage,
        "economic_checks": checks,
        "economic_passes": economic_passes,
        "existing_passes_preserved": existing_passes_preserved,
        "current_fail_fixed": current_fail_fixed,
        "accepted": accept,
        "acceptance_thresholds": {"mae_gain": MIN_MODEL_B_MAE_GAIN, "fold_win_rate": MIN_MODEL_B_FOLD_WIN_RATE, "economic_checks": 5, "coverage": [TARGET_COVERAGE_LOW, TARGET_COVERAGE_HIGH]},
    }


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k); keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=keys)
        w.writeheader(); w.writerows(rows)


def report(payload):
    c = payload["canonical"]
    l = payload["stable_level_sensitivity"]
    q = payload["one_qb_sensitivity"]
    u = payload["repaired_uncertainty_sensitivity"]
    g = payload["residual_gate"]
    state = payload["classification"]
    lines = [
        "# Value-Owned Economic Residual Identification — PR #131",
        "",
        "**Status:** research-only, non-authoritative, unmerged. Production Forecast, Value, Decision, Search, API, and presentation behavior are unchanged.",
        "",
        "## Executive conclusion",
        "",
        f"Residual classification: **{state}**.",
        f"Value-owned residual gate: **{'PASS' if g['pass'] else 'FAIL'}**.",
        f"Model B fitted: **{'yes' if payload['model_b_fitted'] else 'no'}**.",
        "",
        "The persistence research line was stopped because repeated transparent point-estimate challengers failed to recover individual revision persistence. This study therefore holds Forecast conceptually fixed and asks a separate question: whether Model A leaves a stable economic residual after the known Forecast level and uncertainty limitations are represented as sensitivities.",
        "",
        "## Predeclared residual test",
        "",
        f"Elite tail is the top {int((1-TAIL_Q)*100)}% of Model A replacement-adjusted surplus within position and historical fold; the reference middle is the {int(MID_LO*100)}th-{int(MID_HI*100)}th percentiles. The residual gate required a normalized elite-minus-middle residual gap of at least {MATERIAL_NORMALIZED_GAP:.2f}, fold-level t-like magnitude >= {MIN_FOLD_T:.1f}, sign stability >= {MIN_SIGN_STABILITY:.0%}, robustness to 1% winsorization, survival after the stable-player-level Forecast sensitivity, same-direction 1QB behavior, at least {MIN_POSITION_SIGN_COUNT} positions with the same residual direction, and persistence after repaired Forecast uncertainty is represented.",
        "",
        "## Canonical Model A residual",
        "",
        f"- N: **{c['n']}**",
        f"- MAE: **{c['mae']:.3f}**",
        f"- residual-vs-surplus Spearman: **{c['residual_vs_surplus_spearman']:.3f}**",
        f"- within-position rank Spearman: **{c['residual_vs_within_position_rank_spearman']:.3f}**",
        f"- elite-minus-middle residual gap: **{c['tail']['gap']:.3f}**; normalized **{c['tail']['normalized_gap']:.3f}**",
        f"- chronological fold t-like statistic: **{c['fold_gap_t_like']:.3f}**",
        f"- fold sign stability: **{c['fold_sign_stability']:.1%}**",
        f"- positions with same-sign tail gap: **{c['positions_same_sign']}/{c['positions_with_evidence']}**",
        "",
        "## Forecast falsification sensitivities",
        "",
        f"Stable player-level Forecast correction sensitivity: tail gap **{l['tail']['gap']:.3f}** (normalized **{l['tail']['normalized_gap']:.3f}**).",
        f"1QB format sensitivity: tail gap **{q['tail']['gap']:.3f}** (normalized **{q['tail']['normalized_gap']:.3f}**).",
        f"Research-only recursive uncertainty sensitivity: standardized elite-minus-middle residual gap **{u['tail']['gap']:.3f}**; nominal-80% coverage **{u['coverage']:.1%}**.",
        "",
        "## Gate details",
        "",
    ]
    for k, v in g["checks"].items():
        lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    lines += ["", "## Model B decision", ""]
    if payload["model_b_fitted"]:
        b = payload["model_b"]
        lines += [
            "The residual gate justified exactly one narrow challenger: a chronologically fitted monotonic piecewise-linear elite-tail hinge. The knot is the PIT 90th-percentile Model A surplus threshold within position/fold; the single fitted parameter changes only the slope above that threshold. It is never allowed to make the value curve decrease.",
            "",
            f"- Model A MAE: **{b['model_a_mae']:.3f}**",
            f"- Model B MAE: **{b['model_b_mae']:.3f}**",
            f"- relative MAE gain: **{b['relative_mae_gain']:.2%}**",
            f"- chronological fold win rate: **{b['fold_win_rate']:.1%}**",
            f"- economic checks: **{b['economic_passes']}/6**",
            f"- uncertainty coverage: **{b['coverage']:.1%}**",
            f"- governed challenger gate: **{'PASS' if b['accepted'] else 'FAIL'}**",
        ]
    else:
        lines.append("The residual gate failed, so no nonlinear Value challenger was fitted. Model A remains the preferred simple architecture for this research state.")
    lines += [
        "", "## Double-counting / authority boundary", "",
        "- Forecast means, survival, and football uncertainty were not re-owned by Value.",
        "- Survival is already embedded in Forecast means and was not multiplied into surplus again.",
        "- `marginal_lineup_opportunity` remained the replacement definition; no second scarcity premium was added.",
        "- Market Value was not a fitting target.",
        "- Team Utility, contender state, owner preference, and Behavioral Intelligence were excluded.",
        "- Stable player-level Forecast bias and recursive uncertainty carry-forward were sensitivities only and were not promoted.",
        "", "## Production status", "",
        "**NO PRODUCTION PROMOTION.** PR #131 remains research-only, draft, non-authoritative, and unmerged.",
    ]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--career-panel", type=Path, required=True)
    p.add_argument("--dynastyprocess-repo", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = base.load_rows(args.career_panel, rcmod)
    seasons = supported_seasons(rows)
    if len(seasons) < 10:
        raise SystemExit(f"insufficient supported folds: {seasons}")

    _, canonical_paths, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=False)
    _, repaired_unc_paths, _ = hier.baseline_and_sticky(rows, seasons, carry_uncertainty=True)
    _, level_paths, _, _, _ = playerres.build_residual_paths(rows, seasons, carry_uncertainty=False)

    _, canonical = build_variant(rows, seasons, canonical_paths, PRIMARY)
    _, oneqb = build_variant(rows, seasons, canonical_paths, ONE_QB)
    _, level = build_variant(rows, seasons, level_paths, PRIMARY)
    _, repaired_unc = build_variant(rows, seasons, repaired_unc_paths, PRIMARY)

    canon_summary = residual_summary(canonical, "canonical_forecast")
    level_summary = residual_summary(level, "stable_level_bias_sensitivity")
    oneqb_summary = residual_summary(oneqb, "one_qb_sensitivity")
    unc_summary = standardized_uncertainty_summary(repaired_unc)
    gate = residual_gate(canon_summary, level_summary, oneqb_summary, unc_summary)

    model_b = None
    gammas = []
    b_rows = []
    if gate["pass"]:
        b_rows, b_oneqb, gammas = model_b_evaluation(canonical, oneqb)
        model_b = challenger_summary(b_rows, b_oneqb)

    if not gate["pass"]:
        classification = "NO IDENTIFIABLE VALUE RESIDUAL"
    elif model_b is None:
        classification = "VALUE RESIDUAL EXISTS, BUT EVIDENCE IS INSUFFICIENT"
    elif model_b["accepted"]:
        classification = "REPRODUCIBLE VALUE-OWNED RESIDUAL"
    else:
        classification = "VALUE RESIDUAL EXISTS, BUT EVIDENCE IS INSUFFICIENT"

    payload = {
        "research_status": "research_only_non_authoritative_unmerged",
        "supported_folds": seasons,
        "canonical_model_a": {"replacement": CANDIDATE, "weights": list(base.ANNUAL_WEIGHTS)},
        "predeclared_thresholds": {
            "tail_q": TAIL_Q, "middle_reference": [MID_LO, MID_HI], "material_normalized_gap": MATERIAL_NORMALIZED_GAP,
            "fold_t_like": MIN_FOLD_T, "fold_sign_stability": MIN_SIGN_STABILITY,
            "sensitivity_retention": MIN_SENSITIVITY_RETENTION, "format_retention": MIN_FORMAT_RETENTION,
            "position_sign_count": MIN_POSITION_SIGN_COUNT, "model_b_mae_gain": MIN_MODEL_B_MAE_GAIN,
            "model_b_fold_win_rate": MIN_MODEL_B_FOLD_WIN_RATE,
        },
        "canonical": canon_summary,
        "stable_level_sensitivity": level_summary,
        "one_qb_sensitivity": oneqb_summary,
        "repaired_uncertainty_sensitivity": unc_summary,
        "residual_gate": gate,
        "classification": classification,
        "model_b_fitted": bool(gate["pass"]),
        "model_b_gammas": gammas,
        "model_b": model_b,
        "production_promotion": False,
    }

    (args.output_dir / "value_residual_identification_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    text = report(payload)
    (args.output_dir / "value_residual_identification_report.md").write_text(text, encoding="utf-8")
    rows_out = []
    for label, vals in (("canonical", canonical), ("stable_level", level), ("one_qb", oneqb), ("repaired_uncertainty", repaired_unc)):
        for r in vals:
            rows_out.append({"variant": label, **r})
    write_csv(args.output_dir / "value_residual_identification_rows.csv", rows_out)
    fold_rows = [{"variant": "canonical", **x} for x in canon_summary["fold_tail_gaps"]] + [{"variant": "stable_level", **x} for x in level_summary["fold_tail_gaps"]] + [{"variant": "one_qb", **x} for x in oneqb_summary["fold_tail_gaps"]]
    write_csv(args.output_dir / "value_residual_fold_diagnostics.csv", fold_rows)
    if b_rows:
        write_csv(args.output_dir / "value_residual_model_b_rows.csv", b_rows)
        write_csv(args.output_dir / "value_residual_model_b_gammas.csv", gammas)
    print(text)


if __name__ == "__main__":
    main()
