from datetime import datetime, timedelta, timezone

import pytest

from fsffl.forecast.ensemble import equal_weight_ensemble
from fsffl.forecast.evaluation import score_point_forecast
from fsffl.forecast.models import (
    ForecastBundle,
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


def _observation(source: str, mean: float, stddev: float) -> ForecastObservation:
    as_of = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    return ForecastObservation(
        player_id="player:test-qb",
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=timezone.utc),
        period_end=datetime(2027, 1, 10, tzinfo=timezone.utc),
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source=source,
        model_version="test-v1",
        as_of=as_of,
        provenance=Provenance(
            source=source,
            retrieved_at=as_of,
            effective_at=as_of,
        ),
    )


def test_equal_weight_ensemble_averages_like_for_like_forecasts():
    combined = equal_weight_ensemble(
        (
            _observation("source:a", 300.0, 20.0),
            _observation("source:b", 340.0, 30.0),
        )
    )

    assert len(combined) == 1
    assert combined[0].distribution.mean == 320.0
    assert combined[0].distribution.stddev > 0
    assert combined[0].source == "fsffl:equal_weight"


def test_historical_score_reports_point_error_and_standardized_error():
    score = score_point_forecast(_observation("source:a", 300.0, 20.0), actual=320.0)

    assert score.source == "source:a"
    assert score.absolute_error == 20.0
    assert score.squared_error == 400.0
    assert score.standardized_error == -1.0


def test_zero_uncertainty_does_not_fake_standardized_error():
    score = score_point_forecast(_observation("source:a", 300.0, 0.0), actual=320.0)
    assert score.standardized_error is None


def test_observation_rejects_evidence_that_postdates_as_of():
    base = _observation("source:a", 300.0, 20.0)
    with pytest.raises(ValueError, match="cannot postdate"):
        ForecastObservation(
            **{
                **base.model_dump(),
                "provenance": Provenance(
                    source="source:a",
                    retrieved_at=base.as_of + timedelta(days=1),
                    effective_at=base.as_of + timedelta(seconds=1),
                ),
            }
        )


def test_bundle_rejects_observation_for_different_player():
    observation = _observation("source:a", 300.0, 20.0)
    with pytest.raises(ValueError, match="bundle player_id"):
        ForecastBundle(
            player_id="player:someone-else",
            as_of=observation.as_of,
            observations=(observation,),
            model_version="test-v1",
        )
