from fsffl.analytics.historical_conclusion import (
    HistoricalConclusionStatus,
    conclude_historical_trade,
    summarize_historical_conclusions,
)
from fsffl.analytics.historical_grade_envelope import HistoricalGradeEnvelope
from fsffl.runtime.historical_trade_readiness import HistoricalTradeValuationReadiness
from fsffl.trade_decision.decision import BilateralDecisionShape, SideDecisionShape
from fsffl.trade_decision.historical_robustness import (
    HistoricalDecisionRobustness,
    HistoricalDecisionRobustnessStatus,
)


def readiness(transaction_id: str, eligible: bool = True) -> HistoricalTradeValuationReadiness:
    return HistoricalTradeValuationReadiness(
        transaction_id=transaction_id,
        assets=(),
        complete=eligible,
        grade_eligible=eligible,
    )


def robustness(transaction_id: str, status: HistoricalDecisionRobustnessStatus) -> HistoricalDecisionRobustness:
    if status == HistoricalDecisionRobustnessStatus.ROBUST:
        a = (SideDecisionShape.UNIFORM_GAIN,)
        b = (SideDecisionShape.UNIFORM_LOSS,)
        bilateral = (BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,)
    elif status == HistoricalDecisionRobustnessStatus.SENSITIVE:
        a = (SideDecisionShape.UNIFORM_GAIN, SideDecisionShape.UNIFORM_LOSS)
        b = (SideDecisionShape.UNIFORM_LOSS, SideDecisionShape.UNIFORM_GAIN)
        bilateral = (
            BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
            BilateralDecisionShape.SIDE_B_GAIN_SIDE_A_LOSS,
        )
    else:
        a = (SideDecisionShape.INCOMPLETE,)
        b = (SideDecisionShape.INCOMPLETE,)
        bilateral = (BilateralDecisionShape.MIXED_OR_INCOMPLETE,)
    return HistoricalDecisionRobustness(
        proposal_id=transaction_id,
        status=status,
        scenario_ids=tuple(f"s{i}" for i in range(len(a))),
        side_a_team_id="A",
        side_b_team_id="B",
        side_a_shapes=a,
        side_b_shapes=b,
        bilateral_shapes=bilateral,
        model_versions=("decision-v1",),
        reason="test",
    )


def envelope(*letters: str) -> HistoricalGradeEnvelope:
    return HistoricalGradeEnvelope(
        weight_family_id="weights",
        weight_family_version="v1",
        score_lower=60,
        center_score_lower=65,
        center_score_upper=70,
        score_upper=75,
        center_possible_letters=letters,
        possible_letters=letters,
        letter_invariant=len(letters) == 1,
        grade_policy_id="grades",
        grade_policy_version="v1",
    )


def test_final_status_progression_is_fail_closed() -> None:
    assert conclude_historical_trade(readiness("blocked", False)).status == HistoricalConclusionStatus.EVIDENCE_INCOMPLETE
    assert conclude_historical_trade(readiness("ready")).status == HistoricalConclusionStatus.READY_FOR_DECISION
    assert conclude_historical_trade(
        readiness("sensitive"), robustness=robustness("sensitive", HistoricalDecisionRobustnessStatus.SENSITIVE)
    ).status == HistoricalConclusionStatus.DECISION_SENSITIVE
    assert conclude_historical_trade(
        readiness("robust"), robustness=robustness("robust", HistoricalDecisionRobustnessStatus.ROBUST)
    ).status == HistoricalConclusionStatus.READY_FOR_GRADE_ENVELOPE


def test_robust_and_sensitive_grade_are_distinguished() -> None:
    robust = conclude_historical_trade(
        readiness("t1"),
        robustness=robustness("t1", HistoricalDecisionRobustnessStatus.ROBUST),
        grade_envelope=envelope("B"),
    )
    sensitive = conclude_historical_trade(
        readiness("t2"),
        robustness=robustness("t2", HistoricalDecisionRobustnessStatus.ROBUST),
        grade_envelope=envelope("B", "C"),
    )
    assert robust.status == HistoricalConclusionStatus.ROBUST_GRADE
    assert robust.possible_letters == ("B",)
    assert sensitive.status == HistoricalConclusionStatus.GRADE_SENSITIVE
    assert sensitive.possible_letters == ("B", "C")


def test_batch_reports_one_final_status_per_trade() -> None:
    rows = (readiness("a", False), readiness("b"), readiness("c"))
    summary = summarize_historical_conclusions(
        rows,
        robustness_by_transaction_id={
            "c": robustness("c", HistoricalDecisionRobustnessStatus.ROBUST),
        },
        grade_envelope_by_transaction_id={"c": envelope("A")},
    )
    assert summary.trade_count == 3
    assert {row.transaction_id: row.status for row in summary.rows} == {
        "a": HistoricalConclusionStatus.EVIDENCE_INCOMPLETE,
        "b": HistoricalConclusionStatus.READY_FOR_DECISION,
        "c": HistoricalConclusionStatus.ROBUST_GRADE,
    }
