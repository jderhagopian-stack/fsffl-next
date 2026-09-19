from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .context_controlled_profile import OwnerContextControlledPositionPreference, OwnerContextControlledPreferenceProfile
from .context_dataset import BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow
from .context_expectation import BehavioralContextExpectationPolicy
from .context_expectation_v2 import (
    BehavioralMulticlassContextExpectationModel,
    estimate_multiclass_context_acquisition_distribution,
)
from .residual_preference import BehavioralResidualPolicy

_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class OwnerHistoricalContextCoverageIssue(FrozenModel):
    event_id: str
    occurred_at: datetime
    reason: str

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical context coverage issue timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_issue(self) -> "OwnerHistoricalContextCoverageIssue":
        if not self.event_id.strip() or not self.reason.strip():
            raise ValueError("historical context coverage issue metadata cannot be blank")
        return self


class OwnerHistoricalContextCoverage(FrozenModel):
    owner_id: str
    as_of: datetime
    eligible_event_count: Annotated[int, Field(ge=0)]
    estimated_event_count: Annotated[int, Field(ge=0)]
    eligible_positioned_acquisitions: Annotated[int, Field(ge=0)]
    estimated_positioned_acquisitions: Annotated[int, Field(ge=0)]
    event_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    acquisition_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    unavailable: tuple[OwnerHistoricalContextCoverageIssue, ...] = ()
    model_version: str = "owner-historical-context-coverage-v2"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical context coverage as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_coverage(self) -> "OwnerHistoricalContextCoverage":
        if not self.owner_id.strip() or not self.model_version.strip():
            raise ValueError("historical context coverage metadata cannot be blank")
        if self.estimated_event_count > self.eligible_event_count:
            raise ValueError("estimated historical events cannot exceed eligible events")
        if self.estimated_positioned_acquisitions > self.eligible_positioned_acquisitions:
            raise ValueError("estimated acquisitions cannot exceed eligible acquisitions")
        if len(self.unavailable) != self.eligible_event_count - self.estimated_event_count:
            raise ValueError("historical context event coverage issues must reconcile")
        event_rate = self.estimated_event_count / self.eligible_event_count if self.eligible_event_count else 0.0
        asset_rate = self.estimated_positioned_acquisitions / self.eligible_positioned_acquisitions if self.eligible_positioned_acquisitions else 0.0
        if abs(self.event_coverage_rate - event_rate) > 1e-12 or abs(self.acquisition_coverage_rate - asset_rate) > 1e-12:
            raise ValueError("historical context coverage rates must reconcile")
        return self


class OwnerHistoricalContextControlledPreferenceResult(FrozenModel):
    profile: OwnerContextControlledPreferenceProfile
    coverage: OwnerHistoricalContextCoverage
    model_version: str = "owner-historical-context-controlled-preference-v2"

    @model_validator(mode="after")
    def validate_result(self) -> "OwnerHistoricalContextControlledPreferenceResult":
        if self.profile.owner_id != self.coverage.owner_id or self.profile.as_of != self.coverage.as_of:
            raise ValueError("historical context profile and coverage identity must match")
        return self


def _positioned_count(row: BehavioralContextCalibrationRow) -> int:
    return sum(row.acquired_position_counts.get(position.value, 0) for position in _POSITIONS)


