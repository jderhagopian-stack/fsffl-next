from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import StrEnum
from math import log1p, sqrt
from statistics import mean

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .cardinal import NativeMarketMagnitudeObservation


class CardinalTransformKind(StrEnum):
    AFFINE = "affine"
    LOG_AFFINE = "log_affine"


class CardinalCalibrationPair(FrozenModel):
    """Point-in-time matched native magnitudes for non-authoritative scale research.

    ``target`` is another explicitly identified scale, not an FSFFL Value authority.
    The pair exists only to fit and compare challenger transformations.
    """

    asset_id: str
    source_id: str
    native_scale_id: str
    native_value: float
    target_source_id: str
    target_scale_id: str
    target_value: float
    source_observed_at: datetime
    target_observed_at: datetime
    market_context_id: str

    @field_validator("source_observed_at", "target_observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("cardinal calibration timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_pair(self) -> "CardinalCalibrationPair":
        required = (
            self.asset_id,
            self.source_id,
            self.native_scale_id,
            self.target_source_id,
            self.target_scale_id,
            self.market_context_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("cardinal calibration identifiers cannot be blank")
        if self.target_observed_at > self.source_observed_at:
            raise ValueError("target evidence cannot postdate source evidence")
        return self


class CardinalScaleTransform(FrozenModel):
    """Versioned challenger mapping from one provider-native scale to another.

    This object is deliberately not a ValueScale or a MarketPriceEstimate. It may
    be benchmarked and compared, but cannot become production Value authority by
    merely existing.
    """

    source_id: str
    native_scale_id: str
    target_source_id: str
    target_scale_id: str
    kind: CardinalTransformKind
    intercept: float
    slope: float
    model_version: str
    fitted_at: datetime
    evidence_through: datetime
    sample_size: int

    @field_validator("fitted_at", "evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("cardinal transform timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_transform(self) -> "CardinalScaleTransform":
        if self.slope <= 0:
            raise ValueError("cardinal challenger transform must be monotone increasing")
        if self.sample_size < 3:
            raise ValueError("cardinal challenger transform requires at least 3 training pairs")
        if self.evidence_through > self.fitted_at:
            raise ValueError("cardinal transform evidence cannot postdate fit time")
        required = (
            self.source_id,
            self.native_scale_id,
            self.target_source_id,
            self.target_scale_id,
            self.model_version,
        )
        if any(not value.strip() for value in required):
            raise ValueError("cardinal transform identifiers cannot be blank")
        return self

    def apply(self, value: float) -> float:
        feature = _feature(value, self.kind)
        return self.intercept + self.slope * feature


class CardinalTransformBenchmark(FrozenModel):
    source_id: str
    native_scale_id: str
    target_scale_id: str
    kind: CardinalTransformKind
    model_version: str
    sample_size: int
    mean_absolute_error: float
    root_mean_squared_error: float
    mean_signed_error: float
    evidence_through: datetime


def build_chronological_overlap_pairs(
    source_observations: tuple[NativeMarketMagnitudeObservation, ...],
    target_observations: tuple[NativeMarketMagnitudeObservation, ...],
) -> tuple[CardinalCalibrationPair, ...]:
    """Match assets without future leakage.

    For every source observation, use only the latest target observation for the
    same asset/context at or before the source timestamp. This lets research map
    one native scale to another while preserving point-in-time discipline.
    """

    target_history: dict[tuple[str, str], list[NativeMarketMagnitudeObservation]] = defaultdict(list)
    for row in target_observations:
        target_history[(row.asset_id, row.market_context_id)].append(row)
    for rows in target_history.values():
        rows.sort(key=lambda row: row.observed_at)

    pairs: list[CardinalCalibrationPair] = []
    for source in sorted(source_observations, key=lambda row: row.observed_at):
        candidates = target_history.get((source.asset_id, source.market_context_id), [])
        eligible = [row for row in candidates if row.observed_at <= source.observed_at]
        if not eligible:
            continue
        target = eligible[-1]
        pairs.append(
            CardinalCalibrationPair(
                asset_id=source.asset_id,
                source_id=source.source_id,
                native_scale_id=source.native_scale_id,
                native_value=source.value,
                target_source_id=target.source_id,
                target_scale_id=target.native_scale_id,
                target_value=target.value,
                source_observed_at=source.observed_at,
                target_observed_at=target.observed_at,
                market_context_id=source.market_context_id,
            )
        )
    return tuple(pairs)


def fit_cardinal_transform(
    pairs: tuple[CardinalCalibrationPair, ...],
    *,
    kind: CardinalTransformKind,
    fitted_at: datetime,
    model_version: str,
) -> CardinalScaleTransform:
    """Fit one monotone challenger using ordinary least squares.

    This is research infrastructure, not promotion logic. Competing transforms
    must be compared on chronological holdout evidence before any common scale is
    considered authoritative.
    """

    if fitted_at.tzinfo is None:
        raise ValueError("fitted_at must be timezone-aware")
    if len(pairs) < 3:
        raise ValueError("at least 3 cardinal calibration pairs are required")

    source_keys = {(row.source_id, row.native_scale_id) for row in pairs}
    target_keys = {(row.target_source_id, row.target_scale_id) for row in pairs}
    contexts = {row.market_context_id for row in pairs}
    if len(source_keys) != 1 or len(target_keys) != 1 or len(contexts) != 1:
        raise ValueError("cardinal transform fit requires one source scale, target scale, and market context")
    if any(row.source_observed_at > fitted_at or row.target_observed_at > fitted_at for row in pairs):
        raise ValueError("cardinal transform fit cannot use future evidence")

    xs = [_feature(row.native_value, kind) for row in pairs]
    ys = [row.target_value for row in pairs]
    x_bar = mean(xs)
    y_bar = mean(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    if denominator <= 0:
        raise ValueError("cardinal transform fit requires variation in native values")
    slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys, strict=True)) / denominator
    if slope <= 0:
        raise ValueError("fitted cardinal transform is not monotone increasing")
    intercept = y_bar - slope * x_bar

    source_id, native_scale_id = next(iter(source_keys))
    target_source_id, target_scale_id = next(iter(target_keys))
    return CardinalScaleTransform(
        source_id=source_id,
        native_scale_id=native_scale_id,
        target_source_id=target_source_id,
        target_scale_id=target_scale_id,
        kind=kind,
        intercept=intercept,
        slope=slope,
        model_version=model_version,
        fitted_at=fitted_at,
        evidence_through=max(max(row.source_observed_at, row.target_observed_at) for row in pairs),
        sample_size=len(pairs),
    )


def benchmark_cardinal_transform(
    transform: CardinalScaleTransform,
    holdout: tuple[CardinalCalibrationPair, ...],
) -> CardinalTransformBenchmark:
    """Score one frozen challenger on later, non-training matched evidence."""

    if not holdout:
        raise ValueError("cardinal transform benchmark requires holdout pairs")
    errors: list[float] = []
    evidence_times: list[datetime] = []
    for row in holdout:
        if (row.source_id, row.native_scale_id) != (transform.source_id, transform.native_scale_id):
            raise ValueError("holdout source scale does not match transform")
        if (row.target_source_id, row.target_scale_id) != (
            transform.target_source_id,
            transform.target_scale_id,
        ):
            raise ValueError("holdout target scale does not match transform")
        if row.source_observed_at <= transform.evidence_through:
            raise ValueError("holdout evidence must be later than transform training evidence")
        prediction = transform.apply(row.native_value)
        errors.append(prediction - row.target_value)
        evidence_times.append(row.source_observed_at)

    return CardinalTransformBenchmark(
        source_id=transform.source_id,
        native_scale_id=transform.native_scale_id,
        target_scale_id=transform.target_scale_id,
        kind=transform.kind,
        model_version=transform.model_version,
        sample_size=len(errors),
        mean_absolute_error=mean(abs(error) for error in errors),
        root_mean_squared_error=sqrt(mean(error * error for error in errors)),
        mean_signed_error=mean(errors),
        evidence_through=max(evidence_times),
    )


def _feature(value: float, kind: CardinalTransformKind) -> float:
    if kind == CardinalTransformKind.AFFINE:
        return value
    if value <= -1:
        raise ValueError("log-affine cardinal transform requires native values greater than -1")
    return log1p(value)
