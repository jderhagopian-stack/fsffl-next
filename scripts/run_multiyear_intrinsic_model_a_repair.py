from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Iterable

Z80 = 1.2815515655446004
TARGET_COVERAGE = 0.80
COVERAGE_TOLERANCE = 0.10
MATERIAL_MAE_IMPROVEMENT = 0.05
PRIMARY_CONTEXT = "12t_sf_2rb_3wr_1te_1flex"
ONE_QB_CONTEXT = "12t_1qb_2rb_3wr_1te_1flex"
REPAIRED_CANDIDATE = "eligible_slot_opportunity"


def mean(values: Iterable[float]) -> float:
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return math.nan
    xb, yb = mean(xs), mean(ys)
    xx = sum((x - xb) ** 2 for x in xs)
    yy = sum((y - yb) ** 2 for y in ys)
    if xx <= 0 or yy <= 0:
        return 0.0
    return sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / math.sqrt(xx * yy)


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 1.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    position = q * (len(xs) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return xs[lo]
    frac = position - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def load_base():
    path = Path(__file__).with_name("run_multiyear_intrinsic_model_a_benchmark.py")
    spec = importlib.util.spec_from_file_location("pr131_model_a_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PR #131 base benchmark")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cutoff_state(items, count: int):
    if count <= 0 or not items:
        return None
    ordered = sorted(items, key=lambda s: (-s.mean, s.player_id))
    return ordered[min(len(ordered) - 1, count - 1)]


def eligible_slot_replacement_levels(base, states, context_id: str):
    """League-structural opportunity baseline with no positional bonus.

    A position's replacement opportunity is the easiest marginal lineup slot that
    a player at that position is eligible to occupy. Fixed position, FLEX, and
    SUPERFLEX cutoffs are derived directly from league structure and optimized
    allocation. Team-specific need is never consulted.
    """

    context = base.CONTEXTS[context_id]
    counts = base.required_counts(context)
    fixed_selected: set[str] = set()
    fixed_cutoffs = {}
    for pos in base.POSITIONS:
        items = sorted((s for s in states if s.position == pos), key=lambda s: (-s.mean, s.player_id))
        selected = items[: counts[pos]]
        fixed_selected.update(s.player_id for s in selected)
        fixed_cutoffs[pos] = selected[-1] if selected else (items[0] if items else None)

    flex_slots = int(context["team_count"]) * int(context["flex"])
    flex_pool = sorted(
        (s for s in states if s.player_id not in fixed_selected and s.position in {"RB", "WR", "TE"}),
        key=lambda s: (-s.mean, s.player_id),
    )
    flex_selected = flex_pool[:flex_slots]
    flex_cutoff = flex_selected[-1] if flex_selected else None
    after_flex = fixed_selected | {s.player_id for s in flex_selected}

    sf_slots = int(context["team_count"]) * int(context["superflex"])
    sf_pool = sorted((s for s in states if s.player_id not in after_flex), key=lambda s: (-s.mean, s.player_id))
    sf_selected = sf_pool[:sf_slots]
    sf_cutoff = sf_selected[-1] if sf_selected else None

    result = {}
    for pos in base.POSITIONS:
        eligible = [x for x in (fixed_cutoffs[pos],) if x is not None]
        if pos in {"RB", "WR", "TE"} and flex_cutoff is not None:
            eligible.append(flex_cutoff)
        if sf_cutoff is not None:
            eligible.append(sf_cutoff)
        if not eligible:
            result[pos] = (0.0, 0.0)
            continue
        # Lowest score is the easiest lineup opportunity available to the
        # position; this is structural opportunity cost, not a positional bonus.
        chosen = min(eligible, key=lambda s: (s.mean, s.player_id))
        result[pos] = (chosen.mean, chosen.sd)
    return result


def install_repair_candidate(base):
    original = base.replacement_levels

    def replacement_levels(states, context_id: str, candidate: str):
        if candidate == REPAIRED_CANDIDATE:
            return eligible_slot_replacement_levels(base, states, context_id)
        return original(states, context_id, candidate)

    base.replacement_levels = replacement_levels
    base.REPLACEMENT_CANDIDATES = tuple(base.REPLACEMENT_CANDIDATES) + (REPAIRED_CANDIDATE,)
    return original


def uncertainty_scale(prior_rows) -> float:
    """Rolling, point-in-time uncertainty calibration from prior residuals only."""
    ratios = []
    for row in prior_rows:
        if row.model_a_sd > 1e-9:
            ratios.append(abs(row.realized - row.model_a) / (Z80 * row.model_a_sd))
    return max(0.05, quantile(ratios, TARGET_COVERAGE)) if ratios else 1.0


def component_variance(details: list[dict[str, object]]) -> dict[str, tuple[float, float]]:
    by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in details:
        by_player[str(row["asset_id"])].append(row)
    out = {}
    for player_id, rows in by_player.items():
        player_var = 0.0
        replacement_var = 0.0
        for row in rows:
            player_mean = float(row["player_forecast_mean"])
            replacement_mean = float(row["replacement_forecast_mean"])
            if player_mean <= replacement_mean:
                continue
            weight = float(row["annual_weight"])
            player_var += weight**2 * float(row["player_forecast_stddev"]) ** 2
            replacement_var += weight**2 * float(row["replacement_forecast_stddev"]) ** 2
        out[player_id] = (player_var, replacement_var)
    return out


def fold_metrics(base, rows, affine, scale: float, variance_parts: dict[str, tuple[float, float]]):
    intercept, slope, residual_sd = affine
    model_errors = []
    affine_errors = []
    raw_full = calibrated = player_only = replacement_only = affine_covered = 0
    replacement_shares = []
    for row in rows:
        affine_pred = intercept + slope * row.affine_feature
        error = row.model_a - row.realized
        control_error = affine_pred - row.realized
        model_errors.append(error)
        affine_errors.append(control_error)
        pvar, rvar = variance_parts.get(row.player_id, (row.model_a_sd**2, 0.0))
        total = pvar + rvar
        if total > 0:
            replacement_shares.append(rvar / total)
        if row.model_a - Z80 * row.model_a_sd <= row.realized <= row.model_a + Z80 * row.model_a_sd:
            raw_full += 1
        half_width = Z80 * row.model_a_sd * scale
        if row.model_a - half_width <= row.realized <= row.model_a + half_width:
            calibrated += 1
        psd = math.sqrt(max(0.0, pvar))
        rsd = math.sqrt(max(0.0, rvar))
        if row.model_a - Z80 * psd <= row.realized <= row.model_a + Z80 * psd:
            player_only += 1
        if row.model_a - Z80 * rsd <= row.realized <= row.model_a + Z80 * rsd:
            replacement_only += 1
        if affine_pred - Z80 * residual_sd <= row.realized <= affine_pred + Z80 * residual_sd:
            affine_covered += 1
    n = len(rows)
    model_mae = mean(abs(e) for e in model_errors)
    affine_mae = mean(abs(e) for e in affine_errors)
    return {
        "n": n,
        "model_a_mae": model_mae,
        "affine_mae": affine_mae,
        "model_a_rmse": math.sqrt(mean(e * e for e in model_errors)),
        "affine_rmse": math.sqrt(mean(e * e for e in affine_errors)),
        "model_a_bias": mean(model_errors),
        "affine_bias": mean(affine_errors),
        "model_a_raw_coverage": raw_full / n,
        "model_a_coverage": calibrated / n,
        "player_only_raw_coverage": player_only / n,
        "replacement_only_raw_coverage": replacement_only / n,
        "replacement_variance_share": mean(replacement_shares) if replacement_shares else 0.0,
        "uncertainty_scale": scale,
        "affine_coverage": affine_covered / n,
        "mae_improvement": (affine_mae - model_mae) / affine_mae if affine_mae else 0.0,
    }


def context_shift(base, rows, seasons: list[int], candidate: str, rc):
    fold_results = []
    for season in seasons:
        _, sf, _ = base.evaluate_fold(rows, season, PRIMARY_CONTEXT, candidate, rc)
        _, one, _ = base.evaluate_fold(rows, season, ONE_QB_CONTEXT, candidate, rc)
        one_by = {r.player_id: r for r in one}
        qb, non = [], []
        for row in sf:
            other = one_by.get(row.player_id)
            if other is None:
                continue
            delta = row.model_a - other.model_a
            (qb if row.position == "QB" else non).append(delta)
        fold_results.append({
            "season": season,
            "qb_relative_gain": mean(qb) if qb else 0.0,
            "non_qb_relative_gain": mean(non) if non else 0.0,
        })
    qb_positive = sum(1 for f in fold_results if f["qb_relative_gain"] > 0)
    mean_qb = mean(f["qb_relative_gain"] for f in fold_results)
    mean_non = mean(f["non_qb_relative_gain"] for f in fold_results)
    return {
        "folds": fold_results,
        "folds_with_positive_qb_gain": qb_positive,
        "fold_count": len(fold_results),
        "qb_relative_gain": mean_qb,
        "non_qb_relative_gain": mean_non,
        "pass": bool(fold_results)
        and qb_positive == len(fold_results)
        and mean_qb > 0
        and abs(mean_non) < abs(mean_qb),
    }


def scenario_checks(base, rows, fold_rows, scarcity):
    checks = {}
    rbs = [r for r in rows if r.position == "RB" and r.age is not None]
    pairs = []
    for young in rbs:
        for old in rbs:
            if old.age is None or young.age is None or old.age - young.age < 4:
                continue
            denom = max(young.affine_feature, old.affine_feature)
            if denom > 0 and abs(young.affine_feature - old.affine_feature) / denom <= 0.10:
                pairs.append((young, old))
    accuracy = mean(1.0 if (y.model_a > o.model_a) == (y.realized > o.realized) else 0.0 for y, o in pairs) if pairs else 0.0
    checks["aging_rb_vs_young_rb"] = {"n": len(pairs), "directional_accuracy": accuracy, "pass": bool(pairs) and accuracy >= 0.55}

    def rank(values):
        return base.ranks(values)

    def cohort(name, subset):
        signal = corr(rank([r.model_a for r in subset]), rank([r.realized for r in subset])) if len(subset) >= 10 else math.nan
        checks[name] = {"n": len(subset), "rank_signal_correlation": signal, "pass": len(subset) >= 10 and signal > 0.25}

    qbs = [r for r in rows if r.position == "QB"]
    threshold = sorted(r.affine_feature for r in qbs)[int(0.75 * (len(qbs) - 1))] if qbs else math.inf
    cohort("elite_qb_longevity", [r for r in qbs if r.affine_feature >= threshold and (r.age or 0) <= 33])
    cohort("developing_wr", [r for r in rows if r.position == "WR" and r.age is not None and r.age <= 25 and r.experience <= 3])
    cohort("developing_te", [r for r in rows if r.position == "TE" and r.age is not None and r.age <= 26 and r.experience <= 3])
    checks["position_scarcity_shift"] = scarcity

    changes = []
    seasons = sorted(fold_rows)
    for a, b in zip(seasons, seasons[1:]):
        if b != a + 1:
            continue
        prior = {r.player_id: r for r in fold_rows[a]}
        for nxt in fold_rows[b]:
            old = prior.get(nxt.player_id)
            if old is None:
                continue
            predicted = nxt.model_a - old.model_a
            realized = nxt.realized - old.realized
            if abs(predicted) > 1e-9 or abs(realized) > 1e-9:
                changes.append((predicted, realized))
    direction = mean(1.0 if (p > 0) == (r > 0) else 0.0 for p, r in changes) if changes else 0.0
    signal = corr([p for p, _ in changes], [r for _, r in changes]) if len(changes) >= 2 else math.nan
    checks["expected_appreciation_decline"] = {
        "n": len(changes),
        "directional_accuracy": direction,
        "change_correlation": signal,
        "pass": bool(changes) and direction >= 0.55 and math.isfinite(signal) and signal > 0.10,
    }
    return checks


def detail_index(details):
    index = {}
    for row in details:
        key = (int(row["target_season"]), str(row["asset_id"]), int(row["season_offset"]))
        index[key] = row
    return index


def surplus(row, forecast: bool) -> float:
    if forecast:
        return max(0.0, float(row["player_forecast_mean"]) - float(row["replacement_forecast_mean"]))
    return max(0.0, float(row["realized_player_points"]) - float(row["realized_replacement_points"]))


def appreciation_decomposition(base, details, seasons):
    idx = detail_index(details)
    weights = base.ANNUAL_WEIGHTS
    rows = []
    for a, b in zip(seasons, seasons[1:]):
        if b != a + 1:
            continue
        old_players = {asset for season, asset, offset in idx if season == a and offset == 0}
        new_players = {asset for season, asset, offset in idx if season == b and offset == 0}
        for player_id in sorted(old_players & new_players):
            old = [idx.get((a, player_id, o)) for o in range(base.HORIZON)]
            new = [idx.get((b, player_id, o)) for o in range(base.HORIZON)]
            if any(x is None for x in old + new):
                continue
            old_s = [surplus(x, True) for x in old]
            new_s = [surplus(x, True) for x in new]
            old_r = [surplus(x, False) for x in old]
            new_r = [surplus(x, False) for x in new]
            model_delta = sum(w * s for w, s in zip(weights, new_s)) - sum(w * s for w, s in zip(weights, old_s))
            realized_delta = sum(w * s for w, s in zip(weights, new_r)) - sum(w * s for w, s in zip(weights, old_r))
            drop = -weights[0] * old_s[0]
            reweight = (weights[0] - weights[1]) * old_s[1] + (weights[1] - weights[2]) * old_s[2]
            terminal = weights[2] * new_s[2]
            forecast_update = 0.0
            replacement_update = 0.0
            for new_offset, old_offset, weight in ((0, 1, weights[0]), (1, 2, weights[1])):
                old_row = old[old_offset]
                new_row = new[new_offset]
                old_value = surplus(old_row, True)
                same_old_rep = max(0.0, float(new_row["player_forecast_mean"]) - float(old_row["replacement_forecast_mean"]))
                forecast_update += weight * (same_old_rep - old_value)
                replacement_update += weight * (surplus(new_row, True) - same_old_rep)
            reconstructed = drop + reweight + terminal + forecast_update + replacement_update
            equal_model = sum(new_s) - sum(old_s)
            equal_realized = sum(new_r) - sum(old_r)
            rows.append({
                "season": b,
                "asset_id": player_id,
                "model_delta": model_delta,
                "realized_delta": realized_delta,
                "drop_prior_year": drop,
                "overlap_reweight": reweight,
                "new_terminal_year": terminal,
                "shared_forecast_update": forecast_update,
                "shared_replacement_update": replacement_update,
                "reconstruction_error": model_delta - reconstructed,
                "model_delta_without_replacement_update": model_delta - replacement_update,
                "model_delta_without_forecast_update": model_delta - forecast_update,
                "equal_weight_model_delta": equal_model,
                "equal_weight_realized_delta": equal_realized,
            })
    def summarize(pred_key, realized_key="realized_delta"):
        pairs = [(float(r[pred_key]), float(r[realized_key])) for r in rows if abs(float(r[pred_key])) > 1e-9 or abs(float(r[realized_key])) > 1e-9]
        return {
            "n": len(pairs),
            "directional_accuracy": mean(1.0 if (p > 0) == (y > 0) else 0.0 for p, y in pairs) if pairs else 0.0,
            "correlation": corr([p for p, _ in pairs], [y for _, y in pairs]) if len(pairs) >= 2 else math.nan,
        }
    summary = {
        "full": summarize("model_delta"),
        "without_replacement_update": summarize("model_delta_without_replacement_update"),
        "without_forecast_update": summarize("model_delta_without_forecast_update"),
        "equal_weights": summarize("equal_weight_model_delta", "equal_weight_realized_delta"),
        "mean_absolute_reconstruction_error": mean(abs(float(r["reconstruction_error"])) for r in rows) if rows else 0.0,
        "mean_components": {
            key: mean(float(r[key]) for r in rows) if rows else 0.0
            for key in ("drop_prior_year", "overlap_reweight", "new_terminal_year", "shared_forecast_update", "shared_replacement_update")
        },
    }
    return rows, summary


def persistent_residual(base, fold_rows, fold_metrics_by_season):
    probes = []
    for season, rows in sorted(fold_rows.items()):
        if season not in fold_metrics_by_season or len(rows) < 30:
            continue
        ordered = sorted(rows, key=lambda r: r.model_a)
        decile = max(1, len(ordered) // 10)
        top = mean(r.realized - r.model_a for r in ordered[-decile:])
        middle_rows = ordered[len(ordered) // 3: 2 * len(ordered) // 3]
        middle = mean(r.realized - r.model_a for r in middle_rows)
        signed_gap = top - middle
        threshold = 0.25 * float(fold_metrics_by_season[season]["model_a_mae"])
        probes.append({"season": season, "signed_gap": signed_gap, "threshold": threshold, "material": abs(signed_gap) > threshold})
    material = [p for p in probes if p["material"]]
    if not probes or not material:
        return {"folds": probes, "persistent": False, "material_rate": 0.0, "dominant_sign_rate": 0.0}
    positive = sum(1 for p in material if p["signed_gap"] > 0)
    negative = len(material) - positive
    dominant = max(positive, negative) / len(material)
    material_rate = len(material) / len(probes)
    # Reuse the predeclared 60% fold-stability standard rather than inventing a
    # looser post-hoc residual criterion.
    persistent = material_rate >= 0.60 and dominant >= 0.60
    return {"folds": probes, "persistent": persistent, "material_rate": material_rate, "dominant_sign_rate": dominant}


def write_csv(path: Path, rows: list[dict[str, object]]):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--dynastyprocess-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    base = load_base()
    install_repair_candidate(base)
    rc = base.load_calibration_module()
    rows = base.load_rows(args.career_panel, rc)
    max_panel_season = max(r.season for r in rows)
    max_target = max_panel_season - (base.HORIZON - 1)
    supported = []
    for season in range(min(r.season for r in rows) + 1, max_target + 1):
        if base.FoldCalibration(rows, season, rc).supported():
            supported.append(season)
    if len(supported) < 2:
        raise SystemExit(f"insufficient chronological folds: {supported}")

    crosswalk = base.market_crosswalk(args.dynastyprocess_repo)
    candidates = tuple(base.REPLACEMENT_CANDIDATES)
    all_results = {}
    aggregates = {}
    fold_rows = {}
    details_by_candidate = {}
    uncertainty_rows = []
    scarcity_by_candidate = {}

    for candidate in candidates:
        prior_rows = []
        fold_rows[candidate] = {}
        details_by_candidate[candidate] = []
        folds = []
        for season in supported:
            _, holdout, details = base.evaluate_fold(rows, season, PRIMARY_CONTEXT, candidate, rc)
            snapshot = base.market_snapshot(args.dynastyprocess_repo, date(season, 8, 31), PRIMARY_CONTEXT)
            holdout = base.attach_market(holdout, snapshot, crosswalk)
            fold_rows[candidate][season] = holdout
            details_by_candidate[candidate].extend(details)
            if prior_rows:
                affine = base.fit_affine(prior_rows)
                scale = uncertainty_scale(prior_rows)
                parts = component_variance(details)
                metrics = fold_metrics(base, holdout, affine, scale, parts)
                folds.append({
                    "season": season,
                    "affine_fit": {"intercept": affine[0], "slope": affine[1], "residual_sd": affine[2]},
                    "metrics": metrics,
                    "market": base.market_diagnostics(holdout, prior_rows),
                })
                uncertainty_rows.append({"candidate": candidate, "season": season, **{k: metrics[k] for k in (
                    "model_a_raw_coverage", "model_a_coverage", "player_only_raw_coverage", "replacement_only_raw_coverage",
                    "replacement_variance_share", "uncertainty_scale")}})
            prior_rows.extend(holdout)
        n = sum(f["metrics"]["n"] for f in folds)
        def wavg(key):
            return sum(f["metrics"][key] * f["metrics"]["n"] for f in folds) / n if n else math.nan
        aggregate = {
            "holdout_folds": len(folds),
            "n": n,
            "model_a_mae": wavg("model_a_mae"),
            "affine_mae": wavg("affine_mae"),
            "mae_improvement": (wavg("affine_mae") - wavg("model_a_mae")) / wavg("affine_mae") if n and wavg("affine_mae") else 0.0,
            "model_a_raw_coverage": wavg("model_a_raw_coverage"),
            "model_a_coverage": wavg("model_a_coverage"),
            "player_only_raw_coverage": wavg("player_only_raw_coverage"),
            "replacement_only_raw_coverage": wavg("replacement_only_raw_coverage"),
            "replacement_variance_share": wavg("replacement_variance_share"),
            "mean_uncertainty_scale": wavg("uncertainty_scale"),
        }
        aggregate["coverage_error"] = abs(aggregate["model_a_coverage"] - TARGET_COVERAGE)
        scarcity = context_shift(base, rows, supported[1:], candidate, rc)
        scarcity_by_candidate[candidate] = scarcity
        aggregate["scarcity_pass"] = scarcity["pass"]
        aggregates[candidate] = aggregate
        all_results[candidate] = {"aggregate": aggregate, "folds": folds}

    raw_best = min(candidates, key=lambda c: aggregates[c]["model_a_mae"])
    context_valid = [c for c in candidates if aggregates[c]["scarcity_pass"]]
    best = min(context_valid, key=lambda c: aggregates[c]["model_a_mae"]) if context_valid else raw_best

    winners = []
    for season in supported[1:]:
        scores = []
        for candidate in context_valid or candidates:
            fold = next((f for f in all_results[candidate]["folds"] if f["season"] == season), None)
            if fold:
                scores.append((fold["metrics"]["model_a_mae"], candidate))
        if scores:
            winners.append(min(scores)[1])
    winner_counts = Counter(winners)
    stability = winner_counts[best] / len(winners) if winners else 0.0

    best_rows = [r for season in supported[1:] for r in fold_rows[best].get(season, [])]
    scenarios = scenario_checks(base, best_rows, fold_rows[best], scarcity_by_candidate[best])
    scenario_passes = sum(bool(v.get("pass")) for v in scenarios.values())
    economic_pass_rate = scenario_passes / len(scenarios)

    market_folds = [f["market"] for f in all_results[best]["folds"] if f["market"].get("available")]
    market_summary = {"available_folds": len(market_folds)}
    if market_folds:
        for key in ("pearson", "spearman", "mean_absolute_standardized_residual", "material_disagreement_rate"):
            market_summary[key] = mean(float(f[key]) for f in market_folds)
        gains = [f["market_incremental_mae_gain"] for f in market_folds if f.get("market_incremental_mae_gain") is not None]
        market_summary["market_incremental_mae_gain"] = mean(gains) if gains else None
        flags = [f["market_adds_incremental_information"] for f in market_folds if f.get("market_adds_incremental_information") is not None]
        market_summary["market_adds_incremental_information_rate"] = mean(1.0 if x else 0.0 for x in flags) if flags else None

    decomposition_rows, decomposition = appreciation_decomposition(base, details_by_candidate[best], supported[1:])
    best_fold_metrics = {f["season"]: f["metrics"] for f in all_results[best]["folds"]}
    residual = persistent_residual(base, fold_rows[best], best_fold_metrics)

    agg = aggregates[best]
    material = agg["mae_improvement"] >= MATERIAL_MAE_IMPROVEMENT
    uncertainty_ok = agg["coverage_error"] <= COVERAGE_TOLERANCE
    market_independent = bool(market_folds) and market_summary.get("spearman", 1.0) < 0.98 and market_summary.get("material_disagreement_rate", 0.0) >= 0.10
    enough_folds = agg["holdout_folds"] >= 5
    stable = stability >= 0.60
    promotion = material and stable and uncertainty_ok and economic_pass_rate >= 5 / 6 and market_independent and enough_folds

    raw_uncertainty = agg["model_a_raw_coverage"]
    player_only = agg["player_only_raw_coverage"]
    replacement_share = agg["replacement_variance_share"]
    fold_raw = [f["metrics"]["model_a_raw_coverage"] for f in all_results[best]["folds"]]
    fold_scales = [f["metrics"]["uncertainty_scale"] for f in all_results[best]["folds"]]
    if player_only > TARGET_COVERAGE + COVERAGE_TOLERANCE:
        uncertainty_primary = "forecast_uncertainty"
    elif raw_uncertainty > TARGET_COVERAGE + COVERAGE_TOLERANCE and player_only <= TARGET_COVERAGE + COVERAGE_TOLERANCE:
        uncertainty_primary = "replacement_uncertainty_or_shared_component_propagation"
    else:
        uncertainty_primary = "fold_specific_calibration"
    uncertainty_diagnosis = {
        "primary_identified_source": uncertainty_primary,
        "raw_full_coverage": raw_uncertainty,
        "raw_player_only_coverage": player_only,
        "replacement_variance_share": replacement_share,
        "fold_raw_coverage_min": min(fold_raw),
        "fold_raw_coverage_max": max(fold_raw),
        "fold_raw_coverage_stddev": statistics.pstdev(fold_raw),
        "rolling_scale_min": min(fold_scales),
        "rolling_scale_max": max(fold_scales),
        "rolling_scale_mean": mean(fold_scales),
        "repair_method": "rolling pre-fold standardized-residual calibration",
    }

    model_b_specific = None
    if residual["persistent"]:
        model_b_specific = "bounded nonlinear surplus transformation for a chronologically persistent elite-tail residual"

    conclusions = {
        "raw_error_best_replacement": raw_best,
        "promotion_candidate_replacement": best,
        "replacement_winner_stability": stability,
        "replacement_winner_counts": dict(winner_counts),
        "model_a_materially_outperforms_affine": material,
        "model_a_mae_improvement": agg["mae_improvement"],
        "scarcity_sensitivity_ok": bool(scenarios["position_scarcity_shift"]["pass"]),
        "uncertainty_calibration_ok": uncertainty_ok,
        "appreciation_decline_ok": bool(scenarios["expected_appreciation_decline"]["pass"]),
        "economic_scenario_pass_rate": economic_pass_rate,
        "market_independence_ok": market_independent,
        "production_promotion_gate_cleared": promotion,
        "model_b_complexity_justified": model_b_specific is not None,
        "model_b_specific_complexity": model_b_specific,
    }
    payload = {
        "study_version": "pr131-model-a-repair-v2",
        "research_only": True,
        "frozen_thresholds": {
            "material_mae_improvement": MATERIAL_MAE_IMPROVEMENT,
            "target_coverage": TARGET_COVERAGE,
            "coverage_tolerance": COVERAGE_TOLERANCE,
            "economic_pass_requirement": "5_of_6",
            "replacement_stability_requirement": 0.60,
        },
        "supported_target_seasons": supported,
        "replacement_candidates": aggregates,
        "scarcity_diagnostics": scarcity_by_candidate,
        "best_candidate": all_results[best],
        "uncertainty_diagnosis": uncertainty_diagnosis,
        "appreciation_decomposition": decomposition,
        "market_independence": market_summary,
        "economic_scenarios": scenarios,
        "persistent_residual": residual,
        "conclusions": conclusions,
        "guardrails": [
            "Model B was not fitted.",
            "No production intrinsic-value behavior or model authority changed.",
            "Market was used only as an external diagnostic.",
            "Team-specific need was excluded from intrinsic value.",
            "Forecast retained ownership of survival and football trajectory.",
            "Time preference remains unidentified; benchmark weights were not refit.",
        ],
    }
    (args.output_dir / "model_a_repair_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(args.output_dir / "model_a_repair_point_in_time_rows.csv", details_by_candidate[best])
    write_csv(args.output_dir / "model_a_uncertainty_diagnostics.csv", uncertainty_rows)
    write_csv(args.output_dir / "model_a_appreciation_decomposition.csv", decomposition_rows)

    report = [
        "# Model A Repair Cycle — PR #131", "",
        "**Status:** research-only. No production authority changed. Model B was not fitted.", "",
        "## Replacement/context comparison", "",
        "| Candidate | MAE | Affine MAE | Improvement | Raw 80% coverage | Calibrated coverage | Scarcity pass |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for candidate in candidates:
        a = aggregates[candidate]
        report.append(f"| {candidate} | {a['model_a_mae']:.3f} | {a['affine_mae']:.3f} | {a['mae_improvement']:.1%} | {a['model_a_raw_coverage']:.1%} | {a['model_a_coverage']:.1%} | {'YES' if a['scarcity_pass'] else 'NO'} |")
    report += ["", "## Frozen-gate findings", "",
        f"- Raw-error best replacement: **{raw_best}**.",
        f"- Context-valid promotion candidate: **{best}**.",
        f"- Repaired Model A MAE: **{agg['model_a_mae']:.3f}** vs affine **{agg['affine_mae']:.3f}**; improvement **{agg['mae_improvement']:.1%}**.",
        f"- Material performance advantage: **{'PASS' if material else 'FAIL'}**.",
        f"- SF/1QB scarcity sensitivity: **{'PASS' if scenarios['position_scarcity_shift']['pass'] else 'FAIL'}**.",
        f"- Calibrated nominal-80% uncertainty coverage: **{agg['model_a_coverage']:.1%}** — **{'PASS' if uncertainty_ok else 'FAIL'}**.",
        f"- Expected appreciation/decline: **{'PASS' if scenarios['expected_appreciation_decline']['pass'] else 'FAIL'}**; direction={scenarios['expected_appreciation_decline']['directional_accuracy']:.1%}, correlation={scenarios['expected_appreciation_decline']['change_correlation']:.3f}.",
        f"- Economic-usefulness checks: **{scenario_passes}/6**.",
        f"- Market independence: **{'PASS' if market_independent else 'FAIL/INCOMPLETE'}**.",
        f"- Predefined production-promotion gate cleared: **{'YES' if promotion else 'NO'}**.",
        f"- Stable residual justifying Model B: **{model_b_specific or 'NO'}**.", "",
        "## Uncertainty diagnosis", "", "```json", json.dumps(uncertainty_diagnosis, indent=2, sort_keys=True), "```", "",
        "## Appreciation/decline decomposition", "", "```json", json.dumps(decomposition, indent=2, sort_keys=True), "```", "",
        "## Economic scenarios", "",
    ]
    for name, value in scenarios.items():
        report.append(f"- **{name}:** `{json.dumps(value, sort_keys=True)}`")
    report += ["", "## Market independence", "", "```json", json.dumps(market_summary, indent=2, sort_keys=True), "```", "",
        "## Guardrails", "",
        "- Model B was not fitted.",
        "- Production intrinsic behavior and authority were not changed.",
        "- Market values were not training targets.",
        "- Team-specific need remains downstream.",
        "- Survival remains Forecast-owned and is not double-counted.",
        "- Fixed research weights remain fixed; time preference remains unidentified.",
    ]
    text = "\n".join(report)
    (args.output_dir / "model_a_repair_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
