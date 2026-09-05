from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt

from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState

from .lineup import optimize_team_lineup
from .simulation import TeamScoringDistribution


class TeamUncertaintyMethod(StrEnum):
    INDEPENDENT_PLAYER_VARIANCE = "independent_player_variance"


def build_team_scoring_distribution(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    uncertainty_method: TeamUncertaintyMethod = TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE,
    model_version: str = "next4-team-scoring-v1",
) -> TeamScoringDistribution:
    """Build a team scoring distribution from the optimized starting lineup.

    Mean scoring is derived from authoritative NEXT-2 fantasy-point forecasts.
    The v1 uncertainty combination is explicitly independent-player variance,
    because NEXT-2 currently exposes marginal player distributions rather than
    a governed joint covariance model. This assumption is visible and replaceable;
    it is not a hidden correlation coefficient.
    """

    if uncertainty_method != TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE:
        raise ValueError("unsupported team uncertainty method")

    lineup = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
    )

    starter_ids = {assignment.player_id for assignment in lineup.assignments}
    latest: dict[str, ForecastObservation] = {}
    for observation in forecasts:
        if observation.player_id not in starter_ids:
            continue
        if observation.metric != ForecastMetric.FANTASY_POINTS or observation.horizon != horizon:
            continue
        if observation.as_of > as_of:
            continue
        current = latest.get(observation.player_id)
        if current is None or observation.as_of > current.as_of:
            latest[observation.player_id] = observation

    missing = starter_ids - set(latest)
    if missing:
        raise ValueError(f"optimized starter forecast evidence missing: {sorted(missing)}")

    mean_points = sum(latest[player_id].distribution.mean for player_id in starter_ids)
    variance = sum(latest[player_id].distribution.stddev**2 for player_id in starter_ids)

    return TeamScoringDistribution(
        team_id=team_id,
        mean_points=mean_points,
        stddev_points=sqrt(variance),
        model_version=f"{model_version}:{uncertainty_method.value}",
    )
