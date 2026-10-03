from __future__ import annotations

import math

from fsffl.state.models import FrozenModel, LeagueState, Position
from fsffl.value.career_forward_intrinsic import CareerForwardIntrinsicShadowContract
from fsffl.value.career_forward_intrinsic import (
    CAREER_FORWARD_AGGREGATION,
    CAREER_FORWARD_RAW_QUANTITY,
)


DYNASTY_POSITION_ROOM_MODEL_VERSION = "analytics-dynasty-position-room-career-forward-v1"
DYNASTY_ROOM_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class DynastyPositionRoom(FrozenModel):
    """Team-position allocation of governed holistic career-forward raw authority."""

    team_id: str
    position: Position
    room_raw: float | None
    rostered_player_count: int | None
    league_rank: int | None
    strength_index: float | None
    team_count: int
    coverage_count: int
    evidence_complete: bool
    league_state_id: str | None
    model_version: str = DYNASTY_POSITION_ROOM_MODEL_VERSION


def build_dynasty_position_rooms(
    league_state: LeagueState,
    *,
    career_forward: CareerForwardIntrinsicShadowContract | None = None,
    evidence_state_id: str | None = None,
    positions: tuple[Position, ...] = DYNASTY_ROOM_POSITIONS,
) -> tuple[DynastyPositionRoom, ...]:
    """Aggregate raw career-forward references over canonical positional rooms.

    Each canonically rostered player contributes once at their actual position,
    irrespective of lineup or roster slot. Missing roster, player, position, or
    same-State Foundation 4 evidence is never imputed as zero. League rank/index
    are emitted only when every team's room for that position is complete.
    """

    teams = tuple(sorted(league_state.teams, key=lambda item: item.team_id))
    states = {item.team_id: item for item in league_state.team_states}
    players = {item.player_id: item for item in league_state.players}
    contract_valid = (
        career_forward is not None
        and career_forward.evaluation_season == league_state.league.season
        and career_forward.raw_quantity == CAREER_FORWARD_RAW_QUANTITY
        and career_forward.aggregation == CAREER_FORWARD_AGGREGATION
        and not career_forward.display_scaling_applied
        and not career_forward.market_inputs_used
        and evidence_state_id == league_state.state_id
        and bool(evidence_state_id)
    )
    estimates = (
        {row.player_id: row for row in career_forward.estimates}
        if contract_valid and career_forward is not None
        else {}
    )
    team_rosters: dict[str, tuple[tuple[str, Position], ...] | None] = {}
    for team in teams:
        team_state = states.get(team.team_id)
        if team_state is None:
            team_rosters[team.team_id] = None
            continue
        roster: list[tuple[str, Position]] = []
        for entry in team_state.roster:
            player = players.get(entry.player_id)
            if player is None:
                roster = []
                team_rosters[team.team_id] = None
                break
            roster.append((player.player_id, player.position))
        else:
            team_rosters[team.team_id] = tuple(roster)

    output: list[DynastyPositionRoom] = []
    for position in positions:
        partial: dict[str, tuple[int, float | None] | None] = {}
        for team in teams:
            roster = team_rosters.get(team.team_id)
            if roster is None:
                partial[team.team_id] = None
                continue
            members = tuple((pid, actual) for pid, actual in roster if actual == position)
            total = 0.0
            complete = contract_valid
            for player_id, actual_position in members:
                estimate = estimates.get(player_id)
                if (
                    estimate is None
                    or estimate.position != actual_position
                    or not math.isfinite(estimate.raw_career_forward_reference)
                ):
                    complete = False
                    break
                total += estimate.raw_career_forward_reference
            partial[team.team_id] = (len(members), total if complete else None)

        complete_totals = {
            team_id: row[1]
            for team_id, row in partial.items()
            if row is not None and row[1] is not None
        }
        league_complete = len(complete_totals) == len(teams) and bool(teams)
        average = (
            sum(complete_totals.values()) / len(complete_totals)
            if league_complete
            else None
        )
        ordered = sorted(complete_totals.items(), key=lambda item: (-item[1], item[0]))
        ranks: dict[str, int] = {}
        previous_value: float | None = None
        previous_rank = 0
        for index, (team_id, value) in enumerate(ordered, start=1):
            if previous_value is None or value != previous_value:
                previous_rank = index
                previous_value = value
            ranks[team_id] = previous_rank

        for team in teams:
            room = partial.get(team.team_id)
            room_raw = room[1] if room is not None else None
            strength_index = (
                (100.0 * room_raw / average)
                if league_complete and average is not None and average > 0 and room_raw is not None
                else None
            )
            output.append(
                DynastyPositionRoom(
                    team_id=team.team_id,
                    position=position,
                    room_raw=room_raw,
                    rostered_player_count=(room[0] if room is not None else None),
                    league_rank=(ranks.get(team.team_id) if league_complete else None),
                    strength_index=strength_index,
                    team_count=len(teams),
                    coverage_count=len(complete_totals),
                    evidence_complete=room is not None and room_raw is not None,
                    league_state_id=(evidence_state_id if room_raw is not None else None),
                )
            )
    return tuple(output)
