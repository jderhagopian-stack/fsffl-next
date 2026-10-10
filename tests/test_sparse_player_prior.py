from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.forecast.sparse_player_prior import (
    HistoricalOutcome,
    HistoricalSparsePlayerPrior,
    PriorCalibrationCase,
    RollingConformalPriorCalibrator,
    SparsePlayerProfile,
    SparsePriorAuthorityError,
    to_forecast_observation,
)


def _outcome(
    player: int,
    *,
    position: str = "WR",
    season: int = 2024,
    points: float | None = None,
    age: float | None = 24.0,
    experience: int | None = 0,
    observed_at: datetime | None = None,
    scoring_coordinate: str = "standard_non_ppr",
) -> HistoricalOutcome:
    return HistoricalOutcome(
        player_id=f"nflverse:{player}",
        position=position,
        season=season,
        age_years=age,
        experience_years=experience,
        fantasy_points=float(player if points is None else points),
        scoring_coordinate=scoring_coordinate,
        observed_at=observed_at or datetime(2025, 2, 1, tzinfo=UTC),
    )


def _profile(
    *,
    player_id: str = "sleeper:rookie-001",
    position: str = "WR",
    evaluation_season: int = 2026,
    as_of: datetime = datetime(2026, 8, 1, tzinfo=UTC),
    age: float | None = 24.0,
    experience: int | None = 0,
) -> SparsePlayerProfile:
    return SparsePlayerProfile(
        player_id=player_id,
        position=position,
        evaluation_season=evaluation_season,
        as_of=as_of,
        age_years=age,
        experience_years=experience,
    )


def test_sparse_rookie_uses_empirical_position_age_experience_prior() -> None:
    history = [
        _outcome(index, points=float(index % 81), age=24.0, experience=0)
        for index in range(100)
    ]
    prior = HistoricalSparsePlayerPrior(history)

    result = prior.forecast(_profile())

    assert result.player_id == "sleeper:rookie-001"
    assert result.evidence_tier == "position_age_experience"
    assert result.sample_count == 100
    assert result.training_season_max == 2024
    assert result.mean == pytest.approx(sum(row.fantasy_points for row in history) / 100)
    assert result.p10 <= result.p25 <= result.p50 <= result.p75 <= result.p90
    assert result.stddev > 0



def test_missing_features_back_off_to_position_history_without_zero_imputation() -> None:
    history = [
        _outcome(index, points=(0.0 if index == 0 else float(index)), age=None, experience=None)
        for index in range(100)
    ]
    prior = HistoricalSparsePlayerPrior(history)

    result = prior.forecast(_profile(age=None, experience=None))

    assert result.evidence_tier == "position"
    assert result.sample_count == 100
    assert result.p10 > 0
    assert result.mean == pytest.approx(sum(row.fantasy_points for row in history) / 100)


def test_future_seasons_and_late_observations_are_excluded() -> None:
    history = [
        *[_outcome(index, season=2024, points=30.0) for index in range(100)],
        *[_outcome(index + 1000, season=2026, points=9000.0) for index in range(100)],
    ]
    prior = HistoricalSparsePlayerPrior(history)

    result = prior.forecast(_profile())

    assert result.training_season_max == 2024
    assert result.mean == pytest.approx(30.0)
    with pytest.raises(SparsePriorAuthorityError):
        prior.forecast(_profile(as_of=datetime(2025, 1, 1, tzinfo=UTC)))


def test_point_in_time_observation_cutoff_can_return_authority_failure() -> None:
    history = [
        _outcome(
            index,
            season=2024,
            points=20.0,
            observed_at=datetime(2025, 2, 1, tzinfo=UTC),
        )
        for index in range(99)
    ]
    prior = HistoricalSparsePlayerPrior(history)

    with pytest.raises(SparsePriorAuthorityError) as error:
        prior.forecast(_profile(as_of=datetime(2025, 1, 1, tzinfo=UTC)))

    assert error.value.reason == "insufficient_point_in_time_history"
    assert error.value.player_id == "sleeper:rookie-001"


