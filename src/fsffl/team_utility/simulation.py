from __future__ import annotations

from array import array
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

from fsffl.state.draft_order_policy import DraftOrderPolicyEvidence
from fsffl.state.models import FrozenModel, LeaguePlayoffRules, LeagueState

from .future_pick import (
    SupportedFuturePickDraftOrder,
    TeamOriginFuturePickDistribution,
    build_team_origin_future_pick_distribution,
    compile_supported_future_pick_policy,
)

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
    future_pick_draft_season: Annotated[int, Field(ge=1900)] | None = None
    future_pick_draft_order_policy: DraftOrderPolicyEvidence | None = None
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
        if (
            self.future_pick_draft_order_policy is not None
            and self.future_pick_draft_season is None
        ):
            raise ValueError(
                "explicit future-pick draft-order policy requires draft season"
            )
        if (
            self.future_pick_draft_order_policy is not None
            and self.future_pick_draft_season is not None
            and self.future_pick_draft_order_policy.draft_season
            != self.future_pick_draft_season
        ):
            raise ValueError(
                "future-pick draft-order policy season conflicts with draft season"
            )
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


class MultiverseWorldTeamOutcome(FrozenModel):
    """Compact final-season summary for one team in one selected world."""

    team_id: str
    final_wins: float
    points_for: float
    regular_season_rank: Annotated[int, Field(ge=1)]
    playoff_seed: Annotated[int, Field(ge=1)] | None = None
    made_playoffs: bool | None = None
    champion: bool | None = None


class MultiverseNotableMatchup(FrozenModel):
    """Future matchup fact used to explain an upset or blowout exemplar."""

    week: Annotated[int, Field(ge=1)]
    home_team_id: str
    away_team_id: str
    home_points: Annotated[float, Field(ge=0)]
    away_points: Annotated[float, Field(ge=0)]
    margin: Annotated[float, Field(ge=0)]
    expected_home_points: float
    expected_away_points: float
    expected_underdog_disadvantage: Annotated[float, Field(ge=0)] = 0.0


class MultiverseRarityContext(FrozenModel):
    """Empirical rarity from the same canonical Monte Carlo run."""

    basis: Literal[
        "representative_typicality",
        "empirical_upper_tail",
        "empirical_lower_tail",
        "empirical_event_frequency",
    ]
    empirical_probability: Annotated[float, Field(ge=0, le=1)] | None = None
    empirical_percentile: Annotated[float, Field(ge=0, le=1)] | None = None
    sample_count: Annotated[int, Field(ge=1)]
    metric_value: float | None = None
    label: Literal[
        "representative", "common", "plausible", "unusual", "rare", "extreme"
    ]


class MultiverseWorldExample(FrozenModel):
    """Bounded replayable exemplar selected from the authoritative worlds."""

    category: Literal[
        "expected_like",
        "plausible_upside",
        "plausible_downside",
        "extreme_tail",
        "biggest_blowout",
        "biggest_upset",
        "strong_team_misses_playoffs",
        "low_seed_champion",
    ]
    simulation_id: str
    world_id: str
    world_index: Annotated[int, Field(ge=0)]
    root_seed: int
    rng_protocol: str
    rng_runtime_version: str
    rng_bit_generator: str
    rng_batch_size: Annotated[int, Field(ge=1)] | None = None
    rng_draw_layout: str
    rng_seed_derivation: str
    simulation_input_fingerprint: str
    standings: tuple[str, ...]
    team_outcomes: tuple[MultiverseWorldTeamOutcome, ...]
    champion_team_id: str | None = None
    focal_team_id: str | None = None
    notable_matchup: MultiverseNotableMatchup | None = None
    selection_metric: float
    rarity: MultiverseRarityContext
    model_version: str = "next4-multiverse-world-v1"

    @model_validator(mode="after")
    def validate_world(self) -> "MultiverseWorldExample":
        identifiers = (
            self.simulation_id,
            self.world_id,
            self.rng_protocol,
            self.rng_runtime_version,
            self.rng_bit_generator,
            self.rng_draw_layout,
            self.rng_seed_derivation,
            self.simulation_input_fingerprint,
            self.model_version,
        )
        if any(not value.strip() for value in identifiers):
            raise ValueError("Multiverse replay identifiers cannot be blank")
        if not self.standings or len(set(self.standings)) != len(self.standings):
            raise ValueError("Multiverse standings must be non-empty and unique")
        outcome_ids = tuple(item.team_id for item in self.team_outcomes)
        if set(outcome_ids) != set(self.standings):
            raise ValueError("Multiverse team outcomes must match standings")
        return self


