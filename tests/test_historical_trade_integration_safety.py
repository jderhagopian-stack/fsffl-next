from datetime import UTC, datetime

import pytest

from fsffl.analytics.historical_trade import (
    AssetAttribution,
    AssetLineageEvent,
    EvidenceCompleteness,
    GradeBand,
    GradeResult,
    GradeStatus,
    GovernedGradePolicy,
    HistoricalTradeReport,
    PointInTimeDecisionEvidence,
    RetrospectiveOutcomeComponents,
    RetrospectiveOutcomePolicy,
    grade_retrospective_outcome,
    trace_asset_lineage,
)


TRADE_DATE = datetime(2025, 9, 1, tzinfo=UTC)


def _not_graded() -> GradeResult:
    return GradeResult(
        status=GradeStatus.NOT_GRADED,
        confidence=1.0,
        reason="NOT GRADED — test fixture",
    )


def _components(*, complete: bool = True) -> RetrospectiveOutcomeComponents:
    required = ("asset", "production", "franchise")
    available = required if complete else ("asset", "production")
    gaps = () if complete else ("franchise",)
    return RetrospectiveOutcomeComponents(
        asset_value_score=80,
        production_score=70,
        franchise_outcome_score=60 if complete else None,
        evidence=EvidenceCompleteness(
            required_items=required,
            available_items=available,
            gaps=gaps,
        ),
    )


def _report(*, evidence: tuple[PointInTimeDecisionEvidence, ...] = (), teams=("a", "b")) -> HistoricalTradeReport:
    return HistoricalTradeReport(
        transaction_id="tx-1",
        trade_date=TRADE_DATE,
        teams=teams,
        assets_by_team={team_id: (f"asset-{team_id}",) for team_id in set(teams)},
        point_in_time_grade=_not_graded(),
        point_in_time_evidence=evidence,
        final_outcome_grade=_not_graded(),
        outcome_components=_components(),
    )


def _pit(*, transaction_id="tx-1", team_id="a", as_of=TRADE_DATE) -> PointInTimeDecisionEvidence:
    return PointInTimeDecisionEvidence(
        transaction_id=transaction_id,
        team_id=team_id,
        as_of=as_of,
        decision_model_version="decision-v1",
        evidence=EvidenceCompleteness(required_items=(), available_items=()),
    )


def test_historical_report_requires_unique_teams() -> None:
    with pytest.raises(ValueError, match="unique teams"):
        _report(teams=("a", "a"))


def test_historical_report_rejects_future_or_mismatched_point_in_time_evidence() -> None:
    with pytest.raises(ValueError, match="transaction_id"):
        _report(evidence=(_pit(transaction_id="tx-other"),))
    with pytest.raises(ValueError, match="participate"):
        _report(evidence=(_pit(team_id="c"),))
    with pytest.raises(ValueError, match="later than trade_date"):
        _report(evidence=(_pit(as_of=datetime(2025, 9, 2, tzinfo=UTC)),))


def test_retrospective_grade_preserves_weighting_policy_identity_and_context() -> None:
    outcome_policy = RetrospectiveOutcomePolicy(
        policy_id="retrospective-weights-v1",
        model_version="v1",
        provenance="tests",
        asset_value_weight=0.5,
        production_weight=0.3,
        franchise_outcome_weight=0.2,
    )
    grade_policy = GovernedGradePolicy(
        policy_id="letters-v1",
        model_version="v1",
        provenance="tests",
        bands=(
            GradeBand(minimum_score=0, letter="F"),
            GradeBand(minimum_score=60, letter="C"),
            GradeBand(minimum_score=75, letter="B"),
            GradeBand(minimum_score=90, letter="A"),
        ),
    )

    complete = grade_retrospective_outcome(
        _components(), outcome_policy=outcome_policy, grade_policy=grade_policy
    )
    assert complete.score_policy_id == "retrospective-weights-v1"
    assert complete.score_policy_version == "v1"

    incomplete = grade_retrospective_outcome(
        _components(complete=False), outcome_policy=outcome_policy, grade_policy=grade_policy
    )
    assert incomplete.status == GradeStatus.NOT_GRADED
    assert "retrospective outcome evidence" in incomplete.reason
    assert "point-in-time evidence" not in incomplete.reason
    assert incomplete.score_policy_id == "retrospective-weights-v1"


def test_lineage_cannot_follow_events_that_predate_asset_entry() -> None:
    events = (
        AssetLineageEvent(
            event_id="old-player-trade",
            occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
            from_asset_id="player:x",
            to_assets=(AssetAttribution(asset_id="player:old", weight=1.0),),
            description="Player X moved before the pick ever became Player X",
            provenance="test",
        ),
        AssetLineageEvent(
            event_id="pick-conversion",
            occurred_at=datetime(2027, 5, 1, tzinfo=UTC),
            from_asset_id="pick:2027:1:a",
            to_assets=(AssetAttribution(asset_id="player:x", weight=1.0),),
            description="Pick used to select Player X",
            provenance="test",
        ),
    )

    trace = trace_asset_lineage("pick:2027:1:a", events)
    assert not trace.ambiguous
    assert tuple(row.asset_id for row in trace.terminal_assets) == ("player:x",)


def test_root_acquisition_time_filters_preexisting_root_history() -> None:
    events = (
        AssetLineageEvent(
            event_id="before-acquisition",
            occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
            from_asset_id="player:a",
            to_assets=(AssetAttribution(asset_id="player:old", weight=1.0),),
            description="Pre-acquisition history",
            provenance="test",
        ),
        AssetLineageEvent(
            event_id="after-acquisition",
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            from_asset_id="player:a",
            to_assets=(AssetAttribution(asset_id="player:new", weight=1.0),),
            description="Post-acquisition history",
            provenance="test",
        ),
    )

    trace = trace_asset_lineage(
        "player:a", events, root_acquired_at=datetime(2025, 1, 1, tzinfo=UTC)
    )
    assert tuple(row.asset_id for row in trace.terminal_assets) == ("player:new",)
