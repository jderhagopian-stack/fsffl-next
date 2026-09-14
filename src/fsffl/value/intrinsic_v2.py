from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import exp, log1p

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import ForecastEvidenceStrength, IntrinsicV1PlayerForecastPath
from fsffl.state.models import FrozenModel, PlayerState, Position
from fsffl.value.models import IntrinsicDynastyValueEstimate, ValueAssetKind, ValueDistribution, ValueScale


INTRINSIC_VALUE_V2_VERSION = "intrinsic-fundamental-career-value-v5"
INTRINSIC_VALUE_V2_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.85**2)
INTRINSIC_TERMINAL_MODEL_VERSION = "intrinsic-career-continuation-residual-v3"
INTRINSIC_DISPLAY_SCALE_VERSION = "intrinsic-dynasty-display-v5"
INTRINSIC_CALIBRATION_VERSION = "fundamental-intrinsic-shared-career-v5c"

# The v4 calibration normalized each position separately before fitting the
# residual pedigree term. These football-only anchors remain solely to convert
# that already-validated residual contribution back into shared fantasy-point
# units. They no longer normalize the final Fundamental Intrinsic coordinate.
_POSITION_RESIDUAL_UNIT_ANCHOR: dict[Position, float] = {
    Position.QB: 1047.4444288312498,
    Position.RB: 412.1524660625,
    Position.WR: 439.8505064812502,
    Position.TE: 291.60519133749995,
}

# Parent continuation factors from the reproducible PIT calibration.
_POSITION_CONTINUATION_COEFFICIENT: dict[Position, float] = {
    Position.QB: 4.081432648866086,
    Position.RB: 4.751362988643172,
    Position.WR: 5.255557710367663,
    Position.TE: 4.229937041212303,
}

# Chronologically validated aging-only non-QB continuation cells. Young/prime
# players retain the parent factor; QB retains its parent because its governed
# Y2/Y3 Forecast already consumes the QB career-state model. The selected repair
# improved shared-unit MAE in all nine chronological folds and improved the 30+
# RB/WR/TE diagnostics without introducing a standalone youth bonus.
_AGING_CONTINUATION_COEFFICIENT: dict[tuple[Position, str], float] = {
    (Position.RB, "veteran"): 4.288215381859406,
    (Position.RB, "late"): 2.5207667155683695,
    (Position.WR, "veteran"): 6.266997237225151,
    (Position.WR, "late"): 1.7824123309693336,
    (Position.TE, "veteran"): 3.3838536404247157,
    (Position.TE, "late"): 3.7081860928620243,
}

# Pedigree remains the same validated residual-only signal. The residualizer is
# conditioned on governed Y1/Y2/Y3 Forecast means/uncertainty plus position.
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

# Versioned football-only display anchors. Raw values are now shared discounted
# career fantasy-point magnitude. The reference universe is the historical half
# of repaired PIT predictions at or above the pooled median (107.339), excluding
# the fringe half without position quotas, roster rules, market prices, or named-
# player tuning. Output tiers deliberately reserve 9,000+ for the extreme apex
# tail rather than equating p90 among all NFL players with an apex asset.
_DISPLAY_ANCHORS: tuple[tuple[float, int], ...] = (
    (0.0, 0),
    (10.524529721618592, 1000),
    (46.1764651911168, 2500),
    (107.33902767034948, 4000),
    (148.59960572685094, 5000),
    (200.2200043195422, 6000),
    (276.92014727861124, 7000),
    (404.18990857971215, 8000),
    (529.1259104990676, 8500),
    (640.190364644663, 8800),
    (789.6239953076092, 9000),
)
_DISPLAY_TAIL_SCALE = 700.0

INTRINSIC_VALUE_V2_SCALE = ValueScale(
    scale_id="fsffl_intrinsic_fundamental_career",
    version="5",
    unit_label="shared football-only discounted long-term fundamental dynasty career value",
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
    """Map shared football-only Fundamental Intrinsic magnitude onto 0-10,000."""
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
) -> IntrinsicValueV2Estimate:
    """Estimate team-independent long-term dynasty asset worth from football fundamentals.

    The final raw coordinate is shared discounted football-production magnitude,
    not within-position excellence. Years 1-3 consume governed Forecast once.
    Post-Year-3 continuation preserves the validated parent relationship to Y3 but
    uses chronologically validated aging cells for veteran/late non-QBs. Pedigree
    remains a residual-only signal and is converted back to the same shared football
    units before addition. Market, replacement, Team Utility, owner behavior, and
    transaction outcomes remain absent.
    """
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

    fundamental = max(0.0, raw_career + pedigree_value)
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
        fundamental_value=fundamental,
        fundamental_stddev=raw_stddev,
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