from datetime import UTC, datetime
import json

from fsffl.value.package_transaction_evidence import (
    PackageAssetKind,
    normalize_sleeper_package_trades,
)


def test_multi_asset_trade_is_retained_as_two_whole_packages() -> None:
    completed_at = datetime(2026, 8, 15, 12, tzinfo=UTC)
    payload = [
        {
            "type": "trade",
            "status": "complete",
            "transaction_id": "trade-1",
            "roster_ids": [1, 2],
            "status_updated": int(completed_at.timestamp() * 1000),
            "creator": "owner-1",
            "adds": {
                "lamar": 1,
                "stroud": 2,
                "hubbard": 2,
            },
            "draft_picks": [
                {"season": "2027", "round": 2, "roster_id": 1, "previous_owner_id": 1, "owner_id": 2}
            ],
            "waiver_budget": [
                {"sender": 2, "receiver": 1, "amount": 7}
            ],
        }
    ]
    source_pick_id = "sleeper-pick:2027:R2:original-roster:1"
    result = normalize_sleeper_package_trades(
        json.dumps(payload),
        league_id="league-1",
        format_context_id="dynasty:12t:sf:0.5ppr",
        asset_id_by_sleeper_id={"lamar": "p-lamar", "stroud": "p-stroud", "hubbard": "p-hubbard"},
        canonical_pick_id_by_source_id={source_pick_id: "pick-2027-r2-team1"},
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert result.imported == 1
    trade = result.observations[0]
    assert trade.is_one_for_one is False
    assert trade.asset_count == 5
    assert trade.side_a.roster_id == 1
    assert trade.side_b.roster_id == 2
    assert {(row.asset_kind, row.canonical_asset_id, row.quantity) for row in trade.side_a.received} == {
        (PackageAssetKind.PLAYER, "p-lamar", 1.0),
        (PackageAssetKind.FAAB, None, 7.0),
    }
    assert {(row.asset_kind, row.canonical_asset_id) for row in trade.side_b.received} == {
        (PackageAssetKind.PLAYER, "p-stroud"),
        (PackageAssetKind.PLAYER, "p-hubbard"),
        (PackageAssetKind.PICK, "pick-2027-r2-team1"),
    }


def test_unmapped_assets_remain_visible_instead_of_dropping_trade() -> None:
    completed_at = datetime(2026, 8, 15, 12, tzinfo=UTC)
    payload = [
        {
            "type": "trade",
            "status": "complete",
            "transaction_id": "trade-2",
            "roster_ids": [1, 2],
            "status_updated": int(completed_at.timestamp() * 1000),
            "adds": {"known": 1, "unknown": 2},
            "draft_picks": [],
            "waiver_budget": [],
        }
    ]
    result = normalize_sleeper_package_trades(
        json.dumps(payload),
        league_id="league-1",
        format_context_id="dynasty:12t:sf:0.5ppr",
        asset_id_by_sleeper_id={"known": "p-known"},
        canonical_pick_id_by_source_id=None,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert result.imported == 1
    trade = result.observations[0]
    unknown = trade.side_b.received[0]
    assert unknown.source_asset_id == "unknown"
    assert unknown.canonical_asset_id is None


def test_future_package_trade_is_rejected_from_point_in_time_evidence() -> None:
    completed_at = datetime(2026, 9, 2, 12, tzinfo=UTC)
    payload = [
        {
            "type": "trade",
            "status": "complete",
            "transaction_id": "future",
            "roster_ids": [1, 2],
            "status_updated": int(completed_at.timestamp() * 1000),
            "adds": {"a": 1, "b": 2},
            "draft_picks": [],
            "waiver_budget": [],
        }
    ]
    result = normalize_sleeper_package_trades(
        json.dumps(payload),
        league_id="league-1",
        format_context_id="dynasty:12t:sf:0.5ppr",
        asset_id_by_sleeper_id={"a": "a", "b": "b"},
        canonical_pick_id_by_source_id=None,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert result.imported == 0
    assert result.skipped_future == 1
