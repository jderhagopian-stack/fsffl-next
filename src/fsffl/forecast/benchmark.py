from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from fsffl.state.models import Position

from .backtest import HistoricalOutcome, SourcePerformance, challenger_inverse_rmse_weights, evaluate_historical_forecasts
from .calibration import UncertaintyCalibration, evaluate_uncertainty_calibration
from .ensemble import equal_weight_ensemble, weighted_ensemble
from .models import ForecastHorizon, ForecastObservation


@dataclass(frozen=True)
class SourceCoverage:
    source: str
    position: Position
    horizon: ForecastHorizon
    matched_players: int
    eligible_players: int

    @property
    def coverage_rate(self) -> float:
        return self.matched_players / self.eligible_players if self.eligible_players else 0.0


@dataclass(frozen=True)
class BenchmarkResult:
    source_performance: tuple[SourcePerformance, ...]
    source_coverage: tuple[SourceCoverage, ...]
    uncertainty_calibration: tuple[UncertaintyCalibration, ...]
    equal_weight_performance: tuple[SourcePerformance, ...]
    challenger_performance: tuple[SourcePerformance, ...]
    challenger_weights: dict[tuple[Position, ForecastHorizon], dict[str, float]]


def _cohorts(
    observations: tuple[ForecastObservation, ...],
) -> tuple[tuple[Position, ForecastHorizon], ...]:
    return tuple(sorted({(item.position, item.horizon) for item in observations}))


def _source_coverage(
    observations: tuple[ForecastObservation, ...],
    outcomes: tuple[HistoricalOutcome, ...],
) -> tuple[SourceCoverage, ...]:
    eligible: dict[tuple[Position, ForecastHorizon], set[str]] = defaultdict(set)
    for outcome in outcomes:
        eligible[(outcome.position, outcome.horizon)].add(outcome.player_id)

    matched: dict[tuple[str, Position, ForecastHorizon], set[str]] = defaultdict(set)
    for observation in observations:
        cohort = (observation.position, observation.horizon)
        if observation.player_id in eligible.get(cohort, set()):
            matched[(observation.source, observation.position, observation.horizon)].add(
                observation.player_id
            )

    rows: list[SourceCoverage] = []
    for (source, position, horizon), players in matched.items():
        cohort_eligible = eligible[(position, horizon)]
        rows.append(
            SourceCoverage(
                source=source,
                position=position,
                horizon=horizon,
                matched_players=len(players),
                eligible_players=len(cohort_eligible),
            )
        )

    return tuple(sorted(rows, key=lambda item: (item.position, item.horizon, item.source)))


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
    source_coverage = _source_coverage(test_observations, test_outcomes)
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
        source_coverage=source_coverage,
        uncertainty_calibration=uncertainty,
        equal_weight_performance=equal_performance,
        challenger_performance=challenger_performance,
        challenger_weights=weights_by_cohort,
    )
