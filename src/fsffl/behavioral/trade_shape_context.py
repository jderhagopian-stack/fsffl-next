from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .context_dataset import BehavioralContextCalibrationDataset
from .context_expectation import BehavioralContextExpectationPolicy
from .context_expectation_v2 import _full_context_features
from .models import BehavioralEventKind, OwnerBehaviorEvent
from .residual_preference import BehavioralResidualPolicy


class BehavioralTradeShape(StrEnum):
    CONSOLIDATION = "consolidation"
    DIVERSIFICATION = "diversification"
    BALANCED = "balanced"


_SHAPES = (
    BehavioralTradeShape.CONSOLIDATION,
    BehavioralTradeShape.DIVERSIFICATION,
    BehavioralTradeShape.BALANCED,
)


def classify_behavioral_trade_shape(event: OwnerBehaviorEvent) -> BehavioralTradeShape:
    """Preserve the existing descriptive Behavioral trade-shape definition."""
    if event.kind != BehavioralEventKind.TRADE:
        raise ValueError("trade-shape classification requires a trade event")
    sent_count = len(event.disposed)
    received_count = len(event.acquired)
    if sent_count > received_count:
        return BehavioralTradeShape.CONSOLIDATION
    if received_count > sent_count:
        return BehavioralTradeShape.DIVERSIFICATION
    return BehavioralTradeShape.BALANCED


class BehavioralTradeShapeObservation(FrozenModel):
    event_id: str
    owner_id: str
    occurred_at: datetime
    features: tuple[float, ...]
    shape: BehavioralTradeShape
    source_snapshot_state_id: str

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("trade-shape observations require timezone-aware timestamps")
        return value

    @model_validator(mode="after")
    def validate_observation(self) -> "BehavioralTradeShapeObservation":
        if not self.event_id.strip() or not self.owner_id.strip() or not self.source_snapshot_state_id.strip():
            raise ValueError("trade-shape observation identifiers cannot be blank")
        if not self.features:
            raise ValueError("trade-shape observation requires context features")
        return self


class BehavioralTradeShapeContextModel(FrozenModel):
    observations: tuple[BehavioralTradeShapeObservation, ...]
    feature_count: Annotated[int, Field(gt=0)]
    source_dataset_model_version: str
    model_version: str = "behavioral-trade-shape-context-knn-v1"

    @model_validator(mode="after")
    def validate_model(self) -> "BehavioralTradeShapeContextModel":
        if not self.source_dataset_model_version.strip() or not self.model_version.strip():
            raise ValueError("trade-shape context model versions cannot be blank")
        if any(len(item.features) != self.feature_count for item in self.observations):
            raise ValueError("trade-shape context observations must share feature shape")
        return self


class BehavioralTradeShapeExpectation(FrozenModel):
    shape: BehavioralTradeShape
    expected_share: Annotated[float, Field(ge=0.0, le=1.0)]
    raw_neighbor_share: Annotated[float, Field(ge=0.0, le=1.0)]
    pooled_prior_share: Annotated[float, Field(ge=0.0, le=1.0)]


