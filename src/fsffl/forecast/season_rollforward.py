from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from fsffl.state.models import Provenance

from .backtest import RealizedOutcome
from .models import ForecastDistribution, ForecastHorizon, ForecastObservation


ROLL_FORWARD_MODEL_VERSION = "next2-completed-actuals-plus-ros-v1"


def compose_completed_actuals_with_ros(
    *,
    completed_actuals: tuple[RealizedOutcome, ...],
    ros_forecasts: tuple[ForecastObservation, ...],
    season_start: datetime,
) -> tuple[ForecastObservation, ...]:
    """Compose known completed production with a non-overlapping ROS forecast.

    Known actuals are constants, so only ROS uncertainty remains uncertain. WEEK
    projections are never accepted here. The function fails closed on temporal
    overlap or evidence finalized after the ROS information cutoff; it does not
    infer how much of an ambiguous provider total belongs to completed games.
    """

    if season_start.tzinfo is None:
        raise ValueError("season_start must be timezone-aware")
    season_start = season_start.astimezone(UTC)
    if not ros_forecasts:
        return ()
    if any(item.horizon != ForecastHorizon.REST_OF_SEASON for item in ros_forecasts):
        raise ValueError("season roll-forward requires REST_OF_SEASON forecasts only")

    actuals_by_key: dict[tuple[object, ...], list[RealizedOutcome]] = defaultdict(list)
    for actual in completed_actuals:
        actuals_by_key[(actual.player_id, actual.position, actual.metric)].append(actual)

    output: list[ForecastObservation] = []
    for ros in ros_forecasts:
        matching = actuals_by_key.get((ros.player_id, ros.position, ros.metric), [])
        completed_value = 0.0
        used_actuals: list[RealizedOutcome] = []
        for actual in matching:
            if actual.period_start < season_start:
                continue
            if actual.finalized_at > ros.as_of:
                raise ValueError(
                    "completed actual cannot be finalized after ROS forecast cutoff"
                )
            if actual.period_end > ros.period_start:
                raise ValueError(
                    "completed actual period overlaps ROS forecast period"
                )
            completed_value += actual.actual
            used_actuals.append(actual)

        distribution = ros.distribution
        shifted = ForecastDistribution(
            mean=completed_value + distribution.mean,
            stddev=distribution.stddev,
            p10=(completed_value + distribution.p10 if distribution.p10 is not None else None),
            p50=(completed_value + distribution.p50 if distribution.p50 is not None else None),
            p90=(completed_value + distribution.p90 if distribution.p90 is not None else None),
        )
        retrieved_at = max(
            [ros.provenance.retrieved_at]
            + [item.provenance.retrieved_at for item in used_actuals]
        )
        effective_at = max(
            [ros.provenance.effective_at]
            + [item.provenance.effective_at for item in used_actuals]
        )
        if effective_at > ros.as_of or retrieved_at > ros.as_of:
            raise ValueError("season roll-forward evidence postdates ROS forecast cutoff")
        provenance = Provenance(
            source="fsffl:completed-actuals-plus-ros",
            retrieved_at=retrieved_at,
            effective_at=effective_at,
            source_version=ROLL_FORWARD_MODEL_VERSION,
        )
        output.append(
            ros.model_copy(
                update={
                    "horizon": ForecastHorizon.SEASON,
                    "period_start": season_start,
                    "distribution": shifted,
                    "source": "fsffl:completed-actuals-plus-ros",
                    "model_version": ROLL_FORWARD_MODEL_VERSION,
                    "provenance": provenance,
                }
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: (item.player_id, item.metric.value, item.source),
        )
    )
