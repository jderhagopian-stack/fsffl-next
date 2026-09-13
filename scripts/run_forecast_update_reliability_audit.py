from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Iterable

Z80 = 1.2815515655446004
PRIMARY_CONTEXT = "12t_sf_2rb_3wr_1te_1flex"
ONE_QB_CONTEXT = "12t_1qb_2rb_3wr_1te_1flex"
CANDIDATE = "marginal_lineup_opportunity"
MIN_CELL_ROWS = 100  # same evidence-sufficiency floor already used by the PR #131 fold calibration


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def sign(value: float) -> int:
    return 1 if value > 1e-9 else -1 if value < -1e-9 else 0


def age_band(age: int | None) -> str:
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


def career_stage(experience: int) -> str:
    if experience <= 1:
        return "rookie_or_year2"
    if experience <= 3:
        return "young"
    if experience <= 7:
        return "prime"
    return "veteran"


def tier(percentile: float) -> str:
    if percentile >= 0.90:
        return "elite_tail"
    if percentile >= 0.50:
        return "middle"
    return "replacement_tail"


def uncertainty_band(sd: float, mean_value: float) -> str:
    cv = sd / max(1.0, abs(mean_value))
    if cv < 0.35:
        return "low"
    if cv < 0.70:
        return "medium"
    return "high"


def survival_band(probability: float) -> str:
    if probability >= 0.85:
        return "high_survival"
    if probability >= 0.65:
        return "medium_survival"
    return "high_attrition"


def transition_meta(calibration, state, *, rookie: bool = False) -> dict[str, object]:
    q = min(4, max(1, int(state.percentile * 4) + 1))
    key = (state.position, state.age, state.experience, q, rookie)
    item = calibration.cells.get(key)
    fallback = item is None
    if item is None:
        item = calibration.parent[state.position]
    return {
        "production_quartile": q,
        "rookie": rookie,
        "fallback_to_parent": fallback,
        "cell_key": f"{state.position}|age={state.age}|exp={state.experience}|q={q}|rookie={rookie}",
        "sample_size": int(item["sample_size"]),
        "survivor_sample_size": int(item["survivor_sample_size"]),
        "conditional_multiplier": float(item["conditional_production_multiplier"]),
        "survival_probability": float(item["survival_probability"]),
        "dispersion": float(item["conditional_multiplier_stddev"]),
        "multiplier_se": float(item["conditional_multiplier_standard_error"]),
        "survival_se": float(item["survival_standard_error"]),
    }


def source_state(base, row):
    return base.State(
        row.player_id,
        row.position,
        row.current,
        0.0,
        row.age,
        row.experience,
        (row.production_quartile - 0.5) / 4,
    )


def supported_seasons(base, rows, rc) -> list[int]:
    max_panel_season = max(r.season for r in rows)
    max_target = max_panel_season - (base.HORIZON - 1)
    result = []
    for season in range(min(r.season for r in rows) + 1, max_target + 1):
        if base.FoldCalibration(rows, season, rc).supported():
            result.append(season)
    return result


def build_raw_forecasts(base, rows, seasons, rc):
    calibrations = {}
    paths = {}
    for season in seasons:
        calibration, path = base.forecast_paths(rows, season, rc)
        calibrations[season] = calibration
        paths[season] = path
    return calibrations, paths


