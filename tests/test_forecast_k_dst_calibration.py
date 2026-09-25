from __future__ import annotations

import pytest

from fsffl.forecast.k_dst_calibration import (
    KDstCalibrationSample,
    WeeklyRealizedScore,
    fit_k_dst_season_error,
    fit_k_dst_weekly_volatility,
)


def test_season_error_harness_enforces_two_source_gate() -> None:
    samples = (
        KDstCalibrationSample(
            subject_key="K:k1",
            season=2024,
            projected_points=140,
            realized_points=120,
            independent_source_count=1,
        ),
        KDstCalibrationSample(
            subject_key="K:k2",
            season=2024,
            projected_points=150,
            realized_points=160,
            independent_source_count=2,
        ),
    )

    result = fit_k_dst_season_error(samples)

    assert result.sample_size == 1
    assert result.seasons == (2024,)
    assert result.relative_rmse == pytest.approx(10 / 150)


def test_weekly_volatility_uses_realized_games_not_season_mean_division() -> None:
    scores = (
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=1, points=4),
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=2, points=10),
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=3, points=7),
        WeeklyRealizedScore(subject_key="DST:BUF", season=2024, week=1, points=8),
        WeeklyRealizedScore(subject_key="DST:BUF", season=2024, week=2, points=2),
    )

    result = fit_k_dst_weekly_volatility(scores)

    assert result.observation_count == 5
    assert result.subject_count == 2
    assert result.pooled_coefficient_of_variation > 0


def test_weekly_volatility_fails_closed_without_repeated_game_evidence() -> None:
    with pytest.raises(ValueError, match="two games"):
        fit_k_dst_weekly_volatility(
            (
                WeeklyRealizedScore(
                    subject_key="K:k1",
                    season=2024,
                    week=1,
                    points=10,
                ),
            )
        )
