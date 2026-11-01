"""Read-only archived Sleeper factual trade replay; never a contemporaneous model input.

This adapter translates provider evidence into a *retrospective factual witness*.
It must not imply archived year-end rosters were publicly available at the trade
cutoff, nor promote a reconstructed snapshot into canonical PIT State authority.
Source bytes stay outside source control; all returned values are versioned.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import field_validator, model_validator

from .models import FrozenModel


class RetrospectiveTransfer(FrozenModel):
    asset_kind: Literal["player", "pick"]
    source_asset_id: str
    before_roster_id: str
    after_roster_id: str


class RetrospectiveFaabMovement(FrozenModel):
    roster_id: str
    used_before: int
    used_after: int
    reconstructed_budget_before: int
    reconstructed_budget_after: int
    evidence_status: Literal["conditional_on_archived_budget_used_and_complete_later_waivers"] = (
        "conditional_on_archived_budget_used_and_complete_later_waivers"
    )


class RetrospectiveRosterOwnership(FrozenModel):
    """Roster membership at a reconstructed trade boundary; slots are not asserted."""

    roster_id: str
    player_ids: tuple[str, ...]
    pick_ids: tuple[str, ...]
    faab_used: int | None
    faab_evidence_status: Literal[
        "conditional_on_archive_waiver_budget_used_and_later_complete_ledger",
        "not_in_selected_trade",
        "invalid_reconstructed_faab",
    ]

    @model_validator(mode="after")
    def validate_roster(self) -> "RetrospectiveRosterOwnership":
        if not self.roster_id.strip():
            raise ValueError("reconstructed roster identity is required")
        if self.faab_evidence_status in {"not_in_selected_trade", "invalid_reconstructed_faab"}:
            if self.faab_used is not None:
                raise ValueError("unavailable FAAB must remain unknown in the scoped snapshot")
        elif self.faab_used is None or self.faab_used < 0:
            raise ValueError("selected participant requires nonnegative conditional FAAB usage")
        if len(self.player_ids) != len(set(self.player_ids)) or len(self.pick_ids) != len(set(self.pick_ids)):
            raise ValueError("reconstructed roster assets must be unique")
        return self


class RetrospectiveSleeperTradeReplay(FrozenModel):
    provider: Literal["sleeper"] = "sleeper"
    source_revision: str
    source_season_sha256: str
    provider_league_id: str
    season: int
    transaction_id: str
    trade_created_at: datetime
    trade_completed_at: datetime
    raw_roster_slots: tuple[str, ...]
    observed_team_count: int
    league_rules_sha256: str
    future_completed_events_reversed: int
    transfers: tuple[RetrospectiveTransfer, ...]
    faab: tuple[RetrospectiveFaabMovement, ...]
    before_ownership: tuple[RetrospectiveRosterOwnership, ...]
    after_ownership: tuple[RetrospectiveRosterOwnership, ...]
    roster_slot_coverage: Literal["unknown_at_trade_cutoff"] = "unknown_at_trade_cutoff"
    ownership_scope: Literal["retrospective_ownership_snapshot_only"] = "retrospective_ownership_snapshot_only"
    pick_ownership_scope: Literal["archived_traded_pick_records_only"] = "archived_traded_pick_records_only"
    issues: tuple[str, ...]
    status: Literal["provisionally_consistent", "blocked"]
    evidence_scope: Literal["retrospective_archived_facts_only"] = "retrospective_archived_facts_only"
    eligible_for_pit_decision_grade: Literal[False] = False
    historical_anchor_independently_verified: Literal[False] = False
    model_version: Literal["retrospective-sleeper-trade-replay-v1"] = "retrospective-sleeper-trade-replay-v1"

    @field_validator("trade_created_at", "trade_completed_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trade time must be timezone-aware")
        return value

    @model_validator(mode="after")
    def valid(self) -> "RetrospectiveSleeperTradeReplay":
        if (self.status == "blocked") != bool(self.issues):
            raise ValueError("replay blocked status must agree with its evidence issues")
        if self.trade_completed_at < self.trade_created_at:
            raise ValueError("trade completion must not precede creation")
        return self


def _digest(record: object) -> str:
    return sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _millis(row: Mapping[str, Any]) -> int:
    # A trade *offer* may exist for days before it completes. Never fall back
    # to offer-creation time for a completed transaction.
    ms = row.get("status_updated")
    if isinstance(ms, bool) or not isinstance(ms, (int, float)) or ms <= 0:
        raise ValueError("completed transaction missing authoritative completion timestamp")
    return int(ms)


def _pick_id(p: Mapping[str, Any]) -> str:
    return f"{int(p['season'])}:{int(p['round'])}:{int(p['roster_id'])}"


def replay_archived_sleeper_trade(
    season_data: Mapping[str, Any], *, transaction_id: str, source_revision: str,
) -> RetrospectiveSleeperTradeReplay:
    """Reconstruct one trade from a retained season-end archive, with blockers.

    A source revision must be immutable and externally verified by its caller.
    No network/SQL, no data fetch, no mutation, no output to logs, and no Value,
    Forecast, Decision, or Simulation calculation. This is intentionally not a
    generic trade grader or a claim to have canonical historical LeagueState.
    """
    if not transaction_id.strip() or not source_revision.strip():
        raise ValueError("trade ID and immutable source revision required")
    league = season_data.get("league")
    if not isinstance(league, Mapping):
        raise ValueError("source missing original historical league record")
    try:
        season = int(league["season"])
        provider_league_id = str(league["league_id"])
        budget = int(league["settings"]["waiver_budget"])
        slots = tuple(str(v) for v in league["roster_positions"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("original league rules, season, or FAAB budget unavailable") from exc
    if not provider_league_id or budget < 0 or not slots:
        raise ValueError("invalid season-specific league configuration")
    rosters = season_data.get("rosters")
    transactions = season_data.get("transactions")
    traded_picks = season_data.get("traded_picks")
    if not isinstance(rosters, list) or not isinstance(transactions, list) or not isinstance(traded_picks, list):
        raise ValueError("complete-shaped archived rosters, trades and pick ledger required")
    if len(rosters) < 2 or len(rosters) != len({str(row.get("roster_id")) for row in rosters}):
        raise ValueError("duplicate or missing season roster identity")
    issues: list[str] = []
    expected_team_count = league.get("total_rosters")
    if expected_team_count is not None and int(expected_team_count) != len(rosters):
        issues.append("season_team_count_mismatch")
    owners: dict[str, set[str]] = {}
    used: dict[str, int] = {}
    for roster in rosters:
        rid = str(roster["roster_id"])
        members = roster.get("players")
        spent = (roster.get("settings") or {}).get("waiver_budget_used")
        if not isinstance(members, list) or spent is None or isinstance(spent, bool):
            raise ValueError("year-end roster players or budget-used evidence missing")
        owners[rid] = {str(player) for player in members}
        if len(members) != len(owners[rid]):
            issues.append("duplicate_player_on_one_roster")
        used[rid] = int(spent)
    all_players = [p for team in owners.values() for p in team]
    if len(all_players) != len(set(all_players)):
        issues.append("end_anchor_duplicate_player_ownership")
    pick_owners: dict[str, str] = {}
    for p in traded_picks:
        k = _pick_id(p)
        if k in pick_owners:
            issues.append("duplicate_or_conflicting_end_anchor_pick_owner")
        pick_owners[k] = str(p["owner_id"])
    all_tx: list[tuple[int, str, Mapping[str, Any]]] = []
    for tx in transactions:
        if tx.get("status") != "complete":
            continue
        at = _millis(tx)
        tid = str(tx.get("transaction_id") or "")
        if not tid:
            raise ValueError("complete historical transaction lacks ID")
        all_tx.append((at, tid, tx))
    matching = [row for row in all_tx if row[1] == transaction_id]
    if len(matching) != 1 or matching[0][2].get("type") != "trade":
        raise ValueError("historical trade must be one unique completed source record")
    completed, _, candidate = matching[0]
    created = candidate.get("created")
    if not isinstance(created, (int, float)) or completed < created:
        raise ValueError("invalid creation/completion order")
    selected_sides = tuple(str(x) for x in (candidate.get("roster_ids") or ()))
    if len(selected_sides) != 2 or len(set(selected_sides)) != 2 or any(x not in owners for x in selected_sides):
        issues.append("unsupported_trade_participants")
    selected_set = set(selected_sides)
    times = Counter(at for at, _, _ in all_tx)
    if times[completed] > 1:
        issues.append("ambiguous_same_timestamp_as_trade")
    reversed_count = 0

    def reverse(tx: Mapping[str, Any], *, target: bool = False) -> None:
        nonlocal issues
        adds = tx.get("adds") or {}
        drops = tx.get("drops") or {}
        if not isinstance(adds, Mapping) or not isinstance(drops, Mapping):
            issues.append("malformed_transaction_player_movements")
            return
        for pid, rid in adds.items():
            rid = str(rid)
            if rid not in owners or str(pid) not in owners[rid]:
                issues.append("missing_post_event_player_ownership")
            else:
                owners[rid].remove(str(pid))
        for pid, rid in drops.items():
            rid = str(rid)
            if rid not in owners or str(pid) in owners[rid]:
                issues.append("conflicting_pre_event_player_ownership")
            else:
                owners[rid].add(str(pid))
        for p in tx.get("draft_picks") or ():
            k = _pick_id(p)
            to, previous = str(p["owner_id"]), str(p["previous_owner_id"])
            if pick_owners.get(k) != to:
                issues.append("unverified_post_event_pick_owner")
            pick_owners[k] = previous
        for item in tx.get("waiver_budget") or ():
            sender, receiver, amount = str(item["sender"]), str(item["receiver"]), int(item["amount"])
            if amount < 1 or sender not in used or receiver not in used:
                issues.append("invalid_faab_transfer")
                continue
            used[sender] -= amount
            used[receiver] += amount
        if tx.get("type") == "waiver":
            bid = (tx.get("settings") or {}).get("waiver_bid")
            if bid is None or not tx.get("roster_ids"):
                issues.append("unverified_waiver_bid_or_roster")
            else:
                owner = str(tx["roster_ids"][0])
                if owner not in used or int(bid) < 0:
                    issues.append("invalid_waiver_claim")
                else:
                    used[owner] -= int(bid)

    def ownership_snapshot() -> tuple[RetrospectiveRosterOwnership, ...]:
        picks_by_roster: dict[str, list[str]] = {roster_id: [] for roster_id in owners}
        for pick_id, roster_id in pick_owners.items():
            if roster_id in picks_by_roster:
                picks_by_roster[roster_id].append(pick_id)
        return tuple(
            RetrospectiveRosterOwnership(
                roster_id=roster_id,
                player_ids=tuple(sorted(owners[roster_id])),
                pick_ids=tuple(sorted(picks_by_roster[roster_id])),
                faab_used=(used[roster_id] if roster_id in selected_set and used[roster_id] >= 0 else None),
                faab_evidence_status=(
                    "not_in_selected_trade" if roster_id not in selected_set else
                    "invalid_reconstructed_faab" if used[roster_id] < 0 else
                    "conditional_on_archive_waiver_budget_used_and_later_complete_ledger"
                ),
            )
            for roster_id in sorted(owners)
        )

    later = sorted((row for row in all_tx if row[0] > completed), key=lambda r: (r[0], r[1]), reverse=True)
    # Identical timestamps occur in batched waivers. Independent assets can be
    # reversed in either order; overlapping player/pick identities cannot.
    # FAAB sums commute but are still conditional on complete source evidence.
    affected_at: dict[int, set[tuple[str, str]]] = defaultdict(set)
    for at, _, tx in later:
        touched = {("player", str(p)) for p in (tx.get("adds") or {})}
        touched.update(("player", str(p)) for p in (tx.get("drops") or {}))
        touched.update(("pick", _pick_id(p)) for p in (tx.get("draft_picks") or ()))
        if touched & affected_at[at]:
            issues.append("ambiguous_later_event_order")
        affected_at[at].update(touched)
        reverse(tx)
        reversed_count += 1
    raw_adds = candidate.get("adds") or {}
    raw_drops = candidate.get("drops") or {}
    picks = candidate.get("draft_picks") or []
    budget_transfers = candidate.get("waiver_budget") or []
    transfers: list[RetrospectiveTransfer] = []
    for pid, receiving in raw_adds.items():
        sending = raw_drops.get(pid)
        if sending is None or str(sending) == str(receiving) or str(sending) not in selected_set or str(receiving) not in selected_set:
            issues.append("trade_player_sender_or_receiver_unverified")
            continue
        p_owners = tuple(r for r, players in owners.items() if str(pid) in players)
        if p_owners != (str(receiving),):
            issues.append("trade_post_player_owner_mismatch")
        transfers.append(RetrospectiveTransfer(asset_kind="player", source_asset_id=str(pid),
            before_roster_id=str(sending), after_roster_id=str(receiving)))
    if set(map(str, raw_drops)) != set(map(str, raw_adds)):
        issues.append("trade_drop_add_asymmetry")
    for p in picks:
        k = _pick_id(p)
        sending, receiving = str(p["previous_owner_id"]), str(p["owner_id"])
        if sending not in selected_set or receiving not in selected_set or sending == receiving:
            issues.append("trade_pick_participants_mismatch")
        if pick_owners.get(k) != receiving:
            issues.append("trade_post_pick_owner_mismatch")
        transfers.append(RetrospectiveTransfer(asset_kind="pick", source_asset_id=k,
            before_roster_id=sending, after_roster_id=receiving))
    after_ownership = ownership_snapshot()
    faab_after = {r: used[r] for r in selected_sides if r in used}
    reverse(candidate, target=True)
    before_ownership = ownership_snapshot()
    for transfer in transfers:
        if transfer.asset_kind == "player":
            seen = tuple(r for r, players in owners.items() if transfer.source_asset_id in players)
            if seen != (transfer.before_roster_id,):
                issues.append("trade_pre_player_owner_mismatch")
        else:
            if pick_owners.get(transfer.source_asset_id) != transfer.before_roster_id:
                issues.append("trade_pre_pick_owner_mismatch")
    if any(int(x.get("amount", 0)) <= 0 for x in budget_transfers):
        issues.append("trade_faab_amount_invalid")
    if any(str(x.get("sender")) not in selected_set or str(x.get("receiver")) not in selected_set
           for x in budget_transfers):
        issues.append("trade_faab_participants_mismatch")
    if any(x.get("sender") == x.get("receiver") for x in budget_transfers):
        issues.append("trade_faab_self_transfer")
    faab = tuple(RetrospectiveFaabMovement(roster_id=r, used_before=used[r], used_after=faab_after[r],
        reconstructed_budget_before=budget-used[r], reconstructed_budget_after=budget-faab_after[r])
        for r in sorted(faab_after))
    if any(x.used_before < 0 or x.used_after < 0 or x.reconstructed_budget_before < 0
           or x.reconstructed_budget_after < 0 for x in faab):
        issues.append("reconstructed_faab_balance_out_of_bounds")
    if not transfers and not budget_transfers:
        issues.append("no_reconstructible_trade_assets")
    return RetrospectiveSleeperTradeReplay(
        source_revision=source_revision, source_season_sha256=_digest(season_data),
        provider_league_id=provider_league_id, season=season, transaction_id=transaction_id,
        trade_created_at=datetime.fromtimestamp(created/1000, tz=UTC),
        trade_completed_at=datetime.fromtimestamp(completed/1000, tz=UTC),
        raw_roster_slots=slots, observed_team_count=len(rosters),
        league_rules_sha256=_digest({"settings": league.get("settings"),
                                    "scoring": league.get("scoring_settings"), "slots": slots}),
        future_completed_events_reversed=reversed_count,
        transfers=tuple(sorted(transfers, key=lambda x: (x.asset_kind, x.source_asset_id))),
        faab=faab, before_ownership=before_ownership, after_ownership=after_ownership,
        issues=tuple(sorted(set(issues))),
        status="blocked" if issues else "provisionally_consistent",
    )
