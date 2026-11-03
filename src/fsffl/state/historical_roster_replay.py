"""Provider-neutral reverse replay for retrospective roster membership.

Provider adapters normalize their immutable season-end anchor and completed
player ownership events into these records. The replay deliberately owns only
membership: league rules are identity metadata for downstream consumers, while
slots, scoring, forecasts, and point-in-time eligibility remain separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Literal


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class PlayerTransfer:
    """A normalized ownership change; ``None`` represents free agency."""
    player_id: str
    from_team_id: str | None
    to_team_id: str | None

    def __post_init__(self) -> None:
        if not self.player_id.strip():
            raise ValueError("player identity is required")
        if self.from_team_id == self.to_team_id:
            raise ValueError("a transfer must change ownership")
        if self.from_team_id is None and self.to_team_id is None:
            raise ValueError("a transfer must have an owner on at least one side")


@dataclass(frozen=True)
class CompletedRosterEvent:
    event_id: str
    effective_at: datetime
    event_type: str
    player_transfers: tuple[PlayerTransfer, ...]

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.event_type.strip():
            raise ValueError("event identity and type are required")
        if not _aware(self.effective_at):
            raise ValueError("event completion time must be timezone-aware")
        if len({row.player_id for row in self.player_transfers}) != len(self.player_transfers):
            raise ValueError("one event cannot transfer a player more than once")


@dataclass(frozen=True)
class RosterMembershipSnapshot:
    history_id: str
    snapshot_id: str
    effective_at: datetime | None
    boundary: Literal["before_completed_event_batch", "after_completed_event_batch", "archive_end_anchor"]
    event_ids: tuple[str, ...]
    teams: tuple[tuple[str, tuple[str, ...]], ...]
    free_agents: tuple[str, ...]

    def owner_map(self) -> dict[str, str]:
        return {player: team for team, players in self.teams for player in players}


@dataclass(frozen=True)
class HistoricalRosterReplay:
    history_id: str
    provider: str
    league_id: str
    season: int
    source_revision: str
    source_sha256: str
    rules_sha256: str
    snapshots: tuple[RosterMembershipSnapshot, ...]
    issues: tuple[str, ...]
    eligible_for_pit_decision_grade: Literal[False] = False
    model_version: Literal["provider-neutral-roster-replay-v1"] = "provider-neutral-roster-replay-v1"

    def state_at(self, cutoff: datetime, *, boundary: Literal["before", "after"] = "after") -> RosterMembershipSnapshot | None:
        """Return latest reconstructed membership at/before an aware cutoff."""
        if not _aware(cutoff):
            raise ValueError("cutoff must be timezone-aware")
        allowed = {"before_completed_event_batch": "before", "after_completed_event_batch": "after"}
        candidates = [row for row in self.snapshots
                      if row.effective_at is not None and row.effective_at <= cutoff
                      and allowed.get(row.boundary) == boundary]
        if not candidates:
            return None
        return max(candidates, key=lambda row: row.effective_at)

    def pre_transaction_state(self, event_id: str) -> RosterMembershipSnapshot | None:
        """Return a pre-event view only when the event has an unambiguous clock batch."""
        matches = [row for row in self.snapshots
                   if row.boundary == "before_completed_event_batch" and event_id in row.event_ids]
        if len(matches) != 1 or len(matches[0].event_ids) != 1:
            return None
        return matches[0]


def replay_roster_membership(
    *, provider: str, league_id: str, season: int, source_revision: str,
    source_sha256: str, rules_sha256: str,
    end_rosters: dict[str, tuple[str, ...]], events: tuple[CompletedRosterEvent, ...],
) -> HistoricalRosterReplay:
    """Reverse normalized completed events once from a retained end-roster anchor.

    Events at the same instant form one atomic batch. Repeated movement of one
    player inside a batch or any ownership mismatch blocks that batch's replay
    and is returned as an issue; event order is never guessed.
    """
    if not all(value.strip() for value in (provider, league_id, source_revision, source_sha256, rules_sha256)):
        raise ValueError("provider, league, source, and rules identities are required")
    if season < 1900 or len(end_rosters) < 2:
        raise ValueError("valid season and at least two roster anchors are required")
    owners: dict[str, set[str]] = {}
    issues: set[str] = set()
    for team_id, players in end_rosters.items():
        if not team_id.strip() or len(players) != len(set(players)):
            raise ValueError("team identities and unique end-anchor membership are required")
        owners[team_id] = set(players)
    seen: set[str] = {move.player_id for event in events for move in event.player_transfers}
    for players in owners.values():
        overlap = seen.intersection(players)
        if overlap:
            issues.add("end_anchor_duplicate_player_ownership")
        seen.update(players)
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("completed event identities must be unique")

    grouped: dict[datetime, list[CompletedRosterEvent]] = {}
    for event in events:
        grouped.setdefault(event.effective_at, []).append(event)
    history_id = "hrpl_" + _digest({
        "provider": provider, "league_id": league_id, "season": season,
        "source_revision": source_revision, "source_sha256": source_sha256,
        "rules_sha256": rules_sha256, "model_version": "provider-neutral-roster-replay-v1",
    })

    def snapshot(at: datetime | None, boundary: str, batch: tuple[CompletedRosterEvent, ...] = ()) -> RosterMembershipSnapshot:
        teams = tuple((team, tuple(sorted(players))) for team, players in sorted(owners.items()))
        owned = {player for _, players in teams for player in players}
        free_agents = tuple(sorted(seen - owned))
        event_ids = tuple(sorted(row.event_id for row in batch))
        sid = "hrsnap_" + _digest({"history_id": history_id, "at": at, "boundary": boundary,
                                   "events": event_ids, "teams": teams, "free_agents": free_agents})
        return RosterMembershipSnapshot(history_id, sid, at, boundary, event_ids, teams, free_agents)  # type: ignore[arg-type]

    snapshots = [snapshot(None, "archive_end_anchor")]
    for at in sorted(grouped, reverse=True):
        batch = tuple(sorted(grouped[at], key=lambda row: row.event_id))
        snapshots.append(snapshot(at, "after_completed_event_batch", batch))
        transfers = [move for event in batch for move in event.player_transfers]
        batch_issues = reverse_player_transfer_batch(owners, tuple(transfers))
        issues.update(batch_issues)
        snapshots.append(snapshot(at, "before_completed_event_batch", batch))

    snapshots.sort(key=lambda row: (
        row.effective_at is None,
        row.effective_at or datetime.max.replace(tzinfo=events[0].effective_at.tzinfo) if events else datetime.max,
        0 if row.boundary == "before_completed_event_batch" else 1,
    ))
    return HistoricalRosterReplay(history_id, provider, league_id, season, source_revision,
                                  source_sha256, rules_sha256, tuple(snapshots), tuple(sorted(issues)))


def reverse_player_transfer_batch(
    owners: dict[str, set[str]], transfers: tuple[PlayerTransfer, ...]
) -> tuple[str, ...]:
    """Atomically reverse normalized transfers against a mutable owner map."""
    touched = [move.player_id for move in transfers]
    if len(touched) != len(set(touched)):
        return ("ambiguous_same_timestamp_player_order",)
    issues: set[str] = set()
    for move in transfers:
        if ((move.from_team_id is not None and move.from_team_id not in owners)
                or (move.to_team_id is not None and move.to_team_id not in owners)):
            issues.add("event_references_unknown_team")
            continue
        current = next((team for team, players in owners.items() if move.player_id in players), None)
        if current != move.to_team_id:
            issues.add("post_event_player_ownership_mismatch")
        if move.from_team_id is not None and move.player_id in owners[move.from_team_id]:
            issues.add("pre_event_player_ownership_conflict")
    if issues:
        return tuple(sorted(issues))
    for move in transfers:
        if move.to_team_id is not None:
            owners[move.to_team_id].remove(move.player_id)
        if move.from_team_id is not None:
            owners[move.from_team_id].add(move.player_id)
    return ()
