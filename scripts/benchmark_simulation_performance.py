from __future__ import annotations

from collections import defaultdict
from math import sqrt
from random import Random
from time import perf_counter

from fsffl.team_utility.simulation import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    ScoringDistributionKind,
    TeamCompetitiveOutcome,
    WeeklyTeamScoringDistribution,
    simulate_regular_season,
)


def _schedule(team_count: int = 12, weeks: int = 14) -> tuple[ScheduledMatchup, ...]:
    teams = [f"t{i:02d}" for i in range(team_count)]
    rotation = teams[:]
    rows: list[ScheduledMatchup] = []
    for week in range(1, weeks + 1):
        for i in range(team_count // 2):
            rows.append(
                ScheduledMatchup(
                    week=week,
                    home_team_id=rotation[i],
                    away_team_id=rotation[-1 - i],
                )
            )
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return tuple(rows)


def _request(simulation_count: int = 50_000) -> RegularSeasonSimulationInput:
    schedule = _schedule()
    scoring: list[WeeklyTeamScoringDistribution] = []
    for matchup in schedule:
        for team_id in (matchup.home_team_id, matchup.away_team_id):
            index = int(team_id[1:])
            scoring.append(
                WeeklyTeamScoringDistribution(
                    week=matchup.week,
                    team_id=team_id,
                    mean_points=105.0 + index * 3.0 + (matchup.week % 4),
                    stddev_points=18.0 + (index % 5) * 2.0,
                    model_version="benchmark-weekly-v1",
                )
            )
    return RegularSeasonSimulationInput(
        weekly_scoring=tuple(scoring),
        schedule=schedule,
        playoff_team_count=6,
        simulation_count=simulation_count,
        seed=20260905,
        model_version="benchmark-v1",
    )


def _reference(request: RegularSeasonSimulationInput):
    by_week_team = {(item.week, item.team_id): item for item in request.weekly_scoring}
    team_ids = tuple(sorted({item.team_id for item in request.weekly_scoring}))
    rng = Random(request.seed)
    wins_sum = defaultdict(float)
    wins_sq_sum = defaultdict(float)
    playoff_count = defaultdict(int)
    first_count = defaultdict(int)

    for _ in range(request.simulation_count):
        wins = {team_id: 0.0 for team_id in team_ids}
        points_for = {team_id: 0.0 for team_id in team_ids}
        for matchup in request.schedule:
            home_dist = by_week_team[(matchup.week, matchup.home_team_id)]
            away_dist = by_week_team[(matchup.week, matchup.away_team_id)]
            if home_dist.distribution_kind != ScoringDistributionKind.NORMAL:
                raise ValueError("unsupported scoring distribution kind")
            if away_dist.distribution_kind != ScoringDistributionKind.NORMAL:
                raise ValueError("unsupported scoring distribution kind")
            home = max(0.0, rng.gauss(home_dist.mean_points, home_dist.stddev_points))
            away = max(0.0, rng.gauss(away_dist.mean_points, away_dist.stddev_points))
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
    outcomes = []
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
    return tuple(outcomes)


def main() -> None:
    request = _request()

    start = perf_counter()
    reference = _reference(request)
    reference_seconds = perf_counter() - start

    start = perf_counter()
    optimized = simulate_regular_season(request)
    optimized_seconds = perf_counter() - start

    if reference != optimized.outcomes:
        raise SystemExit("optimized simulator output differs from reference implementation")

    speedup = reference_seconds / optimized_seconds
    reduction = 1.0 - (optimized_seconds / reference_seconds)
    print(f"simulation_count={request.simulation_count}")
    print(f"teams=12 weeks=14 games={len(request.schedule)}")
    print(f"reference_seconds={reference_seconds:.6f}")
    print(f"optimized_seconds={optimized_seconds:.6f}")
    print(f"speedup={speedup:.3f}x")
    print(f"runtime_reduction={reduction:.1%}")
    print("outputs_exactly_equal=true")


if __name__ == "__main__":
    main()
