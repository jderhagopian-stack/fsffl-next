from datetime import UTC, datetime

from fsffl.providers.sleeper import SleeperNormalizer, SleeperPayloadBundle
from fsffl.state.models import RosterSlot


AS_OF = datetime(2026, 9, 4, 14, 0, tzinfo=UTC)


def bundle() -> SleeperPayloadBundle:
    return SleeperPayloadBundle(
        league={
            "league_id": "123",
            "name": "Fixture League",
            "season": "2026",
            "settings": {
                "num_teams": 2,
                "roster_size": 4,
                "taxi_slots": 1,
                "reserve_slots": 1,
                "draft_rounds": 2,
                "waiver_budget": 100,
            },
            "roster_positions": ["QB", "RB", "FLEX", "BN"],
            "scoring_settings": {"rec": 0.5, "pass_yd": 0.04},
        },
        users=[
            {"user_id": "u1", "display_name": "Alpha"},
            {"user_id": "u2", "display_name": "Beta"},
        ],
        rosters=[
            {
                "roster_id": 1,
                "owner_id": "u1",
                "players": ["p1", "p2"],
                "starters": ["p1", "p2"],
                "settings": {"waiver_budget_used": 25},
            },
            {
                "roster_id": 2,
                "owner_id": "u2",
                "players": ["p3", "p4"],
                "starters": ["p3"],
                "taxi": ["p4"],
                "settings": {"waiver_budget_used": 10},
            },
        ],
        players={
            "p1": {"full_name": "Quarterback One", "position": "QB", "team": "AAA", "status": "active"},
            "p2": {"full_name": "Runner Two", "position": "RB", "team": "BBB", "status": "active"},
            "p3": {"full_name": "Quarterback Three", "position": "QB", "team": "CCC", "status": "active"},
            "p4": {"full_name": "Receiver Four", "position": "WR", "team": "DDD", "status": "active"},
        },
        traded_picks=[{"season": "2027", "round": 1, "roster_id": 1, "owner_id": 2}],
        retrieved_at=AS_OF,
    )


def test_normalizer_returns_provider_neutral_state() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)

    assert state.league.league_id == "sleeper:123"
    assert state.league.rules.team_count == 2
    assert len(state.teams) == 2
    assert len(state.players) == 4
    assert state.as_of == AS_OF

    alpha = next(item for item in state.team_states if item.team_id.endswith(":team:1"))
    assert alpha.faab_balance == 75
    slots = {entry.player_id: entry.slot for entry in alpha.roster}
    assert slots["sleeper:player:p1"] == RosterSlot.QB
    assert slots["sleeper:player:p2"] == RosterSlot.RB


def test_traded_pick_ownership_is_normalized() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)
    pick = next(
        entry
        for entry in state.pick_ownership
        if entry.pick_id == "sleeper:123:pick:2027:1:1"
    )
    assert pick.owner_team_id == "sleeper:123:team:2"


def test_taxi_assignment_is_preserved() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)
    beta = next(item for item in state.team_states if item.team_id.endswith(":team:2"))
    p4 = next(entry for entry in beta.roster if entry.player_id == "sleeper:player:p4")
    assert p4.slot == RosterSlot.TAXI
