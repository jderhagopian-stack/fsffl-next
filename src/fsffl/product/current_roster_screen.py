"""Read existing weekly scoring authority for a bounded pre-Simulation screen."""
from __future__ import annotations

from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import (
    build_bye_aware_weekly_team_scoring_panel,
    current_season_matchups_from_league_state,
)
from .simulation_forecasts import require_forward_simulation_evidence
from .simulation_runtime import simulation_forecast_dependency_fingerprint


def remaining_regular_points(runtime, changed_state, *, team_ids):
    """Compare scheduled weekly means; never estimate wins or rerun Simulation.

    Only the two legal changed rosters are scored. Baseline reuse requires exact
    State/Forecast proof and complete week coordinates. No retained request cache,
    provider acquisition, new mean/variance calculation or persistence owner.
    """
    state, evidence = runtime.league_state, runtime.forecast_evidence
    require_forward_simulation_evidence(state, evidence)
    if evidence.simulation_source_state_id != state.state_id:
        raise ValueError("Current roster points require exact source State")
    if changed_state.league.league_id != state.league.league_id:
        raise ValueError("Current roster screen requires the same league")
    _, remaining = current_season_matchups_from_league_state(state)
    scheduled = {team: tuple(sorted({m.week for m in remaining
        if team in (m.home_team_id, m.away_team_id)})) for team in team_ids}
    weeks = tuple(sorted({w for items in scheduled.values() for w in items}))
    if not weeks:
        raise ValueError("No remaining regular-season games for current roster screening")
    forecasts = evidence.simulation_forward_forecasts
    cutoff = evidence.simulation_evaluation_as_of
    baseline = runtime.simulation_analytics
    preparation = getattr(baseline, "scenario_preparation", None)
    before = {}
    if (preparation is not None and preparation.source_state_id == state.state_id
            and baseline.league_view.context.league_state_id == state.state_id
            and preparation.forecast_fingerprint == simulation_forecast_dependency_fingerprint(
                forecasts, forecast_model_version=evidence.model_version)):
        before = {(row.team_id, row.week): row.mean_points
                  for row in preparation.forward_weekly_scoring
                  if row.team_id in scheduled and row.week in scheduled[row.team_id]}
    needed = {(team, week) for team, items in scheduled.items() for week in items}
    reused = set(before) == needed
    if not reused:
        panel = build_bye_aware_weekly_team_scoring_panel(
            state, forecasts, team_ids=team_ids, weeks=weeks, as_of=cutoff,
            horizon=ForecastHorizon.REST_OF_SEASON)
        before = {(row.team_id, row.week): row.mean_points for row in panel}
    panel = build_bye_aware_weekly_team_scoring_panel(
        changed_state, forecasts, team_ids=team_ids, weeks=weeks, as_of=cutoff,
        horizon=ForecastHorizon.REST_OF_SEASON)
    after = {(row.team_id, row.week): row.mean_points for row in panel}
    if not needed <= before.keys() or not needed <= after.keys():
        raise ValueError("Current roster screen lacks complete scheduled weekly means")
    return {
        "deltas": {team: sum(after[(team, w)] - before[(team, w)] for w in items)
                   if items else None for team, items in scheduled.items()},
        "basis": "remaining_regular_season_weekly_mean",
        "unit": "fantasy_points",
        "weeks": weeks,
        "weeks_by_team": scheduled,
        "baseline_reused": reused,
    }
