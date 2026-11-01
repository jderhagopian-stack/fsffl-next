"""Separately sourced retrospective facts and their fail-closed reconciliation.

These contracts preserve provenance and date precision. They do not mutate a
provider archive, establish contemporaneous availability, or authorize PIT grades.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import field_validator, model_validator

from .historical_coverage import HistoricalSeasonIdentity
from .models import FrozenModel
from .retrospective_season_audit import RetrospectiveSeasonAudit, RetrospectiveSeasonIssue


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
    provider: str
    source_player_id: str
    player_id: str
    provider_roster_id: str
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
        for value in (self.provider, self.source_player_id, self.player_id, self.provider_roster_id):
            if not value.strip():
                raise ValueError("supplemental movement identities are required")
        if self.date_precision == SupplementalDatePrecision.DATE_ONLY and self.effective_at is not None:
            raise ValueError("date-only evidence cannot claim an exact event time")
        if self.date_precision == SupplementalDatePrecision.EXACT_TIMESTAMP:
            if self.effective_at is None or self.effective_at.date() != self.effective_date:
                raise ValueError("exact timestamp evidence must match its stated event date")
        return self


class SupplementalFindingStatus(StrEnum):
    SUPPORTED_RETROSPECTIVELY = "supported_retrospectively"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class SupplementalOwnershipFinding(FrozenModel):
    issue: RetrospectiveSeasonIssue
    status: SupplementalFindingStatus
    evidence_ids: tuple[str, ...] = ()
    detail: str


class HistoricalSupplementalReconciliation(FrozenModel):
    """Supplement-aware view which retains the original provider audit unchanged."""

    provider_audit: RetrospectiveSeasonAudit
    findings: tuple[SupplementalOwnershipFinding, ...]
    scope: Literal["retrospective_supplemental_reconciliation"] = "retrospective_supplemental_reconciliation"
    eligible_for_pit_decision_grade: Literal[False] = False

    @property
    def supported_gap_count(self) -> int:
        return sum(item.status == SupplementalFindingStatus.SUPPORTED_RETROSPECTIVELY for item in self.findings)


def reconcile_supplemental_player_movements(
    provider_audit: RetrospectiveSeasonAudit,
    movements: tuple[HistoricalSupplementalPlayerMovement, ...],
) -> HistoricalSupplementalReconciliation:
    """Assess whether separately sourced drops support missing source-ledger exits.

    The source audit is embedded verbatim and remains incomplete. Only a
    provider/season/player/roster-matched drop strictly after the source event
    can support a missing ownership departure. Day-only same-day evidence is
    ambiguous because it cannot establish event order.
    """
    for movement in movements:
        if movement.season.league_id != provider_audit.provider_league_id:
            raise ValueError("supplemental movement belongs to another provider league")
        if movement.season.season != provider_audit.season or movement.provider != provider_audit.provider:
            raise ValueError("supplemental movement belongs to another provider season")

    findings: list[SupplementalOwnershipFinding] = []
    for issue in provider_audit.issues:
        if issue.code != "post_event_player_missing":
            continue
        if issue.asset_id is None or issue.provider_roster_id is None or issue.completed_at is None:
            findings.append(SupplementalOwnershipFinding(
                issue=issue, status=SupplementalFindingStatus.UNRESOLVED,
                detail="provider finding lacks player, roster, or completion-time identity",
            ))
            continue
        matching = tuple(
            movement for movement in movements
            if movement.provider == provider_audit.provider
            and movement.source_player_id == issue.asset_id
            and movement.provider_roster_id == issue.provider_roster_id
            and movement.kind == SupplementalPlayerMovementKind.DROPPED_TO_WAIVERS
        )
        ordered: list[HistoricalSupplementalPlayerMovement] = []
        same_day_ambiguous: list[HistoricalSupplementalPlayerMovement] = []
        for movement in matching:
            if movement.date_precision == SupplementalDatePrecision.EXACT_TIMESTAMP:
                if movement.effective_at > issue.completed_at:
                    ordered.append(movement)
                elif movement.effective_at == issue.completed_at:
                    same_day_ambiguous.append(movement)
            elif movement.effective_date > issue.completed_at.date():
                ordered.append(movement)
            elif movement.effective_date == issue.completed_at.date():
                same_day_ambiguous.append(movement)

        if same_day_ambiguous:
            findings.append(SupplementalOwnershipFinding(
                issue=issue, status=SupplementalFindingStatus.AMBIGUOUS,
                evidence_ids=tuple(sorted({m.receipt.evidence_id for m in same_day_ambiguous})),
                detail="date-only movement does not establish order relative to the provider event",
            ))
        elif not ordered:
            findings.append(SupplementalOwnershipFinding(
                issue=issue, status=SupplementalFindingStatus.UNRESOLVED,
                detail="no matching later drop has been supplied",
            ))
        elif len({(m.effective_date, m.effective_at) for m in ordered}) > 1:
            findings.append(SupplementalOwnershipFinding(
                issue=issue, status=SupplementalFindingStatus.AMBIGUOUS,
                evidence_ids=tuple(sorted({m.receipt.evidence_id for m in ordered})),
                detail="multiple distinct later drop events cannot be reconciled without the intervening history",
            ))
        else:
            findings.append(SupplementalOwnershipFinding(
                issue=issue, status=SupplementalFindingStatus.SUPPORTED_RETROSPECTIVELY,
                evidence_ids=tuple(sorted({m.receipt.evidence_id for m in ordered})),
                detail="a separately sourced later drop supports the missing ownership departure; provider audit remains unchanged",
            ))

    return HistoricalSupplementalReconciliation(provider_audit=provider_audit, findings=tuple(findings))
