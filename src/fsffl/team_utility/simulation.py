from __future__ import annotations

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
        if self.playoff_team_count not in {2, 4, 6, 8}:
            raise ValueError("championship simulation currently supports 2, 4, 6, or 8 playoff teams")
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
        return self


class TeamCompetitiveOutcome(FrozenModel):
    team_id: str
    expected_wins: float
    wins_stddev: Annotated[float, Field(ge=0)]
    playoff_probability: Annotated[float, Field(ge=0, le=1)]
    first_place_probability: Annotated[float, Field(ge=0, le=1)]
    championship_probability: Annotated[float, Field(ge=0, le=1)] = 0.0
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
    model_version: str = "next4-live-season-plus-playoffs-v1",
) -> RegularSeasonSimulationInput:
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


def _playoff_distributions(
    team_ids: tuple[str, ...],
    scoring: dict[str, TeamScoringDistribution],
    weekly_scoring: dict[tuple[int, str], WeeklyTeamScoringDistribution],
) -> tuple[tuple[float, float], ...]:
    if scoring:
        return tuple((scoring[team_id].mean_points, scoring[team_id].stddev_points) for team_id in team_ids)
    by_team: dict[str, list[WeeklyTeamScoringDistribution]] = {team_id: [] for team_id in team_ids}
    for item in weekly_scoring.values():
        by_team[item.team_id].append(item)
    result: list[tuple[float, float]] = []
    for team_id in team_ids:
        rows = by_team[team_id]
        if not rows:
            raise ValueError(f"playoff scoring evidence unavailable for {team_id}")
        mean = sum(item.mean_points for item in rows) / len(rows)
        variance = sum(item.stddev_points * item.stddev_points for item in rows) / len(rows)
        result.append((mean, sqrt(max(0.0, variance))))
    return tuple(result)


def _playoff_game(
    left: tuple[int, int],
    right: tuple[int, int],
    playoff_scoring: tuple[tuple[float, float], ...],
    gauss,
) -> tuple[int, int]:
    left_idx, left_seed = left
    right_idx, right_seed = right
    left_mean, left_std = playoff_scoring[left_idx]
    right_mean, right_std = playoff_scoring[right_idx]
    left_points = left_mean if left_std == 0 else max(0.0, gauss(left_mean, left_std))
    right_points = right_mean if right_std == 0 else max(0.0, gauss(right_mean, right_std))
    if left_points > right_points:
        return left
    if right_points > left_points:
        return right
    return left if left_seed < right_seed else right


def _simulate_standard_champion(
    standings: list[int],
    playoff_team_count: int,
    playoff_scoring: tuple[tuple[float, float], ...],
    gauss,
) -> int:
    seeded = [(standings[seed - 1], seed) for seed in range(1, playoff_team_count + 1)]
    if playoff_team_count == 2:
        return _playoff_game(seeded[0], seeded[1], playoff_scoring, gauss)[0]
    if playoff_team_count == 4:
        semi_a = _playoff_game(seeded[0], seeded[3], playoff_scoring, gauss)
        semi_b = _playoff_game(seeded[1], seeded[2], playoff_scoring, gauss)
        return _playoff_game(semi_a, semi_b, playoff_scoring, gauss)[0]
    if playoff_team_count == 6:
        # Sleeper's documented standard six-team winners bracket: 3v6 feeds seed 1;
        # 4v5 feeds seed 2. This is the no-reseed bracket topology.
        round1_a = _playoff_game(seeded[2], seeded[5], playoff_scoring, gauss)
        round1_b = _playoff_game(seeded[3], seeded[4], playoff_scoring, gauss)
        semi_a = _playoff_game(seeded[0], round1_a, playoff_scoring, gauss)
        semi_b = _playoff_game(seeded[1], round1_b, playoff_scoring, gauss)
        return _playoff_game(semi_a, semi_b, playoff_scoring, gauss)[0]
    # Standard eight-team fixed bracket: 1v8 and 4v5 share a semifinal path;
    # 2v7 and 3v6 share the other path.
    q1 = _playoff_game(seeded[0], seeded[7], playoff_scoring, gauss)
    q2 = _playoff_game(seeded[3], seeded[4], playoff_scoring, gauss)
    q3 = _playoff_game(seeded[1], seeded[6], playoff_scoring, gauss)
    q4 = _playoff_game(seeded[2], seeded[5], playoff_scoring, gauss)
    semi_a = _playoff_game(q1, q2, playoff_scoring, gauss)
    semi_b = _playoff_game(q3, q4, playoff_scoring, gauss)
    return _playoff_game(semi_a, semi_b, playoff_scoring, gauss)[0]


