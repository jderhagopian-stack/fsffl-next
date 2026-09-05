from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from fsffl.analytics.league import LeagueAnalyticsView, build_league_analytics_view
from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.team import TeamAnalyticsView, build_team_analytics_view
from fsffl.state.models import FrozenModel, LeagueState


class IntelligenceStage(StrEnum):
    STATE = "state"
    FORECAST = "forecast"
    VALUE = "value"
    TEAM_UTILITY = "team_utility"
    ANALYTICS = "analytics"
    TRADE_DECISION = "trade_decision"
    OPPORTUNITY = "opportunity"


class StageReadiness(StrEnum):
    READY = "ready"
    WAITING_FOR_INPUT = "waiting_for_input"
    NOT_CONFIGURED = "not_configured"


class IntelligenceStageStatus(FrozenModel):
    stage: IntelligenceStage
    readiness: StageReadiness
    message: str


class IntelligenceRuntimeStatus(FrozenModel):
    league_id: str
    league_state_id: str
    stages: tuple[IntelligenceStageStatus, ...]
    status_model_version: str = "next8-intelligence-status-v1"


def _state_only_context(
    league_state: LeagueState,
    *,
    generated_at: datetime | None = None,
) -> AnalyticsContext:
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    if generated < league_state.as_of:
        generated = league_state.as_of
    return AnalyticsContext(
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
                code="live_intelligence_not_enriched",
                message=(
                    "Canonical league state is loaded. Forecast, value, team-utility, "
                    "simulation, trade-decision, and opportunity evidence will attach "
                    "through the production runtime as their governed inputs become available."
                ),
                source_component="product-runtime",
            ),
        ),
    )


def build_state_only_team_views(
    league_state: LeagueState,
    *,
    generated_at: datetime | None = None,
) -> tuple[TeamAnalyticsView, ...]:
    """Build one shared-context NEXT-7 view per team without inventing evidence."""

    context = _state_only_context(league_state, generated_at=generated_at)
    return tuple(
        build_team_analytics_view(
            league_state,
            context=context,
            team_id=team.team_id,
        )
        for team in sorted(league_state.teams, key=lambda item: item.team_id)
    )


def build_state_only_league_view(
    league_state: LeagueState,
    *,
    generated_at: datetime | None = None,
) -> LeagueAnalyticsView:
    """Expose immediately available league analytics from canonical state only.

    This is a production orchestration bridge, not a valuation or forecasting
    fallback. Metrics that require downstream evidence remain explicitly missing.
    """

    team_views = build_state_only_team_views(league_state, generated_at=generated_at)
    context = team_views[0].context if team_views else _state_only_context(
        league_state,
        generated_at=generated_at,
    )
    return build_league_analytics_view(context=context, team_views=team_views)


def state_first_runtime_status(league_state: LeagueState) -> IntelligenceRuntimeStatus:
    return IntelligenceRuntimeStatus(
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        stages=(
            IntelligenceStageStatus(
                stage=IntelligenceStage.STATE,
                readiness=StageReadiness.READY,
                message="Canonical Sleeper league state is loaded and normalized.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.FORECAST,
                readiness=StageReadiness.WAITING_FOR_INPUT,
                message="Production live projection-provider evidence has not yet been attached.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.VALUE,
                readiness=StageReadiness.WAITING_FOR_INPUT,
                message="Value runtime is waiting for authoritative forecast/market inputs.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.TEAM_UTILITY,
                readiness=StageReadiness.WAITING_FOR_INPUT,
                message="Lineup, simulation, and team utility are waiting for forecast/value inputs.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.ANALYTICS,
                readiness=StageReadiness.READY,
                message="State-derived NEXT-7 league/team views are available; enriched metrics remain missing.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.TRADE_DECISION,
                readiness=StageReadiness.WAITING_FOR_INPUT,
                message="Trade Decision is waiting for enriched team/value evidence.",
            ),
            IntelligenceStageStatus(
                stage=IntelligenceStage.OPPORTUNITY,
                readiness=StageReadiness.WAITING_FOR_INPUT,
                message="Opportunity Engine is waiting for Trade Decision runtime evidence.",
            ),
        ),
    )
