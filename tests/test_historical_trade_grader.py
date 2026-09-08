from datetime import UTC, datetime

import pytest

from fsffl.analytics.historical_trade import (
    AssetAttribution,
    AssetLineageEvent,
    EvidenceCompleteness,
    GradeBand,
    GradeStatus,
    GovernedGradePolicy,
    PointInTimeDecisionEvidence,
    RetrospectiveOutcomeComponents,
    RetrospectiveOutcomePolicy,
    grade_point_in_time_decision,
    grade_retrospective_outcome,
    trace_asset_lineage,
)


AS_OF = datetime(2025, 8, 15, tzinfo=UTC)


def grade_policy() -> GovernedGradePolicy:
    return GovernedGradePolicy(
        policy_id="research-grade-policy",
        model_version="v1",
        provenance="tests:explicit-bands",
        bands=(
            GradeBand(minimum_score=0, letter="F"),
            GradeBand(minimum_score=60, letter="C"),
            GradeBand(minimum_score=75, letter="B"),
            GradeBand(minimum_score=90, letter="A"),
        ),
    )


def complete_evidence() -> EvidenceCompleteness:
    return EvidenceCompleteness(
        required_items=("state", "forecast", "value"),
        available_items=("state", "forecast", "value"),
    )


def test_point_in_time_grade_fails_closed_when_required_evidence_is_missing() -> None:
    evidence = PointInTimeDecisionEvidence(
        transaction_id="t1",
        team_id="a",
        as_of=AS_OF,
        decision_model_version="next5",
        decision_quality_score=92,
        evidence=EvidenceCompleteness(
            required_items=("state", "forecast", "value"),
            available_items=("state", "value"),
            gaps=("forecast",),
        ),
    )

    result = grade_point_in_time_decision(evidence, policy=grade_policy())

    assert result.status == GradeStatus.NOT_GRADED
    assert result.letter is None
    assert result.confidence == pytest.approx(2 / 3)
    assert "forecast" in result.reason


def test_point_in_time_grade_does_not_invent_decision_score() -> None:
    evidence = PointInTimeDecisionEvidence(
        transaction_id="t1",
        team_id="a",
        as_of=AS_OF,
        decision_model_version="next5",
        evidence=complete_evidence(),
    )

    result = grade_point_in_time_decision(evidence, policy=grade_policy())

    assert result.status == GradeStatus.NOT_GRADED
    assert "Decision has not emitted" in result.reason


def test_point_in_time_grade_translates_authoritative_score_only_through_policy() -> None:
    evidence = PointInTimeDecisionEvidence(
        transaction_id="t1",
        team_id="a",
        as_of=AS_OF,
        decision_model_version="next5",
        decision_quality_score=91,
        evidence=complete_evidence(),
    )

    result = grade_point_in_time_decision(evidence, policy=grade_policy())

    assert result.status == GradeStatus.GRADED
    assert result.letter == "A"
    assert result.score == 91
    assert result.policy_id == "research-grade-policy"


def test_grade_policy_has_no_implicit_threshold_floor() -> None:
    with pytest.raises(ValueError, match="floor band"):
        GovernedGradePolicy(
            policy_id="bad",
            model_version="v1",
            provenance="tests",
            bands=(GradeBand(minimum_score=50, letter="C"),),
        )


def test_retrospective_summary_requires_every_positively_weighted_component() -> None:
    components = RetrospectiveOutcomeComponents(
        asset_value_score=90,
        production_score=80,
        franchise_outcome_score=None,
        evidence=complete_evidence(),
    )
    outcome_policy = RetrospectiveOutcomePolicy(
        policy_id="outcome",
        model_version="v1",
        provenance="tests:explicit-weights",
        asset_value_weight=0.5,
        production_weight=0.3,
        franchise_outcome_weight=0.2,
    )

    result = grade_retrospective_outcome(
        components,
        outcome_policy=outcome_policy,
        grade_policy=grade_policy(),
    )

    assert result.status == GradeStatus.NOT_GRADED
    assert "components are unavailable" in result.reason


def test_retrospective_grade_uses_explicit_governed_weights() -> None:
    components = RetrospectiveOutcomeComponents(
        asset_value_score=100,
        production_score=80,
        franchise_outcome_score=60,
        evidence=complete_evidence(),
    )
    outcome_policy = RetrospectiveOutcomePolicy(
        policy_id="outcome",
        model_version="v1",
        provenance="tests:explicit-weights",
        asset_value_weight=0.5,
        production_weight=0.3,
        franchise_outcome_weight=0.2,
    )

    result = grade_retrospective_outcome(
        components,
        outcome_policy=outcome_policy,
        grade_policy=grade_policy(),
    )

    assert result.score == pytest.approx(86)
    assert result.letter == "B"


def test_pick_to_player_lineage_is_direct_and_preserved() -> None:
    event = AssetLineageEvent(
        event_id="draft-2027-1.05",
        occurred_at=datetime(2027, 5, 1, tzinfo=UTC),
        from_asset_id="pick:2027:1:a",
        to_assets=(AssetAttribution(asset_id="player:x", weight=1.0),),
        description="2027 first used to select Player X",
        provenance="sleeper:draft",
    )

    trace = trace_asset_lineage("pick:2027:1:a", (event,))

    assert not trace.ambiguous
    assert len(trace.terminal_assets) == 1
    assert trace.terminal_assets[0].asset_id == "player:x"
    assert trace.terminal_assets[0].attribution_weight == 1.0


def test_multi_asset_lineage_requires_explicit_attribution_that_sums_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        AssetLineageEvent(
            event_id="later-trade",
            occurred_at=datetime(2027, 9, 1, tzinfo=UTC),
            from_asset_id="player:a",
            to_assets=(
                AssetAttribution(asset_id="pick:2028:1:b", weight=0.7),
                AssetAttribution(asset_id="player:b", weight=0.2),
            ),
            description="Player A moved in a package",
            provenance="sleeper:transaction",
        )


def test_competing_lineage_events_fail_to_ambiguity_instead_of_choosing_one() -> None:
    events = (
        AssetLineageEvent(
            event_id="e1",
            occurred_at=datetime(2027, 1, 1, tzinfo=UTC),
            from_asset_id="player:a",
            to_assets=(AssetAttribution(asset_id="player:b", weight=1.0),),
            description="first candidate path",
            provenance="source:1",
        ),
        AssetLineageEvent(
            event_id="e2",
            occurred_at=datetime(2027, 2, 1, tzinfo=UTC),
            from_asset_id="player:a",
            to_assets=(AssetAttribution(asset_id="player:c", weight=1.0),),
            description="second candidate path",
            provenance="source:2",
        ),
    )

    trace = trace_asset_lineage("player:a", events)

    assert trace.ambiguous
    assert trace.terminal_assets[0].asset_id == "player:a"
    assert "ambiguous" in trace.notes[0]