def build_adjacent_audit(base, rows, seasons, calibrations, paths) -> list[dict[str, object]]:
    by_season_player = {(r.season, r.player_id): r for r in rows}
    out: list[dict[str, object]] = []
    for old_fold, new_fold in zip(seasons, seasons[1:]):
        if new_fold != old_fold + 1:
            continue
        old_cal = calibrations[old_fold]
        new_cal = calibrations[new_fold]
        for new_offset in (0, 1):
            old_offset = new_offset + 1
            if old_offset not in paths[old_fold] or new_offset not in paths[new_fold]:
                continue
            old_map = {s.player_id: s for s in paths[old_fold][old_offset]}
            new_map = {s.player_id: s for s in paths[new_fold][new_offset]}
            old_pre_map = {s.player_id: s for s in paths[old_fold][old_offset - 1]}
            if new_offset == 0:
                new_pre_map = {
                    r.player_id: source_state(base, r)
                    for r in rows
                    if r.season == new_fold - 1
                }
            else:
                new_pre_map = {s.player_id: s for s in paths[new_fold][new_offset - 1]}
            target_season = new_fold + new_offset
            for player_id in sorted(set(old_map) & set(new_map) & set(old_pre_map) & set(new_pre_map)):
                actual = by_season_player.get((target_season, player_id))
                actual_points = actual.current if actual is not None else 0.0
                old_state = old_map[player_id]
                new_state = new_map[player_id]
                old_pre = old_pre_map[player_id]
                new_pre = new_pre_map[player_id]
                old_meta = transition_meta(old_cal, old_pre)
                new_meta = transition_meta(new_cal, new_pre)
                raw_revision = new_state.mean - old_state.mean
                needed_revision = actual_points - old_state.mean
                baseline_error = abs(needed_revision)
                revised_error = abs(actual_points - new_state.mean)
                same_direction = sign(raw_revision) == sign(needed_revision) and sign(raw_revision) != 0
                if sign(raw_revision) == 0:
                    classification = "no_revision"
                elif not same_direction:
                    classification = "wrong_direction"
                elif abs(raw_revision) > abs(needed_revision):
                    classification = "right_direction_too_large"
                elif abs(raw_revision) < abs(needed_revision):
                    classification = "right_direction_too_small"
                else:
                    classification = "right_direction_exact"
                new_info = by_season_player.get((new_fold - 1, player_id))
                prior_info = by_season_player.get((old_fold - 1, player_id))
                prod_change = None
                improving = "unknown"
                if new_info is not None and prior_info is not None:
                    prod_change = new_info.current - prior_info.current
                    improving = "improving" if prod_change > 1e-9 else "declining" if prod_change < -1e-9 else "flat"
                out.append({
                    "old_fold": old_fold,
                    "new_fold": new_fold,
                    "target_season": target_season,
                    "horizon_overlap": new_offset,
                    "player_id": player_id,
                    "position": new_state.position,
                    "age": new_pre.age,
                    "age_band": age_band(new_pre.age),
                    "experience": new_pre.experience,
                    "career_stage": career_stage(new_pre.experience),
                    "production_tier": tier(new_pre.percentile),
                    "player_group": "rookie_transition" if new_pre.experience <= 1 else "young_player" if new_pre.experience <= 3 else "veteran",
                    "prior_season_production_change": prod_change,
                    "prior_direction": improving,
                    "old_forecast_mean": old_state.mean,
                    "new_forecast_mean": new_state.mean,
                    "actual_points": actual_points,
                    "raw_revision": raw_revision,
                    "needed_revision": needed_revision,
                    "revision_magnitude_error": abs(raw_revision - needed_revision),
                    "no_update_magnitude_error": baseline_error,
                    "new_forecast_absolute_error": revised_error,
                    "revision_improved_absolute_error": revised_error < baseline_error,
                    "revision_direction_correct": same_direction,
                    "revision_classification": classification,
                    "old_forecast_sd": old_state.sd,
                    "new_forecast_sd": new_state.sd,
                    "uncertainty_band": uncertainty_band(new_state.sd, new_state.mean),
                    "old_interval_covered": old_state.mean - Z80 * old_state.sd <= actual_points <= old_state.mean + Z80 * old_state.sd,
                    "new_interval_covered": new_state.mean - Z80 * new_state.sd <= actual_points <= new_state.mean + Z80 * new_state.sd,
                    "old_survival_probability": old_meta["survival_probability"],
                    "new_survival_probability": new_meta["survival_probability"],
                    "survival_risk_band": survival_band(float(new_meta["survival_probability"])),
                    "survived_target": actual_points > 0.0,
                    "old_conditional_multiplier": old_meta["conditional_multiplier"],
                    "new_conditional_multiplier": new_meta["conditional_multiplier"],
                    "old_dispersion": old_meta["dispersion"],
                    "new_dispersion": new_meta["dispersion"],
                    "old_cell": old_meta["cell_key"],
                    "new_cell": new_meta["cell_key"],
                    "old_fallback": old_meta["fallback_to_parent"],
                    "new_fallback": new_meta["fallback_to_parent"],
                    "fallback_changed": old_meta["fallback_to_parent"] != new_meta["fallback_to_parent"],
                    "cohort_changed": old_meta["cell_key"] != new_meta["cell_key"],
                    "survival_probability_change": float(new_meta["survival_probability"]) - float(old_meta["survival_probability"]),
                    "conditional_multiplier_change": float(new_meta["conditional_multiplier"]) - float(old_meta["conditional_multiplier"]),
                    "forecast_sd_change": new_state.sd - old_state.sd,
                    "is_elite_qb": new_state.position == "QB" and new_pre.percentile >= 0.75 and (new_pre.age or 0) <= 33,
                    "provenance": (
                        f"old_fold=preseason-{old_fold}: transition rows season<={old_fold-2}; "
                        f"new_fold=preseason-{new_fold}: transition rows season<={new_fold-2}; "
                        f"new realized season={new_fold-1}; scored target season={target_season}"
                    ),
                })
    return out


