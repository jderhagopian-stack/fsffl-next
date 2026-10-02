from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from fsffl.team_utility.competitive_state import (
    classify_calculated_competitive_state,
    derive_league_relative_competitive_state_policy,
)
from fsffl.team_utility.simulation import (
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    WeeklyTeamScoringDistribution,
    _settings_derived_playoff_rules,
    compare_counterfactual_simulation_results,
    simulate_regular_season,
)
from fsffl.trade_decision.materiality import classify_positive_delta
from fsffl.trade_decision.policy_catalog import live_bounded_materiality_policy


CANDIDATE_COUNT = 35_000
PRODUCTION_COUNT = 50_000
REFERENCE_COUNT = 100_000
COUNTS = (CANDIDATE_COUNT, PRODUCTION_COUNT, REFERENCE_COUNT)
ROOT_SEEDS = tuple(range(20261301, 20261313))
RNG_BATCH_SIZE = 500
TEAM_COUNT = 12
REGULAR_SEASON_WEEKS = 14
STUDY_AS_OF = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
STUDY_MODEL_VERSION = (
    "simulation-35k-stress-v1:production-pcg64:same-root-100k-reference"
)
FOCAL_TEAM = "t05"
OTHER_TEAM = "t06"
PICK_BOUNDARY_TEAM = "t04"
TAIL_TEAM = "t08"


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    tags: tuple[str, ...]
    playoff_teams: int
    base_means: tuple[float, ...]
    base_stddevs: tuple[float, ...]
    future_pick: bool = False
    scenario_near_shift: float | None = None
    scenario_material_shift: float | None = None

    def identity_payload(self) -> dict[str, Any]:
        rules = _settings_derived_playoff_rules(self.playoff_teams, 15)
        if rules is None:
            raise ValueError("stress fixture requires supported governed playoff rules")
        return {
            "fixture_id": self.fixture_id,
            "tags": list(self.tags),
            "team_count": TEAM_COUNT,
            "regular_season_weeks": REGULAR_SEASON_WEEKS,
            "playoff_teams": self.playoff_teams,
            "playoff_start_week": 15,
            "playoff_round_weeks": list(rules.round_weeks),
            "bye_seeds": list(rules.bye_seeds),
            "base_means": list(self.base_means),
            "base_stddevs": list(self.base_stddevs),
            "future_pick": self.future_pick,
            "scenario_near_shift": self.scenario_near_shift,
            "scenario_material_shift": self.scenario_material_shift,
            "draft_order_authority": (
                "governed_standard_fallback" if self.future_pick else None
            ),
        }

    @property
    def fixture_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.identity_payload(),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


def fixtures() -> tuple[Fixture, ...]:
    # One fixture may satisfy more than one directive stress category. This keeps
    # the campaign bounded while preserving deliberately difficult boundaries.
    parity_means = tuple(112.0 + (index - 5.5) * 0.18 for index in range(TEAM_COUNT))
    parity_stddevs = tuple(20.0 + (index % 3) * 1.0 for index in range(TEAM_COUNT))

    tail_means = (
        122.0,
        120.0,
        118.0,
        116.0,
        114.0,
        112.0,
        110.0,
        108.0,
        106.0,
        104.0,
        102.0,
        100.0,
    )
    tail_stddevs = tuple(18.0 + (index % 4) * 1.5 for index in range(TEAM_COUNT))

    # t04 sits close to the 4/5 exact-slot and early/mid tier boundary while the
    # rest of the league remains plausible rather than artificially deterministic.
    pick_means = (
        102.5,
        103.5,
        104.5,
        105.5,
        106.5,
        107.5,
        111.0,
        113.0,
        115.0,
        117.0,
        119.0,
        121.0,
    )
    pick_stddevs = tuple(18.5 + (index % 3) * 1.25 for index in range(TEAM_COUNT))

    scenario_means = tuple(108.0 + index * 0.72 for index in range(TEAM_COUNT))
    scenario_stddevs = tuple(18.0 + (index % 4) * 1.25 for index in range(TEAM_COUNT))

    return (
        Fixture(
            fixture_id="parity_bubble_no_bye",
            tags=("razor_thin_playoff_bubble", "high_parity_league", "postseason_no_bye"),
            playoff_teams=4,
            base_means=parity_means,
            base_stddevs=parity_stddevs,
        ),
        Fixture(
            fixture_id="tail_championship_with_byes",
            tags=("tail_championship_case", "postseason_with_byes"),
            playoff_teams=6,
            base_means=tail_means,
            base_stddevs=tail_stddevs,
        ),
        Fixture(
            fixture_id="future_pick_boundary",
            tags=("future_pick_boundary_case",),
            playoff_teams=6,
            base_means=pick_means,
            base_stddevs=pick_stddevs,
            future_pick=True,
        ),
        Fixture(
            fixture_id="scenario_delta_boundaries",
            tags=("near_zero_scenario_delta", "material_scenario_delta"),
            playoff_teams=6,
            base_means=scenario_means,
            base_stddevs=scenario_stddevs,
            scenario_near_shift=0.20,
            scenario_material_shift=4.0,
        ),
    )


