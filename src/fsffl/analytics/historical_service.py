from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .historical_trade import HistoricalTradeReport
from .models import AnalyticsContext, canonical_analytics_json


class HistoricalTradeQuery(FrozenModel):
    league_id: str
    transaction_id: str
    league_state_id: str
    schema_version: str = "1"
    report_model_version: str = "historical-trade-report-v1"

    @model_validator(mode="after")
    def validate_query(self) -> "HistoricalTradeQuery":
        values = (
            self.league_id,
            self.transaction_id,
            self.league_state_id,
            self.schema_version,
            self.report_model_version,
        )
        if any(not value.strip() for value in values):
            raise ValueError("historical trade query identifiers cannot be blank")
        return self


class HistoricalTradeCacheKey(FrozenModel):
    key: str
    transaction_id: str
    league_state_id: str
    schema_version: str
    report_model_version: str


def historical_trade_cache_key(
    query: HistoricalTradeQuery,
    *,
    context: AnalyticsContext,
) -> HistoricalTradeCacheKey:
    """Stable key for a precomputed historical report and its authority lineage."""

    if query.league_id != context.league_id:
        raise ValueError("historical trade query league must match context")
    if query.league_state_id != context.league_state_id:
        raise ValueError("historical trade query state must match context")

    lineage = tuple(sorted((item.component, item.model_version) for item in context.lineage))
    payload = {
        "league_id": query.league_id,
        "transaction_id": query.transaction_id,
        "league_state_id": query.league_state_id,
        "schema_version": query.schema_version,
        "report_model_version": query.report_model_version,
        "as_of": context.as_of.isoformat(),
        "lineage": lineage,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return HistoricalTradeCacheKey(
        key=f"historical-trade:{digest}",
        transaction_id=query.transaction_id,
        league_state_id=query.league_state_id,
        schema_version=query.schema_version,
        report_model_version=query.report_model_version,
    )


class ReadOnlyHistoricalTradeRepository(Protocol):
    def get(self, key: HistoricalTradeCacheKey) -> HistoricalTradeReport | None: ...


class InMemoryHistoricalTradeRepository:
    """Constructor-populated reference cache; retrieval exposes no write path."""

    def __init__(self, entries: dict[str, HistoricalTradeReport] | None = None) -> None:
        self._entries = dict(entries or {})

    def get(self, key: HistoricalTradeCacheKey) -> HistoricalTradeReport | None:
        return self._entries.get(key.key)


class HistoricalTradeResponse(FrozenModel):
    query: HistoricalTradeQuery
    cache_key: HistoricalTradeCacheKey
    context: AnalyticsContext
    payload_json: str

    @model_validator(mode="after")
    def validate_response(self) -> "HistoricalTradeResponse":
        if self.query.transaction_id != self.cache_key.transaction_id:
            raise ValueError("historical response transaction identity must match cache key")
        if self.query.league_state_id != self.context.league_state_id:
            raise ValueError("historical response state identity must match context")
        if not self.payload_json.strip():
            raise ValueError("historical response payload_json cannot be blank")
        return self


class HistoricalTradeNotFoundError(LookupError):
    pass


class ReadOnlyHistoricalTradeService:
    """Retrieve precomputed reports; never reconstruct, value, grade, or repair them."""

    def __init__(self, repository: ReadOnlyHistoricalTradeRepository) -> None:
        self._repository = repository

    def get(
        self,
        query: HistoricalTradeQuery,
        *,
        context: AnalyticsContext,
    ) -> HistoricalTradeResponse:
        key = historical_trade_cache_key(query, context=context)
        report = self._repository.get(key)
        if report is None:
            raise HistoricalTradeNotFoundError(key.key)
        if report.transaction_id != query.transaction_id:
            raise ValueError("cached historical report transaction identity must match query")
        if report.model_version != query.report_model_version:
            raise ValueError("cached historical report model version must match query")
        return HistoricalTradeResponse(
            query=query,
            cache_key=key,
            context=context,
            payload_json=canonical_analytics_json(report),
        )
