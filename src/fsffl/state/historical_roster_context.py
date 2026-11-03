"""Reusable retrospective roster context reconstructed from a season archive.

This is a provider adapter, not canonical point-in-time State. It starts at a
retained season-end roster anchor and reverses completed events to expose
membership at event-time boundaries. League rules are fingerprinted from each
season's source record; no FSFFL team-count, scoring, or roster-slot constants
are assumed.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import field_validator, model_validator

from .models import FrozenModel


class HistoricalRosterContextTeam(FrozenModel):
    provider_roster_id: str
    player_ids: tuple[str, ...]
    # Only picks present in the archived traded-pick ledger are enumerable.
    traded_pick_ids: tuple[str, ...]
    # This is usage reconstructed from an end-of-season total and later events,
    # not a certified point-in-time balance.
    waiver_budget_used: int | None
    waiver_budget_evidence: Literal["conditional_complete_later_ledger", "unknown"]

    @model_validator(mode="after")
    def valid(self) -> "HistoricalRosterContextTeam":
        if not self.provider_roster_id.strip():
            raise ValueError("provider roster ID is required")
        if len(self.player_ids) != len(set(self.player_ids)):
            raise ValueError("player membership must be unique per roster")
        if len(self.traded_pick_ids) != len(set(self.traded_pick_ids)):
            raise ValueError("traded-pick membership must be unique per roster")
        if (self.waiver_budget_evidence == "unknown") != (self.waiver_budget_used is None):
            raise ValueError("waiver usage value and evidence status disagree")
        if self.waiver_budget_used is not None and self.waiver_budget_used < 0:
            raise ValueError("reconstructed waiver usage cannot be negative")
        return self


class HistoricalRosterContextSnapshot(FrozenModel):
    effective_at: datetime | None
    boundary: Literal["before_completed_event_batch", "after_completed_event_batch", "archive_end_anchor"]
    transaction_ids: tuple[str, ...]
    event_types: tuple[str, ...]
    teams: tuple[HistoricalRosterContextTeam, ...]
    roster_slot_coverage: Literal["unknown"] = "unknown"

    @field_validator("effective_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("historical snapshot timestamp must be timezone-aware")
        return value


class HistoricalRosterContextHistory(FrozenModel):
    provider: str = "sleeper"
    provider_league_id: str
    season: int
    source_revision: str
    source_sha256: str
    league_rules_sha256: str
    raw_roster_slots: tuple[str, ...]
    observed_team_count: int
    completed_event_count: int
    snapshots: tuple[HistoricalRosterContextSnapshot, ...]
    issues: tuple[str, ...]
    membership_issues: tuple[str, ...]
    pick_issues: tuple[str, ...]
    faab_issues: tuple[str, ...]
    membership_status: Literal["provisionally_consistent", "incomplete_source_history"]
    scope: Literal["retrospective_roster_membership_context"] = "retrospective_roster_membership_context"
    pick_scope: Literal["archived_traded_pick_records_only"] = "archived_traded_pick_records_only"
    faab_scope: Literal["conditional_archive_waiver_usage"] = "conditional_archive_waiver_usage"
    eligible_for_pit_decision_grade: Literal[False] = False
    model_version: Literal["historical-roster-context-v1"] = "historical-roster-context-v1"

    @model_validator(mode="after")
    def consistent(self) -> "HistoricalRosterContextHistory":
        if not self.provider.strip():
            raise ValueError("historical context source provider is required")
        scoped_issues = set(self.membership_issues) | set(self.pick_issues) | set(self.faab_issues)
        if scoped_issues != set(self.issues):
            raise ValueError("every history issue must be assigned to an evidence scope")
        if bool(self.membership_issues) != (self.membership_status == "incomplete_source_history"):
            raise ValueError("membership status must reflect membership issues")
        if self.observed_team_count < 2:
            raise ValueError("at least two season rosters are required")
        return self


def _digest(record: object) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode()).hexdigest()


def _pick_id(row: Mapping[str, Any]) -> str:
    return f"{int(row['season'])}:{int(row['round'])}:{int(row['roster_id'])}"


def _timestamp(row: Mapping[str, Any]) -> int | None:
    value = row.get("status_updated")
    if type(value) not in (int, float) or value <= 0:
        return None
    return int(value)


def reconstruct_sleeper_roster_context(
    season_data: Mapping[str, Any], *, source_revision: str,
) -> HistoricalRosterContextHistory:
    """Build roster-membership snapshots for every timestamped completed event.

    Events sharing a completion timestamp are treated as one boundary batch;
    their individual ordering is never invented. Invalid or absent event clocks
    are reported and omitted from reversal, so affected history is visibly
    incomplete. Unknown roster placement does not block membership snapshots.
    """
    if not source_revision.strip():
        raise ValueError("immutable source revision is required")
    league = season_data.get("league")
    rosters = season_data.get("rosters")
    transactions = season_data.get("transactions")
    traded_picks = season_data.get("traded_picks")
    if not isinstance(league, Mapping) or not isinstance(rosters, list) or not isinstance(transactions, list) or not isinstance(traded_picks, list):
        raise ValueError("season-specific league, rosters, transactions and traded picks are required")
    try:
        league_id = str(league["league_id"])
        season = int(league["season"])
        slots = tuple(str(value) for value in league["roster_positions"])
        settings = league["settings"]
        scoring = league["scoring_settings"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("historical season identity and settings are required") from exc
    if not league_id or not slots or not isinstance(settings, Mapping) or not isinstance(scoring, Mapping):
        raise ValueError("invalid season identity, roster slots, or settings")
    if len(rosters) < 2:
        raise ValueError("at least two season rosters are required")

    issues: set[str] = set()
    if league.get("total_rosters") is not None and int(league["total_rosters"]) != len(rosters):
        issues.add("season_team_count_mismatch")

    owners: dict[str, set[str]] = {}
    used: dict[str, int | None] = {}
    faab_uncertain: set[str] = set()
    seen_players: set[str] = set()
    for row in rosters:
        if not isinstance(row, Mapping) or row.get("roster_id") is None:
            raise ValueError("season roster identity is missing")
        roster_id = str(row["roster_id"])
        players = row.get("players")
        if not roster_id or roster_id in owners or not isinstance(players, list):
            raise ValueError("duplicate roster identity or missing end-anchor player list")
        membership = {str(player) for player in players}
        if len(membership) != len(players) or seen_players.intersection(membership):
            issues.add("end_anchor_duplicate_player_ownership")
        seen_players.update(membership)
        owners[roster_id] = membership
        raw_used = (row.get("settings") or {}).get("waiver_budget_used")
        if type(raw_used) not in (int, float) or raw_used < 0:
            used[roster_id] = None
            faab_uncertain.add(roster_id)
            issues.add("missing_or_invalid_end_anchor_waiver_usage")
        else:
            used[roster_id] = int(raw_used)

    pick_owners: dict[str, str] = {}
    for row in traded_picks:
        if not isinstance(row, Mapping):
            issues.add("malformed_traded_pick_anchor")
            continue
        try:
            pick_id = _pick_id(row)
            owner_id = str(row["owner_id"])
        except (KeyError, TypeError, ValueError):
            issues.add("malformed_traded_pick_anchor")
            continue
        if pick_id in pick_owners or owner_id not in owners:
            issues.add("duplicate_or_invalid_traded_pick_anchor")
        pick_owners[pick_id] = owner_id

    grouped: dict[int, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    completed_count = 0
    seen_tx_ids: set[str] = set()
    for tx in transactions:
        if not isinstance(tx, Mapping):
            issues.add("malformed_transaction_row")
            continue
        if tx.get("status") != "complete":
            continue
        completed_count += 1
        tx_id = str(tx.get("transaction_id") or "")
        if not tx_id or tx_id in seen_tx_ids:
            issues.add("duplicate_or_missing_completed_transaction_id")
        seen_tx_ids.add(tx_id)
        at = _timestamp(tx)
        if at is None:
            issues.add("completed_event_missing_completion_timestamp")
            for move in tx.get("waiver_budget") or ():
                if isinstance(move, Mapping):
                    faab_uncertain.update(str(move[key]) for key in ("sender", "receiver") if move.get(key) is not None)
            if tx.get("type") == "waiver":
                faab_uncertain.update(str(roster_id) for roster_id in tx.get("roster_ids") or ())
            continue
        created = tx.get("created")
        if type(created) not in (int, float) or created > at:
            issues.add("invalid_event_clock")
        grouped[at].append((tx_id, tx))

    def snapshot(at: int | None, boundary: str, events: list[tuple[str, Mapping[str, Any]]] | None = None) -> HistoricalRosterContextSnapshot:
        picks_by_roster: dict[str, list[str]] = {roster_id: [] for roster_id in owners}
        for pick_id, owner_id in pick_owners.items():
            if owner_id in picks_by_roster:
                picks_by_roster[owner_id].append(pick_id)
        event_rows = events or []
        event_ids = tuple(sorted(tx_id for tx_id, _ in event_rows))
        types = tuple(sorted({str(tx.get("type") or "unknown") for _, tx in event_rows}))
        instant = datetime.fromtimestamp(at / 1000, tz=UTC) if at is not None else None
        teams_list = []
        for roster_id in sorted(owners):
            budget_used = used[roster_id]
            if roster_id in faab_uncertain:
                budget_used = None
            if budget_used is not None and budget_used < 0:
                issues.add("reconstructed_waiver_usage_out_of_bounds")
                faab_uncertain.add(roster_id)
                budget_used = None
            teams_list.append(HistoricalRosterContextTeam(
                provider_roster_id=roster_id,
                player_ids=tuple(sorted(owners[roster_id])),
                traded_pick_ids=tuple(sorted(picks_by_roster[roster_id])),
                waiver_budget_used=budget_used,
                waiver_budget_evidence="conditional_complete_later_ledger" if budget_used is not None else "unknown",
            ))
        teams = tuple(teams_list)
        return HistoricalRosterContextSnapshot(
            effective_at=instant, boundary=boundary, transaction_ids=event_ids,
            event_types=types, teams=teams,
        )

    snapshots: list[HistoricalRosterContextSnapshot] = [snapshot(None, "archive_end_anchor")]
    # Work backward from the retained season-end anchor. A same-time group is
    # one boundary because the source does not establish order within the group.
    for at in sorted(grouped, reverse=True):
        events = sorted(grouped[at], key=lambda pair: pair[0])
        snapshots.append(snapshot(at, "after_completed_event_batch", events))

        touched: set[tuple[str, str]] = set()
        for _, tx in events:
            adds, drops = tx.get("adds") or {}, tx.get("drops") or {}
            picks = tx.get("draft_picks") or ()
            if not isinstance(adds, Mapping) or not isinstance(drops, Mapping):
                issues.add("malformed_event_player_movements")
                continue
            keys = {("player", str(player)) for player in adds}
            keys.update(("player", str(player)) for player in drops)
            try:
                keys.update(("pick", _pick_id(pick)) for pick in picks)
            except (KeyError, TypeError, ValueError):
                issues.add("malformed_event_pick_movement")
            if touched.intersection(keys):
                issues.add("ambiguous_same_timestamp_asset_order")
            touched.update(keys)

        for _, tx in events:
            adds, drops = tx.get("adds") or {}, tx.get("drops") or {}
            if not isinstance(adds, Mapping) or not isinstance(drops, Mapping):
                continue
            for player_id, destination in adds.items():
                roster_id, player = str(destination), str(player_id)
                if roster_id not in owners or player not in owners[roster_id]:
                    issues.add("post_event_player_ownership_mismatch")
                else:
                    owners[roster_id].remove(player)
            for player_id, source in drops.items():
                roster_id, player = str(source), str(player_id)
                if roster_id not in owners or player in owners[roster_id]:
                    issues.add("pre_event_player_ownership_conflict")
                else:
                    owners[roster_id].add(player)
            for pick in tx.get("draft_picks") or ():
                try:
                    pick_id = _pick_id(pick)
                    before, after = str(pick["previous_owner_id"]), str(pick["owner_id"])
                except (KeyError, TypeError, ValueError):
                    issues.add("malformed_event_pick_movement")
                    continue
                if before not in owners or after not in owners or before == after or pick_owners.get(pick_id) != after:
                    issues.add("traded_pick_history_mismatch")
                pick_owners[pick_id] = before
            for movement in tx.get("waiver_budget") or ():
                if not isinstance(movement, Mapping):
                    issues.add("unreconstructable_faab_transfer")
                    continue
                try:
                    sender, receiver, amount = str(movement["sender"]), str(movement["receiver"]), int(movement["amount"])
                    if sender not in used or receiver not in used or amount < 1 or used[sender] is None or used[receiver] is None:
                        raise ValueError
                    used[sender] -= amount
                    used[receiver] += amount
                except (KeyError, TypeError, ValueError):
                    issues.add("unreconstructable_faab_transfer")
                    for key in ("sender", "receiver"):
                        if movement.get(key) is not None:
                            faab_uncertain.add(str(movement[key]))
            if tx.get("type") == "waiver":
                settings_row = tx.get("settings") or {}
                roster_ids = tx.get("roster_ids") or ()
                bid = settings_row.get("waiver_bid") if isinstance(settings_row, Mapping) else None
                if type(bid) not in (int, float) or bid < 0 or len(roster_ids) != 1:
                    issues.add("unreconstructable_waiver_bid")
                    faab_uncertain.update(str(roster_id) for roster_id in roster_ids)
                else:
                    roster_id = str(roster_ids[0])
                    if roster_id not in used or used[roster_id] is None:
                        issues.add("unreconstructable_waiver_bid")
                        faab_uncertain.add(roster_id)
                    else:
                        used[roster_id] -= int(bid)
                        if used[roster_id] < 0:
                            issues.add("reconstructed_waiver_usage_out_of_bounds")
                            faab_uncertain.add(roster_id)

        snapshots.append(snapshot(at, "before_completed_event_batch", events))

    end_anchor = next(row for row in snapshots if row.boundary == "archive_end_anchor")
    event_snapshots = sorted(
        (row for row in snapshots if row.boundary != "archive_end_anchor"),
        key=lambda row: (
            row.effective_at,
            0 if row.boundary == "before_completed_event_batch" else 1,
        ),
    )
    snapshots = event_snapshots + [end_anchor]
    rules_digest = _digest({
        "settings": settings, "scoring": scoring, "slots": slots,
        "observed_team_count": len(owners),
    })
    issue_tuple = tuple(sorted(issues))
    faab_issue_codes = {
        "missing_or_invalid_end_anchor_waiver_usage",
        "unreconstructable_faab_transfer",
        "unreconstructable_waiver_bid",
        "reconstructed_waiver_usage_out_of_bounds",
    }
    pick_issue_codes = {
        "malformed_traded_pick_anchor",
        "duplicate_or_invalid_traded_pick_anchor",
        "malformed_event_pick_movement",
        "traded_pick_history_mismatch",
    }
    faab_issues = tuple(sorted(issues.intersection(faab_issue_codes)))
    pick_issues = tuple(sorted(issues.intersection(pick_issue_codes)))
    membership_issues = tuple(sorted(issues.difference(faab_issue_codes | pick_issue_codes)))
    return HistoricalRosterContextHistory(
        provider_league_id=league_id, season=season, source_revision=source_revision,
        source_sha256=_digest(season_data), league_rules_sha256=rules_digest,
        raw_roster_slots=slots, observed_team_count=len(owners), completed_event_count=completed_count,
        snapshots=tuple(snapshots), issues=issue_tuple,
        membership_issues=membership_issues, pick_issues=pick_issues, faab_issues=faab_issues,
        membership_status="incomplete_source_history" if membership_issues else "provisionally_consistent",
    )
