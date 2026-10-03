from __future__ import annotations

from fsffl.state.models import FrozenModel, LeagueState, Position


DYNASTY_POSITION_ROOM_MODEL_VERSION = "analytics-dynasty-position-room-breadth-v1"
DYNASTY_ROOM_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class DynastyPositionRoom(FrozenModel):
    """Roster-breadth diagnostic; deliberately contains no player valuation."""

    team_id: str
    position: Position
    rostered_player_count: int | None
    league_rank: int | None
    team_count: int
    coverage_count: int
    model_version: str = DYNASTY_POSITION_ROOM_MODEL_VERSION


def build_dynasty_position_rooms(
    league_state: LeagueState,
    *,
    positions: tuple[Position, ...] = DYNASTY_ROOM_POSITIONS,
) -> tuple[DynastyPositionRoom, ...]:
    """Rank room breadth from canonical rosters, counting starters and depth once.

    Every canonical roster entry counts equally, including bench, IR and taxi.
    The measure is inventory breadth only: it does not grade player quality or
    reinterpret age, Forecast, Market, Current Intrinsic, or Long-Term Intrinsic.
    If even one team lacks canonical roster evidence, league-relative ranks and
    indices are withheld rather than treating missing evidence as an empty roster.
    """

    teams = tuple(sorted(league_state.teams, key=lambda item: item.team_id))
    states = {item.team_id: item for item in league_state.team_states}
    players = {item.player_id: item for item in league_state.players}
    roster_players: dict[str, tuple[Position, ...]] = {}
    for team in teams:
        team_state = states.get(team.team_id)
        if team_state is None:
            continue
        rostered = tuple(players.get(entry.player_id) for entry in team_state.roster)
        if any(player is None for player in rostered):
            continue
        roster_players[team.team_id] = tuple(
            player.position for player in rostered if player is not None
        )
    complete = len(teams) > 0 and len(roster_players) == len(teams)
    output: list[DynastyPositionRoom] = []
    for position in positions:
        counts = {
            team_id: sum(rostered_position == position for rostered_position in roster_positions)
            for team_id, roster_positions in roster_players.items()
        }
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ranks = (
            {team_id: rank for rank, (team_id, _) in enumerate(ordered, start=1)}
            if complete
            else {}
        )
        for team in teams:
            count = counts.get(team.team_id)
            output.append(
                DynastyPositionRoom(
                    team_id=team.team_id,
                    position=position,
                    rostered_player_count=count,
                    league_rank=ranks.get(team.team_id),
                    team_count=len(teams),
                    coverage_count=len(counts),
                )
            )
    return tuple(output)
