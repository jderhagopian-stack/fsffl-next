"""Optional offline archived-source acceptance; never checked-in league source.

Sets FSFFL_RESEARCH_HISTORICAL_ARCHIVE to a secure local source path. Absent the
original pinned archive, this test cannot claim real-source acceptance.
"""
from __future__ import annotations

from hashlib import sha1
import json
import os
from pathlib import Path

import pytest

from fsffl.state.retrospective_sleeper_replay import replay_archived_sleeper_trade
from fsffl.state.historical_trade import normalize_sleeper_completed_trade
from fsffl.state.models import Provenance, PlayerAsset, PickAsset, FaabAsset
from datetime import UTC, datetime


PINNED_SOURCE_BLOB = "e18c01bf25f58c5dfe3d0802f53de484ea257ca1"
PINNED_TRADE = "1014282713371283456"


def _ownership_window_is_consistent(replay):
    before = {row.roster_id: row for row in replay.before_ownership}
    after = {row.roster_id: row for row in replay.after_ownership}
    if len(before) != replay.observed_team_count or len(after) != replay.observed_team_count:
        return False
    for transfer in replay.transfers:
        field = "player_ids" if transfer.asset_kind == "player" else "pick_ids"
        if sum(transfer.source_asset_id in getattr(row, field) for row in replay.before_ownership) != 1:
            return False
        if sum(transfer.source_asset_id in getattr(row, field) for row in replay.after_ownership) != 1:
            return False
        if transfer.source_asset_id not in getattr(before[transfer.before_roster_id], field):
            return False
        if transfer.source_asset_id not in getattr(after[transfer.after_roster_id], field):
            return False
    faab = {row.roster_id: row for row in replay.faab}
    if set(faab) != {row.roster_id for row in replay.before_ownership if row.faab_used is not None}:
        return False
    if set(faab) != {row.roster_id for row in replay.after_ownership if row.faab_used is not None}:
        return False
    if any(before[team].faab_used != row.used_before or after[team].faab_used != row.used_after
           for team, row in faab.items()):
        return False
    return replay.roster_slot_coverage == "unknown_at_trade_cutoff"


def test_pinned_original_archive_2023_factual_replay_private():
    source = os.environ.get("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not source:
        pytest.skip("private original archived source not mounted; no real-source claim")
    bytes_ = Path(source).read_bytes()
    actual = sha1(b"blob " + str(len(bytes_)).encode() + b"\0" + bytes_).hexdigest()
    assert actual == PINNED_SOURCE_BLOB, "archived source changed; do not silently rebaseline"
    archive = json.loads(bytes_)
    seasons = [row for row in archive if row["league"]["season"] == "2023"]
    assert len(seasons) == 1
    s = seasons[0]
    replay = replay_archived_sleeper_trade(
        s, transaction_id=PINNED_TRADE, source_revision="git-blob:" + PINNED_SOURCE_BLOB)
    assert replay.status == "provisionally_consistent", replay.issues
    assert _ownership_window_is_consistent(replay)
    assert replay.future_completed_events_reversed == 191
    assert replay.observed_team_count == 12
    assert len([x for x in replay.transfers if x.asset_kind == "player"]) == 1
    assert len([x for x in replay.transfers if x.asset_kind == "pick"]) == 1
    assert len(replay.faab) == 2
    assert replay.eligible_for_pit_decision_grade is False
    assert replay.historical_anchor_independently_verified is False
    balances = {x.roster_id: x for x in replay.faab}
    assert balances["2"].used_before == 60 and balances["2"].used_after == 70
    assert balances["7"].used_before == 25 and balances["7"].used_after == 15


def test_real_archived_trade_reuses_existing_canonical_transaction_importer():
    """Same archived transaction must have the same sends under NEXT's State authority."""
    path = os.environ.get("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original source not mounted")
    blob = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest() == PINNED_SOURCE_BLOB
    y = next(row for row in json.loads(blob) if row["league"]["season"] == "2023")
    tx = next(t for t in y["transactions"] if t["transaction_id"] == PINNED_TRADE)
    replay = replay_archived_sleeper_trade(y, transaction_id=PINNED_TRADE,
                                            source_revision="git-blob:" + PINNED_SOURCE_BLOB)
    assert replay.status == "provisionally_consistent"
    source_rosters = {int(r["roster_id"]): f"year-2023-team-{int(r['roster_id'])}" for r in y["rosters"]}
    source_player_ids = {str(pid): f"sleeper-player-{str(pid)}" for pid in tx["adds"]}
    key_to_pick = {(int(p["season"]), int(p["round"]), source_rosters[int(p["roster_id"])]):
                   f"pick-{p['season']}-{p['round']}-{p['roster_id']}" for p in tx["draft_picks"]}
    canonical = normalize_sleeper_completed_trade(
        tx, league_id="sleeper:" + str(y["league"]["league_id"]),
        roster_to_team=source_rosters, player_id_by_sleeper_id=source_player_ids,
        pick_id_by_key=key_to_pick,
        provenance=Provenance(source="retrospectively_retained_archive", retrieved_at=datetime.now(UTC),
                              effective_at=replay.trade_completed_at),
        as_of=replay.trade_completed_at,
    )
    assert canonical.record is not None and canonical.skipped_reason is None
    assert canonical.record.completed_at == replay.trade_completed_at
    recorded_sends = {
        (str(int(team_id.rsplit("-", 1)[1])), kind, asset_id)
        for team_id, kinds in (
            (leg.team_id,
             [("player", str(int(asset.player_id.rsplit("-", 1)[1]))) if isinstance(asset, PlayerAsset)
               else ("pick", asset.pick_id) if isinstance(asset, PickAsset)
               else ("faab", str(asset.amount)) for asset in leg.sends])
            for leg in canonical.record.legs
        ) for kind, asset_id in kinds
    }
    expected_sends = set()
    for transfer in replay.transfers:
        label = (str(int(transfer.source_asset_id.rsplit(":", 1)[1])) if transfer.asset_kind == "pick"
                 else transfer.source_asset_id)
        asset_id = (f"pick-{transfer.source_asset_id.replace(':', '-')}" if transfer.asset_kind == "pick"
                    else label)
        expected_sends.add((transfer.before_roster_id, transfer.asset_kind, asset_id))
    for item in tx.get("waiver_budget") or []:
        expected_sends.add((str(item["sender"]), "faab", str(item["amount"])))
    assert recorded_sends == expected_sends
