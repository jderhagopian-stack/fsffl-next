"""Verified, provider-neutral historical season lineage (no inferred manager identity).

A provider's yearly league IDs, roster IDs and team names are NOT stable identities.
This reference index does not fetch sources, migrate facts, or infer prior seasons.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from .historical_coverage import (
    HistoricalEvidenceKind,
    HistoricalEvidenceReceipt,
    HistoricalSeasonIdentity,
)
from .models import FrozenModel, ProviderRef, RosterSlot


class SeasonLinkProof(StrEnum):
    PROVIDER_PREVIOUS_LEAGUE = "provider_previous_league"
    VERIFIED_ARCHIVE = "verified_archive"


class HistoricalRosterBinding(FrozenModel):
    """A *season-scoped* roster identity, not a permanent owner/franchise claim."""

    provider_roster_id: str
    canonical_team_id: str
    provider_manager_id: str | None = None

    @model_validator(mode="after")
    def validate_identifiers(self) -> "HistoricalRosterBinding":
        if not self.provider_roster_id.strip() or not self.canonical_team_id.strip():
            raise ValueError("historical roster/team IDs are required")
        if self.provider_manager_id is not None and not self.provider_manager_id.strip():
            raise ValueError("blank manager ID is not evidence of identity")
        return self


class HistoricalSeasonSource(FrozenModel):
    """A signed-off original provider season record and declared roster mapping.

    Provider settings can be captured retrospectively; source timestamp and
    original date of availability must never be confused. The source record
    identifies the real historical configuration, not an evaluation permission.
    """

    season: HistoricalSeasonIdentity
    provider_ref: ProviderRef
    settings_receipt: HistoricalEvidenceReceipt
    observed_team_count: Annotated[int, Field(ge=0)] | None = None
    roster_bindings: tuple[HistoricalRosterBinding, ...] = ()
    raw_position_or_slot_codes: tuple[str, ...] = ()
    source_version: str = "historical-season-source-v1"
    source_content_sha256: str | None = None  # optional inventory; required by future trusted-ingest gate

    @model_validator(mode="after")
    def validate_source(self) -> "HistoricalSeasonSource":
        if not self.provider_ref.provider.strip() or not self.provider_ref.external_id.strip():
            raise ValueError("source provider and season ID are mandatory")
        if self.settings_receipt.season != self.season:
            raise ValueError("settings receipt belongs to a different season or league family")
        if self.settings_receipt.kind != HistoricalEvidenceKind.SETTINGS:
            raise ValueError("season source requires settings evidence, not an unrelated receipt")
        roster_ids = [row.provider_roster_id for row in self.roster_bindings]
        team_ids = [row.canonical_team_id for row in self.roster_bindings]
        if len(roster_ids) != len(set(roster_ids)) or len(team_ids) != len(set(team_ids)):
            raise ValueError("roster and canonical team identities must be unique within one season")
        if self.observed_team_count is not None and len(self.roster_bindings) > self.observed_team_count:
            raise ValueError("more roster bindings than observed teams")
        if any(not code.strip() for code in self.raw_position_or_slot_codes):
            raise ValueError("raw format codes cannot be blank")
        if not self.source_version.strip():
            raise ValueError("source version must be explicit")
        if self.source_content_sha256 is not None and (
            len(self.source_content_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.source_content_sha256)
        ):
            raise ValueError("source fingerprint must be a lowercase SHA-256 hex digest")
        return self

    @property
    def unknown_slot_codes(self) -> tuple[str, ...]:
        supported = {slot.value for slot in RosterSlot}
        return tuple(sorted({code for code in self.raw_position_or_slot_codes if code not in supported}))

    @property
    def roster_mapping_status(self) -> str:
        if self.observed_team_count is None:
            return "unknown_team_count"
        if len(self.roster_bindings) != self.observed_team_count:
            return "partial_roster_crosswalk"
        if self.unknown_slot_codes:
            return "unsupported_position_or_slot"
        return "complete_mapping_only"  # no implied player/rules/scoring support


class HistoricalSeasonLink(FrozenModel):
    """Only an explicit provider/archival parent relation is a family linkage."""

    previous: HistoricalSeasonIdentity
    current: HistoricalSeasonIdentity
    previous_provider_ref: ProviderRef
    observed_parent_provider_league_id: str
    evidence: HistoricalEvidenceReceipt
    proof: SeasonLinkProof

    @model_validator(mode="after")
    def validate_link(self) -> "HistoricalSeasonLink":
        if self.previous.league_family_id != self.current.league_family_id:
            raise ValueError("cross-family historical links are not permitted")
        if self.current.season <= self.previous.season:
            raise ValueError("historical parent season must precede child season")
        if self.evidence.season != self.current or self.evidence.kind != HistoricalEvidenceKind.OWNER_IDENTITY:
            raise ValueError("link requires season-bound identity evidence")
        if not self.observed_parent_provider_league_id.strip():
            raise ValueError("observed parent ID required")
        if self.observed_parent_provider_league_id != self.previous_provider_ref.external_id:
            raise ValueError("provider parent ID does not match previous season source")
        if self.evidence.available_at is None or self.evidence.availability_basis is None:
            raise ValueError("verified link evidence must have documented source availability")
        return self


class HistoricalSeasonLineage(FrozenModel):
    sources: tuple[HistoricalSeasonSource, ...]
    links: tuple[HistoricalSeasonLink, ...]
    root_or_unlinked_seasons: tuple[HistoricalSeasonIdentity, ...]
    scope: str = "source_lineage_only"

    @property
    def seasons(self) -> tuple[HistoricalSeasonIdentity, ...]:
        return tuple(row.season for row in self.sources)


def build_historical_season_lineage(
    *,
    sources: tuple[HistoricalSeasonSource, ...],
    links: tuple[HistoricalSeasonLink, ...],
) -> HistoricalSeasonLineage:
    """Fail closed on conflicting provider lineage; never join by team name.

    Evidence IDs, source availability, or same user appearance do not themselves
    establish continuity. A year may be intentionally disconnected or absent.
    """
    by_season: dict[HistoricalSeasonIdentity, HistoricalSeasonSource] = {}
    by_provider: dict[tuple[str, str], HistoricalSeasonIdentity] = {}
    per_family_year: dict[tuple[str, int], HistoricalSeasonIdentity] = {}
    for source in sources:
        identity = source.season
        provider_key = (source.provider_ref.provider, source.provider_ref.external_id)
        family_year = (identity.league_family_id, identity.season)
        if identity in by_season or provider_key in by_provider or family_year in per_family_year:
            raise ValueError("duplicate/ambiguous historical season or provider identity")
        by_season[identity] = source
        by_provider[provider_key] = identity
        per_family_year[family_year] = identity

    parents: dict[HistoricalSeasonIdentity, HistoricalSeasonIdentity] = {}
    children: dict[HistoricalSeasonIdentity, HistoricalSeasonIdentity] = {}
    for link in links:
        older = by_season.get(link.previous)
        newer = by_season.get(link.current)
        if older is None or newer is None:
            raise ValueError("historical lineage references an unknown season")
        if older.provider_ref != link.previous_provider_ref:
            raise ValueError("parent provider identity mismatch")
        if older.provider_ref.provider != newer.provider_ref.provider:
            raise ValueError("cross-provider continuity needs a separate governed identity bridge")
        if link.current in parents or link.previous in children:
            raise ValueError("ambiguous fork or multiple parent season")
        parents[link.current] = link.previous
        children[link.previous] = link.current

    return HistoricalSeasonLineage(
        sources=tuple(sorted(sources, key=lambda s: (s.season.league_family_id, s.season.season))),
        links=tuple(sorted(links, key=lambda l: (l.current.league_family_id, l.current.season))),
        root_or_unlinked_seasons=tuple(sorted(
            (s.season for s in sources if s.season not in parents),
            key=lambda s: (s.league_family_id, s.season),
        )),
    )
