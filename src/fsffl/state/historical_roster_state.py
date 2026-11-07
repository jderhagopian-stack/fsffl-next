"""Fail-closed materialization of a roster-context snapshot as canonical State.

The retrospective Sleeper replay intentionally knows membership only. This
adapter requires independently supplied identities, roster placements, rules,
FAAB balances, and a complete pick universe before it emits ``LeagueState``.
It never guesses those facts and never authorizes a historical Decision grade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import model_validator

from .historical_coverage import (
    HistoricalEvidenceKind,
    HistoricalEvidenceReceipt,
    HistoricalSeasonIdentity,
)
from .historical_materializer import HistoricalRosterPlacement
from .historical_roster_context import (
    HistoricalRosterContextHistory,
    HistoricalRosterContextSnapshot,
)
from .historical_supplemental_evidence import HistoricalSupplementalEvidenceReceipt
from .historical_roster_replay import HistoricalRosterReplay, RosterMembershipSnapshot
from .models import (
    DraftPick,
    FrozenModel,
    League,
    LeagueState,
    PickOwnership,
    Player,
    PlayerState,
    ProviderRef,
    RosterEntry,
    Team,
    TeamState,
)


class HistoricalStateMaterializationStatus(StrEnum):
    MATERIALIZED = "materialized_retrospective_roster_state"
    BLOCKED = "blocked_missing_or_conflicting_evidence"


class HistoricalRosterTeamEvidence(FrozenModel):
    """Canonical team identity and an evidenced balance for one source roster."""

    provider_roster_id: str
    team: Team
    faab_balance: int
    identity_receipt: HistoricalEvidenceReceipt
    faab_receipt: HistoricalEvidenceReceipt


class HistoricalRosterPlayerEvidence(FrozenModel):
    """Canonical player metadata and status aligned to the snapshot cutoff."""

    provider_player_id: str
    player: Player
    player_state: PlayerState
    identity_receipt: HistoricalEvidenceReceipt


class HistoricalDraftPickOwner(FrozenModel):
    """One provider pick identity mapped to a canonical pick and its owner."""

    provider_pick_id: str
    pick: DraftPick
    owner_team_id: str


class HistoricalRosterStateMaterialization(FrozenModel):
    status: HistoricalStateMaterializationStatus
    state: LeagueState | None = None
    blockers: tuple[str, ...] = ()
    history_id: str
    snapshot_id: str
    evidence_receipts: tuple[HistoricalEvidenceReceipt, ...] = ()
    supplemental_evidence_receipts: tuple[HistoricalSupplementalEvidenceReceipt, ...] = ()
    source_available_at_cutoff: bool = False
    eligible_for_pit_decision_grade: bool = False
    scope: str = "retrospective_roster_state_only"

    @model_validator(mode="after")
    def validate_result(self) -> "HistoricalRosterStateMaterialization":
        if self.status == HistoricalStateMaterializationStatus.MATERIALIZED:
            if self.state is None or self.blockers:
                raise ValueError("materialized historical State requires a State and no blockers")
        elif self.state is not None or not self.blockers:
            raise ValueError("blocked historical State requires blockers and no State")
        if self.eligible_for_pit_decision_grade:
            raise ValueError("retrospective roster materialization cannot authorize a Decision grade")
        return self


def _receipt_blocker(
    receipt: HistoricalEvidenceReceipt | None,
    *,
    season: HistoricalSeasonIdentity,
    kind: HistoricalEvidenceKind,
    cutoff: datetime,
    label: str,
) -> str | None:
    if receipt is None:
        return f"missing_{label}_receipt"
    if receipt.season != season:
        return f"{label}_receipt_season_mismatch"
    if receipt.kind != kind:
        return f"{label}_receipt_kind_mismatch"
    if receipt.effective_at > cutoff:
        return f"{label}_evidence_after_cutoff"
    return None



@dataclass(frozen=True)
class _SourceRoster:
    provider_roster_id: str
    player_ids: tuple[str, ...]
    traded_pick_ids: tuple[str, ...]


@dataclass(frozen=True)
class _SourceSnapshot:
    history_id: str
    snapshot_id: str
    effective_at: datetime | None
    boundary: str
    teams: tuple[_SourceRoster, ...]
    uncertain_player_ids: tuple[str, ...]
    supplemental_evidence_ids: tuple[str, ...]
    pick_universe_complete: bool | None
    belongs_to_history: bool


@dataclass(frozen=True)
class _SourceHistory:
    history_id: str
    provider: str
    provider_league_id: str
    season: int
    league_family_id: str | None
    membership_complete: bool
    snapshot_ids: frozenset[str]
    pick_issues: tuple[str, ...] = ()
    budget_usage_issues: tuple[str, ...] = ()
    budget_usage_complete: bool | None = None


def _source_views(
    history: HistoricalRosterContextHistory | HistoricalRosterReplay,
    snapshot: HistoricalRosterContextSnapshot | RosterMembershipSnapshot,
) -> tuple[_SourceHistory, _SourceSnapshot]:
    """Normalize adapter-specific and provider-neutral snapshots for one builder."""
    if isinstance(history, HistoricalRosterReplay) and isinstance(snapshot, RosterMembershipSnapshot):
        pick_owner = dict(snapshot.pick_owners)
        source_teams = tuple(
            _SourceRoster(
                provider_roster_id=team_id,
                player_ids=players,
                traded_pick_ids=tuple(sorted(
                    pick_id for pick_id, owner_id in pick_owner.items() if owner_id == team_id
                )),
            )
            for team_id, players in snapshot.teams
        )
        source_history = _SourceHistory(
            history_id=history.history_id,
            provider=history.provider,
            provider_league_id=history.league_id,
            season=history.season,
            league_family_id=None,
            membership_complete=not history.membership_issues,
            snapshot_ids=frozenset(row.snapshot_id for row in history.snapshots),
            pick_issues=history.pick_issues,
            budget_usage_issues=history.budget_usage_issues,
            budget_usage_complete=snapshot.budget_usage_complete,
        )
        source_snapshot = _SourceSnapshot(
            history_id=snapshot.history_id,
            snapshot_id=snapshot.snapshot_id,
            effective_at=snapshot.effective_at,
            boundary=snapshot.boundary,
            teams=source_teams,
            uncertain_player_ids=(),
            supplemental_evidence_ids=(),
            pick_universe_complete=snapshot.pick_universe_complete,
            belongs_to_history=snapshot in history.snapshots,
        )
        return source_history, source_snapshot

    if isinstance(history, HistoricalRosterContextHistory) and isinstance(snapshot, HistoricalRosterContextSnapshot):
        source_teams = tuple(
            _SourceRoster(
                provider_roster_id=row.provider_roster_id,
                player_ids=row.player_ids,
                traded_pick_ids=row.traded_pick_ids,
            )
            for row in snapshot.teams
        )
        source_history = _SourceHistory(
            history_id=history.history_id,
            provider=history.provider,
            provider_league_id=history.provider_league_id,
            season=history.season,
            league_family_id=history.league_family_id,
            membership_complete=history.membership_status == "provisionally_consistent",
            snapshot_ids=frozenset(row.snapshot_id for row in history.snapshots),
        )
        source_snapshot = _SourceSnapshot(
            history_id=snapshot.history_id,
            snapshot_id=snapshot.snapshot_id,
            effective_at=snapshot.effective_at,
            boundary=snapshot.boundary,
            teams=source_teams,
            uncertain_player_ids=snapshot.uncertain_player_ids,
            supplemental_evidence_ids=snapshot.supplemental_evidence_ids,
            pick_universe_complete=None,
            belongs_to_history=snapshot in history.snapshots,
        )
        return source_history, source_snapshot
    raise TypeError("history and snapshot must be a matching provider adapter or normalized replay pair")


def materialize_historical_roster_state(
    *,
    season: HistoricalSeasonIdentity,
    history: HistoricalRosterContextHistory | HistoricalRosterReplay,
    snapshot: HistoricalRosterContextSnapshot | RosterMembershipSnapshot,
    league: League,
    teams: tuple[HistoricalRosterTeamEvidence, ...],
    players: tuple[HistoricalRosterPlayerEvidence, ...],
    roster_placements: tuple[HistoricalRosterPlacement, ...],
    draft_picks: tuple[HistoricalDraftPickOwner, ...],
    settings_receipt: HistoricalEvidenceReceipt | None,
    roster_receipt: HistoricalEvidenceReceipt | None,
    player_universe_receipt: HistoricalEvidenceReceipt | None,
    pick_universe_receipt: HistoricalEvidenceReceipt | None,
    pick_universe_complete: bool = False,
    supplemental_evidence_receipts: tuple[HistoricalSupplementalEvidenceReceipt, ...] = (),
) -> HistoricalRosterStateMaterialization:
    """Build State from either an adapter context or normalized replay plus receipts.

    Historical membership is accepted from the provider-neutral replay, while
    placements, canonical identities, FAAB balances, settings, and the complete
    pick universe still require separate evidence. This never authorizes a
    historical Decision grade.
    """

    source_history, source_snapshot = _source_views(history, snapshot)
    cutoff = source_snapshot.effective_at
    blockers: set[str] = set()
    evidence_receipts = tuple(
        receipt
        for receipt in (
            settings_receipt,
            roster_receipt,
            player_universe_receipt,
            pick_universe_receipt,
            *(row.identity_receipt for row in teams),
            *(row.faab_receipt for row in teams),
            *(row.identity_receipt for row in players),
            *(row.receipt for row in roster_placements),
        )
        if receipt is not None
    )
    if len({receipt.evidence_id for receipt in evidence_receipts}) != len(evidence_receipts):
        blockers.add("duplicate_evidence_receipt_identity")
    if not pick_universe_complete:
        blockers.add("complete_pick_universe_not_asserted")
    if source_snapshot.pick_universe_complete is False:
        blockers.add("replay_pick_universe_incomplete")
    if source_history.pick_issues:
        blockers.add("replay_pick_history_incomplete")
    expected_supplemental_ids = set(source_snapshot.supplemental_evidence_ids)
    supplied_supplemental_ids = {
        receipt.evidence_id for receipt in supplemental_evidence_receipts
    }
    if expected_supplemental_ids != supplied_supplemental_ids:
        blockers.add("supplemental_evidence_receipt_coverage_mismatch")
    if cutoff is None:
        blockers.add("snapshot_has_no_effective_timestamp")
    if source_snapshot.boundary == "archive_end_anchor":
        blockers.add("archive_end_anchor_is_not_an_event_cutoff")
    if source_snapshot.uncertain_player_ids:
        blockers.add("snapshot_contains_uncertain_player_membership")
    if not source_history.membership_complete:
        blockers.add("source_membership_history_incomplete")
    if (
        source_history.history_id != source_snapshot.history_id
        or source_snapshot.snapshot_id not in source_history.snapshot_ids
        or not source_snapshot.belongs_to_history
    ):
        blockers.add("snapshot_does_not_belong_to_history")
    if (
        source_history.provider_league_id != season.league_id
        or source_history.season != season.season
        or league.league_id != season.league_id
        or league.season != season.season
    ):
        blockers.add("league_season_identity_mismatch")
    if source_history.league_family_id is not None and source_history.league_family_id != season.league_family_id:
        blockers.add("league_family_identity_mismatch")
    if len(teams) != len(source_snapshot.teams) or len({row.provider_roster_id for row in teams}) != len(teams):
        blockers.add("team_identity_coverage_mismatch")
    if len(players) != len({row.provider_player_id for row in players}):
        blockers.add("duplicate_player_identity")

    if cutoff is not None:
        required_receipts = (
            (settings_receipt, HistoricalEvidenceKind.SETTINGS, "settings"),
            (roster_receipt, HistoricalEvidenceKind.ROSTERS, "roster"),
            (player_universe_receipt, HistoricalEvidenceKind.PLAYER_STATUS, "player_universe"),
            (pick_universe_receipt, HistoricalEvidenceKind.DRAFT, "pick_universe"),
        )
        for receipt, kind, label in required_receipts:
            problem = _receipt_blocker(
                receipt, season=season, kind=kind, cutoff=cutoff, label=label,
            )
            if problem:
                blockers.add(problem)
        if roster_receipt is not None and roster_receipt.effective_at != cutoff:
            blockers.add("roster_receipt_must_match_snapshot_cutoff")

    team_by_roster = {row.provider_roster_id: row for row in teams}
    team_ids = {row.team.team_id for row in teams}
    provider_roster_by_team = {row.team.team_id: row.provider_roster_id for row in teams}
    team_provider_refs = [
        ref.external_id
        for row in teams
        for ref in row.team.provider_refs
        if ref.provider == source_history.provider
    ]
    if (
        len(team_provider_refs) != len(set(team_provider_refs))
        or set(team_provider_refs) != {row.provider_roster_id for row in source_snapshot.teams}
    ):
        blockers.add("team_provider_identity_mapping_is_not_one_to_one")
    if len(team_ids) != len(teams):
        blockers.add("duplicate_canonical_team_identity")
    if league.rules.team_count != len(source_snapshot.teams):
        blockers.add("league_rule_team_count_mismatch")
    if len({row.team.team_id for row in teams}) != league.rules.team_count:
        blockers.add("canonical_team_count_mismatch")
    for row in teams:
        if row.provider_roster_id not in {team.provider_roster_id for team in source_snapshot.teams}:
            blockers.add("team_identity_not_in_snapshot")
        if row.team.league_id != league.league_id:
            blockers.add("team_league_identity_mismatch")
        if ProviderRef(provider=source_history.provider, external_id=row.provider_roster_id) not in row.team.provider_refs:
            blockers.add("team_provider_identity_not_asserted")
        if row.faab_balance < 0:
            blockers.add("invalid_faab_balance")
        if cutoff is not None:
            for receipt, kind, label in (
                (row.identity_receipt, HistoricalEvidenceKind.OWNER_IDENTITY, "team_identity"),
                (row.faab_receipt, HistoricalEvidenceKind.FAAB, "faab_balance"),
            ):
                problem = _receipt_blocker(
                    receipt, season=season, kind=kind, cutoff=cutoff, label=label,
                )
                if problem:
                    blockers.add(problem)

    expected_membership = {
        (team.provider_roster_id, player_id)
        for team in source_snapshot.teams
        for player_id in team.player_ids
    }
    source_players = {row.provider_player_id: row for row in players}
    canonical_player_ids = {row.player.player_id for row in players}
    player_provider_refs = [
        ref.external_id
        for row in players
        for ref in row.player.provider_refs
        if ref.provider == source_history.provider
    ]
    if (
        len(player_provider_refs) != len(set(player_provider_refs))
        or set(player_provider_refs) != {player for _roster, player in expected_membership}
    ):
        blockers.add("player_provider_identity_mapping_is_not_one_to_one")
    if len(canonical_player_ids) != len(players):
        blockers.add("duplicate_canonical_player_identity")
    if set(source_players) != {player for _roster, player in expected_membership}:
        blockers.add("player_identity_coverage_mismatch")
    for row in players:
        if ProviderRef(provider=source_history.provider, external_id=row.provider_player_id) not in row.player.provider_refs:
            blockers.add("player_provider_identity_not_asserted")
        if row.player_state.player_id != row.player.player_id:
            blockers.add("player_state_identity_mismatch")
        if cutoff is not None and row.player_state.as_of != cutoff:
            blockers.add("player_state_cutoff_mismatch")
        if cutoff is not None:
            problem = _receipt_blocker(
                row.identity_receipt, season=season, kind=HistoricalEvidenceKind.PLAYER_STATUS,
                cutoff=cutoff, label="player_identity",
            )
            if problem:
                blockers.add(problem)

    placement_keys = [(row.team_id, row.player_id) for row in roster_placements]
    canonical_placement_keys: set[tuple[str, str]] = set()
    for provider_roster, provider_player in expected_membership:
        team = team_by_roster.get(provider_roster)
        player = source_players.get(provider_player)
        if team is not None and player is not None:
            canonical_placement_keys.add((team.team.team_id, player.player.player_id))
    if len(placement_keys) != len(set(placement_keys)):
        blockers.add("duplicate_roster_placement_evidence")
    if set(placement_keys) != canonical_placement_keys:
        blockers.add("roster_slot_coverage_incomplete_or_extra")
    for row in roster_placements:
        if row.team_id not in team_ids or row.player_id not in canonical_player_ids:
            blockers.add("roster_placement_identity_mismatch")
        if cutoff is not None:
            problem = _receipt_blocker(
                row.receipt, season=season, kind=HistoricalEvidenceKind.ROSTERS,
                cutoff=cutoff, label="roster_placement",
            )
            if problem:
                blockers.add(problem)
            elif row.receipt.effective_at != cutoff:
                blockers.add("roster_placement_receipt_must_match_snapshot_cutoff")

    pick_by_source_id = {row.provider_pick_id: row for row in draft_picks}
    if len(pick_by_source_id) != len(draft_picks):
        blockers.add("duplicate_provider_pick_identity")
    pick_ids = [row.pick.pick_id for row in draft_picks]
    if len(pick_ids) != len(set(pick_ids)):
        blockers.add("duplicate_canonical_pick_identity")
    for row in draft_picks:
        if row.pick.league_id != league.league_id or row.pick.original_team_id not in team_ids:
            blockers.add("draft_pick_identity_mismatch")
        if row.owner_team_id not in team_ids:
            blockers.add("draft_pick_owner_identity_mismatch")
    source_pick_owners = {
        pick_id: team.provider_roster_id
        for team in source_snapshot.teams
        for pick_id in team.traded_pick_ids
    }
    for provider_pick_id, provider_roster_id in source_pick_owners.items():
        mapped = pick_by_source_id.get(provider_pick_id)
        expected_team = team_by_roster.get(provider_roster_id)
        if mapped is None or expected_team is None or mapped.owner_team_id != expected_team.team.team_id:
            blockers.add("snapshot_pick_ownership_not_represented")

    if blockers or cutoff is None:
        return HistoricalRosterStateMaterialization(
            status=HistoricalStateMaterializationStatus.BLOCKED,
            blockers=tuple(sorted(blockers or {"snapshot_has_no_effective_timestamp"})),
            history_id=source_history.history_id,
            snapshot_id=source_snapshot.snapshot_id,
            evidence_receipts=evidence_receipts,
            supplemental_evidence_receipts=supplemental_evidence_receipts,
        )

    placements_by_team: dict[str, list[RosterEntry]] = {team_id: [] for team_id in team_ids}
    for placement in roster_placements:
        placements_by_team[placement.team_id].append(
            RosterEntry(player_id=placement.player_id, slot=placement.slot)
        )
    team_states = tuple(
        TeamState(
            team_id=team_id,
            roster=tuple(sorted(placements_by_team[team_id], key=lambda entry: entry.player_id)),
            faab_balance=team_by_roster[provider_roster_by_team[team_id]].faab_balance,
        )
        for team_id in sorted(team_ids)
    )
    available = all(
        receipt.available_at is not None
        and receipt.available_at <= cutoff
        for receipt in evidence_receipts
    ) and all(
        receipt.source_available_at is not None
        and receipt.source_available_at <= cutoff
        for receipt in supplemental_evidence_receipts
    )
    state = LeagueState(
        league=league,
        as_of=cutoff,
        teams=tuple(sorted((row.team for row in teams), key=lambda row: row.team_id)),
        team_states=team_states,
        players=tuple(sorted((row.player for row in players), key=lambda row: row.player_id)),
        player_states=tuple(sorted((row.player_state for row in players), key=lambda row: row.player_id)),
        draft_picks=tuple(sorted((row.pick for row in draft_picks), key=lambda row: row.pick_id)),
        pick_ownership=tuple(sorted(
            (PickOwnership(pick_id=row.pick.pick_id, owner_team_id=row.owner_team_id) for row in draft_picks),
            key=lambda row: row.pick_id,
        )),
        provenance=tuple(
            row.player_state.provenance for row in players
        ),
    )
    return HistoricalRosterStateMaterialization(
        status=HistoricalStateMaterializationStatus.MATERIALIZED,
        state=state,
        history_id=source_history.history_id,
        snapshot_id=source_snapshot.snapshot_id,
        evidence_receipts=evidence_receipts,
        supplemental_evidence_receipts=supplemental_evidence_receipts,
        source_available_at_cutoff=available,
    )
