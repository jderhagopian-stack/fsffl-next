from datetime import UTC, datetime

from fsffl.opportunity.waiver import WaiverMove, apply_waiver_move, enumerate_waiver_moves
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROV = Provenance(
    source="test",
    retrieved_at=AS_OF,
    effective_at=AS_OF,
    provider_ref=ProviderRef(provider="test", external_id="x"),
)


def _state(*, full: bool = True) -> LeagueState:
    league = League(
        league_id="l1",
        name="L",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=2,
            taxi_size=1,
            lineup=(),
            scoring=(),
        ),
    )
    teams = (
        Team(team_id="a", league_id="l1", display_name="A"),
        Team(team_id="b", league_id="l1", display_name="B"),
    )
    players = tuple(
        Player(player_id=pid, full_name=pid.upper(), position=Position.WR)
        for pid in ("p1", "p2", "taxi", "p3", "fa1", "fa2")
    )
    player_states = tuple(
        PlayerState(player_id=player.player_id, as_of=AS_OF, provenance=PROV)
        for player in players
    )
    roster_a = [RosterEntry(player_id="p1", slot=RosterSlot.BENCH)]
    if full:
        roster_a.append(RosterEntry(player_id="p2", slot=RosterSlot.BENCH))
    roster_a.append(RosterEntry(player_id="taxi", slot=RosterSlot.TAXI))
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=tuple(roster_a)),
            TeamState(team_id="b", roster=(RosterEntry(player_id="p3", slot=RosterSlot.BENCH),)),
        ),
        players=players,
        player_states=player_states,
    )


def test_full_active_roster_generates_add_drop_pairs_but_not_taxi_drop() -> None:
    universe = enumerate_waiver_moves(
        _state(full=True),
        focal_team_id="a",
        eligible_add_player_ids=("fa1", "fa2"),
    )

    assert universe.active_roster_full
    assert universe.add_pool_size == 2
    assert {(move.add_player_id, move.drop_player_id) for move in universe.moves} == {
        ("fa1", "p1"),
        ("fa1", "p2"),
        ("fa2", "p1"),
        ("fa2", "p2"),
    }


def test_open_active_roster_generates_add_without_drop() -> None:
    universe = enumerate_waiver_moves(
        _state(full=False),
        focal_team_id="a",
        eligible_add_player_ids=("fa1",),
    )

    assert not universe.active_roster_full
    assert universe.moves == (
        WaiverMove(focal_team_id="a", add_player_id="fa1"),
    )


def test_apply_waiver_move_is_immutable_and_adds_to_bench() -> None:
    state = _state(full=True)
    before_id = state.state_id
    scenario = apply_waiver_move(
        state,
        move=WaiverMove(focal_team_id="a", add_player_id="fa1", drop_player_id="p2"),
    )

    assert state.state_id == before_id
    original_a = next(team for team in state.team_states if team.team_id == "a")
    scenario_a = next(team for team in scenario.team_states if team.team_id == "a")
    assert {entry.player_id for entry in original_a.roster} == {"p1", "p2", "taxi"}
    assert {entry.player_id for entry in scenario_a.roster} == {"p1", "fa1", "taxi"}
    assert next(entry for entry in scenario_a.roster if entry.player_id == "fa1").slot == RosterSlot.BENCH


def test_apply_waiver_rejects_rostered_add_and_invalid_drop() -> None:
    state = _state(full=True)

    try:
        apply_waiver_move(
            state,
            move=WaiverMove(focal_team_id="a", add_player_id="p3", drop_player_id="p2"),
        )
    except ValueError as exc:
        assert "already rostered" in str(exc)
    else:
        raise AssertionError("expected rostered add rejection")

    try:
        apply_waiver_move(
            state,
            move=WaiverMove(focal_team_id="a", add_player_id="fa1", drop_player_id="taxi"),
        )
    except ValueError as exc:
        assert "active-roster player" in str(exc)
    else:
        raise AssertionError("expected taxi drop rejection")


def test_open_space_does_not_silently_throw_away_asset() -> None:
    state = _state(full=False)
    try:
        apply_waiver_move(
            state,
            move=WaiverMove(focal_team_id="a", add_player_id="fa1", drop_player_id="p1"),
        )
    except ValueError as exc:
        assert "open roster space" in str(exc)
    else:
        raise AssertionError("expected unnecessary drop rejection")
