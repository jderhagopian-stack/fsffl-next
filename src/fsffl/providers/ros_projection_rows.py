from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, canonical_nfl_team


class ProjectionRightsStatus(StrEnum):
    """Deployment-rights disposition for a projection acquisition path."""

    RESEARCH_ONLY = "research_only"
    LICENSED_BETA = "licensed_beta"
    PRODUCTION_CLEARED = "production_cleared"
    UNKNOWN = "unknown"


class RosProjectionRow(FrozenModel):
    """Provider-shaped K/DST rest-of-season row before Forecast normalization."""

    provider: str
    external_id: str
    subject_name: str
    position: Position
    nfl_team: str
    projected_games: Annotated[int, Field(ge=0, le=18)] | None = None
    stats: tuple[tuple[str, float], ...]

    @field_validator("provider", "external_id", "subject_name")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ROS row identifiers cannot be blank")
        return value

    @field_validator("nfl_team")
    @classmethod
    def normalize_team(cls, value: str) -> str:
        return canonical_nfl_team(value)

    @model_validator(mode="after")
    def validate_row(self) -> "RosProjectionRow":
        if self.position not in {Position.K, Position.DST}:
            raise ValueError("late-start ROS row must be K or D/ST")
        keys = [key for key, _value in self.stats]
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("ROS row stats must be non-empty with unique keys")
        return self

    @property
    def stat_map(self) -> dict[str, float]:
        return dict(self.stats)


class RosProjectionSnapshot(FrozenModel):
    """Horizon-explicit provider capture for the 2026 late-start exception."""

    provider: str
    independence_group: str
    endpoint: str
    season: Annotated[int, Field(ge=2000)]
    horizon: Literal["rest_of_season"] = "rest_of_season"
    captured_at: datetime
    provider_effective_at: datetime | None = None
    rows: tuple[RosProjectionRow, ...]
    source_version: str
    usage_class: str
    rights_status: ProjectionRightsStatus
    content_sha256: str

    @field_validator(
        "provider",
        "independence_group",
        "endpoint",
        "source_version",
        "usage_class",
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ROS snapshot identifiers cannot be blank")
        return value

    @field_validator("captured_at", "provider_effective_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("ROS snapshot timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("content_sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("content_sha256 must be a lowercase SHA-256 digest")
        return normalized

    @model_validator(mode="after")
    def validate_snapshot(self) -> "RosProjectionSnapshot":
        if not self.rows:
            raise ValueError("ROS projection snapshot requires at least one row")
        if any(row.provider != self.provider for row in self.rows):
            raise ValueError("ROS rows must match snapshot provider")
        if (
            self.provider_effective_at is not None
            and self.provider_effective_at > self.captured_at
        ):
            raise ValueError("provider effective time cannot postdate capture")
        return self
