from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .context_expectation import BehavioralContextExpectationResult
from .models import OwnerBehaviorProfile
from .residual_preference import (
    BehavioralResidualPolicy,
    OwnerPositionPreferenceResidual,
    estimate_owner_position_preference_from_context_expectation,
)


_PROFILE_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class OwnerContextControlledPositionPreference(FrozenModel):
    """One position's observed, context-expected, and residual owner behavior."""

    position: Position
    observed_acquisition_share: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    context_expected_acquisition_share: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    raw_residual_share: float | None = None
    shrunk_residual_share: float | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    observed_position_acquisitions: Annotated[int, Field(ge=0)] = 0
    observed_positioned_acquisitions: Annotated[int, Field(ge=0)] = 0
    status: str
    unavailable_reason: str | None = None
    context_authority_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_position(self) -> "OwnerContextControlledPositionPreference":
        if self.status not in {"estimated", "unavailable"}:
            raise ValueError("context-controlled position preference status is invalid")
        numeric = (
            self.observed_acquisition_share,
            self.context_expected_acquisition_share,
            self.raw_residual_share,
            self.shrunk_residual_share,
        )
        if self.status == "estimated":
            if any(value is None for value in numeric):
                raise ValueError("estimated context-controlled preference requires complete numeric evidence")
            if self.unavailable_reason is not None:
                raise ValueError("estimated context-controlled preference cannot be unavailable")
        else:
            if self.unavailable_reason is None or not self.unavailable_reason.strip():
                raise ValueError("unavailable context-controlled preference requires reason")
            if any(value is not None for value in numeric):
                raise ValueError("unavailable context-controlled preference cannot claim numeric inference")
            if self.confidence != 0.0:
                raise ValueError("unavailable context-controlled preference must have zero confidence")
        return self


class OwnerContextControlledPreferenceProfile(FrozenModel):
    """Multi-position owner tendency after removing the empirical context baseline.

    The profile is Behavioral evidence, not Market Value or Decision authority. It
    makes the residual decomposition inspectable across all core positions and
    keeps unavailable positions explicit instead of silently filling them with zero.
    """

    owner_id: str
    league_family_id: str
    as_of: datetime
    positions: tuple[OwnerContextControlledPositionPreference, ...]
    observed_positioned_acquisitions: Annotated[int, Field(ge=0)]
    estimated_position_count: Annotated[int, Field(ge=0, le=4)]
    mean_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    context_training_observation_count: Annotated[int, Field(ge=0)]
    context_training_owner_count: Annotated[int, Field(ge=0)]
    context_training_through: datetime | None = None
    context_policy_parameter_id: str
    residual_policy_parameter_id: str
    context_model_version: str
    profile_model_version: str
    model_version: str = "owner-context-controlled-preference-profile-v1"

    @field_validator("as_of", "context_training_through")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("context-controlled profile timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> "OwnerContextControlledPreferenceProfile":
        if any(
            not value.strip()
            for value in (
                self.owner_id,
                self.league_family_id,
                self.context_policy_parameter_id,
                self.residual_policy_parameter_id,
                self.context_model_version,
                self.profile_model_version,
                self.model_version,
            )
        ):
            raise ValueError("context-controlled profile metadata cannot be blank")
        positions = [item.position for item in self.positions]
        if tuple(positions) != _PROFILE_POSITIONS:
            raise ValueError("context-controlled profile requires ordered QB/RB/WR/TE rows")
        estimated = [item for item in self.positions if item.status == "estimated"]
        if self.estimated_position_count != len(estimated):
            raise ValueError("context-controlled profile estimated position count must reconcile")
        expected_confidence = sum(item.confidence for item in estimated) / len(estimated) if estimated else 0.0
        if abs(self.mean_confidence - expected_confidence) > 1e-12:
            raise ValueError("context-controlled profile mean confidence must reconcile")
        if len(estimated) == len(_PROFILE_POSITIONS):
            raw_total = sum(item.raw_residual_share or 0.0 for item in estimated)
            shrunk_total = sum(item.shrunk_residual_share or 0.0 for item in estimated)
            if abs(raw_total) > 1e-9 or abs(shrunk_total) > 1e-9:
                raise ValueError("complete context-controlled residual shares must net to zero")
        return self

    def position(self, position: str | Position) -> OwnerContextControlledPositionPreference:
        target = Position(position)
        return next(item for item in self.positions if item.position == target)


def _estimated_row(position: Position, residual: OwnerPositionPreferenceResidual) -> OwnerContextControlledPositionPreference:
    return OwnerContextControlledPositionPreference(
        position=position,
        observed_acquisition_share=residual.observed_acquisition_share,
        context_expected_acquisition_share=residual.context_expected_acquisition_share,
        raw_residual_share=residual.raw_residual_share,
        shrunk_residual_share=residual.shrunk_residual_share,
        confidence=residual.confidence,
        observed_position_acquisitions=residual.observed_position_acquisitions,
        observed_positioned_acquisitions=residual.observed_positioned_acquisitions,
        status="estimated",
        context_authority_ids=residual.context_authority_ids,
        evidence_ids=residual.evidence_ids,
    )


def build_owner_context_controlled_preference_profile(
    profile: OwnerBehaviorProfile,
    *,
    context_expectation: BehavioralContextExpectationResult,
    residual_policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerContextControlledPreferenceProfile:
    """Build an inspectable QB/RB/WR/TE residual preference profile."""

    if context_expectation.owner_id != profile.owner_id:
        raise ValueError("context expectation owner must match behavioral profile owner")
    if profile.as_of > as_of or context_expectation.as_of > as_of:
        raise ValueError("context-controlled owner profile cannot use future evidence")

    rows: list[OwnerContextControlledPositionPreference] = []
    for position in _PROFILE_POSITIONS:
        result = estimate_owner_position_preference_from_context_expectation(
            profile,
            position=position.value,
            context_expectation=context_expectation,
            policy=residual_policy,
            as_of=as_of,
        )
        if result.residual is None:
            rows.append(
                OwnerContextControlledPositionPreference(
                    position=position,
                    status="unavailable",
                    unavailable_reason=result.unavailable_reason or "residual owner preference unavailable",
                )
            )
            continue
        # No positioned owner history is not a numeric residual estimate even though
        # the lower-level residual contract can carry the context expectation.
        if result.residual.observed_acquisition_share is None:
            rows.append(
                OwnerContextControlledPositionPreference(
                    position=position,
                    status="unavailable",
                    unavailable_reason="owner has no positioned acquisition history",
                )
            )
            continue
        rows.append(_estimated_row(position, result.residual))

    estimated = [row for row in rows if row.status == "estimated"]
    mean_confidence = sum(row.confidence for row in estimated) / len(estimated) if estimated else 0.0
    return OwnerContextControlledPreferenceProfile(
        owner_id=profile.owner_id,
        league_family_id=profile.league_family_id,
        as_of=as_of,
        positions=tuple(rows),
        observed_positioned_acquisitions=sum(profile.acquired_positions.values()),
        estimated_position_count=len(estimated),
        mean_confidence=mean_confidence,
        context_training_observation_count=context_expectation.training_observation_count,
        context_training_owner_count=context_expectation.training_owner_count,
        context_training_through=context_expectation.training_through,
        context_policy_parameter_id=context_expectation.policy_parameter_id,
        residual_policy_parameter_id=residual_policy.parameter_id,
        context_model_version=context_expectation.source_model_version,
        profile_model_version=profile.model_version,
    )
