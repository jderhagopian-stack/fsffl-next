from __future__ import annotations

from dataclasses import dataclass

from .models import ForecastObservation


@dataclass(frozen=True)
class ForecastScore:
    source: str
    absolute_error: float
    squared_error: float
    standardized_error: float | None


def score_point_forecast(observation: ForecastObservation, actual: float) -> ForecastScore:
    """Score one historical forecast against an observed outcome.

    The standardized error is only reported when the forecast supplied a
    non-zero uncertainty estimate. More calibration metrics will be layered on
    top of this primitive rather than hidden inside provider adapters.
    """
    error = observation.distribution.mean - actual
    standardized = (
        error / observation.distribution.stddev
        if observation.distribution.stddev > 0
        else None
    )
    return ForecastScore(
        source=observation.source,
        absolute_error=abs(error),
        squared_error=error**2,
        standardized_error=standardized,
    )
