from __future__ import annotations

from datetime import datetime

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import LeagueState

from .lineup import marginal_lineup_impact, optimize_team_lineup
from .utility import RosterResilience


def build_roster_resilience(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    model_version: str = "next4-roster-resilience-v1",
) -> RosterResilience:
    """Describe roster fragility using real lineup substitutions.

    This function does not value players, apply market premiums, or decide whether
    fragility is strategically good/bad. It reports team-specific roster
    consequences for downstream utility.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    lineup = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
    )

    drops: list[float] = []
    for assignment in lineup.assignments:
        try:
            impact = marginal_lineup_impact(
                league_state,
                forecasts,
                team_id=team_id,
                player_id=assignment.player_id,
                as_of=as_of,
                horizon=horizon,
            )
        except ValueError as exc:
            # If removing a starter makes the lineup impossible to fill, the
            # roster is maximally exposed relative to this lineup and the full
            # starter contribution is a transparent lower-bound drop.
            if "cannot fill every required lineup slot" not in str(exc):
                raise
            drops.append(assignment.expected_points)
        else:
            drops.append(impact.marginal_expected_points)

    return RosterResilience(
        team_id=team_id,
        starter_count=len(lineup.assignments),
        bench_forecasted_count=len(lineup.bench_player_ids),
        unavailable_count=len(lineup.unavailable_player_ids),
        missing_forecast_count=len(lineup.missing_forecast_player_ids),
        largest_single_player_lineup_drop=max(drops, default=0.0),
        model_version=model_version,
    )
