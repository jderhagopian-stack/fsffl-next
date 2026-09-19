from datetime import UTC, datetime

import pytest

from fsffl.analytics.historical_service import (
    HistoricalTradeNotFoundError,
    HistoricalTradeQuery,
    InMemoryHistoricalTradeRepository,
    ReadOnlyHistoricalTradeService,
    historical_trade_cache_key,
)
from fsffl.analytics.historical_trade import (
    EvidenceCompleteness,
    GradeResult,
    GradeStatus,
    HistoricalTradeReport,
    RetrospectiveOutcomeComponents,
)
from fsffl.analytics.models import AnalyticsContext, ModelLineageEntry


def context() -> AnalyticsContext:
    when = datetime(2026, 9, 7, tzinfo=UTC)
    return AnalyticsContext(
        schema_version="1",
        league_id="league-x",
        league_state_id="state-2026-09-07",
        as_of=when,
        generated_at=when,
        lineage=(
            ModelLineageEntry(component="state", model_version="state-v1"),
            ModelLineageEntry(component="decision", model_version="decision-v1"),
        ),
    )


def report() -> HistoricalTradeReport:
    trade_date = datetime(2025, 10, 1, tzinfo=UTC)
    not_graded = GradeResult(
        status=GradeStatus.NOT_GRADED,
        confidence=0.0,
        reason="NOT GRADED — fixture has no scoring policy",
    )
    missing = EvidenceCompleteness(required_items=("outcome",), available_items=())
    return HistoricalTradeReport(
        transaction_id="tx-1",
        trade_date=trade_date,
        teams=("team-a", "team-b"),
        assets_by_team={"team-a": ("player-a",), "team-b": ("player-b",)},
        point_in_time_grade=not_graded,
        point_in_time_evidence=(),
        final_outcome_grade=not_graded,
        outcome_components=RetrospectiveOutcomeComponents(evidence=missing),
    )


def query() -> HistoricalTradeQuery:
    return HistoricalTradeQuery(
        league_id="league-x",
        transaction_id="tx-1",
        league_state_id="state-2026-09-07",
    )


def test_cache_key_changes_when_authority_lineage_changes():
    original_context = context()
    original = historical_trade_cache_key(query(), context=original_context)
    changed_context = original_context.model_copy(
        update={
            "lineage": (
                ModelLineageEntry(component="state", model_version="state-v1"),
                ModelLineageEntry(component="decision", model_version="decision-v2"),
            )
        }
    )
    changed = historical_trade_cache_key(query(), context=changed_context)
    assert original.key != changed.key


def test_service_returns_only_precomputed_report():
    ctx = context()
    key = historical_trade_cache_key(query(), context=ctx)
    stored = report()
    service = ReadOnlyHistoricalTradeService(
        InMemoryHistoricalTradeRepository({key.key: stored})
    )

    response = service.get(query(), context=ctx)

    assert response.cache_key == key
    assert '"transaction_id":"tx-1"' in response.payload_json


def test_service_does_not_reconstruct_on_cache_miss():
    with pytest.raises(HistoricalTradeNotFoundError):
        ReadOnlyHistoricalTradeService(InMemoryHistoricalTradeRepository()).get(
            query(), context=context()
        )
