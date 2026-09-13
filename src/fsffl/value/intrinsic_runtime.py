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

from .intrinsic_v1 import (
    INTRINSIC_VALUE_V1_VERSION,
    IntrinsicValueV1Estimate,
    as_intrinsic_dynasty_value_estimate,
    estimate_intrinsic_value_v1,
)


@dataclass(frozen=True)
class CurrentIntrinsicV1RuntimeResult:
    league_state_id: str
    estimates: tuple[IntrinsicValueV1Estimate, ...]
    profiles: tuple[AssetValueProfile, ...]
    roster_player_count: int
    valued_roster_player_count: int
    base_forecast_model_version: str
    forecast_policy_version: str = INTRINSIC_V1_FORECAST_POLICY_VERSION
    model_version: str = INTRINSIC_VALUE_V1_VERSION

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
        if observation.horizon != ForecastHorizon.SEASON:
            continue
        if observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        prior = selected.get(observation.player_id)
        if prior is None or observation.as_of > prior.as_of:
            selected[observation.player_id] = observation
    return selected


def build_current_intrinsic_values_v1(
    league_state: LeagueState,
    *,
    season_forecasts: tuple[ForecastObservation, ...],
    base_forecast_model_version: str,
    bounded_paths: Mapping[str, tuple[MultiYearForecastPoint, ...]] | None = None,
    qb_career_states: Mapping[str, QBCareerStateForecast] | None = None,
) -> CurrentIntrinsicV1RuntimeResult:
    """Build current FSFFL Intrinsic Value v1 from authoritative Forecast evidence.

    Value consumes Forecast-owned Year 1, optional bounded non-QB paths, and optional
    QB career-state expectations. It never estimates meaningful-starting-role
    probability itself. Missing/stale QB evidence is handled by Forecast's Intrinsic
    v1 materializer as conservative carry-forward.
    """

    by_player = _season_fantasy_forecasts(season_forecasts)
    player_by_id = {player.player_id: player for player in league_state.players}
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
    if not paths:
        return CurrentIntrinsicV1RuntimeResult(
            league_state_id=league_state.state_id,
            estimates=(),
            profiles=(),
            roster_player_count=len(roster_player_ids),
            valued_roster_player_count=0,
            base_forecast_model_version=base_forecast_model_version,
        )

    estimates: list[IntrinsicValueV1Estimate] = []
    profiles: list[AssetValueProfile] = []
    for player_id in sorted(paths):
        try:
            estimate = estimate_intrinsic_value_v1(
                player_path=paths[player_id],
                all_player_paths=paths,
                league_id=league_state.league.league_id,
                rules=league_state.league.rules,
            )
        except ValueError:
            # Replacement construction must fail closed for incomplete league-wide
            # position evidence rather than fabricate a replacement level.
            continue
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
    return CurrentIntrinsicV1RuntimeResult(
        league_state_id=league_state.state_id,
        estimates=tuple(estimates),
        profiles=tuple(profiles),
        roster_player_count=len(roster_player_ids),
        valued_roster_player_count=len(valued_ids),
        base_forecast_model_version=base_forecast_model_version,
    )
