from math import sqrt

from fsffl.forecast.weekly_volatility import active_game_distribution
from fsffl.state.models import Position
from fsffl.team_utility.simulation import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    WeeklyTeamScoringDistribution,
    simulate_regular_season,
)


def _team_distribution(week: int, team_id: str, players: tuple[tuple[Position, float], ...]):
    means = []
    variances = []
    for position, season_mean in players:
        mean, stddev = active_game_distribution(
            season_mean=season_mean,
            position=position,
        )
        means.append(mean)
        variances.append(stddev**2)
    return WeeklyTeamScoringDistribution(
        week=week,
        team_id=team_id,
        mean_points=sum(means),
        stddev_points=sqrt(sum(variances)),
        model_version="test:empirical-weekly-volatility",
    )


def test_empirical_weekly_volatility_preserves_obvious_team_separation() -> None:
    """A juggernaut and intentional-tanker profile must not collapse toward .500.

    This is a structural sanity regression, not a target for any real FSFFL team.
    It protects against reintroducing season forecast-error uncertainty as weekly
    scoring variance, the defect that compressed the live beta standings.
    """

    juggernaut = (
        (Position.QB, 360.0),
        (Position.RB, 240.0),
        (Position.RB, 220.0),
        (Position.WR, 260.0),
        (Position.WR, 240.0),
        (Position.WR, 220.0),
        (Position.TE, 180.0),
        (Position.WR, 210.0),
        (Position.QB, 320.0),
    )
    tanker = (
        (Position.QB, 180.0),
        (Position.RB, 100.0),
        (Position.RB, 90.0),
        (Position.WR, 100.0),
        (Position.WR, 90.0),
        (Position.WR, 80.0),
        (Position.TE, 80.0),
        (Position.WR, 80.0),
        (Position.QB, 150.0),
    )

    weeks = tuple(range(1, 15))
    weekly_scoring = tuple(
        distribution
        for week in weeks
        for distribution in (
            _team_distribution(week, "juggernaut", juggernaut),
            _team_distribution(week, "tanker", tanker),
        )
    )
    schedule = tuple(
        ScheduledMatchup(
            week=week,
            home_team_id="juggernaut",
            away_team_id="tanker",
        )
        for week in weeks
    )

    result = simulate_regular_season(
        RegularSeasonSimulationInput(
            weekly_scoring=weekly_scoring,
            schedule=schedule,
            playoff_team_count=1,
            simulation_count=5_000,
            seed=20260906,
            model_version="test:weekly-volatility-separation",
        )
    )
    outcomes = {item.team_id: item for item in result.outcomes}

    assert outcomes["juggernaut"].expected_wins > 11.5
    assert outcomes["tanker"].expected_wins < 2.5
    assert outcomes["juggernaut"].expected_wins - outcomes["tanker"].expected_wins > 9.0
