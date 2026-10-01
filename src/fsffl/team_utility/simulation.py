from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from math import sqrt
import logging
import os
import platform
from random import Random
from time import perf_counter, process_time
from typing import Annotated, Callable, Literal

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeaguePlayoffRules, LeagueState

_logger = logging.getLogger("uvicorn.error")


def _profile_clock() -> tuple[float, float]:
    return perf_counter(), process_time()


def _profile_wall_clock() -> float:
    return perf_counter()

PYTHON_RANDOM_GAUSS_V1 = "python-random-gauss-v1"
NUMPY_PCG64_BATCHED_GAUSS_V1 = "numpy-pcg64-batched-gauss-v1"
SIMULATION_RNG_PROTOCOLS = (PYTHON_RANDOM_GAUSS_V1, NUMPY_PCG64_BATCHED_GAUSS_V1)
NUMPY_BATCH_SIZE_DEFAULT = 500


class ScoringDistributionKind(StrEnum):
    NORMAL = "normal"


class TeamScoringDistribution(FrozenModel):
    """Point-in-time team scoring evidence consumed by Simulation authority."""

    team_id: str
    mean_points: float
    stddev_points: Annotated[float, Field(ge=0)]
    distribution_kind: ScoringDistributionKind = ScoringDistributionKind.NORMAL
    model_version: str

    @model_validator(mode="after")
    def validate_identifiers(self) -> "TeamScoringDistribution":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("team scoring identifiers cannot be blank")
        return self


class WeeklyTeamScoringDistribution(FrozenModel):
    """Week-specific team scoring evidence after canonical availability/lineup resolution."""

    week: Annotated[int, Field(ge=1)]
    team_id: str
    mean_points: float
    stddev_points: Annotated[float, Field(ge=0)]
    distribution_kind: ScoringDistributionKind = ScoringDistributionKind.NORMAL
    model_version: str

    @model_validator(mode="after")
    def validate_identifiers(self) -> "WeeklyTeamScoringDistribution":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("weekly team scoring identifiers cannot be blank")
        return self


class ScheduledMatchup(FrozenModel):
    week: Annotated[int, Field(ge=1)]
    home_team_id: str
    away_team_id: str

    @model_validator(mode="after")
    def validate_matchup(self) -> "ScheduledMatchup":
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            raise ValueError("matchup team ids cannot be blank")
        if self.home_team_id == self.away_team_id:
            raise ValueError("a team cannot play itself")
        return self


class CompletedMatchup(FrozenModel):
    """Immutable factual regular-season result already completed in canonical State."""

    week: Annotated[int, Field(ge=1)]
    home_team_id: str
    away_team_id: str
    home_points: float
    away_points: float

    @model_validator(mode="after")
    def validate_matchup(self) -> "CompletedMatchup":
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            raise ValueError("completed matchup team ids cannot be blank")
        if self.home_team_id == self.away_team_id:
            raise ValueError("a team cannot play itself")
        return self


class RegularSeasonSimulationInput(FrozenModel):
    scoring: tuple[TeamScoringDistribution, ...] = ()
    weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = ()
    playoff_weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = ()
    completed_matchups: tuple[CompletedMatchup, ...] = ()
    schedule: tuple[ScheduledMatchup, ...]
    playoff_team_count: Annotated[int, Field(ge=1)] | None = None
    playoff_rules: LeaguePlayoffRules | None = None
    simulation_count: Annotated[int, Field(ge=1)] = 50_000
    seed: int = 20260905
    model_version: str
    rng_protocol: Literal[
        "python-random-gauss-v1", "numpy-pcg64-batched-gauss-v1"
    ] = PYTHON_RANDOM_GAUSS_V1
    rng_batch_size: Annotated[int, Field(ge=1, le=50_000)] | None = None

    @model_validator(mode="after")
    def validate_input(self) -> "RegularSeasonSimulationInput":
        if not self.model_version.strip():
            raise ValueError("simulation model_version cannot be blank")
        if self.rng_protocol == PYTHON_RANDOM_GAUSS_V1 and self.rng_batch_size is not None:
            raise ValueError("Python RNG protocol does not accept a batch size")
        ids = [item.team_id for item in self.scoring]
        if len(ids) != len(set(ids)):
            raise ValueError("team scoring distributions must have unique team ids")
        weekly_keys = [(item.week, item.team_id) for item in self.weekly_scoring]
        if len(weekly_keys) != len(set(weekly_keys)):
            raise ValueError("weekly team scoring distributions must have unique week/team keys")
        playoff_weekly_keys = [
            (item.week, item.team_id) for item in self.playoff_weekly_scoring
        ]
        if len(playoff_weekly_keys) != len(set(playoff_weekly_keys)):
            raise ValueError(
                "playoff weekly team scoring distributions must have unique week/team keys"
            )
        known = (
            set(ids)
            | {item.team_id for item in self.weekly_scoring}
            | {item.team_id for item in self.playoff_weekly_scoring}
            | {
                team_id
                for matchup in self.completed_matchups
                for team_id in (matchup.home_team_id, matchup.away_team_id)
            }
        )
        if not known:
            raise ValueError("simulation requires at least one team")
        if self.playoff_team_count is not None and self.playoff_team_count > len(known):
            raise ValueError("playoff_team_count cannot exceed team count")
        if (
            self.playoff_rules is not None
            and self.playoff_team_count is not None
            and self.playoff_rules.playoff_team_count != self.playoff_team_count
        ):
            raise ValueError("playoff_rules team count must match playoff_team_count")
        for matchup in self.completed_matchups:
            if matchup.home_team_id not in known or matchup.away_team_id not in known:
                raise ValueError("completed matchup references unknown team")
        for matchup in self.schedule:
            if matchup.home_team_id not in known or matchup.away_team_id not in known:
                raise ValueError("schedule references unknown team")
        seen_week_team: set[tuple[int, str]] = set()
        required_weekly: set[tuple[int, str]] = set()
        for matchup in self.completed_matchups:
            for team_id in (matchup.home_team_id, matchup.away_team_id):
                key = (matchup.week, team_id)
                if key in seen_week_team:
                    raise ValueError("a team may appear only once per regular-season week")
                seen_week_team.add(key)
        for matchup in self.schedule:
            for team_id in (matchup.home_team_id, matchup.away_team_id):
                key = (matchup.week, team_id)
                if key in seen_week_team:
                    raise ValueError("a team may appear only once per scheduled week")
                seen_week_team.add(key)
                required_weekly.add(key)
        if self.weekly_scoring and set(weekly_keys) != required_weekly:
            missing = sorted(required_weekly - set(weekly_keys))
            extra = sorted(set(weekly_keys) - required_weekly)
            raise ValueError(f"weekly scoring must exactly cover schedule; missing={missing} extra={extra}")
        if self.playoff_weekly_scoring:
            if self.playoff_rules is None:
                raise ValueError("playoff weekly scoring requires configured playoff rules")
            required_playoff_weekly = {
                (week, team_id)
                for week in self.playoff_rules.round_weeks
                for team_id in known
            }
            if set(playoff_weekly_keys) != required_playoff_weekly:
                missing = sorted(required_playoff_weekly - set(playoff_weekly_keys))
                extra = sorted(set(playoff_weekly_keys) - required_playoff_weekly)
                raise ValueError(
                    "playoff weekly scoring must exactly cover configured playoff weeks; "
                    f"missing={missing} extra={extra}"
                )
        if (
            self.playoff_rules is not None
            and self.playoff_rules.simulation_unavailability_reason() is None
            and not self.scoring
            and not self.playoff_weekly_scoring
        ):
            raise ValueError("configured championship simulation requires playoff scoring evidence")
        return self