def _round_robin_schedule() -> tuple[ScheduledMatchup, ...]:
    teams = [f"t{index:02d}" for index in range(TEAM_COUNT)]
    rotation = teams[:]
    rows: list[ScheduledMatchup] = []
    for week in range(1, REGULAR_SEASON_WEEKS + 1):
        for index in range(TEAM_COUNT // 2):
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
    fixture: Fixture,
    schedule: tuple[ScheduledMatchup, ...],
    *,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> tuple[WeeklyTeamScoringDistribution, ...]:
    rows: list[WeeklyTeamScoringDistribution] = []
    for matchup in schedule:
        for team_id in (matchup.home_team_id, matchup.away_team_id):
            index = int(team_id[1:])
            shift = (
                focal_shift
                if team_id == FOCAL_TEAM
                else other_shift
                if team_id == OTHER_TEAM
                else 0.0
            )
            rows.append(
                WeeklyTeamScoringDistribution(
                    week=matchup.week,
                    team_id=team_id,
                    mean_points=(
                        fixture.base_means[index]
                        + (matchup.week % 3 - 1) * 0.35
                        + shift
                    ),
                    stddev_points=fixture.base_stddevs[index],
                    model_version=f"{fixture.fixture_id}:regular-v1",
                )
            )
    return tuple(rows)


def _playoff_rows(
    fixture: Fixture,
    *,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> tuple[WeeklyTeamScoringDistribution, ...]:
    rules = _settings_derived_playoff_rules(fixture.playoff_teams, 15)
    if rules is None:
        raise ValueError("stress fixture requires supported governed playoff rules")
    rows: list[WeeklyTeamScoringDistribution] = []
    for week in rules.round_weeks:
        for index in range(TEAM_COUNT):
            team_id = f"t{index:02d}"
            shift = (
                focal_shift
                if team_id == FOCAL_TEAM
                else other_shift
                if team_id == OTHER_TEAM
                else 0.0
            )
            rows.append(
                WeeklyTeamScoringDistribution(
                    week=week,
                    team_id=team_id,
                    mean_points=(
                        fixture.base_means[index]
                        + (week % 3 - 1) * 0.30
                        + shift
                    ),
                    stddev_points=fixture.base_stddevs[index],
                    model_version=f"{fixture.fixture_id}:playoff-v1",
                )
            )
    return tuple(rows)


def _request(
    fixture: Fixture,
    *,
    count: int,
    seed: int,
    focal_shift: float = 0.0,
    other_shift: float = 0.0,
) -> RegularSeasonSimulationInput:
    schedule = _round_robin_schedule()
    rules = _settings_derived_playoff_rules(fixture.playoff_teams, 15)
    if rules is None:
        raise ValueError("stress fixture requires supported governed playoff rules")
    return RegularSeasonSimulationInput(
        weekly_scoring=_weekly_rows(
            fixture,
            schedule,
            focal_shift=focal_shift,
            other_shift=other_shift,
        ),
        playoff_weekly_scoring=_playoff_rows(
            fixture,
            focal_shift=focal_shift,
            other_shift=other_shift,
        ),
        schedule=schedule,
        playoff_team_count=fixture.playoff_teams,
        playoff_rules=rules,
        future_pick_draft_season=(2027 if fixture.future_pick else None),
        simulation_count=count,
        seed=seed,
        model_version=STUDY_MODEL_VERSION,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=RNG_BATCH_SIZE,
    )


def _outcomes(result) -> dict[str, Any]:
    return {row.team_id: row for row in result.outcomes}


def _finishes(result) -> dict[str, Any]:
    return {row.team_id: row for row in result.finish_distributions}


def _picks(result) -> dict[str, Any]:
    return {row.original_team_id: row for row in result.future_pick_distributions}


def _pick_vector(row) -> tuple[float, ...]:
    by_slot = {item.slot_in_round: item.probability for item in row.slot_probabilities}
    return tuple(by_slot.get(slot, 0.0) for slot in range(1, TEAM_COUNT + 1))


def _tv(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right, strict=True))


def _js_round_percent(value: float | None) -> int | None:
    if value is None:
        return None
    return int(math.floor(value * 100.0 + 0.5))


def _sign(value: float | None, *, eps: float = 1e-12) -> int | None:
    if value is None:
        return None
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _ranking_signature(result) -> tuple[str, ...]:
    rows = result.outcomes
    return tuple(
        row.team_id
        for row in sorted(
            rows,
            key=lambda row: (
                -(row.playoff_probability or 0.0),
                -row.expected_wins,
                row.team_id,
            ),
        )
    )


def _rounded_probability_signature(result) -> tuple[tuple[str, int | None, int | None], ...]:
    return tuple(
        (
            row.team_id,
            _js_round_percent(row.playoff_probability),
            _js_round_percent(row.championship_probability),
        )
        for row in sorted(result.outcomes, key=lambda item: item.team_id)
    )


def _rounded_probability_differences(
    observed: list[list[Any]] | tuple[tuple[Any, ...], ...],
    reference: list[list[Any]] | tuple[tuple[Any, ...], ...],
) -> list[dict[str, Any]]:
    observed_by_team = {
        str(team_id): {
            "playoff_probability": playoff,
            "championship_probability": championship,
        }
        for team_id, playoff, championship in observed
    }
    reference_by_team = {
        str(team_id): {
            "playoff_probability": playoff,
            "championship_probability": championship,
        }
        for team_id, playoff, championship in reference
    }
    differences: list[dict[str, Any]] = []
    for team_id in sorted(reference_by_team):
        for metric in ("playoff_probability", "championship_probability"):
            actual = observed_by_team[team_id][metric]
            expected = reference_by_team[team_id][metric]
            if actual != expected:
                differences.append(
                    {
                        "team_id": team_id,
                        "metric": metric,
                        "observed_percent": actual,
                        "reference_percent": expected,
                    }
                )
    return differences


def _competitive_state_signature(result) -> tuple[tuple[str, str], ...]:
    policy = derive_league_relative_competitive_state_policy(
        result.outcomes,
        as_of=STUDY_AS_OF,
    )
    return tuple(
        (
            row.team_id,
            classify_calculated_competitive_state(
                row,
                policy,
                as_of=STUDY_AS_OF,
            ).value,
        )
        for row in sorted(result.outcomes, key=lambda item: item.team_id)
    )


def _pick_summary_signature(result, *, team_id: str) -> dict[str, Any] | None:
    row = _picks(result).get(team_id)
    if row is None:
        return None
    tier_rows = {
        "early": row.early_probability,
        "mid": row.mid_probability,
        "late": row.late_probability,
    }
    dominant = sorted(tier_rows, key=lambda key: (-tier_rows[key], key))[0]
    return {
        "expected_slot_one_decimal": round(row.expected_slot, 1),
        "median_slot": row.median_slot,
        "rounded_tiers_pct": {
            key: _js_round_percent(value) for key, value in tier_rows.items()
        },
        "dominant_tier": dominant,
    }


def _materiality_signature(baseline, scenario) -> dict[str, Any]:
    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id=FOCAL_TEAM,
        model_version="simulation-35k-stress-counterfactual-v1",
    )
    policy = live_bounded_materiality_policy(as_of=STUDY_AS_OF).competitive
    title_threshold = policy.championship_probability_abs
    return {
        "delta": {
            "expected_wins": delta.expected_wins,
            "playoff_probability": delta.playoff_probability,
            "championship_probability": delta.championship_probability,
        },
        "signs": {
            "expected_wins": _sign(delta.expected_wins),
            "playoff_probability": _sign(delta.playoff_probability),
            "championship_probability": _sign(delta.championship_probability),
        },
        "materiality": {
            "expected_wins": classify_positive_delta(
                delta.expected_wins,
                absolute_threshold=policy.expected_wins_abs,
            ).value,
            "playoff_probability": classify_positive_delta(
                delta.playoff_probability,
                absolute_threshold=policy.playoff_probability_abs,
            ).value,
            "championship_probability": (
                "unavailable"
                if title_threshold is None
                else classify_positive_delta(
                    delta.championship_probability,
                    absolute_threshold=title_threshold,
                ).value
            ),
        },
        "common_world": {
            "regular_season": delta.regular_season_common_worlds,
            "postseason": delta.postseason_common_worlds,
        },
        "policy": {
            "model_version": policy.model_version,
            "expected_wins_abs": policy.expected_wins_abs,
            "playoff_probability_abs": policy.playoff_probability_abs,
            "championship_probability_abs": policy.championship_probability_abs,
        },
        "disposition_check": (
            "not_applicable_simulation_only_fixture_no_fabricated_economics_or_negotiation"
        ),
    }


