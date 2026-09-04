from datetime import UTC, datetime

from fsffl.forecast.backtest import RealizedOutcome
from fsffl.forecast.benchmark import run_multi_source_benchmark
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


PERIOD_START = datetime(2026, 9, 1, tzinfo=UTC)
PERIOD_END = datetime(2027, 1, 10, tzinfo=UTC)


def _obs(
    player: str,
    source: str,
    mean: float,
    as_of: datetime,
    *,
    metric: ForecastMetric = ForecastMetric.FANTASY_POINTS,
    period_start: datetime = PERIOD_START,
    period_end: datetime = PERIOD_END,
) -> ForecastObservation:
    return ForecastObservation(
        player_id=player,
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(mean=mean, stddev=10.0),
        source=source,
        model_version="1",
        as_of=as_of,
        provenance=Provenance(source=source, retrieved_at=as_of, effective_at=as_of),
    )


def _outcome(
    player: str,
    actual: float,
    *,
    metric: ForecastMetric = ForecastMetric.FANTASY_POINTS,
    period_start: datetime = PERIOD_START,
    period_end: datetime = PERIOD_END,
) -> RealizedOutcome:
    finalized = datetime(2027, 1, 11, tzinfo=UTC)
    return RealizedOutcome(
        player_id=player,
        position=Position.WR,
        metric=metric,
        period_start=period_start,
        period_end=period_end,
        actual=actual,
        finalized_at=max(finalized, period_end),
        provenance=Provenance(
            source="outcomes:test",
            retrieved_at=max(finalized, period_end),
            effective_at=period_end,
        ),
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
    assert (
        result.challenger_performance[0].root_mean_squared_error
        < result.equal_weight_performance[0].root_mean_squared_error
    )
    assert {row.source: row.coverage_rate for row in result.source_coverage} == {
        "source:a": 1.0,
        "source:b": 1.0,
    }


def test_benchmark_reports_partial_source_coverage() -> None:
    train_time = datetime(2025, 8, 20, tzinfo=UTC)
    test_time = datetime(2026, 8, 20, tzinfo=UTC)

    training = (
        _obs("train-1", "source:a", 100.0, train_time),
        _obs("train-1", "source:b", 110.0, train_time),
    )
    training_outcomes = (_outcome("train-1", 105.0),)

    test = (
        _obs("test-1", "source:a", 150.0, test_time),
        _obs("test-2", "source:a", 170.0, test_time),
        _obs("test-1", "source:b", 160.0, test_time),
    )
    test_outcomes = (_outcome("test-1", 155.0), _outcome("test-2", 175.0))

    result = run_multi_source_benchmark(training, training_outcomes, test, test_outcomes)
    coverage = {row.source: row for row in result.source_coverage}

    assert coverage["source:a"].matched_targets == 2
    assert coverage["source:a"].eligible_targets == 2
    assert coverage["source:a"].coverage_rate == 1.0
    assert coverage["source:b"].matched_targets == 1
    assert coverage["source:b"].eligible_targets == 2
    assert coverage["source:b"].coverage_rate == 0.5


def test_benchmark_does_not_count_wrong_metric_as_coverage() -> None:
    train_time = datetime(2025, 8, 20, tzinfo=UTC)
    test_time = datetime(2026, 8, 20, tzinfo=UTC)
    training = (_obs("train-1", "source:a", 100.0, train_time),)
    training_outcomes = (_outcome("train-1", 105.0),)

    test = (
        _obs("test-1", "source:a", 150.0, test_time),
        _obs(
            "test-1",
            "source:b",
            900.0,
            test_time,
            metric=ForecastMetric.REC_YARDS,
        ),
    )
    test_outcomes = (_outcome("test-1", 155.0),)

    result = run_multi_source_benchmark(training, training_outcomes, test, test_outcomes)
    coverage = {row.source: row for row in result.source_coverage}

    assert coverage["source:a"].coverage_rate == 1.0
    assert coverage["source:b"].coverage_rate == 0.0
