from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from fsffl.state.models import Position

from .backtest import (
    RealizedOutcome,
    SourcePerformance,
    challenger_inverse_rmse_weights,
    evaluate_historical_forecasts,
)
from .calibration import UncertaintyCalibration, evaluate_uncertainty_calibration
from .ensemble import equal_weight_ensemble, weighted_ensemble
from .models import ForecastHorizon, ForecastObservation


@dataclass(frozen=True)
class SourceCoverage:
    source: str
    position: Position
    horizon: ForecastHorizon
    matched_targets: int
    eligible_targets: int

    @property
    def coverage_rate(self) -> float:
        return self.matched_targets / self.eligible_targets if self.eligible_targets else 0.0

    @property
    def matched_players(self) -> int:
        """Compatibility alias; coverage is now counted by exact evaluation target."""
        return self.matched_targets

    @property
    def eligible_players(self) -> int:
        """Compatibility alias; coverage is now counted by exact evaluation target."""
        return self.eligible_targets


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
    outcomes: tuple[RealizedOutcome, ...],
) -> tuple[SourceCoverage, ...]:
    """Report exact target coverage, including sources with zero valid matches.

    Eligibility is defined from realized targets whose metric/period appears in the
    benchmark cohort. A player projected for the wrong metric or period no longer
    counts as covered merely because the player name matches.
    """
    outcome_by_identity = {outcome.identity: outcome for outcome in outcomes}
    if len(outcome_by_identity) != len(outcomes):
        raise ValueError("duplicate realized outcome identities are not allowed")

    cohort_shapes: dict[
        tuple[Position, ForecastHorizon], set[tuple[object, object, object]]
    ] = defaultdict(set)
    sources_by_cohort: dict[tuple[Position, ForecastHorizon], set[str]] = defaultdict(set)
    for observation in observations:
        cohort = (observation.position, observation.horizon)
        cohort_shapes[cohort].add(
            (observation.metric, observation.period_start, observation.period_end)
        )
        sources_by_cohort[cohort].add(observation.source)

    eligible: dict[tuple[Position, ForecastHorizon], set[tuple[object, ...]]] = defaultdict(set)
    for cohort, shapes in cohort_shapes.items():
        position, _ = cohort
        for outcome in outcomes:
            shape = (outcome.metric, outcome.period_start, outcome.period_end)
            if outcome.position == position and shape in shapes:
                eligible[cohort].add(outcome.identity)

    matched: dict[tuple[str, Position, ForecastHorizon], set[tuple[object, ...]]] = defaultdict(set)
    for observation in observations:
        cohort = (observation.position, observation.horizon)
        identity = (
            observation.player_id,
            observation.position,
            observation.metric,
            observation.period_start,
            observation.period_end,
        )
        if identity in eligible.get(cohort, set()):
            matched[(observation.source, *cohort)].add(identity)

    rows: list[SourceCoverage] = []
    for (position, horizon), sources in sources_by_cohort.items():
        cohort_eligible = eligible.get((position, horizon), set())
        for source in sources:
            rows.append(
                SourceCoverage(
                    source=source,
                    position=position,
                    horizon=horizon,
                    matched_targets=len(matched.get((source, position, horizon), set())),
                    eligible_targets=len(cohort_eligible),
                )
            )

    return tuple(sorted(rows, key=lambda item: (item.position, item.horizon, item.source)))


def run_multi_source_benchmark(
    training_observations: tuple[ForecastObservation, ...],
    training_outcomes: tuple[RealizedOutcome, ...],
    test_observations: tuple[ForecastObservation, ...],
    test_outcomes: tuple[RealizedOutcome, ...],
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
