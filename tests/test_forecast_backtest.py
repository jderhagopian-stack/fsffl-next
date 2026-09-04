from datetime import UTC, datetime

import pytest

from fsffl.forecast.backtest import (
    RealizedOutcome,
    challenger_inverse_rmse_weights,
    evaluate_historical_forecasts,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


PERIOD_START = datetime(2026, 9, 1, tzinfo=UTC)
PERIOD_END = datetime(2027, 1, 10, tzinfo=UTC)
FINALIZED = datetime(2027, 1, 11, tzinfo=UTC)


def _obs(
    player_id: str,
    source: str,
    mean: float,
    position: Position = Position.QB,
    *,
    metric: ForecastMetric = ForecastMetric.FANTASY_POINTS,
    period_start: datetime = PERIOD_START,
    period_end: datetime = PERIOD_END,
) -> ForecastObservation:
    as_of = datetime(2026, 8, 1, tzinfo=UTC)
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(mean=mean, stddev=10.0),
        source=source,
        model_version="test",
        as_of=as_of,
        provenance=Provenance(
            source=source,
            retrieved_at=as_of,
            effective_at=as_of,
        ),
    )


def _outcome(
    player_id: str,
    actual: float,
    position: Position = Position.QB,
    *,
    metric: ForecastMetric = ForecastMetric.FANTASY_POINTS,
    period_start: datetime = PERIOD_START,
    period_end: datetime = PERIOD_END,
) -> RealizedOutcome:
    return RealizedOutcome(
        player_id=player_id,
        position=position,
        metric=metric,
        period_start=period_start,
        period_end=period_end,
        actual=actual,
        finalized_at=max(FINALIZED, period_end),
        provenance=Provenance(
            source="outcomes:test",
            retrieved_at=max(FINALIZED, period_end),
            effective_at=period_end,
        ),
    )


def test_historical_evaluation_groups_by_source_position_and_horizon():
    observations = (
        _obs("p1", "source-a", 300.0),
        _obs("p1", "source-b", 280.0),
        _obs("p2", "source-a", 240.0),
        _obs("p2", "source-b", 220.0),
    )
    outcomes = (_outcome("p1", 290.0), _outcome("p2", 230.0))

    results = evaluate_historical_forecasts(observations, outcomes)

    assert len(results) == 2
    assert all(item.sample_size == 2 for item in results)
    assert all(item.mean_absolute_error == 10.0 for item in results)


def test_historical_evaluation_does_not_fill_missing_outcomes():
    observations = (_obs("p1", "source-a", 300.0), _obs("missing", "source-a", 250.0))
    outcomes = (_outcome("p1", 290.0),)

    results = evaluate_historical_forecasts(observations, outcomes)

    assert results[0].sample_size == 1


def test_historical_evaluation_requires_exact_metric_and_period_match():
    wrong_metric = _obs(
        "p1", "source-a", 300.0, metric=ForecastMetric.REC_YARDS
    )
    wrong_period = _obs(
        "p1",
        "source-b",
        300.0,
        period_start=datetime(2026, 9, 8, tzinfo=UTC),
    )
    outcomes = (_outcome("p1", 290.0),)

    assert evaluate_historical_forecasts((wrong_metric, wrong_period), outcomes) == ()


def test_duplicate_realized_outcome_identity_is_rejected():
    observations = (_obs("p1", "source-a", 300.0),)
    outcomes = (_outcome("p1", 290.0), _outcome("p1", 291.0))

    with pytest.raises(ValueError, match="duplicate realized outcome identity"):
        evaluate_historical_forecasts(observations, outcomes)


def test_challenger_weights_favor_lower_historical_error_without_hardcoded_source_preference():
    observations = (
        _obs("p1", "better", 295.0),
        _obs("p1", "worse", 260.0),
        _obs("p2", "better", 232.0),
        _obs("p2", "worse", 200.0),
    )
    outcomes = (_outcome("p1", 290.0), _outcome("p2", 230.0))
    performance = evaluate_historical_forecasts(observations, outcomes)

    weights = challenger_inverse_rmse_weights(
        performance,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
    )

    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert weights["better"] > weights["worse"]
