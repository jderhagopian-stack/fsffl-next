import pytest

from fsffl.team_utility import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    simulate_regular_season,
)


def test_regular_season_simulation_is_reproducible_and_orders_stronger_team() -> None:
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(
                team_id="strong",
                mean_points=140.0,
                stddev_points=10.0,
                model_version="team-score-v1",
            ),
            TeamScoringDistribution(
                team_id="weak",
                mean_points=105.0,
                stddev_points=10.0,
                model_version="team-score-v1",
            ),
        ),
        schedule=tuple(
            ScheduledMatchup(week=week, home_team_id="strong", away_team_id="weak")
            for week in range(1, 15)
        ),
        playoff_team_count=1,
        simulation_count=5_000,
        seed=42,
        model_version="regular-season-v1",
    )

    left = simulate_regular_season(request)
    right = simulate_regular_season(request)

    assert left == right
    by_team = {row.team_id: row for row in left.outcomes}
    assert by_team["strong"].expected_wins > by_team["weak"].expected_wins
    assert by_team["strong"].playoff_probability > 0.95
    assert by_team["strong"].first_place_probability == by_team["strong"].playoff_probability


def test_regular_season_simulation_rejects_duplicate_team_in_week() -> None:
    with pytest.raises(ValueError, match="only once per scheduled week"):
        RegularSeasonSimulationInput(
            scoring=(
                TeamScoringDistribution(
                    team_id="a", mean_points=100, stddev_points=10, model_version="v1"
                ),
                TeamScoringDistribution(
                    team_id="b", mean_points=100, stddev_points=10, model_version="v1"
                ),
                TeamScoringDistribution(
                    team_id="c", mean_points=100, stddev_points=10, model_version="v1"
                ),
            ),
            schedule=(
                ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),
                ScheduledMatchup(week=1, home_team_id="a", away_team_id="c"),
            ),
            playoff_team_count=2,
            simulation_count=100,
            model_version="v1",
        )


def test_equal_deterministic_teams_split_tied_matchup_wins() -> None:
    result = simulate_regular_season(
        RegularSeasonSimulationInput(
            scoring=(
                TeamScoringDistribution(
                    team_id="a", mean_points=120, stddev_points=0, model_version="v1"
                ),
                TeamScoringDistribution(
                    team_id="b", mean_points=120, stddev_points=0, model_version="v1"
                ),
            ),
            schedule=(ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),),
            playoff_team_count=1,
            simulation_count=10,
            seed=1,
            model_version="v1",
        )
    )
    by_team = {row.team_id: row for row in result.outcomes}
    assert by_team["a"].expected_wins == 0.5
    assert by_team["b"].expected_wins == 0.5
