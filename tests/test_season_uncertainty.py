from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.forecast.season_uncertainty import (
    SEASON_FANTASY_POINT_ERROR_CALIBRATION,
    apply_empirical_season_fantasy_point_uncertainty,
)
from fsffl.state.models import Position, Provenance


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def observation(*, position: Position, mean: float, stddev: float, horizon: ForecastHorizon = ForecastHorizon.SEASON) -> ForecastObservation:
    return ForecastObservation(
        player_id=f"player:{position.value}",
        position=position,
        horizon=horizon,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=180),
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v2",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def test_empirical_uncertainty_floors_provider_disagreement() -> None:
    base = observation(position=Position.QB, mean=400.0, stddev=10.0)
    result = apply_empirical_season_fantasy_point_uncertainty((base,))[0]
    expected = 400.0 * SEASON_FANTASY_POINT_ERROR_CALIBRATION[Position.QB].relative_rmse
    assert result.distribution.mean == 400.0
    assert result.distribution.stddev == pytest.approx(expected)
    assert "next2-live-season-fp-uncertainty-v1" in result.model_version


def test_empirical_uncertainty_never_shrinks_larger_live_dispersion() -> None:
    base = observation(position=Position.WR, mean=200.0, stddev=150.0)
    result = apply_empirical_season_fantasy_point_uncertainty((base,))[0]
    assert result.distribution.stddev == 150.0


def test_empirical_uncertainty_is_position_specific_and_evidence_versioned() -> None:
    assert SEASON_FANTASY_POINT_ERROR_CALIBRATION[Position.RB].sample_size == 250
    assert SEASON_FANTASY_POINT_ERROR_CALIBRATION[Position.WR].sample_size == 378
    assert SEASON_FANTASY_POINT_ERROR_CALIBRATION[Position.TE].seasons == (2024, 2025)
    assert SEASON_FANTASY_POINT_ERROR_CALIBRATION[Position.QB].evidence_workflow_run == 33958374013


def test_empirical_uncertainty_refuses_nonseason_forecasts() -> None:
    weekly = observation(position=Position.QB, mean=20.0, stddev=5.0, horizon=ForecastHorizon.WEEK)
    with pytest.raises(ValueError, match="SEASON horizon"):
        apply_empirical_season_fantasy_point_uncertainty((weekly,))
