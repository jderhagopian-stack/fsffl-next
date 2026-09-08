from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality import (
    DecisionQualityPolicy,
    DecisionQualityPolicyAuthority,
    DecisionQualityWeight,
)
from fsffl.trade_decision.decision_quality_calibration import (
    DecisionQualityCalibrationObservation,
    DecisionQualityCalibrationPanel,
    backtest_decision_quality_policies,
    promote_calibrated_policy,
)
from fsffl.value.calibration import DataRightsClass


def policy(policy_id: str, economic_weight: float, competitive_weight: float) -> DecisionQualityPolicy:
    return DecisionQualityPolicy(
        policy_id=policy_id,
        model_version="candidate-v1",
        provenance="tests:explicit-candidate",
        evidence_through=datetime(2025, 1, 1, tzinfo=UTC),
        weights=(
            DecisionQualityWeight(component_id="economic", weight=economic_weight),
            DecisionQualityWeight(component_id="competitive", weight=competitive_weight),
        ),
        authority=DecisionQualityPolicyAuthority.BOUNDED_PRIOR,
    )


def row(observation_id: str, observed_at: datetime, economic: float, competitive: float, target: float):
    return DecisionQualityCalibrationObservation(
        observation_id=observation_id,
        transaction_id=f"tx-{observation_id}",
        team_id="team-a",
        observed_at=observed_at,
        target_score=target,
        component_scores={"economic": economic, "competitive": competitive},
        source_id="research-review",
        target_definition="contemporaneous blinded decision-quality review",
        rights_class=DataRightsClass.PRIVATE_RETAINED,
        provenance="tests:research-review",
    )


def test_backtest_keeps_training_and_holdout_separate_and_selects_training_winner() -> None:
    panel = DecisionQualityCalibrationPanel(
        observations=(
            row("1", datetime(2025, 2, 1, tzinfo=UTC), 90, 20, 76),
            row("2", datetime(2025, 3, 1, tzinfo=UTC), 80, 30, 70),
            row("3", datetime(2025, 8, 1, tzinfo=UTC), 20, 90, 55),
        ),
        as_of=datetime(2025, 12, 31, tzinfo=UTC),
        panel_version="panel-v1",
    )
    economic_heavy = policy("economic-heavy", 0.8, 0.2)
    balanced = policy("balanced", 0.5, 0.5)

    result = backtest_decision_quality_policies(
        panel=panel,
        candidate_policies=(economic_heavy, balanced),
        holdout_start=datetime(2025, 7, 1, tzinfo=UTC),
    )

    assert result.best_training_policy_id == "economic-heavy"
    assert {item.sample_size for item in result.training_scores} == {2}
    assert {item.sample_size for item in result.holdout_scores} == {1}


def test_backtest_rejects_future_evidence_and_missing_policy_components() -> None:
    with pytest.raises(ValueError, match="future evidence"):
        DecisionQualityCalibrationPanel(
            observations=(
                row("1", datetime(2026, 1, 1, tzinfo=UTC), 50, 50, 50),
            ),
            as_of=datetime(2025, 12, 31, tzinfo=UTC),
            panel_version="panel-v1",
        )

    incomplete = row("2", datetime(2025, 2, 1, tzinfo=UTC), 50, 50, 50).model_copy(
        update={"component_scores": {"economic": 50}}
    )
    panel = DecisionQualityCalibrationPanel(
        observations=(
            incomplete,
            row("3", datetime(2025, 8, 1, tzinfo=UTC), 50, 50, 50),
        ),
        as_of=datetime(2025, 12, 31, tzinfo=UTC),
        panel_version="panel-v1",
    )
    with pytest.raises(ValueError, match="missing policy components"):
        backtest_decision_quality_policies(
            panel=panel,
            candidate_policies=(policy("balanced", 0.5, 0.5),),
            holdout_start=datetime(2025, 7, 1, tzinfo=UTC),
        )


def test_promotion_is_explicit_and_only_allows_recorded_training_winner() -> None:
    panel = DecisionQualityCalibrationPanel(
        observations=(
            row("1", datetime(2025, 2, 1, tzinfo=UTC), 90, 20, 76),
            row("2", datetime(2025, 8, 1, tzinfo=UTC), 30, 80, 50),
        ),
        as_of=datetime(2025, 12, 31, tzinfo=UTC),
        panel_version="panel-v1",
    )
    winner = policy("winner", 0.8, 0.2)
    loser = policy("loser", 0.5, 0.5)
    result = backtest_decision_quality_policies(
        panel=panel,
        candidate_policies=(winner, loser),
        holdout_start=datetime(2025, 7, 1, tzinfo=UTC),
    )

    promoted = promote_calibrated_policy(
        winner,
        calibration=result,
        provenance="calibration:panel-v1; explicit governance approval",
        model_version="calibrated-v1",
    )
    assert promoted.authority == DecisionQualityPolicyAuthority.CALIBRATED
    assert promoted.evidence_through == panel.as_of

    with pytest.raises(ValueError, match="training winner"):
        promote_calibrated_policy(
            loser,
            calibration=result,
            provenance="tests",
            model_version="calibrated-v1",
        )


def test_calibration_target_requires_explicit_non_hindsight_definition_metadata() -> None:
    with pytest.raises(ValueError, match="metadata cannot be blank"):
        DecisionQualityCalibrationObservation(
            observation_id="x",
            transaction_id="tx-x",
            team_id="team-a",
            observed_at=datetime(2025, 1, 1, tzinfo=UTC),
            target_score=50,
            component_scores={"economic": 50},
            source_id="research-review",
            target_definition=" ",
            rights_class=DataRightsClass.PRIVATE_RETAINED,
            provenance="tests",
        )
