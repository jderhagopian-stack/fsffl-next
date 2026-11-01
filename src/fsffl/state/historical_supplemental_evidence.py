"""Separately sourced retrospective facts, kept outside provider transaction history.

These contracts preserve provenance and date precision. They do not mutate a
provider archive, establish contemporaneous availability, or authorize PIT grades.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .historical_coverage import HistoricalSeasonIdentity
from .models import FrozenModel


class SupplementalEvidenceSource(StrEnum):
    USER_SUPPLIED_SCREENSHOT = "user_supplied_screenshot"
    USER_SUPPLIED_DOCUMENT = "user_supplied_document"
    INDEPENDENT_ARCHIVE = "independent_archive"


class SupplementalDatePrecision(StrEnum):
    DATE_ONLY = "date_only"
    EXACT_TIMESTAMP = "exact_timestamp"


class SupplementalPlayerMovementKind(StrEnum):
    ADDED_TO_ROSTER = "added_to_roster"
    DROPPED_TO_WAIVERS = "dropped_to_waivers"


class HistoricalSupplementalEvidenceReceipt(FrozenModel):
    """Immutable pointer to external evidence; raw/private bytes stay elsewhere."""

    evidence_id: str
    source: SupplementalEvidenceSource
    source_fingerprint_sha256: str
    received_at: datetime
    source_available_at: datetime | None = None
    availability_basis: Literal["provider_timestamp", "verified_archive"] | None = None
    source_reference: str

    @field_validator("received_at", "source_available_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("supplemental evidence timestamps must be timezone-aware")
        return value

    @field_validator("source_fingerprint_sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("evidence fingerprint must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_receipt(self) -> "HistoricalSupplementalEvidenceReceipt":
        if not self.evidence_id.strip() or not self.source_reference.strip():
            raise ValueError("supplemental evidence identity and reference are required")
        if (self.source_available_at is None) != (self.availability_basis is None):
            raise ValueError("source availability time requires an explicit proof basis")
        return self


class HistoricalSupplementalPlayerMovement(FrozenModel):
    """A supplemental roster movement, never a normalized trade or PIT event."""

    season: HistoricalSeasonIdentity
    player_id: str
    team_id: str
    kind: SupplementalPlayerMovementKind
    effective_date: date
    date_precision: SupplementalDatePrecision
    effective_at: datetime | None = None
    receipt: HistoricalSupplementalEvidenceReceipt
    scope: Literal["supplemental_retrospective_fact"] = "supplemental_retrospective_fact"
    eligible_for_pit_decision_grade: Literal[False] = False

    @field_validator("effective_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("supplemental event time must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_precision_and_identity(self) -> "HistoricalSupplementalPlayerMovement":
        if not self.player_id.strip() or not self.team_id.strip():
            raise ValueError("supplemental player and team identities are required")
        if self.date_precision == SupplementalDatePrecision.DATE_ONLY and self.effective_at is not None:
            raise ValueError("date-only evidence cannot claim an exact event time")
        if self.date_precision == SupplementalDatePrecision.EXACT_TIMESTAMP:
            if self.effective_at is None or self.effective_at.date() != self.effective_date:
                raise ValueError("exact timestamp evidence must match its stated event date")
        return self
