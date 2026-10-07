from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from fsffl.state.models import Provenance

from .backtest import RealizedOutcome
from .models import ForecastDistribution, ForecastHorizon, ForecastObservation


ROLL_FORWARD_MODEL_VERSION = "next2-completed-actuals-plus-ros-v1"
COMPLETED_ACTUALS_ONLY_MODEL_VERSION = "next2-completed-actuals-only-v1"


def _validated_actuals_by_key(
    completed_actuals: tuple[RealizedOutcome, ...],
) -> dict[tuple[object, ...], list[RealizedOutcome]]:
    grouped: dict[tuple[object, ...], list[RealizedOutcome]] = defaultdict(list)
    for actual in completed_actuals:
        grouped[(actual.player_id, actual.position, actual.metric)].append(actual)

    for key, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: (item.period_start, item.period_end))
        previous: RealizedOutcome | None = None
        for current in ordered:
            if previous is not None and current.period_start < previous.period_end:
                raise ValueError(
                    "completed actual periods overlap for player/metric; "
                    f"cannot compose season outlook safely: {key}"
                )
            previous = current
        grouped[key] = ordered
    return grouped



def compose_completed_actuals_only(
    *,
    completed_actuals: tuple[RealizedOutcome, ...],
    season_start: datetime,
    season_end: datetime,
) -> tuple[ForecastObservation, ...]:
    """Represent a completed regular season as factual season-outlook observations.

    This is the terminal form of completed-actuals + ROS: once no regular-season
    games remain, forward production and uncertainty are exactly zero. The result
    preserves Forecast's season-outlook contract without inventing an overlapping
    REST_OF_SEASON period.
    """

    if season_start.tzinfo is None or season_end.tzinfo is None:
        raise ValueError("completed season window must be timezone-aware")
    season_start = season_start.astimezone(UTC)
    season_end = season_end.astimezone(UTC)
    if season_end <= season_start:
        raise ValueError("completed season_end must follow season_start")

    actuals_by_key = _validated_actuals_by_key(completed_actuals)
    output: list[ForecastObservation] = []
    for (player_id, position, metric), rows in actuals_by_key.items():
        used = [
            item
            for item in rows
            if item.period_start >= season_start and item.period_end <= season_end
        ]
        if not used:
            continue
        total = sum(item.actual for item in used)
        as_of = max(
            max(item.finalized_at, item.provenance.retrieved_at, item.provenance.effective_at)
            for item in used
        ).astimezone(UTC)
        retrieved_at = max(item.provenance.retrieved_at for item in used).astimezone(UTC)
        effective_at = max(item.provenance.effective_at for item in used).astimezone(UTC)
        output.append(
            ForecastObservation(
                player_id=player_id,
                position=position,
                horizon=ForecastHorizon.SEASON,
                metric=metric,
                period_start=season_start,
                period_end=season_end,
                distribution=ForecastDistribution(
                    mean=total,
                    stddev=0.0,
                    p10=total,
                    p50=total,
                    p90=total,
                ),
                source="fsffl:completed-actuals-only",
                model_version=COMPLETED_ACTUALS_ONLY_MODEL_VERSION,
                as_of=as_of,
                provenance=Provenance(
                    source="fsffl:completed-actuals-only",
                    retrieved_at=retrieved_at,
                    effective_at=effective_at,
                    source_version=COMPLETED_ACTUALS_ONLY_MODEL_VERSION,
                ),
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: (item.player_id, item.metric.value, item.source),
        )
    )

def compose_completed_actuals_with_ros(
    *,
    completed_actuals: tuple[RealizedOutcome, ...],
    ros_forecasts: tuple[ForecastObservation, ...],
    season_start: datetime,
) -> tuple[ForecastObservation, ...]:
    """Compose known completed production with a non-overlapping ROS forecast.

    Known actuals are constants, so only ROS uncertainty remains uncertain. WEEK
    projections are never accepted here. The function fails closed on overlap among
    actual records, overlap with the ROS period, or evidence finalized after the ROS
    information cutoff; it never infers how much of an ambiguous provider total
    belongs to completed games.
    """

    if season_start.tzinfo is None:
        raise ValueError("season_start must be timezone-aware")
    season_start = season_start.astimezone(UTC)
    if not ros_forecasts:
        return ()
    if any(item.horizon != ForecastHorizon.REST_OF_SEASON for item in ros_forecasts):
        raise ValueError("season roll-forward requires REST_OF_SEASON forecasts only")

    actuals_by_key = _validated_actuals_by_key(completed_actuals)

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
