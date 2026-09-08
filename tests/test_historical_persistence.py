from datetime import UTC, datetime, timedelta

import pytest

from fsffl.analytics.historical_persistence import (
    HistoricalArtifactIdentity,
    HistoricalArtifactKind,
    HistoricalInvalidationRequest,
    HistoricalSyncCheckpoint,
    InMemoryHistoricalReportRepository,
    InMemoryHistoricalSyncCheckpointRepository,
)
from fsffl.analytics.historical_trade import (
    EvidenceCompleteness,
    GradeResult,
    GradeStatus,
    HistoricalTradeReport,
    RetrospectiveOutcomeComponents,
)


def _report(transaction_id: str = "tx-1") -> HistoricalTradeReport:
    not_graded = GradeResult(
        status=GradeStatus.NOT_GRADED,
        confidence=0.5,
        reason="NOT GRADED — test fixture",
    )
    return HistoricalTradeReport(
        transaction_id=transaction_id,
        trade_date=datetime(2025, 9, 1, tzinfo=UTC),
        teams=("team-a", "team-b"),
        assets_by_team={"team-a": ("player-1",), "team-b": ("pick-1",)},
        point_in_time_grade=not_graded,
        point_in_time_evidence=(),
        final_outcome_grade=not_graded,
        outcome_components=RetrospectiveOutcomeComponents(
            evidence=EvidenceCompleteness(required_items=(), available_items=())
        ),
    )


def _derived_fingerprint(*, decision: str = "decision-v1", pick: str = "pick-v1") -> str:
    return f"decision={decision}|historical_pick_coordinate={pick}"


def test_persisted_artifact_identity_is_immutable() -> None:
    repo = InMemoryHistoricalReportRepository()
    identity = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint=_derived_fingerprint(),
    )
    report = _report()
    repo.put(identity, report)
    repo.put(identity, report)

    changed = report.model_copy(update={"model_version": "changed"})
    with pytest.raises(ValueError, match="immutable"):
        repo.put(identity, changed)


def test_dependency_invalidation_preserves_historical_facts() -> None:
    repo = InMemoryHistoricalReportRepository()
    report = _report()
    fact = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.TRANSACTION_FACT,
        artifact_version="fact-v1",
    )
    analysis = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint=_derived_fingerprint(),
    )
    repo.put(fact, report)
    repo.put(analysis, report)

    removed = repo.invalidate(
        HistoricalInvalidationRequest(
            league_id="league-1",
            dependency_component="historical_pick_coordinate",
            old_version="pick-v1",
            new_version="pick-v2",
        )
    )

    assert removed == (analysis,)
    assert repo.get(fact) == report
    assert repo.get(analysis) is None


def test_selective_invalidation_limits_recompute_scope() -> None:
    repo = InMemoryHistoricalReportRepository()
    for tx_id in ("tx-1", "tx-2"):
        identity = HistoricalArtifactIdentity(
            league_id="league-1",
            transaction_id=tx_id,
            artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
            artifact_version="report-v1",
            as_of=datetime(2026, 9, 7, tzinfo=UTC),
            dependency_fingerprint=_derived_fingerprint(),
        )
        repo.put(identity, _report(tx_id))

    removed = repo.invalidate(
        HistoricalInvalidationRequest(
            league_id="league-1",
            dependency_component="historical_pick_coordinate",
            old_version="pick-v1",
            new_version="pick-v2",
            affected_transaction_ids=("tx-2",),
        )
    )

    assert len(removed) == 1
    assert removed[0].transaction_id == "tx-2"


def test_dependency_invalidation_matches_component_and_version_exactly() -> None:
    repo = InMemoryHistoricalReportRepository()
    matching = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint=_derived_fingerprint(pick="pick-v1"),
    )
    newer = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-2",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint=_derived_fingerprint(pick="pick-v10"),
    )
    other_component = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-3",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint="decision=pick-v1|historical_pick_coordinate=pick-v2",
    )
    for identity in (matching, newer, other_component):
        repo.put(identity, _report(identity.transaction_id))

    removed = repo.invalidate(
        HistoricalInvalidationRequest(
            league_id="league-1",
            dependency_component="historical_pick_coordinate",
            old_version="pick-v1",
            new_version="pick-v2",
        )
    )

    assert removed == (matching,)
    assert repo.get(newer) is not None
    assert repo.get(other_component) is not None


def test_dependency_derived_artifacts_require_structured_fingerprint() -> None:
    with pytest.raises(ValueError, match="require a dependency_fingerprint"):
        HistoricalArtifactIdentity(
            league_id="league-1",
            transaction_id="tx-1",
            artifact_kind=HistoricalArtifactKind.POINT_IN_TIME_ANALYSIS,
            artifact_version="analysis-v1",
        )
    with pytest.raises(ValueError, match="component=version"):
        HistoricalArtifactIdentity(
            league_id="league-1",
            transaction_id="tx-1",
            artifact_kind=HistoricalArtifactKind.POINT_IN_TIME_ANALYSIS,
            artifact_version="analysis-v1",
            dependency_fingerprint="decision-v1|pick-v1",
        )


def test_repository_rejects_cross_transaction_report_identity() -> None:
    repo = InMemoryHistoricalReportRepository()
    identity = HistoricalArtifactIdentity(
        league_id="league-1",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version="report-v1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        dependency_fingerprint=_derived_fingerprint(),
    )
    with pytest.raises(ValueError, match="transaction_id must match"):
        repo.put(identity, _report("tx-2"))


def test_sync_checkpoint_only_moves_forward() -> None:
    first = HistoricalSyncCheckpoint(
        league_id="league-1",
        provider="sleeper",
        last_completed_at=datetime(2026, 9, 1, tzinfo=UTC),
        provider_cursor="cursor-1",
    )
    repo = InMemoryHistoricalSyncCheckpointRepository((first,))
    later = first.model_copy(
        update={
            "last_completed_at": first.last_completed_at + timedelta(days=1),
            "provider_cursor": "cursor-2",
        }
    )
    repo.put(later)
    assert repo.get("league-1", "sleeper") == later

    earlier = first.model_copy(
        update={"last_completed_at": first.last_completed_at - timedelta(days=1)}
    )
    with pytest.raises(ValueError, match="cannot move backward"):
        repo.put(earlier)


def test_refreshable_artifacts_require_as_of() -> None:
    with pytest.raises(ValueError, match="require a dependency_fingerprint"):
        HistoricalArtifactIdentity(
            league_id="league-1",
            transaction_id="tx-1",
            artifact_kind=HistoricalArtifactKind.RETROSPECTIVE_ANALYSIS,
            artifact_version="retro-v1",
        )
    with pytest.raises(ValueError, match="require an as_of"):
        HistoricalArtifactIdentity(
            league_id="league-1",
            transaction_id="tx-1",
            artifact_kind=HistoricalArtifactKind.RETROSPECTIVE_ANALYSIS,
            artifact_version="retro-v1",
            dependency_fingerprint=_derived_fingerprint(),
        )
