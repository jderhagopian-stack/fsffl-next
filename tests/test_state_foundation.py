from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.history import InMemorySnapshotStore
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    PickOwnership,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.state.serialization import canonical_state_json, load_state_json


NOW = datetime(2026, 9, 4, 13, 0, tzinfo=UTC)


def make_state(as_of: datetime = NOW) -> LeagueState:
    league = League(
        league_id="league:test",
        name="Test League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=2,
            rookie_draft_rounds=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(ScoringRule(stat="pass_yd", points=0.04),),
        ),
    )
    teams = (
        Team(team_id="team:b", league_id=league.league_id, display_name="B"),
        Team(team_id="team:a", league_id=league.league_id, display_name="A"),
    )
    players = (
        Player(player_id="player:2", full_name="Player Two", position=Position.RB),
        Player(player_id="player:1", full_name="Player One", position=Position.QB),
    )
    provenance = Provenance(source="fixture", retrieved_at=as_of, effective_at=as_of)
    states = (
        PlayerState(player_id="player:2", as_of=as_of, status=PlayerStatus.ACTIVE, provenance=provenance),
        PlayerState(player_id="player:1", as_of=as_of, status=PlayerStatus.ACTIVE, provenance=provenance),
    )
    team_states = (
        TeamState(team_id="team:b", roster=(RosterEntry(player_id="player:2", slot=RosterSlot.BENCH),)),
        TeamState(team_id="team:a", roster=(RosterEntry(player_id="player:1", slot=RosterSlot.QB),)),
    )
    pick = DraftPick(
        pick_id="pick:2027:1:a",
        league_id=league.league_id,
        season=2027,
        round=1,
        original_team_id="team:a",
    )
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=teams,
        team_states=team_states,
        players=players,
        player_states=states,
        draft_picks=(pick,),
        pick_ownership=(PickOwnership(pick_id=pick.pick_id, owner_team_id="team:b"),),
        provenance=(provenance,),
    )


def test_round_trip_preserves_state_identity() -> None:
    state = make_state()
    canonical = canonical_state_json(state)
    restored = load_state_json(canonical)
    assert restored.state_id == state.state_id
    assert canonical_state_json(restored) == canonical


def test_state_identity_is_order_independent_for_canonical_collections() -> None:
    state = make_state()
    reordered = state.model_copy(
        update={
            "teams": tuple(reversed(state.teams)),
            "team_states": tuple(reversed(state.team_states)),
            "players": tuple(reversed(state.players)),
            "player_states": tuple(reversed(state.player_states)),
        }
    )
    assert reordered.state_id == state.state_id


def test_unknown_roster_player_is_rejected() -> None:
    state = make_state()
    bad_team_state = state.team_states[0].model_copy(
        update={"roster": (RosterEntry(player_id="unknown", slot=RosterSlot.BENCH),)}
    )
    with pytest.raises(ValueError, match="unknown player"):
        LeagueState(
            **{
                **state.model_dump(),
                "team_states": (bad_team_state, state.team_states[1]),
            }
        )


def test_snapshot_store_never_uses_future_state() -> None:
    old_state = make_state(NOW - timedelta(days=2))
    new_state = make_state(NOW)
    store = InMemorySnapshotStore((new_state, old_state))
    query_time = NOW - timedelta(days=1)
    result = store.latest_at_or_before("league:test", query_time)
    assert result is not None
    assert result.as_of == old_state.as_of
