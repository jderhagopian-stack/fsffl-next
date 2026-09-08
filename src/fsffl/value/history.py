from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .models import MarketPriceEstimate, ValueAssetKind, ValueScale


class MarketMovementStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MarketValueSnapshot(FrozenModel):
    """One genuinely retained point-in-time market estimate.

    The estimate remains the authoritative NEXT-3 Value object. ``recorded_at``
    records when the product persisted that object; it is not a substitute for
    the estimate's own point-in-time ``as_of`` timestamp.
    """

    estimate: MarketPriceEstimate
    recorded_at: datetime
    snapshot_schema_version: str = "next3-market-value-snapshot-v1"

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> "MarketValueSnapshot":
        if not self.snapshot_schema_version.strip():
            raise ValueError("snapshot_schema_version cannot be blank")
        if self.recorded_at < self.estimate.as_of:
            raise ValueError("recorded_at cannot predate market estimate as_of")
        return self


class MarketMovement(FrozenModel):
    """Same-scale point-in-time market movement over a requested lookback.

    ``delta`` is expressed only in the estimate's explicit ValueScale units. For
    a market-percentile scale that means percentile points in the underlying
    0..1 representation; Presentation may label that clearly but may not turn it
    into an additive asset-value claim.
    """

    asset_id: str
    asset_kind: ValueAssetKind
    status: MarketMovementStatus
    lookback_days: int
    target_as_of: datetime
    current_as_of: datetime
    prior_as_of: datetime | None = None
    current_value: float | None = None
    prior_value: float | None = None
    delta: float | None = None
    scale: ValueScale | None = None
    market_context_id: str | None = None
    unavailable_reason: str | None = None
    model_version: str = "next3-market-movement-v1"

    @model_validator(mode="after")
    def validate_movement(self) -> "MarketMovement":
        if self.lookback_days <= 0:
            raise ValueError("lookback_days must be positive")
        if self.target_as_of.tzinfo is None or self.current_as_of.tzinfo is None:
            raise ValueError("market movement timestamps must be timezone-aware")
        if not self.asset_id.strip() or not self.model_version.strip():
            raise ValueError("market movement identifiers cannot be blank")
        if self.status == MarketMovementStatus.AVAILABLE:
            required = (
                self.prior_as_of,
                self.current_value,
                self.prior_value,
                self.delta,
                self.scale,
                self.market_context_id,
            )
            if any(value is None for value in required):
                raise ValueError("available market movement requires comparable current and prior evidence")
            if self.unavailable_reason is not None:
                raise ValueError("available market movement cannot carry an unavailable reason")
        else:
            if self.unavailable_reason is None or not self.unavailable_reason.strip():
                raise ValueError("unavailable market movement requires an explicit reason")
            if any(value is not None for value in (self.prior_as_of, self.prior_value, self.delta)):
                raise ValueError("unavailable market movement cannot claim prior comparison evidence")
        return self


class MarketValueHistoryStore(Protocol):
    """Persistence boundary for retained current-market snapshots.

    Production adapters may use a durable database/object store. The Value layer
    depends only on this contract and never assumes in-process memory is durable.
    """

    def append(self, snapshot: MarketValueSnapshot) -> None: ...

    def history(
        self,
        *,
        asset_id: str,
        asset_kind: ValueAssetKind,
        scale: ValueScale,
        market_context_id: str,
        through: datetime,
    ) -> tuple[MarketValueSnapshot, ...]: ...


def calculate_market_movement(
    current: MarketPriceEstimate,
    snapshots: tuple[MarketValueSnapshot, ...],
    *,
    lookback_days: int = 30,
    tolerance_days: int = 5,
    model_version: str = "next3-market-movement-v1",
) -> MarketMovement:
    """Resolve movement only from genuine comparable retained snapshots.

    The resolver chooses the compatible prior snapshot nearest the requested
    lookback date, within ``tolerance_days``. It never fabricates history from a
    current snapshot, mixes market contexts/scales, or borrows Cardinal values.
    """

    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    if tolerance_days < 0:
        raise ValueError("tolerance_days must be non-negative")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    target = current.as_of - timedelta(days=lookback_days)
    tolerance = timedelta(days=tolerance_days)
    compatible = [
        snapshot
        for snapshot in snapshots
        if snapshot.estimate.asset_id == current.asset_id
        and snapshot.estimate.asset_kind == current.asset_kind
        and snapshot.estimate.scale == current.scale
        and snapshot.estimate.market_context_id == current.market_context_id
        and snapshot.estimate.as_of < current.as_of
        and abs(snapshot.estimate.as_of - target) <= tolerance
    ]
    if not compatible:
        return MarketMovement(
            asset_id=current.asset_id,
            asset_kind=current.asset_kind,
            status=MarketMovementStatus.UNAVAILABLE,
            lookback_days=lookback_days,
            target_as_of=target,
            current_as_of=current.as_of,
            current_value=current.distribution.mean,
            scale=current.scale,
            market_context_id=current.market_context_id,
            unavailable_reason=(
                "No retained comparable market snapshot exists within the requested lookback tolerance."
            ),
            model_version=model_version,
        )

    prior = min(
        compatible,
        key=lambda snapshot: (
            abs(snapshot.estimate.as_of - target),
            -snapshot.estimate.as_of.timestamp(),
        ),
    ).estimate
    return MarketMovement(
        asset_id=current.asset_id,
        asset_kind=current.asset_kind,
        status=MarketMovementStatus.AVAILABLE,
        lookback_days=lookback_days,
        target_as_of=target,
        current_as_of=current.as_of,
        prior_as_of=prior.as_of,
        current_value=current.distribution.mean,
        prior_value=prior.distribution.mean,
        delta=current.distribution.mean - prior.distribution.mean,
        scale=current.scale,
        market_context_id=current.market_context_id,
        model_version=model_version,
    )
