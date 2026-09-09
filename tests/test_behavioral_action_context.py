from datetime import UTC, datetime, timedelta

from fsffl.behavioral.action_context import reconstruct_behavioral_action_context
from fsffl.behavioral.models import BehavioralEventKind, OwnerBehaviorEvent
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
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)

EVENT_AT = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)
PRE_AT = EVENT_AT - timedelta(hours=2)
PROV = Provenance(source="test", retrieved_at=PRE_AT, effective_at=PRE_AT)


def _event() -> OwnerBehaviorEvent:
    return OwnerBehaviorEvent(
        event_id="evt-1",
        league_family_id="family-1",
        league_external_id="external-2026",
        season=2026,
        owner_id="owner-a",
        roster_id=1,
        occurred_at=EVENT_AT,
        kind=BehavioralEventKind.TRADE,
        source="test",
        source_version="test-v1",
    )


def _state(as_of: datetime, *, team_a_rb_count: int = 1) -> LeagueState:
    rules = LeagueRules(
        team_count=2,
        roster_size=8,
        taxi_size=1,
        ir_size=1,
        rookie_draft_rounds=3,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=2),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )
    league = League(league_id="league-1", name="Test", season=2026, rules=rules)
    teams = (
        Team(team_id="a", league_id="league-1", display_name="A"),
        Team(team_id="b", league_id="league-1", display_name="B"),
    )

    players = [
        Player(player_id="a-qb", full_name="A QB", position=Position.QB),
        Player(player_id="a-wr1", full_name="A WR1", position=Position.WR),
        Player(player_id="a-wr2", full_name="A WR2", position=Position.WR),
        Player(player_id="a-te", full_name="A TE", position=Position.TE),
        Player(player_id="a-ir-rb", full_name="A IR RB", position=Position.RB),
        Player(player_id="b-qb", full_name="B QB", position=Position.QB),
        Player(player_id="b-rb1", full_name="B RB1", position=Position.RB),
        Player(player_id="b-rb2", full_name="B RB2", position=Position.RB),
        Player(player_id="b-rb3", full_name="B RB3", position=Position.RB),
        Player(player_id="b-wr", full_name="B WR", position=Position.WR),
        Player(player_id="b-te", full_name="B TE", position=Position.TE),
    ]
    a_roster = [
        RosterEntry(player_id="a-qb", slot=RosterSlot.BENCH),
        RosterEntry(player_id="a-wr1", slot=RosterSlot.BENCH),
        RosterEntry(player_id="a-wr2", slot=RosterSlot.BENCH),
        RosterEntry(player_id="a-te", slot=RosterSlot.BENCH),
        RosterEntry(player_id="a-ir-rb", slot=RosterSlot.IR),
    ]
    for idx in range(team_a_rb_count):
        player_id = f"a-rb-{idx}"
        players.append(Player(player_id=player_id, full_name=f"A RB {idx}", position=Position.RB))
        a_roster.append(RosterEntry(player_id=player_id, slot=RosterSlot.BENCH))

    b_roster = (
        RosterEntry(player_id="b-qb", slot=RosterSlot.BENCH),
        RosterEntry(player_id="b-rb1", slot=RosterSlot.BENCH),
        RosterEntry(player_id="b-rb2", slot=RosterSlot.BENCH),
        RosterEntry(player_id="b-rb3", slot=RosterSlot.BENCH),
        RosterEntry(player_id="b-wr", slot=RosterSlot.BENCH),
        RosterEntry(player_id="b-te", slot=RosterSlot.BENCH),
    )
    player_states = tuple(
        PlayerState(player_id=player.player_id, as_of=as_of, provenance=PROV)
        for player in players
    )
    picks = (
        DraftPick(pick_id="a-2027-1", league_id="league-1", season=2027, round=1, original_team_id="a"),
        DraftPick(pick_id="b-2027-1", league_id="league-1", season=2027, round=1, original_team_id="b"),
    )
    ownership = (
        PickOwnership(pick_id="a-2027-1", owner_team_id="a"),
        PickOwnership(pick_id="b-2027-1", owner_team_id="a"),
    )
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=tuple(a_roster), faab_balance=77),
            TeamState(team_id="b", roster=b_roster, faab_balance=40),
        ),
        players=tuple(players),
        player_states=player_states,
        draft_picks=picks,
        pick_ownership=ownership,
        provenance=(PROV,),
    )


def test_reconstructs_strictly_pre_action_roster_and_league_context() -> None:
    state = _state(PRE_AT, team_a_rb_count=1)
    result = reconstruct_behavioral_action_context(
        _event(), league_id="league-1", team_id="a", snapshots=InMemorySnapshotStore((state,))
    )
    assert result.unavailable_reason is None
    context = result.context
    assert context is not None
    assert context.snapshot_as_of == PRE_AT
    assert context.snapshot_state_id == state.state_id
    assert context.faab_balance == 77
    assert context.owned_pick_count == 2
    assert context.flex_slot_count == 1
    assert context.superflex_slot_count == 1

    rb = next(row for row in context.positions if row.position == Position.RB)
    assert rb.rostered_count == 2  # one active RB plus one IR RB
    assert rb.active_rostered_count == 1
    assert rb.direct_starter_requirement == 2
    assert rb.league_average_rostered_count == 2.5
    assert rb.league_average_active_rostered_count == 2.0


def test_same_timestamp_snapshot_is_rejected_as_potential_post_action_state() -> None:
    result = reconstruct_behavioral_action_context(
        _event(),
        league_id="league-1",
        team_id="a",
        snapshots=InMemorySnapshotStore((_state(EVENT_AT, team_a_rb_count=3),)),
    )
    assert result.context is None
    assert result.unavailable_reason == "latest historical snapshot is not strictly pre-action"


def test_latest_pre_action_snapshot_is_used_without_future_leakage() -> None:
    earlier = _state(PRE_AT, team_a_rb_count=1)
    future = _state(EVENT_AT + timedelta(minutes=1), team_a_rb_count=4)
    result = reconstruct_behavioral_action_context(
        _event(),
        league_id="league-1",
        team_id="a",
        snapshots=InMemorySnapshotStore((earlier, future)),
    )
    assert result.context is not None
    rb = next(row for row in result.context.positions if row.position == Position.RB)
    assert rb.active_rostered_count == 1
    assert result.context.snapshot_state_id == earlier.state_id


def test_missing_historical_coverage_is_unavailable_not_neutral() -> None:
    result = reconstruct_behavioral_action_context(
        _event(), league_id="league-1", team_id="a", snapshots=InMemorySnapshotStore()
    )
    assert result.context is None
    assert "no league-state snapshot" in result.unavailable_reason
