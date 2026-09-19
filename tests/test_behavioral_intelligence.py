from datetime import UTC, datetime

from fsffl.behavioral.models import (
    BehavioralAsset,
    BehavioralAssetKind,
    BehavioralEventKind,
    OwnerBehaviorEvent,
)
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.store import BehavioralIntelligenceStore


def _event(event_id: str, *, acquired: tuple[BehavioralAsset, ...], disposed: tuple[BehavioralAsset, ...]) -> OwnerBehaviorEvent:
    return OwnerBehaviorEvent(
        event_id=event_id,
        league_family_id="sleeper-family:oldest",
        league_external_id="current",
        season=2026,
        owner_id="owner-a",
        roster_id=1,
        occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
        kind=BehavioralEventKind.TRADE,
        acquired=acquired,
        disposed=disposed,
        counterparty_owner_ids=("owner-b",),
    )


def test_behavior_profile_is_descriptive_and_reconciles_trade_shape() -> None:
    player = BehavioralAsset(kind=BehavioralAssetKind.PLAYER, asset_ref="player:a", position="QB")
    pick = BehavioralAsset(kind=BehavioralAssetKind.PICK, asset_ref="pick:2027:1", pick_season=2027, pick_round=1)
    profiles = build_owner_behavior_profiles(
        [
            _event("e1", acquired=(player,), disposed=(player, pick)),
            _event("e2", acquired=(player, pick), disposed=(player,)),
            _event("e3", acquired=(player,), disposed=(player,)),
        ],
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    profile = profiles[0]
    assert profile.event_count == 3
    assert profile.trade_count == 3
    assert profile.consolidation_trade_count == 1
    assert profile.diversification_trade_count == 1
    assert profile.balanced_trade_count == 1
    assert profile.acquired_pick_count == 1
    assert profile.disposed_pick_count == 1
    assert profile.acquired_positions == {"QB": 3}
    assert profile.counterparty_trade_counts == {"owner-b": 3}


def test_behavior_store_persists_and_deduplicates_events(tmp_path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    player = BehavioralAsset(kind=BehavioralAssetKind.PLAYER, asset_ref="player:a", position="QB")
    event = _event("e1", acquired=(player,), disposed=(player,))
    assert store.put_events((event,)) == 1
    assert store.put_events((event,)) == 0
    assert store.load_events("sleeper-family:oldest") == (event,)

    profile = build_owner_behavior_profiles(
        (event,), as_of=datetime(2026, 9, 1, tzinfo=UTC)
    )[0]
    store.put_profiles((profile,))
    assert store.load_profiles("sleeper-family:oldest") == (profile,)

    store.mark_season_complete("sleeper-family:oldest", "oldest", 2025)
    assert store.season_is_complete("sleeper-family:oldest", "oldest")
    assert store.complete_league_ids() == frozenset({"oldest"})
