from datetime import UTC, datetime

from fsffl.analytics.dynasty_position_room import build_dynasty_position_rooms
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)


NOW = datetime(2026, 10, 3, tzinfo=UTC)


def _state() -> LeagueState:
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )
    teams = (
        Team(team_id="alpha", league_id="league", display_name="Alpha"),
        Team(team_id="beta", league_id="league", display_name="Beta"),
    )
    team_states = (
        TeamState(
            team_id="alpha",
            roster=(
                RosterEntry(player_id="a1", slot=RosterSlot.RB),
                RosterEntry(player_id="a2", slot=RosterSlot.BENCH),
                RosterEntry(player_id="a3", slot=RosterSlot.IR),
                RosterEntry(player_id="a4", slot=RosterSlot.TAXI),
            ),
        ),
        TeamState(
            team_id="beta",
            roster=(RosterEntry(player_id="b1", slot=RosterSlot.BENCH),),
        ),
    )
    return LeagueState(
        league=League(
            league_id="league",
            name="Room breadth fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=10,
                ir_size=2,
                taxi_size=2,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=NOW,
        teams=teams,
        team_states=team_states,
        players=tuple(
            Player(player_id=player_id, full_name=player_id, position=Position.RB)
            for player_id in ("a1", "a2", "a3", "a4", "b1")
        ),
        player_states=tuple(
            PlayerState(player_id=player_id, as_of=NOW, provenance=provenance)
            for player_id in ("a1", "a2", "a3", "a4", "b1")
        ),
    )


def test_dynasty_room_breadth_counts_every_rostered_player_once_and_ranks_by_count() -> None:
    rows = build_dynasty_position_rooms(_state(), positions=(Position.RB,))
    by_team = {row.team_id: row for row in rows}

    assert by_team["alpha"].rostered_player_count == 4
    assert by_team["alpha"].league_rank == 1
    assert by_team["beta"].rostered_player_count == 1
    assert by_team["beta"].league_rank == 2
    assert by_team["alpha"].model_version == "analytics-dynasty-position-room-breadth-v1"
