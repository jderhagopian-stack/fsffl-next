from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

from fsffl.forecast.football_state import CanonicalFootballStateEvidence, CanonicalRoleEvidence
from fsffl.forecast.integrated_i1 import I1ForecastInput, I1TrainingRow, IntegratedI1Model
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    STATE_NAMES,
    monte_carlo_shapley_scenarios,
)

SEED = 20260915
TEST_SEASONS = (2021, 2022)
PROB_TOL = 1e-8
POINT_TOL = 1e-6
SHAPLEY_MAE_TOL = 0.25
SHAPLEY_PLAYER_TOL = 0.50
SHAPLEY_SPEARMAN_MIN = 0.999
EFFICIENCY_REL_TOL = 1e-8


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def rankdata(values):
    values = list(values)
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    output = [0.0] * len(values); index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = (index + end - 1) / 2 + 1
        for member in order[index:end]:
            output[member] = rank
        index = end
    return output


def corr(xs, ys):
    xs = list(xs); ys = list(ys)
    if len(xs) < 2:
        return 0.0
    mx = mean(xs); my = mean(ys)
    dx = [x - mx for x in xs]; dy = [y - my for y in ys]
    denominator = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / denominator if denominator > 1e-12 else 0.0


def spearman(xs, ys):
    return corr(rankdata(xs), rankdata(ys))


def _role(raw):
    if not raw:
        return None
    return CanonicalRoleEvidence(
        games=max(0.0, float(raw.get("games", 0) or 0)),
        opportunity_per_game=max(0.0, float(raw.get("opportunity_per_game", 0) or 0)),
        role_band=str(raw.get("role_band") or "unknown"),
    )


def canonical_evidence(player_id, position, age, experience, current_points, prior_points, usage, raw):
    role = _role(usage)
    raw = raw or {}
    roster_weeks = max(0.0, float(raw.get("roster_weeks", 0) or 0))
    injury_report_weeks = max(0.0, float(raw.get("injury_report_weeks", 0) or 0))
    participation_weeks = max(0.0, float(raw.get("participation_weeks", 0) or 0))
    return CanonicalFootballStateEvidence(
        player_id=player_id,
        position=position,
        age_years=age,
        experience_years=int(experience) if experience is not None else None,
        current_fantasy_points=max(0.0, float(current_points)),
        prior_fantasy_points=None if prior_points is None else max(0.0, float(prior_points)),
        role=role,
        role_coverage=role is not None,
        roster_weeks=roster_weeks,
        roster_coverage=roster_weeks > 0,
        injury_report_weeks=injury_report_weeks,
        injury_coverage=injury_report_weeks > 0,
        participation_weeks=participation_weeks,
        participation_coverage=participation_weeks > 0,
        stats_weeks=max(0.0, float(raw.get("stats_weeks", 0) or 0)),
        snap_play_weeks=max(0.0, float(raw.get("snap_play_weeks", 0) or 0)),
        active_share=max(0.0, min(1.0, float(raw.get("active_share", 0) or 0))),
        released_share=max(0.0, min(1.0, float(raw.get("released_share", 0) or 0))),
        practice_share=max(0.0, min(1.0, float(raw.get("practice_share", 0) or 0))),
        reserve_share=max(0.0, min(1.0, float(raw.get("reserve_share", 0) or 0))),
        last_status_active=bool(raw.get("last_status_active", 0)),
        last_status_attached=bool(raw.get("last_status_attached", 0)),
        last_status_release=bool(raw.get("last_status_release", 0)),
        last_status_practice=bool(raw.get("last_status_practice", 0)),
        last_status_reserve=bool(raw.get("last_status_reserve", 0)),
        status_change_count=max(0.0, float(raw.get("status_change_count", 0) or 0)),
        team_change_count=max(0.0, float(raw.get("team_change_count", 0) or 0)),
        active_return_count=max(0.0, float(raw.get("active_return_count", 0) or 0)),
        release_entry_count=max(0.0, float(raw.get("release_entry_count", 0) or 0)),
        practice_entry_count=max(0.0, float(raw.get("practice_entry_count", 0) or 0)),
        reserve_entry_count=max(0.0, float(raw.get("reserve_entry_count", 0) or 0)),
        injury_limited_weeks=max(0.0, float(raw.get("injury_limited_weeks", 0) or 0)),
        non_ir_injury_limited_weeks=max(0.0, float(raw.get("non_ir_injury_limited_weeks", 0) or 0)),
        inactive_injury_limited_weeks=max(0.0, float(raw.get("inactive_injury_limited_weeks", 0) or 0)),
        reserve_injury_limited_weeks=max(0.0, float(raw.get("reserve_injury_limited_weeks", 0) or 0)),
        non_ir_injury_flag=bool(raw.get("non_ir_injury_flag", 0)),
        inactive_injury_flag=bool(raw.get("inactive_injury_flag", 0)),
    )


