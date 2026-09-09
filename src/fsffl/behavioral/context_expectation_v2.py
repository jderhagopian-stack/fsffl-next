from __future__ import annotations

from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .action_context import BehavioralActionContext
from .context_dataset import BehavioralContextCalibrationDataset
from .context_expectation import (
    BehavioralContextExpectationPolicy,
    BehavioralContextExpectationResult,
    BehavioralPositionContextExpectation,
)


_CONTEXT_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class BehavioralMulticlassContextObservation(FrozenModel):
    """One PIT action represented by the full roster context and position outcome."""

    event_id: str
    owner_id: str
    occurred_at: datetime
    features: tuple[float, ...]
    acquired_position_counts: dict[str, int]
    total_positioned_acquisitions: Annotated[int, Field(gt=0)]
    source_snapshot_state_id: str

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("multiclass context observations require timezone-aware timestamps")
        return value

    @model_validator(mode="after")
    def validate_observation(self) -> "BehavioralMulticlassContextObservation":
        if not self.event_id.strip() or not self.owner_id.strip() or not self.source_snapshot_state_id.strip():
            raise ValueError("multiclass context observation identifiers cannot be blank")
        if not self.features:
            raise ValueError("multiclass context observation requires full-roster features")
        relevant = sum(self.acquired_position_counts.get(position.value, 0) for position in _CONTEXT_POSITIONS)
        if relevant != self.total_positioned_acquisitions:
            raise ValueError("multiclass context outcome counts must reconcile")
        if any(value < 0 for value in self.acquired_position_counts.values()):
            raise ValueError("multiclass context acquisition counts cannot be negative")
        return self


class BehavioralMulticlassContextExpectationModel(FrozenModel):
    """Cross-owner, PIT-safe full-roster model for position acquisition choice."""

    observations: tuple[BehavioralMulticlassContextObservation, ...]
    feature_count: Annotated[int, Field(gt=0)]
    source_dataset_model_version: str
    source_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    model_version: str = "behavioral-context-expectation-multiclass-knn-v2"

    @model_validator(mode="after")
    def validate_model(self) -> "BehavioralMulticlassContextExpectationModel":
        if not self.source_dataset_model_version.strip() or not self.model_version.strip():
            raise ValueError("multiclass context model versions cannot be blank")
        if any(len(item.features) != self.feature_count for item in self.observations):
            raise ValueError("multiclass context observations must share feature shape")
        return self


def _full_context_features(context: BehavioralActionContext) -> tuple[float, ...]:
    """Represent the full pre-action roster state without owner identity or outcomes."""

    by_position = {row.position: row for row in context.positions}
    values: list[float] = []
    for position in _CONTEXT_POSITIONS:
        row = by_position.get(position)
        if row is None:
            raise ValueError(f"full-roster context is missing {position.value}")
        values.extend(
            (
                row.rostered_count - row.league_average_rostered_count,
                row.active_rostered_count - row.league_average_active_rostered_count,
                row.active_rostered_count - row.direct_starter_requirement,
                float(row.direct_starter_requirement),
            )
        )
    values.extend(
        (
            float(context.flex_slot_count),
            float(context.superflex_slot_count),
            float(context.roster_size),
            float(context.active_roster_size),
            float(context.owned_pick_count),
        )
    )
    return tuple(values)


def fit_behavioral_multiclass_context_expectation_model(
    dataset: BehavioralContextCalibrationDataset,
) -> BehavioralMulticlassContextExpectationModel:
    """Build the full-roster empirical substrate from positioned acquisitions."""

    observations: list[BehavioralMulticlassContextObservation] = []
    feature_count: int | None = None
    for row in dataset.rows:
        total = sum(row.acquired_position_counts.get(position.value, 0) for position in _CONTEXT_POSITIONS)
        if total <= 0:
            continue
        features = _full_context_features(row.context)
        if feature_count is None:
            feature_count = len(features)
        elif len(features) != feature_count:
            raise ValueError("multiclass context feature shape changed across calibration rows")
        observations.append(
            BehavioralMulticlassContextObservation(
                event_id=row.event_id,
                owner_id=row.owner_id,
                occurred_at=row.occurred_at,
                features=features,
                acquired_position_counts={
                    position.value: row.acquired_position_counts.get(position.value, 0)
                    for position in _CONTEXT_POSITIONS
                },
                total_positioned_acquisitions=total,
                source_snapshot_state_id=row.context.snapshot_state_id,
            )
        )

    return BehavioralMulticlassContextExpectationModel(
        observations=tuple(observations),
        feature_count=feature_count or len(_full_context_features(dataset.rows[0].context)) if dataset.rows else 21,
        source_dataset_model_version=dataset.model_version,
        source_coverage_rate=dataset.coverage_rate,
    )


def _sample_scale(observations: list[BehavioralMulticlassContextObservation]) -> tuple[float, ...]:
    if not observations:
        return ()
    columns = list(zip(*(item.features for item in observations), strict=True))
    scales: list[float] = []
    for column in columns:
        values = list(column)
        if len(values) <= 1:
            scales.append(1.0)
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        scales.append(sqrt(variance) if variance > 0.0 else 1.0)
    return tuple(scales)


