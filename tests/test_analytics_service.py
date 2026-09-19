from datetime import UTC, datetime, timedelta

from fsffl.analytics.league import LeagueAnalyticsView
from fsffl.analytics.models import AnalyticsContext, ModelLineageEntry
from fsffl.analytics.service import (
    AnalyticsNotFoundError,
    AnalyticsQuery,
    AnalyticsResourceKind,
    InMemoryAnalyticsRepository,
    ReadOnlyAnalyticsService,
    analytics_cache_key,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _context(*, generated_offset: int = 1) -> AnalyticsContext:
    return AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="state-1",
        as_of=AS_OF,
        generated_at=AS_OF + timedelta(seconds=generated_offset),
        lineage=(ModelLineageEntry(component="opportunity", model_version="next6-v1"),),
    )


def _query() -> AnalyticsQuery:
    return AnalyticsQuery(
        resource_kind=AnalyticsResourceKind.LEAGUE,
        league_id="l1",
        league_state_id="state-1",
        schema_version="1",
        view_model_version="next7-league-view-v1",
    )


def test_cache_key_ignores_render_time_but_preserves_authoritative_identity() -> None:
    query = _query()
    first = analytics_cache_key(query, context=_context(generated_offset=1))
    second = analytics_cache_key(query, context=_context(generated_offset=99))
    assert first == second

    changed = AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="state-1",
        as_of=AS_OF,
        generated_at=AS_OF + timedelta(seconds=1),
        lineage=(ModelLineageEntry(component="opportunity", model_version="next6-v2"),),
    )
    assert analytics_cache_key(query, context=changed).key != first.key


def test_team_scoped_query_requires_team_id() -> None:
    try:
        AnalyticsQuery(
            resource_kind=AnalyticsResourceKind.TEAM,
            league_id="l1",
            league_state_id="state-1",
            view_model_version="next7-team-view-v1",
        )
    except ValueError as exc:
        assert "requires team_id" in str(exc)
    else:
        raise AssertionError("expected team-id validation failure")


def test_read_only_service_retrieves_exact_context_and_serializes_view() -> None:
    context = _context()
    query = _query()
    key = analytics_cache_key(query, context=context)
    view = LeagueAnalyticsView(context=context, teams=())
    service = ReadOnlyAnalyticsService(InMemoryAnalyticsRepository({key.key: view}))

    response = service.get(query, context=context)
    assert response.cache_key == key
    assert '"teams":[]' in response.payload_json
    assert not hasattr(service, "create")
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")


def test_read_only_service_fails_closed_on_missing_view() -> None:
    service = ReadOnlyAnalyticsService(InMemoryAnalyticsRepository())
    try:
        service.get(_query(), context=_context())
    except AnalyticsNotFoundError:
        pass
    else:
        raise AssertionError("expected analytics not-found error")
