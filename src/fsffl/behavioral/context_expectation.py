from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .action_context import BehavioralActionContext, BehavioralPositionContext
from .context_dataset import BehavioralContextCalibrationDataset


_CONTEXT_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)
_FEATURE_NAMES = (
    "rostered_vs_league",
    "active_vs_league",
    "active_vs_direct_starters",
    "direct_starter_requirement",
    "flex_slot_count",
    "superflex_slot_count",
)


class BehavioralContextExpectationPolicy(FrozenModel):
    """Explicit governance for the empirical context-only expectation model.

    The model learns outcomes from comparable historical actions. This policy owns
    only the non-empirical choices: how many nearest historical contexts to use,
    how strongly to shrink sparse neighborhoods toward the eligible pooled prior,
    and how many distinct other owners are required before an estimate is exposed.
    """

    parameter_id: str
    neighbor_count: Annotated[int, Field(ge=1)]
    prior_strength: Annotated[float, Field(ge=0.0)]
    min_distinct_owners: Annotated[int, Field(ge=1)] = 2
    provenance: str
    update_mode: str = "empirically_tunable"
    model_version: str = "behavioral-context-expectation-policy-v1"

    @model_validator(mode="after")
    def validate_policy(self) -> "BehavioralContextExpectationPolicy":
        if any(
            not value.strip()
            for value in (self.parameter_id, self.provenance, self.update_mode, self.model_version)
        ):
            raise ValueError("behavioral context expectation policy metadata cannot be blank")
        return self


class BehavioralContextExpectationObservation(FrozenModel):
    event_id: str
    owner_id: str
    occurred_at: datetime
    position: Position
    features: tuple[float, ...]
    acquired_position_count: Annotated[int, Field(ge=0)]
    total_positioned_acquisitions: Annotated[int, Field(gt=0)]
    source_snapshot_state_id: str

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("context expectation observations require timezone-aware timestamps")
        return value

    @model_validator(mode="after")
    def validate_observation(self) -> "BehavioralContextExpectationObservation":
        if not self.event_id.strip() or not self.owner_id.strip() or not self.source_snapshot_state_id.strip():
            raise ValueError("context expectation observation identifiers cannot be blank")
        if len(self.features) != len(_FEATURE_NAMES):
            raise ValueError("context expectation observation feature shape is invalid")
        if self.acquired_position_count > self.total_positioned_acquisitions:
            raise ValueError("position acquisitions cannot exceed total positioned acquisitions")
        return self


class BehavioralContextFeatureScale(FrozenModel):
    position: Position
    means: tuple[float, ...]
    standard_deviations: tuple[float, ...]

    @model_validator(mode="after")
    def validate_scale(self) -> "BehavioralContextFeatureScale":
        if len(self.means) != len(_FEATURE_NAMES) or len(self.standard_deviations) != len(_FEATURE_NAMES):
            raise ValueError("context expectation feature scale shape is invalid")
        if any(value <= 0.0 for value in self.standard_deviations):
            raise ValueError("context expectation feature scales must be positive")
        return self


class BehavioralContextExpectationModel(FrozenModel):
    """Pooled empirical context model with no owner-specific effects.

    Observations are retained with timestamps so every prediction can filter out
    future actions. Owner identity is used only to exclude the focal owner's own
    history from the context baseline and to enforce distinct-owner coverage.
    """

    observations: tuple[BehavioralContextExpectationObservation, ...]
    feature_scales: tuple[BehavioralContextFeatureScale, ...]
    source_dataset_model_version: str
    source_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    model_version: str = "behavioral-context-expectation-knn-v1"

    @model_validator(mode="after")
    def validate_model(self) -> "BehavioralContextExpectationModel":
        if not self.source_dataset_model_version.strip() or not self.model_version.strip():
            raise ValueError("context expectation model versions cannot be blank")
        positions = [item.position for item in self.feature_scales]
        if len(positions) != len(set(positions)):
            raise ValueError("context expectation model may have only one feature scale per position")
        return self


class BehavioralPositionContextExpectation(FrozenModel):
    position: Position
    expected_acquisition_share: Annotated[float, Field(ge=0.0, le=1.0)]
    raw_neighbor_share: Annotated[float, Field(ge=0.0, le=1.0)]
    pooled_prior_share: Annotated[float, Field(ge=0.0, le=1.0)]
    neighbor_count: Annotated[int, Field(ge=1)]
    distinct_owner_count: Annotated[int, Field(ge=1)]
    neighbor_positioned_acquisitions: Annotated[int, Field(gt=0)]
    evidence_weight: Annotated[float, Field(ge=0.0, le=1.0)]


