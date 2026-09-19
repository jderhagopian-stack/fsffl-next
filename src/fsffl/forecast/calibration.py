from __future__ import annotations

from collections import defaultdict
from math import sqrt

from fsffl.state.models import FrozenModel, Position

from .backtest import RealizedOutcome, _outcome_map, outcome_for_observation
from .models import ForecastHorizon, ForecastObservation


class UncertaintyCalibration(FrozenModel):
    source: str
    position: Position
    horizon: ForecastHorizon
    sample_size: int
    standardized_rmse: float | None
    p10_p90_coverage: float | None


def evaluate_uncertainty_calibration(
    observations: tuple[ForecastObservation, ...],
    outcomes: tuple[RealizedOutcome, ...],
) -> tuple[UncertaintyCalibration, ...]:
    """Measure whether stated forecast uncertainty matches realized error.

    Exact player/position/metric/period identity is required. This reports
    diagnostics only and never silently rescales provider or production forecasts.
    """

    mapped_outcomes = _outcome_map(outcomes)
    grouped: dict[
        tuple[str, Position, ForecastHorizon],
        list[tuple[float | None, bool | None]],
    ] = defaultdict(list)

    for observation in observations:
        outcome = outcome_for_observation(observation, mapped_outcomes)
        if outcome is None:
            continue
        actual = outcome.actual

        standardized_sq: float | None = None
        if observation.distribution.stddev > 0:
            error = observation.distribution.mean - actual
            standardized_sq = (error / observation.distribution.stddev) ** 2

        coverage: bool | None = None
        if (
            observation.distribution.p10 is not None
            and observation.distribution.p90 is not None
        ):
            coverage = (
                observation.distribution.p10
                <= actual
                <= observation.distribution.p90
            )

        grouped[(observation.source, observation.position, observation.horizon)].append(
            (standardized_sq, coverage)
        )

    results: list[UncertaintyCalibration] = []
    for (source, position, horizon), rows in grouped.items():
        standardized = [value for value, _ in rows if value is not None]
        covered = [value for _, value in rows if value is not None]
        results.append(
            UncertaintyCalibration(
                source=source,
                position=position,
                horizon=horizon,
                sample_size=len(rows),
                standardized_rmse=(
                    sqrt(sum(standardized) / len(standardized))
                    if standardized
                    else None
                ),
                p10_p90_coverage=(
                    sum(1 for value in covered if value) / len(covered)
                    if covered
                    else None
                ),
            )
        )

    return tuple(
        sorted(results, key=lambda item: (item.position, item.horizon, item.source))
    )
