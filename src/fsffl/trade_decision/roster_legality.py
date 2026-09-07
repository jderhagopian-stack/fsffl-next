from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState, RosterSlot, TeamState
from fsffl.team_utility import optimize_team_lineup


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
    model_version: str = "next5-mandatory-roster-cuts-v1"


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


def _projected_starters(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
) -> frozenset[str]:
    if not forecasts:
        return frozenset()
    try:
        lineup = optimize_team_lineup(
            league_state,
            forecasts,
            team_id=team_id,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
            allow_unfilled_slots=True,
            model_version="next5-mandatory-roster-cuts-v1:lineup",
        )
    except ValueError:
        return frozenset()
    return frozenset(assignment.player_id for assignment in lineup.assignments)


def resolve_mandatory_roster_cuts(
    league_state: LeagueState,
    *,
    forecasts: tuple[ForecastObservation, ...] = (),
    market_values: Mapping[str, float] | None = None,
) -> ResolvedRosterState:
    """Make post-transaction active rosters legal using explicit upstream evidence.

    Roster-size legality is structural Decision authority. When a transaction leaves
    an active roster above the canonical league limit, projected non-starters are
    cut before projected starters. Within each group, the lowest known authoritative
    market Value is cut first. Unknown-value players are preserved behind known-value
    candidates where possible and are surfaced as incomplete cut-cost evidence.

    This policy does not invent a package premium or utility coefficient. It simply
    prevents downstream Trade/Simulation analysis from treating impossible extra
    roster spots as free assets.
    """

    values = market_values or {}
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

        starter_ids = _projected_starters(
            league_state,
            forecasts,
            team_id=team.team_id,
        )

        def cut_rank(entry) -> tuple[int, int, float, str]:
            value = values.get(entry.player_id)
            return (
                1 if entry.player_id in starter_ids else 0,
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
                was_projected_starter=entry.player_id in starter_ids,
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
