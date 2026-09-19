from fsffl.team_utility.dispersion_diagnostics import build_scoring_dispersion_diagnostic
from fsffl.team_utility.simulation import (
    RegularSeasonSimulationResult,
    TeamCompetitiveOutcome,
    WeeklyTeamScoringDistribution,
)


def _weekly(team_id: str, mean: float, stddev: float) -> tuple[WeeklyTeamScoringDistribution, ...]:
    return tuple(
        WeeklyTeamScoringDistribution(
            week=week,
            team_id=team_id,
            mean_points=mean,
            stddev_points=stddev,
            model_version="test-weekly",
        )
        for week in range(1, 4)
    )


def _outcome(team_id: str, expected_wins: float) -> TeamCompetitiveOutcome:
    return TeamCompetitiveOutcome(
        team_id=team_id,
        expected_wins=expected_wins,
        wins_stddev=1.0,
        playoff_probability=0.5,
        first_place_probability=0.2,
        simulation_count=50_000,
        simulation_model_version="test-sim",
    )


def _simulation(outcomes: tuple[TeamCompetitiveOutcome, ...]) -> RegularSeasonSimulationResult:
    return RegularSeasonSimulationResult(
        outcomes=outcomes,
        simulation_count=50_000,
        seed=1,
        model_version="test-sim",
    )


def test_dispersion_diagnostic_separates_mean_signal_from_weekly_noise() -> None:
    weekly = _weekly("bad", 100.0, 30.0) + _weekly("mid", 120.0, 30.0) + _weekly("great", 140.0, 30.0)
    result = build_scoring_dispersion_diagnostic(
        weekly,
        _simulation((_outcome("bad", 4.5), _outcome("mid", 7.0), _outcome("great", 9.5))),
    )

    assert result.league_average_weekly_mean == 120.0
    assert result.best_worst_weekly_mean_spread == 40.0
    assert result.best_worst_expected_win_spread == 5.0
    assert result.between_team_mean_stddev > 0.0
    assert result.median_within_team_weekly_stddev == 30.0
    assert result.signal_to_noise_ratio == result.between_team_mean_stddev / 30.0
    rows = {row.team_id: row for row in result.teams}
    assert rows["great"].neutral_opponent_win_probability > 0.5
    assert rows["bad"].neutral_opponent_win_probability < 0.5


def test_more_weekly_noise_reduces_neutral_opponent_separation_without_changing_means() -> None:
    low_noise = build_scoring_dispersion_diagnostic(
        _weekly("bad", 100.0, 15.0) + _weekly("great", 140.0, 15.0),
        _simulation((_outcome("bad", 5.0), _outcome("great", 9.0))),
    )
    high_noise = build_scoring_dispersion_diagnostic(
        _weekly("bad", 100.0, 45.0) + _weekly("great", 140.0, 45.0),
        _simulation((_outcome("bad", 5.0), _outcome("great", 9.0))),
    )

    low = {row.team_id: row for row in low_noise.teams}
    high = {row.team_id: row for row in high_noise.teams}
    assert low_noise.best_worst_weekly_mean_spread == high_noise.best_worst_weekly_mean_spread
    assert low["great"].neutral_opponent_win_probability > high["great"].neutral_opponent_win_probability
    assert low_noise.signal_to_noise_ratio > high_noise.signal_to_noise_ratio


def test_dispersion_diagnostic_rejects_mismatched_simulation_team_set() -> None:
    weekly = _weekly("a", 100.0, 20.0)
    simulation = _simulation((_outcome("b", 7.0),))
    try:
        build_scoring_dispersion_diagnostic(weekly, simulation)
    except ValueError as exc:
        assert "must match exactly" in str(exc)
    else:
        raise AssertionError("expected mismatched team sets to fail closed")
