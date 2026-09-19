from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Protocol

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .league import LeagueAnalyticsView
from .models import AnalyticsContext, canonical_analytics_json
from .opportunity import OpportunityAnalyticsView, TradePartnerAnalyticsView
from .report import LeagueReportData
from .team import TeamAnalyticsView


class AnalyticsResourceKind(StrEnum):
    TEAM = "team"
    LEAGUE = "league"
    OPPORTUNITY = "opportunity"
    TRADE_PARTNERS = "trade_partners"
    REPORT = "report"


class AnalyticsQuery(FrozenModel):
    resource_kind: AnalyticsResourceKind
    league_id: str
    league_state_id: str
    team_id: str | None = None
    resource_id: str | None = None
    schema_version: str = "1"
    view_model_version: str

    @model_validator(mode="after")
    def validate_query(self) -> "AnalyticsQuery":
        if any(not value.strip() for value in (
            self.league_id,
            self.league_state_id,
            self.schema_version,
            self.view_model_version,
        )):
            raise ValueError("analytics query identifiers cannot be blank")
        if self.resource_kind in {
            AnalyticsResourceKind.TEAM,
            AnalyticsResourceKind.OPPORTUNITY,
            AnalyticsResourceKind.TRADE_PARTNERS,
        } and (self.team_id is None or not self.team_id.strip()):
            raise ValueError("team-scoped analytics query requires team_id")
        return self


class AnalyticsCacheKey(FrozenModel):
    key: str
    resource_kind: AnalyticsResourceKind
    league_state_id: str
    schema_version: str
    view_model_version: str


def analytics_cache_key(
    query: AnalyticsQuery,
    *,
    context: AnalyticsContext,
) -> AnalyticsCacheKey:
    """Create a stable content-addressable key from authoritative identity/lineage.

    `generated_at` and warnings are deliberately excluded. The cache key describes
    the underlying authoritative state/model identity, not when a view was rendered.
    """

    if query.league_id != context.league_id:
        raise ValueError("analytics query league must match context")
    if query.league_state_id != context.league_state_id:
        raise ValueError("analytics query state must match context")

    lineage = tuple(sorted((item.component, item.model_version) for item in context.lineage))
    payload = {
        "resource_kind": query.resource_kind.value,
        "league_id": query.league_id,
        "league_state_id": query.league_state_id,
        "team_id": query.team_id,
        "resource_id": query.resource_id,
        "schema_version": query.schema_version,
        "view_model_version": query.view_model_version,
        "as_of": context.as_of.isoformat(),
        "lineage": lineage,
    }
    import json

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return AnalyticsCacheKey(
        key=f"analytics:{digest}",
        resource_kind=query.resource_kind,
        league_state_id=query.league_state_id,
        schema_version=query.schema_version,
        view_model_version=query.view_model_version,
    )


AnalyticsView = (
    TeamAnalyticsView
    | LeagueAnalyticsView
    | OpportunityAnalyticsView
    | TradePartnerAnalyticsView
    | LeagueReportData
)


class ReadOnlyAnalyticsRepository(Protocol):
    """Storage boundary for already-built analytics views; intentionally read-only."""

    def get(self, key: AnalyticsCacheKey) -> AnalyticsView | None: ...


class InMemoryAnalyticsRepository:
    """Simple immutable-at-read cache useful for runtime/tests.

    Population is constructor-only so the NEXT-7 service itself exposes no mutation
    endpoint. A production cache can implement the same read-only repository protocol.
    """

    def __init__(self, entries: dict[str, AnalyticsView] | None = None) -> None:
        self._entries = dict(entries or {})

    def get(self, key: AnalyticsCacheKey) -> AnalyticsView | None:
        return self._entries.get(key.key)


class AnalyticsResponse(FrozenModel):
    query: AnalyticsQuery
    cache_key: AnalyticsCacheKey
    context: AnalyticsContext
    payload_json: str

    @model_validator(mode="after")
    def validate_response(self) -> "AnalyticsResponse":
        if self.query.resource_kind != self.cache_key.resource_kind:
            raise ValueError("analytics response query/cache resource kinds must match")
        if self.query.league_state_id != self.context.league_state_id:
            raise ValueError("analytics response state identity must match")
        if not self.payload_json.strip():
            raise ValueError("analytics response payload_json cannot be blank")
        return self


class AnalyticsNotFoundError(LookupError):
    pass


class ReadOnlyAnalyticsService:
    """Read-only retrieval service; contains no model or presentation repair logic."""

    def __init__(self, repository: ReadOnlyAnalyticsRepository) -> None:
        self._repository = repository

    def get(self, query: AnalyticsQuery, *, context: AnalyticsContext) -> AnalyticsResponse:
        key = analytics_cache_key(query, context=context)
        view = self._repository.get(key)
        if view is None:
            raise AnalyticsNotFoundError(key.key)
        view_context = getattr(view, "context", None)
        if view_context != context:
            raise ValueError("cached analytics view context must exactly match requested context")
        return AnalyticsResponse(
            query=query,
            cache_key=key,
            context=context,
            payload_json=canonical_analytics_json(view),
        )
