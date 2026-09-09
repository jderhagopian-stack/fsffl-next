from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .context_controlled_profile import (
    OwnerContextControlledPositionPreference,
    OwnerContextControlledPreferenceProfile,
)
from .context_dataset import BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow
from .context_expectation import (
    BehavioralContextExpectationModel,
    BehavioralContextExpectationPolicy,
    estimate_context_acquisition_distribution,
)
from .residual_preference import BehavioralResidualPolicy


_HISTORICAL_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


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
    """Evidence-completeness accounting for eventwise owner context control."""

    owner_id: str
    as_of: datetime
    eligible_event_count: Annotated[int, Field(ge=0)]
    estimated_event_count: Annotated[int, Field(ge=0)]
    eligible_positioned_acquisitions: Annotated[int, Field(ge=0)]
    estimated_positioned_acquisitions: Annotated[int, Field(ge=0)]
    event_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    acquisition_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    unavailable: tuple[OwnerHistoricalContextCoverageIssue, ...] = ()
    model_version: str = "owner-historical-context-coverage-v1"

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
            raise ValueError("estimated positioned acquisitions cannot exceed eligible acquisitions")
        if len(self.unavailable) != self.eligible_event_count - self.estimated_event_count:
            raise ValueError("historical context event coverage issues must reconcile")
        expected_events = self.estimated_event_count / self.eligible_event_count if self.eligible_event_count else 0.0
        expected_assets = (
            self.estimated_positioned_acquisitions / self.eligible_positioned_acquisitions
            if self.eligible_positioned_acquisitions
            else 0.0
        )
        if abs(self.event_coverage_rate - expected_events) > 1e-12:
            raise ValueError("historical context event coverage rate must reconcile")
        if abs(self.acquisition_coverage_rate - expected_assets) > 1e-12:
            raise ValueError("historical context acquisition coverage rate must reconcile")
        return self


class OwnerHistoricalContextControlledPreferenceResult(FrozenModel):
    """Preferred eventwise historical owner preference evidence plus coverage."""

    profile: OwnerContextControlledPreferenceProfile
    coverage: OwnerHistoricalContextCoverage
    model_version: str = "owner-historical-context-controlled-preference-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "OwnerHistoricalContextControlledPreferenceResult":
        if self.profile.owner_id != self.coverage.owner_id:
            raise ValueError("historical context profile and coverage owner must match")
        if self.profile.as_of != self.coverage.as_of:
            raise ValueError("historical context profile and coverage as_of must match")
        if not self.model_version.strip():
            raise ValueError("historical context result model_version cannot be blank")
        return self


def _positioned_acquisition_count(row: BehavioralContextCalibrationRow) -> int:
    return sum(row.acquired_position_counts.get(position.value, 0) for position in _HISTORICAL_POSITIONS)


