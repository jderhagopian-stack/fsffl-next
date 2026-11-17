"""Offline archive integration using admitted season and franchise identities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from fsffl.state.historical_coverage import HistoricalSeasonIdentity
from fsffl.state.historical_pick_lineage import (
    HistoricalPickLineage, HistoricalSeasonPickInventory, reconcile_historical_pick_lineage,
)
from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
from fsffl.state.historical_season_lineage import HistoricalSeasonLineage
from fsffl.state.historical_supplemental_evidence import HistoricalSupplementalPlayerMovement
from fsffl.state.historical_trade_context_coverage import (
    HistoricalTradeContextCoverage, HistoricalTradeContextRequest, build_historical_trade_context_coverage,
)
from .sleeper_historical_pick_inventory import (
    _ms, normalize_sleeper_historical_pick_inventory, sleeper_linear_draft_allotment,
)


@dataclass(frozen=True)
class HistoricalRookieDraftEvidence:
    season: HistoricalSeasonIdentity
    draft_id: str
    purpose_source_ref: str
    roster_identity_source_ref: str


@dataclass(frozen=True)
class SleeperHistoricalContextIntegration:
    picks: HistoricalPickLineage
    trades: HistoricalTradeContextCoverage


def build_sleeper_historical_context(*, seasons: Mapping[HistoricalSeasonIdentity, Mapping[str, Any]],
        lineage: HistoricalSeasonLineage, rookie_drafts: tuple[HistoricalRookieDraftEvidence, ...],
        source_revision: str, source_observed_at: datetime,
        required_pick_seasons: Mapping[HistoricalSeasonIdentity, tuple[int, ...]] | None = None,
        supplemental_movements: Mapping[HistoricalSeasonIdentity, tuple[HistoricalSupplementalPlayerMovement, ...]] | None = None,
        ) -> SleeperHistoricalContextIntegration:
    """Build each native history once, join pick facts, report completion coverage.

    The caller supplies admitted roster/franchise bindings and identified rookie
    drafts. This adapter does not infer them from equal IDs or a year threshold.
    Source scans alone do not attest complete transfer/use histories.
    """
    sources = {s.season: s for s in lineage.sources}
    histories = {}
    for identity, data in seasons.items():
        source = sources.get(identity)
        if (source is None or source.provider_ref.provider != "sleeper"
                or str((data.get("league") or {}).get("league_id")) != source.provider_ref.external_id
                or int((data.get("league") or {}).get("season", 0)) != identity.season):
            raise ValueError("archived season does not match admitted provider identity")
        bindings = {b.provider_roster_id: b for b in source.roster_bindings}
        raw_rosters = {str(r["roster_id"]): r for r in data.get("rosters", ())}
        if set(bindings) != set(raw_rosters):
            raise ValueError("archived rosters lack an exact admitted crosswalk")
        if any(b.provider_manager_id is not None and str(raw_rosters[r].get("owner_id")) != b.provider_manager_id
               for r, b in bindings.items()):
            raise ValueError("recorded season owner differs from admitted crosswalk")
        provider_identity = identity.model_copy(update={"league_id": source.provider_ref.external_id})
        histories[identity] = reconstruct_sleeper_roster_context(data, source_revision=source_revision,
            season_identity=provider_identity, supplemental_movements=(supplemental_movements or {}).get(identity, ()))
        if source.source_content_sha256 != histories[identity].source_sha256:
            raise ValueError("source fingerprint is absent or differs from admitted archive")
    cohort_rights = {}
    bindings_by_season = {}
    for spec in rookie_drafts:
        if spec.season not in seasons or spec.season.season in cohort_rights:
            raise ValueError("rookie draft scope is unregistered or ambiguous")
        rights, bindings = sleeper_linear_draft_allotment(seasons[spec.season], draft_id=spec.draft_id,
            purpose="rookie", purpose_source_ref=spec.purpose_source_ref,
            roster_identity_source_ref=spec.roster_identity_source_ref)
        source = sources[spec.season]
        canonical = {b.provider_roster_id: b.canonical_team_id for b in source.roster_bindings}
        cohort_rights[spec.season.season] = tuple(replace(r, original_team_id=canonical[r.original_team_id]) for r in rights)
        bindings_by_season[spec.season] = bindings
    if not cohort_rights:
        raise ValueError("explicit draft allotment evidence required")
    inputs = []
    requests = []
    for identity, data in seasons.items():
        source = sources[identity]
        local = {b.canonical_team_id: b.provider_roster_id for b in source.roster_bindings}
        rights = []
        for year, cohort in cohort_rights.items():
            if any(p.original_team_id not in local for p in cohort):
                raise ValueError("draft original franchise lacks a cross-season roster binding")
            rights.extend(replace(p, pick_id=f"{p.draft_season}:{p.round}:{local[p.original_team_id]}",
                                  original_team_id=local[p.original_team_id]) for p in cohort)
        inventory = normalize_sleeper_historical_pick_inventory(data, rights=tuple(rights),
            draft_pick_bindings=bindings_by_season.get(identity, {}),
            declared_draft_seasons=tuple(sorted(cohort_rights)),
            scope_source_ref="admitted-draft-allotments:"+source.settings_receipt.evidence_id,
            source_revision=source_revision, source_observed_at=source_observed_at, allotment_complete=True)
        # Sleeper transaction IDs are supplied here with their provider-global
        # identity scope. The generic join requires this namespace explicitly.
        inputs.append(HistoricalSeasonPickInventory(identity, inventory, "sleeper-transaction"))
        for tx in data.get("transactions", ()):
            if tx.get("type") != "trade" or tx.get("status") != "complete":
                continue
            completed = _ms(tx.get("status_updated"))
            if completed is None:
                raise ValueError("trade completion clock unavailable; no creation-time substitution")
            requests.append(HistoricalTradeContextRequest(identity, str(tx.get("transaction_id") or ""),
                _ms(tx.get("created")), completed, tuple(str(r) for r in (tx.get("roster_ids") or ())),
                source_revision+":"+histories[identity].source_sha256,
                (required_pick_seasons or {}).get(identity)))
    joined = reconcile_historical_pick_lineage(lineage=lineage, seasons=tuple(inputs))
    coverage = build_historical_trade_context_coverage(requests=tuple(requests), lineage=lineage,
        roster_histories=histories, picks=joined)
    return SleeperHistoricalContextIntegration(joined, coverage)
