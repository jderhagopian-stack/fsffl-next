from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import exp

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import ForecastEvidenceStrength, IntrinsicV1PlayerForecastPath
from fsffl.state.models import FrozenModel, PlayerState, Position
from fsffl.value.models import IntrinsicDynastyValueEstimate, ValueAssetKind, ValueDistribution, ValueScale


INTRINSIC_VALUE_V2_VERSION = "intrinsic-fundamental-career-value-v3"
INTRINSIC_VALUE_V2_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.70)
INTRINSIC_TERMINAL_MODEL_VERSION = "intrinsic-terminal-continuation-pedigree-v1"
INTRINSIC_DISPLAY_SCALE_VERSION = "intrinsic-dynasty-display-v3"

# Historical PIT 90th-percentile expected discounted career-production anchors after
# adding the governed post-Y3 continuation model. These are football-only scale
# anchors: no market price, replacement level, roster fit, owner behavior, or
# transaction data enters them.
_POSITION_PREMIUM_CAREER_ANCHOR: dict[Position, float] = {
    Position.QB: 507.603397,
    Position.RB: 248.867301,
    Position.WR: 236.010168,
    Position.TE: 161.181638,
}

# Expected discounted Y4-Y6 continuation per unit of governed Y3 production.
# The fallback is position-only. Pedigree cells are chronologically validated,
# 100-observation-shrunk residuals from the PIT PR #131 football evidence panel.
# Expanding-fold validation (2011-2017) improved continuation MAE in 7/7 folds,
# 43.881 -> 42.668 overall (2.76%), with positive aggregate improvement at every
# position. Other tested age/experience additions did not clear this final target
# robustly and are therefore not independently added here.
_POSITION_TERMINAL_FACTOR: dict[Position, float] = {
    Position.QB: 1.415355,
    Position.RB: 1.066644,
    Position.WR: 1.172313,
    Position.TE: 1.337047,
}
_PEDIGREE_TERMINAL_FACTOR: dict[tuple[Position, str], float] = {
    (Position.QB, "late"): 1.390491,
    (Position.QB, "mid"): 1.119118,
    (Position.QB, "early"): 1.464664,
    (Position.RB, "late"): 0.612746,
    (Position.RB, "mid"): 0.862962,
    (Position.RB, "early"): 1.338371,
    (Position.WR, "late"): 0.687983,
    (Position.WR, "mid"): 1.018094,
    (Position.WR, "early"): 1.605961,
    (Position.TE, "late"): 0.904837,
    (Position.TE, "mid"): 1.245851,
    (Position.TE, "early"): 1.620248,
}

# Fundamental score 100 is the historical premium-career anchor. This monotone,
# market-independent display curve maps that point to 7,500 and keeps an open
# elite tail. Historical football-only distribution checks put roughly the median
# near 38 raw units, 90th near 100, and 99th near 169.
_DISPLAY_DECAY_SCALE = 72.13475204444818