def test_prior_rejects_invalid_identity_position_coordinate_and_duplicate_rows() -> None:
    with pytest.raises(SparsePriorAuthorityError, match="canonical_identity_missing"):
        HistoricalSparsePlayerPrior([]).forecast(_profile(player_id=" "))
    with pytest.raises(SparsePriorAuthorityError, match="unsupported_position"):
        HistoricalSparsePlayerPrior([]).forecast(_profile(position="K"))
    with pytest.raises(SparsePriorAuthorityError, match="invalid_age"):
        HistoricalSparsePlayerPrior([]).forecast(_profile(age=-1))
    with pytest.raises(ValueError, match="standard_non_ppr"):
        HistoricalSparsePlayerPrior(
            [_outcome(1, position="QB", scoring_coordinate="connected_league")]
        )
    with pytest.raises(ValueError, match="duplicate historical player-season"):
        HistoricalSparsePlayerPrior([_outcome(1), _outcome(1)])


def test_forecast_adapter_rejects_mismatched_canonical_identity() -> None:
    history = [_outcome(index, points=float(index), age=24.0, experience=0) for index in range(100)]
    prior = HistoricalSparsePlayerPrior(history)
    result = prior.forecast(_profile())

    with pytest.raises(ValueError, match="identity mismatch"):
        to_forecast_observation(
            _profile(player_id="sleeper:wrong-player"),
            result,
            period_start=datetime(2026, 9, 1, tzinfo=UTC),
            period_end=datetime(2027, 1, 4, tzinfo=UTC),
        )


def test_rolling_conformal_calibration_corrects_intervals_and_preserves_pit() -> None:
    history = [
        _outcome(index, points=float(index % 61), age=24.0, experience=0)
        for index in range(100)
    ]
    profile = _profile()
    base = HistoricalSparsePlayerPrior(history).forecast(profile)
    calibration_cases = [
        PriorCalibrationCase(
            position="WR",
            evidence_tier="position_age_experience",
            evaluation_season=2024,
            observed_at=datetime(2025, 2, 1, tzinfo=UTC),
            actual=300.0,
            p10=10.0,
            p25=20.0,
            p75=40.0,
            p90=50.0,
        )
        for _ in range(100)
    ]
    # These later-fold cases cannot contribute to a 2026 forecast calibration.
    calibration_cases.extend(
        PriorCalibrationCase(
            position="WR",
            evidence_tier="position_age_experience",
            evaluation_season=2026,
            observed_at=datetime(2027, 2, 1, tzinfo=UTC),
            actual=-500.0,
            p10=-10.0,
            p25=0.0,
            p75=10.0,
            p90=20.0,
        )
        for _ in range(100)
    )
    calibrated = RollingConformalPriorCalibrator(calibration_cases).calibrate(
        base, as_of=profile.as_of
    )

    assert calibrated.calibration_status == "rolling_conformal"
    assert calibrated.calibration_sample_count == 100
    assert calibrated.calibration_observed_through == datetime(2025, 2, 1, tzinfo=UTC)
    assert calibrated.p10 < base.p10
    assert calibrated.p25 < base.p25
    assert calibrated.p50 == base.p50
    assert calibrated.p75 > base.p75
    assert calibrated.p90 > base.p90
    assert calibrated.p10 <= calibrated.p25 <= calibrated.p50 <= calibrated.p75 <= calibrated.p90
    observation = to_forecast_observation(
        profile,
        calibrated,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 4, tzinfo=UTC),
    )
    assert observation.provenance.effective_at == datetime(2025, 2, 1, tzinfo=UTC)


def test_uncalibrated_prior_cannot_be_published_as_a_forecast_observation() -> None:
    history = [_outcome(index, points=float(index), age=24.0, experience=0) for index in range(100)]
    profile = _profile()
    base = HistoricalSparsePlayerPrior(history).forecast(profile)

    with pytest.raises(ValueError, match="has not passed rolling conformal calibration"):
        to_forecast_observation(
            profile,
            base,
            period_start=datetime(2026, 9, 1, tzinfo=UTC),
            period_end=datetime(2027, 1, 4, tzinfo=UTC),
        )


def test_underpowered_position_pool_fails_explicitly_instead_of_fabricating_a_value() -> None:
    prior = HistoricalSparsePlayerPrior([_outcome(index) for index in range(99)])

    with pytest.raises(SparsePriorAuthorityError) as error:
        prior.forecast(_profile())

    assert error.value.reason == "insufficient_point_in_time_history"