def metrics(rows: list[dict[str, object]], revision_key: str = "raw_revision") -> dict[str, object]:
    usable = [r for r in rows if abs(float(r["needed_revision"])) > 1e-9 or abs(float(r[revision_key])) > 1e-9]
    if not usable:
        return {"n": 0}
    revisions = [float(r[revision_key]) for r in usable]
    needed = [float(r["needed_revision"]) for r in usable]
    direction = mean(1.0 if sign(a) == sign(b) and sign(a) != 0 else 0.0 for a, b in zip(revisions, needed))
    revision_mae = mean(abs(a - b) for a, b in zip(revisions, needed))
    no_update_mae = mean(abs(b) for b in needed)
    classifications = Counter(str(r.get("revision_classification", "")) for r in usable) if revision_key == "raw_revision" else Counter()
    return {
        "n": len(usable),
        "directional_accuracy": direction,
        "revision_to_needed_correlation": corr(revisions, needed),
        "revision_magnitude_mae": revision_mae,
        "no_update_magnitude_mae": no_update_mae,
        "relative_magnitude_improvement_vs_no_update": (no_update_mae - revision_mae) / no_update_mae if no_update_mae else 0.0,
        "absolute_error_improvement_rate": mean(1.0 if abs(b - a) < abs(b) else 0.0 for a, b in zip(revisions, needed)),
        "mean_revision": mean(revisions),
        "mean_needed_revision": mean(needed),
        "classification_counts": dict(classifications),
    }


def grouped_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    dimensions = (
        "position",
        "age_band",
        "career_stage",
        "production_tier",
        "player_group",
        "prior_direction",
        "uncertainty_band",
        "survival_risk_band",
        "horizon_overlap",
        "is_elite_qb",
        "fallback_changed",
    )
    out = []
    for dimension in dimensions:
        groups = defaultdict(list)
        for row in rows:
            groups[str(row[dimension])].append(row)
        for value, subset in sorted(groups.items()):
            result = metrics(subset)
            out.append({"dimension": dimension, "value": value, **result})
    return out