class TeamCompetitiveOutcome(FrozenModel):
    team_id: str
    # Final projected regular-season wins = immutable actual wins + simulated remaining wins.
    expected_wins: float
    expected_remaining_wins: Annotated[float, Field(ge=0)] | None = None
    wins_stddev: Annotated[float, Field(ge=0)]
    playoff_probability: Annotated[float, Field(ge=0, le=1)] | None = None
    playoff_seed_probabilities: tuple[
        Annotated[float, Field(ge=0, le=1)], ...
    ] | None = None
    playoff_unavailability_reason: str | None = None
    bye_probability: Annotated[float, Field(ge=0, le=1)] | None = None
    bye_unavailability_reason: str | None = None
    first_place_probability: Annotated[float, Field(ge=0, le=1)]
    championship_probability: Annotated[float | None, Field(ge=0, le=1)] = None
    championship_unavailability_reason: str | None = None
    simulation_count: Annotated[int, Field(ge=1)]
    simulation_model_version: str


class TeamFinishDistribution(FrozenModel):
    """Regular-season finish distribution retained from the authoritative Simulation.

    Rank 1 is the best simulated regular-season finish. The distribution records
    what the existing season simulation already observed; it does not infer rookie
    draft order. Draft-order interpretation belongs to a downstream governed pick
    location mapping because league rules may treat playoff teams differently.
    """

    team_id: str
    expected_finish: Annotated[float, Field(ge=1)]
    median_finish: Annotated[int, Field(ge=1)] | None = None
    rank_probabilities: tuple[float, ...]
    simulation_count: Annotated[int, Field(ge=1)]
    simulation_model_version: str

    @model_validator(mode="after")
    def validate_distribution(self) -> "TeamFinishDistribution":
        if not self.team_id.strip() or not self.simulation_model_version.strip():
            raise ValueError("finish distribution identifiers cannot be blank")
        if not self.rank_probabilities:
            raise ValueError("finish distribution must include at least one rank")
        if any(value < 0.0 or value > 1.0 for value in self.rank_probabilities):
            raise ValueError("finish probabilities must be between zero and one")
        if abs(sum(self.rank_probabilities) - 1.0) > 1e-9:
            raise ValueError("finish probabilities must sum to one")
        if self.expected_finish > len(self.rank_probabilities):
            raise ValueError("expected finish cannot exceed team count")
        if self.median_finish is not None and self.median_finish > len(
            self.rank_probabilities
        ):
            raise ValueError("median finish cannot exceed team count")
        return self


class RegularSeasonSimulationResult(FrozenModel):
    outcomes: tuple[TeamCompetitiveOutcome, ...]
    finish_distributions: tuple[TeamFinishDistribution, ...] = ()
    # Persisted with the Simulation artifact; intentionally absent from per-team product views.
    championship_probability_provenance: Literal["provider_observed_exact", "settings_derived_standard"] | None = None
    simulation_count: Annotated[int, Field(ge=1)]
    seed: int
    model_version: str
    rng_protocol: Literal[
        "python-random-gauss-v1", "numpy-pcg64-batched-gauss-v1"
    ] = PYTHON_RANDOM_GAUSS_V1
    rng_runtime_version: str = "legacy-unrecorded"
    rng_bit_generator: str = "legacy-unrecorded"
    rng_batch_size: Annotated[int, Field(ge=1, le=50_000)] | None = None
    rng_draw_dtype: str = "legacy-unrecorded"
    rng_draw_layout: str = "legacy-unrecorded"
    rng_seed_derivation: str = "legacy-python-seed-v1"
    simulation_input_fingerprint: str = "legacy-unfingerprinted"
    # Topology-only coordinates used to prove when two alternate-State runs consume
    # the same ordered random-number stream. Means/standard deviations are omitted
    # intentionally so changed football strength can vary while the Monte Carlo
    # worlds remain paired.
    common_world_regular_season_coordinate: str = "legacy-unrecorded"
    common_world_postseason_coordinate: str | None = None
    common_world_postseason_unavailability_reason: str | None = "legacy-unrecorded"


