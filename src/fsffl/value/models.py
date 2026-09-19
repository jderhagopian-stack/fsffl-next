from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.state.models import FrozenModel


class ValueAssetKind(StrEnum):
    PLAYER = "player"
    PICK = "pick"
    FAAB = "faab"


class TransactionDirection(StrEnum):
    ACQUIRE = "acquire"
    SELL = "sell"


class ValueScale(FrozenModel):
    """Versioned unit system for economic values.

    A numeric value is not comparable to another merely because both are floats.
    Downstream code should compare values only when `scale_id` and `version` match.
    """

    scale_id: str
    version: str
    unit_label: str

    @model_validator(mode="after")
    def require_nonblank_identifiers(self) -> "ValueScale":
        for name, value in (
            ("scale_id", self.scale_id),
            ("version", self.version),
            ("unit_label", self.unit_label),
        ):
            if not value.strip():
                raise ValueError(f"{name} cannot be blank")
        return self


class ValueDistribution(FrozenModel):
    """Economic outcome distribution on one explicit ValueScale."""

    mean: float
    stddev: Annotated[float, Field(ge=0)] = 0.0
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None

    @model_validator(mode="after")
    def ordered_quantiles(self) -> "ValueDistribution":
        quantiles = [value for value in (self.p10, self.p50, self.p90) if value is not None]
        if quantiles != sorted(quantiles):
            raise ValueError("value quantiles must be ordered p10 <= p50 <= p90")
        return self


class ForecastValueInput(FrozenModel):
    """Immutable NEXT-2 evidence consumed by intrinsic valuation.

    NEXT-3 may transform this evidence into economic value but may not write back
    to, rescale, or otherwise mutate the underlying football forecast.
    """

    player_id: str
    horizon: ForecastHorizon
    distribution: ForecastDistribution
    forecast_model_version: str
    forecast_as_of: datetime

    @field_validator("forecast_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("forecast_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_identifiers(self) -> "ForecastValueInput":
        if not self.player_id.strip():
            raise ValueError("player_id cannot be blank")
        if not self.forecast_model_version.strip():
            raise ValueError("forecast_model_version cannot be blank")
        return self


class MarketPriceEstimate(FrozenModel):
    """Observed/inferred exchange price, not intrinsic truth."""

    asset_id: str
    asset_kind: ValueAssetKind
    distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    market_context_id: str
    model_version: str
    evidence_sources: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_market_estimate(self) -> "MarketPriceEstimate":
        _require_nonblank_value_fields(
            self.asset_id,
            self.market_context_id,
            self.model_version,
        )
        return self


class IntrinsicDynastyValueEstimate(FrozenModel):
    """Modeled economic worth of expected football outcomes and optionality.

    Market price may be an explicitly governed prior/input to an intrinsic model,
    but this object remains a distinct estimate and records the conversion model
    that produced it.
    """

    asset_id: str
    asset_kind: ValueAssetKind
    distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    model_version: str
    conversion_model_version: str
    forecast_model_versions: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_intrinsic_estimate(self) -> "IntrinsicDynastyValueEstimate":
        _require_nonblank_value_fields(
            self.asset_id,
            self.model_version,
            self.conversion_model_version,
        )
        return self


class PickValueEstimate(FrozenModel):
    """Distributional draft-capital value before the pick becomes a player."""

    asset_id: str
    distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    draft_season: Annotated[int, Field(ge=1900)]
    round: Annotated[int, Field(ge=1)]
    model_version: str
    class_strength_model_version: str
    slot_uncertainty_model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_pick_estimate(self) -> "PickValueEstimate":
        _require_nonblank_value_fields(
            self.asset_id,
            self.model_version,
            self.class_strength_model_version,
            self.slot_uncertainty_model_version,
        )
        return self


class TransactionPriceEstimate(FrozenModel):
    """Estimated exchange price required to execute an acquisition or sale.

    This is not team utility or a recommendation. It describes expected market
    clearing cost/liquidity on a market scale; team-specific desirability belongs
    downstream.
    """

    asset_id: str
    asset_kind: ValueAssetKind
    direction: TransactionDirection
    distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    market_context_id: str
    model_version: str
    liquidity_model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_transaction_estimate(self) -> "TransactionPriceEstimate":
        _require_nonblank_value_fields(
            self.asset_id,
            self.market_context_id,
            self.model_version,
            self.liquidity_model_version,
        )
        return self


class AssetValueProfile(FrozenModel):
    """Non-collapsing view of the distinct NEXT-3 value concepts for one asset."""

    asset_id: str
    asset_kind: ValueAssetKind
    market_price: MarketPriceEstimate | None = None
    intrinsic_value: IntrinsicDynastyValueEstimate | None = None
    pick_value: PickValueEstimate | None = None
    acquisition_price: TransactionPriceEstimate | None = None
    sale_price: TransactionPriceEstimate | None = None

    @model_validator(mode="after")
    def consistent_asset_identity_and_roles(self) -> "AssetValueProfile":
        if not self.asset_id.strip():
            raise ValueError("asset_id cannot be blank")

        typed_estimates = (
            self.market_price,
            self.intrinsic_value,
            self.acquisition_price,
            self.sale_price,
        )
        for estimate in typed_estimates:
            if estimate is None:
                continue
            if estimate.asset_id != self.asset_id or estimate.asset_kind != self.asset_kind:
                raise ValueError("all value estimates must describe the profile asset")

        if self.pick_value is not None:
            if self.asset_kind != ValueAssetKind.PICK:
                raise ValueError("pick_value may only be attached to a pick asset")
            if self.pick_value.asset_id != self.asset_id:
                raise ValueError("pick_value must describe the profile asset")

        if (
            self.acquisition_price is not None
            and self.acquisition_price.direction != TransactionDirection.ACQUIRE
        ):
            raise ValueError("acquisition_price must use ACQUIRE direction")
        if self.sale_price is not None and self.sale_price.direction != TransactionDirection.SELL:
            raise ValueError("sale_price must use SELL direction")
        return self


def comparable_values(
    left_distribution: ValueDistribution,
    left_scale: ValueScale,
    right_distribution: ValueDistribution,
    right_scale: ValueScale,
) -> tuple[ValueDistribution, ValueDistribution]:
    """Fail closed when callers try to compare values on different scales."""

    if left_scale != right_scale:
        raise ValueError("economic values are comparable only on the same value scale/version")
    return left_distribution, right_distribution


def _require_nonblank_value_fields(*values: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError("value estimate identifiers cannot be blank")