def fit_alpha(rows: list[dict[str, object]], position: str | None = None) -> dict[str, object]:
    subset = [r for r in rows if (position is None or r["position"] == position) and abs(float(r["raw_revision"])) > 1e-9]
    denom = sum(float(r["raw_revision"]) ** 2 for r in subset)
    raw = (
        sum(float(r["raw_revision"]) * float(r["needed_revision"]) for r in subset) / denom
        if denom > 0 else 1.0
    )
    # This is a constrained shrinkage model between the prior and updated Forecast,
    # not a post-hoc damping constant. The parameter is estimated from resolved
    # pre-cutoff revisions only; [0,1] is the structural model class.
    constrained = min(1.0, max(0.0, raw))
    return {"n": len(subset), "raw_alpha": raw, "alpha": constrained}


def rolling_alpha(audit_rows: list[dict[str, object]], new_fold: int, position: str) -> dict[str, object]:
    training = [
        r for r in audit_rows
        if int(r["new_fold"]) < new_fold and int(r["target_season"]) <= new_fold - 1
    ]
    global_fit = fit_alpha(training)
    position_fit = fit_alpha(training, position)
    chosen = position_fit if int(position_fit["n"]) >= MIN_CELL_ROWS else global_fit
    return {
        "alpha": float(chosen["alpha"]),
        "raw_alpha": float(chosen["raw_alpha"]),
        "n": int(chosen["n"]),
        "scope": f"position:{position}" if chosen is position_fit else "global",
    }


def annotate_repaired_revisions(audit_rows: list[dict[str, object]]) -> None:
    for row in audit_rows:
        fit = rolling_alpha(audit_rows, int(row["new_fold"]), str(row["position"]))
        repaired = fit["alpha"] * float(row["raw_revision"])
        row["repair_alpha"] = fit["alpha"]
        row["repair_alpha_raw_estimate"] = fit["raw_alpha"]
        row["repair_training_n"] = fit["n"]
        row["repair_scope"] = fit["scope"]
        row["repaired_revision"] = repaired
        row["repaired_forecast_mean"] = float(row["old_forecast_mean"]) + repaired
        row["repaired_revision_magnitude_error"] = abs(repaired - float(row["needed_revision"]))
        row["repaired_revision_direction_correct"] = sign(repaired) == sign(float(row["needed_revision"])) and sign(repaired) != 0


def repaired_paths(base, seasons, raw_paths, audit_rows):
    result = {}
    for season in seasons:
        season_paths = {offset: list(states) for offset, states in raw_paths[season].items()}
        prior = season - 1
        if prior not in raw_paths:
            result[season] = season_paths
            continue
        for offset in (0, 1):
            prior_offset = offset + 1
            if offset not in season_paths or prior_offset not in raw_paths[prior]:
                continue
            anchors = {s.player_id: s for s in raw_paths[prior][prior_offset]}
            adjusted = []
            for state in season_paths[offset]:
                anchor = anchors.get(state.player_id)
                if anchor is None:
                    adjusted.append(state)
                    continue
                fit = rolling_alpha(audit_rows, season, state.position)
                adjusted_mean = anchor.mean + fit["alpha"] * (state.mean - anchor.mean)
                adjusted.append(replace(state, mean=max(0.0, adjusted_mean)))
            season_paths[offset] = base.assign_percentiles(adjusted)
        result[season] = season_paths
    return result