class BehavioralTradeShapeContextResult(FrozenModel):
    owner_id: str
    as_of: datetime
    expectations: tuple[BehavioralTradeShapeExpectation, ...] = ()
    unavailable_reason: str | None = None
    training_observation_count: Annotated[int, Field(ge=0)] = 0
    training_owner_count: Annotated[int, Field(ge=0)] = 0
    neighbor_count: Annotated[int, Field(ge=0)] = 0
    neighbor_owner_count: Annotated[int, Field(ge=0)] = 0
    evidence_weight: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    training_through: datetime | None = None
    policy_parameter_id: str
    source_model_version: str
    model_version: str = "behavioral-trade-shape-context-result-v1"

    @field_validator("as_of", "training_through")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("trade-shape context timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "BehavioralTradeShapeContextResult":
        if not self.owner_id.strip() or not self.policy_parameter_id.strip() or not self.source_model_version.strip():
            raise ValueError("trade-shape context result metadata cannot be blank")
        if self.unavailable_reason is not None:
            if self.expectations:
                raise ValueError("unavailable trade-shape context cannot contain estimates")
            return self
        if tuple(item.shape for item in self.expectations) != _SHAPES:
            raise ValueError("trade-shape context requires ordered consolidation/diversification/balanced estimates")
        if abs(sum(item.expected_share for item in self.expectations) - 1.0) > 1e-9:
            raise ValueError("trade-shape context shares must sum to one")
        return self

    def share_for(self, shape: str | BehavioralTradeShape) -> float | None:
        target = BehavioralTradeShape(shape)
        for item in self.expectations:
            if item.shape == target:
                return item.expected_share
        return None


def fit_behavioral_trade_shape_context_model(
    dataset: BehavioralContextCalibrationDataset,
    events: tuple[OwnerBehaviorEvent, ...] | list[OwnerBehaviorEvent],
) -> BehavioralTradeShapeContextModel:
    """Join observed trade shape to the same PIT contexts used by Behavioral calibration."""
    rows_by_id = {row.event_id: row for row in dataset.rows}
    observations: list[BehavioralTradeShapeObservation] = []
    feature_count = 21
    for event in sorted(events, key=lambda item: (item.occurred_at, item.event_id)):
        if event.kind != BehavioralEventKind.TRADE:
            continue
        row = rows_by_id.get(event.event_id)
        if row is None:
            continue
        if row.owner_id != event.owner_id or row.occurred_at != event.occurred_at:
            raise ValueError("trade-shape event/context identity must match")
        features = _full_context_features(row.context)
        feature_count = len(features)
        observations.append(
            BehavioralTradeShapeObservation(
                event_id=event.event_id,
                owner_id=event.owner_id,
                occurred_at=event.occurred_at,
                features=features,
                shape=classify_behavioral_trade_shape(event),
                source_snapshot_state_id=row.context.snapshot_state_id,
            )
        )
    return BehavioralTradeShapeContextModel(
        observations=tuple(observations),
        feature_count=feature_count,
        source_dataset_model_version=dataset.model_version,
    )


def _scale(observations: list[BehavioralTradeShapeObservation]) -> tuple[float, ...]:
    columns = list(zip(*(item.features for item in observations), strict=True))
    result = []
    for column in columns:
        values = list(column)
        if len(values) <= 1:
            result.append(1.0)
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        result.append(sqrt(variance) if variance > 0.0 else 1.0)
    return tuple(result)


def _distance(left: tuple[float, ...], right: tuple[float, ...], scales: tuple[float, ...]) -> float:
    return sqrt(sum(((a - b) / scale) ** 2 for a, b, scale in zip(left, right, scales, strict=True)))


def estimate_trade_shape_context_distribution(
    model: BehavioralTradeShapeContextModel,
    context,
    *,
    owner_id: str,
    policy: BehavioralContextExpectationPolicy,
) -> BehavioralTradeShapeContextResult:
    """Estimate trade shape from full PIT roster context, excluding focal-owner history."""
    eligible = [
        item for item in model.observations
        if item.occurred_at < context.occurred_at and item.owner_id != owner_id and item.event_id != context.event_id
    ]
    owners = {item.owner_id for item in eligible}
    training_through = max((item.occurred_at for item in eligible), default=None)
    base = dict(
        owner_id=owner_id,
        as_of=context.occurred_at,
        training_observation_count=len(eligible),
        training_owner_count=len(owners),
        training_through=training_through,
        policy_parameter_id=policy.parameter_id,
        source_model_version=model.model_version,
    )
    if len(owners) < policy.min_distinct_owners:
        return BehavioralTradeShapeContextResult(
            unavailable_reason="insufficient distinct other-owner PIT trade history for shape expectation", **base
        )
    scales = _scale(eligible)
    target = _full_context_features(context)
    ranked = sorted(eligible, key=lambda item: (_distance(target, item.features, scales), item.occurred_at, item.event_id))
    neighbors = ranked[: policy.neighbor_count]
    neighbor_owners = {item.owner_id for item in neighbors}
    if len(neighbor_owners) < policy.min_distinct_owners:
        return BehavioralTradeShapeContextResult(
            unavailable_reason="insufficient distinct-owner trade-shape neighborhood", **base
        )
    weight = len(neighbors) / (len(neighbors) + policy.prior_strength) if policy.prior_strength > 0 else 1.0
    expectations = []
    for shape in _SHAPES:
        raw = sum(item.shape == shape for item in neighbors) / len(neighbors)
        pooled = sum(item.shape == shape for item in eligible) / len(eligible)
        expectations.append(BehavioralTradeShapeExpectation(
            shape=shape,
            expected_share=weight * raw + (1.0 - weight) * pooled,
            raw_neighbor_share=raw,
            pooled_prior_share=pooled,
        ))
    return BehavioralTradeShapeContextResult(
        expectations=tuple(expectations),
        neighbor_count=len(neighbors),
        neighbor_owner_count=len(neighbor_owners),
        evidence_weight=weight,
        **base,
    )


class OwnerTradeShapePreference(FrozenModel):
    shape: BehavioralTradeShape
    observed_share: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    context_expected_share: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    raw_residual_share: float | None = None
    shrunk_residual_share: float | None = None
    status: str


class OwnerTradeShapePreferenceProfile(FrozenModel):
    owner_id: str
    league_family_id: str
    as_of: datetime
    shapes: tuple[OwnerTradeShapePreference, ...]
    eligible_trade_count: Annotated[int, Field(ge=0)]
    estimated_trade_count: Annotated[int, Field(ge=0)]
    coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    context_policy_parameter_id: str
    residual_policy_parameter_id: str
    context_model_version: str
    model_version: str = "owner-trade-shape-preference-profile-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("owner trade-shape profile as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> "OwnerTradeShapePreferenceProfile":
        if tuple(item.shape for item in self.shapes) != _SHAPES:
            raise ValueError("owner trade-shape profile requires ordered shape rows")
        if self.estimated_trade_count > self.eligible_trade_count:
            raise ValueError("estimated trade-shape events cannot exceed eligible events")
        expected = self.estimated_trade_count / self.eligible_trade_count if self.eligible_trade_count else 0.0
        if abs(self.coverage_rate - expected) > 1e-12:
            raise ValueError("trade-shape coverage rate must reconcile")
        estimated = all(item.status == "estimated" for item in self.shapes)
        if estimated:
            if abs(sum(item.raw_residual_share or 0.0 for item in self.shapes)) > 1e-9:
                raise ValueError("trade-shape raw residuals must net to zero")
            if abs(sum(item.shrunk_residual_share or 0.0 for item in self.shapes)) > 1e-9:
                raise ValueError("trade-shape shrunk residuals must net to zero")
        return self

    def shape(self, shape: str | BehavioralTradeShape) -> OwnerTradeShapePreference:
        target = BehavioralTradeShape(shape)
        return next(item for item in self.shapes if item.shape == target)


def build_owner_trade_shape_preference_profile(
    dataset: BehavioralContextCalibrationDataset,
    events: tuple[OwnerBehaviorEvent, ...] | list[OwnerBehaviorEvent],
    model: BehavioralTradeShapeContextModel,
    *,
    owner_id: str,
    league_family_id: str,
    context_policy: BehavioralContextExpectationPolicy,
    residual_policy: BehavioralResidualPolicy,
    as_of: datetime,
) -> OwnerTradeShapePreferenceProfile:
    """Residualize each historical trade shape against its own PIT context expectation."""
    events_by_id = {event.event_id: event for event in events}
    focal_rows = sorted(
        (row for row in dataset.rows if row.owner_id == owner_id and row.occurred_at <= as_of and events_by_id.get(row.event_id) is not None and events_by_id[row.event_id].kind == BehavioralEventKind.TRADE),
        key=lambda row: (row.occurred_at, row.event_id),
    )
    observed = {shape: 0 for shape in _SHAPES}
    expected = {shape: 0.0 for shape in _SHAPES}
    covered = 0
    for row in focal_rows:
        result = estimate_trade_shape_context_distribution(model, row.context, owner_id=owner_id, policy=context_policy)
        if result.unavailable_reason is not None:
            continue
        event = events_by_id[row.event_id]
        observed[classify_behavioral_trade_shape(event)] += 1
        for shape in _SHAPES:
            share = result.share_for(shape)
            if share is None:
                raise ValueError("available trade-shape context must contain every shape")
            expected[shape] += share
        covered += 1

    coverage_rate = covered / len(focal_rows) if focal_rows else 0.0
    if covered == 0:
        return OwnerTradeShapePreferenceProfile(
            owner_id=owner_id,
            league_family_id=league_family_id,
            as_of=as_of,
            shapes=tuple(OwnerTradeShapePreference(shape=shape, status="unavailable") for shape in _SHAPES),
            eligible_trade_count=len(focal_rows),
            estimated_trade_count=0,
            coverage_rate=coverage_rate,
            confidence=0.0,
            context_policy_parameter_id=context_policy.parameter_id,
            residual_policy_parameter_id=residual_policy.parameter_id,
            context_model_version=model.model_version,
        )
    shrinkage = covered / (covered + residual_policy.prior_strength)
    rows = []
    for shape in _SHAPES:
        observed_share = observed[shape] / covered
        expected_share = expected[shape] / covered
        raw = observed_share - expected_share
        rows.append(OwnerTradeShapePreference(
            shape=shape,
            observed_share=observed_share,
            context_expected_share=expected_share,
            raw_residual_share=raw,
            shrunk_residual_share=raw * shrinkage,
            status="estimated",
        ))
    return OwnerTradeShapePreferenceProfile(
        owner_id=owner_id,
        league_family_id=league_family_id,
        as_of=as_of,
        shapes=tuple(rows),
        eligible_trade_count=len(focal_rows),
        estimated_trade_count=covered,
        coverage_rate=coverage_rate,
        confidence=shrinkage,
        context_policy_parameter_id=context_policy.parameter_id,
        residual_policy_parameter_id=residual_policy.parameter_id,
        context_model_version=model.model_version,
    )
