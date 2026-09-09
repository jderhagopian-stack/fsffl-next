from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.position_strength import LeagueRelativePositionStrength
from fsffl.value.models import MarketPriceEstimate, ValueDistribution

from .contextual_value import (
    ContextualValueAdjustment,
    ContextualValueAdjustmentKind,
    ContextualValueEvidenceLevel,
    TeamOwnerAdjustedValueEstimate,
)


class ContextualValueSignal(FrozenModel):
    """Dimensionless contextual evidence before any cardinal-value conversion.

    Signals keep descriptive/derived evidence separate from the provisional policy
    that translates it onto the universal Market Value scale. Positive values mean
    greater contextual willingness to pay; negative values mean lower willingness
    to pay. A signal is not itself Market Value, Decision Utility, or acceptance
    probability.
    """

    kind: ContextualValueAdjustmentKind
    authority_id: str
    overlap_group: str
    signal_center: float
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence_ids: tuple[str, ...]
    source_model_version: str
    residualized_against: tuple[str, ...] = ()
    explanation: str = ""

    @model_validator(mode="after")
    def validate_signal(self) -> "ContextualValueSignal":
        if not isfinite(self.signal_center):
            raise ValueError("contextual value signal must be finite")
        for field_name, value in (
            ("authority_id", self.authority_id),
            ("overlap_group", self.overlap_group),
            ("source_model_version", self.source_model_version),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} cannot be blank")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("contextual value signal requires nonblank evidence_ids")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("contextual value signal evidence_ids must be unique")
        if len(self.residualized_against) != len(set(self.residualized_against)):
            raise ValueError("contextual value signal residualized authorities must be unique")
        if self.authority_id in self.residualized_against:
            raise ValueError("contextual value signal cannot residualize against itself")
        return self


