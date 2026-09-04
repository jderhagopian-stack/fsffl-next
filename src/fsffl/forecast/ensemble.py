from __future__ import annotations

from collections import defaultdict
from math import sqrt

from .models import ForecastDistribution, ForecastObservation


def equal_weight_ensemble(
    observations: tuple[ForecastObservation, ...],
    *,
    source: str = "fsffl:equal_weight",
    model_version: str = "0.1.0",
) -> tuple[ForecastObservation, ...]:
    """Deterministic baseline ensemble for like-for-like forecast observations.

    This is intentionally a baseline, not a claim that equal weighting is
    optimal. Historical evidence may later replace it with calibrated weights.
    """
    grouped: dict[tuple[object, ...], list[ForecastObservation]] = defaultdict(list)
    for observation in observations:
        key = (
            observation.player_id,
            observation.position,
            observation.horizon,
            observation.metric,
            observation.period_start,
            observation.period_end,
            observation.as_of,
        )
        grouped[key].append(observation)

    output: list[ForecastObservation] = []
    for items in grouped.values():
        first = items[0]
        n = len(items)
        mean = sum(item.distribution.mean for item in items) / n

        second_moment = sum(
            item.distribution.stddev**2 + item.distribution.mean**2 for item in items
        ) / n
        variance = max(0.0, second_moment - mean**2)

        def avg_quantile(name: str) -> float | None:
            values = [getattr(item.distribution, name) for item in items]
            concrete = [value for value in values if value is not None]
            return sum(concrete) / len(concrete) if len(concrete) == len(values) else None

        output.append(
            ForecastObservation(
                player_id=first.player_id,
                position=first.position,
                horizon=first.horizon,
                metric=first.metric,
                period_start=first.period_start,
                period_end=first.period_end,
                distribution=ForecastDistribution(
                    mean=mean,
                    stddev=sqrt(variance),
                    p10=avg_quantile("p10"),
                    p50=avg_quantile("p50"),
                    p90=avg_quantile("p90"),
                ),
                source=source,
                model_version=model_version,
                as_of=first.as_of,
                provenance=first.provenance,
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: (
                item.player_id,
                item.horizon,
                item.metric,
                item.period_start,
                item.period_end,
            ),
        )
    )
