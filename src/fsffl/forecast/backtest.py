from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, Provenance

from .evaluation import score_point_forecast
from .models import ForecastHorizon, ForecastMetric, ForecastObservation


class RealizedOutcome(FrozenModel):
    """A realized evaluation target with exact metric/period identity.

    Outcomes are targets only. They must never be used as historical forecast
    inputs. Horizon is intentionally absent: the realized fact is defined by the
    metric and period, while forecast horizon remains a property of the forecast.
    """

    player_id: str
    position: Position
    metric: ForecastMetric
    period_start: datetime
    period_end: datetime
    actual: float
    finalized_at: datetime
    provenance: Provenance

    @field_validator("period_start", "period_end", "finalized_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("realized outcome timestamps must be timezone-aware")
        return value

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("realized outcome player_id cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_period_and_finalization(self) -> "RealizedOutcome":
        if self.period_end <= self.period_start:
            raise ValueError("realized outcome period_end must be after period_start")
        if self.finalized_at < self.period_end:
            raise ValueError("realized outcome cannot be finalized before period_end")
        return self

    @property
    def identity(self) -> tuple[str, Position, ForecastMetric, datetime, datetime]:
        return (
            self.player_id,
            self.position,
            self.metric,
            self.period_start,
            self.period_end,
        )


# Temporary compatibility alias while downstream callers migrate to the clearer name.
HistoricalOutcome = RealizedOutcome


class SourcePerformance(FrozenModel):
    source: str
    position: Position
    horizon: ForecastHorizon
    sample_size: int
    mean_absolute_error: float
    root_mean_squared_error: float
    mean_standardized_error: float | None


def _outcome_map(
    outcomes: tuple[RealizedOutcome, ...],
) -> dict[tuple[str, Position, ForecastMetric, datetime, datetime], RealizedOutcome]:
    mapped: dict[
        tuple[str, Position, ForecastMetric, datetime, datetime], RealizedOutcome
    ] = {}
    for outcome in outcomes:
        if outcome.identity in mapped:
            raise ValueError(f"duplicate realized outcome identity: {outcome.identity}")
        mapped[outcome.identity] = outcome
    return mapped


def outcome_for_observation(
    observation: ForecastObservation,
    outcome_map: dict[
        tuple[str, Position, ForecastMetric, datetime, datetime], RealizedOutcome
    ],
) -> RealizedOutcome | None:
    return outcome_map.get(
        (
            observation.player_id,
            observation.position,
            observation.metric,
            observation.period_start,
            observation.period_end,
        )
    )


def evaluate_historical_forecasts(
    observations: tuple[ForecastObservation, ...],
    outcomes: tuple[RealizedOutcome, ...],
) -> tuple[SourcePerformance, ...]:
    """Aggregate PIT forecast accuracy by source, position, and horizon.

    Only exact player/position/metric/period matches are scored. This function
    does not infer missing outcomes or substitute later/current information.
    """
    mapped_outcomes = _outcome_map(outcomes)
    grouped: dict[
        tuple[str, Position, ForecastHorizon],
        list[tuple[float, float, float | None]],
    ] = defaultdict(list)

    for observation in observations:
        outcome = outcome_for_observation(observation, mapped_outcomes)
        if outcome is None:
            continue
        score = score_point_forecast(observation, outcome.actual)
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
        sorted(
            results,
            key=lambda item: (
                item.position,
                item.horizon,
                item.root_mean_squared_error,
                item.source,
            ),
        )
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
        if item.position == position
        and item.horizon == horizon
        and item.sample_size > 0
    ]
    if not rows:
        return {}

    zero_error = [item for item in rows if item.root_mean_squared_error == 0]
    if zero_error:
        share = 1.0 / len(zero_error)
        return {item.source: share for item in zero_error}

    inverse = {item.source: 1.0 / item.root_mean_squared_error for item in rows}
    total = sum(inverse.values())
    return {source: value / total for source, value in sorted(inverse.items())}