def _distance(left: tuple[float, ...], right: tuple[float, ...], scales: tuple[float, ...]) -> float:
    return sqrt(sum(((a - b) / scale) ** 2 for a, b, scale in zip(left, right, scales, strict=True)))


def estimate_multiclass_context_acquisition_distribution(
    model: BehavioralMulticlassContextExpectationModel,
    context: BehavioralActionContext,
    *,
    owner_id: str,
    policy: BehavioralContextExpectationPolicy,
) -> BehavioralContextExpectationResult:
    """Estimate QB/RB/WR/TE acquisition mix from the entire PIT roster context.

    The focal owner's own observations and all same-time/future actions are excluded.
    One full-context neighbor set is used for all four outcomes, allowing the model
    to learn substitution effects such as WR acquisition associated with RB surplus.
    Feature scaling is re-estimated only from the eligible historical population at
    prediction time, so future contexts cannot leak into distance calculations.
    """

    if context.occurred_at.tzinfo is None:
        raise ValueError("multiclass context target timestamp must be timezone-aware")
    if not owner_id.strip():
        raise ValueError("multiclass context owner_id cannot be blank")

    eligible = [
        item
        for item in model.observations
        if item.occurred_at < context.occurred_at and item.owner_id != owner_id and item.event_id != context.event_id
    ]
    distinct_owners = {item.owner_id for item in eligible}
    training_through = max((item.occurred_at for item in eligible), default=None)
    if len(distinct_owners) < policy.min_distinct_owners:
        return BehavioralContextExpectationResult(
            owner_id=owner_id,
            as_of=context.occurred_at,
            unavailable_reason="insufficient distinct other-owner PIT history for multiclass context expectation",
            training_observation_count=len(eligible),
            training_owner_count=len(distinct_owners),
            training_through=training_through,
            policy_parameter_id=policy.parameter_id,
            source_model_version=model.model_version,
        )

    scales = _sample_scale(eligible)
    target_features = _full_context_features(context)
    ranked = sorted(
        eligible,
        key=lambda item: (_distance(target_features, item.features, scales), item.occurred_at, item.event_id),
    )
    neighbors = ranked[: policy.neighbor_count]
    neighbor_owners = {item.owner_id for item in neighbors}
    if len(neighbor_owners) < policy.min_distinct_owners:
        return BehavioralContextExpectationResult(
            owner_id=owner_id,
            as_of=context.occurred_at,
            unavailable_reason="insufficient distinct-owner multiclass neighborhood",
            training_observation_count=len(eligible),
            training_owner_count=len(distinct_owners),
            training_through=training_through,
            policy_parameter_id=policy.parameter_id,
            source_model_version=model.model_version,
        )

    neighbor_total = sum(item.total_positioned_acquisitions for item in neighbors)
    pooled_total = sum(item.total_positioned_acquisitions for item in eligible)
    if neighbor_total <= 0 or pooled_total <= 0:
        return BehavioralContextExpectationResult(
            owner_id=owner_id,
            as_of=context.occurred_at,
            unavailable_reason="insufficient positioned acquisition outcomes for multiclass context expectation",
            training_observation_count=len(eligible),
            training_owner_count=len(distinct_owners),
            training_through=training_through,
            policy_parameter_id=policy.parameter_id,
            source_model_version=model.model_version,
        )

    weight = neighbor_total / (neighbor_total + policy.prior_strength) if policy.prior_strength > 0 else 1.0
    expectations: list[BehavioralPositionContextExpectation] = []
    for position in _CONTEXT_POSITIONS:
        neighbor_position = sum(item.acquired_position_counts.get(position.value, 0) for item in neighbors)
        pooled_position = sum(item.acquired_position_counts.get(position.value, 0) for item in eligible)
        raw = neighbor_position / neighbor_total
        pooled = pooled_position / pooled_total
        expected = weight * raw + (1.0 - weight) * pooled
        expectations.append(
            BehavioralPositionContextExpectation(
                position=position,
                expected_acquisition_share=expected,
                raw_neighbor_share=raw,
                pooled_prior_share=pooled,
                neighbor_count=len(neighbors),
                distinct_owner_count=len(neighbor_owners),
                neighbor_positioned_acquisitions=neighbor_total,
                evidence_weight=weight,
            )
        )

    total_share = sum(item.expected_acquisition_share for item in expectations)
    if abs(total_share - 1.0) > 1e-9:
        raise ValueError("multiclass context expectation shares must sum to one")

    return BehavioralContextExpectationResult(
        owner_id=owner_id,
        as_of=context.occurred_at,
        expectations=tuple(expectations),
        training_observation_count=len(eligible),
        training_owner_count=len(distinct_owners),
        training_through=training_through,
        policy_parameter_id=policy.parameter_id,
        source_model_version=model.model_version,
    )
