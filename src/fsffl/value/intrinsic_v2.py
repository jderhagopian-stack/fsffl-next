from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import exp, log1p

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import ForecastEvidenceStrength, IntrinsicV1PlayerForecastPath
from fsffl.state.models import FrozenModel, PlayerState, Position
from fsffl.value.models import IntrinsicDynastyValueEstimate, ValueAssetKind, ValueDistribution, ValueScale


INTRINSIC_VALUE_V2_VERSION = "intrinsic-fundamental-career-value-v4"
INTRINSIC_VALUE_V2_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.85**2)
INTRINSIC_TERMINAL_MODEL_VERSION = "intrinsic-career-continuation-residual-v2"
INTRINSIC_DISPLAY_SCALE_VERSION = "intrinsic-dynasty-display-v4"
INTRINSIC_CALIBRATION_VERSION = "fundamental-intrinsic-residual-calibration-v1"

# Frozen from the reproducible PIT calibration on 8,196 examples (2005-2019).
# Each anchor is the football-only 90th percentile of six-season discounted
# realized production for the position. No market, replacement, roster, owner,
# or transaction evidence enters these anchors.
_POSITION_PREMIUM_CAREER_ANCHOR: dict[Position, float] = {
    Position.QB: 1047.4444288312498,
    Position.RB: 412.1524660625,
    Position.WR: 439.8505064812502,
    Position.TE: 291.60519133749995,
}

# Expected discounted post-Year-3 continuation per unit of discounted Y3
# production, fitted chronologically against six-season realized football output.
_POSITION_CONTINUATION_COEFFICIENT: dict[Position, float] = {
    Position.QB: 4.081432648866087,
    Position.RB: 4.75136298864317,
    Position.WR: 5.2555577103676425,
    Position.TE: 4.229937041212317,
}

# Pedigree is the smallest residual bundle that remained positive and stable after
# conditioning on the complete governed Y1/Y2/Y3 Forecast mean/uncertainty vector.
# These coefficients reconstruct the expected pedigree signal from Forecast; only
# the residual is allowed to enter Value. Position order for the dummies is RB/WR/TE.
_PEDIGREE_RESIDUALIZER: tuple[float, ...] = (
    0.2484781735505464,
    -0.12700456930531967,
    -0.06841075885449754,
    0.03180806595946706,
    1.1280967595880664,
    0.1363146597623892,
    -0.09238759750627423,
    -0.19708700895188297,
    -0.14843554731856134,
    -0.18572704938326556,
)
_PEDIGREE_RESIDUAL_INTERCEPT = -1.0825294742668998
_PEDIGREE_RESIDUAL_COEFFICIENT = 28.187525270792843

# Frozen football-only raw Intrinsic distribution anchors from the same PIT
# calibration. These make the customer coordinate readable on 0-10,000 without
# fitting to Broad Market or any league-specific price. Above the 99th percentile
# an asymptotic tail preserves separation among apex assets.
_DISPLAY_ANCHORS: tuple[tuple[float, int], ...] = (
    (0.0, 0),
    (2.5403076284015347, 1000),
    (11.47640196854105, 2500),
    (27.052355227573865, 4500),
    (46.86605715804196, 6500),
    (65.97299494625445, 8000),
    (92.30611891476637, 9000),
    (120.44077383478454, 9500),
)
_DISPLAY_TAIL_SCALE = 70.0

INTRINSIC_VALUE_V2_SCALE = ValueScale(
    scale_id="fsffl_intrinsic_fundamental_career",
    version="4",
    unit_label="football-only discounted long-term fundamental dynasty career value",
)


