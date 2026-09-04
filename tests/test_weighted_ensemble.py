from datetime import UTC, datetime

import pytest

from fsffl.forecast.ensemble import weighted_ensemble
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


def _obs(source: str, mean: float) -> ForecastObservation:
    return ForecastObservation(
        player_id="player-1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 10, tzinfo=UTC),
        period_end=datetime(2027, 1, 5, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=10.0),
        source=source,
        model_version="1",
        as_of=datetime(2026, 8, 20, tzinfo=UTC),
        provenance=Provenance(
            source=source,
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
            effective_at=datetime(2026, 8, 20, tzinfo=UTC),
        ),
    )


def test_weighted_ensemble_applies_explicit_source_weights() -> None:
    result = weighted_ensemble(
        (_obs("a", 100.0), _obs("b", 200.0)),
        {"a": 0.75, "b": 0.25},
    )
    assert len(result) == 1
    assert result[0].distribution.mean == pytest.approx(125.0)


def test_weighted_ensemble_renormalizes_when_source_is_missing() -> None:
    result = weighted_ensemble(
        (_obs("a", 100.0),),
        {"a": 0.25, "b": 0.75},
    )
    assert result[0].distribution.mean == pytest.approx(100.0)


def test_weighted_ensemble_rejects_duplicate_source_in_same_group() -> None:
    with pytest.raises(ValueError, match="duplicate forecast source"):
        weighted_ensemble(
            (_obs("a", 100.0), _obs("a", 110.0)),
            {"a": 1.0},
        )


def test_weighted_ensemble_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        weighted_ensemble((_obs("a", 100.0),), {"a": -1.0})