class RegularSeasonSimulationResult(FrozenModel):
    outcomes: tuple[TeamCompetitiveOutcome, ...]
    finish_distributions: tuple[TeamFinishDistribution, ...] = ()
    future_pick_distributions: tuple[TeamOriginFuturePickDistribution, ...] = ()
    future_pick_unavailability_reason: str | None = None
    multiverse_worlds: tuple[MultiverseWorldExample, ...] = ()
    multiverse_model_version: str = "next4-multiverse-v1"
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
    baseline_simulation_model_version: str
    scenario_simulation_model_version: str
    baseline_simulation_count: Annotated[int, Field(ge=1)]
    scenario_simulation_count: Annotated[int, Field(ge=1)]
    baseline_seed: int
    scenario_seed: int
    baseline_rng_protocol: str
    scenario_rng_protocol: str
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
        identifiers = (
            self.team_id,
            self.model_version,
            self.baseline_simulation_model_version,
            self.scenario_simulation_model_version,
            self.baseline_rng_protocol,
            self.scenario_rng_protocol,
            self.baseline_simulation_input_fingerprint,
            self.scenario_simulation_input_fingerprint,
        )
        if any(not value.strip() for value in identifiers):
            raise ValueError("counterfactual delta identifiers cannot be blank")

        if self.regular_season_common_worlds:
            if self.regular_season_unavailability_reason is not None:
                raise ValueError(
                    "common regular-season worlds cannot carry an unavailability reason"
                )
            if self.comparison_method != "common_random_numbers":
                raise ValueError(
                    "common regular-season worlds require common-random-number provenance"
                )
            if (
                self.baseline_simulation_model_version
                != self.scenario_simulation_model_version
                or self.baseline_simulation_count != self.scenario_simulation_count
                or self.baseline_seed != self.scenario_seed
                or self.baseline_rng_protocol != self.scenario_rng_protocol
            ):
                raise ValueError(
                    "common regular-season worlds require matching replay coordinates"
                )
        else:
            if self.regular_season_unavailability_reason is None:
                raise ValueError(
                    "unpaired regular-season comparison requires an unavailability reason"
                )
            if self.comparison_method != "aggregate_difference":
                raise ValueError(
                    "unpaired regular-season comparison must use aggregate-difference provenance"
                )

        if self.postseason_common_worlds:
            if not self.regular_season_common_worlds:
                raise ValueError(
                    "common postseason worlds require common regular-season worlds"
                )
            if self.postseason_unavailability_reason is not None:
                raise ValueError(
                    "common postseason worlds cannot carry an unavailability reason"
                )
            if (
                self.championship_probability is None
                or self.championship_comparison_method != "common_random_numbers"
            ):
                raise ValueError(
                    "common postseason worlds require a paired championship delta"
                )
        else:
            if self.postseason_unavailability_reason is None:
                raise ValueError(
                    "unpaired postseason comparison requires an unavailability reason"
                )
            expected_method = (
                "unavailable"
                if self.championship_probability is None
                else "aggregate_difference"
            )
            if self.championship_comparison_method != expected_method:
                raise ValueError(
                    "championship comparison provenance conflicts with postseason pairing"
                )
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
        baseline_simulation_model_version=baseline.model_version,
        scenario_simulation_model_version=scenario.model_version,
        baseline_simulation_count=baseline.simulation_count,
        scenario_simulation_count=scenario.simulation_count,
        baseline_seed=baseline.seed,
        scenario_seed=scenario.seed,
        baseline_rng_protocol=baseline.rng_protocol,
        scenario_rng_protocol=scenario.rng_protocol,
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
    future_pick_draft_season: int | None = None,
    future_pick_draft_order_policy: DraftOrderPolicyEvidence | None = None,
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
        future_pick_draft_season=future_pick_draft_season,
        future_pick_draft_order_policy=future_pick_draft_order_policy,
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


def _playoff_game_result(left, right, playoff_scoring, week, gauss):
    winner = _playoff_game(left, right, playoff_scoring, week, gauss)
    loser = right if winner == left else left
    return winner, loser


def _simulate_configured_playoff_outcomes(
    standings,
    playoff_rules,
    playoff_scoring,
    gauss,
) -> tuple[int, dict[int, int]]:
    """Return champion plus each loser's canonical elimination round."""

    if (
        playoff_rules is None
        or playoff_rules.simulation_unavailability_reason() is not None
    ):
        raise ValueError(
            "future-pick playoff elimination requires governed playoff structure"
        )
    seeds = {
        seed: (standings[seed - 1], seed)
        for seed in range(1, playoff_rules.playoff_team_count + 1)
    }
    winners = {}
    elimination_round: dict[int, int] = {}
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
        winner, loser = _playoff_game_result(
            left,
            right,
            playoff_scoring,
            matchup.week,
            gauss,
        )
        winners[matchup.matchup_id] = winner
        elimination_round[loser[0]] = matchup.round_number
    champion = winners[playoff_rules.championship_matchup_id][0]
    return champion, elimination_round


def _simulate_explicit_six_team_placement_order(
    standings,
    playoff_rules,
    playoff_scoring,
    bracket_gauss,
    placement_gauss,
) -> tuple[int, dict[int, int]]:
    """Honor an explicitly governed six-team placement-game draft rule.

    This is never used by the derived standard fallback. It exists only for an
    explicit league policy that says 5th-/3rd-place games affect draft order.
    """

    if (
        playoff_rules is None
        or playoff_rules.playoff_team_count != 6
        or playoff_rules.round_count != 3
        or tuple(playoff_rules.bye_seeds) != (1, 2)
        or len(playoff_rules.round_weeks) != 3
    ):
        raise ValueError(
            "explicit placement-game draft order requires six-team playoff structure"
        )
    seeds = {seed: (standings[seed - 1], seed) for seed in range(1, 7)}
    week_one, week_two, week_three = playoff_rules.round_weeks

    qf_a_winner, qf_a_loser = _playoff_game_result(
        seeds[3], seeds[6], playoff_scoring, week_one, bracket_gauss
    )
    qf_b_winner, qf_b_loser = _playoff_game_result(
        seeds[4], seeds[5], playoff_scoring, week_one, bracket_gauss
    )
    fifth_winner, fifth_loser = _playoff_game_result(
        qf_a_loser, qf_b_loser, playoff_scoring, week_two, placement_gauss
    )
    sf_a_winner, sf_a_loser = _playoff_game_result(
        seeds[1], qf_b_winner, playoff_scoring, week_two, bracket_gauss
    )
    sf_b_winner, sf_b_loser = _playoff_game_result(
        seeds[2], qf_a_winner, playoff_scoring, week_two, bracket_gauss
    )
    third_winner, third_loser = _playoff_game_result(
        sf_a_loser, sf_b_loser, playoff_scoring, week_three, placement_gauss
    )
    champion, runner_up = _playoff_game_result(
        sf_a_winner, sf_b_winner, playoff_scoring, week_three, bracket_gauss
    )

    return champion[0], {
        champion[0]: 1,
        runner_up[0]: 2,
        third_winner[0]: 3,
        third_loser[0]: 4,
        fifth_winner[0]: 5,
        fifth_loser[0]: 6,
    }


