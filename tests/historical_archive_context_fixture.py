"""Explicit retrospective declarations for the one pinned archive fixture.

These are test inputs, not a generic franchise-matching algorithm or independent
at-time identity certification. Production callers need their own admitted maps.
"""
from fsffl.state.historical_coverage import (
    HistoricalSeasonIdentity, HistoricalEvidenceReceipt, HistoricalEvidenceKind,
)
from fsffl.state.historical_season_lineage import (
    HistoricalSeasonSource, HistoricalRosterBinding, HistoricalSeasonLink,
    SeasonLinkProof, build_historical_season_lineage,
)
from fsffl.state.historical_roster_context import _digest
from fsffl.state.models import ProviderRef
from fsffl.providers.sleeper_historical_context import HistoricalRookieDraftEvidence


# This fixture's explicitly declared franchise crosswalk. Equality of raw IDs
# is not a production matching rule; changed source maps must be reviewed.
DECLARED_FRANCHISES = (
    ("1", "fixture-franchise-A"), ("2", "fixture-franchise-B"),
    ("3", "fixture-franchise-C"), ("4", "fixture-franchise-D"),
    ("5", "fixture-franchise-E"), ("6", "fixture-franchise-F"),
    ("7", "fixture-franchise-G"), ("8", "fixture-franchise-H"),
    ("9", "fixture-franchise-I"), ("10", "fixture-franchise-J"),
    ("11", "fixture-franchise-K"), ("12", "fixture-franchise-L"),
)


def declared_archive_context_inputs(records, *, observed, source_revision):
    sources = []
    data_by_season = {}
    for data in sorted(records, key=lambda d: int(d["league"]["season"])):
        league = data["league"]
        identity = HistoricalSeasonIdentity(league_family_id="pinned-retrospective-fixture",
            league_id=str(league["league_id"]), season=int(league["season"]))
        rows = {str(r["roster_id"]): r for r in data["rosters"]}
        if set(rows) != {r for r, _ in DECLARED_FRANCHISES}:
            raise ValueError("declared fixture roster crosswalk changed")
        settings = HistoricalEvidenceReceipt(season=identity, kind=HistoricalEvidenceKind.SETTINGS,
            evidence_id=f"pinned-fixture-settings:{identity.season}", effective_at=observed,
            available_at=observed, availability_basis="verified_archive", source=source_revision)
        sources.append(HistoricalSeasonSource(season=identity,
            provider_ref=ProviderRef(provider="sleeper", external_id=identity.league_id),
            settings_receipt=settings, observed_team_count=len(rows), source_content_sha256=_digest(data),
            raw_position_or_slot_codes=tuple(league["roster_positions"]),
            roster_bindings=tuple(HistoricalRosterBinding(provider_roster_id=raw, canonical_team_id=canonical,
                provider_manager_id=str(rows[raw]["owner_id"]) if rows[raw].get("owner_id") is not None else None)
                for raw, canonical in DECLARED_FRANCHISES)))
        data_by_season[identity] = data
    links = []
    for older, newer in zip(sources, sources[1:]):
        links.append(HistoricalSeasonLink(previous=older.season, current=newer.season,
            previous_provider_ref=older.provider_ref,
            observed_parent_provider_league_id=str(data_by_season[newer.season]["league"]["previous_league_id"]),
            evidence=HistoricalEvidenceReceipt(season=newer.season, kind=HistoricalEvidenceKind.OWNER_IDENTITY,
                evidence_id=f"pinned-fixture-parent:{newer.season.season}", effective_at=observed,
                available_at=observed, availability_basis="verified_archive", source=source_revision),
            proof=SeasonLinkProof.PROVIDER_PREVIOUS_LEAGUE))
    drafts = []
    # Explicit known fixture purpose; 2022 startup remains separate.
    for source in sources:
        if source.season.season in (2023, 2024, 2025, 2026):
            rows = data_by_season[source.season]["drafts"]
            if len(rows) != 1:
                raise ValueError("known fixture rookie-draft scope changed")
            drafts.append(HistoricalRookieDraftEvidence(source.season, str(rows[0]["draft"]["draft_id"]),
                "pinned-fixture:identified-rookie-draft", "pinned-fixture:declared-retrospective-crosswalk"))
    return data_by_season, build_historical_season_lineage(sources=tuple(sources), links=tuple(links)), tuple(drafts)
