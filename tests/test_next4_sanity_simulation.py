from fsffl.team_utility import (
    OwnerStrategicPosture,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    StrategicTeamView,
    TeamScoringDistribution,
    TeamUtilityVector,
    simulate_regular_season,
)
from datetime import UTC, datetime


AS_OF = datetime(2026, 9, 5, 15, 0, tzinfo=UTC)


def _schedule(weeks: int = 14) -> tuple[ScheduledMatchup, ...]:
    return tuple(
        ScheduledMatchup(week=week, home_team_id="team:a", away_team_id="team:b")
        for week in range(1, weeks + 1)
    )


def _simulate(team_a_mean: float, *, seed: int = 12345):
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(
                team_id="team:a",
                mean_points=team_a_mean,
                stddev_points=6.0,
                model_version="sanity-scoring-v1",
            ),
            TeamScoringDistribution(
                team_id="team:b",
                mean_points=20.0,
                stddev_points=6.0,
                model_version="sanity-scoring-v1",
            ),
        ),
        schedule=_schedule(),
        playoff_team_count=1,
        simulation_count=5_000,
        seed=seed,
        model_version="sanity-sim-v1",
    )
    return simulate_regular_season(request)


def _outcome(result, team_id: str):
    return next(item for item in result.outcomes if item.team_id == team_id)


def test_identical_simulation_inputs_and_seed_are_reproducible() -> None:
    first = _simulate(20.0, seed=777)
    second = _simulate(20.0, seed=777)
    assert first == second


def test_stronger_scoring_mean_improves_competitive_outcomes() -> None:
    baseline = _outcome(_simulate(20.0, seed=888), "team:a")
    improved = _outcome(_simulate(25.0, seed=888), "team:a")

    assert improved.expected_wins > baseline.expected_wins
    assert improved.playoff_probability > baseline.playoff_probability
    assert improved.first_place_probability > baseline.first_place_probability


def test_owner_posture_does_not_change_calculated_team_state() -> None:
    outcome = _outcome(_simulate(22.0, seed=999), "team:a")
    calculated = TeamUtilityVector(
        team_id="team:a",
        as_of=AS_OF,
        competitive_outcome=outcome,
        model_version="utility-sanity-v1",
    )

    win_now = StrategicTeamView(
        calculated=calculated,
        owner_posture=OwnerStrategicPosture.WIN_NOW,
    )
    rebuild = StrategicTeamView(
        calculated=calculated,
        owner_posture=OwnerStrategicPosture.REBUILD,
    )

    assert win_now.calculated == rebuild.calculated == calculated
    assert win_now.owner_posture != rebuild.owner_posture