class BoundedContextualValuePrior(FrozenModel):
    """Explicit policy for translating one contextual signal onto a ValueScale.

    The prior contains the cardinal assumptions instead of hiding them in estimator
    code. Callers must supply both the maximum absolute effect and the dimensionless
    signal magnitude at which that effect saturates. The policy is intentionally
    evidence-updating so later empirical calibration can replace these values
    without changing the estimator or the universal Market Value model.
    """

    kind: ContextualValueAdjustmentKind
    parameter_id: str
    max_abs_delta: Annotated[float, Field(ge=0.0)]
    signal_saturation_abs: Annotated[float, Field(gt=0.0)]
    evidence_level: ContextualValueEvidenceLevel = ContextualValueEvidenceLevel.INFERRED
    evidence_through: datetime
    provenance: str
    update_mode: str = "bounded_provisional_prior"
    model_version: str = "contextual-value-prior-v1"

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("contextual value prior evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_prior(self) -> "BoundedContextualValuePrior":
        if any(
            not value.strip()
            for value in (self.parameter_id, self.provenance, self.update_mode, self.model_version)
        ):
            raise ValueError("contextual value prior metadata cannot be blank")
        if self.update_mode == "bounded_provisional_prior" and self.evidence_level != ContextualValueEvidenceLevel.INFERRED:
            raise ValueError("bounded provisional contextual prior must remain inferred")
        return self


def derive_team_need_signal(
    position_strength: LeagueRelativePositionStrength,
) -> ContextualValueSignal | None:
    """Derive a transparent team-need signal from league-relative lineup strength.

    100 is league-average optimized starter production, so `(100 - index) / 100`
    is a dimensionless shortage/surplus coordinate. The function deliberately does
    not choose how many ValueScale units that coordinate is worth. That conversion
    belongs to an explicit governed prior or future calibrated model.
    """

    if position_strength.strength_index is None:
        return None
    signal = (100.0 - position_strength.strength_index) / 100.0
    position = position_strength.position.value
    return ContextualValueSignal(
        kind=ContextualValueAdjustmentKind.TEAM_NEED,
        authority_id="decision:contextual-team-need",
        overlap_group=f"team-need:{position}",
        signal_center=signal,
        confidence=1.0,
        evidence_ids=(
            f"team-utility:position-strength:{position_strength.team_id}:{position}:{position_strength.model_version}",
        ),
        source_model_version=position_strength.model_version,
        residualized_against=(),
        explanation=(
            f"{position} optimized starter production is "
            f"{position_strength.strength_index:.1f} versus league average 100; "
            "positive signal indicates relative need and negative signal relative surplus."
        ),
    )


def estimate_contextual_adjustment(
    signal: ContextualValueSignal,
    prior: BoundedContextualValuePrior,
    *,
    as_of: datetime,
) -> ContextualValueAdjustment:
    """Translate one governed signal into one bounded additive value adjustment."""

    if as_of.tzinfo is None:
        raise ValueError("contextual value estimation timestamp must be timezone-aware")
    if prior.evidence_through > as_of:
        raise ValueError("contextual value prior cannot use future evidence")
    if signal.kind != prior.kind:
        raise ValueError("contextual value signal and prior kinds must match")

    normalized = signal.signal_center / prior.signal_saturation_abs
    bounded = max(-1.0, min(1.0, normalized))
    delta = bounded * prior.max_abs_delta
    evidence_ids = signal.evidence_ids + (f"parameter:{prior.parameter_id}",)
    return ContextualValueAdjustment(
        kind=signal.kind,
        authority_id=signal.authority_id,
        overlap_group=signal.overlap_group,
        delta_mean=delta,
        confidence=signal.confidence,
        evidence_level=prior.evidence_level,
        evidence_ids=evidence_ids,
        source_model_version=f"{signal.source_model_version}+{prior.model_version}",
        residualized_against=signal.residualized_against,
        explanation=(
            f"{signal.explanation} Cardinal effect is bounded by governed parameter "
            f"{prior.parameter_id}; no multiplier is applied to universal Market Value."
        ).strip(),
    )


def build_team_owner_adjusted_value(
    *,
    team_id: str,
    market_baseline: MarketPriceEstimate,
    signals: tuple[ContextualValueSignal, ...],
    priors: tuple[BoundedContextualValuePrior, ...],
    as_of: datetime,
    owner_id: str | None = None,
    model_version: str = "team-owner-adjusted-value-estimator-v1",
) -> TeamOwnerAdjustedValueEstimate:
    """Build a contextual clearing-value estimate from explicitly governed signals.

    Each signal kind must have exactly one supplied prior. The aggregate contract
    still owns anti-double-counting validation across authority IDs, overlap groups,
    and evidence IDs. Baseline dispersion is preserved and shifted rather than
    re-estimated here because this v1 has no calibrated contextual error model.
    """

    if as_of.tzinfo is None:
        raise ValueError("team/owner-adjusted value timestamp must be timezone-aware")
    if market_baseline.as_of > as_of:
        raise ValueError("contextual value cannot use a future market baseline")
    if not model_version.strip():
        raise ValueError("contextual value estimator model_version cannot be blank")

    prior_by_kind: dict[ContextualValueAdjustmentKind, BoundedContextualValuePrior] = {}
    for prior in priors:
        if prior.kind in prior_by_kind:
            raise ValueError("contextual value estimator requires one prior per adjustment kind")
        prior_by_kind[prior.kind] = prior

    adjustments: list[ContextualValueAdjustment] = []
    used_priors: list[BoundedContextualValuePrior] = []
    for signal in signals:
        prior = prior_by_kind.get(signal.kind)
        if prior is None:
            raise ValueError(f"missing contextual value prior for {signal.kind.value}")
        adjustments.append(estimate_contextual_adjustment(signal, prior, as_of=as_of))
        used_priors.append(prior)

    total_delta = sum(item.delta_mean for item in adjustments)
    baseline = market_baseline.distribution

    def shifted(value: float | None) -> float | None:
        return None if value is None else value + total_delta

    adjusted_distribution = ValueDistribution(
        mean=baseline.mean + total_delta,
        stddev=baseline.stddev,
        p10=shifted(baseline.p10),
        p50=shifted(baseline.p50),
        p90=shifted(baseline.p90),
    )
    # The sum of per-channel absolute bounds is the widest permitted aggregate
    # movement. The TeamOwnerAdjustedValueEstimate contract separately verifies
    # the realized total and all anti-double-counting constraints.
    aggregate_bound = sum(prior.max_abs_delta for prior in used_priors)
    return TeamOwnerAdjustedValueEstimate(
        team_id=team_id,
        owner_id=owner_id,
        market_baseline=market_baseline,
        adjusted_distribution=adjusted_distribution,
        scale=market_baseline.scale,
        as_of=as_of,
        adjustments=tuple(adjustments),
        adjustment_bound_abs=aggregate_bound,
        model_version=model_version,
    )
