from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Mapping

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .calibration import DataRightsClass


class OneForOneTradeObservation(FrozenModel):
    """One completed two-team, player-for-player trade.

    This preserves the transaction as a pairwise equivalence observation. It
    deliberately does not assign either player a scalar clearing price.
    """

    transaction_id: str
    league_id: str
    format_context_id: str
    completed_at: datetime
    roster_a_id: int = Field(ge=1)
    roster_b_id: int = Field(ge=1)
    asset_a_id: str
    asset_b_id: str
    creator_user_id: str | None = None
    rights_class: DataRightsClass = DataRightsClass.RESEARCH_ONLY
    provenance_uri: str | None = None

    @field_validator("completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_trade(self) -> "OneForOneTradeObservation":
        required = (self.transaction_id, self.league_id, self.format_context_id)
        if any(not value.strip() for value in required):
            raise ValueError("transaction identifiers and format context cannot be blank")
        if not self.asset_a_id.strip() or not self.asset_b_id.strip():
            raise ValueError("trade asset ids cannot be blank")
        if self.asset_a_id == self.asset_b_id:
            raise ValueError("one-for-one trade assets must be distinct")
        if self.roster_a_id == self.roster_b_id:
            raise ValueError("one-for-one trade must involve two distinct rosters")
        if self.creator_user_id is not None and not self.creator_user_id.strip():
            raise ValueError("creator_user_id cannot be blank")
        if self.provenance_uri is not None and not self.provenance_uri.strip():
            raise ValueError("provenance_uri cannot be blank")
        return self


class SleeperOneForOneImportResult(FrozenModel):
    observations: tuple[OneForOneTradeObservation, ...]
    transactions_seen: int = Field(ge=0)
    completed_trades_seen: int = Field(ge=0)
    imported: int = Field(ge=0)
    skipped_non_one_for_one: int = Field(ge=0)
    skipped_unmapped: int = Field(ge=0)
    skipped_future: int = Field(ge=0)


def normalize_sleeper_one_for_one_trades(
    json_text: str,
    *,
    league_id: str,
    format_context_id: str,
    asset_id_by_sleeper_id: Mapping[str, str],
    as_of: datetime,
    rights_class: DataRightsClass = DataRightsClass.RESEARCH_ONLY,
    provenance_uri: str | None = None,
) -> SleeperOneForOneImportResult:
    """Extract only clean completed two-player trades from Sleeper transactions.

    Eligible trades must be complete, involve exactly two rosters, contain
    exactly two player additions with one player received by each roster, and
    contain no draft picks or FAAB transfer. Multi-asset packages are skipped,
    not decomposed into unsupported per-asset prices.
    """

    if not league_id.strip() or not format_context_id.strip():
        raise ValueError("league_id and format_context_id cannot be blank")
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    payload = json.loads(json_text)
    if not isinstance(payload, list):
        raise ValueError("Sleeper transactions payload must be a list")

    observations: list[OneForOneTradeObservation] = []
    transactions_seen = 0
    completed_trades_seen = 0
    skipped_non_one_for_one = 0
    skipped_unmapped = 0
    skipped_future = 0

    for row in payload:
        transactions_seen += 1
        if not isinstance(row, dict):
            raise ValueError("Sleeper transaction rows must be objects")
        if row.get("type") != "trade" or row.get("status") != "complete":
            continue
        completed_trades_seen += 1

        roster_ids_raw = row.get("roster_ids") or []
        adds = row.get("adds") or {}
        draft_picks = row.get("draft_picks") or []
        waiver_budget = row.get("waiver_budget") or []

        if (
            not isinstance(roster_ids_raw, list)
            or len(roster_ids_raw) != 2
            or not isinstance(adds, dict)
            or len(adds) != 2
            or draft_picks
            or waiver_budget
        ):
            skipped_non_one_for_one += 1
            continue

        roster_ids = tuple(int(value) for value in roster_ids_raw)
        if roster_ids[0] == roster_ids[1]:
            skipped_non_one_for_one += 1
            continue

        received_by_roster: dict[int, str] = {}
        invalid = False
        for sleeper_player_id, receiving_roster in adds.items():
            try:
                roster_id = int(receiving_roster)
            except (TypeError, ValueError):
                invalid = True
                break
            if roster_id not in roster_ids or roster_id in received_by_roster:
                invalid = True
                break
            player_id = str(sleeper_player_id).strip()
            if not player_id:
                invalid = True
                break
            received_by_roster[roster_id] = player_id
        if invalid or set(received_by_roster) != set(roster_ids):
            skipped_non_one_for_one += 1
            continue

        asset_by_roster: dict[int, str] = {}
        for roster_id, player_id in received_by_roster.items():
            asset_id = asset_id_by_sleeper_id.get(player_id)
            if asset_id is None:
                invalid = True
                break
            asset_by_roster[roster_id] = asset_id
        if invalid:
            skipped_unmapped += 1
            continue

        timestamp_ms = row.get("status_updated") or row.get("created")
        if timestamp_ms is None:
            raise ValueError("completed Sleeper trade is missing transaction timestamp")
        completed_at = datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=UTC)
        if completed_at > as_of:
            skipped_future += 1
            continue

        roster_a, roster_b = sorted(roster_ids)
        transaction_id = str(row.get("transaction_id") or "").strip()
        if not transaction_id:
            raise ValueError("completed Sleeper trade is missing transaction_id")
        creator = row.get("creator")
        observations.append(
            OneForOneTradeObservation(
                transaction_id=transaction_id,
                league_id=league_id,
                format_context_id=format_context_id,
                completed_at=completed_at,
                roster_a_id=roster_a,
                roster_b_id=roster_b,
                asset_a_id=asset_by_roster[roster_a],
                asset_b_id=asset_by_roster[roster_b],
                creator_user_id=str(creator).strip() if creator is not None else None,
                rights_class=rights_class,
                provenance_uri=provenance_uri,
            )
        )

    observations.sort(key=lambda item: (item.completed_at, item.transaction_id))
    return SleeperOneForOneImportResult(
        observations=tuple(observations),
        transactions_seen=transactions_seen,
        completed_trades_seen=completed_trades_seen,
        imported=len(observations),
        skipped_non_one_for_one=skipped_non_one_for_one,
        skipped_unmapped=skipped_unmapped,
        skipped_future=skipped_future,
    )
