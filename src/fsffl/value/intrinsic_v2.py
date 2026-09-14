from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import exp, log1p

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import ForecastEvidenceStrength, IntrinsicV1PlayerForecastPath
from fsffl.state.models import FrozenModel, PlayerState, Position
from fsffl.value.models import IntrinsicDynastyValueEstimate, ValueAssetKind, ValueDistribution, ValueScale

from .intrinsic_economics import INTRINSIC_STRUCTURAL_ECONOMICS_VERSION


INTRINSIC_VALUE_V2_VERSION = "intrinsic-fundamental-economic-value-v6"
INTRINSIC_VALUE_V2_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.85**2)
INTRINSIC_TERMINAL_MODEL_VERSION = "intrinsic-career-continuation-residual-v4"
INTRINSIC_DISPLAY_SCALE_VERSION = "intrinsic-dynasty-display-v6-economic-reference"
INTRINSIC_CALIBRATION_VERSION = "fundamental-intrinsic-production-parity-v1"

# Production-parity calibration still residualizes draft pedigree in normalized
# position units. These football-only anchors exist solely to convert that
# validated residual contribution back into shared football-production units;
# they do not normalize the final cross-position coordinate.
_POSITION_RESIDUAL_UNIT_ANCHOR: dict[Position, float] = {
    Position.QB: 1016.0174027306249,
    Position.RB: 407.56763725000013,
    Position.WR: 416.2464794999999,
    Position.TE: 278.95638595624996,
}

# Parent post-Y3 factors recalibrated against the exact deployed Forecast horizon
# policy: PIT Model-A Y1; QB career-state when frozen PIT evidence exists; bounded
# RB/TE transitions; WR Y2 carry-forward and bounded Y3.
_POSITION_CONTINUATION_COEFFICIENT: dict[Position, float] = {
    Position.QB: 3.04477622642943,
    Position.RB: 4.303817924177665,
    Position.WR: 6.143984964367542,
    Position.TE: 5.817300974838888,
}

# Aging-only cells from the same production-parity calibration. They are not
# forced monotonic. The recalibrated evidence itself resolves the prior oddities:
# WR veteran and late tails taper below younger cohorts and TE late < veteran.
_AGING_CONTINUATION_COEFFICIENT: dict[tuple[Position, str], float] = {
    (Position.RB, "veteran"): 3.950333600958593,
    (Position.RB, "late"): 2.7510651150227448,
    (Position.WR, "veteran"): 6.004984105473204,
    (Position.WR, "late"): 2.6770751749625927,
    (Position.TE, "veteran"): 5.618822091672501,
    (Position.TE, "late"): 4.858769764287097,
}

# Pedigree remains the only promoted residual signal. Coefficients are refitted
# against the production-parity Y1/Y2/Y3 Forecast mean/uncertainty vector.
_PEDIGREE_RESIDUALIZER: tuple[float, ...] = (
    0.20196416032092881,
    -0.3623290279557141,
    0.13015925666996386,
    1.1964187061171963,
    2.492600343793169,
    -1.5201173612975936,
    -0.17258143695061712,
    -0.14174301358417163,
    -0.10544604937416151,
    -0.13242423855480032,
)
_PEDIGREE_RESIDUAL_INTERCEPT = -2.2638022612451145
_PEDIGREE_RESIDUAL_COEFFICIENT = 28.101305498458085

# Stable football/rules-only customer scale. The reference universe is the top
# 216 predicted economic assets per PIT season: 12 teams x 18 active roster
# places, with no positional quota. The raw cut points therefore emerge from a
# dynasty-relevant roster-capacity universe rather than the full NFL population,
# current-player values, or any market source.
_DISPLAY_ANCHORS: tuple[tuple[float, int], ...] = (
    (0.0, 0),
    (121.44812067567622, 2000),
    (153.5200104805043, 4500),
    (241.62841665403283, 6500),
    (398.4623347230747, 8000),
    (860.2953473881821, 9000),
    (1431.1653907320676, 9400),
    (1783.2893275391143, 9700),
)
_DISPLAY_TAIL_SCALE = 1783.2893275391143