class CounterfactualCompetitiveOutcomeDelta(FrozenModel):
    """Simulation-owned before/after competitive delta with pairing provenance."""

    team_id: str
    expected_wins: float
    expected_remaining_wins: float | None = None
    playoff_probability: float | None = None
    bye_probability: float | None = None
    first_place_probability: float
    championship_probability: float | None = None
    simulation_count: Annotated[int, Field(ge=1)]
    seed: int
    rng_protocol: str
    comparison_method: Literal["common_random_numbers", "aggregate_difference"]
    championship_comparison_method: Literal[
        "common_random_numbers", "aggregate_difference", "unavailable"
    ]
    regular_season_common_worlds: bool
    postseason_common_worlds: bool
    regular_season_unavailability_reason: str | None = None
    postseason_unavailability_reason: str | None = None
    common_world_metrics: tuple[str, ...] = ()
    baseline_simulation_input_fingerprint: str
    scenario_simulation_input_fingerprint: str
    model_version: str = "next4-counterfactual-competitive-delta-v1"

    @model_validator(mode="after")
    def validate_counterfactual_delta(self) -> "CounterfactualCompetitiveOutcomeDelta":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("counterfactual delta identifiers cannot be blank")
        if self.regular_season_common_worlds and self.regular_season_unavailability_reason is not None:
            raise ValueError("common regular-season worlds cannot carry an unavailability reason")
        if self.postseason_common_worlds and self.postseason_unavailability_reason is not None:
            raise ValueError("common postseason worlds cannot carry an unavailability reason")
        return self


def _optional_probability_delta(after: float | None, before: float | None) -> float | None:
    return None if after is None or before is None else after - before


def _common_world_replay_mismatch(
    baseline: RegularSeasonSimulationResult,
    scenario: RegularSeasonSimulationResult,
) -> str | None:
    if baseline.model_version != scenario.model_version:
        return "simulation_model_mismatch"
    if baseline.simulation_count != scenario.simulation_count:
        return "simulation_count_mismatch"
    if baseline.seed != scenario.seed:
        return "seed_mismatch"
    replay_fields = (
        "rng_protocol",
        "rng_runtime_version",
        "rng_bit_generator",
        "rng_batch_size",
        "rng_draw_dtype",
        "rng_draw_layout",
        "rng_seed_derivation",
    )
    if any(getattr(baseline, field) != getattr(scenario, field) for field in replay_fields):
        return "rng_replay_identity_mismatch"
    return None


def compare_counterfactual_simulation_results(
    baseline: RegularSeasonSimulationResult,
    scenario: RegularSeasonSimulationResult,
    *,
    team_id: str,
    model_version: str = "next4-counterfactual-competitive-delta-v1",
) -> CounterfactualCompetitiveOutcomeDelta:
    """Return competitive deltas and prove common-world coupling where valid.

    Aggregate subtraction is always mathematically valid when both authoritative
    outputs exist. It is labeled common-random-number comparison only when the two
    simulations share the exact replay identity and topology-only draw coordinate.
    """

    baseline_by_team = {item.team_id: item for item in baseline.outcomes}
    scenario_by_team = {item.team_id: item for item in scenario.outcomes}
    if team_id not in baseline_by_team or team_id not in scenario_by_team:
        raise ValueError("counterfactual comparison requires the team in both simulations")
    if not model_version.strip():
        raise ValueError("counterfactual comparison model_version cannot be blank")

    before = baseline_by_team[team_id]
    after = scenario_by_team[team_id]
    replay_reason = _common_world_replay_mismatch(baseline, scenario)
    regular_reason = replay_reason
    if regular_reason is None:
        if (
            baseline.common_world_regular_season_coordinate == "legacy-unrecorded"
            or scenario.common_world_regular_season_coordinate == "legacy-unrecorded"
        ):
            regular_reason = "common_world_coordinate_unavailable"
        elif (
            baseline.common_world_regular_season_coordinate
            != scenario.common_world_regular_season_coordinate
        ):
            regular_reason = "regular_season_draw_topology_mismatch"
    regular_common = regular_reason is None

    postseason_reason = replay_reason
    if postseason_reason is None and not regular_common:
        postseason_reason = "regular_season_common_worlds_unavailable"
    if postseason_reason is None:
        if baseline.common_world_postseason_coordinate is None:
            postseason_reason = (
                baseline.common_world_postseason_unavailability_reason
                or "baseline_postseason_common_world_coordinate_unavailable"
            )
        elif scenario.common_world_postseason_coordinate is None:
            postseason_reason = (
                scenario.common_world_postseason_unavailability_reason
                or "scenario_postseason_common_world_coordinate_unavailable"
            )
        elif (
            baseline.common_world_postseason_coordinate
            != scenario.common_world_postseason_coordinate
        ):
            postseason_reason = "postseason_draw_topology_mismatch"
    postseason_common = postseason_reason is None

    regular_metrics = [
        "expected_wins",
        "first_place_probability",
    ]
    if before.expected_remaining_wins is not None and after.expected_remaining_wins is not None:
        regular_metrics.append("expected_remaining_wins")
    if before.playoff_probability is not None and after.playoff_probability is not None:
        regular_metrics.append("playoff_probability")
    if before.bye_probability is not None and after.bye_probability is not None:
        regular_metrics.append("bye_probability")
    common_metrics = tuple(regular_metrics if regular_common else ())
    if (
        postseason_common
        and before.championship_probability is not None
        and after.championship_probability is not None
    ):
        common_metrics += ("championship_probability",)

    championship_delta = _optional_probability_delta(
        after.championship_probability,
        before.championship_probability,
    )
    championship_method: Literal[
        "common_random_numbers", "aggregate_difference", "unavailable"
    ]
    if championship_delta is None:
        championship_method = "unavailable"
    elif postseason_common:
        championship_method = "common_random_numbers"
    else:
        championship_method = "aggregate_difference"

    return CounterfactualCompetitiveOutcomeDelta(
        team_id=team_id,
        expected_wins=after.expected_wins - before.expected_wins,
        expected_remaining_wins=(
            None
            if after.expected_remaining_wins is None or before.expected_remaining_wins is None
            else after.expected_remaining_wins - before.expected_remaining_wins
        ),
        playoff_probability=_optional_probability_delta(
            after.playoff_probability,
            before.playoff_probability,
        ),
        bye_probability=_optional_probability_delta(
            after.bye_probability,
            before.bye_probability,
        ),
        first_place_probability=(
            after.first_place_probability - before.first_place_probability
        ),
        championship_probability=championship_delta,
        simulation_count=baseline.simulation_count,
        seed=baseline.seed,
        rng_protocol=baseline.rng_protocol,
        comparison_method=(
            "common_random_numbers" if regular_common else "aggregate_difference"
        ),
        championship_comparison_method=championship_method,
        regular_season_common_worlds=regular_common,
        postseason_common_worlds=postseason_common,
        regular_season_unavailability_reason=regular_reason,
        postseason_unavailability_reason=postseason_reason,
        common_world_metrics=common_metrics,
        baseline_simulation_input_fingerprint=baseline.simulation_input_fingerprint,
        scenario_simulation_input_fingerprint=scenario.simulation_input_fingerprint,
        model_version=model_version,
    )


