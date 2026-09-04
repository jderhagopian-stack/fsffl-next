from __future__ import annotations

from collections import defaultdict
from math import sqrt

from .models import ForecastDistribution, ForecastObservation


def _group_like_for_like(
    observations: tuple[ForecastObservation, ...],
) -> dict[tuple[object, ...], list[ForecastObservation]]:
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
    return grouped


def _build_ensemble_observation(
    items: list[ForecastObservation],
    *,
    normalized_weights: dict[str, float],
    source: str,
    model_version: str,
) -> ForecastObservation:
    first = items[0]
    if len({item.source for item in items}) != len(items):
        raise ValueError("duplicate forecast source within one ensemble group")

    missing = [item.source for item in items if item.source not in normalized_weights]
    if missing:
        raise ValueError(f"missing weights for sources: {', '.join(sorted(missing))}")

    active = {item.source: normalized_weights[item.source] for item in items}
    total = sum(active.values())
    if total <= 0:
        raise ValueError("active ensemble weights must sum to a positive value")
    active = {name: value / total for name, value in active.items()}

    mean = sum(active[item.source] * item.distribution.mean for item in items)
    second_moment = sum(
        active[item.source]
        * (item.distribution.stddev**2 + item.distribution.mean**2)
        for item in items
    )
    variance = max(0.0, second_moment - mean**2)

    def weighted_quantile(name: str) -> float | None:
        values = [getattr(item.distribution, name) for item in items]
        if any(value is None for value in values):
            return None
        return sum(
            active[item.source] * float(getattr(item.distribution, name))
            for item in items
        )

    return ForecastObservation(
        player_id=first.player_id,
        position=first.position,
        horizon=first.horizon,
        metric=first.metric,
        period_start=first.period_start,
        period_end=first.period_end,
        distribution=ForecastDistribution(
            mean=mean,
            stddev=sqrt(variance),
            p10=weighted_quantile("p10"),
            p50=weighted_quantile("p50"),
            p90=weighted_quantile("p90"),
        ),
        source=source,
        model_version=model_version,
        as_of=first.as_of,
        provenance=first.provenance,
    )


def weighted_ensemble(
    observations: tuple[ForecastObservation, ...],
    weights: dict[str, float],
    *,
    source: str = "fsffl:weighted_challenger",
    model_version: str = "0.1.0",
) -> tuple[ForecastObservation, ...]:
    """Apply explicit source weights to like-for-like observations.

    This function is mechanism only. Supplying a weight does not make that weight
    authoritative. NEXT-2 derives and validates challenger weights separately.
    Missing sources are renormalized over the sources actually present so a
    historical backtest never fabricates a projection that did not exist.
    """
    if not weights:
        raise ValueError("weights cannot be empty")
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights cannot be negative")
    if sum(weights.values()) <= 0:
        raise ValueError("weights must sum to a positive value")

    grouped = _group_like_for_like(observations)
    output = [
        _build_ensemble_observation(
            items,
            normalized_weights=weights,
            source=source,
            model_version=model_version,
        )
        for items in grouped.values()
    ]
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
    sources = sorted({observation.source for observation in observations})
    if not sources:
        return ()
    weights = {source_name: 1.0 for source_name in sources}
    return weighted_ensemble(
        observations,
        weights,
        source=source,
        model_version=model_version,
    )
