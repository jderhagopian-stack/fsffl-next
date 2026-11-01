"""Read-only season-wide historical source reconciliation.

A retrospective archive is **not** a historical point-in-time State or forecast.
This provider-edge audit witnesses consistency of retained transactions with the
retained season-end roster/pick ledger and reports every unresolved contradiction.
It performs no inference of missing transactions or missing scoring/roster rules.
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


class RetrospectiveSeasonIssue(FrozenModel):
    code: Literal[
        "end_anchor_duplicate_player", "end_anchor_duplicate_pick", "end_anchor_roster_count_mismatch",
        "end_anchor_reserve_not_in_players", "end_anchor_taxi_not_in_players",
        "duplicate_completed_transaction_id", "missing_completed_transaction_time", "invalid_event_clock",
        "tied_completion_asset_overlap", "post_event_player_missing", "pre_event_player_conflict",
        "unknown_event_roster", "post_event_pick_owner_mismatch", "missing_end_pick_anchor",
        "invalid_pick_transfer", "invalid_faab_transfer", "missing_waiver_bid_or_owner",
    ]
    transaction_id: str | None = None
    completed_at: datetime | None = None
    event_type: str | None = None
    asset_id: str | None = None

    @field_validator("completed_at")
    @classmethod
    def requires_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("event time must be timezone-aware")
        return value


class RetrospectiveSeasonAudit(FrozenModel):
    provider: Literal["sleeper"] = "sleeper"
    provider_league_id: str
    season: int
    source_revision: str
    source_sha256: str
    original_rules_sha256: str
    team_count: int
    completed_events_examined: int
    completed_trades_examined: int
    player_movements_examined: int
    pick_movements_examined: int
    faab_transfers_examined: int
    waiver_bids_examined: int
    completed_timestamp_tie_groups: int
    issues: tuple[RetrospectiveSeasonIssue, ...]
    status: Literal["retrospective_ledger_consistent", "incomplete_source_history"]
    source_provides_contemporaneous_state: Literal[False] = False
    eligible_for_pit_decision_grade: Literal[False] = False
    historically_validated_faab_balances: Literal[False] = False
    model_version: Literal["retrospective-sleeper-season-audit-v1"] = "retrospective-sleeper-season-audit-v1"

    @model_validator(mode="after")
    def consistent_status(self) -> "RetrospectiveSeasonAudit":
        if bool(self.issues) != (self.status == "incomplete_source_history"):
            raise ValueError("status must reflect all source-history issues")
        return self


def _sha(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _pick_id(p: Mapping[str, Any]) -> str:
    return f"{int(p['season'])}:{int(p['round'])}:{int(p['roster_id'])}"


def audit_retrospective_sleeper_season(
    season_data: Mapping[str, Any], *, source_revision: str,
) -> RetrospectiveSeasonAudit:
    """Reconcile every completed source event against a *retrospective* end anchor.

    No network, persistence, source modification or FSFFL-specific constants.
    The present-day copy of historical source data cannot certify that its
    evidence was available to an owner at a prior decision cutoff.
    """
    if not source_revision.strip():
        raise ValueError("immutable source revision required")
    league = season_data.get("league")
    if not isinstance(league, Mapping):
        raise ValueError("missing season-specific source league settings")
    try:
        season = int(league["season"])
        league_id = str(league["league_id"])
        slots = league["roster_positions"]
        settings = league["settings"]
        scoring = league["scoring_settings"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("historical season-specific rules are required") from exc
    if not league_id or not isinstance(slots, list) or not slots or not isinstance(settings, Mapping) or not isinstance(scoring, Mapping):
        raise ValueError("invalid original league identity or rules")
    rosters = season_data.get("rosters")
    txs = season_data.get("transactions")
    picks = season_data.get("traded_picks")
    if not isinstance(rosters, list) or not isinstance(txs, list) or not isinstance(picks, list):
        raise ValueError("original roster, transaction and traded-pick lists required")
    if len(rosters) < 2:
        raise ValueError("not enough historical rosters")
    ids = tuple(str(x.get("roster_id", "")) for x in rosters)
    if any(not x or x == "None" for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("ambiguous season-roster IDs")
    anomalies: list[RetrospectiveSeasonIssue] = []

    def record(code: str, tx: Mapping[str, Any] | None = None, *, asset_id: str | None = None) -> None:
        completed = tx.get("status_updated") if tx is not None else None
        event_time = datetime.fromtimestamp(completed / 1000, tz=UTC) if type(completed) in (int, float) and completed > 0 else None
        anomalies.append(RetrospectiveSeasonIssue(code=code, transaction_id=str(tx.get("transaction_id")) if tx else None,
                                                completed_at=event_time, event_type=str(tx.get("type")) if tx else None,
                                                asset_id=asset_id))

    if league.get("total_rosters") is not None and int(league["total_rosters"]) != len(rosters):
        record("end_anchor_roster_count_mismatch")
    owners: dict[str, set[str]] = {}
    seen_players: set[str] = set()
    for row in rosters:
        rid = str(row["roster_id"])
        players = row.get("players")
        if not isinstance(players, list):
            raise ValueError("end anchor missing roster players")
        vals = [str(p) for p in players]
        own = set(vals)
        if len(own) != len(vals) or seen_players & own:
            record("end_anchor_duplicate_player")
        seen_players.update(own)
        owners[rid] = own
        for key, code in (("reserve", "end_anchor_reserve_not_in_players"),
                          ("taxi", "end_anchor_taxi_not_in_players")):
            if row.get(key) is not None and not set(map(str, row[key])).issubset(own):
                record(code)
    picked: dict[str, str] = {}
    for p in picks:
        k = _pick_id(p)
        if k in picked:
            record("end_anchor_duplicate_pick")
        picked[k] = str(p["owner_id"])
    completed_rows: list[tuple[int, str, Mapping[str, Any]]] = []
    seen_ids: set[str] = set()
    for tx in txs:
        if tx.get("status") != "complete":
            continue
        tid = str(tx.get("transaction_id") or "")
        if not tid or tid in seen_ids:
            record("duplicate_completed_transaction_id", tx)
        seen_ids.add(tid)
        at = tx.get("status_updated")
        if type(at) not in (int, float) or at <= 0:
            record("missing_completed_transaction_time", tx)
            continue
        created = tx.get("created")
        if type(created) not in (int, float) or created > at:
            record("invalid_event_clock", tx)
        completed_rows.append((int(at), tid, tx))

    # A tied provider timestamp has no known order. If two completed events
    # affect the same player/pick, reverse reconstruction is intrinsically ambiguous.
    by_time: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for at, _, tx in completed_rows:
        by_time[at].append(tx)
    tie_groups = 0
    for tx_group in by_time.values():
        if len(tx_group) < 2:
            continue
        tie_groups += 1
        touched: set[tuple[str, str]] = set()
        for tx in tx_group:
            keys = {("player", str(p)) for p in (tx.get("adds") or {})}
            keys.update(("player", str(p)) for p in (tx.get("drops") or {}))
            keys.update(("pick", _pick_id(p)) for p in (tx.get("draft_picks") or ()))
            if keys & touched:
                record("tied_completion_asset_overlap", tx)
            touched.update(keys)

    player_moves = pick_moves = faab_moves = bids = trades = 0
    # Stable order is an implementation detail for independent same-time assets,
    # not an assertion that lexical IDs give the true provider event order.
    for _, _, tx in sorted(completed_rows, key=lambda x: (x[0], x[1]), reverse=True):
        if tx.get("type") == "trade":
            trades += 1
        for player, dest in (tx.get("adds") or {}).items():
            player_moves += 1
            dst = str(dest)
            if dst not in owners:
                record("unknown_event_roster", tx)
            elif str(player) not in owners[dst]:
                record("post_event_player_missing", tx, asset_id=str(player))
            else:
                owners[dst].remove(str(player))
        for player, orig in (tx.get("drops") or {}).items():
            player_moves += 1
            src = str(orig)
            if src not in owners:
                record("unknown_event_roster", tx)
            elif str(player) in owners[src]:
                record("pre_event_player_conflict", tx)
            else:
                owners[src].add(str(player))
        for p in tx.get("draft_picks") or ():
            pick_moves += 1
            k = _pick_id(p)
            prev, after = str(p["previous_owner_id"]), str(p["owner_id"])
            if prev not in owners or after not in owners or prev == after:
                record("invalid_pick_transfer", tx)
            if k not in picked:
                record("missing_end_pick_anchor", tx)
            elif picked[k] != after:
                record("post_event_pick_owner_mismatch", tx)
            picked[k] = prev
        for row in tx.get("waiver_budget") or ():
            faab_moves += 1
            if (str(row.get("sender")) not in owners or str(row.get("receiver")) not in owners
                    or str(row.get("sender")) == str(row.get("receiver"))
                    or type(row.get("amount")) not in (int, float) or row["amount"] <= 0):
                record("invalid_faab_transfer", tx)
        if tx.get("type") == "waiver":
            bids += 1
            bid = (tx.get("settings") or {}).get("waiver_bid")
            roster_ids = tx.get("roster_ids") or []
            if (type(bid) not in (int, float) or bid < 0 or len(roster_ids) != 1
                    or str(roster_ids[0]) not in owners):
                record("missing_waiver_bid_or_owner", tx)
    issues = tuple(anomalies)
    return RetrospectiveSeasonAudit(
        provider_league_id=league_id, season=season, source_revision=source_revision,
        source_sha256=_sha(season_data),
        original_rules_sha256=_sha({"settings": settings, "scoring": scoring, "slots": slots}),
        team_count=len(rosters), completed_events_examined=len(completed_rows),
        completed_trades_examined=trades, player_movements_examined=player_moves,
        pick_movements_examined=pick_moves, faab_transfers_examined=faab_moves,
        waiver_bids_examined=bids, completed_timestamp_tie_groups=tie_groups,
        issues=issues, status="incomplete_source_history" if issues else "retrospective_ledger_consistent",
    )
