from datetime import UTC, datetime

from fsffl.forecast.backtest import HistoricalOutcome
from fsffl.forecast.benchmark import run_multi_source_benchmark
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import Position, Provenance


def _obs(player: str, source: str, mean: float, as_of: datetime) -> ForecastObservation:
    return ForecastObservation(
        player_id=player,
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 10, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=10.0),
        source=source,
        model_version="1",
        as_of=as_of,
        provenance=Provenance(source=source, retrieved_at=as_of, effective_at=as_of),
    )


def _outcome(player: str, actual: float) -> HistoricalOutcome:
    return HistoricalOutcome(
        player_id=player,
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        actual=actual,
    )


def test_benchmark_learns_weights_on_training_and_scores_held_out_test() -> None:
    train_time = datetime(2025, 8, 20, tzinfo=UTC)
    test_time = datetime(2026, 8, 20, tzinfo=UTC)

    training = (
        _obs("train-1", "source:a", 100.0, train_time),
        _obs("train-1", "source:b", 140.0, train_time),
        _obs("train-2", "source:a", 200.0, train_time),
        _obs("train-2", "source:b", 240.0, train_time),
    )
    training_outcomes = (_outcome("train-1", 105.0), _outcome("train-2", 205.0))

    test = (
        _obs("test-1", "source:a", 150.0, test_time),
        _obs("test-1", "source:b", 190.0, test_time),
    )
    test_outcomes = (_outcome("test-1", 155.0),)

    result = run_multi_source_benchmark(training, training_outcomes, test, test_outcomes)

    weights = result.challenger_weights[(Position.WR, ForecastHorizon.SEASON)]
    assert weights["source:a"] > weights["source:b"]
    assert len(result.source_performance) == 2
    assert len(result.equal_weight_performance) == 1
    assert len(result.challenger_performance) == 1
    assert result.challenger_performance[0].root_mean_squared_error < result.equal_weight_performance[0].root_mean_squared_error