def current_season_matchups_from_league_state(
    league_state: LeagueState,
) -> tuple[tuple[CompletedMatchup, ...], tuple[ScheduledMatchup, ...]]:
    """Split canonical schedule into immutable facts and unresolved future games.

    completed_through_week is the authority boundary. Numeric scores after that
    boundary can be live/in-progress and are never promoted to factual results here.
    When the boundary says a week is complete, both final scores must exist or
    Simulation fails closed rather than inventing or re-simulating a completed result.
    """

    if not league_state.matchups:
        raise ValueError("canonical league state has no regular-season schedule")
    boundary = league_state.completed_through_week
    completed: list[CompletedMatchup] = []
    remaining: list[ScheduledMatchup] = []
    for item in league_state.matchups:
        if boundary is not None and item.week <= boundary:
            if item.team_a_points is None or item.team_b_points is None:
                raise ValueError(
                    "completed regular-season matchup lacks factual points: "
                    f"week={item.week} teams={item.team_a_id},{item.team_b_id}"
                )
            completed.append(
                CompletedMatchup(
                    week=item.week,
                    home_team_id=item.team_a_id,
                    away_team_id=item.team_b_id,
                    home_points=item.team_a_points,
                    away_points=item.team_b_points,
                )
            )
        else:
            remaining.append(
                ScheduledMatchup(
                    week=item.week,
                    home_team_id=item.team_a_id,
                    away_team_id=item.team_b_id,
                )
            )
    return tuple(completed), tuple(remaining)


def scheduled_matchups_from_league_state(league_state: LeagueState) -> tuple[ScheduledMatchup, ...]:
    if not league_state.matchups:
        raise ValueError("canonical league state has no regular-season schedule")
    return tuple(
        ScheduledMatchup(week=item.week, home_team_id=item.team_a_id, away_team_id=item.team_b_id)
        for item in league_state.matchups
    )


def regular_season_game_counts(league_state: LeagueState) -> dict[str, int]:
    schedule = scheduled_matchups_from_league_state(league_state)
    counts = {team.team_id: 0 for team in league_state.teams}
    for matchup in schedule:
        counts[matchup.home_team_id] += 1
        counts[matchup.away_team_id] += 1
    if any(count < 1 for count in counts.values()):
        missing = sorted(team_id for team_id, count in counts.items() if count < 1)
        raise ValueError(f"regular-season schedule missing teams: {missing}")
    return counts


def resolved_playoff_rules_from_league_state(
    league_state: LeagueState,
) -> LeaguePlayoffRules | None:
    """Return exact or defensibly settings-derived canonical postseason rules."""

    league_rules = league_state.league.rules
    playoff_team_count = league_rules.playoff_team_count
    playoff_rules = league_rules.playoff_rules
    if (
        playoff_team_count is not None
        and playoff_team_count >= 2
        and playoff_rules is None
        and league_rules.playoff_start_week is not None
    ):
        playoff_rules = _settings_derived_playoff_rules(
            playoff_team_count, league_rules.playoff_start_week
        )
    return playoff_rules


def build_regular_season_simulation_input(
    league_state: LeagueState,
    *,
    scoring: tuple[TeamScoringDistribution, ...] = (),
    weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = (),
    playoff_weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = (),
    simulation_count: int = 50_000,
    seed: int = 20260905,
    model_version: str = "next4-live-season-plus-playoffs-v2",
    rng_protocol: Literal[
        "python-random-gauss-v1", "numpy-pcg64-batched-gauss-v1"
    ] = PYTHON_RANDOM_GAUSS_V1,
    rng_batch_size: int | None = None,
) -> RegularSeasonSimulationInput:
    league_rules = league_state.league.rules
    completed_matchups, remaining_schedule = current_season_matchups_from_league_state(
        league_state
    )
    playoff_team_count = league_rules.playoff_team_count
    playoff_rules = resolved_playoff_rules_from_league_state(league_state)
    return RegularSeasonSimulationInput(
        scoring=scoring,
        weekly_scoring=weekly_scoring,
        playoff_weekly_scoring=playoff_weekly_scoring,
        completed_matchups=completed_matchups,
        schedule=remaining_schedule,
        playoff_team_count=playoff_team_count,
        playoff_rules=playoff_rules,
        simulation_count=simulation_count,
        seed=seed,
        model_version=model_version,
        rng_protocol=rng_protocol,
        rng_batch_size=rng_batch_size,
    )


def _settings_derived_playoff_rules(
    playoff_team_count: int, playoff_start_week: int
) -> LeaguePlayoffRules | None:
    """Build the standard fixed seeded bracket from basic canonical settings.

    Sleeper exposes the playoff team count and start week for ordinary leagues.
    Those facts support the top-N qualification assumption and, for the standard
    2/4/6/8-team formats, a derived bracket. Other sizes retain qualification
    odds while the title structure remains unavailable absent exact evidence.
    """
    if playoff_team_count in (2,):
        round_count, bye_seeds = 1, ()
    elif playoff_team_count == 4:
        round_count, bye_seeds = 2, ()
    elif playoff_team_count == 6:
        round_count, bye_seeds = 3, (1, 2)
    elif playoff_team_count == 8:
        round_count, bye_seeds = 3, ()
    else:
        # Round count/byes are retained as an explicit unsupported standard
        # shape. Qualification is still derived from finish rank.
        round_count, bye_seeds = 1, ()
    round_weeks = tuple(range(playoff_start_week, playoff_start_week + round_count))
    if round_weeks[-1] > 22:
        return None
    return LeaguePlayoffRules(
        playoff_team_count=playoff_team_count,
        playoff_start_week=playoff_start_week,
        round_count=round_count,
        round_weeks=round_weeks,
        bye_count=len(bye_seeds),
        bye_seeds=bye_seeds,
        seeding_policy="overall_standings",
        standings_tiebreak_policy="wins_then_points_for_then_team_id_v1",
        reseeding_policy="fixed_bracket",
        bracket_authority="settings_derived_standard",
        bracket_derivation_policy="seeded_standard_fixed_v1",
        championship_round_number=round_count,
        championship_week=round_weeks[-1],
        championship_matchup_id="championship",
        playoff_scoring_policy="same_as_league_regular_season",
        matchup_tiebreak_policy="higher_original_seed",
    )