def build_owner_historical_context_controlled_preference_profile(
    dataset: BehavioralContextCalibrationDataset,
    model: BehavioralMulticlassContextExpectationModel,
    *,
    owner_id: str,
    league_family_id: str,
    context_policy: BehavioralContextExpectationPolicy,
    residual_policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerHistoricalContextControlledPreferenceResult:
    """Compare observed owner history with event-matched PIT context expectations.

    Each focal-owner historical action is evaluated using only other-owner actions
    that preceded it. Observed and expected position counts are aggregated over the
    exact same covered events; unavailable early events are excluded from both sides
    and reported explicitly instead of biasing the residual toward zero or away from it.
    """
    if as_of.tzinfo is None:
        raise ValueError("historical owner preference as_of must be timezone-aware")
    if not owner_id.strip() or not league_family_id.strip():
        raise ValueError("historical owner preference identifiers cannot be blank")
    if residual_policy.evidence_through > as_of:
        raise ValueError("historical owner preference residual policy cannot use future evidence")

    focal = sorted(
        (row for row in dataset.rows if row.owner_id == owner_id and row.occurred_at <= as_of and _positioned_count(row) > 0),
        key=lambda row: (row.occurred_at, row.event_id),
    )
    observed = {position: 0 for position in _POSITIONS}
    expected = {position: 0.0 for position in _POSITIONS}
    unavailable: list[OwnerHistoricalContextCoverageIssue] = []
    covered_ids: list[str] = []
    estimated_assets = 0
    max_training_observations = 0
    max_training_owners = 0
    training_through: datetime | None = None

    for row in focal:
        count = _positioned_count(row)
        estimate = estimate_multiclass_context_acquisition_distribution(
            model, row.context, owner_id=owner_id, policy=context_policy
        )
        if estimate.unavailable_reason is not None:
            unavailable.append(OwnerHistoricalContextCoverageIssue(event_id=row.event_id, occurred_at=row.occurred_at, reason=estimate.unavailable_reason))
            continue
        covered_ids.append(row.event_id)
        estimated_assets += count
        max_training_observations = max(max_training_observations, estimate.training_observation_count)
        max_training_owners = max(max_training_owners, estimate.training_owner_count)
        if estimate.training_through is not None and (training_through is None or estimate.training_through > training_through):
            training_through = estimate.training_through
        for position in _POSITIONS:
            observed[position] += row.acquired_position_counts.get(position.value, 0)
            share = estimate.share_for(position)
            if share is None:
                raise ValueError("available multiclass context expectation must contain every core position")
            expected[position] += share * count

    eligible_assets = sum(_positioned_count(row) for row in focal)
    coverage = OwnerHistoricalContextCoverage(
        owner_id=owner_id,
        as_of=as_of,
        eligible_event_count=len(focal),
        estimated_event_count=len(covered_ids),
        eligible_positioned_acquisitions=eligible_assets,
        estimated_positioned_acquisitions=estimated_assets,
        event_coverage_rate=len(covered_ids) / len(focal) if focal else 0.0,
        acquisition_coverage_rate=estimated_assets / eligible_assets if eligible_assets else 0.0,
        unavailable=tuple(unavailable),
    )

    common = dict(
        owner_id=owner_id,
        league_family_id=league_family_id,
        as_of=as_of,
        context_training_observation_count=max_training_observations,
        context_training_owner_count=max_training_owners,
        context_training_through=training_through,
        context_policy_parameter_id=context_policy.parameter_id,
        residual_policy_parameter_id=residual_policy.parameter_id,
        context_model_version=f"{model.model_version}+eventwise-history-v2",
        profile_model_version="owner-historical-covered-events-v2",
    )
    if estimated_assets == 0:
        profile = OwnerContextControlledPreferenceProfile(
            positions=tuple(OwnerContextControlledPositionPreference(position=position, status="unavailable", unavailable_reason="no historical owner actions have estimable eventwise context") for position in _POSITIONS),
            observed_positioned_acquisitions=0,
            estimated_position_count=0,
            mean_confidence=0.0,
            **common,
        )
        return OwnerHistoricalContextControlledPreferenceResult(profile=profile, coverage=coverage)

    shrinkage = estimated_assets / (estimated_assets + residual_policy.prior_strength)
    authorities = (
        f"behavioral:eventwise-context-expectation:{model.model_version}",
        f"behavioral:context-policy:{context_policy.parameter_id}",
    )
    evidence_ids = tuple(
        [f"behavioral-covered-event:{event_id}" for event_id in covered_ids]
        + [f"context-model:{model.model_version}", f"context-policy:{context_policy.parameter_id}", f"residual-policy:{residual_policy.parameter_id}"]
    )
    rows = []
    for position in _POSITIONS:
        observed_share = observed[position] / estimated_assets
        expected_share = expected[position] / estimated_assets
        raw = observed_share - expected_share
        rows.append(OwnerContextControlledPositionPreference(
            position=position,
            observed_acquisition_share=observed_share,
            context_expected_acquisition_share=expected_share,
            raw_residual_share=raw,
            shrunk_residual_share=raw * shrinkage,
            confidence=shrinkage,
            observed_position_acquisitions=observed[position],
            observed_positioned_acquisitions=estimated_assets,
            status="estimated",
            context_authority_ids=authorities,
            evidence_ids=evidence_ids,
        ))

    profile = OwnerContextControlledPreferenceProfile(
        positions=tuple(rows),
        observed_positioned_acquisitions=estimated_assets,
        estimated_position_count=4,
        mean_confidence=shrinkage,
        **common,
    )
    return OwnerHistoricalContextControlledPreferenceResult(profile=profile, coverage=coverage)
