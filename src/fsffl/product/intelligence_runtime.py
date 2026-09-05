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
    status_model_version: str = "next8-intelligence-status-v2"


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
        lineage=(ModelLineageEntry(component="state", model_version=league_state.schema_version),),
        warnings=(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.MISSING_EVIDENCE,
                code="live_intelligence_not_enriched",
                message=(
                    "Canonical league state is loaded. Forecast, value, team-utility, simulation, "
                    "trade-decision, and opportunity evidence attach through the production runtime."
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
    context = _state_only_context(league_state, generated_at=generated_at)
    return tuple(
        build_team_analytics_view(league_state, context=context, team_id=team.team_id)
        for team in sorted(league_state.teams, key=lambda item: item.team_id)
    )


def build_state_only_league_view(
    league_state: LeagueState,
    *,
    generated_at: datetime | None = None,
) -> LeagueAnalyticsView:
    team_views = build_state_only_team_views(league_state, generated_at=generated_at)
    context = team_views[0].context if team_views else _state_only_context(league_state, generated_at=generated_at)
    return build_league_analytics_view(context=context, team_views=team_views)


def state_first_runtime_status(
    league_state: LeagueState,
    *,
    forecast_ready: bool = False,
    forecast_message: str | None = None,
) -> IntelligenceRuntimeStatus:
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
                readiness=StageReadiness.READY if forecast_ready else StageReadiness.WAITING_FOR_INPUT,
                message=(
                    forecast_message
                    or (
                        "Authoritative multi-provider NEXT-2 forecast evidence is loaded."
                        if forecast_ready
                        else "Authoritative multi-provider live forecast evidence has not yet been attached."
                    )
                ),
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
                message=(
                    "NEXT-7 state and forecast views are available; value/simulation metrics remain missing."
                    if forecast_ready
                    else "State-derived NEXT-7 league/team views are available; enriched metrics remain missing."
                ),
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
