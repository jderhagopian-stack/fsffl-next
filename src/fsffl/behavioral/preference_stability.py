from __future__ import annotations

from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .context_controlled_profile import OwnerContextControlledPreferenceProfile


_STABILITY_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class OwnerPositionPreferenceStability(FrozenModel):
    """Descriptive persistence evidence for one context-controlled position tendency.

    This object intentionally avoids a composite stability score. It exposes the
    empirical ingredients separately so downstream consumers can distinguish a
    persistent sign, a volatile magnitude, sparse history, and a recent shift.
    """

    position: Position
    available_snapshot_count: Annotated[int, Field(ge=0)]
    first_estimated_at: datetime | None = None
    latest_estimated_at: datetime | None = None
    earliest_residual_share: float | None = None
    latest_residual_share: float | None = None
    mean_residual_share: float | None = None
    residual_standard_deviation: Annotated[float | None, Field(ge=0.0)] = None
    mean_absolute_change: Annotated[float | None, Field(ge=0.0)] = None
    nonzero_snapshot_count: Annotated[int, Field(ge=0)] = 0
    positive_snapshot_count: Annotated[int, Field(ge=0)] = 0
    negative_snapshot_count: Annotated[int, Field(ge=0)] = 0
    latest_direction_agreement: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    latest_confidence: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    status: str
    unavailable_reason: str | None = None

    @field_validator("first_estimated_at", "latest_estimated_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("owner preference stability timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_stability(self) -> "OwnerPositionPreferenceStability":
        if self.status not in {"estimated", "unavailable"}:
            raise ValueError("owner preference stability status is invalid")
        if self.positive_snapshot_count + self.negative_snapshot_count != self.nonzero_snapshot_count:
            raise ValueError("owner preference stability direction counts must reconcile")
        if self.nonzero_snapshot_count > self.available_snapshot_count:
            raise ValueError("nonzero stability snapshots cannot exceed available snapshots")
        numeric = (
            self.earliest_residual_share,
            self.latest_residual_share,
            self.mean_residual_share,
            self.residual_standard_deviation,
            self.mean_absolute_change,
            self.latest_confidence,
        )
        if self.status == "estimated":
            if self.available_snapshot_count < 2:
                raise ValueError("estimated stability requires at least two snapshots")
            if self.first_estimated_at is None or self.latest_estimated_at is None:
                raise ValueError("estimated stability requires snapshot timestamps")
            if any(value is None for value in numeric):
                raise ValueError("estimated stability requires complete descriptive metrics")
            if self.unavailable_reason is not None:
                raise ValueError("estimated stability cannot carry unavailable_reason")
        else:
            if self.unavailable_reason is None or not self.unavailable_reason.strip():
                raise ValueError("unavailable stability requires reason")
            if any(value is not None for value in numeric):
                raise ValueError("unavailable stability cannot claim persistence metrics")
            if self.latest_direction_agreement is not None:
                raise ValueError("unavailable stability cannot claim direction agreement")
        return self


class OwnerPreferenceStabilityProfile(FrozenModel):
    """Cross-time persistence view of context-controlled QB/RB/WR/TE tendencies."""

    owner_id: str
    league_family_id: str
    as_of: datetime
    snapshot_count: Annotated[int, Field(ge=0)]
    positions: tuple[OwnerPositionPreferenceStability, ...]
    source_profile_model_versions: tuple[str, ...]
    model_version: str = "owner-preference-stability-profile-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("owner preference stability profile as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> "OwnerPreferenceStabilityProfile":
        if not self.owner_id.strip() or not self.league_family_id.strip() or not self.model_version.strip():
            raise ValueError("owner preference stability profile metadata cannot be blank")
        if tuple(item.position for item in self.positions) != _STABILITY_POSITIONS:
            raise ValueError("owner preference stability profile requires ordered QB/RB/WR/TE rows")
        if self.snapshot_count != len(self.source_profile_model_versions):
            raise ValueError("stability profile snapshot/model-version counts must reconcile")
        return self

    def position(self, position: str | Position) -> OwnerPositionPreferenceStability:
        target = Position(position)
        return next(item for item in self.positions if item.position == target)


def _sample_std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def build_owner_preference_stability_profile(
    profiles: tuple[OwnerContextControlledPreferenceProfile, ...] | list[OwnerContextControlledPreferenceProfile],
    *,
    as_of: datetime,
) -> OwnerPreferenceStabilityProfile:
    """Describe how context-controlled owner tendencies persist across PIT snapshots.

    Only supplied profiles at or before `as_of` are admitted. All snapshots must
    belong to the same owner and league family. A position needs at least two
    estimated snapshots before persistence statistics are exposed; otherwise it is
    explicitly unavailable rather than treated as stable or neutral.
    """

    if as_of.tzinfo is None:
        raise ValueError("owner preference stability as_of must be timezone-aware")
    admitted = sorted((profile for profile in profiles if profile.as_of <= as_of), key=lambda item: item.as_of)
    if not admitted:
        raise ValueError("owner preference stability requires at least one PIT profile")

    owners = {profile.owner_id for profile in admitted}
    families = {profile.league_family_id for profile in admitted}
    if len(owners) != 1 or len(families) != 1:
        raise ValueError("owner preference stability profiles must share owner and league family")
    timestamps = [profile.as_of for profile in admitted]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("owner preference stability snapshots require unique as_of timestamps")

    rows: list[OwnerPositionPreferenceStability] = []
    for position in _STABILITY_POSITIONS:
        estimates = []
        for profile in admitted:
            row = profile.position(position)
            if row.status == "estimated" and row.shrunk_residual_share is not None:
                estimates.append((profile.as_of, row.shrunk_residual_share, row.confidence))
        if len(estimates) < 2:
            rows.append(
                OwnerPositionPreferenceStability(
                    position=position,
                    available_snapshot_count=len(estimates),
                    status="unavailable",
                    unavailable_reason="fewer than two estimated PIT preference snapshots",
                )
            )
            continue

        values = [item[1] for item in estimates]
        nonzero = [value for value in values if value != 0.0]
        positive = sum(value > 0.0 for value in nonzero)
        negative = sum(value < 0.0 for value in nonzero)
        latest = values[-1]
        if latest > 0.0 and nonzero:
            direction_agreement = positive / len(nonzero)
        elif latest < 0.0 and nonzero:
            direction_agreement = negative / len(nonzero)
        else:
            direction_agreement = None
        changes = [abs(current - previous) for previous, current in zip(values, values[1:])]
        rows.append(
            OwnerPositionPreferenceStability(
                position=position,
                available_snapshot_count=len(estimates),
                first_estimated_at=estimates[0][0],
                latest_estimated_at=estimates[-1][0],
                earliest_residual_share=values[0],
                latest_residual_share=latest,
                mean_residual_share=sum(values) / len(values),
                residual_standard_deviation=_sample_std(values),
                mean_absolute_change=sum(changes) / len(changes),
                nonzero_snapshot_count=len(nonzero),
                positive_snapshot_count=positive,
                negative_snapshot_count=negative,
                latest_direction_agreement=direction_agreement,
                latest_confidence=estimates[-1][2],
                status="estimated",
            )
        )

    return OwnerPreferenceStabilityProfile(
        owner_id=admitted[0].owner_id,
        league_family_id=admitted[0].league_family_id,
        as_of=as_of,
        snapshot_count=len(admitted),
        positions=tuple(rows),
        source_profile_model_versions=tuple(profile.model_version for profile in admitted),
    )
