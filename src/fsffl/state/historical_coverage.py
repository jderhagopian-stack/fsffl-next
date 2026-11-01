"""Provider-neutral, read-only historical evidence admission for an exact cutoff.

This is an inventory/guard, NOT a historical State builder, trade grader or
licensing decision.  It cannot promote a result to Forecast/Value/Decision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .models import FrozenModel, LeagueState


class HistoricalEvidenceKind(StrEnum):
    SETTINGS = "settings"
    ROSTERS = "rosters"
    TRANSACTIONS = "transactions"
    DRAFT = "draft"
    MATCHUPS = "matchups"
    PLAYER_STATUS = "player_status"
    FORECAST = "forecast"
    MARKET = "market"
    OWNER_IDENTITY = "owner_identity"


class HistoricalSeasonIdentity(FrozenModel):
    """A single provider-neutral season, even if its provider league ID changes.

    A league family may include many seasons; neither team names nor platform
    roster IDs establish permanent franchise/manager identity across seasons.
    """

    league_family_id: str
    league_id: str
    season: Annotated[int, Field(ge=1900)]

    @model_validator(mode="after")
    def verify_names(self) -> "HistoricalSeasonIdentity":
        if not self.league_family_id.strip() or not self.league_id.strip():
            raise ValueError("historical league family and season identities are required")
        return self


class HistoricalEvidenceReceipt(FrozenModel):
    """A verifiable evidence pointer; never the evidence or an inferred value.

    ``available_at`` is when the *source evidence* was knowable, not when
    FSFFL fetched it.  Unknown source availability cannot pass a PIT gate.
    Hindsight facts may be listed for retrospective analysis but are not
    quietly promoted as contemporaneous Forecast, Value or Decision evidence.
    """

    season: HistoricalSeasonIdentity
    kind: HistoricalEvidenceKind
    evidence_id: str
    effective_at: datetime
    available_at: datetime | None = None
    availability_basis: Literal["provider_timestamp", "verified_archive"] | None = None
    source: str
    source_version: str | None = None

    @field_validator("effective_at", "available_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("historical evidence times must carry a timezone")
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def verify_proof(self) -> "HistoricalEvidenceReceipt":
        if not self.evidence_id.strip() or not self.source.strip():
            raise ValueError("evidence ID and provenance source are mandatory")
        if (self.available_at is None) != (self.availability_basis is None):
            raise ValueError("historical evidence available_at requires a proof basis")
        return self


class HistoricalEvidenceFinding(FrozenModel):
    kind: HistoricalEvidenceKind
    status: Literal["available_at_cutoff", "unverified", "only_future_evidence", "missing"]
    eligible_evidence_ids: tuple[str, ...] = ()
    excluded_evidence_ids: tuple[str, ...] = ()


class HistoricalCutoffInventory(FrozenModel):
    """Read-only historical coverage summary; never a claim that a grade exists."""

    season: HistoricalSeasonIdentity
    cutoff: datetime
    state_id: str | None
    state_as_of: datetime | None
    team_count_declared: int | None
    team_count_observed: int | None
    roster_size: int | None
    taxi_size: int | None
    ir_size: int | None
    rookie_draft_rounds: int | None
    lineup_slots: tuple[tuple[str, int], ...]
    scoring_rules: tuple[tuple[str, float], ...]
    rule_fingerprint: str | None
    findings: tuple[HistoricalEvidenceFinding, ...]
    blockers: tuple[str, ...]
    scope: Literal["evidence_inventory_only"] = "evidence_inventory_only"

    @property
    def requested_evidence_present(self) -> bool:
        """Only inventory coverage; never authorization for Decision grading."""
        return not self.blockers


def _rules_signature(state: LeagueState) -> str:
    rules = state.league.rules.model_dump(mode="json")
    encoded = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def inventory_historical_cutoff(
    *,
    season: HistoricalSeasonIdentity,
    cutoff: datetime,
    snapshots: tuple[LeagueState, ...],
    receipts: tuple[HistoricalEvidenceReceipt, ...],
    required_kinds: tuple[HistoricalEvidenceKind, ...],
) -> HistoricalCutoffInventory:
    """Validate season-specific State and PIT evidence without inventing coverage.

    The caller supplies already-authorized, bounded references to a *single*
    league season.  Never fetch providers or mutate State. Snapshot selection
    cannot let a later season, post-cutoff transaction or future rule change
    bleed into a historical decision. Different seasons in a league family may
    have different team counts, rosters, lineup positions, scoring and ID.
    """

    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("historical cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(UTC)
    if len(set(required_kinds)) != len(required_kinds):
        raise ValueError("required historical evidence kinds must be unique")
    for state in snapshots:
        if state.league.league_id != season.league_id or state.league.season != season.season:
            raise ValueError("snapshot belongs to a different league or season")
    for receipt in receipts:
        if receipt.season != season:
            raise ValueError("evidence belongs to a different league family, league, or season")
    identifiers = [r.evidence_id for r in receipts]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate evidence IDs are ambiguous; record versioned identities")

    candidates = [state for state in snapshots if state.as_of <= cutoff]
    selected = max(candidates, key=lambda x: (x.as_of, x.state_id)) if candidates else None
    blockers: list[str] = []
    if selected is None:
        blockers.append("no_same_season_state_at_cutoff")
    elif len(selected.teams) != selected.league.rules.team_count:
        blockers.append("declared_team_count_differs_from_observed_state")

    findings: list[HistoricalEvidenceFinding] = []
    for kind in sorted(required_kinds, key=lambda x: x.value):
        rows = [r for r in receipts if r.kind == kind]
        eligible = sorted(r.evidence_id for r in rows
                          if r.effective_at <= cutoff and r.available_at is not None
                          and r.available_at <= cutoff)
        excluded = sorted(r.evidence_id for r in rows if r.evidence_id not in eligible)
        if eligible:
            status = "available_at_cutoff"
        elif any(r.available_at is None and r.effective_at <= cutoff for r in rows):
            status = "unverified"
        elif rows:
            status = "only_future_evidence"
        else:
            status = "missing"
        if not eligible:
            blockers.append(f"{kind.value}:{status}")
        findings.append(HistoricalEvidenceFinding(kind=kind, status=status,
                                                 eligible_evidence_ids=tuple(eligible),
                                                 excluded_evidence_ids=tuple(excluded)))

    rules = selected.league.rules if selected is not None else None
    return HistoricalCutoffInventory(
        season=season, cutoff=cutoff,
        state_id=selected.state_id if selected is not None else None,
        state_as_of=selected.as_of if selected is not None else None,
        team_count_declared=rules.team_count if rules else None,
        team_count_observed=len(selected.teams) if selected is not None else None,
        roster_size=rules.roster_size if rules else None,
        taxi_size=rules.taxi_size if rules else None,
        ir_size=rules.ir_size if rules else None,
        rookie_draft_rounds=rules.rookie_draft_rounds if rules else None,
        lineup_slots=tuple((row.slot.value, row.count) for row in rules.lineup) if rules else (),
        scoring_rules=tuple((row.stat, row.points) for row in rules.scoring) if rules else (),
        rule_fingerprint=_rules_signature(selected) if selected is not None else None,
        findings=tuple(findings), blockers=tuple(blockers),
    )
