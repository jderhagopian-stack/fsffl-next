from __future__ import annotations

from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .models import MarketPriceEstimate, ValueDistribution


class MarketContextCalibration(FrozenModel):
    """Hierarchical market-context adjustment learned from historical evidence.

    NEXT-3 may adapt a broad market estimate to a league-format cohort and then
    to one league's observed market behavior. The shrinkage weights are explicit
    empirical outputs, not hidden runtime heuristics. Team-specific desirability
    is deliberately out of scope.
    """

    global_context_id: str
    format_context_id: str | None = None
    league_context_id: str | None = None
    format_offset: float = 0.0
    league_offset: float = 0.0
    format_shrinkage_weight: Annotated[float, Field(ge=0, le=1)] = 0.0
    league_shrinkage_weight: Annotated[float, Field(ge=0, le=1)] = 0.0
    residual_stddev: Annotated[float, Field(ge=0)] = 0.0
    model_version: str
    evidence_through: datetime
    format_sample_size: Annotated[int, Field(ge=0)] = 0
    league_sample_size: Annotated[int, Field(ge=0)] = 0

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_calibration(self) -> "MarketContextCalibration":
        if not self.global_context_id.strip() or not self.model_version.strip():
            raise ValueError("market-context calibration identifiers cannot be blank")
        if self.format_context_id is None:
            if self.format_sample_size != 0 or self.format_shrinkage_weight != 0 or self.format_offset != 0:
                raise ValueError("format adjustment evidence requires format_context_id")
        elif not self.format_context_id.strip():
            raise ValueError("format_context_id cannot be blank")
        if self.league_context_id is None:
            if self.league_sample_size != 0 or self.league_shrinkage_weight != 0 or self.league_offset != 0:
                raise ValueError("league adjustment evidence requires league_context_id")
        elif not self.league_context_id.strip():
            raise ValueError("league_context_id cannot be blank")
        if self.format_shrinkage_weight > 0 and self.format_sample_size == 0:
            raise ValueError("format shrinkage weight requires format evidence")
        if self.league_shrinkage_weight > 0 and self.league_sample_size == 0:
            raise ValueError("league shrinkage weight requires league evidence")
        return self


def apply_market_context(
    market_price: MarketPriceEstimate,
    calibration: MarketContextCalibration,
    *,
    as_of: datetime,
    model_version: str,
) -> MarketPriceEstimate:
    """Adapt a broad market estimate using explicit hierarchical evidence.

    The effective adjustment is the empirically estimated format offset shrunk
    toward the global market plus the league residual shrunk toward its format
    cohort. No roster, contender, or owner-specific information is permitted.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if market_price.as_of > as_of:
        raise ValueError("market context cannot use a market estimate observed after as_of")
    if calibration.evidence_through > as_of:
        raise ValueError("market context calibration contains future evidence")
    if market_price.market_context_id != calibration.global_context_id:
        raise ValueError("market estimate does not match calibration global context")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    adjustment = (
        calibration.format_shrinkage_weight * calibration.format_offset
        + calibration.league_shrinkage_weight * calibration.league_offset
    )
    source = market_price.distribution
    variance = source.stddev**2 + calibration.residual_stddev**2

    if calibration.league_context_id is not None:
        target_context = calibration.league_context_id
    elif calibration.format_context_id is not None:
        target_context = calibration.format_context_id
    else:
        target_context = calibration.global_context_id

    if calibration.residual_stddev == 0:
        p10 = source.p10 + adjustment if source.p10 is not None else None
        p50 = source.p50 + adjustment if source.p50 is not None else None
        p90 = source.p90 + adjustment if source.p90 is not None else None
    else:
        p10 = p50 = p90 = None

    return MarketPriceEstimate(
        asset_id=market_price.asset_id,
        asset_kind=market_price.asset_kind,
        distribution=ValueDistribution(
            mean=source.mean + adjustment,
            stddev=sqrt(variance),
            p10=p10,
            p50=p50,
            p90=p90,
        ),
        scale=market_price.scale,
        as_of=as_of,
        market_context_id=target_context,
        model_version=model_version,
        evidence_sources=market_price.evidence_sources,
    )
