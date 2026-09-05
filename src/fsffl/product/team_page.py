from __future__ import annotations

from datetime import UTC, datetime

from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.team import TeamAnalyticsView, build_team_analytics_view
from fsffl.state.models import LeagueState


def build_state_only_team_view(
    league_state: LeagueState,
    *,
    team_id: str,
    generated_at: datetime | None = None,
) -> TeamAnalyticsView:
    """Expose canonical roster/picks before forecast/value runtime enrichment.

    Missing downstream evidence is explicitly warned about. Product code does not
    create substitute projections, values, or utility.
    """

    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    if generated < league_state.as_of:
        generated = league_state.as_of
    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=generated,
        lineage=(
            ModelLineageEntry(component="state", model_version=league_state.schema_version),
        ),
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
    return build_team_analytics_view(
        league_state,
        context=context,
        team_id=team_id,
    )
