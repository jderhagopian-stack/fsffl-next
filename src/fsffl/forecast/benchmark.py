from __future__ import annotations

from dataclasses import dataclass

from fsffl.state.models import Position

from .backtest import HistoricalOutcome, SourcePerformance, challenger_inverse_rmse_weights, evaluate_historical_forecasts
from .calibration import UncertaintyCalibration, evaluate_uncertainty_calibration
from .ensemble import equal_weight_ensemble, weighted_ensemble
from .models import ForecastHorizon, ForecastObservation


@dataclass(frozen=True)
class BenchmarkResult:
    source_performance: tuple[SourcePerformance, ...]
    uncertainty_calibration: tuple[UncertaintyCalibration, ...]
    equal_weight_performance: tuple[SourcePerformance, ...]
    challenger_performance: tuple[SourcePerformance, ...]
    challenger_weights: dict[tuple[Position, ForecastHorizon], dict[str, float]]


def _cohorts(
    observations: tuple[ForecastObservation, ...],
) -> tuple[tuple[Position, ForecastHorizon], ...]:
    return tuple(sorted({(item.position, item.horizon) for item in observations}))


def run_multi_source_benchmark(
    training_observations: tuple[ForecastObservation, ...],
    training_outcomes: tuple[HistoricalOutcome, ...],
    test_observations: tuple[ForecastObservation, ...],
    test_outcomes: tuple[HistoricalOutcome, ...],
) -> BenchmarkResult:
    """Run one held-out benchmark across every supplied projection source.

    Weights are learned only from the training sample and then applied to the
    held-out test observations. This is the reusable batch entry point for
    comparing many providers at once; it deliberately avoids one-off source
    studies and same-sample weight promotion.
    """

    training_performance = evaluate_historical_forecasts(
        training_observations, training_outcomes
    )
    source_performance = evaluate_historical_forecasts(test_observations, test_outcomes)
    uncertainty = evaluate_uncertainty_calibration(test_observations, test_outcomes)

    equal = equal_weight_ensemble(test_observations)
    equal_performance = evaluate_historical_forecasts(equal, test_outcomes)

    weights_by_cohort: dict[tuple[Position, ForecastHorizon], dict[str, float]] = {}
    challenger_parts: list[ForecastObservation] = []

    for position, horizon in _cohorts(test_observations):
        weights = challenger_inverse_rmse_weights(
            training_performance,
            position=position,
            horizon=horizon,
        )
        if not weights:
            continue
        weights_by_cohort[(position, horizon)] = weights
        cohort_observations = tuple(
            item
            for item in test_observations
            if item.position == position and item.horizon == horizon
        )
        challenger_parts.extend(
            weighted_ensemble(
                cohort_observations,
                weights,
                source="fsffl:weighted_challenger",
                model_version="research-v1",
            )
        )

    challenger_performance = evaluate_historical_forecasts(
        tuple(challenger_parts), test_outcomes
    )

    return BenchmarkResult(
        source_performance=source_performance,
        uncertainty_calibration=uncertainty,
        equal_weight_performance=equal_performance,
        challenger_performance=challenger_performance,
        challenger_weights=weights_by_cohort,
    )
