"""Read-only field coverage at archived trade-completion boundaries.

This does not turn retrospective membership into creation-time model features.
Missing position/active-roster evidence remains missing; no forecasts are run.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .historical_coverage import HistoricalSeasonIdentity
from .historical_pick_lineage import HistoricalPickLineage
from .historical_roster_context import HistoricalRosterContextHistory
from .historical_season_lineage import HistoricalSeasonLineage, build_historical_season_lineage


@dataclass(frozen=True)
class HistoricalTradeContextRequest:
    season: HistoricalSeasonIdentity
    transaction_id: str
    created_at: datetime | None
    completed_at: datetime
    participant_roster_ids: tuple[str, ...]
    source_ref: str
    required_pick_seasons: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        for at in (self.created_at, self.completed_at):
            if at is not None and (at.tzinfo is None or at.utcoffset() is None):
                raise ValueError("trade clocks must be timezone-aware")
        if not self.transaction_id.strip() or not self.source_ref.strip() or self.completed_at is None:
            raise ValueError("trade identity, completion clock and source required")
        if self.created_at is not None and self.created_at > self.completed_at:
            raise ValueError("trade creation is after completion")
        if len(self.participant_roster_ids) < 2 or len(set(self.participant_roster_ids)) != len(self.participant_roster_ids):
            raise ValueError("trade requires distinct participants")


@dataclass(frozen=True)
class HistoricalTradeContextCoverageRow:
    request: HistoricalTradeContextRequest
    roster_snapshot_id: str | None
    pre_completion_snapshot_available: bool
    source_content_verified: bool
    player_membership_context_available: bool
    season_owner_mapping_available: bool
    complete_pick_counts_available: bool
    known_used_pick_count: int
    conditional_outstanding_pick_count: int
    same_time_event_count: int
    issues: tuple[str, ...]
    context_clock: Literal["before_completion_batch"] = "before_completion_batch"
    # The archive contract itself supplies neither historical position evidence
    # nor active slot placement. Native v2 fitting is a separate admission step.
    archived_full_model_input_ready: Literal[False] = False
    eligible_for_pit_decision_grade: Literal[False] = False


@dataclass(frozen=True)
class HistoricalTradeContextCoverage:
    rows: tuple[HistoricalTradeContextCoverageRow, ...]
    input_request_count: int
    duplicate_request_count: int

    def summary(self) -> dict[str, int]:
        return {"trade_rows": len(self.rows), "input_requests": self.input_request_count,
            "duplicate_requests": self.duplicate_request_count,
            "pre_completion_snapshot_rows": sum(r.pre_completion_snapshot_available for r in self.rows),
            "source_content_verified_rows": sum(r.source_content_verified for r in self.rows),
            "membership_context_rows": sum(r.player_membership_context_available for r in self.rows),
            "season_owner_mapping_rows": sum(r.season_owner_mapping_available for r in self.rows),
            "complete_pick_count_rows": sum(r.complete_pick_counts_available for r in self.rows),
            "different_creation_completion_clock_rows": sum(r.request.created_at is not None
                and r.request.created_at != r.request.completed_at for r in self.rows),
            "tied_completion_batch_rows": sum(r.same_time_event_count > 1 for r in self.rows),
            "archived_full_model_input_rows": 0}

    def issue_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(issue for row in self.rows for issue in row.issues).items()))


def build_historical_trade_context_coverage(*, requests: tuple[HistoricalTradeContextRequest, ...],
        lineage: HistoricalSeasonLineage,
        roster_histories: Mapping[HistoricalSeasonIdentity, HistoricalRosterContextHistory],
        picks: HistoricalPickLineage | None = None) -> HistoricalTradeContextCoverage:
    """Index native snapshots once; reuse one pick query per unique cutoff."""
    checked = build_historical_season_lineage(sources=lineage.sources, links=lineage.links)
    sources = {s.season: s for s in checked.sources}
    index = {}
    for season, history in roster_histories.items():
        source = sources.get(season)
        if (source is None or history.league_family_id != season.league_family_id
                or history.provider_league_id != source.provider_ref.external_id or history.season != season.season):
            raise ValueError("roster history does not match registered historical season")
        if source.source_content_sha256 is not None and source.source_content_sha256 != history.source_sha256:
            raise ValueError("registered roster history source fingerprint mismatch")
        for snapshot in history.snapshots:
            if snapshot.boundary != "before_completed_event_batch":
                continue
            for tid in snapshot.transaction_ids:
                key = (season, tid)
                if key in index:
                    raise ValueError("ambiguous archived pre-completion snapshot")
                index[key] = snapshot
    unique = {}
    for request in requests:
        key = (request.season, request.transaction_id)
        old = unique.setdefault(key, request)
        if old != request:
            raise ValueError("conflicting repeated trade-context request")
    rows = []
    last_pick_cutoff = None
    last_pick_snapshot = None
    for request in sorted(unique.values(), key=lambda r: (r.completed_at, r.season.league_id, r.transaction_id)):
        source = sources.get(request.season)
        if source is None:
            raise ValueError("trade request season is unregistered")
        if picks is not None and picks.league_family_id != request.season.league_family_id:
            raise ValueError("cross-family pick context is forbidden")
        if picks is not None and request.season in picks.source_seasons and source not in picks.season_sources:
            raise ValueError("pick context uses a different registered season crosswalk")
        history = roster_histories.get(request.season)
        snapshot = index.get((request.season, request.transaction_id))
        issues = {"position_evidence_unavailable", "historical_slot_placement_unavailable"}
        available = snapshot is not None and snapshot.effective_at == request.completed_at
        source_verified = bool(history is not None and source.source_content_sha256 == history.source_sha256)
        if not source_verified:
            issues.add("historical_source_fingerprint_unverified")
        if not available:
            issues.add("pre_completion_snapshot_missing_or_clock_mismatch")
        rosters = {t.provider_roster_id for t in snapshot.teams} if available else set()
        bindings = {r.provider_roster_id: r for r in source.roster_bindings}
        owners = all(r in bindings and bindings[r].provider_manager_id is not None for r in request.participant_roster_ids)
        membership = bool(available and source_verified and set(request.participant_roster_ids) <= rosters
                          and history.membership_status == "provisionally_consistent" and not snapshot.uncertain_player_ids)
        if not membership:
            issues.add("player_membership_context_unavailable")
        if not owners:
            issues.add("season_owner_mapping_unavailable")
        used = conditional = 0
        complete_picks = False
        if picks is not None and request.season in picks.source_seasons:
            cutoff = request.completed_at
            if cutoff != last_pick_cutoff:
                last_pick_snapshot = picks.inventory.at(cutoff, boundary="before")
                last_pick_cutoff = cutoff
            pick_snapshot = last_pick_snapshot
            used = sum(p.status == "used" for p in pick_snapshot.picks)
            conditional = sum(p.status == "outstanding" for p in pick_snapshot.picks)
            complete_picks = (request.required_pick_seasons is not None and pick_snapshot.complete_for_declared_seasons
                and set(request.required_pick_seasons) <= set(pick_snapshot.declared_draft_seasons))
        if not complete_picks:
            issues.add("complete_pick_counts_unavailable")
        rows.append(HistoricalTradeContextCoverageRow(request, snapshot.snapshot_id if available else None,
            available, source_verified, membership, owners, complete_picks, used, conditional,
            len(snapshot.transaction_ids) if available else 0, tuple(sorted(issues))))
    return HistoricalTradeContextCoverage(tuple(rows), len(requests), len(requests)-len(unique))