def training_rows_from_research(records, position_enum):
    rows = []
    for record in records:
        position = position_enum(record["position"])
        evidence = canonical_evidence(
            "training",
            position,
            None,
            record["exp"],
            record["srcpts"],
            record["prev"],
            record["u"],
            record["e"],
        )
        rows.append(
            I1TrainingRow(
                position=position,
                age_band=record["age"],
                current_state=record["current"],
                horizon=int(record["h"]),
                target_state=record["state"],
                target_points=max(0.0, float(record["points"])),
                current_points=max(0.0, float(record["srcpts"])),
                prior_points=None if record["prev"] is None else max(0.0, float(record["prev"])),
                experience_years=int(record["exp"]) if record["exp"] is not None else None,
                evidence=evidence,
            )
        )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--usage-panel", type=Path, required=True)
    parser.add_argument("--model-a-rows", type=Path, required=True)
    parser.add_argument("--qb-results", type=Path, required=True)
    parser.add_argument("--prior-forecast-json", type=Path, required=True)
    parser.add_argument("--prior-event-json", type=Path, required=True)
    parser.add_argument("--prior-persistence-json", type=Path, required=True)
    parser.add_argument("--integrated-results", type=Path, required=True)
    parser.add_argument("--downstream-results", type=Path, required=True)
    parser.add_argument("--downstream-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    research_scripts = args.research_root / "scripts"
    im = load(research_scripts / "run_integrated_multivariate_forecast.py", "parity_im")
    pf = load(research_scripts / "run_persistence_first_forecast_calibration.py", "parity_pf")
    prior = load(research_scripts / "run_forecast_low_end_career_calibration.py", "parity_prior")
    legacy = load(research_scripts / "run_fundamental_intrinsic_residual_calibration.py", "parity_legacy")
    parity = load(research_scripts / "run_fundamental_intrinsic_production_parity.py", "parity_build")
    base = load(research_scripts / "run_intrinsic_explicit_state_challenge.py", "parity_base")
    evt = load(research_scripts / "reconstruct_event_time_absence_cause_evidence.py", "parity_evt")

    selected = json.loads(args.integrated_results.read_text())
    frozen_downstream = json.loads(args.downstream_results.read_text())
    frozen_rows = json.loads(args.downstream_rows.read_text())
    frozen_by = {(int(row["season"]), row["player_id"]): row for row in frozen_rows}
    if selected["holdout"]["selected"] != "I1" or float(selected["C"]["I1"]) != 0.25:
        raise RuntimeError("research selection is not frozen I1 C=0.25")

    F = json.loads(args.prior_forecast_json.read_text())
    E = json.loads(args.prior_event_json.read_text())
    P = json.loads(args.prior_persistence_json.read_text())
    checks = {
        "c0": abs(F["summaries"]["low_end"]["c0_"]["state_brier"] - .17558645736306655) < 1e-10,
        "resolution": abs(E["overall_resolution"]["resolved_share"] - 685 / 925) < 1e-10,
        "p145": P["conclusion"] == "P4. TWO-STAGE PERSISTENCE-FIRST DECOMPOSITION DOES NOT IMPROVE THE PROBLEM",
    }
    if not all(checks.values()):
        raise RuntimeError("frozen evidence parity failed")

    examples, _ = parity.build_examples(
        panel_path=args.career_panel,
        model_rows_path=args.model_a_rows,
        qb_results_path=args.qb_results,
        legacy=legacy,
    )
    panel = legacy.load_rows(args.career_panel)
    by = {(row.player_id, row.season): row for row in panel}
    usage = pf.load_usage(args.usage_panel)
    qb = parity.load_qb_probabilities(args.qb_results)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))
    caps = load(research_scripts / "run_deployment_shapley_intrinsic_research.py", "parity_dep").subset_caps()

    max_probability_diff = 0.0
    max_persistence_diff = 0.0
    max_anticipated_diff = 0.0
    player_shapley_diffs = []
    production_rows = []
    season_diagnostics = {}
    started = time.perf_counter()

    for season in TEST_SEASONS:
        supply = [example for example in examples if example.season == season and (example.player_id, season) in by]
        bounds = base.fit_state_boundaries(panel, season)
        transitions = base.fit_transition_counts(panel, season, bounds)
        records = im.records(pf, base, panel, by, season, bounds, usage, ev)
        research_model = im.fitmodel(records, 0.25, "I1")
        production_model = IntegratedI1Model(training_rows_from_research(records, im.Position))
        forecasts = {}

        for example in supply:
            source = by[(example.player_id, season)]
            current_state = base.state_for_points(source.points, bounds[example.position])
            band = base.age_band(example.position, example.age)
            role = usage.get((example.player_id, season))
            raw_evidence = ev["source"].get((example.player_id, season))
            previous = by.get((example.player_id, season - 1))
            prior_points = None if previous is None else float(previous.points)
            position = im.Position(example.position)
            canonical = canonical_evidence(
                example.player_id,
                position,
                example.age,
                example.experience,
                float(source.points),
                prior_points,
                role,
                raw_evidence,
            )
            forecasts[example.player_id] = {}
            for horizon in (1, 2):
                _, p0 = prior.probs(base, transitions, example, bounds, qb, horizon)
                research_input = {
                    "position": example.position,
                    "age": band,
                    "current": current_state,
                    "h": horizon,
                    "srcpts": float(source.points),
                    "prev": prior_points,
                    "exp": example.experience,
                    "u": role,
                    "e": raw_evidence,
                }
                research_probabilities, research_path = im.pred(research_model, research_input, p0)
                research_expected = max(0.0, float(research_model["means"].exp(research_probabilities, example.position, horizon)))
                item = I1ForecastInput(
                    position=position,
                    age_band=band,
                    current_state=current_state,
                    horizon=horizon,
                    current_points=max(0.0, float(source.points)),
                    prior_points=prior_points,
                    experience_years=int(example.experience) if example.experience is not None else None,
                    evidence=canonical,
                )
                result = production_model.predict(item, fallback_probabilities=p0)
                probability_diff = max(abs(result.probabilities[state] - research_probabilities[state]) for state in STATE_NAMES)
                max_probability_diff = max(max_probability_diff, probability_diff)
                max_persistence_diff = max(max_persistence_diff, abs(result.persistence_probability - (1 - research_probabilities["out"])))
                max_anticipated_diff = max(max_anticipated_diff, abs(result.anticipated_points - research_expected))
                expected_path = "rich" if research_path == "full" else ("reduced" if research_path == "red" else "legacy_fallback")
                if result.evidence_path != expected_path:
                    raise AssertionError(f"evidence path mismatch: {result.evidence_path} != {expected_path}")
                forecasts[example.player_id][horizon] = result

        horizon_results = {}
        efficiency = []
        for horizon in (0, 1, 2):
            if horizon == 0:
                players = [(example.player_id, example.position, max(0.0, float(example.means[0]))) for example in supply]
                scenarios = {player_id: (weight,) for player_id, _position, weight in players}
            else:
                players = [(example.player_id, example.position, forecasts[example.player_id][horizon].anticipated_points) for example in supply]
                scenarios = {
                    example.player_id: (
                        forecasts[example.player_id][horizon].anticipated_points,
                        *(forecasts[example.player_id][horizon].state_means[state] for state in STATE_NAMES),
                    )
                    for example in supply
                }
            result = monte_carlo_shapley_scenarios(
                players,
                scenarios,
                caps,
                permutations=FROZEN_SHAPLEY_PERMUTATIONS,
                seed=SEED + season * 10 + horizon,
            )
            horizon_results[horizon] = result
            efficiency.append(abs(result.efficiency_residual) / max(1.0, abs(result.full_value)))

        for example in supply:
            frozen = frozen_by.get((season, example.player_id))
            if frozen is None:
                continue
            phi0 = horizon_results[0].estimates[example.player_id][0]
            future = []
            total = phi0
            for horizon in (1, 2):
                forecast = forecasts[example.player_id][horizon]
                values = horizon_results[horizon].estimates[example.player_id]
                expected_phi = sum(
                    forecast.probabilities[state] * values[1 + STATE_NAMES.index(state)]
                    for state in STATE_NAMES
                )
                future.append(expected_phi)
                total += (FROZEN_INTRINSIC_DISCOUNT ** horizon) * expected_phi
            diff = total - float(frozen["integrated_shapley"])
            player_shapley_diffs.append(diff)
            production_rows.append({
                "season": season,
                "player_id": example.player_id,
                "position": example.position,
                "implementation": total,
                "frozen": float(frozen["integrated_shapley"]),
                "realized_h3": float(frozen["realized_h3"]),
                "diff": diff,
            })
        season_diagnostics[str(season)] = {
            "supply_n": len(supply),
            "max_relative_efficiency_residual": max(efficiency),
        }

    implementation_values = [row["implementation"] for row in production_rows]
    frozen_values = [row["frozen"] for row in production_rows]
    realized = [row["realized_h3"] for row in production_rows]
    implementation_mae = mean(abs(value - target) for value, target in zip(implementation_values, realized, strict=True))
    frozen_mae = float(frozen_downstream["metrics"]["integrated_vs_realized_h3"]["mae"])
    player_max = max(abs(diff) for diff in player_shapley_diffs) if player_shapley_diffs else float("inf")
    player_spearman = spearman(implementation_values, frozen_values)
    max_efficiency = max(item["max_relative_efficiency_residual"] for item in season_diagnostics.values())

    gates = {
        "probability_parity": max_probability_diff <= PROB_TOL,
        "persistence_parity": max_persistence_diff <= PROB_TOL,
        "anticipated_production_parity": max_anticipated_diff <= POINT_TOL,
        "shapley_mae_parity": abs(implementation_mae - frozen_mae) <= SHAPLEY_MAE_TOL,
        "shapley_player_max_parity": player_max <= SHAPLEY_PLAYER_TOL,
        "shapley_rank_parity": player_spearman >= SHAPLEY_SPEARMAN_MIN,
        "shapley_efficiency": max_efficiency <= EFFICIENCY_REL_TOL,
    }
    output = {
        "study": "forecast-intrinsic-production-parity-v1",
        "frozen_candidate": {"name": "I1", "C": 0.25},
        "predeclared_tolerances": {
            "probability": PROB_TOL,
            "anticipated_points": POINT_TOL,
            "shapley_mae": SHAPLEY_MAE_TOL,
            "shapley_player": SHAPLEY_PLAYER_TOL,
            "shapley_spearman": SHAPLEY_SPEARMAN_MIN,
            "efficiency_relative": EFFICIENCY_REL_TOL,
        },
        "gates": gates,
        "pass": all(gates.values()),
        "metrics": {
            "rows": len(production_rows),
            "max_probability_abs_diff": max_probability_diff,
            "max_persistence_abs_diff": max_persistence_diff,
            "max_anticipated_points_abs_diff": max_anticipated_diff,
            "implementation_shapley_mae_vs_realized_h3": implementation_mae,
            "frozen_shapley_mae_vs_realized_h3": frozen_mae,
            "shapley_mae_abs_diff": abs(implementation_mae - frozen_mae),
            "max_player_shapley_abs_diff": player_max,
            "implementation_vs_frozen_shapley_spearman": player_spearman,
            "max_relative_efficiency_residual": max_efficiency,
            "runtime_seconds": time.perf_counter() - started,
        },
        "season_diagnostics": season_diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True))
    args.output.with_name("production_parity_rows.json").write_text(json.dumps(production_rows, indent=2, sort_keys=True))
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
