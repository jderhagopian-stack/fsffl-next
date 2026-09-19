from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .context_expectation import BehavioralContextExpectationResult
from .models import OwnerBehaviorProfile


class BehavioralResidualPolicy(FrozenModel):
    """Explicit shrinkage policy for residual owner-preference inference."""

    parameter_id: str
    prior_strength: Annotated[float, Field(gt=0.0)]
    evidence_through: datetime
    provenance: str
    update_mode: str = "bounded_provisional_prior"
    model_version: str = "behavioral-residual-policy-v1"

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral residual policy evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "BehavioralResidualPolicy":
        if any(
            not value.strip()
            for value in (self.parameter_id, self.provenance, self.update_mode, self.model_version)
        ):
            raise ValueError("behavioral residual policy metadata cannot be blank")
        return self


class OwnerPositionPreferenceResidual(FrozenModel):
    """Owner position tendency remaining after an explicit context expectation."""

    owner_id: str
    position: str
    as_of: datetime
    observed_positioned_acquisitions: Annotated[int, Field(ge=0)]
    observed_position_acquisitions: Annotated[int, Field(ge=0)]
    observed_acquisition_share: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    context_expected_acquisition_share: Annotated[float, Field(ge=0.0, le=1.0)]
    raw_residual_share: float | None = None
    shrunk_residual_share: float | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    context_authority_ids: tuple[str, ...]
    context_model_version: str
    profile_model_version: str
    policy_parameter_id: str
    evidence_ids: tuple[str, ...]
    model_version: str = "owner-position-preference-residual-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("owner preference residual timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_residual(self) -> "OwnerPositionPreferenceResidual":
        if any(
            not value.strip()
            for value in (
                self.owner_id,
                self.position,
                self.context_model_version,
                self.profile_model_version,
                self.policy_parameter_id,
                self.model_version,
            )
        ):
            raise ValueError("owner preference residual metadata cannot be blank")
        if not self.context_authority_ids or any(not item.strip() for item in self.context_authority_ids):
            raise ValueError("owner preference residual requires context authorities")
        if len(self.context_authority_ids) != len(set(self.context_authority_ids)):
            raise ValueError("owner preference residual context authorities must be unique")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("owner preference residual requires evidence_ids")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("owner preference residual evidence_ids must be unique")
        if self.observed_position_acquisitions > self.observed_positioned_acquisitions:
            raise ValueError("position acquisitions cannot exceed positioned acquisitions")

        has_observation = self.observed_positioned_acquisitions > 0
        residual_fields = (
            self.observed_acquisition_share,
            self.raw_residual_share,
            self.shrunk_residual_share,
        )
        if has_observation and any(value is None for value in residual_fields):
            raise ValueError("observed owner preference residual requires complete estimates")
        if not has_observation and any(value is not None for value in residual_fields):
            raise ValueError("no-history owner preference residual cannot claim numeric tendency")
        if not has_observation and self.confidence != 0.0:
            raise ValueError("no-history owner preference residual must have zero confidence")
        return self


class OwnerPositionPreferenceResidualResult(FrozenModel):
    """Governed bridge result from empirical context expectation to owner residual."""

    residual: OwnerPositionPreferenceResidual | None = None
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def exactly_one_result(self) -> "OwnerPositionPreferenceResidualResult":
        if (self.residual is None) == (self.unavailable_reason is None):
            raise ValueError("owner residual result requires residual or unavailable_reason")
        if self.unavailable_reason is not None and not self.unavailable_reason.strip():
            raise ValueError("owner residual unavailable_reason cannot be blank")
        return self