def evaluate_with_paths(base, rows, season: int, paths, context_id: str, candidate: str):
    if not paths:
        return [], []
    forecast_rep = {o: base.replacement_levels(paths[o], context_id, candidate) for o in range(base.HORIZON)}
    realized_rep = {o: base.replacement_levels(base.actual_states(rows, season + o), context_id, candidate) for o in range(base.HORIZON)}
    actual = {o: {r.player_id: r for r in rows if r.season == season + o} for o in range(base.HORIZON)}
    path = {o: {s.player_id: s for s in paths[o]} for o in range(base.HORIZON)}
    prior = {r.player_id: r for r in rows if r.season == season - 1}
    evaluations = []
    details = []
    for player_id, first in path[0].items():
        if player_id not in prior or any(player_id not in path[o] for o in range(base.HORIZON)):
            continue
        model_a = 0.0
        model_var = 0.0
        realized = 0.0
        for offset, weight in enumerate(base.ANNUAL_WEIGHTS):
            state = path[offset][player_id]
            rep_mean, rep_sd = forecast_rep[offset][state.position]
            model_a += weight * max(0.0, state.mean - rep_mean)
            if state.mean > rep_mean:
                model_var += weight**2 * (state.sd**2 + rep_sd**2)
            actual_row = actual[offset].get(player_id)
            actual_points = actual_row.current if actual_row is not None else 0.0
            realized_replacement = realized_rep[offset][state.position][0]
            realized += weight * max(0.0, actual_points - realized_replacement)
            details.append({
                "fold_id": f"preseason-{season}",
                "target_season": season,
                "asset_id": player_id,
                "position": state.position,
                "league_context_id": context_id,
                "replacement_candidate": candidate,
                "season_offset": offset,
                "player_forecast_mean": state.mean,
                "player_forecast_stddev": state.sd,
                "replacement_forecast_mean": rep_mean,
                "replacement_forecast_stddev": rep_sd,
                "realized_player_points": actual_points,
                "realized_replacement_points": realized_replacement,
                "annual_weight": weight,
                "provenance": "PR131 Forecast-update repair; alpha estimated only from resolved earlier adjacent-fold revisions",
            })
        p = prior[player_id]
        evaluations.append(base.EvalRow(
            player_id=player_id,
            position=first.position,
            season=season,
            model_a=model_a,
            model_a_sd=math.sqrt(max(0.0, model_var)),
            affine_feature=first.mean,
            realized=realized,
            age=first.age,
            experience=p.experience + 1,
        ))
    return evaluations, details


def model_a_rerun(base, repair, rows, seasons, repaired, dynasty_repo: Path):
    crosswalk = base.market_crosswalk(dynasty_repo)
    fold_rows = {}
    all_details = []
    prior_rows = []
    folds = []
    for season in seasons:
        holdout, details = evaluate_with_paths(base, rows, season, repaired[season], PRIMARY_CONTEXT, CANDIDATE)
        snapshot = base.market_snapshot(dynasty_repo, date(season, 8, 31), PRIMARY_CONTEXT)
        holdout = base.attach_market(holdout, snapshot, crosswalk)
        fold_rows[season] = holdout
        all_details.extend(details)
        if prior_rows:
            affine = base.fit_affine(prior_rows)
            scale = repair.uncertainty_scale(prior_rows)
            parts = repair.component_variance(details)
            fm = repair.fold_metrics(base, holdout, affine, scale, parts)
            folds.append({"season": season, "metrics": fm, "market": base.market_diagnostics(holdout, prior_rows)})
        prior_rows.extend(holdout)
    n = sum(f["metrics"]["n"] for f in folds)
    def wavg(key: str) -> float:
        return sum(f["metrics"][key] * f["metrics"]["n"] for f in folds) / n if n else math.nan
    aggregate = {
        "holdout_folds": len(folds),
        "n": n,
        "model_a_mae": wavg("model_a_mae"),
        "affine_mae": wavg("affine_mae"),
        "mae_improvement": (wavg("affine_mae") - wavg("model_a_mae")) / wavg("affine_mae") if n and wavg("affine_mae") else 0.0,
        "coverage": wavg("model_a_coverage"),
        "raw_coverage": wavg("model_a_raw_coverage"),
    }
    scarcity_folds = []
    for season in seasons[1:]:
        sf, _ = evaluate_with_paths(base, rows, season, repaired[season], PRIMARY_CONTEXT, CANDIDATE)
        one, _ = evaluate_with_paths(base, rows, season, repaired[season], ONE_QB_CONTEXT, CANDIDATE)
        one_by = {r.player_id: r for r in one}
        qb, non = [], []
        for row in sf:
            other = one_by.get(row.player_id)
            if other is None:
                continue
            delta = row.model_a - other.model_a
            (qb if row.position == "QB" else non).append(delta)
        scarcity_folds.append({"season": season, "qb_relative_gain": mean(qb), "non_qb_relative_gain": mean(non)})
    scarcity = {
        "fold_count": len(scarcity_folds),
        "folds_with_positive_qb_gain": sum(1 for f in scarcity_folds if f["qb_relative_gain"] > 0),
        "qb_relative_gain": mean(f["qb_relative_gain"] for f in scarcity_folds),
        "non_qb_relative_gain": mean(f["non_qb_relative_gain"] for f in scarcity_folds),
    }
    scarcity["pass"] = scarcity["fold_count"] > 0 and scarcity["folds_with_positive_qb_gain"] == scarcity["fold_count"] and scarcity["qb_relative_gain"] > 0 and abs(scarcity["non_qb_relative_gain"]) < abs(scarcity["qb_relative_gain"])
    best_rows = [r for s in seasons[1:] for r in fold_rows.get(s, [])]
    scenarios = repair.scenario_checks(base, best_rows, fold_rows, scarcity)
    market_folds = [f["market"] for f in folds if f["market"].get("available")]
    market = {"available_folds": len(market_folds)}
    if market_folds:
        for key in ("pearson", "spearman", "mean_absolute_standardized_residual", "material_disagreement_rate"):
            market[key] = mean(float(f[key]) for f in market_folds)
        gains = [f["market_incremental_mae_gain"] for f in market_folds if f.get("market_incremental_mae_gain") is not None]
        market["market_incremental_mae_gain"] = mean(gains) if gains else None
    return aggregate, scenarios, market, fold_rows, all_details