INTRINSIC_VALUE_V2_SCALE = ValueScale(
    scale_id="fsffl_intrinsic_fundamental_career",
    version="3",
    unit_label="position-normalized discounted expected fundamental career value",
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


class IntrinsicV2TerminalContribution(FrozenModel):
    year3_forecast_mean: float
    year3_forecast_stddev: float
    position_baseline_factor: float
    applied_factor: float
    pedigree_band: str | None = None
    pedigree_residual_value: float = 0.0
    continuation_value: float
    continuation_stddev: float
    model_version: str = INTRINSIC_TERMINAL_MODEL_VERSION


class IntrinsicValueV2Estimate(FrozenModel):
    player_id: str
    position: Position
    evaluation_as_of: datetime
    raw_discounted_y1_y3: float
    raw_terminal_value: float
    raw_fundamental_career_value: float
    raw_fundamental_stddev: float
    fundamental_value: float
    fundamental_stddev: float
    display_value: int
    confidence: IntrinsicV2Confidence
    model_version: str = INTRINSIC_VALUE_V2_VERSION
    display_scale_version: str = INTRINSIC_DISPLAY_SCALE_VERSION
    forecast_policy_version: str
    base_forecast_model_version: str
    terminal: IntrinsicV2TerminalContribution
    horizons: tuple[IntrinsicV2HorizonContribution, ...]

    @field_validator("evaluation_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluation_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_contract(self) -> "IntrinsicValueV2Estimate":
        if tuple(point.horizon_year for point in self.horizons) != (1, 2, 3):
            raise ValueError("Fundamental Intrinsic requires exactly Year 1, Year 2, and Year 3 Forecast inputs")
        if self.fundamental_value < 0 or not 0 <= self.display_value <= 10_000:
            raise ValueError("Fundamental Intrinsic values must be non-negative and display-bounded")
        return self


def _confidence(path: IntrinsicV1PlayerForecastPath) -> IntrinsicV2Confidence:
    strengths = [point.evidence_strength for point in path.horizons[1:]]
    if ForecastEvidenceStrength.LOW in strengths:
        return IntrinsicV2Confidence.LOW
    if all(strength == ForecastEvidenceStrength.MODERATE for strength in strengths):
        return IntrinsicV2Confidence.MODERATE
    return IntrinsicV2Confidence.HIGH


def _pedigree_band(player_state: PlayerState | None) -> str | None:
    if player_state is None:
        return None
    if player_state.draft_number is not None:
        if player_state.draft_number <= 86:
            return "early"
        if player_state.draft_number <= 173:
            return "mid"
        return "late"
    if player_state.draft_round is not None:
        if player_state.draft_round <= 3:
            return "early"
        if player_state.draft_round <= 5:
            return "mid"
        return "late"
    return None


def intrinsic_display_value(fundamental_value: float) -> int:
    """Normalize independent Fundamental Intrinsic onto the shared 0-10,000 language."""
    if fundamental_value <= 0:
        return 0
    value = 10_000.0 * (1.0 - exp(-fundamental_value / _DISPLAY_DECAY_SCALE))
    return min(10_000, max(0, round(value)))


def estimate_intrinsic_value_v2(
    *,
    player_path: IntrinsicV1PlayerForecastPath,
    player_state: PlayerState | None = None,
) -> IntrinsicValueV2Estimate:
    """Estimate team-independent long-term dynasty asset worth from football fundamentals.

    Years 1-3 consume the governed Forecast distribution exactly once. Value then
    adds an empirically calibrated terminal continuation representing expected
    discounted Years 4-6 football production. Draft pedigree is used only through
    its chronologically validated residual effect on that continuation after the
    complete Y1-Y3 Forecast path is known. Replacement level, Broad/League Market,
    Team Utility, owner behavior, and transaction outcomes are absent.

    Age/career state/survival continue to affect the coordinate through Forecast's
    governed multi-year distributions. Separate age/experience residual terms were
    tested against the final continuation target but did not improve robustly enough
    to justify another Value-layer adjustment, preventing double counting.
    """
    anchor = _POSITION_PREMIUM_CAREER_ANCHOR[player_path.position]
    contributions: list[IntrinsicV2HorizonContribution] = []
    y1_y3_mean = 0.0
    # Cross-horizon covariance is not published. Summing weighted SDs is the
    # conservative perfect-positive-dependence bound rather than false precision.
    y1_y3_stddev = 0.0
    for weight, horizon in zip(INTRINSIC_VALUE_V2_WEIGHTS, player_path.horizons, strict=True):
        weighted_mean = weight * max(0.0, horizon.distribution.mean)
        weighted_stddev = weight * horizon.distribution.stddev
        y1_y3_mean += weighted_mean
        y1_y3_stddev += weighted_stddev
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

    y3 = player_path.horizons[2].distribution
    baseline_factor = _POSITION_TERMINAL_FACTOR[player_path.position]
    pedigree_band = _pedigree_band(player_state)
    applied_factor = _PEDIGREE_TERMINAL_FACTOR.get(
        (player_path.position, pedigree_band), baseline_factor
    ) if pedigree_band is not None else baseline_factor
    baseline_continuation = max(0.0, y3.mean) * baseline_factor
    continuation = max(0.0, y3.mean) * applied_factor
    pedigree_residual = continuation - baseline_continuation
    continuation_sd = y3.stddev * applied_factor
    raw_career = y1_y3_mean + continuation
    raw_stddev = y1_y3_stddev + continuation_sd

    fundamental = 100.0 * raw_career / anchor
    fundamental_sd = 100.0 * raw_stddev / anchor
    terminal = IntrinsicV2TerminalContribution(
        year3_forecast_mean=y3.mean,
        year3_forecast_stddev=y3.stddev,
        position_baseline_factor=baseline_factor,
        applied_factor=applied_factor,
        pedigree_band=pedigree_band,
        pedigree_residual_value=pedigree_residual,
        continuation_value=continuation,
        continuation_stddev=continuation_sd,
    )
    return IntrinsicValueV2Estimate(
        player_id=player_path.player_id,
        position=player_path.position,
        evaluation_as_of=player_path.evaluation_as_of,
        raw_discounted_y1_y3=y1_y3_mean,
        raw_terminal_value=continuation,
        raw_fundamental_career_value=raw_career,
        raw_fundamental_stddev=raw_stddev,
        fundamental_value=fundamental,
        fundamental_stddev=fundamental_sd,
        display_value=intrinsic_display_value(fundamental),
        confidence=_confidence(player_path),
        forecast_policy_version=player_path.policy_version,
        base_forecast_model_version=player_path.base_forecast_model_version,
        terminal=terminal,
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
