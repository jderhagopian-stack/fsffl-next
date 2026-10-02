from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.history import InMemorySnapshotStore
from fsffl.state.models import (
    DraftOrderPolicyEvidence,
    DraftOrderPolicyParameter,
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    PickOwnership,
    Player,
    PlayerState,
    PlayerStatus,
    PlayerWeekAvailability,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
    WeeklyAvailabilityStatus,
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


def test_empty_draft_order_policy_coordinate_preserves_legacy_state_identity() -> None:
    state = make_state()
    canonical = canonical_state_json(state)

    assert '"draft_order_policies"' not in canonical
    assert load_state_json(canonical).state_id == state.state_id


def test_governed_draft_order_policy_is_canonical_state_evidence() -> None:
    state = make_state()
    provenance = state.provenance[0]
    policy = DraftOrderPolicyEvidence(
        league_id=state.league.league_id,
        draft_season=2027,
        effective_at=NOW - timedelta(days=1),
        available_at=NOW,
        policy_id="league-bylaw",
        version="v1",
        mechanism="standard_record_h2h_pf_then_playoff_elimination_v1",
        description="explicit league draft-order rule",
        parameters=(
            DraftOrderPolicyParameter(name="placement_games_affect_order", value=False),
        ),
        provenance=provenance,
    )
    governed = state.model_copy(update={"draft_order_policies": (policy,)})

    assert governed.state_id != state.state_id
    assert '"draft_order_policies"' in canonical_state_json(governed)
    assert load_state_json(canonical_state_json(governed)) == governed

    wrong_league = policy.model_copy(update={"league_id": "other"})
    with pytest.raises(ValueError, match="must belong to the league"):
        LeagueState.model_validate(
            {
                **state.model_dump(),
                "draft_order_policies": (wrong_league,),
            }
        )


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

def test_optional_matchup_completion_coordinate_is_backward_compatible_but_authoritative_when_present() -> None:
    legacy = make_state()
    canonical = canonical_state_json(legacy)
    assert '"completed_through_week"' not in canonical

    completed = legacy.model_copy(update={"completed_through_week": 2})
    completed_canonical = canonical_state_json(completed)
    assert '"completed_through_week":2' in completed_canonical
    assert completed.state_id != legacy.state_id


def test_optional_weekly_availability_is_backward_compatible_but_authoritative_when_present() -> None:
    legacy = make_state()
    canonical = canonical_state_json(legacy)
    assert '"player_week_availability"' not in canonical

    availability = (
        PlayerWeekAvailability(
            player_id="player:1",
            week=1,
            status=WeeklyAvailabilityStatus.UNAVAILABLE,
            provenance=legacy.provenance[0],
        ),
        PlayerWeekAvailability(
            player_id="player:2",
            week=2,
            status=WeeklyAvailabilityStatus.AVAILABLE,
            provenance=legacy.provenance[0],
        ),
    )
    with_availability = legacy.model_copy(
        update={"player_week_availability": availability}
    )
    reversed_availability = legacy.model_copy(
        update={"player_week_availability": tuple(reversed(availability))}
    )

    serialized = canonical_state_json(with_availability)
    assert '"player_week_availability"' in serialized
    assert with_availability.state_id != legacy.state_id
    assert reversed_availability.state_id == with_availability.state_id


def test_weekly_availability_rejects_unknown_player_and_duplicate_player_week() -> None:
    state = make_state()
    with pytest.raises(ValueError, match="availability references unknown player"):
        LeagueState.model_validate(
            {
                **state.model_dump(),
                "player_week_availability": (
                    PlayerWeekAvailability(
                        player_id="unknown",
                        week=1,
                        status=WeeklyAvailabilityStatus.UNAVAILABLE,
                        provenance=state.provenance[0],
                    ),
                ),
            }
        )

    duplicate = PlayerWeekAvailability(
        player_id="player:1",
        week=1,
        status=WeeklyAvailabilityStatus.UNAVAILABLE,
        provenance=state.provenance[0],
    )
    with pytest.raises(ValueError, match="only one fact per player/week"):
        LeagueState.model_validate(
            {
                **state.model_dump(),
                "player_week_availability": (duplicate, duplicate),
            }
        )

