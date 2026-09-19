from __future__ import annotations

from datetime import datetime

from fsffl.state.draft_metric import HistoricalTeamDraftMetric, resolve_historical_draft_metrics
from fsffl.state.models import LeagueRules
from fsffl.team_utility.draft_order_metric import DraftMetricScenario, DraftMetricScenarioSet, TeamDraftMetric


def build_observed_draft_metric_scenarios(
    *,
    observations: tuple[HistoricalTeamDraftMetric, ...],
    league_id: str,
    draft_season: int,
    metric_id: str,
    as_of: datetime,
    league_rules: LeagueRules,
    model_version: str = "observed-draft-metric-v1",
) -> DraftMetricScenarioSet | None:
    """Convert complete observed metric facts into a deterministic scenario set.

    Returns None when the metric was not yet completely knowable for every team.
    It never fills missing teams from current data or simulations.
    """

    resolved = resolve_historical_draft_metrics(
        observations,
        league_id=league_id,
        draft_season=draft_season,
        metric_id=metric_id,
        as_of=as_of,
    )
    if len(resolved) != league_rules.team_count:
        return None
    team_ids = [item.team_id for item in resolved]
    if len(team_ids) != len(set(team_ids)):
        raise ValueError("resolved historical draft metrics must have unique team ids")

    provenance = "; ".join(sorted({item.provenance.source for item in resolved}))
    versions = "+".join(sorted({item.model_version for item in resolved}))
    return DraftMetricScenarioSet(
        league_id=league_id,
        draft_season=draft_season,
        as_of=max(item.available_at for item in resolved),
        scenarios=(
            DraftMetricScenario(
                probability=1.0,
                metrics=tuple(TeamDraftMetric(team_id=item.team_id, value=item.value) for item in resolved),
            ),
        ),
        metric_id=metric_id,
        model_version=f"{model_version}+inputs:{versions}",
        provenance=f"observed historical draft metric evidence; {provenance}",
    )
