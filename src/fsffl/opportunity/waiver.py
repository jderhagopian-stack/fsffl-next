from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueState, RosterEntry, RosterSlot, TeamState


class WaiverMove(FrozenModel):
    focal_team_id: str
    add_player_id: str
    drop_player_id: str | None = None

    @model_validator(mode="after")
    def validate_move(self) -> "WaiverMove":
        if not self.focal_team_id.strip() or not self.add_player_id.strip():
            raise ValueError("waiver move identifiers cannot be blank")
        if self.drop_player_id is not None and not self.drop_player_id.strip():
            raise ValueError("drop_player_id cannot be blank")
        if self.drop_player_id == self.add_player_id:
            raise ValueError("waiver move cannot add and drop the same player")
        return self


class WaiverCandidateUniverse(FrozenModel):
    focal_team_id: str
    moves: tuple[WaiverMove, ...]
    active_roster_full: bool
    add_pool_size: int
    search_model_version: str = "next6-waiver-universe-v1"

    @model_validator(mode="after")
    def validate_universe(self) -> "WaiverCandidateUniverse":
        if not self.focal_team_id.strip() or not self.search_model_version.strip():
            raise ValueError("waiver universe identifiers cannot be blank")
        if self.add_pool_size < 0:
            raise ValueError("add_pool_size cannot be negative")
        identities = [(move.add_player_id, move.drop_player_id) for move in self.moves]
        if len(identities) != len(set(identities)):
            raise ValueError("waiver universe may not contain duplicate moves")
        return self


def _active_roster_entries(team_state: TeamState) -> tuple[RosterEntry, ...]:
    return tuple(
        entry
        for entry in team_state.roster
        if entry.slot not in {RosterSlot.TAXI, RosterSlot.IR}
    )


def enumerate_waiver_moves(
    league_state: LeagueState,
    *,
    focal_team_id: str,
    eligible_add_player_ids: tuple[str, ...] | None = None,
    search_model_version: str = "next6-waiver-universe-v1",
) -> WaiverCandidateUniverse:
    """Enumerate structurally legal add/drop candidates without valuation.

    When the active roster is full, every active-roster player is exposed as a
    possible drop candidate; NEXT-4/NEXT-3 downstream consequences decide whether
    any move is worthwhile. Taxi/IR players are not silently treated as active-roster
    cuts. An optional add pool may be supplied by a separate discovery stage.
    """

    if not search_model_version.strip():
        raise ValueError("search_model_version cannot be blank")

    team_states = {state.team_id: state for state in league_state.team_states}
    if focal_team_id not in team_states:
        raise ValueError("unknown focal team")
    focal_state = team_states[focal_team_id]

    rostered_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    known_player_ids = {player.player_id for player in league_state.players}
    free_agent_ids = known_player_ids - rostered_ids

    if eligible_add_player_ids is None:
        add_ids = tuple(sorted(free_agent_ids))
    else:
        requested = set(eligible_add_player_ids)
        unknown = requested - known_player_ids
        if unknown:
            raise ValueError("eligible add pool contains unknown player")
        unavailable = requested - free_agent_ids
        if unavailable:
            raise ValueError("eligible add pool contains rostered player")
        add_ids = tuple(sorted(requested))

    active_entries = _active_roster_entries(focal_state)
    active_roster_full = len(active_entries) >= league_state.league.rules.roster_size
    moves: list[WaiverMove] = []

    if active_roster_full:
        drop_ids = tuple(sorted(entry.player_id for entry in active_entries))
        for add_id in add_ids:
            for drop_id in drop_ids:
                moves.append(
                    WaiverMove(
                        focal_team_id=focal_team_id,
                        add_player_id=add_id,
                        drop_player_id=drop_id,
                    )
                )
    else:
        moves.extend(
            WaiverMove(focal_team_id=focal_team_id, add_player_id=add_id)
            for add_id in add_ids
        )

    return WaiverCandidateUniverse(
        focal_team_id=focal_team_id,
        moves=tuple(moves),
        active_roster_full=active_roster_full,
        add_pool_size=len(add_ids),
        search_model_version=search_model_version,
    )


def apply_waiver_move(
    league_state: LeagueState,
    *,
    move: WaiverMove,
) -> LeagueState:
    """Create an immutable canonical scenario for one waiver/add-drop move."""

    team_states = {state.team_id: state for state in league_state.team_states}
    if move.focal_team_id not in team_states:
        raise ValueError("unknown focal team")

    known_players = {player.player_id for player in league_state.players}
    if move.add_player_id not in known_players:
        raise ValueError("cannot add unknown player")

    rostered_by = {
        entry.player_id: team_state.team_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    if move.add_player_id in rostered_by:
        raise ValueError("waiver add player is already rostered")

    focal_state = team_states[move.focal_team_id]
    active_entries = _active_roster_entries(focal_state)
    active_roster_full = len(active_entries) >= league_state.league.rules.roster_size

    if active_roster_full and move.drop_player_id is None:
        raise ValueError("full active roster requires a drop")
    if not active_roster_full and move.drop_player_id is not None:
        # Explicit drops with open space are allowed only through a later roster-cut
        # workflow; waiver search should not throw away an asset unnecessarily.
        raise ValueError("waiver move with open roster space must not include a drop")

    roster = list(focal_state.roster)
    if move.drop_player_id is not None:
        active_ids = {entry.player_id for entry in active_entries}
        if move.drop_player_id not in active_ids:
            raise ValueError("waiver drop must be an active-roster player owned by focal team")
        roster = [entry for entry in roster if entry.player_id != move.drop_player_id]

    roster.append(RosterEntry(player_id=move.add_player_id, slot=RosterSlot.BENCH))
    updated_focal = focal_state.model_copy(update={"roster": tuple(roster)})
    updated_states = tuple(
        updated_focal if state.team_id == move.focal_team_id else state
        for state in league_state.team_states
    )
    return league_state.model_copy(update={"team_states": updated_states})
