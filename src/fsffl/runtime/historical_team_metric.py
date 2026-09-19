from __future__ import annotations

from fsffl.forecast.team_metric import TeamMetricForecastSet
from fsffl.state.models import LeagueRules
from fsffl.team_utility.draft_metric_simulation import (
    DraftMetricSimulationInput,
    TeamDraftMetricDistribution,
)


def build_draft_metric_simulation_input(
    *,
    forecasts: TeamMetricForecastSet,
    league_rules: LeagueRules,
    draft_season: int,
    simulation_count: int = 50_000,
    seed: int = 20260907,
) -> DraftMetricSimulationInput:
    """Translate Forecast-owned future team metrics into Simulation input.

    ``draft_season`` is explicit because the relationship between a competitive
    season and a later rookie draft is league-policy/configuration knowledge.
    Runtime does not assume that draft season equals target season + 1.
    """

    if len(forecasts.observations) != league_rules.team_count:
        raise ValueError("draft metric simulation requires one forecast for every league team")

    distributions = tuple(
        TeamDraftMetricDistribution(
            team_id=item.team_id,
            mean_value=item.distribution.mean,
            stddev_value=item.distribution.stddev,
            model_version=item.model_version,
        )
        for item in forecasts.observations
    )
    return DraftMetricSimulationInput(
        league_id=forecasts.league_id,
        draft_season=draft_season,
        as_of=forecasts.as_of,
        metric_id=forecasts.metric_id,
        distributions=distributions,
        simulation_count=simulation_count,
        seed=seed,
        model_version=f"future-team-metric-runtime-v1+{forecasts.model_version}",
        provenance=forecasts.provenance,
    )
