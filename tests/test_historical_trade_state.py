from datetime import UTC, datetime

from fsffl.state.historical_trade import normalize_sleeper_completed_trade
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset, Provenance


def provenance() -> Provenance:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    return Provenance(source="fixture", retrieved_at=now, effective_at=now)


def base_trade():
    return {
        "type": "trade",
        "status": "complete",
        "transaction_id": "t1",
        "status_updated": 1_735_689_600_000,
        "roster_ids": [1, 2],
        "adds": {"101": 2, "202": 1},
        "drops": {"101": 1, "202": 2},
        "draft_picks": [],
        "waiver_budget": [],
        "creator": "user-a",
    }


def test_normalizes_player_for_player_without_value_inference():
    result = normalize_sleeper_completed_trade(
        base_trade(),
        league_id="league-x",
        roster_to_team={1: "team-a", 2: "team-b"},
        player_id_by_sleeper_id={"101": "player-a", "202": "player-b"},
        pick_id_by_key={},
        provenance=provenance(),
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        creator_team_by_user_id={"user-a": "team-a"},
    )
    assert result.record is not None
    assert result.record.creator_team_id == "team-a"
    legs = {leg.team_id: leg for leg in result.record.legs}
    assert legs["team-a"].sends == (PlayerAsset(player_id="player-a"),)
    assert legs["team-b"].sends == (PlayerAsset(player_id="player-b"),)


def test_preserves_picks_and_faab_as_assets():
    row = base_trade()
    row["draft_picks"] = [
        {
            "season": 2027,
            "round": 1,
            "roster_id": 1,
            "previous_owner_id": 1,
            "owner_id": 2,
        }
    ]
    row["waiver_budget"] = [{"sender": 2, "receiver": 1, "amount": 7}]
    result = normalize_sleeper_completed_trade(
        row,
        league_id="league-x",
        roster_to_team={1: "team-a", 2: "team-b"},
        player_id_by_sleeper_id={"101": "player-a", "202": "player-b"},
        pick_id_by_key={(2027, 1, "team-a"): "pick-2027-a-1"},
        provenance=provenance(),
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
    )
    assert result.record is not None
    legs = {leg.team_id: leg for leg in result.record.legs}
    assert PickAsset(pick_id="pick-2027-a-1") in legs["team-a"].sends
    assert FaabAsset(amount=7) in legs["team-b"].sends


def test_unmapped_asset_fails_entire_trade_closed():
    row = base_trade()
    result = normalize_sleeper_completed_trade(
        row,
        league_id="league-x",
        roster_to_team={1: "team-a", 2: "team-b"},
        player_id_by_sleeper_id={"101": "player-a"},
        pick_id_by_key={},
        provenance=provenance(),
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
    )
    assert result.record is None
    assert result.skipped_reason == "trade contains assets that cannot be reconstructed defensibly"
    assert result.unmapped_assets == ("player:202",)


def test_future_trade_is_not_reconstructed_at_earlier_cutoff():
    row = base_trade()
    result = normalize_sleeper_completed_trade(
        row,
        league_id="league-x",
        roster_to_team={1: "team-a", 2: "team-b"},
        player_id_by_sleeper_id={"101": "player-a", "202": "player-b"},
        pick_id_by_key={},
        provenance=provenance(),
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    )
    assert result.record is None
    assert result.skipped_reason == "trade occurred after requested as_of"
