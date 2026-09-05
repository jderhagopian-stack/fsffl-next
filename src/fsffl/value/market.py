from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt
from statistics import mean, median
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .models import (
    MarketPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
)


class MarketEvidenceKind(StrEnum):
    COMPLETED_TRANSACTION = "completed_transaction"
    MARKET_INDEX = "market_index"
    RANKING = "ranking"
    ADP = "adp"
    OTHER = "other"


class MarketObservation(FrozenModel):
    """One point-in-time observation of external dynasty-market information."""

    asset_id: str
    asset_kind: ValueAssetKind
    source: str
    evidence_kind: MarketEvidenceKind
    observed_at: datetime
    value: float
    scale: ValueScale
    source_version: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_identifiers(self) -> "MarketObservation":
        if not self.asset_id.strip() or not self.source.strip():
            raise ValueError("market observation identifiers cannot be blank")
        return self


class MarketBaselineMethod(StrEnum):
    MEDIAN = "median"
    MEAN = "mean"


def estimate_market_price(
    observations: tuple[MarketObservation, ...],
    *,
    asset_id: str,
    asset_kind: ValueAssetKind,
    scale: ValueScale,
    as_of: datetime,
    market_context_id: str,
    model_version: str,
    method: MarketBaselineMethod = MarketBaselineMethod.MEDIAN,
    minimum_sources: Annotated[int, Field(ge=1)] = 1,
) -> MarketPriceEstimate:
    """Build a transparent point-in-time market baseline.

    No source reliability weights or recency coefficients are hidden here. The
    caller supplies the admissible evidence window; this function rejects future
    observations, incompatible scales, duplicate source snapshots, and thin
    source coverage. Median is the robust default comparator. Evidence-derived
    source weighting can challenge this baseline later.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    eligible = tuple(
        observation
        for observation in observations
        if observation.asset_id == asset_id
        and observation.asset_kind == asset_kind
        and observation.observed_at <= as_of
    )
    if not eligible:
        raise ValueError("no eligible point-in-time market observations")

    incompatible = [observation for observation in eligible if observation.scale != scale]
    if incompatible:
        raise ValueError("market observations on incompatible scales must be converted explicitly")

    # A source may not cast multiple votes for the same retained snapshot.
    snapshot_keys = [
        (observation.source, observation.observed_at, observation.source_version)
        for observation in eligible
    ]
    if len(snapshot_keys) != len(set(snapshot_keys)):
        raise ValueError("duplicate market source snapshot detected")

    sources = tuple(sorted({observation.source for observation in eligible}))
    if len(sources) < minimum_sources:
        raise ValueError(
            f"market estimate has {len(sources)} independent sources; requires {minimum_sources}"
        )

    values = sorted(observation.value for observation in eligible)
    center = median(values) if method == MarketBaselineMethod.MEDIAN else mean(values)
    variance = mean((value - center) ** 2 for value in values) if len(values) > 1 else 0.0

    return MarketPriceEstimate(
        asset_id=asset_id,
        asset_kind=asset_kind,
        distribution=ValueDistribution(
            mean=center,
            stddev=sqrt(variance),
            p10=_empirical_quantile(values, 0.10),
            p50=_empirical_quantile(values, 0.50),
            p90=_empirical_quantile(values, 0.90),
        ),
        scale=scale,
        as_of=as_of,
        market_context_id=market_context_id,
        model_version=model_version,
        evidence_sources=sources,
    )


def _empirical_quantile(values: list[float], probability: float) -> float:
    if len(values) == 1:
        return values[0]
    position = probability * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + fraction * (values[upper] - values[lower])