class IntrinsicV2Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class IntrinsicV2EvidenceState(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


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
    pedigree_score: float | None = None
    pedigree_forecast_explained: float | None = None
    pedigree_residual: float | None = None
    pedigree_residual_value: float = 0.0
    continuation_value: float
    continuation_stddev: float
    model_version: str = INTRINSIC_TERMINAL_MODEL_VERSION
    calibration_version: str = INTRINSIC_CALIBRATION_VERSION


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
    residual_fundamental_value: float = 0.0
    display_value: int
    confidence: IntrinsicV2Confidence
    evidence_state: IntrinsicV2EvidenceState
    evidence_note: str
    model_version: str = INTRINSIC_VALUE_V2_VERSION
    calibration_version: str = INTRINSIC_CALIBRATION_VERSION
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


def _pedigree_score(player_state: PlayerState | None) -> float | None:
    """Return the calibrated continuous pedigree coordinate when exact pick is known.

    Missing provider pedigree is not treated as known-undrafted. That preserves
    explicit missingness and prevents a fabricated negative Value adjustment.
    """
    if player_state is None or player_state.draft_number is None:
        return None
    pick = max(1, min(260, player_state.draft_number))
    return max(0.0, 1.0 - log1p(pick) / log1p(260.0))


def _forecast_conditioning_vector(
    player_path: IntrinsicV1PlayerForecastPath,
    *,
    anchor: float,
) -> tuple[float, ...]:
    means = tuple(max(0.0, point.distribution.mean) / anchor for point in player_path.horizons)
    sds = tuple(point.distribution.stddev / anchor for point in player_path.horizons)
    return (
        1.0,
        *means,
        *sds,
        1.0 if player_path.position == Position.RB else 0.0,
        1.0 if player_path.position == Position.WR else 0.0,
        1.0 if player_path.position == Position.TE else 0.0,
    )


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def intrinsic_display_value(fundamental_value: float) -> int:
    """Map frozen football-only Fundamental Intrinsic onto 0-10,000."""
    if fundamental_value <= 0:
        return 0
    for (x0, y0), (x1, y1) in zip(_DISPLAY_ANCHORS, _DISPLAY_ANCHORS[1:]):
        if fundamental_value <= x1:
            fraction = (fundamental_value - x0) / (x1 - x0)
            return min(10_000, max(0, round(y0 + fraction * (y1 - y0))))
    x99, y99 = _DISPLAY_ANCHORS[-1]
    tail = y99 + (10_000 - y99) * (1.0 - exp(-(fundamental_value - x99) / _DISPLAY_TAIL_SCALE))
    return min(9_999, max(y99, round(tail)))


def estimate_intrinsic_value_v2(
    *,
    player_path: IntrinsicV1PlayerForecastPath,
    player_state: PlayerState | None = None,
) -> IntrinsicValueV2Estimate:
    """Estimate team-independent long-term dynasty asset worth from football fundamentals.

    Years 1-3 consume the governed Forecast distributions once. A chronologically
    fitted post-Year-3 continuation term represents remaining career value through
    the six-season calibration target. Draft pedigree enters only as a residual:
    its Forecast-explained portion is removed before the validated Value coefficient
    is applied. Missing pedigree is neutral rather than silently treated as known
    poor pedigree. Replacement, market price, Team Utility, owner behavior, and
    transaction outcomes are absent.
    """
    anchor = _POSITION_PREMIUM_CAREER_ANCHOR[player_path.position]
    contributions: list[IntrinsicV2HorizonContribution] = []
    y1_y3_mean = 0.0
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
    continuation_coefficient = _POSITION_CONTINUATION_COEFFICIENT[player_path.position]
    terminal_weight = 0.85**3
    continuation = max(0.0, y3.mean) * terminal_weight * continuation_coefficient
    continuation_sd = y3.stddev * terminal_weight * continuation_coefficient
    raw_career = y1_y3_mean + continuation
    raw_stddev = y1_y3_stddev + continuation_sd
    base_fundamental = 100.0 * raw_career / anchor
    fundamental_sd = 100.0 * raw_stddev / anchor

    pedigree = _pedigree_score(player_state)
    pedigree_explained: float | None = None
    pedigree_residual: float | None = None
    pedigree_value = 0.0
    evidence_state = IntrinsicV2EvidenceState.COMPLETE
    evidence_note = "Full governed Forecast career distribution and exact draft-pick pedigree are available."
    if pedigree is None:
        evidence_state = IntrinsicV2EvidenceState.PARTIAL
        evidence_note = "Fundamental career value is available; exact draft-pick pedigree is unavailable, so no residual pedigree adjustment is fabricated."
    else:
        vector = _forecast_conditioning_vector(player_path, anchor=anchor)
        pedigree_explained = _dot(vector, _PEDIGREE_RESIDUALIZER)
        pedigree_residual = pedigree - pedigree_explained
        pedigree_value = _PEDIGREE_RESIDUAL_INTERCEPT + _PEDIGREE_RESIDUAL_COEFFICIENT * pedigree_residual

    fundamental = max(0.0, base_fundamental + pedigree_value)
    terminal = IntrinsicV2TerminalContribution(
        year3_forecast_mean=y3.mean,
        year3_forecast_stddev=y3.stddev,
        position_baseline_factor=continuation_coefficient,
        applied_factor=continuation_coefficient,
        pedigree_score=pedigree,
        pedigree_forecast_explained=pedigree_explained,
        pedigree_residual=pedigree_residual,
        pedigree_residual_value=pedigree_value,
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
        residual_fundamental_value=pedigree_value,
        display_value=intrinsic_display_value(fundamental),
        confidence=_confidence(player_path),
        evidence_state=evidence_state,
        evidence_note=evidence_note,
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