def estimate_owner_position_preference_residual(
    profile: OwnerBehaviorProfile,
    *,
    position: str,
    context_expected_acquisition_share: float,
    context_authority_ids: tuple[str, ...],
    context_model_version: str,
    policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerPositionPreferenceResidual:
    """Estimate a context-controlled, shrinkage-adjusted owner position tendency."""

    if as_of.tzinfo is None:
        raise ValueError("owner preference residual timestamp must be timezone-aware")
    if profile.as_of > as_of:
        raise ValueError("owner preference residual cannot use a future profile")
    if policy.evidence_through > as_of:
        raise ValueError("owner preference residual policy cannot use future evidence")
    if not position.strip() or not context_model_version.strip():
        raise ValueError("owner preference residual position/context model cannot be blank")
    if not 0.0 <= context_expected_acquisition_share <= 1.0:
        raise ValueError("context expected acquisition share must be between zero and one")
    if not context_authority_ids:
        raise ValueError("owner preference residual requires context authorities")

    positioned_count = sum(profile.acquired_positions.values())
    position_count = profile.acquired_positions.get(position, 0)
    evidence_ids = (
        f"behavioral-profile:{profile.league_family_id}:{profile.owner_id}:{profile.model_version}",
        f"context-model:{context_model_version}",
        f"parameter:{policy.parameter_id}",
    )

    if positioned_count == 0:
        return OwnerPositionPreferenceResidual(
            owner_id=profile.owner_id,
            position=position,
            as_of=as_of,
            observed_positioned_acquisitions=0,
            observed_position_acquisitions=0,
            observed_acquisition_share=None,
            context_expected_acquisition_share=context_expected_acquisition_share,
            raw_residual_share=None,
            shrunk_residual_share=None,
            confidence=0.0,
            context_authority_ids=context_authority_ids,
            context_model_version=context_model_version,
            profile_model_version=profile.model_version,
            policy_parameter_id=policy.parameter_id,
            evidence_ids=evidence_ids,
        )

    observed_share = position_count / positioned_count
    raw_residual = observed_share - context_expected_acquisition_share
    shrinkage = positioned_count / (positioned_count + policy.prior_strength)
    shrunk_residual = raw_residual * shrinkage
    return OwnerPositionPreferenceResidual(
        owner_id=profile.owner_id,
        position=position,
        as_of=as_of,
        observed_positioned_acquisitions=positioned_count,
        observed_position_acquisitions=position_count,
        observed_acquisition_share=observed_share,
        context_expected_acquisition_share=context_expected_acquisition_share,
        raw_residual_share=raw_residual,
        shrunk_residual_share=shrunk_residual,
        confidence=shrinkage,
        context_authority_ids=context_authority_ids,
        context_model_version=context_model_version,
        profile_model_version=profile.model_version,
        policy_parameter_id=policy.parameter_id,
        evidence_ids=evidence_ids,
    )


def estimate_owner_position_preference_from_context_expectation(
    profile: OwnerBehaviorProfile,
    *,
    position: str,
    context_expectation: BehavioralContextExpectationResult,
    policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerPositionPreferenceResidualResult:
    """Bridge the empirical context-only baseline into residual owner inference.

    This function removes the manual middle-number seam. It accepts only a governed
    context expectation result, propagates its model/policy provenance as the
    context authority, and then delegates the owner-specific residual calculation
    to the existing shrinkage-governed estimator.
    """

    if context_expectation.owner_id != profile.owner_id:
        raise ValueError("context expectation owner must match behavioral profile owner")
    if context_expectation.as_of > as_of:
        raise ValueError("owner residual cannot use a future context expectation")
    if context_expectation.unavailable_reason is not None:
        return OwnerPositionPreferenceResidualResult(
            unavailable_reason=f"context expectation unavailable: {context_expectation.unavailable_reason}"
        )

    expected_share = context_expectation.share_for(position)
    if expected_share is None:
        return OwnerPositionPreferenceResidualResult(
            unavailable_reason=f"context expectation has no estimate for {position}"
        )

    context_model_version = (
        f"{context_expectation.source_model_version}+"
        f"{context_expectation.model_version}+"
        f"{context_expectation.policy_parameter_id}"
    )
    residual = estimate_owner_position_preference_residual(
        profile,
        position=position,
        context_expected_acquisition_share=expected_share,
        context_authority_ids=(
            f"behavioral:context-expectation:{context_expectation.source_model_version}",
            f"behavioral:context-policy:{context_expectation.policy_parameter_id}",
        ),
        context_model_version=context_model_version,
        policy=policy,
        as_of=as_of,
    )
    return OwnerPositionPreferenceResidualResult(residual=residual)