def build_owner_historical_context_controlled_preference_profile(
    dataset: BehavioralContextCalibrationDataset,
    model: BehavioralContextExpectationModel,
    *,
    owner_id: str,
    league_family_id: str,
    context_policy: BehavioralContextExpectationPolicy,
    residual_policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerHistoricalContextControlledPreferenceResult:
    """Residualize owner acquisition history against context at each historical action.

    For every eligible focal-owner action, the pooled context model estimates what
    comparable *other* owners had acquired in similar strictly pre-action contexts,
    using only observations that occurred before that action. Expected position
    counts are then aggregated across the same covered events as observed counts.
    This is the preferred statistical interpretation of residual owner preference:
    observed historical behavior minus event-matched historical context, rather
    than cumulative history minus one current-context expectation.
    """

    if as_of.tzinfo is None:
        raise ValueError("historical owner preference as_of must be timezone-aware")
    if not owner_id.strip() or not league_family_id.strip():
        raise ValueError("historical owner preference owner/league identifiers cannot be blank")
    if residual_policy.evidence_through > as_of:
        raise ValueError("historical owner preference residual policy cannot use future evidence")

    focal_rows = [
        row
        for row in dataset.rows
        if row.owner_id == owner_id and row.occurred_at <= as_of and _positioned_acquisition_count(row) > 0
    ]
    focal_rows.sort(key=lambda row: (row.occurred_at, row.event_id))

    observed = {position: 0 for position in _HISTORICAL_POSITIONS}
    expected = {position: 0.0 for position in _HISTORICAL_POSITIONS}
    unavailable: list[OwnerHistoricalContextCoverageIssue] = []
    estimated_events = 0
    eligible_acquisitions = sum(_positioned_acquisition_count(row) for row in focal_rows)
    estimated_acquisitions = 0
    training_observation_count = 0
    training_owner_count = 0
    training_through: datetime | None = None
    covered_event_ids: list[str] = []

    for row in focal_rows:
        positioned_count = _positioned_acquisition_count(row)
        result = estimate_context_acquisition_distribution(
            model,
            row.context,
            owner_id=owner_id,
            policy=context_policy,
        )
        if result.unavailable_reason is not None:
            unavailable.append(
                OwnerHistoricalContextCoverageIssue(
                    event_id=row.event_id,
                    occurred_at=row.occurred_at,
                    reason=result.unavailable_reason,
                )
            )
            continue

        estimated_events += 1
        estimated_acquisitions += positioned_count
        covered_event_ids.append(row.event_id)
        training_observation_count = max(training_observation_count, result.training_observation_count)
        training_owner_count = max(training_owner_count, result.training_owner_count)
        if result.training_through is not None and (
            training_through is None or result.training_through > training_through
        ):
            training_through = result.training_through

        for position in _HISTORICAL_POSITIONS:
            observed[position] += row.acquired_position_counts.get(position.value, 0)
            share = result.share_for(position)
            if share is None:
                raise ValueError("available historical context expectation must contain every core position")
            expected[position] += share * positioned_count

    coverage = OwnerHistoricalContextCoverage(
        owner_id=owner_id,
        as_of=as_of,
        eligible_event_count=len(focal_rows),
        estimated_event_count=estimated_events,
        eligible_positioned_acquisitions=eligible_acquisitions,
        estimated_positioned_acquisitions=estimated_acquisitions,
        event_coverage_rate=estimated_events / len(focal_rows) if focal_rows else 0.0,
        acquisition_coverage_rate=estimated_acquisitions / eligible_acquisitions if eligible_acquisitions else 0.0,
        unavailable=tuple(unavailable),
    )

    rows: list[OwnerContextControlledPositionPreference] = []
    if estimated_acquisitions <= 0:
        rows = [
            OwnerContextControlledPositionPreference(
                position=position,
                status="unavailable",
                unavailable_reason="no focal-owner historical actions have estimable eventwise context",
            )
            for position in _HISTORICAL_POSITIONS
        ]
        profile = OwnerContextControlledPreferenceProfile(
            owner_id=owner_id,
            league_family_id=league_family_id,
            as_of=as_of,
            positions=tuple(rows),
            observed_positioned_acquisitions=0,
            estimated_position_count=0,
            mean_confidence=0.0,
            context_training_observation_count=training_observation_count,
            context_training_owner_count=training_owner_count,
            context_training_through=training_through,
            context_policy_parameter_id=context_policy.parameter_id,
            residual_policy_parameter_id=residual_policy.parameter_id,
            context_model_version=f"{model.model_version}+eventwise-history-v1",
            profile_model_version="owner-historical-covered-events-v1",
        )
        return OwnerHistoricalContextControlledPreferenceResult(profile=profile, coverage=coverage)

    shrinkage = estimated_acquisitions / (estimated_acquisitions + residual_policy.prior_strength)
    context_authorities = (
        f"behavioral:eventwise-context-expectation:{model.model_version}",
        f"behavioral:context-policy:{context_policy.parameter_id}",
    )
    evidence_ids = tuple(
        [f"behavioral-covered-event:{event_id}" for event_id in covered_event_ids]
        + [
            f"context-model:{model.model_version}",
            f"context-policy:{context_policy.parameter_id}",
            f"residual-policy:{residual_policy.parameter_id}",
        ]
    )

    for position in _HISTORICAL_POSITIONS:
        observed_share = observed[position] / estimated_acquisitions
        expected_share = expected[position] / estimated_acquisitions
        raw_residual = observed_share - expected_share
        rows.append(
            OwnerContextControlledPositionPreference(
                position=position,
                observed_acquisition_share=observed_share,
                context_expected_acquisition_share=expected_share,
                raw_residual_share=raw_residual,
                shrunk_residual_share=raw_residual * shrinkage,
                confidence=shrinkage,
                observed_position_acquisitions=observed[position],
                observed_positioned_acquisitions=estimated_acquisitions,
                status="estimated",
                context_authority_ids=context_authorities,
                evidence_ids=evidence_ids,
            )
        )

    profile = OwnerContextControlledPreferenceProfile(
        owner_id=owner_id,
        league_family_id=league_family_id,
        as_of=as_of,
        positions=tuple(rows),
        observed_positioned_acquisitions=estimated_acquisitions,
        estimated_position_count=4,
        mean_confidence=shrinkage,
        context_training_observation_count=training_observation_count,
        context_training_owner_count=training_owner_count,
        context_training_through=training_through,
        context_policy_parameter_id=context_policy.parameter_id,
        residual_policy_parameter_id=residual_policy.parameter_id,
        context_model_version=f"{model.model_version}+eventwise-history-v1",
        profile_model_version="owner-historical-covered-events-v1",
    )
    return OwnerHistoricalContextControlledPreferenceResult(profile=profile, coverage=coverage)
