from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .models import OwnerBehaviorProfile


class BehavioralResidualPolicy(FrozenModel):
    """Explicit shrinkage policy for residual owner-preference inference.

    The policy controls how strongly sparse accepted-action history is shrunk
    toward the context-explained expectation. It is separate from both the raw
    descriptive profile and any downstream ValueScale conversion.
    """

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
    """Owner position tendency remaining after an explicit context expectation.

    This is inferred from completed/observed acquisition history only. It is not an
    acceptance probability and does not pretend that rejected offers were observed.
    `context_expected_acquisition_share` must come from a separately identified
    context model so team need or league environment can be removed before a true
    owner-specific residual is claimed.
    """

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
    """Estimate a context-controlled, shrinkage-adjusted owner position tendency.

    Sparse history is shrunk toward zero residual using `n / (n + prior_strength)`.
    The shrinkage parameter is explicit policy rather than a hidden coefficient.
    Missing positioned acquisition history remains unestimated (`None`) rather than
    being silently interpreted as neutral owner preference.
    """

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
