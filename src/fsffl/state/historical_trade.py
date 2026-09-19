from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from .models import Asset, FaabAsset, FrozenModel, PickAsset, PlayerAsset, Provenance


class HistoricalTradeLeg(FrozenModel):
    """Assets sent by one team in a completed historical trade."""

    team_id: str
    sends: tuple[Asset, ...]

    @model_validator(mode="after")
    def validate_leg(self) -> "HistoricalTradeLeg":
        if not self.team_id.strip():
            raise ValueError("historical trade team_id cannot be blank")
        if not self.sends:
            raise ValueError("historical trade leg must contain at least one sent asset")
        return self


class HistoricalTradeRecord(FrozenModel):
    """Provider-normalized completed trade, before any valuation or grading."""

    transaction_id: str
    league_id: str
    completed_at: datetime
    legs: tuple[HistoricalTradeLeg, ...]
    creator_team_id: str | None = None
    provenance: Provenance
    model_version: str = "historical-trade-state-v1"

    @field_validator("completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_record(self) -> "HistoricalTradeRecord":
        if not self.transaction_id.strip() or not self.league_id.strip() or not self.model_version.strip():
            raise ValueError("historical trade identifiers cannot be blank")
        if len(self.legs) < 2:
            raise ValueError("historical trade requires at least two teams")
        team_ids = [leg.team_id for leg in self.legs]
        if len(team_ids) != len(set(team_ids)):
            raise ValueError("historical trade may contain only one leg per team")
        if self.creator_team_id is not None and self.creator_team_id not in set(team_ids):
            raise ValueError("creator_team_id must be a participating team")
        return self


class HistoricalTradeImportResult(FrozenModel):
    record: HistoricalTradeRecord | None = None
    skipped_reason: str | None = None
    unmapped_assets: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> "HistoricalTradeImportResult":
        if (self.record is None) == (self.skipped_reason is None):
            raise ValueError("historical trade import must contain either a record or skipped_reason")
        return self


PickKey = tuple[int, int, str]


def _pick_key(row: Mapping[str, Any], roster_to_team: Mapping[int, str]) -> PickKey | None:
    try:
        season = int(row["season"])
        round_number = int(row["round"])
        original_roster = int(row["roster_id"])
    except (KeyError, TypeError, ValueError):
        return None
    original_team = roster_to_team.get(original_roster)
    if original_team is None:
        return None
    return season, round_number, original_team


def normalize_sleeper_completed_trade(
    row: Mapping[str, Any],
    *,
    league_id: str,
    roster_to_team: Mapping[int, str],
    player_id_by_sleeper_id: Mapping[str, str],
    pick_id_by_key: Mapping[PickKey, str],
    provenance: Provenance,
    as_of: datetime,
    creator_team_by_user_id: Mapping[str, str] | None = None,
) -> HistoricalTradeImportResult:
    """Normalize one completed Sleeper trade without assigning economic value.

    Players require both provider ``adds`` and ``drops`` so their sender is known.
    Draft picks use Sleeper's previous/current owner fields and a caller-supplied
    point-in-time pick identity mapping. FAAB transfers are preserved as amount
    assets. Unknown or malformed assets fail the whole trade closed rather than
    producing a deceptively partial historical transaction.
    """

    if not league_id.strip():
        raise ValueError("league_id cannot be blank")
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if row.get("type") != "trade" or row.get("status") != "complete":
        return HistoricalTradeImportResult(skipped_reason="not a completed trade")

    timestamp_ms = row.get("status_updated") or row.get("created")
    transaction_id = str(row.get("transaction_id") or "").strip()
    if timestamp_ms is None or not transaction_id:
        return HistoricalTradeImportResult(skipped_reason="completed trade is missing identity or timestamp")
    completed_at = datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=UTC)
    if completed_at > as_of:
        return HistoricalTradeImportResult(skipped_reason="trade occurred after requested as_of")

    roster_ids_raw = row.get("roster_ids") or []
    try:
        roster_ids = tuple(int(value) for value in roster_ids_raw)
    except (TypeError, ValueError):
        return HistoricalTradeImportResult(skipped_reason="trade contains invalid roster ids")
    if len(roster_ids) < 2 or len(roster_ids) != len(set(roster_ids)):
        return HistoricalTradeImportResult(skipped_reason="trade must contain distinct participating rosters")
    if any(roster_id not in roster_to_team for roster_id in roster_ids):
        return HistoricalTradeImportResult(skipped_reason="trade contains an unmapped roster")

    sent_by_team: dict[str, list[Asset]] = {roster_to_team[roster_id]: [] for roster_id in roster_ids}
    unmapped: list[str] = []

    adds = row.get("adds") or {}
    drops = row.get("drops") or {}
    if not isinstance(adds, Mapping) or not isinstance(drops, Mapping):
        return HistoricalTradeImportResult(skipped_reason="trade player transfers are malformed")
    for sleeper_id, receiving_roster_raw in adds.items():
        sleeper_player_id = str(sleeper_id)
        player_id = player_id_by_sleeper_id.get(sleeper_player_id)
        sending_roster_raw = drops.get(sleeper_id)
        if sending_roster_raw is None:
            sending_roster_raw = drops.get(sleeper_player_id)
        if player_id is None or sending_roster_raw is None:
            unmapped.append(f"player:{sleeper_player_id}")
            continue
        try:
            sending_roster = int(sending_roster_raw)
            receiving_roster = int(receiving_roster_raw)
        except (TypeError, ValueError):
            unmapped.append(f"player:{sleeper_player_id}")
            continue
        if sending_roster not in roster_ids or receiving_roster not in roster_ids or sending_roster == receiving_roster:
            unmapped.append(f"player:{sleeper_player_id}")
            continue
        sent_by_team[roster_to_team[sending_roster]].append(PlayerAsset(player_id=player_id))

    draft_picks = row.get("draft_picks") or []
    if not isinstance(draft_picks, list):
        return HistoricalTradeImportResult(skipped_reason="trade draft-pick transfers are malformed")
    for pick_row in draft_picks:
        if not isinstance(pick_row, Mapping):
            unmapped.append("pick:malformed")
            continue
        key = _pick_key(pick_row, roster_to_team)
        pick_id = pick_id_by_key.get(key) if key is not None else None
        try:
            sending_roster = int(pick_row["previous_owner_id"])
            receiving_roster = int(pick_row["owner_id"])
        except (KeyError, TypeError, ValueError):
            sending_roster = receiving_roster = -1
        if (
            pick_id is None
            or sending_roster not in roster_ids
            or receiving_roster not in roster_ids
            or sending_roster == receiving_roster
        ):
            label = key if key is not None else "malformed"
            unmapped.append(f"pick:{label}")
            continue
        sent_by_team[roster_to_team[sending_roster]].append(PickAsset(pick_id=pick_id))

    waiver_budget = row.get("waiver_budget") or []
    if not isinstance(waiver_budget, list):
        return HistoricalTradeImportResult(skipped_reason="trade FAAB transfers are malformed")
    for transfer in waiver_budget:
        if not isinstance(transfer, Mapping):
            unmapped.append("faab:malformed")
            continue
        try:
            sender = int(transfer["sender"])
            receiver = int(transfer["receiver"])
            amount = int(transfer["amount"])
        except (KeyError, TypeError, ValueError):
            unmapped.append("faab:malformed")
            continue
        if sender not in roster_ids or receiver not in roster_ids or sender == receiver or amount <= 0:
            unmapped.append(f"faab:{amount}")
            continue
        sent_by_team[roster_to_team[sender]].append(FaabAsset(amount=amount))

    if unmapped:
        return HistoricalTradeImportResult(
            skipped_reason="trade contains assets that cannot be reconstructed defensibly",
            unmapped_assets=tuple(sorted(unmapped)),
        )
    if any(not sent_by_team[team_id] for team_id in sent_by_team):
        return HistoricalTradeImportResult(skipped_reason="one or more trade sides has no reconstructed outgoing asset")

    creator_team_id = None
    creator = row.get("creator")
    if creator is not None and creator_team_by_user_id is not None:
        creator_team_id = creator_team_by_user_id.get(str(creator))

    legs = tuple(
        HistoricalTradeLeg(team_id=team_id, sends=tuple(sent_by_team[team_id]))
        for team_id in sorted(sent_by_team)
    )
    return HistoricalTradeImportResult(
        record=HistoricalTradeRecord(
            transaction_id=transaction_id,
            league_id=league_id,
            completed_at=completed_at,
            legs=legs,
            creator_team_id=creator_team_id,
            provenance=provenance,
        )
    )
