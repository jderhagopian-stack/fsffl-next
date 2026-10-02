from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsffl.team_utility.simulation import (
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    WeeklyTeamScoringDistribution,
    _settings_derived_playoff_rules,
    compare_counterfactual_simulation_results,
    simulate_regular_season,
)


SCREENING_CONTEXT_COUNT = 1_000
CONVERGENCE_COUNTS = (5_000, 10_000, 25_000, 35_000, 50_000, 75_000, 100_000)
COUNTS = (SCREENING_CONTEXT_COUNT, *CONVERGENCE_COUNTS)
REFERENCE_COUNT = 100_000
PRODUCTION_COUNT = 50_000
ROOT_SEEDS = tuple(range(20261201, 20261209))
FOCAL_TEAM = "t05"
OTHER_TEAM = "t06"
STUDY_MODEL_VERSION = "simulation-convergence-study-v2:independent-root-stability"
RNG_BATCH_SIZE = 500


@dataclass(frozen=True)
class RunBundle:
    baseline: Any
    clear: Any
    near: Any
    elapsed_seconds: float


def _round_robin_schedule(team_count: int = 12, weeks: int = 14) -> tuple[ScheduledMatchup, ...]:
    teams = [f"t{i:02d}" for i in range(team_count)]
    rotation = teams[:]
    rows: list[ScheduledMatchup] = []
    for week in range(1, weeks + 1):
        for index in range(team_count // 2):
            rows.append(
                ScheduledMatchup(
                    week=week,
                    home_team_id=rotation[index],
                    away_team_id=rotation[-1 - index],
                )
            )
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return tuple(rows)


def _weekly_rows(
    schedule: tuple[ScheduledMatchup, ...],
    *,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> tuple[WeeklyTeamScoringDistribution, ...]:
    rows: list[WeeklyTeamScoringDistribution] = []
    for matchup in schedule:
        for team_id in (matchup.home_team_id, matchup.away_team_id):
            index = int(team_id[1:])
            shift = focal_shift if team_id == FOCAL_TEAM else other_shift if team_id == OTHER_TEAM else 0.0
            rows.append(
                WeeklyTeamScoringDistribution(
                    week=matchup.week,
                    team_id=team_id,
                    mean_points=104.0 + index * 2.4 + (matchup.week % 3) + shift,
                    stddev_points=17.0 + (index % 4) * 2.5,
                    model_version="convergence-weekly-v1",
                )
            )
    return tuple(rows)


def _playoff_rows(
    *,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> tuple[WeeklyTeamScoringDistribution, ...]:
    rules = _settings_derived_playoff_rules(6, 15)
    assert rules is not None
    rows: list[WeeklyTeamScoringDistribution] = []
    for week in rules.round_weeks:
        for index in range(12):
            team_id = f"t{index:02d}"
            shift = focal_shift if team_id == FOCAL_TEAM else other_shift if team_id == OTHER_TEAM else 0.0
            rows.append(
                WeeklyTeamScoringDistribution(
                    week=week,
                    team_id=team_id,
                    mean_points=105.0 + index * 2.4 + (week % 3) + shift,
                    stddev_points=17.0 + (index % 4) * 2.5,
                    model_version="convergence-playoff-v1",
                )
            )
    return tuple(rows)


def _request(
    *,
    count: int,
    seed: int,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> RegularSeasonSimulationInput:
    schedule = _round_robin_schedule()
    rules = _settings_derived_playoff_rules(6, 15)
    assert rules is not None
    return RegularSeasonSimulationInput(
        weekly_scoring=_weekly_rows(
            schedule,
            focal_shift=focal_shift,
            other_shift=other_shift,
        ),
        playoff_weekly_scoring=_playoff_rows(
            focal_shift=focal_shift,
            other_shift=other_shift,
        ),
        schedule=schedule,
        playoff_team_count=6,
        playoff_rules=rules,
        future_pick_draft_season=2027,
        simulation_count=count,
        seed=seed,
        model_version=STUDY_MODEL_VERSION,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=RNG_BATCH_SIZE,
    )


def _run_bundle(count: int, seed: int) -> RunBundle:
    started = time.perf_counter()
    baseline = simulate_regular_season(_request(count=count, seed=seed))
    clear = simulate_regular_season(
        _request(count=count, seed=seed, focal_shift=6.0, other_shift=-6.0)
    )
    near = simulate_regular_season(
        _request(count=count, seed=seed, focal_shift=0.5, other_shift=-0.5)
    )
    return RunBundle(
        baseline=baseline,
        clear=clear,
        near=near,
        elapsed_seconds=time.perf_counter() - started,
    )


def _outcomes(result) -> dict[str, Any]:
    return {row.team_id: row for row in result.outcomes}


def _finishes(result) -> dict[str, Any]:
    return {row.team_id: row for row in result.finish_distributions}


def _picks(result) -> dict[str, Any]:
    return {row.original_team_id: row for row in result.future_pick_distributions}


def _pick_vector(row, team_count: int = 12) -> tuple[float, ...]:
    by_slot = {item.slot_in_round: item.probability for item in row.slot_probabilities}
    return tuple(by_slot.get(slot, 0.0) for slot in range(1, team_count + 1))


def _tv(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right, strict=True))


def _sign(value: float | None, *, eps: float = 1e-12) -> int | None:
    if value is None:
        return None
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _delta_metrics(baseline, scenario) -> dict[str, float | None]:
    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id=FOCAL_TEAM,
        model_version="convergence-counterfactual-v1",
    )
    return {
        "expected_wins": delta.expected_wins,
        "playoff_probability": delta.playoff_probability,
        "championship_probability": delta.championship_probability,
    }


def _absolute_metrics(bundle: RunBundle) -> dict[str, float | None]:
    outcomes = _outcomes(bundle.baseline)
    focal = outcomes[FOCAL_TEAM]
    pick = _picks(bundle.baseline)[FOCAL_TEAM]
    result: dict[str, float | None] = {
        "baseline_expected_wins": focal.expected_wins,
        "baseline_playoff_probability": focal.playoff_probability,
        "baseline_championship_probability": focal.championship_probability,
        "baseline_future_pick_expected_slot": pick.expected_slot,
    }
    for label, scenario in (("clear", bundle.clear), ("near", bundle.near)):
        values = _delta_metrics(bundle.baseline, scenario)
        for metric, value in values.items():
            result[f"{label}_{metric}_delta"] = value
    return result


def _comparison_metrics(bundle: RunBundle, reference: RunBundle) -> dict[str, float | bool | None]:
    out = _outcomes(bundle.baseline)
    ref_out = _outcomes(reference.baseline)
    finish = _finishes(bundle.baseline)
    ref_finish = _finishes(reference.baseline)
    picks = _picks(bundle.baseline)
    ref_picks = _picks(reference.baseline)

    result: dict[str, float | bool | None] = {
        "expected_wins_max_abs_error_vs_100k": max(
            abs(out[team].expected_wins - ref_out[team].expected_wins)
            for team in out
        ),
        "playoff_probability_max_abs_error_vs_100k": max(
            abs((out[team].playoff_probability or 0.0) - (ref_out[team].playoff_probability or 0.0))
            for team in out
        ),
        "championship_probability_max_abs_error_vs_100k": max(
            abs((out[team].championship_probability or 0.0) - (ref_out[team].championship_probability or 0.0))
            for team in out
        ),
        "finish_rank_max_tv_vs_100k": max(
            _tv(
                tuple(finish[team].rank_probabilities),
                tuple(ref_finish[team].rank_probabilities),
            )
            for team in finish
        ),
        "future_pick_slot_max_tv_vs_100k": max(
            _tv(_pick_vector(picks[team]), _pick_vector(ref_picks[team]))
            for team in picks
        ),
        "elapsed_seconds_three_runs": bundle.elapsed_seconds,
    }

    for label, scenario, ref_scenario in (
        ("clear", bundle.clear, reference.clear),
        ("near", bundle.near, reference.near),
    ):
        values = _delta_metrics(bundle.baseline, scenario)
        refs = _delta_metrics(reference.baseline, ref_scenario)
        for metric in ("expected_wins", "playoff_probability", "championship_probability"):
            value = values[metric]
            ref = refs[metric]
            result[f"{label}_{metric}_delta_abs_error_vs_100k"] = (
                None if value is None or ref is None else abs(value - ref)
            )
            result[f"{label}_{metric}_delta_sign_matches_100k"] = (
                None if value is None or ref is None else _sign(value) == _sign(ref)
            )
    return result


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _aggregate(rows: list[dict[str, float | bool | None]]) -> dict[str, Any]:
    keys = sorted({key for row in rows for key in row})
    out: dict[str, Any] = {}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        if not values:
            out[key] = None
        elif all(isinstance(value, bool) for value in values):
            out[key] = {
                "agreement_rate": sum(1 for value in values if value) / len(values),
                "n": len(values),
            }
        else:
            numeric = [float(value) for value in values]
            out[key] = {
                "median": statistics.median(numeric),
                "p90": _percentile(numeric, 0.90),
                "max": max(numeric),
                "n": len(numeric),
            }
    return out


def _seed_stability(
    rows: list[dict[str, float | None]],
) -> dict[str, Any]:
    keys = sorted({key for row in rows for key in row})
    result: dict[str, Any] = {}
    for key in keys:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        if not values:
            result[key] = None
            continue
        cell: dict[str, Any] = {
            "mean": statistics.mean(values),
            "stddev_across_independent_roots": statistics.pstdev(values),
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "n": len(values),
        }
        if key.endswith("_delta"):
            signs = [_sign(value) for value in values]
            counts = {sign: signs.count(sign) for sign in set(signs)}
            modal = max(counts.values())
            cell["sign_consensus_rate"] = modal / len(signs)
            cell["signs"] = {
                str(sign): count for sign, count in sorted(counts.items(), key=lambda item: str(item[0]))
            }
        result[key] = cell
    return result


def _pit_readiness(repo_root: Path) -> dict[str, Any]:
    inventory_path = (
        repo_root
        / "docs/operations/evidence/simulation_item8_pit_inventory_20261002.json"
    )
    if not inventory_path.exists():
        raise FileNotFoundError(
            "item-8 PIT inventory is required; do not infer historical Forecast coverage"
        )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    eligibility = inventory["calibration_eligibility"]
    evidence = inventory["authentic_evidence"]
    return {
        "status": "authentic_inputs_available_final_outcomes_pending",
        "eligible_full_simulation_cases": int(
            eligibility["fully_realized_final_season_cases"]
        ),
        "scored_probability_observations": int(
            eligibility["scored_probability_observations"]
        ),
        "scored_continuous_observations": int(
            eligibility["scored_continuous_observations"]
        ),
        "prospective_input_checkpoints_exist": bool(
            eligibility["prospective_input_checkpoints_exist"]
        ),
        "broad_multi_year_forecast_coverage": bool(
            eligibility["broad_multi_year_forecast_coverage"]
        ),
        "state_snapshot_count": int(
            evidence["canonical_state_snapshots"]["total"]
        ),
        "projection_snapshot_count": int(
            evidence["provider_projection_snapshots"]["total"]
        ),
        "projection_observation_count": int(
            evidence["provider_projection_snapshots"]["normalized_observations"]
        ),
        "prospective_football_state_capture_count": int(
            evidence["prospective_football_state_captures"]["total"]
        ),
        "durable_state_forecast_pairs": evidence["durable_state_forecast_pairs"],
        "pre_opener_forecast_only_evidence": evidence[
            "pre_opener_forecast_only_evidence"
        ],
        "earliest_matched_state_forecast_checkpoint": evidence[
            "earliest_matched_state_forecast_checkpoint"
        ],
        "post_opener_frozen_baseline": evidence["post_opener_frozen_baseline"],
        "reason": eligibility["reason"],
        "limitations": inventory["limitations"],
        "framework": {
            "module": "fsffl.team_utility.simulation_validation",
            "probability_metrics": "Brier score, mean predicted probability, observed rate, calibration bias",
            "continuous_metrics": "mean error, MAE, RMSE",
            "leakage_guards": (
                "State as_of and Forecast effective/retrieved timestamps must be <= "
                "checkpoint cutoff; realized outcome must postdate cutoff."
            ),
        },
        "allowed_claim": (
            "Authentic PIT input evidence exists and is retained for prospective "
            "Simulation calibration. Final-season standings/playoff/title/pick "
            "calibration sample size is currently zero because 2026 outcomes are not final."
        ),
        "prohibited_shortcut": (
            "Do not reconstruct unavailable historical Forecasts from current data, "
            "and do not count repeated refresh artifacts as independent calibration cases."
        ),
    }


def _recommendation(summary: dict[int, dict[str, Any]]) -> dict[str, Any]:
    production = summary[PRODUCTION_COUNT]
    sign_rates = [
        cell["agreement_rate"]
        for key, cell in production.items()
        if key.endswith("_delta_sign_matches_100k") and isinstance(cell, dict)
    ]
    return {
        "production_count": PRODUCTION_COUNT,
        "reference_count": REFERENCE_COUNT,
        "production_sign_agreement_min": min(sign_rates) if sign_rates else None,
        "authority_change_applied": False,
        "management_approval_required_for_any_change": True,
        "interpretation": (
            "Use the measured 50k-vs-100k error envelope and sign stability to "
            "decide whether a different production count is worth considering. "
            "Do not infer a new adaptive authority rule from preview-stage counts."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/research/simulation_convergence_pit_20261002"),
    )
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-count", type=int, default=len(ROOT_SEEDS))
    args = parser.parse_args()

    if args.seed_start < 0 or args.seed_count < 1:
        raise SystemExit("seed-start must be nonnegative and seed-count positive")
    seeds = ROOT_SEEDS[args.seed_start : args.seed_start + args.seed_count]
    if not seeds:
        raise SystemExit("requested seed slice is empty")

    raw: dict[int, list[dict[str, float | bool | None]]] = {
        count: [] for count in COUNTS
    }
    absolute_raw: dict[int, list[dict[str, float | None]]] = {
        count: [] for count in COUNTS
    }
    seed_runtime_seconds: dict[int, float] = {}

    for seed in seeds:
        bundles: dict[int, RunBundle] = {}
        seed_started = time.perf_counter()
        for count in COUNTS:
            bundles[count] = _run_bundle(count, seed)
        reference = bundles[REFERENCE_COUNT]
        for count in COUNTS:
            raw[count].append(_comparison_metrics(bundles[count], reference))
            absolute_raw[count].append(_absolute_metrics(bundles[count]))
        seed_runtime_seconds[seed] = time.perf_counter() - seed_started
        print(
            json.dumps(
                {
                    "event": "seed_complete",
                    "seed": seed,
                    "elapsed_seconds": round(seed_runtime_seconds[seed], 3),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    summary = {count: _aggregate(raw[count]) for count in COUNTS}
    independent_seed_stability = {
        count: _seed_stability(absolute_raw[count]) for count in COUNTS
    }
    pit = _pit_readiness(Path("."))
    report = {
        "study_id": "simulation-convergence-pit-20261002-v1",
        "authority_status": "research_only_no_production_change",
        "rng_protocol": NUMPY_PCG64_BATCHED_GAUSS_V1,
        "rng_batch_size": RNG_BATCH_SIZE,
        "counts": list(COUNTS),
        "governed_convergence_counts": list(CONVERGENCE_COUNTS),
        "screening_context_count": SCREENING_CONTEXT_COUNT,
        "reference_count": REFERENCE_COUNT,
        "production_count": PRODUCTION_COUNT,
        "root_seeds": list(seeds),
        "seed_start": args.seed_start,
        "raw_by_count": {
            str(count): rows for count, rows in raw.items()
        },
        "absolute_raw_by_count": {
            str(count): rows for count, rows in absolute_raw.items()
        },
        "fixture": {
            "teams": 12,
            "regular_season_weeks": 14,
            "playoff_teams": 6,
            "playoff_weeks": [15, 16, 17],
            "future_pick_draft_season": 2027,
            "draft_order_authority": "governed_standard_fallback",
            "scenarios": {
                "clear": {FOCAL_TEAM: 6.0, OTHER_TEAM: -6.0},
                "near_boundary": {FOCAL_TEAM: 0.5, OTHER_TEAM: -0.5},
            },
        },
        "convergence_summary": {str(key): value for key, value in summary.items()},
        "independent_seed_stability": {
            str(key): value for key, value in independent_seed_stability.items()
        },
        "seed_runtime_seconds": seed_runtime_seconds,
        "pit_calibration": pit,
        "authority_recommendation_guard": _recommendation(summary),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "RESULTS.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    production = summary[PRODUCTION_COUNT]
    lines = [
        "# Simulation 2.0 item 8 — convergence + PIT calibration study",
        "",
        "**Status:** research evidence only; production authority remains 50,000.",
        "",
        f"- RNG: {NUMPY_PCG64_BATCHED_GAUSS_V1}, batch {RNG_BATCH_SIZE}",
        f"- Seeds: {len(seeds)}",
        f"- Counts executed: {', '.join(f'{value:,}' for value in COUNTS)}",
        (
            "- Governed convergence range: "
            + ", ".join(f"{value:,}" for value in CONVERGENCE_COUNTS)
        ),
        (
            f"- {SCREENING_CONTEXT_COUNT:,} is shown only as the governed item-7 "
            "screening context; it is not a canonical-authority candidate."
        ),
        f"- Reference: {REFERENCE_COUNT:,} (research reference only)",
        "",
        "## 50,000 vs 100,000 reference envelope",
        "",
    ]
    for key in (
        "expected_wins_max_abs_error_vs_100k",
        "finish_rank_max_tv_vs_100k",
        "playoff_probability_max_abs_error_vs_100k",
        "championship_probability_max_abs_error_vs_100k",
        "future_pick_slot_max_tv_vs_100k",
    ):
        cell = production[key]
        lines.append(
            f"- {key}: median={cell['median']:.6f}, p90={cell['p90']:.6f}, max={cell['max']:.6f}"
        )
    lines += ["", "## Scenario delta sign stability at 50,000", ""]
    for key, cell in production.items():
        if key.endswith("_delta_sign_matches_100k") and isinstance(cell, dict):
            lines.append(f"- {key}: {cell['agreement_rate']:.1%} ({cell['n']} seeds)")
    lines.append(
        "- Interpretation: stability/sensitivity only; alternate-world outcomes are "
        "not historically observable and these are not causal Decision-accuracy claims."
    )
    lines += ["", "## Independent-root stability at 50,000", ""]
    for key, cell in independent_seed_stability[PRODUCTION_COUNT].items():
        if isinstance(cell, dict):
            line = (
                f"- {key}: mean={cell['mean']:.6f}, "
                f"root_stddev={cell['stddev_across_independent_roots']:.6f}, "
                f"range={cell['range']:.6f}, n={cell['n']}"
            )
            if "sign_consensus_rate" in cell:
                line += f", sign_consensus={cell['sign_consensus_rate']:.1%}"
            lines.append(line)
    lines += [
        "",
        "## PIT calibration",
        "",
        f"- Status: {pit['status']}",
        f"- Authentic canonical State snapshots: {pit['state_snapshot_count']}",
        f"- Authentic provider projection snapshots: {pit['projection_snapshot_count']}",
        f"- Normalized projection observations: {pit['projection_observation_count']}",
        (
            "- Authentic prospective football-state captures: "
            f"{pit['prospective_football_state_capture_count']}"
        ),
        (
            "- Finalized full-season Simulation calibration cases: "
            f"{pit['eligible_full_simulation_cases']}"
        ),
        f"- Scored probability observations: {pit['scored_probability_observations']}",
        f"- Scored continuous observations: {pit['scored_continuous_observations']}",
        f"- Reason: {pit['reason']}",
        "- Limitations:",
        *[f"  - {item}" for item in pit["limitations"]],
        "",
        "No production-count or adaptive-authority change is made by this study.",
        "Any proposed change must be returned to Management for sanity check and explicit approval.",
    ]
    md_path = args.output_dir / "REPORT.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("FSFFL_ITEM8_RESULT_JSON_BEGIN")
    print(json.dumps(report, sort_keys=True))
    print("FSFFL_ITEM8_RESULT_JSON_END")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
