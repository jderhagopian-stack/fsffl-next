from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from fsffl.state.models import FrozenModel, LeagueState, RosterSlot, TeamState


class RosterLegalityStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    RESOLVED = "resolved"
    RESOLVED_WITH_INCOMPLETE_VALUE = "resolved_with_incomplete_value"


class MandatoryRosterCut(FrozenModel):
    player_id: str
    market_value: float | None = None
    was_projected_starter: bool = False


class TeamRosterLegalityResolution(FrozenModel):
    team_id: str
    active_roster_before_resolution: int
    roster_limit: int
    required_cut_count: int
    cuts: tuple[MandatoryRosterCut, ...] = ()
    cut_market_value_total: float | None = None
    status: RosterLegalityStatus
    model_version: str = "next5-mandatory-roster-cuts-v2"


@dataclass(frozen=True)
class ResolvedRosterState:
    league_state: LeagueState
    resolutions: tuple[TeamRosterLegalityResolution, ...]


def _active_entries(team_state: TeamState):
    return tuple(
        entry
        for entry in team_state.roster
        if entry.slot not in {RosterSlot.TAXI, RosterSlot.IR}
    )


def resolve_mandatory_roster_cuts(
    league_state: LeagueState,
    *,
    protected_player_ids_by_team: Mapping[str, frozenset[str]] | None = None,
    market_values: Mapping[str, float] | None = None,
) -> ResolvedRosterState:
    """Make post-transaction active rosters legal using upstream evidence.

    NEXT-5 owns the structural fact that an oversized active roster cannot survive
    a transaction unchanged. Team Utility may supply projected starter ids as a
    protected set; Value may supply authoritative market evidence. Decision does
    not import or recompute Forecast/lineup logic itself.

    Non-protected players are cut before protected players. Within each group the
    lowest known market Value is cut first. Unknown-value players are preserved
    behind known-value candidates where possible and any unknown cut cost remains
    explicit rather than being treated as zero.
    """

    values = market_values or {}
    protected = protected_player_ids_by_team or {}
    roster_limit = league_state.league.rules.roster_size
    team_state_map = {state.team_id: state for state in league_state.team_states}
    resolutions: list[TeamRosterLegalityResolution] = []

    for team in league_state.teams:
        team_state = team_state_map[team.team_id]
        active = _active_entries(team_state)
        overflow = max(0, len(active) - roster_limit)
        if overflow == 0:
            resolutions.append(
                TeamRosterLegalityResolution(
                    team_id=team.team_id,
                    active_roster_before_resolution=len(active),
                    roster_limit=roster_limit,
                    required_cut_count=0,
                    status=RosterLegalityStatus.NOT_REQUIRED,
                )
            )
            continue

        protected_ids = protected.get(team.team_id, frozenset())

        def cut_rank(entry) -> tuple[int, int, float, str]:
            value = values.get(entry.player_id)
            return (
                1 if entry.player_id in protected_ids else 0,
                1 if value is None else 0,
                float("inf") if value is None else float(value),
                entry.player_id,
            )

        ordered = sorted(active, key=cut_rank)
        chosen = tuple(ordered[:overflow])
        chosen_ids = {entry.player_id for entry in chosen}
        cuts = tuple(
            MandatoryRosterCut(
                player_id=entry.player_id,
                market_value=values.get(entry.player_id),
                was_projected_starter=entry.player_id in protected_ids,
            )
            for entry in chosen
        )
        known_values = [cut.market_value for cut in cuts if cut.market_value is not None]
        complete_cost = len(known_values) == len(cuts)
        cut_market_value_total = sum(known_values) if complete_cost else None
        team_state_map[team.team_id] = team_state.model_copy(
            update={
                "roster": tuple(
                    entry for entry in team_state.roster if entry.player_id not in chosen_ids
                )
            }
        )
        resolutions.append(
            TeamRosterLegalityResolution(
                team_id=team.team_id,
                active_roster_before_resolution=len(active),
                roster_limit=roster_limit,
                required_cut_count=overflow,
                cuts=cuts,
                cut_market_value_total=cut_market_value_total,
                status=(
                    RosterLegalityStatus.RESOLVED
                    if complete_cost
                    else RosterLegalityStatus.RESOLVED_WITH_INCOMPLETE_VALUE
                ),
            )
        )

    adjusted = league_state.model_copy(
        update={
            "team_states": tuple(team_state_map[team.team_id] for team in league_state.teams)
        }
    )
    adjusted = LeagueState.model_validate(adjusted.model_dump(mode="python"))
    return ResolvedRosterState(
        league_state=adjusted,
        resolutions=tuple(resolutions),
    )