def _record_head_to_head_result(
    home_idx: int,
    away_idx: int,
    home_points: float,
    away_points: float,
    h2h_points: list[list[float]],
    h2h_games: list[list[int]],
) -> None:
    h2h_games[home_idx][away_idx] += 1
    h2h_games[away_idx][home_idx] += 1
    if home_points > away_points:
        h2h_points[home_idx][away_idx] += 1.0
    elif away_points > home_points:
        h2h_points[away_idx][home_idx] += 1.0
    else:
        h2h_points[home_idx][away_idx] += 0.5
        h2h_points[away_idx][home_idx] += 0.5


def _group_equal_values(
    indexes: list[int],
    value_for,
) -> list[list[int]]:
    groups: list[list[int]] = []
    for index in indexes:
        value = value_for(index)
        if groups and value_for(groups[-1][0]) == value:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _regular_season_draft_order_groups(
    team_indexes,
    *,
    wins,
    points_for,
    games_by_team,
    h2h_points,
    h2h_games,
) -> list[list[int]]:
    """Order earlier picks by record, resolvable H2H, then lower Points For.

    Exact ties remaining after the governed sequence are returned as one group so
    callers can spread probability evenly across the still-unresolved slots rather
    than inventing a hidden final tiebreak.
    """

    ordered = sorted(
        team_indexes,
        key=lambda index: (
            wins[index] / games_by_team[index],
            points_for[index],
        ),
    )
    record_groups = _group_equal_values(
        ordered,
        lambda index: wins[index] / games_by_team[index],
    )
    output: list[list[int]] = []
    for record_group in record_groups:
        if len(record_group) == 1:
            output.append(record_group)
            continue

        h2h_game_totals = {
            index: sum(
                h2h_games[index][other]
                for other in record_group
                if other != index
            )
            for index in record_group
        }
        h2h_resolvable = (
            all(value > 0 for value in h2h_game_totals.values())
            and len(set(h2h_game_totals.values())) == 1
        )
        h2h_groups = [record_group]
        if h2h_resolvable:
            h2h_pct = {
                index: (
                    sum(
                        h2h_points[index][other]
                        for other in record_group
                        if other != index
                    )
                    / h2h_game_totals[index]
                )
                for index in record_group
            }
            if len(set(h2h_pct.values())) > 1:
                h2h_ordered = sorted(record_group, key=lambda index: h2h_pct[index])
                h2h_groups = _group_equal_values(
                    h2h_ordered,
                    lambda index: h2h_pct[index],
                )

        for h2h_group in h2h_groups:
            pf_ordered = sorted(h2h_group, key=lambda index: points_for[index])
            output.extend(
                _group_equal_values(
                    pf_ordered,
                    lambda index: points_for[index],
                )
            )
    return output


def _accumulate_slot_groups(
    slot_counts: list[list[float]],
    groups: list[list[int]],
    *,
    start_slot: int,
) -> int:
    """Accumulate one world's governed order, splitting unresolved exact ties."""

    slot = start_slot
    for group in groups:
        width = len(group)
        weight = 1.0 / width
        for team_idx in group:
            for slot_in_round in range(slot, slot + width):
                slot_counts[team_idx][slot_in_round - 1] += weight
        slot += width
    return slot


def _multiverse_rarity_label(
    probability: float | None,
    *,
    representative: bool = False,
) -> Literal["representative", "common", "plausible", "unusual", "rare", "extreme"]:
    if representative:
        return "representative"
    if probability is None:
        return "plausible"
    if probability <= 0.001:
        return "extreme"
    if probability <= 0.01:
        return "rare"
    if probability <= 0.05:
        return "unusual"
    if probability <= 0.25:
        return "plausible"
    return "common"


def _capture_multiverse_candidate(
    *,
    trial_index: int,
    wins: list[float],
    points_for: list[float],
    standings: list[int],
    champion: int | None,
    focal_team: int | None,
    selection_metric: float,
    rarity_metric_value: float | None = None,
    notable_matchup: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "trial_index": trial_index,
        "wins": tuple(wins),
        "points_for": tuple(points_for),
        "standings": tuple(standings),
        "champion": champion,
        "focal_team": focal_team,
        "selection_metric": float(selection_metric),
        "rarity_metric_value": (
            None if rarity_metric_value is None else float(rarity_metric_value)
        ),
        "notable_matchup": notable_matchup,
    }


def _empirical_probability(
    values: array,
    threshold: float,
    *,
    upper_tail: bool,
) -> float:
    if not values:
        return 0.0
    if upper_tail:
        count = sum(1 for value in values if value >= threshold)
    else:
        count = sum(1 for value in values if value <= threshold)
    return count / len(values)


def _empirical_percentile(values: array, threshold: float) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value <= threshold) / len(values)