def brier(rows: list[dict[str, object]], probability_key: str) -> float:
    return mean((float(r[probability_key]) - (1.0 if r["survived_target"] else 0.0)) ** 2 for r in rows)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
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

    here = Path(__file__).resolve().parent
    base = load_module(here / "run_multiyear_intrinsic_model_a_benchmark.py", "pr131_forecast_audit_base")
    repair = load_module(here / "run_multiyear_intrinsic_model_a_repair.py", "pr131_forecast_audit_repair")
    rc = base.load_calibration_module()
    rows = base.load_rows(args.career_panel, rc)
    seasons = supported_seasons(base, rows, rc)
    calibrations, raw_paths = build_raw_forecasts(base, rows, seasons, rc)
    audit = build_adjacent_audit(base, rows, seasons, calibrations, raw_paths)
    annotate_repaired_revisions(audit)

    baseline_update = metrics(audit, "raw_revision")
    repaired_update = metrics(audit, "repaired_revision")
    groups = grouped_metrics(audit)
    repaired = repaired_paths(base, seasons, raw_paths, audit)
    aggregate, scenarios, market, fold_rows, details = model_a_rerun(base, repair, rows, seasons, repaired, args.dynastyprocess_repo)

    elite = [r for r in audit if r["is_elite_qb"]]
    fallback_changed = [r for r in audit if r["fallback_changed"]]
    cohort_changed = [r for r in audit if r["cohort_changed"]]
    production_change_corr = corr(
        [float(r["prior_season_production_change"] or 0.0) for r in audit],
        [float(r["raw_revision"]) for r in audit],
    )
    survival = {
        "old_brier": brier(audit, "old_survival_probability"),
        "new_brier": brier(audit, "new_survival_probability"),
        "mean_probability_change": mean(float(r["survival_probability_change"]) for r in audit),
        "note": "mean-update repair does not alter Forecast survival probabilities; no survival-specific correction is applied absent separate evidence",
    }
    uncertainty = {
        "old_nominal80_coverage": mean(1.0 if r["old_interval_covered"] else 0.0 for r in audit),
        "new_nominal80_coverage": mean(1.0 if r["new_interval_covered"] else 0.0 for r in audit),
        "mean_sd_change": mean(float(r["forecast_sd_change"]) for r in audit),
        "note": "repair leaves Forecast SD unchanged; downstream rolling PIT calibration remains the existing PR #131 uncertainty repair",
    }
    audit_diagnosis = {
        "baseline": baseline_update,
        "chronologically_repaired": repaired_update,
        "elite_qb_baseline": metrics(elite, "raw_revision"),
        "elite_qb_repaired": metrics(elite, "repaired_revision"),
        "fallback_change_rate": len(fallback_changed) / len(audit) if audit else 0.0,
        "fallback_changed_baseline": metrics(fallback_changed, "raw_revision"),
        "cohort_change_rate": len(cohort_changed) / len(audit) if audit else 0.0,
        "cohort_changed_baseline": metrics(cohort_changed, "raw_revision"),
        "production_change_to_revision_correlation": production_change_corr,
        "survival_calibration": survival,
        "uncertainty_calibration": uncertainty,
        "rolling_alpha_by_position_at_final_fold": {
            pos: rolling_alpha(audit, seasons[-1], pos) for pos in base.POSITIONS
        },
    }

    scenario_passes = sum(bool(v.get("pass")) for v in scenarios.values())
    market_independent = bool(market.get("available_folds")) and market.get("spearman", 1.0) < 0.98 and market.get("material_disagreement_rate", 0.0) >= 0.10
    promotion = (
        aggregate["mae_improvement"] >= repair.MATERIAL_MAE_IMPROVEMENT
        and abs(aggregate["coverage"] - repair.TARGET_COVERAGE) <= repair.COVERAGE_TOLERANCE
        and scenario_passes >= 5
        and bool(scenarios["position_scarcity_shift"]["pass"])
        and market_independent
        and aggregate["holdout_folds"] >= 5
    )

    payload = {
        "study_version": "pr131-forecast-update-reliability-v1",
        "research_only": True,
        "supported_target_seasons": seasons,
        "adjacent_update_rows": len(audit),
        "forecast_update_audit": audit_diagnosis,
        "group_diagnostics": groups,
        "repaired_model_a": {
            "aggregate": aggregate,
            "economic_scenarios": scenarios,
            "economic_checks_passed": scenario_passes,
            "market_independence": market,
            "market_independence_ok": market_independent,
            "promotion_gate_cleared": promotion,
        },
        "guardrails": [
            "Forecast update repair is research-only and does not change production Forecast authority.",
            "Model A economics and marginal_lineup_opportunity replacement are unchanged.",
            "No Model B was fitted.",
            "No market values were used as Forecast or intrinsic targets.",
            "All repair alphas are estimated only from resolved pre-cutoff adjacent-fold revisions.",
            "Survival remains Forecast-owned and is not double-counted.",
        ],
    }
    (args.output_dir / "forecast_update_reliability_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(args.output_dir / "forecast_update_reliability_rows.csv", audit)
    write_csv(args.output_dir / "forecast_update_group_diagnostics.csv", groups)
    write_csv(args.output_dir / "forecast_update_repaired_model_a_rows.csv", details)

    appreciation = scenarios["expected_appreciation_decline"]
    elite_scenario = scenarios["elite_qb_longevity"]
    final_alphas = audit_diagnosis["rolling_alpha_by_position_at_final_fold"]
    report = [
        "# Forecast Update Reliability Audit — PR #131", "",
        "**Status:** research-only. Production Forecast and Value authority are unchanged. Model B was not fitted.", "",
        "## Adjacent-fold Forecast revision audit", "",
        f"- Adjacent revision observations: **{len(audit):,}**.",
        f"- Baseline revision directional accuracy: **{baseline_update['directional_accuracy']:.1%}**.",
        f"- Baseline revision-to-needed correlation: **{baseline_update['revision_to_needed_correlation']:.3f}**.",
        f"- Baseline revision magnitude MAE: **{baseline_update['revision_magnitude_mae']:.3f}** vs no-update **{baseline_update['no_update_magnitude_mae']:.3f}**.",
        f"- Chronologically repaired revision directional accuracy: **{repaired_update['directional_accuracy']:.1%}**.",
        f"- Chronologically repaired revision-to-needed correlation: **{repaired_update['revision_to_needed_correlation']:.3f}**.",
        f"- Chronologically repaired revision magnitude MAE: **{repaired_update['revision_magnitude_mae']:.3f}**.", "",
        "### Final-fold rolling shrinkage estimates", "",
    ]
    for pos in base.POSITIONS:
        fit = final_alphas[pos]
        report.append(f"- {pos}: alpha={fit['alpha']:.3f} (raw={fit['raw_alpha']:.3f}, n={fit['n']}, scope={fit['scope']})")
    report += ["", "## Transition diagnostics", "",
        f"- Fallback-status change rate: **{audit_diagnosis['fallback_change_rate']:.1%}**.",
        f"- Cohort/cell change rate: **{audit_diagnosis['cohort_change_rate']:.1%}**.",
        f"- Prior-season production-change / Forecast-revision correlation: **{production_change_corr:.3f}**.",
        f"- Survival Brier, old→new: **{survival['old_brier']:.4f} → {survival['new_brier']:.4f}**.",
        f"- Forecast nominal-80% coverage, old→new shared targets: **{uncertainty['old_nominal80_coverage']:.1%} → {uncertainty['new_nominal80_coverage']:.1%}**.", "",
        "## Elite-QB update audit", "",
        f"- Elite-QB adjacent updates: **{audit_diagnosis['elite_qb_baseline']['n']}**.",
        f"- Baseline elite-QB revision direction: **{audit_diagnosis['elite_qb_baseline']['directional_accuracy']:.1%}**; correlation **{audit_diagnosis['elite_qb_baseline']['revision_to_needed_correlation']:.3f}**.",
        f"- Repaired elite-QB revision direction: **{audit_diagnosis['elite_qb_repaired']['directional_accuracy']:.1%}**; correlation **{audit_diagnosis['elite_qb_repaired']['revision_to_needed_correlation']:.3f}**.", "",
        "## Model A unchanged-economics retest", "",
        f"- Model A MAE: **{aggregate['model_a_mae']:.3f}** vs affine **{aggregate['affine_mae']:.3f}**; improvement **{aggregate['mae_improvement']:.1%}**.",
        f"- Calibrated nominal-80% coverage: **{aggregate['coverage']:.1%}**.",
        f"- Elite-QB longevity: **{'PASS' if elite_scenario['pass'] else 'FAIL'}**, rank correlation **{elite_scenario['rank_signal_correlation']:.4f}**.",
        f"- Expected appreciation/decline: **{'PASS' if appreciation['pass'] else 'FAIL'}**, direction **{appreciation['directional_accuracy']:.2%}**, correlation **{appreciation['change_correlation']:.4f}**.",
        f"- Economic-usefulness checks: **{scenario_passes}/6**.",
        f"- Market independence: **{'PASS' if market_independent else 'FAIL/INCOMPLETE'}**.",
        f"- Frozen production-promotion gate: **{'CLEARED' if promotion else 'NOT CLEARED'}**.", "",
        "## Guardrails", "",
        "- Forecast owns football trajectory and survival.",
        "- Value economics were not altered to compensate for Forecast behavior.",
        "- `marginal_lineup_opportunity` and the Model A Value construction were held fixed.",
        "- Repair parameters were estimated chronologically from resolved prior evidence only.",
        "- No Model B was fitted and no production behavior was changed.",
    ]
    text = "\n".join(report)
    (args.output_dir / "forecast_update_reliability_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
