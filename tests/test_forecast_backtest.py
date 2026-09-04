from datetime import UTC, datetime

from fsffl.forecast.backtest import (
    HistoricalOutcome,
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


def _obs(player_id: str, source: str, mean: float, position: Position = Position.QB) -> ForecastObservation:
    as_of = datetime(2026, 8, 1, tzinfo=UTC)
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 10, tzinfo=UTC),
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


def test_historical_evaluation_groups_by_source_position_and_horizon():
    observations = (
        _obs("p1", "source-a", 300.0),
        _obs("p1", "source-b", 280.0),
        _obs("p2", "source-a", 240.0),
        _obs("p2", "source-b", 220.0),
    )
    outcomes = (
        HistoricalOutcome("p1", Position.QB, ForecastHorizon.SEASON, 290.0),
        HistoricalOutcome("p2", Position.QB, ForecastHorizon.SEASON, 230.0),
    )

    results = evaluate_historical_forecasts(observations, outcomes)

    assert len(results) == 2
    assert all(item.sample_size == 2 for item in results)
    assert all(item.mean_absolute_error == 10.0 for item in results)


def test_historical_evaluation_does_not_fill_missing_outcomes():
    observations = (_obs("p1", "source-a", 300.0), _obs("missing", "source-a", 250.0))
    outcomes = (HistoricalOutcome("p1", Position.QB, ForecastHorizon.SEASON, 290.0),)

    results = evaluate_historical_forecasts(observations, outcomes)

    assert results[0].sample_size == 1


def test_challenger_weights_favor_lower_historical_error_without_hardcoded_source_preference():
    observations = (
        _obs("p1", "better", 295.0),
        _obs("p1", "worse", 260.0),
        _obs("p2", "better", 232.0),
        _obs("p2", "worse", 200.0),
    )
    outcomes = (
        HistoricalOutcome("p1", Position.QB, ForecastHorizon.SEASON, 290.0),
        HistoricalOutcome("p2", Position.QB, ForecastHorizon.SEASON, 230.0),
    )
    performance = evaluate_historical_forecasts(observations, outcomes)

    weights = challenger_inverse_rmse_weights(
        performance,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
    )

    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert weights["better"] > weights["worse"]
