from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt

from fsffl.state.models import Position

from .evaluation import score_point_forecast
from .models import ForecastHorizon, ForecastObservation


@dataclass(frozen=True)
class HistoricalOutcome:
    player_id: str
    position: Position
    horizon: ForecastHorizon
    actual: float


@dataclass(frozen=True)
class SourcePerformance:
    source: str
    position: Position
    horizon: ForecastHorizon
    sample_size: int
    mean_absolute_error: float
    root_mean_squared_error: float
    mean_standardized_error: float | None


def evaluate_historical_forecasts(
    observations: tuple[ForecastObservation, ...],
    outcomes: tuple[HistoricalOutcome, ...],
) -> tuple[SourcePerformance, ...]:
    """Aggregate point-in-time forecast accuracy by source, position, and horizon.

    Only exact player/position/horizon matches are scored. This function does not
    infer missing outcomes or substitute later/current information.
    """
    outcome_map = {
        (item.player_id, item.position, item.horizon): item.actual for item in outcomes
    }
    grouped: dict[tuple[str, Position, ForecastHorizon], list[tuple[float, float, float | None]]] = defaultdict(list)

    for observation in observations:
        key = (observation.player_id, observation.position, observation.horizon)
        actual = outcome_map.get(key)
        if actual is None:
            continue
        score = score_point_forecast(observation, actual)
        grouped[(observation.source, observation.position, observation.horizon)].append(
            (score.absolute_error, score.squared_error, score.standardized_error)
        )

    results: list[SourcePerformance] = []
    for (source, position, horizon), scores in grouped.items():
        n = len(scores)
        mae = sum(item[0] for item in scores) / n
        rmse = sqrt(sum(item[1] for item in scores) / n)
        standardized = [item[2] for item in scores if item[2] is not None]
        mean_standardized = (
            sum(standardized) / len(standardized) if standardized else None
        )
        results.append(
            SourcePerformance(
                source=source,
                position=position,
                horizon=horizon,
                sample_size=n,
                mean_absolute_error=mae,
                root_mean_squared_error=rmse,
                mean_standardized_error=mean_standardized,
            )
        )

    return tuple(
        sorted(results, key=lambda item: (item.position, item.horizon, item.root_mean_squared_error, item.source))
    )


def challenger_inverse_rmse_weights(
    performance: tuple[SourcePerformance, ...],
    *,
    position: Position,
    horizon: ForecastHorizon,
) -> dict[str, float]:
    """Produce a transparent challenger weighting from historical RMSE.

    This is deliberately not production authority. It exists so NEXT-2 can test
    whether a simple evidence-derived weighting beats equal weighting out of
    sample. Zero-error sources are handled deterministically rather than with an
    arbitrary smoothing constant.
    """
    rows = [
        item
        for item in performance
        if item.position == position and item.horizon == horizon and item.sample_size > 0
    ]
    if not rows:
        return {}

    zero_error = [item for item in rows if item.root_mean_squared_error == 0]
    if zero_error:
        share = 1.0 / len(zero_error)
        return {item.source: share for item in zero_error}

    inverse = {
        item.source: 1.0 / item.root_mean_squared_error
        for item in rows
    }
    total = sum(inverse.values())
    return {source: value / total for source, value in sorted(inverse.items())}
