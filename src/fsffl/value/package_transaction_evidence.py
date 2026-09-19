from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .calibration import DataRightsClass


class PackageAssetKind(StrEnum):
    PLAYER = "player"
    PICK = "pick"
    FAAB = "faab"


class PackageAssetLeg(FrozenModel):
    """One asset movement retained inside its completed transaction package."""

    asset_kind: PackageAssetKind
    receiving_roster_id: int = Field(ge=1)
    canonical_asset_id: str | None = None
    source_asset_id: str
    quantity: float = Field(gt=0.0)

    @model_validator(mode="after")
    def validate_leg(self) -> "PackageAssetLeg":
        if not self.source_asset_id.strip():
            raise ValueError("package source asset id cannot be blank")
        if self.canonical_asset_id is not None and not self.canonical_asset_id.strip():
            raise ValueError("canonical package asset id cannot be blank")
        return self


class PackageTradeSide(FrozenModel):
    roster_id: int = Field(ge=1)
    received: tuple[PackageAssetLeg, ...]

    @model_validator(mode="after")
    def validate_side(self) -> "PackageTradeSide":
        if not self.received:
            raise ValueError("package trade side must receive at least one asset")
        if any(row.receiving_roster_id != self.roster_id for row in self.received):
            raise ValueError("package trade leg receiving roster must match side")
        return self


class MultiAssetTradeObservation(FrozenModel):
    """Completed two-team trade preserved as two whole packages.

    No asset is assigned a synthetic one-for-one clearing price. Missing historical
    identity mapping remains explicit on individual legs so downstream research can
    fail closed rather than silently dropping the difficult parts of a package.
    """

    transaction_id: str
    league_id: str
    format_context_id: str
    completed_at: datetime
    side_a: PackageTradeSide
    side_b: PackageTradeSide
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
    def validate_trade(self) -> "MultiAssetTradeObservation":
        if not self.transaction_id.strip() or not self.league_id.strip() or not self.format_context_id.strip():
            raise ValueError("package trade identifiers cannot be blank")
        if self.side_a.roster_id == self.side_b.roster_id:
            raise ValueError("package trade requires two distinct rosters")
        if self.creator_user_id is not None and not self.creator_user_id.strip():
            raise ValueError("creator_user_id cannot be blank")
        if self.provenance_uri is not None and not self.provenance_uri.strip():
            raise ValueError("provenance_uri cannot be blank")
        return self

    @property
    def asset_count(self) -> int:
        return len(self.side_a.received) + len(self.side_b.received)

    @property
    def is_one_for_one(self) -> bool:
        return len(self.side_a.received) == 1 and len(self.side_b.received) == 1


class SleeperPackageTradeImportResult(FrozenModel):
    observations: tuple[MultiAssetTradeObservation, ...]
    transactions_seen: int = Field(ge=0)
    completed_trades_seen: int = Field(ge=0)
    imported: int = Field(ge=0)
    skipped_non_two_team: int = Field(ge=0)
    skipped_empty_side: int = Field(ge=0)
    skipped_future: int = Field(ge=0)


def _pick_source_id(row: Mapping[str, object]) -> str:
    season = int(row.get("season") or 0)
    round_number = int(row.get("round") or 0)
    original_roster_id = int(row.get("roster_id") or 0)
    if season < 1900 or round_number < 1 or original_roster_id < 1:
        raise ValueError("Sleeper draft-pick transfer is missing season/round/original roster")
    return f"sleeper-pick:{season}:R{round_number}:original-roster:{original_roster_id}"


