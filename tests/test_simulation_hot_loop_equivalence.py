from collections import defaultdict
from math import sqrt
from random import Random

from fsffl.team_utility import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    simulate_regular_season,
)


def _reference(request: RegularSeasonSimulationInput):
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
            home = max(0.0, home_dist.mean_points if home_dist.stddev_points == 0 else rng.gauss(home_dist.mean_points, home_dist.stddev_points))
            away = max(0.0, away_dist.mean_points if away_dist.stddev_points == 0 else rng.gauss(away_dist.mean_points, away_dist.stddev_points))
            points_for[matchup.home_team_id] += home
            points_for[matchup.away_team_id] += away
            if home > away:
                wins[matchup.home_team_id] += 1.0
            elif away > home:
                wins[matchup.away_team_id] += 1.0
            else:
                wins[matchup.home_team_id] += 0.5
                wins[matchup.away_team_id] += 0.5
        standings = sorted(team_ids, key=lambda team_id: (-wins[team_id], -points_for[team_id], team_id))
        playoff_teams = set(standings[: request.playoff_team_count])
        first_count[standings[0]] += 1
        for team_id in team_ids:
            value = wins[team_id]
            wins_sum[team_id] += value
            wins_sq_sum[team_id] += value * value
            if team_id in playoff_teams:
                playoff_count[team_id] += 1

    n = request.simulation_count
    return {
        team_id: (
            wins_sum[team_id] / n,
            sqrt(max(0.0, wins_sq_sum[team_id] / n - (wins_sum[team_id] / n) ** 2)),
            playoff_count[team_id] / n,
            first_count[team_id] / n,
        )
        for team_id in team_ids
    }


def test_optimized_hot_loop_is_exactly_equivalent_to_reference_rng_and_standings() -> None:
    team_ids = ("a", "b", "c", "d")
    schedule = (
        ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),
        ScheduledMatchup(week=1, home_team_id="c", away_team_id="d"),
        ScheduledMatchup(week=2, home_team_id="a", away_team_id="c"),
        ScheduledMatchup(week=2, home_team_id="b", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="a", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="b", away_team_id="c"),
    )
    weekly = tuple(
        WeeklyTeamScoringDistribution(
            week=week,
            team_id=team_id,
            mean_points=110.0 + index * 7.0 + week,
            stddev_points=12.0 + index,
            model_version="weekly-v1",
        )
        for week in (1, 2, 3)
        for index, team_id in enumerate(team_ids)
    )
    request = RegularSeasonSimulationInput(
        weekly_scoring=weekly,
        schedule=schedule,
        playoff_team_count=2,
        simulation_count=2_000,
        seed=987654,
        model_version="equivalence-v1",
    )

    expected = _reference(request)
    actual = {row.team_id: row for row in simulate_regular_season(request).outcomes}
    for team_id, reference in expected.items():
        row = actual[team_id]
        assert (
            row.expected_wins,
            row.wins_stddev,
            row.playoff_probability,
            row.first_place_probability,
        ) == reference


def test_optimized_hot_loop_preserves_zero_variance_rng_behavior() -> None:
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(team_id="a", mean_points=120, stddev_points=0, model_version="v1"),
            TeamScoringDistribution(team_id="b", mean_points=120, stddev_points=0, model_version="v1"),
        ),
        schedule=(ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),),
        playoff_team_count=1,
        simulation_count=50,
        seed=22,
        model_version="zero-variance-v1",
    )
    assert _reference(request) == {
        row.team_id: (
            row.expected_wins,
            row.wins_stddev,
            row.playoff_probability,
            row.first_place_probability,
        )
        for row in simulate_regular_season(request).outcomes
    }
