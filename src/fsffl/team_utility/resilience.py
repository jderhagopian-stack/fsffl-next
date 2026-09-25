from __future__ import annotations

from datetime import datetime

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import LeagueState

from .lineup import optimize_team_lineup
from .utility import RosterResilience


def build_roster_resilience(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    model_version: str = "next4-roster-resilience-v2:argmax-driver-identity",
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

    # The baseline lineup above is authoritative for every marginal-loss
    # comparison. Re-running the same baseline inside marginal_lineup_impact for
    # every starter is mathematically redundant and was the dominant Market
    # pre-Simulation cost on the hosted beta. Compute only each exact
    # leave-one-starter-out lineup here; semantics are identical.
    drops: list[tuple[str, float]] = []
    for assignment in lineup.assignments:
        try:
            without = optimize_team_lineup(
                league_state,
                forecasts,
                team_id=team_id,
                as_of=as_of,
                horizon=horizon,
                excluded_player_ids=frozenset({assignment.player_id}),
            )
        except ValueError as exc:
            # If removing a starter makes the lineup impossible to fill, the
            # roster is maximally exposed relative to this lineup and the full
            # starter contribution is a transparent lower-bound drop.
            if "cannot fill every required lineup slot" not in str(exc):
                raise
            drop = assignment.expected_points
        else:
            drop = max(0.0, lineup.expected_points - without.expected_points)
        drops.append((assignment.player_id, drop))

    largest_drop = max((drop for _, drop in drops), default=0.0)
    driver_ids = tuple(
        sorted(
            player_id
            for player_id, drop in drops
            if abs(drop - largest_drop) <= 1e-9
        )
    )

    return RosterResilience(
        team_id=team_id,
        starter_count=len(lineup.assignments),
        bench_forecasted_count=len(lineup.bench_player_ids),
        unavailable_count=len(lineup.unavailable_player_ids),
        missing_forecast_count=len(lineup.missing_forecast_player_ids),
        largest_single_player_lineup_drop=largest_drop,
        largest_single_player_lineup_drop_player_ids=driver_ids,
        model_version=model_version,
    )
