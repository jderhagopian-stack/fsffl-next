import pytest

from fsffl.team_utility.simulation import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    simulate_regular_season,
)


def test_regular_season_simulation_retains_exact_finish_rank_distribution() -> None:
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(
                team_id="team:a",
                mean_points=100.0,
                stddev_points=0.0,
                model_version="test-scoring-v1",
            ),
            TeamScoringDistribution(
                team_id="team:b",
                mean_points=50.0,
                stddev_points=0.0,
                model_version="test-scoring-v1",
            ),
        ),
        schedule=(
            ScheduledMatchup(week=1, home_team_id="team:a", away_team_id="team:b"),
        ),
        playoff_team_count=1,
        simulation_count=100,
        seed=7,
        model_version="test-simulation-v1",
    )

    result = simulate_regular_season(request)
    by_team = {row.team_id: row for row in result.finish_distributions}

    assert by_team["team:a"].rank_probabilities == (1.0, 0.0)
    assert by_team["team:a"].expected_finish == pytest.approx(1.0)
    assert by_team["team:b"].rank_probabilities == (0.0, 1.0)
    assert by_team["team:b"].expected_finish == pytest.approx(2.0)
    assert all(sum(row.rank_probabilities) == pytest.approx(1.0) for row in by_team.values())


def test_finish_distribution_is_regular_season_rank_not_automatic_draft_order() -> None:
    source = __import__("pathlib").Path("src/fsffl/team_utility/simulation.py").read_text()
    assert "does not infer rookie" in source
    assert "Draft-order interpretation belongs to a downstream governed pick" in source
    assert "finish_count[team_idx][rank_index]" in source
