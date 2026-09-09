from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .historical_context_profile import OwnerHistoricalContextControlledPreferenceResult
from .preference_stability import OwnerPreferenceStabilityProfile


class OwnerPositionInferenceQuality(FrozenModel):
    """Transparent evidence quality for one owner-position Behavioral inference.

    No composite score is produced. Historical coverage, residual confidence, and
    cross-time stability remain separate so downstream code cannot silently multiply
    them into a new authority weight.
    """

    position: Position
    preference_status: str
    residual_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    event_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    acquisition_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    covered_event_count: Annotated[int, Field(ge=0)]
    covered_positioned_acquisitions: Annotated[int, Field(ge=0)]
    stability_status: str
    stability_snapshot_count: Annotated[int, Field(ge=0)]
    latest_direction_agreement: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    residual_standard_deviation: Annotated[float | None, Field(ge=0.0)] = None
    mean_absolute_change: Annotated[float | None, Field(ge=0.0)] = None
    latest_residual_share: float | None = None

    @model_validator(mode="after")
    def validate_quality(self) -> "OwnerPositionInferenceQuality":
        if self.preference_status not in {"estimated", "unavailable"}:
            raise ValueError("owner inference quality preference status is invalid")
        if self.stability_status not in {"estimated", "unavailable", "not_supplied"}:
            raise ValueError("owner inference quality stability status is invalid")
        stability_metrics = (
            self.latest_direction_agreement,
            self.residual_standard_deviation,
            self.mean_absolute_change,
            self.latest_residual_share,
        )
        if self.stability_status == "estimated" and any(value is None for value in stability_metrics):
            raise ValueError("estimated stability quality requires complete stability metrics")
        if self.stability_status != "estimated" and any(value is not None for value in stability_metrics):
            raise ValueError("unestimated stability quality cannot claim stability metrics")
        return self


class OwnerBehaviorInferenceQualityProfile(FrozenModel):
    owner_id: str
    league_family_id: str
    as_of: datetime
    eligible_event_count: Annotated[int, Field(ge=0)]
    covered_event_count: Annotated[int, Field(ge=0)]
    eligible_positioned_acquisitions: Annotated[int, Field(ge=0)]
    covered_positioned_acquisitions: Annotated[int, Field(ge=0)]
    event_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    acquisition_coverage_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    positions: tuple[OwnerPositionInferenceQuality, ...]
    source_preference_model_version: str
    source_coverage_model_version: str
    source_stability_model_version: str | None = None
    model_version: str = "owner-behavior-inference-quality-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("owner inference quality as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> "OwnerBehaviorInferenceQualityProfile":
        if any(not value.strip() for value in (self.owner_id, self.league_family_id, self.source_preference_model_version, self.source_coverage_model_version, self.model_version)):
            raise ValueError("owner inference quality metadata cannot be blank")
        if tuple(item.position for item in self.positions) != (Position.QB, Position.RB, Position.WR, Position.TE):
            raise ValueError("owner inference quality requires ordered QB/RB/WR/TE rows")
        if self.covered_event_count > self.eligible_event_count or self.covered_positioned_acquisitions > self.eligible_positioned_acquisitions:
            raise ValueError("owner inference quality covered evidence cannot exceed eligible evidence")
        return self

    def position(self, position: str | Position) -> OwnerPositionInferenceQuality:
        target = Position(position)
        return next(item for item in self.positions if item.position == target)


def build_owner_behavior_inference_quality_profile(
    historical: OwnerHistoricalContextControlledPreferenceResult,
    *,
    stability: OwnerPreferenceStabilityProfile | None = None,
) -> OwnerBehaviorInferenceQualityProfile:
    """Join preference, coverage, and stability evidence without collapsing them.

    Stability is optional because a newly estimable owner may not yet have multiple
    PIT preference snapshots. If supplied, identity and as-of must match exactly.
    """

    profile = historical.profile
    coverage = historical.coverage
    if stability is not None:
        if stability.owner_id != profile.owner_id or stability.league_family_id != profile.league_family_id:
            raise ValueError("owner inference quality stability identity must match preference profile")
        if stability.as_of != profile.as_of:
            raise ValueError("owner inference quality stability as_of must match preference profile")

    rows: list[OwnerPositionInferenceQuality] = []
    for position in (Position.QB, Position.RB, Position.WR, Position.TE):
        preference = profile.position(position)
        stability_row = stability.position(position) if stability is not None else None
        if stability_row is not None and stability_row.status == "estimated":
            stability_status = "estimated"
            snapshot_count = stability_row.available_snapshot_count
            direction = stability_row.latest_direction_agreement
            stddev = stability_row.residual_standard_deviation
            mean_change = stability_row.mean_absolute_change
            latest = stability_row.latest_residual_share
        else:
            stability_status = stability_row.status if stability_row is not None else "not_supplied"
            snapshot_count = stability_row.available_snapshot_count if stability_row is not None else 0
            direction = stddev = mean_change = latest = None

        rows.append(
            OwnerPositionInferenceQuality(
                position=position,
                preference_status=preference.status,
                residual_confidence=preference.confidence,
                event_coverage_rate=coverage.event_coverage_rate,
                acquisition_coverage_rate=coverage.acquisition_coverage_rate,
                covered_event_count=coverage.estimated_event_count,
                covered_positioned_acquisitions=coverage.estimated_positioned_acquisitions,
                stability_status=stability_status,
                stability_snapshot_count=snapshot_count,
                latest_direction_agreement=direction,
                residual_standard_deviation=stddev,
                mean_absolute_change=mean_change,
                latest_residual_share=latest,
            )
        )

    return OwnerBehaviorInferenceQualityProfile(
        owner_id=profile.owner_id,
        league_family_id=profile.league_family_id,
        as_of=profile.as_of,
        eligible_event_count=coverage.eligible_event_count,
        covered_event_count=coverage.estimated_event_count,
        eligible_positioned_acquisitions=coverage.eligible_positioned_acquisitions,
        covered_positioned_acquisitions=coverage.estimated_positioned_acquisitions,
        event_coverage_rate=coverage.event_coverage_rate,
        acquisition_coverage_rate=coverage.acquisition_coverage_rate,
        positions=tuple(rows),
        source_preference_model_version=profile.model_version,
        source_coverage_model_version=coverage.model_version,
        source_stability_model_version=stability.model_version if stability is not None else None,
    )
