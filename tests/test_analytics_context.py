from datetime import UTC, datetime, timedelta

from fsffl.analytics import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
    canonical_analytics_json,
)


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
GENERATED = AS_OF + timedelta(minutes=1)


def _context() -> AnalyticsContext:
    return AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="state-1",
        as_of=AS_OF,
        generated_at=GENERATED,
        lineage=(
            ModelLineageEntry(component="forecast", model_version="next2-v1"),
            ModelLineageEntry(component="value", model_version="next3-v1"),
        ),
        warnings=(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.UNKNOWN_ACCEPTANCE,
                code="acceptance-not-estimated",
                message="Acceptance probability has not been estimated.",
                source_component="trade_decision",
            ),
        ),
    )


def test_canonical_analytics_json_is_deterministic() -> None:
    first = canonical_analytics_json(_context())
    second = canonical_analytics_json(_context())
    assert first == second
    assert '"league_state_id":"state-1"' in first


def test_context_rejects_duplicate_lineage_components() -> None:
    try:
        AnalyticsContext(
            schema_version="1",
            league_id="l1",
            league_state_id="state-1",
            as_of=AS_OF,
            generated_at=GENERATED,
            lineage=(
                ModelLineageEntry(component="forecast", model_version="v1"),
                ModelLineageEntry(component="forecast", model_version="v2"),
            ),
        )
    except ValueError as exc:
        assert "one version per component" in str(exc)
    else:
        raise AssertionError("expected duplicate-lineage rejection")


def test_context_rejects_generation_before_evidence_cutoff() -> None:
    try:
        AnalyticsContext(
            schema_version="1",
            league_id="l1",
            league_state_id="state-1",
            as_of=AS_OF,
            generated_at=AS_OF - timedelta(seconds=1),
            lineage=(),
        )
    except ValueError as exc:
        assert "cannot precede" in str(exc)
    else:
        raise AssertionError("expected generated-at ordering rejection")
