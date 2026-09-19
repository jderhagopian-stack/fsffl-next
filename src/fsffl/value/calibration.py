from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


class CalibrationEvidenceKind(StrEnum):
    MARKET_VALUE = "market_value"
    COMPLETED_TRANSACTION = "completed_transaction"
    REALIZED_OUTCOME = "realized_outcome"
    FORECAST = "forecast"
    PICK_OUTCOME = "pick_outcome"
    LEAGUE_RULE = "league_rule"
    OTHER = "other"


class DataRightsClass(StrEnum):
    PUBLIC_REDISTRIBUTABLE = "public_redistributable"
    RESEARCH_ONLY = "research_only"
    PRIVATE_RETAINED = "private_retained"
    RUNTIME_ONLY = "runtime_only"
    UNKNOWN = "unknown"


class CalibrationObservation(FrozenModel):
    """One point-in-time evidence row used by NEXT-3 empirical fitting.

    Raw third-party datasets do not need to live in git. This contract carries
    the provenance and rights metadata needed to reproduce a calibration from a
    runtime artifact, private retained store, or redistributable public source.
    """

    source_id: str
    evidence_kind: CalibrationEvidenceKind
    observed_at: datetime
    asset_id: str | None = None
    league_context_id: str | None = None
    format_context_id: str | None = None
    metric: str
    value: float
    rights_class: DataRightsClass
    source_version: str | None = None
    provenance_uri: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identifiers(self) -> "CalibrationObservation":
        required = (self.source_id, self.metric)
        if any(not value.strip() for value in required):
            raise ValueError("calibration evidence identifiers cannot be blank")
        for optional in (
            self.asset_id,
            self.league_context_id,
            self.format_context_id,
            self.source_version,
            self.provenance_uri,
        ):
            if optional is not None and not optional.strip():
                raise ValueError("optional calibration identifiers cannot be blank")
        return self


class CalibrationPanel(FrozenModel):
    """Immutable, point-in-time panel consumable by multiple NEXT-3 fitters."""

    observations: tuple[CalibrationObservation, ...]
    as_of: datetime
    panel_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_panel(self) -> "CalibrationPanel":
        if not self.panel_version.strip():
            raise ValueError("panel_version cannot be blank")
        future = [row for row in self.observations if row.observed_at > self.as_of]
        if future:
            raise ValueError("calibration panel contains evidence observed after as_of")
        return self

    def by_kind(self, kind: CalibrationEvidenceKind) -> tuple[CalibrationObservation, ...]:
        return tuple(row for row in self.observations if row.evidence_kind == kind)

    def by_league(self, league_context_id: str) -> tuple[CalibrationObservation, ...]:
        if not league_context_id.strip():
            raise ValueError("league_context_id cannot be blank")
        return tuple(row for row in self.observations if row.league_context_id == league_context_id)

    def sources(self) -> tuple[str, ...]:
        return tuple(sorted({row.source_id for row in self.observations}))


class CalibrationFitMetadata(FrozenModel):
    """Common provenance recorded by every fitted NEXT-3 calibration."""

    model_version: str
    fitted_at: datetime
    evidence_through: datetime
    sample_size: Annotated[int, Field(ge=1)]
    panel_version: str
    source_ids: tuple[str, ...]
    training_window_start: datetime | None = None
    holdout_window_start: datetime | None = None

    @field_validator("fitted_at", "evidence_through", "training_window_start", "holdout_window_start")
    @classmethod
    def require_timezone_if_present(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("calibration timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_metadata(self) -> "CalibrationFitMetadata":
        if not self.model_version.strip() or not self.panel_version.strip():
            raise ValueError("calibration fit identifiers cannot be blank")
        if not self.source_ids or any(not source.strip() for source in self.source_ids):
            raise ValueError("calibration fit must record nonblank evidence sources")
        if self.evidence_through > self.fitted_at:
            raise ValueError("evidence_through cannot be after fitted_at")
        if (
            self.training_window_start is not None
            and self.training_window_start > self.evidence_through
        ):
            raise ValueError("training window cannot start after evidence_through")
        if (
            self.holdout_window_start is not None
            and self.training_window_start is not None
            and self.holdout_window_start <= self.training_window_start
        ):
            raise ValueError("holdout window must begin after training window start")
        return self