def _run_fixture(
    fixture: Fixture,
    *,
    count: int,
    seed: int,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    baseline = simulate_regular_season(
        _request(fixture, count=count, seed=seed)
    )
    scenarios: dict[str, Any] = {}
    if fixture.scenario_near_shift is not None:
        shift = fixture.scenario_near_shift
        scenarios["near"] = simulate_regular_season(
            _request(
                fixture,
                count=count,
                seed=seed,
                focal_shift=shift,
                other_shift=-shift,
            )
        )
    if fixture.scenario_material_shift is not None:
        shift = fixture.scenario_material_shift
        scenarios["material"] = simulate_regular_season(
            _request(
                fixture,
                count=count,
                seed=seed,
                focal_shift=shift,
                other_shift=-shift,
            )
        )

    outcomes = _outcomes(baseline)
    finishes = _finishes(baseline)
    data: dict[str, Any] = {
        "fixture_id": fixture.fixture_id,
        "fixture_hash": fixture.fixture_hash,
        "count": count,
        "seed": seed,
        "baseline": {
            "outcomes": {
                team_id: {
                    "expected_wins": row.expected_wins,
                    "playoff_probability": row.playoff_probability,
                    "championship_probability": row.championship_probability,
                    "first_place_probability": row.first_place_probability,
                }
                for team_id, row in outcomes.items()
            },
            "finish_vectors": {
                team_id: list(row.rank_probabilities)
                for team_id, row in finishes.items()
            },
            "ranking_signature": list(_ranking_signature(baseline)),
            "rounded_probability_signature": [
                list(item) for item in _rounded_probability_signature(baseline)
            ],
            "competitive_state_signature": [
                list(item) for item in _competitive_state_signature(baseline)
            ],
        },
    }
    if fixture.fixture_id == "tail_championship_with_byes":
        data["baseline"]["tail_team"] = {
            "team_id": TAIL_TEAM,
            "championship_probability": outcomes[TAIL_TEAM].championship_probability,
            "rounded_championship_pct": _js_round_percent(
                outcomes[TAIL_TEAM].championship_probability
            ),
        }
    if fixture.future_pick:
        picks = _picks(baseline)
        data["baseline"]["pick_vectors"] = {
            team_id: list(_pick_vector(row)) for team_id, row in picks.items()
        }
        data["baseline"]["pick_boundary_summary"] = _pick_summary_signature(
            baseline,
            team_id=PICK_BOUNDARY_TEAM,
        )
    if "near" in scenarios:
        data["near_scenario"] = _materiality_signature(
            baseline,
            scenarios["near"],
        )
    if "material" in scenarios:
        data["material_scenario"] = _materiality_signature(
            baseline,
            scenarios["material"],
        )

    return data, time.perf_counter() - started


def _compare_to_reference(
    row: dict[str, Any],
    reference: dict[str, Any],
) -> dict[str, Any]:
    outcomes = row["baseline"]["outcomes"]
    ref_outcomes = reference["baseline"]["outcomes"]
    finishes = row["baseline"]["finish_vectors"]
    ref_finishes = reference["baseline"]["finish_vectors"]

    comparison: dict[str, Any] = {
        "expected_wins_max_abs_error_vs_100k": max(
            abs(outcomes[team]["expected_wins"] - ref_outcomes[team]["expected_wins"])
            for team in outcomes
        ),
        "playoff_probability_max_abs_error_vs_100k": max(
            abs(
                (outcomes[team]["playoff_probability"] or 0.0)
                - (ref_outcomes[team]["playoff_probability"] or 0.0)
            )
            for team in outcomes
        ),
        "championship_probability_max_abs_error_vs_100k": max(
            abs(
                (outcomes[team]["championship_probability"] or 0.0)
                - (ref_outcomes[team]["championship_probability"] or 0.0)
            )
            for team in outcomes
        ),
        "finish_rank_max_tv_vs_100k": max(
            _tv(tuple(finishes[team]), tuple(ref_finishes[team]))
            for team in finishes
        ),
        "ranking_matches_100k": (
            row["baseline"]["ranking_signature"]
            == reference["baseline"]["ranking_signature"]
        ),
        "rounded_probabilities_matches_100k": (
            row["baseline"]["rounded_probability_signature"]
            == reference["baseline"]["rounded_probability_signature"]
        ),
        "rounded_probability_differences_vs_100k": _rounded_probability_differences(
            row["baseline"]["rounded_probability_signature"],
            reference["baseline"]["rounded_probability_signature"],
        ),
        "competitive_states_match_100k": (
            row["baseline"]["competitive_state_signature"]
            == reference["baseline"]["competitive_state_signature"]
        ),
    }

    if "tail_team" in row["baseline"]:
        comparison["tail_championship_abs_error_vs_100k"] = abs(
            (row["baseline"]["tail_team"]["championship_probability"] or 0.0)
            - (reference["baseline"]["tail_team"]["championship_probability"] or 0.0)
        )
        comparison["tail_rounded_championship_matches_100k"] = (
            row["baseline"]["tail_team"]["rounded_championship_pct"]
            == reference["baseline"]["tail_team"]["rounded_championship_pct"]
        )

    if "pick_vectors" in row["baseline"]:
        comparison["future_pick_slot_max_tv_vs_100k"] = max(
            _tv(
                tuple(row["baseline"]["pick_vectors"][team]),
                tuple(reference["baseline"]["pick_vectors"][team]),
            )
            for team in row["baseline"]["pick_vectors"]
        )
        comparison["pick_boundary_summary_matches_100k"] = (
            row["baseline"]["pick_boundary_summary"]
            == reference["baseline"]["pick_boundary_summary"]
        )

    for scenario_key in ("near_scenario", "material_scenario"):
        if scenario_key not in row:
            continue
        label = scenario_key.removesuffix("_scenario")
        values = row[scenario_key]
        refs = reference[scenario_key]
        for metric in (
            "expected_wins",
            "playoff_probability",
            "championship_probability",
        ):
            value = values["delta"][metric]
            ref_value = refs["delta"][metric]
            comparison[f"{label}_{metric}_delta_abs_error_vs_100k"] = (
                None
                if value is None or ref_value is None
                else abs(value - ref_value)
            )
            comparison[f"{label}_{metric}_delta_sign_matches_100k"] = (
                values["signs"][metric] == refs["signs"][metric]
            )
        comparison[f"{label}_materiality_matches_100k"] = (
            values["materiality"] == refs["materiality"]
        )
        comparison[f"{label}_common_world_contract"] = values["common_world"]

    product_checks = {
        key: value
        for key, value in comparison.items()
        if (
            key.endswith("_matches_100k")
            or key.endswith("_sign_matches_100k")
            or key.endswith("_materiality_matches_100k")
        )
        and isinstance(value, bool)
    }
    comparison["product_equivalent_to_100k"] = all(product_checks.values())
    comparison["product_check_results"] = product_checks
    return comparison


def _absolute_root_metrics(row: dict[str, Any]) -> dict[str, float]:
    baseline = row["baseline"]
    outcomes = baseline["outcomes"]
    focal = outcomes[FOCAL_TEAM]
    result = {
        "focal_expected_wins": float(focal["expected_wins"]),
        "focal_playoff_probability": float(focal["playoff_probability"] or 0.0),
        "focal_championship_probability": float(
            focal["championship_probability"] or 0.0
        ),
    }
    if "tail_team" in baseline:
        result["tail_championship_probability"] = float(
            baseline["tail_team"]["championship_probability"] or 0.0
        )
    if "pick_boundary_summary" in baseline:
        picks = baseline["pick_vectors"][PICK_BOUNDARY_TEAM]
        result["pick_boundary_expected_slot"] = sum(
            (index + 1) * probability for index, probability in enumerate(picks)
        )
    for label in ("near", "material"):
        key = f"{label}_scenario"
        if key not in row:
            continue
        for metric, value in row[key]["delta"].items():
            if value is not None:
                result[f"{label}_{metric}_delta"] = float(value)
    return result


def run_seed(seed: int) -> dict[str, Any]:
    fixture_rows: dict[str, dict[int, dict[str, Any]]] = {}
    runtime_by_count = {count: 0.0 for count in COUNTS}
    for fixture in fixtures():
        by_count: dict[int, dict[str, Any]] = {}
        for count in COUNTS:
            row, elapsed = _run_fixture(fixture, count=count, seed=seed)
            by_count[count] = row
            runtime_by_count[count] += elapsed
        fixture_rows[fixture.fixture_id] = by_count

    raw_rows: list[dict[str, Any]] = []
    absolute_rows: list[dict[str, Any]] = []
    for fixture in fixtures():
        by_count = fixture_rows[fixture.fixture_id]
        reference = by_count[REFERENCE_COUNT]
        for count in COUNTS:
            row = by_count[count]
            raw_rows.append(
                {
                    "seed": seed,
                    "fixture_id": fixture.fixture_id,
                    "fixture_hash": fixture.fixture_hash,
                    "count": count,
                    "comparison": _compare_to_reference(row, reference),
                    "runtime_seconds": (
                        None if count == REFERENCE_COUNT else None
                    ),
                }
            )
            absolute_rows.append(
                {
                    "seed": seed,
                    "fixture_id": fixture.fixture_id,
                    "count": count,
                    **_absolute_root_metrics(row),
                }
            )

    return {
        "seed": seed,
        "raw_rows": raw_rows,
        "absolute_rows": absolute_rows,
        "runtime_by_count_seconds": {
            str(count): runtime_by_count[count] for count in COUNTS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-count", type=int, default=len(ROOT_SEEDS))
    args = parser.parse_args()

    if args.seed_start < 0 or args.seed_count < 1:
        raise SystemExit("seed-start must be nonnegative and seed-count positive")
    seeds = ROOT_SEEDS[args.seed_start : args.seed_start + args.seed_count]
    if not seeds:
        raise SystemExit("requested seed slice is empty")

    started = time.perf_counter()
    results = []
    for seed in seeds:
        seed_started = time.perf_counter()
        result = run_seed(seed)
        result["seed_elapsed_seconds"] = time.perf_counter() - seed_started
        results.append(result)
        print(
            json.dumps(
                {
                    "event": "seed_complete",
                    "seed": seed,
                    "elapsed_seconds": round(result["seed_elapsed_seconds"], 3),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    report = {
        "study_id": "simulation-35k-stress-20261002-v1",
        "authority_status": "research_only_no_production_change",
        "production_count": PRODUCTION_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "reference_count": REFERENCE_COUNT,
        "rng_protocol": NUMPY_PCG64_BATCHED_GAUSS_V1,
        "rng_batch_size": RNG_BATCH_SIZE,
        "root_seeds": list(seeds),
        "seed_start": args.seed_start,
        "counts": list(COUNTS),
        "fixtures": [
            {
                **fixture.identity_payload(),
                "fixture_hash": fixture.fixture_hash,
            }
            for fixture in fixtures()
        ],
        "seed_results": results,
        "slice_elapsed_seconds": time.perf_counter() - started,
        "guardrails": {
            "production_authority_changed": False,
            "adaptive_count_rule_changed": False,
            "production_runtime_code_touched": False,
            "origin_aware_pick_value_status": "held_pending_management_gate",
            "reference_100k_role": "same_root_research_reference_only",
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "RESULTS.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("FSFFL_SIM35K_PART_JSON_BEGIN")
    print(json.dumps(report, sort_keys=True))
    print("FSFFL_SIM35K_PART_JSON_END")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
