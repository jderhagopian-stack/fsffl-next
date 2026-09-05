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


def _obs(source: str, mean: float, *, with_quantiles: bool = False) -> ForecastObservation:
    distribution = ForecastDistribution(
        mean=mean,
        stddev=10.0,
        p10=mean - 10.0 if with_quantiles else None,
        p50=mean if with_quantiles else None,
        p90=mean + 10.0 if with_quantiles else None,
    )
    return ForecastObservation(
        player_id="player-1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 10, tzinfo=UTC),
        period_end=datetime(2027, 1, 5, tzinfo=UTC),
        distribution=distribution,
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


def test_weighted_ensemble_records_all_component_sources() -> None:
    result = weighted_ensemble(
        (_obs("provider:b", 200.0), _obs("provider:a", 100.0)),
        {"provider:a": 0.5, "provider:b": 0.5},
    )[0]
    assert "provider:a" in result.provenance.source
    assert "provider:b" in result.provenance.source


def test_weighted_ensemble_does_not_average_incompatible_provider_quantiles() -> None:
    result = weighted_ensemble(
        (_obs("a", 0.0, with_quantiles=True), _obs("b", 100.0, with_quantiles=True)),
        {"a": 0.5, "b": 0.5},
    )[0]
    assert result.distribution.stddev > 10.0
    assert result.distribution.p10 is None
    assert result.distribution.p50 is None
    assert result.distribution.p90 is None