def _build_multiverse_examples(
    *,
    candidates: dict[str, dict[str, object]],
    team_ids: tuple[str, ...],
    playoff_team_count: int | None,
    playoff_supported: bool,
    championship_supported: bool,
    league_totals: array,
    typicality_values: array,
    blowout_values: array,
    upset_values: array,
    strong_team_miss_count: int,
    champion_seed_counts: list[int],
    simulation_count: int,
    simulation_id: str,
    root_seed: int,
    rng_protocol: str,
    rng_runtime_version: str,
    rng_bit_generator: str,
    rng_batch_size: int | None,
    rng_draw_layout: str,
    rng_seed_derivation: str,
    simulation_input_fingerprint: str,
) -> tuple[MultiverseWorldExample, ...]:
    category_order = (
        "expected_like",
        "plausible_upside",
        "plausible_downside",
        "extreme_tail",
        "biggest_blowout",
        "biggest_upset",
        "strong_team_misses_playoffs",
        "low_seed_champion",
    )
    examples: list[MultiverseWorldExample] = []
    for category in category_order:
        candidate = candidates.get(category)
        if candidate is None:
            continue
        metric_value = candidate.get("rarity_metric_value")
        empirical_probability: float | None = None
        empirical_percentile: float | None = None
        basis: Literal[
            "representative_typicality",
            "empirical_upper_tail",
            "empirical_lower_tail",
            "empirical_event_frequency",
        ]
        if category == "expected_like":
            basis = "representative_typicality"
            if metric_value is not None:
                empirical_percentile = _empirical_percentile(
                    typicality_values, float(metric_value)
                )
            label = _multiverse_rarity_label(None, representative=True)
        elif category == "plausible_upside":
            basis = "empirical_upper_tail"
            empirical_probability = _empirical_probability(
                league_totals, float(metric_value), upper_tail=True
            )
            empirical_percentile = _empirical_percentile(
                league_totals, float(metric_value)
            )
            label = _multiverse_rarity_label(empirical_probability)
        elif category == "plausible_downside":
            basis = "empirical_lower_tail"
            empirical_probability = _empirical_probability(
                league_totals, float(metric_value), upper_tail=False
            )
            empirical_percentile = _empirical_percentile(
                league_totals, float(metric_value)
            )
            label = _multiverse_rarity_label(empirical_probability)
        elif category == "extreme_tail":
            basis = "empirical_upper_tail"
            empirical_probability = _empirical_probability(
                typicality_values, float(metric_value), upper_tail=True
            )
            empirical_percentile = _empirical_percentile(
                typicality_values, float(metric_value)
            )
            label = _multiverse_rarity_label(empirical_probability)
        elif category == "biggest_blowout":
            basis = "empirical_upper_tail"
            empirical_probability = _empirical_probability(
                blowout_values, float(metric_value), upper_tail=True
            )
            empirical_percentile = _empirical_percentile(
                blowout_values, float(metric_value)
            )
            label = _multiverse_rarity_label(empirical_probability)
        elif category == "biggest_upset":
            basis = "empirical_upper_tail"
            empirical_probability = _empirical_probability(
                upset_values, float(metric_value), upper_tail=True
            )
            empirical_percentile = _empirical_percentile(
                upset_values, float(metric_value)
            )
            label = _multiverse_rarity_label(empirical_probability)
        elif category == "strong_team_misses_playoffs":
            basis = "empirical_event_frequency"
            empirical_probability = strong_team_miss_count / simulation_count
            label = _multiverse_rarity_label(empirical_probability)
        else:
            basis = "empirical_event_frequency"
            seed = int(round(float(metric_value)))
            empirical_probability = (
                sum(champion_seed_counts[seed:]) / simulation_count
                if 0 <= seed < len(champion_seed_counts)
                else 0.0
            )
            label = _multiverse_rarity_label(empirical_probability)

        standings_indexes = tuple(candidate["standings"])
        standings = tuple(team_ids[index] for index in standings_indexes)
        wins = tuple(candidate["wins"])
        points_for = tuple(candidate["points_for"])
        champion_index = candidate["champion"]
        team_outcomes = tuple(
            MultiverseWorldTeamOutcome(
                team_id=team_id,
                final_wins=float(wins[index]),
                points_for=float(points_for[index]),
                regular_season_rank=standings_indexes.index(index) + 1,
                playoff_seed=(
                    standings_indexes.index(index) + 1
                    if (
                        playoff_supported
                        and playoff_team_count is not None
                        and standings_indexes.index(index) < playoff_team_count
                    )
                    else None
                ),
                made_playoffs=(
                    standings_indexes.index(index) < playoff_team_count
                    if playoff_supported and playoff_team_count is not None
                    else None
                ),
                champion=(
                    index == champion_index if championship_supported else None
                ),
            )
            for index, team_id in enumerate(team_ids)
        )

        notable = candidate.get("notable_matchup")
        notable_model = None
        if isinstance(notable, dict):
            notable_model = MultiverseNotableMatchup(
                week=int(notable["week"]),
                home_team_id=str(notable["home_team_id"]),
                away_team_id=str(notable["away_team_id"]),
                home_points=float(notable["home_points"]),
                away_points=float(notable["away_points"]),
                margin=float(notable["margin"]),
                expected_home_points=float(notable["expected_home_points"]),
                expected_away_points=float(notable["expected_away_points"]),
                expected_underdog_disadvantage=float(
                    notable.get("expected_underdog_disadvantage", 0.0)
                ),
            )

        world_index = int(candidate["trial_index"])
        world_id = hashlib.sha256(
            f"{simulation_id}:{world_index}".encode()
        ).hexdigest()
        focal_index = candidate.get("focal_team")
        examples.append(
            MultiverseWorldExample(
                category=category,
                simulation_id=simulation_id,
                world_id=world_id,
                world_index=world_index,
                root_seed=root_seed,
                rng_protocol=rng_protocol,
                rng_runtime_version=rng_runtime_version,
                rng_bit_generator=rng_bit_generator,
                rng_batch_size=rng_batch_size,
                rng_draw_layout=rng_draw_layout,
                rng_seed_derivation=rng_seed_derivation,
                simulation_input_fingerprint=simulation_input_fingerprint,
                standings=standings,
                team_outcomes=team_outcomes,
                champion_team_id=(
                    team_ids[int(champion_index)]
                    if champion_index is not None
                    else None
                ),
                focal_team_id=(
                    team_ids[int(focal_index)]
                    if focal_index is not None
                    else None
                ),
                notable_matchup=notable_model,
                selection_metric=float(candidate["selection_metric"]),
                rarity=MultiverseRarityContext(
                    basis=basis,
                    empirical_probability=empirical_probability,
                    empirical_percentile=empirical_percentile,
                    sample_count=simulation_count,
                    metric_value=(
                        None if metric_value is None else float(metric_value)
                    ),
                    label=label,
                ),
            )
        )
    return tuple(examples)


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

    future_pick_policy: SupportedFuturePickDraftOrder | None = None
    future_pick_unavailability_reason: str | None = None
    if request.future_pick_draft_season is not None:
        try:
            future_pick_policy = compile_supported_future_pick_policy(
                request.future_pick_draft_order_policy,
                draft_season=request.future_pick_draft_season,
                team_count=team_count,
                playoff_team_count=request.playoff_team_count,
            )
        except ValueError as exc:
            future_pick_policy = None
            future_pick_unavailability_reason = str(exc)

    actual_wins = [0.0] * team_count
    actual_points_for = [0.0] * team_count
    actual_games = [0] * team_count
    actual_h2h_points = [[0.0] * team_count for _ in range(team_count)]
    actual_h2h_games = [[0] * team_count for _ in range(team_count)]
    for matchup in request.completed_matchups:
        home_idx = team_index[matchup.home_team_id]
        away_idx = team_index[matchup.away_team_id]
        home_points = matchup.home_points
        away_points = matchup.away_points
        actual_points_for[home_idx] += home_points
        actual_points_for[away_idx] += away_points
        actual_games[home_idx] += 1
        actual_games[away_idx] += 1
        _record_head_to_head_result(
            home_idx,
            away_idx,
            home_points,
            away_points,
            actual_h2h_points,
            actual_h2h_games,
        )
        if home_points > away_points:
            actual_wins[home_idx] += 1.0
        elif away_points > home_points:
            actual_wins[away_idx] += 1.0
        else:
            actual_wins[home_idx] += 0.5
            actual_wins[away_idx] += 0.5

    games_by_team = actual_games.copy()
    for matchup in request.schedule:
        games_by_team[team_index[matchup.home_team_id]] += 1
        games_by_team[team_index[matchup.away_team_id]] += 1
    if future_pick_policy is not None and any(value < 1 for value in games_by_team):
        future_pick_policy = None
        future_pick_unavailability_reason = (
            "governed draft-order fallback requires regular-season games for every team"
        )
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
    placement_game_rng = Random(request.seed ^ 0xD12A70D5)
    placement_game_gauss = placement_game_rng.gauss
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

    future_pick_slot_counts: list[list[float]] | None = None
    if future_pick_policy is not None:
        if playoff_scoring is None or request.playoff_rules is None:
            future_pick_unavailability_reason = (
                "future_pick_playoff_elimination_evidence_unavailable"
            )
        elif (
            request.playoff_rules.playoff_team_count
            != future_pick_policy.playoff_team_count
        ):
            future_pick_unavailability_reason = (
                "future_pick_playoff_count_conflicts_with_policy"
            )
        else:
            future_pick_slot_counts = [
                [0.0] * team_count for _ in range(team_count)
            ]
            future_pick_unavailability_reason = None

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
        postseason_randomness_by_week: list[tuple[int, str]] = []
        for week in request.playoff_rules.round_weeks:
            week_stochastic_flags = tuple(
                stddev != 0.0 for _mean, stddev in playoff_scoring[week]
            )
            # Pairing is stable when every possible participant in a given game
            # week consumes the same number of RNG draws. Different playoff weeks
            # may legitimately be all-stochastic vs all-deterministic because the
            # number of draws remains fixed within each week for either State.
            if len(set(week_stochastic_flags)) > 1:
                common_world_postseason_unavailability_reason = (
                    "mixed_deterministic_stochastic_playoff_draws"
                )
                break
            postseason_randomness_by_week.append(
                (
                    week,
                    "all_stochastic"
                    if week_stochastic_flags and week_stochastic_flags[0]
                    else "all_deterministic",
                )
            )
        if common_world_postseason_unavailability_reason is None:
            postseason_common_world_payload = {
                "regular_coordinate": common_world_regular_season_coordinate,
                "playoff_rules": request.playoff_rules.model_dump(mode="json"),
                "canonical_execution_matchups": [
                    item.model_dump(mode="json")
                    for item in request.playoff_rules.canonical_execution_matchups()
                ],
                "postseason_randomness_by_week": postseason_randomness_by_week,
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

    expected_final_points = actual_points_for.copy()
    final_points_variance = [0.0] * team_count
    for (
        home_idx,
        away_idx,
        home_mean,
        home_stddev,
        away_mean,
        away_stddev,
    ) in compiled_schedule:
        expected_final_points[home_idx] += home_mean
        expected_final_points[away_idx] += away_mean
        final_points_variance[home_idx] += home_stddev * home_stddev
        final_points_variance[away_idx] += away_stddev * away_stddev
    final_points_stddev = [sqrt(value) for value in final_points_variance]
    league_expected_total = sum(expected_final_points)
    league_total_stddev = sqrt(sum(final_points_variance))
    plausible_upside_target = league_expected_total + league_total_stddev
    plausible_downside_target = max(0.0, league_expected_total - league_total_stddev)
    strongest_expected_team = max(
        range(team_count),
        key=lambda index: (expected_final_points[index], -index),
    )

    multiverse_candidates: dict[str, dict[str, object]] = {}
    league_totals = array("d")
    typicality_values = array("d")
    blowout_values = array("d")
    upset_values = array("d")
    strong_team_miss_count = 0
    champion_seed_counts = [0] * (team_count + 1)

    for trial_index in range(request.simulation_count):
        # Scheduling-only checkpoint. Product orchestration may yield this worker
        # while foreground requests are active; the callback cannot alter the
        # simulation request, RNG stream, iteration count, or accumulated outputs.
        if cooperative_yield is not None:
            cooperative_yield()
        wins = actual_wins.copy()
        points_for = actual_points_for.copy()
        h2h_points = [row.copy() for row in actual_h2h_points]
        h2h_games = [row.copy() for row in actual_h2h_games]
        trial_score_row = None
        trial_biggest_blowout: tuple[float, int, float, float] | None = None
        trial_biggest_upset: tuple[float, float, int, float, float] | None = None
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
            trial_score_row = score_batch[score_batch_offset]
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
            for matchup_index, (
                home_idx,
                away_idx,
                home_mean,
                home_stddev,
                away_mean,
                away_stddev,
            ) in enumerate(compiled_schedule):
                home = home_mean if home_stddev == 0 else gauss(home_mean, home_stddev)
                away = away_mean if away_stddev == 0 else gauss(away_mean, away_stddev)
                home = floor_at_zero(0.0, home)
                away = floor_at_zero(0.0, away)
                points_for[home_idx] += home
                points_for[away_idx] += away
                _record_head_to_head_result(
                    home_idx,
                    away_idx,
                    home,
                    away,
                    h2h_points,
                    h2h_games,
                )
                if home > away:
                    wins[home_idx] += 1.0
                elif away > home:
                    wins[away_idx] += 1.0
                else:
                    wins[home_idx] += 0.5
                    wins[away_idx] += 0.5
                margin = abs(home - away)
                if (
                    trial_biggest_blowout is None
                    or margin > trial_biggest_blowout[0]
                ):
                    trial_biggest_blowout = (
                        margin,
                        matchup_index,
                        home,
                        away,
                    )
                upset_disadvantage = 0.0
                if home > away and home_mean < away_mean:
                    upset_disadvantage = away_mean - home_mean
                elif away > home and away_mean < home_mean:
                    upset_disadvantage = home_mean - away_mean
                if upset_disadvantage > 0.0:
                    upset_key = (upset_disadvantage, margin)
                    if (
                        trial_biggest_upset is None
                        or upset_key
                        > (
                            trial_biggest_upset[0],
                            trial_biggest_upset[1],
                        )
                    ):
                        trial_biggest_upset = (
                            upset_disadvantage,
                            margin,
                            matchup_index,
                            home,
                            away,
                        )
        else:
            wins = trial_wins
            points_for = trial_points
            if trial_score_row is not None:
                for matchup_index, row in enumerate(compiled_schedule):
                    (
                        home_idx,
                        away_idx,
                        home_mean,
                        _home_stddev,
                        away_mean,
                        _away_stddev,
                    ) = row
                    home = float(trial_score_row[2 * matchup_index])
                    away = float(trial_score_row[2 * matchup_index + 1])
                    _record_head_to_head_result(
                        home_idx,
                        away_idx,
                        home,
                        away,
                        h2h_points,
                        h2h_games,
                    )
                    margin = abs(home - away)
                    if (
                        trial_biggest_blowout is None
                        or margin > trial_biggest_blowout[0]
                    ):
                        trial_biggest_blowout = (
                            margin,
                            matchup_index,
                            home,
                            away,
                        )
                    upset_disadvantage = 0.0
                    if home > away and home_mean < away_mean:
                        upset_disadvantage = away_mean - home_mean
                    elif away > home and away_mean < home_mean:
                        upset_disadvantage = home_mean - away_mean
                    if upset_disadvantage > 0.0:
                        upset_key = (upset_disadvantage, margin)
                        if (
                            trial_biggest_upset is None
                            or upset_key
                            > (
                                trial_biggest_upset[0],
                                trial_biggest_upset[1],
                            )
                        ):
                            trial_biggest_upset = (
                                upset_disadvantage,
                                margin,
                                matchup_index,
                                home,
                                away,
                            )
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
        playoff_places_for_draft = None
        playoff_elimination_rounds = None
        if championship_supported:
            if (
                future_pick_slot_counts is not None
                and future_pick_policy is not None
                and future_pick_policy.placement_games_affect_order
            ):
                champion, playoff_places_for_draft = (
                    _simulate_explicit_six_team_placement_order(
                        standings,
                        request.playoff_rules,
                        playoff_scoring,
                        playoff_gauss,
                        placement_game_gauss,
                    )
                )
            elif future_pick_slot_counts is not None and future_pick_policy is not None:
                champion, playoff_elimination_rounds = (
                    _simulate_configured_playoff_outcomes(
                        standings,
                        request.playoff_rules,
                        playoff_scoring,
                        playoff_gauss,
                    )
                )
            else:
                champion = _simulate_configured_champion(
                    standings, request.playoff_rules, playoff_scoring, playoff_gauss
                )
            champion_count[champion] += 1
        else:
            champion = None

        if future_pick_slot_counts is not None and future_pick_policy is not None:
            playoff_team_count = future_pick_policy.playoff_team_count
            non_playoff = standings[playoff_team_count:]
            if len(non_playoff) != future_pick_policy.non_playoff_team_count:
                raise ValueError(
                    "future-pick non-playoff team count conflicts with policy"
                )

            non_playoff_groups = _regular_season_draft_order_groups(
                non_playoff,
                wins=wins,
                points_for=points_for,
                games_by_team=games_by_team,
                h2h_points=h2h_points,
                h2h_games=h2h_games,
            )
            next_slot = _accumulate_slot_groups(
                future_pick_slot_counts,
                non_playoff_groups,
                start_slot=1,
            )

            if future_pick_policy.placement_games_affect_order:
                if playoff_places_for_draft is None:
                    raise ValueError(
                        "explicit placement-game draft order was not simulated"
                    )
                ordered = sorted(
                    playoff_places_for_draft.items(),
                    key=lambda row: row[1],
                    reverse=True,
                )
                for team_idx, _final_place in ordered:
                    future_pick_slot_counts[team_idx][next_slot - 1] += 1.0
                    next_slot += 1
            else:
                if playoff_elimination_rounds is None or champion is None:
                    raise ValueError(
                        "future-pick playoff elimination was not simulated"
                    )
                eliminated_by_round: dict[int, list[int]] = {}
                for team_idx, round_number in playoff_elimination_rounds.items():
                    eliminated_by_round.setdefault(round_number, []).append(team_idx)
                for round_number in sorted(eliminated_by_round):
                    round_groups = _regular_season_draft_order_groups(
                        eliminated_by_round[round_number],
                        wins=wins,
                        points_for=points_for,
                        games_by_team=games_by_team,
                        h2h_points=h2h_points,
                        h2h_games=h2h_games,
                    )
                    next_slot = _accumulate_slot_groups(
                        future_pick_slot_counts,
                        round_groups,
                        start_slot=next_slot,
                    )
                future_pick_slot_counts[champion][team_count - 1] += 1.0
                next_slot += 1

            if next_slot != team_count + 1:
                raise ValueError(
                    "future-pick draft order did not assign every league slot"
                )

        league_total = sum(points_for)
        typicality = 0.0
        for index in range(team_count):
            stddev = final_points_stddev[index]
            if stddev > 0.0:
                z_score = (
                    points_for[index] - expected_final_points[index]
                ) / stddev
                typicality += z_score * z_score
        league_totals.append(league_total)
        typicality_values.append(typicality)
        blowout_metric = (
            trial_biggest_blowout[0]
            if trial_biggest_blowout is not None
            else 0.0
        )
        upset_metric = (
            trial_biggest_upset[0]
            if trial_biggest_upset is not None
            else 0.0
        )
        blowout_values.append(blowout_metric)
        upset_values.append(upset_metric)

        expected_like = multiverse_candidates.get("expected_like")
        if (
            expected_like is None
            or typicality < float(expected_like["selection_metric"])
        ):
            multiverse_candidates["expected_like"] = _capture_multiverse_candidate(
                trial_index=trial_index,
                wins=wins,
                points_for=points_for,
                standings=standings,
                champion=champion,
                focal_team=None,
                selection_metric=typicality,
                rarity_metric_value=typicality,
            )

        if league_total_stddev > 0.0:
            upside_distance = abs(league_total - plausible_upside_target)
            upside = multiverse_candidates.get("plausible_upside")
            if (
                upside is None
                or upside_distance < float(upside["selection_metric"])
            ):
                multiverse_candidates["plausible_upside"] = _capture_multiverse_candidate(
                    trial_index=trial_index,
                    wins=wins,
                    points_for=points_for,
                    standings=standings,
                    champion=champion,
                    focal_team=None,
                    selection_metric=upside_distance,
                    rarity_metric_value=league_total,
                )

            downside_distance = abs(league_total - plausible_downside_target)
            downside = multiverse_candidates.get("plausible_downside")
            if (
                downside is None
                or downside_distance < float(downside["selection_metric"])
            ):
                multiverse_candidates["plausible_downside"] = _capture_multiverse_candidate(
                    trial_index=trial_index,
                    wins=wins,
                    points_for=points_for,
                    standings=standings,
                    champion=champion,
                    focal_team=None,
                    selection_metric=downside_distance,
                    rarity_metric_value=league_total,
                )

            extreme = multiverse_candidates.get("extreme_tail")
            if (
                extreme is None
                or typicality > float(extreme["selection_metric"])
            ):
                multiverse_candidates["extreme_tail"] = _capture_multiverse_candidate(
                    trial_index=trial_index,
                    wins=wins,
                    points_for=points_for,
                    standings=standings,
                    champion=champion,
                    focal_team=None,
                    selection_metric=typicality,
                    rarity_metric_value=typicality,
                )

        if trial_biggest_blowout is not None:
            margin, matchup_index, home, away = trial_biggest_blowout
            blowout = multiverse_candidates.get("biggest_blowout")
            if blowout is None or margin > float(blowout["selection_metric"]):
                matchup = request.schedule[matchup_index]
                schedule_row = compiled_schedule[matchup_index]
                multiverse_candidates["biggest_blowout"] = (
                    _capture_multiverse_candidate(
                        trial_index=trial_index,
                        wins=wins,
                        points_for=points_for,
                        standings=standings,
                        champion=champion,
                        focal_team=None,
                        selection_metric=margin,
                        rarity_metric_value=margin,
                        notable_matchup={
                            "week": matchup.week,
                            "home_team_id": matchup.home_team_id,
                            "away_team_id": matchup.away_team_id,
                            "home_points": home,
                            "away_points": away,
                            "margin": margin,
                            "expected_home_points": schedule_row[2],
                            "expected_away_points": schedule_row[4],
                            "expected_underdog_disadvantage": 0.0,
                        },
                    )
                )

        if trial_biggest_upset is not None:
            (
                disadvantage,
                upset_margin,
                matchup_index,
                home,
                away,
            ) = trial_biggest_upset
            upset = multiverse_candidates.get("biggest_upset")
            existing_key = (
                (
                    float(upset["selection_metric"]),
                    float(
                        (upset.get("notable_matchup") or {}).get("margin", 0.0)
                    ),
                )
                if upset is not None
                else None
            )
            if (
                existing_key is None
                or (disadvantage, upset_margin) > existing_key
            ):
                matchup = request.schedule[matchup_index]
                schedule_row = compiled_schedule[matchup_index]
                multiverse_candidates["biggest_upset"] = (
                    _capture_multiverse_candidate(
                        trial_index=trial_index,
                        wins=wins,
                        points_for=points_for,
                        standings=standings,
                        champion=champion,
                        focal_team=None,
                        selection_metric=disadvantage,
                        rarity_metric_value=disadvantage,
                        notable_matchup={
                            "week": matchup.week,
                            "home_team_id": matchup.home_team_id,
                            "away_team_id": matchup.away_team_id,
                            "home_points": home,
                            "away_points": away,
                            "margin": upset_margin,
                            "expected_home_points": schedule_row[2],
                            "expected_away_points": schedule_row[4],
                            "expected_underdog_disadvantage": disadvantage,
                        },
                    )
                )

        if playoff_supported and request.playoff_team_count is not None:
            strongest_rank = standings.index(strongest_expected_team) + 1
            if strongest_rank > request.playoff_team_count:
                strong_team_miss_count += 1
                miss = multiverse_candidates.get("strong_team_misses_playoffs")
                should_replace = (
                    miss is None
                    or strongest_rank > float(miss["selection_metric"])
                    or (
                        strongest_rank == int(float(miss["selection_metric"]))
                        and points_for[strongest_expected_team]
                        < float(tuple(miss["points_for"])[strongest_expected_team])
                    )
                )
                if should_replace:
                    multiverse_candidates["strong_team_misses_playoffs"] = (
                        _capture_multiverse_candidate(
                            trial_index=trial_index,
                            wins=wins,
                            points_for=points_for,
                            standings=standings,
                            champion=champion,
                            focal_team=strongest_expected_team,
                            selection_metric=float(strongest_rank),
                            rarity_metric_value=float(strongest_rank),
                        )
                    )

        if champion is not None:
            champion_seed = standings.index(champion) + 1
            champion_seed_counts[champion_seed] += 1
            low_seed = multiverse_candidates.get("low_seed_champion")
            if (
                low_seed is None
                or champion_seed > float(low_seed["selection_metric"])
            ):
                multiverse_candidates["low_seed_champion"] = (
                    _capture_multiverse_candidate(
                        trial_index=trial_index,
                        wins=wins,
                        points_for=points_for,
                        standings=standings,
                        champion=champion,
                        focal_team=champion,
                        selection_metric=float(champion_seed),
                        rarity_metric_value=float(champion_seed),
                    )
                )

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
        seed_derivation = (
            "pcg64-regular-root-seed-v1;"
            "python-playoff-xor-0x5F3759DF-v1"
        )
    else:
        runtime_version = f"python-{platform.python_version()}"
        bit_generator_name = "python-random-mt19937"
        draw_layout = "trial-major;compiled-schedule-major;home-away-v1"
        seed_derivation = (
            "python-regular-root-seed-v1;"
            "python-playoff-xor-0x5F3759DF-v1"
        )
    future_pick_distributions: tuple[TeamOriginFuturePickDistribution, ...] = ()
    if future_pick_slot_counts is not None and future_pick_policy is not None:
        future_pick_distributions = tuple(
            build_team_origin_future_pick_distribution(
                draft_season=future_pick_policy.draft_season,
                original_team_id=team_id,
                slot_counts=tuple(future_pick_slot_counts[index]),
                simulation_count=n,
                simulation_model_version=request.model_version,
                policy=future_pick_policy,
                draft_order_projection_model_version=(
                    "record-h2h-points-for-plus-playoff-elimination-v1"
                ),
            )
            for index, team_id in enumerate(team_ids)
        )

    simulation_id = hashlib.sha256(
        json.dumps(
            {
                "simulation_input_fingerprint": input_fingerprint,
                "model_version": request.model_version,
                "simulation_count": n,
                "seed": request.seed,
                "rng_protocol": request.rng_protocol,
                "rng_runtime_version": runtime_version,
                "rng_bit_generator": bit_generator_name,
                "rng_batch_size": batch_size,
                "rng_draw_layout": draw_layout,
                "rng_seed_derivation": seed_derivation,
                "multiverse_model_version": "next4-multiverse-v1",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    multiverse_worlds = _build_multiverse_examples(
        candidates=multiverse_candidates,
        team_ids=team_ids,
        playoff_team_count=request.playoff_team_count,
        playoff_supported=playoff_supported,
        championship_supported=championship_supported,
        league_totals=league_totals,
        typicality_values=typicality_values,
        blowout_values=blowout_values,
        upset_values=upset_values,
        strong_team_miss_count=strong_team_miss_count,
        champion_seed_counts=champion_seed_counts,
        simulation_count=n,
        simulation_id=simulation_id,
        root_seed=request.seed,
        rng_protocol=request.rng_protocol,
        rng_runtime_version=runtime_version,
        rng_bit_generator=bit_generator_name,
        rng_batch_size=batch_size,
        rng_draw_layout=draw_layout,
        rng_seed_derivation=seed_derivation,
        simulation_input_fingerprint=input_fingerprint,
    )

    result = RegularSeasonSimulationResult(
        outcomes=tuple(outcomes),
        finish_distributions=tuple(finish_distributions),
        future_pick_distributions=future_pick_distributions,
        future_pick_unavailability_reason=future_pick_unavailability_reason,
        multiverse_worlds=multiverse_worlds,
        multiverse_model_version="next4-multiverse-v1",
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
