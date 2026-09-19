from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.forecast.career import MultiYearForecastPoint
from fsffl.forecast.models import ForecastDistribution
from fsffl.forecast.qb_career_state import QBCareerStateForecast
from fsffl.state.models import FrozenModel, Position


INTRINSIC_V1_FORECAST_POLICY_VERSION = "intrinsic-v1-forecast-policy-2"


class IntrinsicV1ForecastMethod(StrEnum):
    AUTHORITATIVE_CURRENT = "authoritative_current"
    BOUNDED_CAREER_TRANSITION = "bounded_career_transition"
    CONSERVATIVE_CARRY_FORWARD = "conservative_carry_forward"
    QB_CAREER_STATE = "qb_career_state"


class ForecastEvidenceStrength(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class IntrinsicV1ForecastHorizon(FrozenModel):
    horizon_year: int
    distribution: ForecastDistribution
    method: IntrinsicV1ForecastMethod
    evidence_strength: ForecastEvidenceStrength
    cumulative_survival_probability: float | None = None
    meaningful_starter_probability: float | None = None
    evidence_model_version: str | None = None
    provenance_note: str


class IntrinsicV1PlayerForecastPath(FrozenModel):
    player_id: str
    position: Position
    evaluation_as_of: datetime
    base_forecast_model_version: str
    policy_version: str = INTRINSIC_V1_FORECAST_POLICY_VERSION
    horizons: tuple[IntrinsicV1ForecastHorizon, ...]

    @field_validator("evaluation_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluation_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_three_year_path(self) -> "IntrinsicV1PlayerForecastPath":
        if tuple(point.horizon_year for point in self.horizons) != (1, 2, 3):
            raise ValueError("Intrinsic v1 requires exactly Year 1, Year 2, and Year 3")
        return self


_INTRINSIC_V1_METHOD_POLICY: dict[Position, dict[int, IntrinsicV1ForecastMethod]] = {
    Position.QB: {
        2: IntrinsicV1ForecastMethod.QB_CAREER_STATE,
        3: IntrinsicV1ForecastMethod.QB_CAREER_STATE,
    },
    Position.RB: {
        2: IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
        3: IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
    },
    Position.WR: {
        2: IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD,
        3: IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
    },
    Position.TE: {
        2: IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
        3: IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
    },
}


def intrinsic_v1_method(position: Position, horizon_year: int) -> IntrinsicV1ForecastMethod:
    if horizon_year == 1:
        return IntrinsicV1ForecastMethod.AUTHORITATIVE_CURRENT
    if position not in _INTRINSIC_V1_METHOD_POLICY or horizon_year not in (2, 3):
        raise ValueError("Intrinsic v1 supports QB/RB/WR/TE and horizons 1-3 only")
    return _INTRINSIC_V1_METHOD_POLICY[position][horizon_year]


def _carry_distribution(base: ForecastDistribution, bounded: ForecastDistribution | None) -> ForecastDistribution:
    return ForecastDistribution(
        mean=base.mean,
        stddev=max(base.stddev, bounded.stddev if bounded is not None else base.stddev),
    )


def _qb_state_distribution(base: ForecastDistribution, probability: float) -> ForecastDistribution:
    # Historical validation changed only expected mean. Preserve authoritative Y1
    # uncertainty rather than inventing an unvalidated deep-horizon variance rule.
    return ForecastDistribution(mean=base.mean * probability, stddev=base.stddev)


def materialize_intrinsic_v1_forecast_path(
    *,
    player_id: str,
    position: Position,
    evaluation_as_of: datetime,
    base_distribution: ForecastDistribution,
    base_forecast_model_version: str,
    bounded_path: tuple[MultiYearForecastPoint, ...] | None = None,
    qb_career_state: QBCareerStateForecast | None = None,
) -> IntrinsicV1PlayerForecastPath:
    """Materialize the governed three-year Forecast input used by Intrinsic v1.

    QB deep-horizon means use the Forecast-owned career-state model when valid
    season-scoped PIT evidence is available. The model predicts meaningful-starting-
    role probability only; conditional starter production remains the conservative
    authoritative Year-1 mean. Missing/stale QB evidence fails closed to the prior
    conservative carry-forward treatment. No survival probability is applied again.
    """

    bounded_by_year = {point.season_offset + 1: point for point in (bounded_path or ())}
    horizons: list[IntrinsicV1ForecastHorizon] = [
        IntrinsicV1ForecastHorizon(
            horizon_year=1,
            distribution=base_distribution,
            method=IntrinsicV1ForecastMethod.AUTHORITATIVE_CURRENT,
            evidence_strength=ForecastEvidenceStrength.HIGH,
            cumulative_survival_probability=1.0,
            evidence_model_version=base_forecast_model_version,
            provenance_note="authoritative current-season Forecast",
        )
    ]

    for year in (2, 3):
        configured = intrinsic_v1_method(position, year)
        bounded = bounded_by_year.get(year)
        if configured == IntrinsicV1ForecastMethod.QB_CAREER_STATE and qb_career_state is not None:
            probability = qb_career_state.year2_probability if year == 2 else qb_career_state.year3_probability
            horizons.append(
                IntrinsicV1ForecastHorizon(
                    horizon_year=year,
                    distribution=_qb_state_distribution(base_distribution, probability),
                    method=configured,
                    evidence_strength=ForecastEvidenceStrength.MODERATE,
                    meaningful_starter_probability=probability,
                    evidence_model_version=qb_career_state.model_version,
                    provenance_note=(
                        f"Forecast-owned QB meaningful-starter probability; PIT football features through "
                        f"{qb_career_state.feature_cutoff_season}; conditional production = authoritative Year-1 mean; "
                        f"evidence={qb_career_state.evidence_version}; no second survival adjustment"
                    ),
                )
            )
            continue
        if configured == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION and bounded is not None:
            horizons.append(
                IntrinsicV1ForecastHorizon(
                    horizon_year=year,
                    distribution=bounded.distribution,
                    method=configured,
                    evidence_strength=ForecastEvidenceStrength.MODERATE,
                    cumulative_survival_probability=bounded.cumulative_survival_probability,
                    evidence_model_version=bounded.transition_model_version,
                    provenance_note=(
                        "governed bounded empirical career-transition path; horizon selected independently from authoritative Year 1"
                    ),
                )
            )
            continue

        horizons.append(
            IntrinsicV1ForecastHorizon(
                horizon_year=year,
                distribution=_carry_distribution(base_distribution, bounded.distribution if bounded is not None else None),
                method=IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD,
                evidence_strength=ForecastEvidenceStrength.LOW,
                cumulative_survival_probability=None,
                evidence_model_version=bounded.transition_model_version if bounded is not None else None,
                provenance_note=(
                    "QB career-state evidence unavailable/stale; conservative carry-forward fallback"
                    if configured == IntrinsicV1ForecastMethod.QB_CAREER_STATE
                    else "frozen v1 conservative carry-forward"
                    if configured == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
                    else "bounded transition evidence unavailable; conservative carry-forward fallback"
                ),
            )
        )

    return IntrinsicV1PlayerForecastPath(
        player_id=player_id,
        position=position,
        evaluation_as_of=evaluation_as_of,
        base_forecast_model_version=base_forecast_model_version,
        horizons=tuple(horizons),
    )