class BehavioralContextExpectationResult(FrozenModel):
    owner_id: str
    as_of: datetime
    expectations: tuple[BehavioralPositionContextExpectation, ...] = ()
    unavailable_reason: str | None = None
    training_observation_count: Annotated[int, Field(ge=0)] = 0
    training_owner_count: Annotated[int, Field(ge=0)] = 0
    training_through: datetime | None = None
    policy_parameter_id: str
    source_model_version: str
    model_version: str = "behavioral-context-expectation-result-v1"

    @field_validator("as_of", "training_through")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("context expectation result timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "BehavioralContextExpectationResult":
        if not self.owner_id.strip() or not self.policy_parameter_id.strip() or not self.source_model_version.strip():
            raise ValueError("context expectation result metadata cannot be blank")
        if self.unavailable_reason is not None:
            if self.expectations:
                raise ValueError("unavailable context expectation cannot contain estimates")
            if not self.unavailable_reason.strip():
                raise ValueError("context expectation unavailable reason cannot be blank")
            return self
        if len(self.expectations) != len(_CONTEXT_POSITIONS):
            raise ValueError("available context expectation requires QB/RB/WR/TE estimates")
        total = sum(item.expected_acquisition_share for item in self.expectations)
        if abs(total - 1.0) > 1e-9:
            raise ValueError("context expectation shares must sum to one")
        return self

    def share_for(self, position: str | Position) -> float | None:
        target = Position(position)
        for item in self.expectations:
            if item.position == target:
                return item.expected_acquisition_share
        return None


def _features(context: BehavioralActionContext, row: BehavioralPositionContext) -> tuple[float, ...]:
    return (
        row.rostered_count - row.league_average_rostered_count,
        row.active_rostered_count - row.league_average_active_rostered_count,
        row.active_rostered_count - row.direct_starter_requirement,
        float(row.direct_starter_requirement),
        float(context.flex_slot_count),
        float(context.superflex_slot_count),
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_std(values: list[float], mean: float) -> float:
    if len(values) <= 1:
        return 1.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    # A constant feature carries no distance information. Scale it to one rather
    # than injecting an arbitrary epsilon that could distort another feature.
    return sqrt(variance) if variance > 0.0 else 1.0


def fit_behavioral_context_expectation_model(
    dataset: BehavioralContextCalibrationDataset,
) -> BehavioralContextExpectationModel:
    """Fit the data substrate for a cross-owner empirical context model.

    Only rows with at least one positioned player acquisition teach the conditional
    distribution of QB/RB/WR/TE acquisitions. No owner-specific indicator or future
    outcome is included in the feature vector.
    """

    observations: list[BehavioralContextExpectationObservation] = []
    feature_values: dict[Position, list[list[float]]] = defaultdict(list)

    for row in dataset.rows:
        total = sum(row.acquired_position_counts.get(position.value, 0) for position in _CONTEXT_POSITIONS)
        if total <= 0:
            continue
        by_position = {item.position: item for item in row.context.positions}
        for position in _CONTEXT_POSITIONS:
            position_context = by_position.get(position)
            if position_context is None:
                continue
            values = _features(row.context, position_context)
            observations.append(
                BehavioralContextExpectationObservation(
                    event_id=row.event_id,
                    owner_id=row.owner_id,
                    occurred_at=row.occurred_at,
                    position=position,
                    features=values,
                    acquired_position_count=row.acquired_position_counts.get(position.value, 0),
                    total_positioned_acquisitions=total,
                    source_snapshot_state_id=row.context.snapshot_state_id,
                )
            )
            feature_values[position].append(list(values))

    scales: list[BehavioralContextFeatureScale] = []
    for position in _CONTEXT_POSITIONS:
        rows = feature_values.get(position, [])
        if not rows:
            continue
        columns = list(zip(*rows, strict=True))
        means = tuple(_mean(list(column)) for column in columns)
        stds = tuple(_sample_std(list(column), mean) for column, mean in zip(columns, means, strict=True))
        scales.append(
            BehavioralContextFeatureScale(
                position=position,
                means=means,
                standard_deviations=stds,
            )
        )

    return BehavioralContextExpectationModel(
        observations=tuple(observations),
        feature_scales=tuple(scales),
        source_dataset_model_version=dataset.model_version,
        source_coverage_rate=dataset.coverage_rate,
    )


def _distance(
    left: tuple[float, ...],
    right: tuple[float, ...],
    scale: BehavioralContextFeatureScale,
) -> float:
    return sqrt(
        sum(
            ((a - b) / std) ** 2
            for a, b, std in zip(left, right, scale.standard_deviations, strict=True)
        )
    )


def estimate_context_acquisition_distribution(
    model: BehavioralContextExpectationModel,
    context: BehavioralActionContext,
    *,
    owner_id: str,
    policy: BehavioralContextExpectationPolicy,
) -> BehavioralContextExpectationResult:
    """Estimate the position mix expected from context, excluding focal-owner history.

    Every eligible training observation must precede the target action/context.
    Neighbors are chosen independently for each position on standardized factual
    roster/lineup features. The four shrunken empirical rates are normalized into a
    position-acquisition distribution so it can feed the existing residual model.
    """

    if context.occurred_at.tzinfo is None:
        raise ValueError("context expectation target timestamp must be timezone-aware")
    if not owner_id.strip():
        raise ValueError("context expectation owner_id cannot be blank")

    scale_by_position = {item.position: item for item in model.feature_scales}
    target_by_position = {item.position: item for item in context.positions}
    eligible_all = [
        item
        for item in model.observations
        if item.occurred_at < context.occurred_at and item.owner_id != owner_id and item.event_id != context.event_id
    ]
    distinct_owners_all = {item.owner_id for item in eligible_all}
    if len(distinct_owners_all) < policy.min_distinct_owners:
        return BehavioralContextExpectationResult(
            owner_id=owner_id,
            as_of=context.occurred_at,
            unavailable_reason="insufficient distinct other-owner PIT history for context expectation",
            training_observation_count=len(eligible_all),
            training_owner_count=len(distinct_owners_all),
            training_through=max((item.occurred_at for item in eligible_all), default=None),
            policy_parameter_id=policy.parameter_id,
            source_model_version=model.model_version,
        )

    provisional: list[tuple[Position, float, float, float, int, int, int, float]] = []
    for position in _CONTEXT_POSITIONS:
        scale = scale_by_position.get(position)
        target = target_by_position.get(position)
        if scale is None or target is None:
            return BehavioralContextExpectationResult(
                owner_id=owner_id,
                as_of=context.occurred_at,
                unavailable_reason=f"missing empirical feature coverage for {position.value}",
                training_observation_count=len(eligible_all),
                training_owner_count=len(distinct_owners_all),
                training_through=max((item.occurred_at for item in eligible_all), default=None),
                policy_parameter_id=policy.parameter_id,
                source_model_version=model.model_version,
            )

        candidates = [item for item in eligible_all if item.position == position]
        target_features = _features(context, target)
        ranked = sorted(
            candidates,
            key=lambda item: (_distance(target_features, item.features, scale), item.occurred_at, item.event_id),
        )
        neighbors = ranked[: policy.neighbor_count]
        owners = {item.owner_id for item in neighbors}
        if len(owners) < policy.min_distinct_owners:
            return BehavioralContextExpectationResult(
                owner_id=owner_id,
                as_of=context.occurred_at,
                unavailable_reason=f"insufficient distinct-owner neighborhood for {position.value}",
                training_observation_count=len(eligible_all),
                training_owner_count=len(distinct_owners_all),
                training_through=max((item.occurred_at for item in eligible_all), default=None),
                policy_parameter_id=policy.parameter_id,
                source_model_version=model.model_version,
            )

        neighbor_total = sum(item.total_positioned_acquisitions for item in neighbors)
        neighbor_position = sum(item.acquired_position_count for item in neighbors)
        all_position = sum(item.acquired_position_count for item in candidates)
        all_total = sum(item.total_positioned_acquisitions for item in candidates)
        if neighbor_total <= 0 or all_total <= 0:
            return BehavioralContextExpectationResult(
                owner_id=owner_id,
                as_of=context.occurred_at,
                unavailable_reason=f"insufficient positioned acquisition outcomes for {position.value}",
                training_observation_count=len(eligible_all),
                training_owner_count=len(distinct_owners_all),
                training_through=max((item.occurred_at for item in eligible_all), default=None),
                policy_parameter_id=policy.parameter_id,
                source_model_version=model.model_version,
            )

        raw = neighbor_position / neighbor_total
        pooled = all_position / all_total
        weight = neighbor_total / (neighbor_total + policy.prior_strength) if policy.prior_strength > 0 else 1.0
        shrunken = weight * raw + (1.0 - weight) * pooled
        provisional.append(
            (position, shrunken, raw, pooled, len(neighbors), len(owners), neighbor_total, weight)
        )

    normalization = sum(item[1] for item in provisional)
    if normalization <= 0.0:
        return BehavioralContextExpectationResult(
            owner_id=owner_id,
            as_of=context.occurred_at,
            unavailable_reason="empirical context expectation has no positioned acquisition mass",
            training_observation_count=len(eligible_all),
            training_owner_count=len(distinct_owners_all),
            training_through=max((item.occurred_at for item in eligible_all), default=None),
            policy_parameter_id=policy.parameter_id,
            source_model_version=model.model_version,
        )

    expectations = tuple(
        BehavioralPositionContextExpectation(
            position=position,
            expected_acquisition_share=shrunken / normalization,
            raw_neighbor_share=raw,
            pooled_prior_share=pooled,
            neighbor_count=count,
            distinct_owner_count=owner_count,
            neighbor_positioned_acquisitions=neighbor_total,
            evidence_weight=weight,
        )
        for position, shrunken, raw, pooled, count, owner_count, neighbor_total, weight in provisional
    )
    return BehavioralContextExpectationResult(
        owner_id=owner_id,
        as_of=context.occurred_at,
        expectations=expectations,
        training_observation_count=len(eligible_all),
        training_owner_count=len(distinct_owners_all),
        training_through=max((item.occurred_at for item in eligible_all), default=None),
        policy_parameter_id=policy.parameter_id,
        source_model_version=model.model_version,
    )
