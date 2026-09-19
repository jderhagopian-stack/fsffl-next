from __future__ import annotations

from math import sqrt
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .models import (
    ForecastValueInput,
    IntrinsicDynastyValueEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
)


class ForecastValueMapping(FrozenModel):
    """Empirically fitted conversion from a football forecast to economic value.

    The coefficients are evidence, not defaults. NEXT-3 owns their calibration;
    this object makes the model form/version/provenance explicit so callers cannot
    silently turn football points into dynasty value with an unexplained weight.
    """

    forecast_model_version: str | None = None
    economic_units_per_forecast_unit: Annotated[float, Field(ge=0)]
    intercept: float = 0.0
    residual_stddev: Annotated[float, Field(ge=0)] = 0.0
    model_version: str
    evidence_through_season: Annotated[int, Field(ge=1900)]
    sample_size: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def validate_identifiers(self) -> "ForecastValueMapping":
        if not self.model_version.strip():
            raise ValueError("model_version cannot be blank")
        if self.forecast_model_version is not None and not self.forecast_model_version.strip():
            raise ValueError("forecast_model_version cannot be blank")
        return self


def estimate_intrinsic_player_value(
    forecast: ForecastValueInput,
    mapping: ForecastValueMapping,
    *,
    scale: ValueScale,
    as_of,
    model_version: str,
) -> IntrinsicDynastyValueEstimate:
    """Convert immutable NEXT-2 football evidence into intrinsic economic value.

    This is deliberately a transparent calibrated baseline. The affine form has
    exact first/second-moment propagation. More flexible challengers may replace
    it only through chronological validation; they should not be hidden here.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if forecast.forecast_as_of > as_of:
        raise ValueError("intrinsic value cannot use a forecast issued after value as_of")
    if (
        mapping.forecast_model_version is not None
        and mapping.forecast_model_version != forecast.forecast_model_version
    ):
        raise ValueError("forecast mapping was calibrated for a different forecast model version")

    slope = mapping.economic_units_per_forecast_unit
    source = forecast.distribution
    mean = mapping.intercept + slope * source.mean
    variance = (slope * source.stddev) ** 2 + mapping.residual_stddev**2

    # Mapping provider quantiles remains valid only for a deterministic monotone
    # affine conversion. Once conversion residual uncertainty is present, the
    # combined quantiles require an explicit residual distribution or sampling.
    if mapping.residual_stddev == 0:
        p10 = mapping.intercept + slope * source.p10 if source.p10 is not None else None
        p50 = mapping.intercept + slope * source.p50 if source.p50 is not None else None
        p90 = mapping.intercept + slope * source.p90 if source.p90 is not None else None
    else:
        p10 = p50 = p90 = None

    return IntrinsicDynastyValueEstimate(
        asset_id=forecast.player_id,
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(
            mean=mean,
            stddev=sqrt(variance),
            p10=p10,
            p50=p50,
            p90=p90,
        ),
        scale=scale,
        as_of=as_of,
        model_version=model_version,
        conversion_model_version=mapping.model_version,
        forecast_model_versions=(forecast.forecast_model_version,),
    )