def _playoff_distributions(
    team_ids,
    scoring,
    playoff_weekly_scoring,
    playoff_rules,
):
    if playoff_rules is None:
        raise ValueError("playoff scoring requires configured playoff rules")
    if playoff_weekly_scoring:
        result = {}
        for week in playoff_rules.round_weeks:
            rows = []
            for team_id in team_ids:
                item = playoff_weekly_scoring.get((week, team_id))
                if item is None:
                    raise ValueError(
                        f"playoff scoring evidence unavailable for {team_id} week {week}"
                    )
                rows.append((item.mean_points, item.stddev_points))
            result[week] = tuple(rows)
        return result
    if scoring:
        static = tuple(
            (scoring[team_id].mean_points, scoring[team_id].stddev_points)
            for team_id in team_ids
        )
        return {week: static for week in playoff_rules.round_weeks}
    raise ValueError("configured championship simulation requires playoff scoring evidence")


def _playoff_game(left, right, playoff_scoring, week, gauss):
    left_idx, left_seed = left
    right_idx, right_seed = right
    week_scoring = playoff_scoring[week]
    left_mean, left_std = week_scoring[left_idx]
    right_mean, right_std = week_scoring[right_idx]
    left_points = left_mean if left_std == 0 else max(0.0, gauss(left_mean, left_std))
    right_points = right_mean if right_std == 0 else max(0.0, gauss(right_mean, right_std))
    if left_points > right_points:
        return left
    if right_points > left_points:
        return right
    return left if left_seed < right_seed else right


def _simulate_configured_champion(standings, playoff_rules, playoff_scoring, gauss):
    if playoff_rules is None or playoff_rules.simulation_unavailability_reason() is not None:
        return None
    seeds = {
        seed: (standings[seed - 1], seed)
        for seed in range(1, playoff_rules.playoff_team_count + 1)
    }
    winners = {}
    for matchup in playoff_rules.canonical_execution_matchups():
        left = (
            seeds[matchup.participant_a.seed_number]
            if matchup.participant_a.seed_number is not None
            else winners[matchup.participant_a.winner_of_matchup_id]
        )
        right = (
            seeds[matchup.participant_b.seed_number]
            if matchup.participant_b.seed_number is not None
            else winners[matchup.participant_b.winner_of_matchup_id]
        )
        winners[matchup.matchup_id] = _playoff_game(
            left, right, playoff_scoring, matchup.week, gauss
        )
    return winners[playoff_rules.championship_matchup_id][0]


def _numpy_regular_season_score_batches(request, compiled_schedule, batch_size):
    """Yield bounded trial-by-draw arrays under the experimental RNG protocol."""
    import numpy as np

    draw_means = np.empty(len(compiled_schedule) * 2, dtype=np.float64)
    draw_stddevs = np.empty(len(compiled_schedule) * 2, dtype=np.float64)
    for index, row in enumerate(compiled_schedule):
        draw_means[2 * index] = row[2]
        draw_stddevs[2 * index] = row[3]
        draw_means[2 * index + 1] = row[4]
        draw_stddevs[2 * index + 1] = row[5]
    deterministic_columns = np.flatnonzero(draw_stddevs == 0.0)
    stochastic_columns = np.flatnonzero(draw_stddevs != 0.0)
    if os.getenv("FSFFL_SIMULATION_PROFILE", "").strip().lower() in {"1", "true", "yes", "on"}:
        _logger.info(
            "FSFFL simulation profile arrays draw_parameters_shapes=(%s,)(%s,) "
            "score_shape=(%s,%s) dtype=float64 bytes_per_batch=%s "
            "deterministic_draws=%s stochastic_draws=%s",
            len(draw_means),
            len(draw_stddevs),
            batch_size,
            len(draw_means),
            batch_size * len(draw_means) * 8,
            int(deterministic_columns.size),
            int(stochastic_columns.size),
        )
    bit_generator = np.random.PCG64(request.seed)
    generator = np.random.Generator(bit_generator)

    remaining = request.simulation_count
    while remaining:
        count = min(batch_size, remaining)
        scores = np.empty((count, len(draw_means)), dtype=np.float64)
        if deterministic_columns.size:
            scores[:, deterministic_columns] = draw_means[deterministic_columns]
        if stochastic_columns.size:
            scores[:, stochastic_columns] = generator.normal(
                loc=draw_means[stochastic_columns],
                scale=draw_stddevs[stochastic_columns],
                size=(count, stochastic_columns.size),
            )
        # fmax retains Python max(0.0, value)'s floor behavior for NaN inputs.
        np.fmax(scores, 0.0, out=scores)
        yield scores
        remaining -= count


def _numpy_regular_season_matchup_batches(scores, compiled_schedule, team_count):
    """Accumulate one bounded batch in the same matchup-addition order."""
    import numpy as np

    wins = np.zeros((scores.shape[0], team_count), dtype=np.float64)
    points_for = np.zeros((scores.shape[0], team_count), dtype=np.float64)
    for matchup_index, (home_idx, away_idx, *_draw_parameters) in enumerate(
        compiled_schedule
    ):
        home = scores[:, 2 * matchup_index]
        away = scores[:, 2 * matchup_index + 1]
        points_for[:, home_idx] += home
        points_for[:, away_idx] += away
        home_wins = home > away
        away_wins = away > home
        ties = ~(home_wins | away_wins)
        wins[:, home_idx] += home_wins
        wins[:, away_idx] += away_wins
        wins[:, home_idx] += ties * 0.5
        wins[:, away_idx] += ties * 0.5
    return wins, points_for


