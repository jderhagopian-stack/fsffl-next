from __future__ import annotations

from datetime import UTC, datetime

from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.team import TeamAnalyticsView, build_team_analytics_view
from fsffl.forecast.models import ForecastObservation
from fsffl.state.models import LeagueState


def _generated_at(league_state: LeagueState, generated_at: datetime | None) -> datetime:
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    return max(generated, league_state.as_of)


def build_state_only_team_view(
    league_state: LeagueState,
    *,
    team_id: str,
    generated_at: datetime | None = None,
) -> TeamAnalyticsView:
    """Expose canonical roster/picks before forecast/value runtime enrichment."""

    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=_generated_at(league_state, generated_at),
        lineage=(ModelLineageEntry(component="state", model_version=league_state.schema_version),),
        warnings=(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.MISSING_EVIDENCE,
                code="team_runtime_not_enriched",
                message=(
                    "Canonical roster/picks are loaded; forecast, value, optimized-lineup, "
                    "and team-utility runtime evidence has not yet been attached."
                ),
                source_component="product-runtime",
            ),
        ),
    )
    return build_team_analytics_view(league_state, context=context, team_id=team_id)


def build_forecast_team_view(
    league_state: LeagueState,
    *,
    team_id: str,
    forecasts: tuple[ForecastObservation, ...],
    forecast_model_version: str,
    generated_at: datetime | None = None,
) -> TeamAnalyticsView:
    """Expose authoritative NEXT-2 forecast evidence through the NEXT-7 team view.

    This remains intentionally partial: value, optimized lineup and team utility
    are still absent until their authoritative upstream runtime stages are attached.
    """

    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("team forecast evidence cannot postdate LeagueState")
    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=_generated_at(league_state, generated_at),
        lineage=(
            ModelLineageEntry(component="state", model_version=league_state.schema_version),
            ModelLineageEntry(component="forecast", model_version=forecast_model_version),
        ),
        warnings=(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.MISSING_EVIDENCE,
                code="team_value_utility_not_enriched",
                message=(
                    "Authoritative FSFFL forecasts are loaded; dynasty value, optimized lineup, "
                    "simulation and team-utility runtime evidence are still pending."
                ),
                source_component="product-runtime",
            ),
        ),
    )
    return build_team_analytics_view(
        league_state,
        context=context,
        team_id=team_id,
        forecasts=forecasts,
    )
