from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from fsffl.forecast.career import MultiYearForecastPoint
from fsffl.forecast.intrinsic_v1 import (
    INTRINSIC_V1_FORECAST_POLICY_VERSION,
    IntrinsicV1PlayerForecastPath,
    materialize_intrinsic_v1_forecast_path,
)
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.forecast.qb_career_state import QBCareerStateForecast
from fsffl.state.models import LeagueState, Position
from fsffl.value.models import AssetValueProfile

from .intrinsic_v2 import (
    INTRINSIC_VALUE_V2_VERSION,
    IntrinsicValueV2Estimate,
    as_intrinsic_dynasty_value_estimate,
    estimate_intrinsic_value_v2,
)


@dataclass(frozen=True)
class CurrentIntrinsicV2RuntimeResult:
    league_state_id: str
    estimates: tuple[IntrinsicValueV2Estimate, ...]
    profiles: tuple[AssetValueProfile, ...]
    roster_player_count: int
    valued_roster_player_count: int
    base_forecast_model_version: str
    forecast_policy_version: str = INTRINSIC_V1_FORECAST_POLICY_VERSION
    model_version: str = INTRINSIC_VALUE_V2_VERSION

    @property
    def coverage(self) -> float:
        if self.roster_player_count == 0:
            return 0.0
        return self.valued_roster_player_count / self.roster_player_count


def _season_fantasy_forecasts(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    selected: dict[str, ForecastObservation] = {}
    for observation in observations:
        if observation.horizon != ForecastHorizon.SEASON or observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        prior = selected.get(observation.player_id)
        if prior is None or observation.as_of > prior.as_of:
            selected[observation.player_id] = observation
    return selected


def build_current_intrinsic_values_v2(
    league_state: LeagueState,
    *,
    season_forecasts: tuple[ForecastObservation, ...],
    base_forecast_model_version: str,
    bounded_paths: Mapping[str, tuple[MultiYearForecastPoint, ...]] | None = None,
    qb_career_states: Mapping[str, QBCareerStateForecast] | None = None,
) -> CurrentIntrinsicV2RuntimeResult:
    """Build Fundamental Intrinsic without replacement, market, or team-context inputs."""

    by_player = _season_fantasy_forecasts(season_forecasts)
    player_by_id = {player.player_id: player for player in league_state.players}
    state_by_id = {state.player_id: state for state in league_state.player_states}
    paths: dict[str, IntrinsicV1PlayerForecastPath] = {}
    for player_id, observation in by_player.items():
        player = player_by_id.get(player_id)
        if player is None or player.position not in {Position.QB, Position.RB, Position.WR, Position.TE}:
            continue
        if observation.as_of > league_state.as_of:
            raise ValueError("intrinsic Forecast evidence cannot postdate canonical league state")
        paths[player_id] = materialize_intrinsic_v1_forecast_path(
            player_id=player_id,
            position=player.position,
            evaluation_as_of=observation.as_of,
            base_distribution=observation.distribution,
            base_forecast_model_version=base_forecast_model_version,
            bounded_path=(bounded_paths or {}).get(player_id),
            qb_career_state=(qb_career_states or {}).get(player_id),
        )

    roster_player_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
        if entry.player_id in player_by_id
        and player_by_id[entry.player_id].position in {Position.QB, Position.RB, Position.WR, Position.TE}
    }
    estimates: list[IntrinsicValueV2Estimate] = []
    profiles: list[AssetValueProfile] = []
    for player_id in sorted(paths):
        estimate = estimate_intrinsic_value_v2(
            player_path=paths[player_id],
            player_state=state_by_id.get(player_id),
        )
        estimates.append(estimate)
        typed = as_intrinsic_dynasty_value_estimate(estimate)
        profiles.append(
            AssetValueProfile(
                asset_id=player_id,
                asset_kind=typed.asset_kind,
                intrinsic_value=typed,
            )
        )

    valued_ids = roster_player_ids.intersection({estimate.player_id for estimate in estimates})
    return CurrentIntrinsicV2RuntimeResult(
        league_state_id=league_state.state_id,
        estimates=tuple(estimates),
        profiles=tuple(profiles),
        roster_player_count=len(roster_player_ids),
        valued_roster_player_count=len(valued_ids),
        base_forecast_model_version=base_forecast_model_version,
    )
