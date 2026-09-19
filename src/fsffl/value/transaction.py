from __future__ import annotations

from math import sqrt
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .models import (
    MarketPriceEstimate,
    TransactionDirection,
    TransactionPriceEstimate,
    ValueDistribution,
)


class TransactionPriceMapping(FrozenModel):
    """Empirically calibrated market-to-clearing-price transformation.

    The directional offsets and residual uncertainty are evidence inputs learned
    from completed historical transactions. This class intentionally contains no
    team-fit, contender, negotiation, or recommendation logic.
    """

    acquire_offset: float
    sell_offset: float
    residual_stddev: Annotated[float, Field(ge=0)] = 0.0
    model_version: str
    evidence_through_season: Annotated[int, Field(ge=1900)]
    sample_size: Annotated[int, Field(ge=1)]
    market_context_id: str | None = None

    @model_validator(mode="after")
    def validate_mapping(self) -> "TransactionPriceMapping":
        if not self.model_version.strip():
            raise ValueError("model_version cannot be blank")
        if self.market_context_id is not None and not self.market_context_id.strip():
            raise ValueError("market_context_id cannot be blank")
        return self


def estimate_transaction_price(
    market_price: MarketPriceEstimate,
    mapping: TransactionPriceMapping,
    *,
    direction: TransactionDirection,
    as_of,
    model_version: str,
) -> TransactionPriceEstimate:
    """Estimate directional market clearing price from observed market evidence.

    NEXT-3 owns this economic estimate. The mapping must be calibrated separately
    from historical completed transactions. No fallback premium/discount is
    invented here when calibration evidence is absent.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if market_price.as_of > as_of:
        raise ValueError("transaction price cannot use market evidence observed after as_of")
    if (
        mapping.market_context_id is not None
        and mapping.market_context_id != market_price.market_context_id
    ):
        raise ValueError("transaction mapping was calibrated for a different market context")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    offset = (
        mapping.acquire_offset
        if direction == TransactionDirection.ACQUIRE
        else mapping.sell_offset
    )
    source = market_price.distribution
    mean = source.mean + offset
    variance = source.stddev**2 + mapping.residual_stddev**2

    # A deterministic offset preserves source quantiles exactly. Once residual
    # transaction uncertainty is introduced, quantiles require an explicit
    # residual distribution or simulation and are therefore left unset.
    if mapping.residual_stddev == 0:
        p10 = source.p10 + offset if source.p10 is not None else None
        p50 = source.p50 + offset if source.p50 is not None else None
        p90 = source.p90 + offset if source.p90 is not None else None
    else:
        p10 = p50 = p90 = None

    return TransactionPriceEstimate(
        asset_id=market_price.asset_id,
        asset_kind=market_price.asset_kind,
        direction=direction,
        distribution=ValueDistribution(
            mean=mean,
            stddev=sqrt(variance),
            p10=p10,
            p50=p50,
            p90=p90,
        ),
        scale=market_price.scale,
        as_of=as_of,
        market_context_id=market_price.market_context_id,
        model_version=model_version,
        liquidity_model_version=mapping.model_version,
    )
