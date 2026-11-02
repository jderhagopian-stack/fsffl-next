"""Apply a fully evidenced bilateral trade to an immutable canonical State.

This is a factual State transformation only. It does not estimate trade value,
prove that the supplied pre-trade State is complete, or authorize a historical
Decision grade. The caller supplies the exact pre-trade State and source
receipts; missing roster placement evidence blocks the transformation.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import model_validator

from .historical_coverage import (
    HistoricalEvidenceKind,
    HistoricalEvidenceReceipt,
    HistoricalSeasonIdentity,
)
from .historical_trade import HistoricalTradeRecord
from .models import (
    FaabAsset,
    FrozenModel,
    LeagueState,
    PickAsset,
    PickOwnership,
    PlayerAsset,
    RosterEntry,
    RosterSlot,
)


class MaterializationStatus(StrEnum):
    MATERIALIZED = "materialized_factual_state"
    BLOCKED = "blocked_missing_or_conflicting_evidence"


class HistoricalRosterPlacement(FrozenModel):
    """Evidence for the receiving roster slot of one traded player."""

    player_id: str
    team_id: str
    slot: RosterSlot
    receipt: HistoricalEvidenceReceipt

    @model_validator(mode="after")
    def validate_receipt(self) -> "HistoricalRosterPlacement":
        if not self.player_id.strip() or not self.team_id.strip():
            raise ValueError("roster placement requires player and team identities")
        if self.receipt.kind != HistoricalEvidenceKind.ROSTERS:
            raise ValueError("roster placement requires roster evidence")
        return self


class HistoricalTransactionWindow(FrozenModel):
    """Source-backed completeness claim for a single transaction interval."""

    season: HistoricalSeasonIdentity
    start_exclusive: datetime
    end_inclusive: datetime
    transaction_ids: tuple[str, ...]
    receipt: HistoricalEvidenceReceipt

    @model_validator(mode="after")
    def validate_window(self) -> "HistoricalTransactionWindow":
        # Keep these runtime checks local so the public contract rejects naive
        # timestamps even if constructed from untyped provider input.
        if (
            self.start_exclusive.tzinfo is None
            or self.start_exclusive.utcoffset() is None
            or self.end_inclusive.tzinfo is None
            or self.end_inclusive.utcoffset() is None
        ):
            raise ValueError("transaction window boundaries must be timezone-aware")
        if self.start_exclusive >= self.end_inclusive:
            raise ValueError("transaction window must have positive duration")
        if self.season != self.receipt.season or self.receipt.kind != HistoricalEvidenceKind.TRANSACTIONS:
            raise ValueError("transaction window receipt must match the historical season")
        if self.receipt.effective_at != self.end_inclusive:
            raise ValueError("transaction window receipt must match its end boundary")
        if len(set(self.transaction_ids)) != len(self.transaction_ids):
            raise ValueError("transaction window IDs must be unique")
        if any(not value.strip() for value in self.transaction_ids):
            raise ValueError("transaction window IDs cannot be blank")
        return self


class HistoricalTradeMaterialization(FrozenModel):
    status: MaterializationStatus
    state: LeagueState | None = None
    blockers: tuple[str, ...] = ()
    applied_transaction_id: str | None = None
    scope: str = "bilateral_trade_factual_state_only"
    source_available_at_cutoff: bool = False
    eligible_for_pit_decision_grade: bool = False

    @model_validator(mode="after")
    def validate_result(self) -> "HistoricalTradeMaterialization":
        if self.status == MaterializationStatus.MATERIALIZED:
            if self.state is None or self.blockers or self.applied_transaction_id is None:
                raise ValueError("materialized result requires a State and no blockers")
        elif self.state is not None or not self.blockers:
            raise ValueError("blocked result requires blockers and cannot contain a State")
        if self.eligible_for_pit_decision_grade:
            raise ValueError("factual trade materialization cannot authorize a Decision grade")
        return self


def materialize_post_trade_state(
    *,
    season: HistoricalSeasonIdentity,
    before: LeagueState,
    before_roster_receipt: HistoricalEvidenceReceipt,
    trade: HistoricalTradeRecord,
    transaction_window: HistoricalTransactionWindow,
    roster_placements: tuple[HistoricalRosterPlacement, ...] = (),
    faab_receipt: HistoricalEvidenceReceipt | None = None,
    draft_receipt: HistoricalEvidenceReceipt | None = None,
) -> HistoricalTradeMaterialization:
    """Create the post-trade State by applying one exact bilateral trade.

    The `before` State must be the caller-verified state immediately before this
    event window. Receipts may be retrospective: in that case a factual State
    can still be produced, but this function never upgrades it to PIT Decision
    evidence. All player receiving slots must be independently evidenced.
    """

    if before.as_of.tzinfo is None or trade.completed_at.tzinfo is None:
        raise ValueError("State and transaction timestamps must be timezone-aware")
    if before.league.league_id != season.league_id or before.league.season != season.season:
        raise ValueError("pre-trade State belongs to a different league season")
    if trade.league_id != season.league_id:
        raise ValueError("trade belongs to a different league season")
    if before.as_of >= trade.completed_at:
        raise ValueError("pre-trade State must precede the transaction cutoff")
    if transaction_window.season != season:
        raise ValueError("transaction window must match the historical season")
    if transaction_window.start_exclusive != before.as_of:
        raise ValueError("transaction window must start at the supplied pre-trade State")
    if transaction_window.end_inclusive != trade.completed_at:
        raise ValueError("transaction window must end at the trade timestamp")
    if transaction_window.transaction_ids != (trade.transaction_id,):
        blockers = ["transaction_window_contains_unapplied_events"]
        return HistoricalTradeMaterialization(
            status=MaterializationStatus.BLOCKED,
            blockers=tuple(blockers),
        )
    if before_roster_receipt.season != season or before_roster_receipt.kind != HistoricalEvidenceKind.ROSTERS:
        raise ValueError("pre-trade roster receipt must match the historical season")
    if before_roster_receipt.effective_at != before.as_of:
        raise ValueError("pre-trade roster receipt must match the supplied State timestamp")

    blockers: list[str] = []
    if len(trade.legs) != 2:
        blockers.append("unsupported_trade_party_count")

    placements = {item.player_id: item for item in roster_placements}
    if len(placements) != len(roster_placements):
        blockers.append("duplicate_roster_placement_evidence")

    teams = {row.team_id: row for row in before.team_states}
    players = {entry.player_id: state.team_id for state in before.team_states for entry in state.roster}
    picks = {row.pick_id: row.owner_team_id for row in before.pick_ownership}
    pick_ids = {row.pick_id for row in before.draft_picks}
    teams_with_faab_change: set[str] = set()
    traded_player_ids: set[str] = set()
    traded_pick_ids: set[str] = set()
    seen_assets: set[tuple[str, str]] = set()
    faab_delta = {team_id: 0 for team_id in teams}

    if trade.provenance.effective_at != trade.completed_at:
        blockers.append("trade_provenance_timestamp_mismatch")

    if len(trade.legs) == 2:
        left, right = trade.legs
        if left.team_id == right.team_id or left.team_id not in teams or right.team_id not in teams:
            blockers.append("trade_team_not_in_pretrade_state")
        else:
            outgoing = ((left, right), (right, left))
            for sender, receiver in outgoing:
                for asset in sender.sends:
                    if isinstance(asset, PlayerAsset):
                        if ("player", asset.player_id) in seen_assets:
                            blockers.append(f"duplicate_trade_asset:player:{asset.player_id}")
                        seen_assets.add(("player", asset.player_id))
                        traded_player_ids.add(asset.player_id)
                        if players.get(asset.player_id) != sender.team_id:
                            blockers.append(f"player_not_owned_before_trade:{asset.player_id}")
                        placement = placements.get(asset.player_id)
                        if placement is None:
                            blockers.append(f"missing_receiving_roster_slot:{asset.player_id}")
                        elif placement.team_id != receiver.team_id:
                            blockers.append(f"roster_slot_team_mismatch:{asset.player_id}")
                        elif (
                            placement.receipt.season != season
                            or placement.receipt.effective_at != trade.completed_at
                        ):
                            blockers.append(f"roster_slot_receipt_mismatch:{asset.player_id}")
                    elif isinstance(asset, PickAsset):
                        if ("pick", asset.pick_id) in seen_assets:
                            blockers.append(f"duplicate_trade_asset:pick:{asset.pick_id}")
                        seen_assets.add(("pick", asset.pick_id))
                        traded_pick_ids.add(asset.pick_id)
                        if asset.pick_id not in pick_ids or picks.get(asset.pick_id) != sender.team_id:
                            blockers.append(f"pick_not_owned_before_trade:{asset.pick_id}")
                    elif isinstance(asset, FaabAsset):
                        teams_with_faab_change.update((sender.team_id, receiver.team_id))
                        faab_delta[sender.team_id] -= asset.amount
                        faab_delta[receiver.team_id] += asset.amount

    for team_id in teams_with_faab_change:
        if teams[team_id].faab_balance + faab_delta[team_id] < 0:
            blockers.append(f"insufficient_pretrade_faab:{team_id}")

    if set(placements) - traded_player_ids:
        blockers.append("roster_placement_for_untraded_player")
    if traded_pick_ids and (
        draft_receipt is None
        or draft_receipt.season != season
        or draft_receipt.kind != HistoricalEvidenceKind.DRAFT
        or draft_receipt.effective_at != before.as_of
    ):
        blockers.append("missing_pretrade_pick_universe_evidence")
    if teams_with_faab_change and (
        faab_receipt is None
        or faab_receipt.season != season
        or faab_receipt.kind != HistoricalEvidenceKind.FAAB
        or faab_receipt.effective_at != before.as_of
    ):
        blockers.append("missing_pretrade_faab_balance_evidence")

    if blockers:
        return HistoricalTradeMaterialization(
            status=MaterializationStatus.BLOCKED,
            blockers=tuple(sorted(set(blockers))),
        )

    left, right = trade.legs
    roster_by_team = {team_id: list(state.roster) for team_id, state in teams.items()}
    pick_owner_by_id = dict(picks)
    for sender, receiver in ((left, right), (right, left)):
        for asset in sender.sends:
            if isinstance(asset, PlayerAsset):
                roster_by_team[sender.team_id] = [
                    entry for entry in roster_by_team[sender.team_id]
                    if entry.player_id != asset.player_id
                ]
                placement = placements[asset.player_id]
                roster_by_team[receiver.team_id].append(
                    RosterEntry(player_id=asset.player_id, slot=placement.slot)
                )
            elif isinstance(asset, PickAsset):
                pick_owner_by_id[asset.pick_id] = receiver.team_id

    team_states = tuple(
        teams[team_id].model_copy(update={
            "roster": tuple(sorted(roster_by_team[team_id], key=lambda row: row.player_id)),
            "faab_balance": teams[team_id].faab_balance + faab_delta[team_id],
        })
        for team_id in sorted(teams)
    )
    pick_ownership = tuple(
        PickOwnership(pick_id=pick_id, owner_team_id=owner)
        for pick_id, owner in sorted(pick_owner_by_id.items())
    )
    post_trade = LeagueState.model_validate(before.model_copy(update={
        "as_of": trade.completed_at,
        "team_states": team_states,
        "pick_ownership": pick_ownership,
        "provenance": (*before.provenance, trade.provenance),
    }).model_dump())

    receipts = (before_roster_receipt, transaction_window.receipt, *(item.receipt for item in roster_placements))
    if faab_receipt is not None:
        receipts += (faab_receipt,)
    if draft_receipt is not None:
        receipts += (draft_receipt,)
    # Retrospective archives generally fail this condition. That does not stop
    # factual reconstruction; PIT Decision eligibility is always owned elsewhere.
    source_available_at_cutoff = all(
        receipt.available_at is not None and receipt.available_at <= trade.completed_at
        for receipt in receipts
    )

    return HistoricalTradeMaterialization(
        status=MaterializationStatus.MATERIALIZED,
        state=post_trade,
        applied_transaction_id=trade.transaction_id,
        source_available_at_cutoff=source_available_at_cutoff,
        eligible_for_pit_decision_grade=False,
    )
