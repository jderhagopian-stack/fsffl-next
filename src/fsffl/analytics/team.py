from __future__ import annotations

from collections.abc import Mapping

from pydantic import model_validator

from fsffl.forecast.models import ForecastObservation
from fsffl.state.models import DraftPick, FrozenModel, LeagueState, Position, RosterSlot
from fsffl.team_utility.models import OptimizedTeamLineup
from fsffl.team_utility.utility import OwnerStrategicPosture, TeamUtilityVector
from fsffl.value.models import AssetValueProfile

from .models import AnalyticsContext


class PlayerAnalyticsRow(FrozenModel):
    player_id: str
    full_name: str
    position: Position
    roster_slot: RosterSlot
    age_years: float | None = None
    projected_starter: bool = False
    projected_lineup_slot: RosterSlot | None = None
    forecasts: tuple[ForecastObservation, ...] = ()
    value_profile: AssetValueProfile | None = None

    @model_validator(mode="after")
    def validate_row(self) -> "PlayerAnalyticsRow":
        if not self.player_id.strip() or not self.full_name.strip():
            raise ValueError("player analytics identifiers cannot be blank")
        if self.projected_starter != (self.projected_lineup_slot is not None):
            raise ValueError("projected starter flag and lineup slot must agree")
        if any(observation.player_id != self.player_id for observation in self.forecasts):
            raise ValueError("player analytics forecasts must match player")
        if self.value_profile is not None and self.value_profile.asset_id != self.player_id:
            raise ValueError("player analytics value profile must match player")
        return self


class DraftPickAnalyticsRow(FrozenModel):
    pick: DraftPick
    value_profile: AssetValueProfile | None = None

    @model_validator(mode="after")
    def validate_pick(self) -> "DraftPickAnalyticsRow":
        if self.value_profile is not None and self.value_profile.asset_id != self.pick.pick_id:
            raise ValueError("pick analytics value profile must match pick")
        return self


class TeamAnalyticsView(FrozenModel):
    context: AnalyticsContext
    team_id: str
    display_name: str
    players: tuple[PlayerAnalyticsRow, ...]
    draft_picks: tuple[DraftPickAnalyticsRow, ...] = ()
    optimized_lineup: OptimizedTeamLineup | None = None
    utility: TeamUtilityVector | None = None
    owner_posture: OwnerStrategicPosture | None = None
    view_model_version: str = "next7-team-view-v1"

    @model_validator(mode="after")
    def validate_view(self) -> "TeamAnalyticsView":
        if not self.team_id.strip() or not self.display_name.strip() or not self.view_model_version.strip():
            raise ValueError("team analytics identifiers cannot be blank")
        if self.optimized_lineup is not None and self.optimized_lineup.team_id != self.team_id:
            raise ValueError("optimized lineup must match analytics team")
        if self.utility is not None and self.utility.team_id != self.team_id:
            raise ValueError("team utility must match analytics team")
        if len({row.player_id for row in self.players}) != len(self.players):
            raise ValueError("team analytics players must be unique")
        return self


def build_team_analytics_view(
    league_state: LeagueState,
    *,
    context: AnalyticsContext,
    team_id: str,
    forecasts: tuple[ForecastObservation, ...] = (),
    value_profiles: Mapping[str, AssetValueProfile] | None = None,
    optimized_lineup: OptimizedTeamLineup | None = None,
    utility: TeamUtilityVector | None = None,
    owner_posture: OwnerStrategicPosture | None = None,
    view_model_version: str = "next7-team-view-v1",
) -> TeamAnalyticsView:
    """Join authoritative team evidence into a read-only analytics view."""

    if context.league_id != league_state.league.league_id:
        raise ValueError("analytics context league must match LeagueState")
    if context.league_state_id != league_state.state_id:
        raise ValueError("analytics context state id must match LeagueState")
    if context.as_of != league_state.as_of:
        raise ValueError("analytics context as_of must match LeagueState")

    team = next((item for item in league_state.teams if item.team_id == team_id), None)
    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team is None or team_state is None:
        raise ValueError("unknown team_id")

    if optimized_lineup is not None:
        if optimized_lineup.team_id != team_id:
            raise ValueError("optimized lineup must describe team")
        if optimized_lineup.as_of > context.as_of:
            raise ValueError("optimized lineup cannot postdate analytics context")
    if utility is not None:
        if utility.team_id != team_id:
            raise ValueError("team utility must describe team")
        if utility.as_of > context.as_of:
            raise ValueError("team utility cannot postdate analytics context")

    profiles = value_profiles or {}
    players_by_id = {player.player_id: player for player in league_state.players}
    states_by_id = {state.player_id: state for state in league_state.player_states}
    starter_slot_by_player = {
        assignment.player_id: assignment.slot
        for assignment in optimized_lineup.assignments
    } if optimized_lineup is not None else {}

    forecasts_by_player: dict[str, list[ForecastObservation]] = {}
    for observation in forecasts:
        if observation.as_of > context.as_of:
            continue
        forecasts_by_player.setdefault(observation.player_id, []).append(observation)

    player_rows: list[PlayerAnalyticsRow] = []
    for entry in team_state.roster:
        player = players_by_id[entry.player_id]
        player_state = states_by_id[player.player_id]
        observations = tuple(
            sorted(
                forecasts_by_player.get(player.player_id, ()),
                key=lambda item: (
                    item.horizon.value,
                    item.metric.value,
                    item.period_start,
                    item.model_version,
                ),
            )
        )
        projected_slot = starter_slot_by_player.get(player.player_id)
        player_rows.append(
            PlayerAnalyticsRow(
                player_id=player.player_id,
                full_name=player.full_name,
                position=player.position,
                roster_slot=entry.slot,
                age_years=player_state.age_years,
                projected_starter=projected_slot is not None,
                projected_lineup_slot=projected_slot,
                forecasts=observations,
                value_profile=profiles.get(player.player_id),
            )
        )

    owned_pick_ids = {
        ownership.pick_id
        for ownership in league_state.pick_ownership
        if ownership.owner_team_id == team_id
    }
    picks_by_id = {pick.pick_id: pick for pick in league_state.draft_picks}
    pick_rows = tuple(
        DraftPickAnalyticsRow(
            pick=picks_by_id[pick_id],
            value_profile=profiles.get(pick_id),
        )
        for pick_id in sorted(
            owned_pick_ids,
            key=lambda pid: (
                picks_by_id[pid].season,
                picks_by_id[pid].round,
                pid,
            ),
        )
    )

    slot_order = {slot: index for index, slot in enumerate(RosterSlot)}
    player_rows.sort(
        key=lambda row: (
            0 if row.projected_starter else 1,
            slot_order[row.projected_lineup_slot or row.roster_slot],
            row.position.value,
            row.full_name,
            row.player_id,
        )
    )

    return TeamAnalyticsView(
        context=context,
        team_id=team_id,
        display_name=team.display_name,
        players=tuple(player_rows),
        draft_picks=pick_rows,
        optimized_lineup=optimized_lineup,
        utility=utility,
        owner_posture=owner_posture,
        view_model_version=view_model_version,
    )
