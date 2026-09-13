from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import exp, sqrt

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import ForecastEvidenceStrength, IntrinsicV1PlayerForecastPath
from fsffl.state.models import FrozenModel, Position
from fsffl.value.models import IntrinsicDynastyValueEstimate, ValueAssetKind, ValueDistribution, ValueScale


INTRINSIC_VALUE_V2_VERSION = "intrinsic-fundamental-career-value-v2"
INTRINSIC_VALUE_V2_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.70)
INTRINSIC_DISPLAY_SCALE_VERSION = "intrinsic-dynasty-display-v2"

# Fixed football-only reference anchors: historical 90th-percentile discounted
# three-year Forecast production from the governed PR #131 PIT research universe.
# They normalize scoring magnitude across positions without using market price,
# lineup replacement, roster need, or owner behavior.
_POSITION_PREMIUM_PRODUCTION_ANCHOR: dict[Position, float] = {
    Position.QB: 372.30,
    Position.RB: 182.84,
    Position.WR: 161.79,
    Position.TE: 105.82,
}

# A fundamental score of 100 is the fixed historical premium-production anchor.
# The display curve places that anchor at 7,500 while preserving an open elite
# tail.  scale = 100 / ln(4), expressed as a frozen versioned constant.
_DISPLAY_DECAY_SCALE = 72.13475204444818

INTRINSIC_VALUE_V2_SCALE = ValueScale(
    scale_id="fsffl_intrinsic_fundamental_career",
    version="2",
    unit_label="position-normalized discounted expected career production",
)


class IntrinsicV2Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class IntrinsicV2HorizonContribution(FrozenModel):
    horizon_year: int
    forecast_mean: float
    forecast_stddev: float
    weight: float
    weighted_mean: float
    weighted_stddev: float
    forecast_evidence_strength: ForecastEvidenceStrength
    forecast_method: str


class IntrinsicValueV2Estimate(FrozenModel):
    player_id: str
    position: Position
    evaluation_as_of: datetime
    raw_discounted_production: float
    raw_discounted_stddev: float
    fundamental_value: float
    fundamental_stddev: float
    display_value: int
    confidence: IntrinsicV2Confidence
    model_version: str = INTRINSIC_VALUE_V2_VERSION
    display_scale_version: str = INTRINSIC_DISPLAY_SCALE_VERSION
    forecast_policy_version: str
    base_forecast_model_version: str
    horizons: tuple[IntrinsicV2HorizonContribution, ...]

    @field_validator("evaluation_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluation_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_three_horizons(self) -> "IntrinsicValueV2Estimate":
        if tuple(point.horizon_year for point in self.horizons) != (1, 2, 3):
            raise ValueError("Intrinsic v2 requires exactly three horizon contributions")
        if self.fundamental_value < 0 or not 0 <= self.display_value <= 10_000:
            raise ValueError("Intrinsic v2 values must be non-negative and display-bounded")
        return self


def _confidence(path: IntrinsicV1PlayerForecastPath) -> IntrinsicV2Confidence:
    strengths = [point.evidence_strength for point in path.horizons[1:]]
    if ForecastEvidenceStrength.LOW in strengths:
        return IntrinsicV2Confidence.LOW
    if all(strength == ForecastEvidenceStrength.MODERATE for strength in strengths):
        return IntrinsicV2Confidence.MODERATE
    return IntrinsicV2Confidence.HIGH


def intrinsic_display_value(fundamental_value: float) -> int:
    """Market-independent monotone normalization onto the customer 0-10,000 scale."""
    if fundamental_value <= 0:
        return 0
    value = 10_000.0 * (1.0 - exp(-fundamental_value / _DISPLAY_DECAY_SCALE))
    return min(10_000, max(0, round(value)))


def estimate_intrinsic_value_v2(*, player_path: IntrinsicV1PlayerForecastPath) -> IntrinsicValueV2Estimate:
    """Estimate team-independent fundamental dynasty asset value from Forecast.

    The mean is discounted expected multi-year football production. Forecast owns
    age, role, survival, trajectory, and uncertainty. Value only applies time
    weighting plus a fixed football-only positional magnitude normalization.
    Replacement level, market price, Team Utility, and owner behavior are absent.
    """
    anchor = _POSITION_PREMIUM_PRODUCTION_ANCHOR[player_path.position]
    contributions: list[IntrinsicV2HorizonContribution] = []
    raw_mean = 0.0
    # Horizon outcomes are positively related and the production contract does
    # not publish cross-horizon covariance. Use the conservative perfect-positive
    # dependence bound instead of pretending independence and false precision.
    raw_stddev = 0.0
    for weight, horizon in zip(INTRINSIC_VALUE_V2_WEIGHTS, player_path.horizons, strict=True):
        weighted_mean = weight * max(0.0, horizon.distribution.mean)
        weighted_stddev = weight * horizon.distribution.stddev
        raw_mean += weighted_mean
        raw_stddev += weighted_stddev
        contributions.append(
            IntrinsicV2HorizonContribution(
                horizon_year=horizon.horizon_year,
                forecast_mean=horizon.distribution.mean,
                forecast_stddev=horizon.distribution.stddev,
                weight=weight,
                weighted_mean=weighted_mean,
                weighted_stddev=weighted_stddev,
                forecast_evidence_strength=horizon.evidence_strength,
                forecast_method=horizon.method.value,
            )
        )

    fundamental = 100.0 * raw_mean / anchor
    fundamental_sd = 100.0 * raw_stddev / anchor
    return IntrinsicValueV2Estimate(
        player_id=player_path.player_id,
        position=player_path.position,
        evaluation_as_of=player_path.evaluation_as_of,
        raw_discounted_production=raw_mean,
        raw_discounted_stddev=raw_stddev,
        fundamental_value=fundamental,
        fundamental_stddev=fundamental_sd,
        display_value=intrinsic_display_value(fundamental),
        confidence=_confidence(player_path),
        forecast_policy_version=player_path.policy_version,
        base_forecast_model_version=player_path.base_forecast_model_version,
        horizons=tuple(contributions),
    )


def as_intrinsic_dynasty_value_estimate(estimate: IntrinsicValueV2Estimate) -> IntrinsicDynastyValueEstimate:
    return IntrinsicDynastyValueEstimate(
        asset_id=estimate.player_id,
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=estimate.fundamental_value, stddev=estimate.fundamental_stddev),
        scale=INTRINSIC_VALUE_V2_SCALE,
        as_of=estimate.evaluation_as_of,
        model_version=estimate.model_version,
        conversion_model_version=INTRINSIC_DISPLAY_SCALE_VERSION,
        forecast_model_versions=(estimate.base_forecast_model_version, estimate.forecast_policy_version),
    )