def simulate_regular_season(
    request: RegularSeasonSimulationInput,
    *,
    cooperative_yield: Callable[[], object] | None = None,
    trial_observer: Callable[
        [tuple[float, ...], tuple[float, ...], tuple[int, ...], int | None], object
    ]
    | None = None,
) -> RegularSeasonSimulationResult:
    """Simulate canonical regular season and, when supported, a standard seeded title bracket.

    A separate deterministic postseason RNG preserves the established regular-season
    RNG stream exactly. Unsupported/custom playoff sizes keep championship probability
    explicitly unavailable rather than blocking regular-season simulation or fabricating
    bracket semantics. Every simulated final regular-season rank is retained as a
    distribution for downstream analytics and probabilistic pick-location evidence.
    """

    profile_enabled = os.getenv("FSFFL_SIMULATION_PROFILE", "").strip().lower() in {"1", "true", "yes", "on"}
    compile_started = _profile_clock() if profile_enabled else None
    by_team = {item.team_id: item for item in request.scoring}
    by_week_team = {(item.week, item.team_id): item for item in request.weekly_scoring}
    by_playoff_week_team = {
        (item.week, item.team_id): item for item in request.playoff_weekly_scoring
    }
    team_ids = tuple(
        sorted(
            set(by_team)
            | {item.team_id for item in request.weekly_scoring}
            | {item.team_id for item in request.playoff_weekly_scoring}
            | {
                team_id
                for matchup in request.completed_matchups
                for team_id in (matchup.home_team_id, matchup.away_team_id)
            }
        )
    )
    team_index = {team_id: index for index, team_id in enumerate(team_ids)}
    team_count = len(team_ids)
    actual_wins = [0.0] * team_count
    actual_points_for = [0.0] * team_count
    for matchup in request.completed_matchups:
        home_idx = team_index[matchup.home_team_id]
        away_idx = team_index[matchup.away_team_id]
        home_points = matchup.home_points
        away_points = matchup.away_points
        actual_points_for[home_idx] += home_points
        actual_points_for[away_idx] += away_points
        if home_points > away_points:
            actual_wins[home_idx] += 1.0
        elif away_points > home_points:
            actual_wins[away_idx] += 1.0
        else:
            actual_wins[home_idx] += 0.5
            actual_wins[away_idx] += 0.5
    compiled_schedule = []
    weekly = bool(by_week_team)
    for matchup in request.schedule:
        if weekly:
            home_dist = by_week_team[(matchup.week, matchup.home_team_id)]
            away_dist = by_week_team[(matchup.week, matchup.away_team_id)]
        else:
            home_dist = by_team[matchup.home_team_id]
            away_dist = by_team[matchup.away_team_id]
        if home_dist.distribution_kind != ScoringDistributionKind.NORMAL or away_dist.distribution_kind != ScoringDistributionKind.NORMAL:
            raise ValueError("unsupported scoring distribution kind")
        compiled_schedule.append((
            team_index[matchup.home_team_id], team_index[matchup.away_team_id],
            home_dist.mean_points, home_dist.stddev_points,
            away_dist.mean_points, away_dist.stddev_points,
        ))
    if compile_started is not None:
        ended = _profile_clock()
        _logger.info(
            "FSFFL simulation profile phase=schedule_compile wall=%.6f cpu=%.6f "
            "teams=%s matchups=%s weekly=%s",
            ended[0] - compile_started[0], ended[1] - compile_started[1],
            team_count, len(compiled_schedule), weekly,
        )

    rng = Random(request.seed)
    gauss = rng.gauss
    playoff_rng = Random(request.seed ^ 0x5F3759DF)
    playoff_gauss = playoff_rng.gauss
    is_batched = request.rng_protocol == NUMPY_PCG64_BATCHED_GAUSS_V1
    batch_size = (
        request.rng_batch_size or NUMPY_BATCH_SIZE_DEFAULT if is_batched else None
    )
    score_batches = (
        iter(_numpy_regular_season_score_batches(request, compiled_schedule, batch_size))
        if is_batched
        else None
    )
    score_batch = None
    score_batch_offset = 0
    numpy_batch_wins = None
    numpy_batch_points = None
    rng_wall_seconds = 0.0
    rng_cpu_seconds = 0.0
    matchup_wall_seconds = 0.0
    matchup_cpu_seconds = 0.0
    aggregation_wall_seconds = 0.0
    profile_sample_interval = 100
    profile_sample_count = 0
    wins_sum = [0.0] * team_count
    remaining_wins_sum = [0.0] * team_count
    wins_sq_sum = [0.0] * team_count
    playoff_count = [0] * team_count
    first_count = [0] * team_count
    champion_count = [0] * team_count
    finish_count = [[0] * team_count for _ in range(team_count)]
    basic_playoff_config_supported = (
        request.playoff_team_count is not None
        and 2 <= request.playoff_team_count <= team_count
    )
    playoff_unavailability_reason = (
        request.playoff_rules.qualification_unavailability_reason()
        if request.playoff_rules is not None
        else (None if basic_playoff_config_supported else "playoff_settings_unavailable")
    )
    championship_unavailability_reason = (
        request.playoff_rules.simulation_unavailability_reason()
        if request.playoff_rules is not None
        else (
            "playoff_settings_unavailable"
            if not basic_playoff_config_supported
            else "playoff_start_week_unavailable"
        )
    )
    playoff_supported = playoff_unavailability_reason is None and basic_playoff_config_supported
    bye_unavailability_reason = (
        playoff_unavailability_reason
        if not playoff_supported
        else (
            "playoff_start_week_unavailable"
            if request.playoff_rules is None
            else (
                None
                if request.playoff_rules.effective_matchups()
                else "playoff_rules_unsupported:bracket_structure"
            )
        )
    )
    bye_supported = bye_unavailability_reason is None
    championship_supported = championship_unavailability_reason is None
    playoff_scoring = (
        _playoff_distributions(
            team_ids,
            by_team,
            by_playoff_week_team,
            request.playoff_rules,
        )
        if championship_supported
        else None
    )

    # Common-world coordinates intentionally fingerprint only the factual baseline,
    # ordered draw topology and governed league structure. Forecast means/standard
    # deviations are excluded except for the deterministic-vs-stochastic mask,
    # because changed strength is the counterfactual signal while draw alignment is
    # the variance-reduction contract.
    regular_common_world_payload = {
        "team_ids": team_ids,
        "completed_matchups": [
            item.model_dump(mode="json") for item in request.completed_matchups
        ],
        "schedule_draw_topology": [
            {
                "week": matchup.week,
                "home_team_id": matchup.home_team_id,
                "away_team_id": matchup.away_team_id,
                "home_stochastic": row[3] != 0.0,
                "away_stochastic": row[5] != 0.0,
            }
            for matchup, row in zip(request.schedule, compiled_schedule, strict=True)
        ],
        "playoff_team_count": request.playoff_team_count,
        "qualification_rules": (
            {
                "playoff_team_count": request.playoff_rules.playoff_team_count,
                "playoff_start_week": request.playoff_rules.playoff_start_week,
                "bye_seeds": request.playoff_rules.bye_seeds,
                "seeding_policy": request.playoff_rules.seeding_policy,
                "standings_tiebreak_policy": (
                    request.playoff_rules.standings_tiebreak_policy
                ),
            }
            if request.playoff_rules is not None
            else None
        ),
    }
    common_world_regular_season_coordinate = hashlib.sha256(
        json.dumps(
            regular_common_world_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    common_world_postseason_coordinate = None
    common_world_postseason_unavailability_reason = None
    if not championship_supported:
        common_world_postseason_unavailability_reason = (
            championship_unavailability_reason
            or "championship_simulation_unavailable"
        )
    elif playoff_scoring is None or request.playoff_rules is None:
        common_world_postseason_unavailability_reason = (
            "postseason_scoring_or_rules_unavailable"
        )
    else:
        postseason_stochastic_flags = tuple(
            stddev != 0.0
            for week in request.playoff_rules.round_weeks
            for _mean, stddev in playoff_scoring[week]
        )
        # If some possible playoff participants consume RNG and others do not,
        # advancement can change the number of draws between alternate States.
        # Same seed is then not sufficient to prove paired postseason worlds.
        if len(set(postseason_stochastic_flags)) > 1:
            common_world_postseason_unavailability_reason = (
                "mixed_deterministic_stochastic_playoff_draws"
            )
        else:
            postseason_common_world_payload = {
                "regular_coordinate": common_world_regular_season_coordinate,
                "playoff_rules": request.playoff_rules.model_dump(mode="json"),
                "canonical_execution_matchups": [
                    item.model_dump(mode="json")
                    for item in request.playoff_rules.canonical_execution_matchups()
                ],
                "postseason_randomness": (
                    "all_stochastic"
                    if postseason_stochastic_flags
                    and postseason_stochastic_flags[0]
                    else "all_deterministic"
                ),
            }
            common_world_postseason_coordinate = hashlib.sha256(
                json.dumps(
                    postseason_common_world_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()

    ranking_indexes = tuple(range(team_count))
    floor_at_zero = max

    for trial_index in range(request.simulation_count):
        # Scheduling-only checkpoint. Product orchestration may yield this worker
        # while foreground requests are active; the callback cannot alter the
        # simulation request, RNG stream, iteration count, or accumulated outputs.
        if cooperative_yield is not None:
            cooperative_yield()
        wins = actual_wins.copy()
        points_for = actual_points_for.copy()
        if is_batched:
            if score_batch is None or score_batch_offset >= len(score_batch):
                rng_started = _profile_clock() if profile_enabled else None
                score_batch = next(score_batches)
                if rng_started is not None:
                    rng_ended = _profile_clock()
                    rng_wall_seconds += rng_ended[0] - rng_started[0]
                    rng_cpu_seconds += rng_ended[1] - rng_started[1]
                matchup_started = _profile_clock() if profile_enabled else None
                numpy_batch_wins, numpy_batch_points = (
                    _numpy_regular_season_matchup_batches(
                        score_batch, compiled_schedule, team_count
                    )
                )
                if matchup_started is not None:
                    matchup_ended = _profile_clock()
                    matchup_wall_seconds += matchup_ended[0] - matchup_started[0]
                    matchup_cpu_seconds += matchup_ended[1] - matchup_started[1]
                score_batch_offset = 0
            simulated_wins = numpy_batch_wins[score_batch_offset].tolist()
            simulated_points = numpy_batch_points[score_batch_offset].tolist()
            trial_wins = [
                actual_wins[index] + simulated_wins[index]
                for index in range(team_count)
            ]
            trial_points = [
                actual_points_for[index] + simulated_points[index]
                for index in range(team_count)
            ]
            score_batch_offset += 1
        else:
            trial_wins = actual_wins.copy()
            trial_points = actual_points_for.copy()
        sample_trial = bool(
            profile_enabled and trial_index % profile_sample_interval == 0
        )
        sample_weight = min(
            profile_sample_interval,
            request.simulation_count - trial_index,
        )
        matchup_started = (
            _profile_wall_clock() if sample_trial and not is_batched else None
        )
        if not is_batched:
            wins = trial_wins
            points_for = trial_points
            for home_idx, away_idx, home_mean, home_stddev, away_mean, away_stddev in compiled_schedule:
                home = home_mean if home_stddev == 0 else gauss(home_mean, home_stddev)
                away = away_mean if away_stddev == 0 else gauss(away_mean, away_stddev)
                home = floor_at_zero(0.0, home)
                away = floor_at_zero(0.0, away)
                points_for[home_idx] += home
                points_for[away_idx] += away
                if home > away:
                    wins[home_idx] += 1.0
                elif away > home:
                    wins[away_idx] += 1.0
                else:
                    wins[home_idx] += 0.5
                    wins[away_idx] += 0.5
        else:
            wins = trial_wins
            points_for = trial_points
        if matchup_started is not None:
            matchup_ended = _profile_wall_clock()
            matchup_wall_seconds += (matchup_ended - matchup_started) * sample_weight
        aggregation_started = _profile_wall_clock() if sample_trial else None
        standings = sorted(ranking_indexes, key=lambda index: (-wins[index], -points_for[index], team_ids[index]))
        first_count[standings[0]] += 1
        for rank_index, team_idx in enumerate(standings):
            finish_count[team_idx][rank_index] += 1
        if playoff_supported:
            for index in standings[: request.playoff_team_count]:
                playoff_count[index] += 1
        if championship_supported:
            champion = _simulate_configured_champion(
                standings, request.playoff_rules, playoff_scoring, playoff_gauss
            )
            champion_count[champion] += 1
        else:
            champion = None
        if trial_observer is not None:
            trial_observer(
                tuple(wins), tuple(points_for), tuple(standings), champion
            )
        for index, value in enumerate(wins):
            wins_sum[index] += value
            remaining_wins_sum[index] += value - actual_wins[index]
            wins_sq_sum[index] += value * value
        if aggregation_started is not None:
            aggregation_ended = _profile_wall_clock()
            aggregation_wall_seconds += (aggregation_ended - aggregation_started) * sample_weight
            profile_sample_count += 1

    result_started = _profile_clock() if profile_enabled else None
    n = request.simulation_count
    outcomes = []
    finish_distributions = []
    for index, team_id in enumerate(team_ids):
        expected = wins_sum[index] / n
        variance = max(0.0, wins_sq_sum[index] / n - expected * expected)
        probabilities = tuple(count / n for count in finish_count[index])
        playoff_seed_probabilities = (
            probabilities[: request.playoff_team_count]
            if playoff_supported and request.playoff_team_count is not None
            else None
        )
        bye_probability = (
            sum(
                probabilities[seed - 1]
                for seed in request.playoff_rules.bye_seeds
            )
            if bye_supported and request.playoff_rules is not None
            else None
        )
        outcomes.append(TeamCompetitiveOutcome(
            team_id=team_id,
            expected_wins=expected,
            expected_remaining_wins=remaining_wins_sum[index] / n,
            wins_stddev=sqrt(variance),
            playoff_probability=(playoff_count[index] / n if playoff_supported else None),
            playoff_seed_probabilities=playoff_seed_probabilities,
            playoff_unavailability_reason=playoff_unavailability_reason,
            bye_probability=bye_probability,
            bye_unavailability_reason=bye_unavailability_reason,
            first_place_probability=first_count[index] / n,
            championship_probability=(champion_count[index] / n if championship_supported else None),
            championship_unavailability_reason=championship_unavailability_reason,
            simulation_count=n,
            simulation_model_version=request.model_version,
        ))
        expected_finish = sum((rank + 1) * probability for rank, probability in enumerate(probabilities))
        cumulative = 0.0
        median_finish = len(probabilities)
        for rank, probability in enumerate(probabilities, start=1):
            cumulative += probability
            if cumulative >= 0.5:
                median_finish = rank
                break
        finish_distributions.append(
            TeamFinishDistribution(
                team_id=team_id,
                expected_finish=expected_finish,
                median_finish=median_finish,
                rank_probabilities=probabilities,
                simulation_count=n,
                simulation_model_version=request.model_version,
            )
        )
    identity_payload = request.model_dump(mode="json")
    if not request.playoff_weekly_scoring:
        # Preserve replay identity for requests whose semantics did not gain
        # separate postseason evidence; populated postseason evidence remains
        # fingerprinted in full.
        identity_payload.pop("playoff_weekly_scoring", None)
    identity_payload["rng_batch_size"] = batch_size
    identity_payload["effective_rng_batch_size"] = batch_size
    input_fingerprint = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if is_batched:
        import numpy as np

        runtime_version = f"numpy-{np.__version__};python-{platform.python_version()}"
        bit_generator_name = "PCG64"
        draw_layout = "batch-major;trial-major;compiled-schedule-major;home-away-v1"
        seed_derivation = "pcg64-regular-root-seed-v1;python-playoff-xor-0x5F3759DF-v1"
    else:
        runtime_version = f"python-{platform.python_version()}"
        bit_generator_name = "python-random-mt19937"
        draw_layout = "trial-major;compiled-schedule-major;home-away-v1"
        seed_derivation = "python-regular-root-seed-v1;python-playoff-xor-0x5F3759DF-v1"
    result = RegularSeasonSimulationResult(
        outcomes=tuple(outcomes),
        finish_distributions=tuple(finish_distributions),
        championship_probability_provenance=(
            request.playoff_rules.championship_probability_provenance()
            if championship_supported and request.playoff_rules is not None else None
        ),
        simulation_count=n,
        seed=request.seed,
        model_version=request.model_version,
        rng_protocol=request.rng_protocol,
        rng_runtime_version=runtime_version,
        rng_bit_generator=bit_generator_name,
        rng_batch_size=batch_size,
        rng_draw_dtype="float64",
        rng_draw_layout=draw_layout,
        rng_seed_derivation=seed_derivation,
        simulation_input_fingerprint=input_fingerprint,
        common_world_regular_season_coordinate=(
            common_world_regular_season_coordinate
        ),
        common_world_postseason_coordinate=common_world_postseason_coordinate,
        common_world_postseason_unavailability_reason=(
            common_world_postseason_unavailability_reason
        ),
    )
    if result_started is not None:
        result_ended = _profile_clock()
        _logger.info(
            "FSFFL simulation profile phase=kernel_summary trials=%s rng_protocol=%s batch=%s "
            "rng_wall=%.6f rng_cpu=%.6f matchup_wall=%.6f matchup_cpu=%.6f "
            "standings_playoff_aggregation_wall_estimate=%.6f sample_interval=%s samples=%s "
            "result_materialization_wall=%.6f result_materialization_cpu=%.6f",
            request.simulation_count, request.rng_protocol, batch_size,
            rng_wall_seconds, rng_cpu_seconds, matchup_wall_seconds,
            matchup_cpu_seconds, aggregation_wall_seconds, profile_sample_interval,
            profile_sample_count,
            result_ended[0] - result_started[0], result_ended[1] - result_started[1],
        )
    return result


def _sample_points(distribution, rng: Random) -> float:
    if distribution.distribution_kind != ScoringDistributionKind.NORMAL:
        raise ValueError("unsupported scoring distribution kind")
    if distribution.stddev_points == 0:
        return max(0.0, distribution.mean_points)
    return max(0.0, rng.gauss(distribution.mean_points, distribution.stddev_points))
