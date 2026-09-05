from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from math import sqrt
from random import Random
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueState


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


class RegularSeasonSimulationInput(FrozenModel):
    scoring: tuple[TeamScoringDistribution, ...] = ()
    weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = ()
    schedule: tuple[ScheduledMatchup, ...]
    playoff_team_count: Annotated[int, Field(ge=1)]
    simulation_count: Annotated[int, Field(ge=1)] = 50_000
    seed: int = 20260905
    model_version: str

    @model_validator(mode="after")
    def validate_input(self) -> "RegularSeasonSimulationInput":
        if not self.model_version.strip():
            raise ValueError("simulation model_version cannot be blank")
        ids = [item.team_id for item in self.scoring]
        if len(ids) != len(set(ids)):
            raise ValueError("team scoring distributions must have unique team ids")
        weekly_keys = [(item.week, item.team_id) for item in self.weekly_scoring]
        if len(weekly_keys) != len(set(weekly_keys)):
            raise ValueError("weekly team scoring distributions must have unique week/team keys")

        known = set(ids) | {item.team_id for item in self.weekly_scoring}
        if not known:
            raise ValueError("simulation requires at least one team")
        if self.playoff_team_count > len(known):
            raise ValueError("playoff_team_count cannot exceed team count")
        for matchup in self.schedule:
            if matchup.home_team_id not in known or matchup.away_team_id not in known:
                raise ValueError("schedule references unknown team")
        seen_week_team: set[tuple[int, str]] = set()
        required_weekly: set[tuple[int, str]] = set()
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
        if not self.weekly_scoring and set(ids) != known:
            raise ValueError("constant scoring requires one distribution per known team")
        return self


class TeamCompetitiveOutcome(FrozenModel):
    team_id: str
    expected_wins: float
    wins_stddev: Annotated[float, Field(ge=0)]
    playoff_probability: Annotated[float, Field(ge=0, le=1)]
    first_place_probability: Annotated[float, Field(ge=0, le=1)]
    simulation_count: Annotated[int, Field(ge=1)]
    simulation_model_version: str


class RegularSeasonSimulationResult(FrozenModel):
    outcomes: tuple[TeamCompetitiveOutcome, ...]
    simulation_count: Annotated[int, Field(ge=1)]
    seed: int
    model_version: str


def scheduled_matchups_from_league_state(
    league_state: LeagueState,
) -> tuple[ScheduledMatchup, ...]:
    """Expose canonical State schedule to Simulation without provider semantics."""

    if not league_state.matchups:
        raise ValueError("canonical league state has no regular-season schedule")
    return tuple(
        ScheduledMatchup(
            week=matchup.week,
            home_team_id=matchup.team_a_id,
            away_team_id=matchup.team_b_id,
        )
        for matchup in league_state.matchups
    )


def regular_season_game_counts(
    league_state: LeagueState,
) -> dict[str, int]:
    """Count scheduled fantasy regular-season games per canonical team."""

    schedule = scheduled_matchups_from_league_state(league_state)
    counts = {team.team_id: 0 for team in league_state.teams}
    for matchup in schedule:
        counts[matchup.home_team_id] += 1
        counts[matchup.away_team_id] += 1
    if any(count < 1 for count in counts.values()):
        missing = sorted(team_id for team_id, count in counts.items() if count < 1)
        raise ValueError(f"regular-season schedule missing teams: {missing}")
    return counts


def build_regular_season_simulation_input(
    league_state: LeagueState,
    *,
    scoring: tuple[TeamScoringDistribution, ...] = (),
    weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...] = (),
    simulation_count: int = 50_000,
    seed: int = 20260905,
    model_version: str = "next4-live-regular-season-v2",
) -> RegularSeasonSimulationInput:
    """Build simulation input only from canonical schedule/rules plus scoring."""

    playoff_team_count = league_state.league.rules.playoff_team_count
    if playoff_team_count is None:
        raise ValueError("canonical league rules do not define playoff_team_count")
    return RegularSeasonSimulationInput(
        scoring=scoring,
        weekly_scoring=weekly_scoring,
        schedule=scheduled_matchups_from_league_state(league_state),
        playoff_team_count=playoff_team_count,
        simulation_count=simulation_count,
        seed=seed,
        model_version=model_version,
    )


def simulate_regular_season(
    request: RegularSeasonSimulationInput,
) -> RegularSeasonSimulationResult:
    """Simulate regular-season competitive outcomes only."""

    by_team = {item.team_id: item for item in request.scoring}
    by_week_team = {(item.week, item.team_id): item for item in request.weekly_scoring}
    team_ids = tuple(sorted(set(by_team) | {item.team_id for item in request.weekly_scoring}))
    rng = Random(request.seed)

    wins_sum = defaultdict(float)
    wins_sq_sum = defaultdict(float)
    playoff_count = defaultdict(int)
    first_count = defaultdict(int)

    for _ in range(request.simulation_count):
        wins = {team_id: 0.0 for team_id in team_ids}
        points_for = {team_id: 0.0 for team_id in team_ids}

        for matchup in request.schedule:
            if by_week_team:
                home_dist = by_week_team[(matchup.week, matchup.home_team_id)]
                away_dist = by_week_team[(matchup.week, matchup.away_team_id)]
            else:
                home_dist = by_team[matchup.home_team_id]
                away_dist = by_team[matchup.away_team_id]
            home = _sample_points(home_dist, rng)
            away = _sample_points(away_dist, rng)
            points_for[matchup.home_team_id] += home
            points_for[matchup.away_team_id] += away
            if home > away:
                wins[matchup.home_team_id] += 1.0
            elif away > home:
                wins[matchup.away_team_id] += 1.0
            else:
                wins[matchup.home_team_id] += 0.5
                wins[matchup.away_team_id] += 0.5

        standings = sorted(
            team_ids,
            key=lambda team_id: (-wins[team_id], -points_for[team_id], team_id),
        )
        playoff_teams = set(standings[: request.playoff_team_count])
        first_team = standings[0]

        for team_id in team_ids:
            value = wins[team_id]
            wins_sum[team_id] += value
            wins_sq_sum[team_id] += value * value
            if team_id in playoff_teams:
                playoff_count[team_id] += 1
        first_count[first_team] += 1

    outcomes: list[TeamCompetitiveOutcome] = []
    n = request.simulation_count
    for team_id in team_ids:
        expected = wins_sum[team_id] / n
        variance = max(0.0, wins_sq_sum[team_id] / n - expected * expected)
        outcomes.append(
            TeamCompetitiveOutcome(
                team_id=team_id,
                expected_wins=expected,
                wins_stddev=sqrt(variance),
                playoff_probability=playoff_count[team_id] / n,
                first_place_probability=first_count[team_id] / n,
                simulation_count=n,
                simulation_model_version=request.model_version,
            )
        )

    return RegularSeasonSimulationResult(
        outcomes=tuple(outcomes),
        simulation_count=n,
        seed=request.seed,
        model_version=request.model_version,
    )


def _sample_points(distribution, rng: Random) -> float:
    if distribution.distribution_kind != ScoringDistributionKind.NORMAL:
        raise ValueError("unsupported scoring distribution kind")
    if distribution.stddev_points == 0:
        return max(0.0, distribution.mean_points)
    return max(0.0, rng.gauss(distribution.mean_points, distribution.stddev_points))