def normalize_sleeper_package_trades(
    json_text: str,
    *,
    league_id: str,
    format_context_id: str,
    asset_id_by_sleeper_id: Mapping[str, str],
    canonical_pick_id_by_source_id: Mapping[str, str] | None,
    as_of: datetime,
    rights_class: DataRightsClass = DataRightsClass.RESEARCH_ONLY,
    provenance_uri: str | None = None,
) -> SleeperPackageTradeImportResult:
    """Retain every completed two-team Sleeper trade as a whole package.

    Players, picks and FAAB remain distinct legs. A missing player/pick crosswalk
    does not cause the transaction to disappear; the canonical id remains None and
    downstream calibration must decide whether the observation has enough mapped
    evidence for its question. This importer performs no valuation or decomposition.
    """

    if not league_id.strip() or not format_context_id.strip():
        raise ValueError("league_id and format_context_id cannot be blank")
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    payload = json.loads(json_text)
    if not isinstance(payload, list):
        raise ValueError("Sleeper transactions payload must be a list")
    pick_map = canonical_pick_id_by_source_id or {}

    observations: list[MultiAssetTradeObservation] = []
    transactions_seen = completed_trades_seen = 0
    skipped_non_two_team = skipped_empty_side = skipped_future = 0

    for row in payload:
        transactions_seen += 1
        if not isinstance(row, dict):
            raise ValueError("Sleeper transaction rows must be objects")
        if row.get("type") != "trade" or row.get("status") != "complete":
            continue
        completed_trades_seen += 1

        timestamp_ms = row.get("status_updated") or row.get("created")
        if timestamp_ms is None:
            raise ValueError("completed Sleeper trade is missing transaction timestamp")
        completed_at = datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=UTC)
        if completed_at > as_of:
            skipped_future += 1
            continue

        roster_ids_raw = row.get("roster_ids") or []
        if not isinstance(roster_ids_raw, list) or len(roster_ids_raw) != 2:
            skipped_non_two_team += 1
            continue
        roster_ids = tuple(sorted(int(value) for value in roster_ids_raw))
        if roster_ids[0] == roster_ids[1]:
            skipped_non_two_team += 1
            continue

        legs_by_roster: dict[int, list[PackageAssetLeg]] = {roster_ids[0]: [], roster_ids[1]: []}
        adds = row.get("adds") or {}
        if not isinstance(adds, dict):
            raise ValueError("Sleeper trade adds must be an object")
        for sleeper_player_id, receiving_roster in adds.items():
            roster_id = int(receiving_roster)
            if roster_id not in legs_by_roster:
                raise ValueError("Sleeper trade player receiver is not one of the transaction rosters")
            source_id = str(sleeper_player_id).strip()
            if not source_id:
                raise ValueError("Sleeper trade contains a blank player id")
            legs_by_roster[roster_id].append(
                PackageAssetLeg(
                    asset_kind=PackageAssetKind.PLAYER,
                    receiving_roster_id=roster_id,
                    canonical_asset_id=asset_id_by_sleeper_id.get(source_id),
                    source_asset_id=source_id,
                    quantity=1.0,
                )
            )

        draft_picks = row.get("draft_picks") or []
        if not isinstance(draft_picks, list):
            raise ValueError("Sleeper trade draft_picks must be a list")
        for pick in draft_picks:
            if not isinstance(pick, dict):
                raise ValueError("Sleeper draft-pick transfer must be an object")
            receiving_roster = int(pick.get("owner_id") or 0)
            if receiving_roster not in legs_by_roster:
                raise ValueError("Sleeper draft-pick receiver is not one of the transaction rosters")
            source_id = _pick_source_id(pick)
            legs_by_roster[receiving_roster].append(
                PackageAssetLeg(
                    asset_kind=PackageAssetKind.PICK,
                    receiving_roster_id=receiving_roster,
                    canonical_asset_id=pick_map.get(source_id),
                    source_asset_id=source_id,
                    quantity=1.0,
                )
            )

        waiver_budget = row.get("waiver_budget") or []
        if not isinstance(waiver_budget, list):
            raise ValueError("Sleeper trade waiver_budget must be a list")
        for transfer in waiver_budget:
            if not isinstance(transfer, dict):
                raise ValueError("Sleeper FAAB transfer must be an object")
            sender = int(transfer.get("sender") or 0)
            receiver = int(transfer.get("receiver") or 0)
            amount = float(transfer.get("amount") or 0.0)
            if sender not in legs_by_roster or receiver not in legs_by_roster or amount <= 0:
                raise ValueError("Sleeper FAAB transfer is malformed")
            legs_by_roster[receiver].append(
                PackageAssetLeg(
                    asset_kind=PackageAssetKind.FAAB,
                    receiving_roster_id=receiver,
                    canonical_asset_id=None,
                    source_asset_id=f"sleeper-faab:{sender}->{receiver}",
                    quantity=amount,
                )
            )

        if any(not legs_by_roster[roster_id] for roster_id in roster_ids):
            skipped_empty_side += 1
            continue

        transaction_id = str(row.get("transaction_id") or "").strip()
        if not transaction_id:
            raise ValueError("completed Sleeper trade is missing transaction_id")
        creator = row.get("creator")
        observations.append(
            MultiAssetTradeObservation(
                transaction_id=transaction_id,
                league_id=league_id,
                format_context_id=format_context_id,
                completed_at=completed_at,
                side_a=PackageTradeSide(roster_id=roster_ids[0], received=tuple(legs_by_roster[roster_ids[0]])),
                side_b=PackageTradeSide(roster_id=roster_ids[1], received=tuple(legs_by_roster[roster_ids[1]])),
                creator_user_id=str(creator).strip() if creator is not None else None,
                rights_class=rights_class,
                provenance_uri=provenance_uri,
            )
        )

    observations.sort(key=lambda item: (item.completed_at, item.transaction_id))
    return SleeperPackageTradeImportResult(
        observations=tuple(observations),
        transactions_seen=transactions_seen,
        completed_trades_seen=completed_trades_seen,
        imported=len(observations),
        skipped_non_two_team=skipped_non_two_team,
        skipped_empty_side=skipped_empty_side,
        skipped_future=skipped_future,
    )