INTRINSIC_VALUE_V2_SCALE = ValueScale(
    scale_id="fsffl_intrinsic_fundamental_economic",
    version="6",
    unit_label="league-structural long-term fundamental dynasty asset value",
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
    pre_structural_fundamental_value: float
    fundamental_value: float
    fundamental_stddev: float
    residual_fundamental_value: float = 0.0
    structural_factor: float = 1.0
    structural_starter_demand: int = 0
    structural_effective_supply: float = 0.0
    display_value: int
    confidence: IntrinsicV2Confidence
    evidence_state: IntrinsicV2EvidenceState
    evidence_note: str
    model_version: str = INTRINSIC_VALUE_V2_VERSION
    calibration_version: str = INTRINSIC_CALIBRATION_VERSION
    display_scale_version: str = INTRINSIC_DISPLAY_SCALE_VERSION
    structural_economics_version: str = INTRINSIC_STRUCTURAL_ECONOMICS_VERSION
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
        if self.fundamental_value < 0 or self.pre_structural_fundamental_value < 0 or not 0 <= self.display_value <= 10_000:
            raise ValueError("Fundamental Intrinsic values must be non-negative and display-bounded")
        if self.structural_factor <= 0 or self.structural_starter_demand < 0 or self.structural_effective_supply < 0:
            raise ValueError("structural economics must be positive/non-negative")
        return self


def _confidence(path: IntrinsicV1PlayerForecastPath) -> IntrinsicV2Confidence:
    strengths = [point.evidence_strength for point in path.horizons[1:]]
    if ForecastEvidenceStrength.LOW in strengths:
        return IntrinsicV2Confidence.LOW
    if all(strength == ForecastEvidenceStrength.MODERATE for strength in strengths):
        return IntrinsicV2Confidence.MODERATE
    return IntrinsicV2Confidence.HIGH


def _pedigree_score(player_state: PlayerState | None) -> float | None:
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


def _non_qb_age_band(position: Position, age: float | None) -> str | None:
    if age is None or position == Position.QB:
        return None
    if age <= 23:
        return "young"
    if age <= 26:
        return "prime"
    if age <= 29:
        return "veteran"
    return "late"


def _continuation_factor(position: Position, player_state: PlayerState | None) -> float:
    parent = _POSITION_CONTINUATION_COEFFICIENT[position]
    age = player_state.age_years if player_state is not None else None
    band = _non_qb_age_band(position, age)
    if band is None:
        return parent
    return _AGING_CONTINUATION_COEFFICIENT.get((position, band), parent)


def intrinsic_display_value(fundamental_value: float) -> int:
    """Map economic Fundamental Intrinsic magnitude onto the customer 0-10,000 scale."""
    if fundamental_value <= 0:
        return 0
    for (x0, y0), (x1, y1) in zip(_DISPLAY_ANCHORS, _DISPLAY_ANCHORS[1:]):
        if fundamental_value <= x1:
            fraction = (fundamental_value - x0) / (x1 - x0)
            return min(10_000, max(0, round(y0 + fraction * (y1 - y0))))
    x_apex, y_apex = _DISPLAY_ANCHORS[-1]
    tail = y_apex + (10_000 - y_apex) * (1.0 - exp(-(fundamental_value - x_apex) / _DISPLAY_TAIL_SCALE))
    return min(9_999, max(y_apex, round(tail)))


def estimate_intrinsic_value_v2(
    *,
    player_path: IntrinsicV1PlayerForecastPath,
    player_state: PlayerState | None = None,
    structural_factor: float = 1.0,
    structural_starter_demand: int = 0,
    structural_effective_supply: float = 0.0,
) -> IntrinsicValueV2Estimate:
    """Estimate team-independent long-term dynasty asset worth from fundamentals.

    Football production remains Forecast-owned. Value discounts governed Y1-Y3,
    adds the validated state-conditioned continuation and residual draft pedigree,
    then applies one deterministic league-wide positional-economic conversion from
    lineup demand versus production-concentration supply. No individual team,
    replacement surplus, market price, owner behavior, or transaction evidence is
    accepted by this estimator.
    """
    if structural_factor <= 0:
        raise ValueError("structural_factor must be positive")
    if structural_starter_demand < 0 or structural_effective_supply < 0:
        raise ValueError("structural demand/supply must be non-negative")

    residual_unit_anchor = _POSITION_RESIDUAL_UNIT_ANCHOR[player_path.position]
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
    parent_factor = _POSITION_CONTINUATION_COEFFICIENT[player_path.position]
    applied_factor = _continuation_factor(player_path.position, player_state)
    terminal_weight = 0.85**3
    continuation = max(0.0, y3.mean) * terminal_weight * applied_factor
    continuation_sd = y3.stddev * terminal_weight * applied_factor
    raw_career = y1_y3_mean + continuation
    raw_stddev = y1_y3_stddev + continuation_sd

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
        vector = _forecast_conditioning_vector(player_path, anchor=residual_unit_anchor)
        pedigree_explained = _dot(vector, _PEDIGREE_RESIDUALIZER)
        pedigree_residual = pedigree - pedigree_explained
        normalized_pedigree_value = _PEDIGREE_RESIDUAL_INTERCEPT + _PEDIGREE_RESIDUAL_COEFFICIENT * pedigree_residual
        pedigree_value = normalized_pedigree_value * residual_unit_anchor / 100.0

    pre_structural = max(0.0, raw_career + pedigree_value)
    fundamental = pre_structural * structural_factor
    fundamental_stddev = raw_stddev * structural_factor
    economic_residual = pedigree_value * structural_factor
    evidence_note += (
        f" League-wide structural factor {structural_factor:.3f} converts football contribution into asset economics "
        f"from {structural_starter_demand} neutral starters and {structural_effective_supply:.1f} effective production-supply units."
        if structural_starter_demand > 0 and structural_effective_supply > 0
        else " Structural factor is neutral because league-wide structural evidence was not supplied."
    )

    terminal = IntrinsicV2TerminalContribution(
        year3_forecast_mean=y3.mean,
        year3_forecast_stddev=y3.stddev,
        position_baseline_factor=parent_factor,
        applied_factor=applied_factor,
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
        pre_structural_fundamental_value=pre_structural,
        fundamental_value=fundamental,
        fundamental_stddev=fundamental_stddev,
        residual_fundamental_value=economic_residual,
        structural_factor=structural_factor,
        structural_starter_demand=structural_starter_demand,
        structural_effective_supply=structural_effective_supply,
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