def simulate_regular_season(
    request: RegularSeasonSimulationInput,
) -> RegularSeasonSimulationResult:
    """Simulate regular season plus the standard seeded championship bracket.

    Regular-season schedule, standings, tiebreaks and playoff qualification remain
    canonical. Championship probability is generated inside the same Monte Carlo
    path so seed/qualification correlation is preserved. Postseason team scoring
    uses explicit team scoring input when supplied; otherwise it uses the RMS
    weekly volatility and mean weekly scoring implied by the authoritative weekly
    panel. The bracket topology is versioned in the simulation model rather than
    guessed in Product/Presentation.
    """

    by_team = {item.team_id: item for item in request.scoring}
    by_week_team = {(item.week, item.team_id): item for item in request.weekly_scoring}
    team_ids = tuple(sorted(set(by_team) | {item.team_id for item in request.weekly_scoring}))
    team_index = {team_id: index for index, team_id in enumerate(team_ids)}
    team_count = len(team_ids)
    playoff_scoring = _playoff_distributions(team_ids, by_team, by_week_team)

    compiled_schedule: list[tuple[int, int, float, float, float, float]] = []
    weekly = bool(by_week_team)
    for matchup in request.schedule:
        if weekly:
            home_dist = by_week_team[(matchup.week, matchup.home_team_id)]
            away_dist = by_week_team[(matchup.week, matchup.away_team_id)]
        else:
            home_dist = by_team[matchup.home_team_id]
            away_dist = by_team[matchup.away_team_id]
        if home_dist.distribution_kind != ScoringDistributionKind.NORMAL:
            raise ValueError("unsupported scoring distribution kind")
        if away_dist.distribution_kind != ScoringDistributionKind.NORMAL:
            raise ValueError("unsupported scoring distribution kind")
        compiled_schedule.append(
            (
                team_index[matchup.home_team_id],
                team_index[matchup.away_team_id],
                home_dist.mean_points,
                home_dist.stddev_points,
                away_dist.mean_points,
                away_dist.stddev_points,
            )
        )

    rng = Random(request.seed)
    gauss = rng.gauss
    wins_sum = [0.0] * team_count
    wins_sq_sum = [0.0] * team_count
    playoff_count = [0] * team_count
    first_count = [0] * team_count
    champion_count = [0] * team_count
    ranking_indexes = tuple(range(team_count))
    playoff_team_count = request.playoff_team_count

    for _ in range(request.simulation_count):
        wins = [0.0] * team_count
        points_for = [0.0] * team_count

        for home_idx, away_idx, home_mean, home_stddev, away_mean, away_stddev in compiled_schedule:
            home = home_mean if home_stddev == 0 else gauss(home_mean, home_stddev)
            away = away_mean if away_stddev == 0 else gauss(away_mean, away_stddev)
            if home < 0.0:
                home = 0.0
            if away < 0.0:
                away = 0.0
            points_for[home_idx] += home
            points_for[away_idx] += away
            if home > away:
                wins[home_idx] += 1.0
            elif away > home:
                wins[away_idx] += 1.0
            else:
                wins[home_idx] += 0.5
                wins[away_idx] += 0.5

        standings = sorted(
            ranking_indexes,
            key=lambda index: (-wins[index], -points_for[index], team_ids[index]),
        )
        first_count[standings[0]] += 1
        for index in standings[:playoff_team_count]:
            playoff_count[index] += 1
        champion = _simulate_standard_champion(
            standings,
            playoff_team_count,
            playoff_scoring,
            gauss,
        )
        champion_count[champion] += 1
        for index, value in enumerate(wins):
            wins_sum[index] += value
            wins_sq_sum[index] += value * value

    outcomes: list[TeamCompetitiveOutcome] = []
    n = request.simulation_count
    for index, team_id in enumerate(team_ids):
        expected = wins_sum[index] / n
        variance = max(0.0, wins_sq_sum[index] / n - expected * expected)
        outcomes.append(
            TeamCompetitiveOutcome(
                team_id=team_id,
                expected_wins=expected,
                wins_stddev=sqrt(variance),
                playoff_probability=playoff_count[index] / n,
                first_place_probability=first_count[index] / n,
                championship_probability=champion_count[index] / n,
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
