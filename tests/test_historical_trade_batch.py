from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_trade_batch import (
    HistoricalTradeProgressStatus,
    classify_historical_trade_progress,
    summarize_historical_trade_progress,
)
from fsffl.runtime.historical_trade_readiness import (
    HistoricalAssetEvidence,
    HistoricalAssetEvidenceStatus,
    HistoricalEvidenceMode,
    assess_historical_trade_valuation_readiness,
    historical_trade_asset_key,
)
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import PickAsset, PlayerAsset, Provenance
from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    Direction,
    SideDecisionShape,
    SideDirectionalAssessment,
)
from fsffl.trade_decision.historical_robustness import (
    HistoricalDecisionRobustness,
    HistoricalDecisionRobustnessStatus,
)


def provenance() -> Provenance:
    at = datetime(2024, 1, 1, tzinfo=UTC)
    return Provenance(source="test", retrieved_at=at, effective_at=at)


def record(transaction_id: str) -> HistoricalTradeRecord:
    return HistoricalTradeRecord(
        transaction_id=transaction_id,
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id=f"{transaction_id}-pick"),)),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id=f"{transaction_id}-player"),)),
        ),
        provenance=provenance(),
    )


def complete_readiness(transaction_id: str, *, mode: HistoricalEvidenceMode):
    row = record(transaction_id)
    evidence = []
    for leg in row.legs:
        for ordinal, asset in enumerate(leg.sends):
            key = historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset)
            evidence.append(
                HistoricalAssetEvidence(
                    asset_key=key,
                    status=HistoricalAssetEvidenceStatus.AVAILABLE,
                    reason="usable PIT evidence",
                    model_version="value-v1",
                    mode=mode if isinstance(asset, PickAsset) else HistoricalEvidenceMode.EXACT,
                )
            )
    return assess_historical_trade_valuation_readiness(row, evidence=tuple(evidence))


def missing_readiness(transaction_id: str):
    row = record(transaction_id)
    player = row.legs[1].sends[0]
    player_key = historical_trade_asset_key(team_id="B", ordinal=0, asset=player)
    evidence = (
        HistoricalAssetEvidence(
            asset_key=player_key,
            status=HistoricalAssetEvidenceStatus.AVAILABLE,
            reason="player value available",
            model_version="value-v1",
            mode=HistoricalEvidenceMode.EXACT,
        ),
    )
    return assess_historical_trade_valuation_readiness(row, evidence=evidence)


def side(team_id: str, shape: SideDecisionShape) -> SideDirectionalAssessment:
    direction = Direction.IMPROVES if shape == SideDecisionShape.UNIFORM_GAIN else Direction.WORSENS
    return SideDirectionalAssessment(
        team_id=team_id,
        expected_wins=direction,
        playoff_probability=direction,
        first_place_probability=direction,
        asset_portfolio_mean=direction,
        largest_single_player_lineup_drop=direction,
        bench_forecasted_count=direction,
        unavailable_count=direction,
        missing_forecast_count=direction,
        shape=shape,
    )


def robustness(transaction_id: str, status: HistoricalDecisionRobustnessStatus) -> HistoricalDecisionRobustness:
    if status == HistoricalDecisionRobustnessStatus.ROBUST:
        a_shapes = (SideDecisionShape.UNIFORM_GAIN, SideDecisionShape.UNIFORM_GAIN)
        b_shapes = (SideDecisionShape.UNIFORM_LOSS, SideDecisionShape.UNIFORM_LOSS)
        bilateral = (
            BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
            BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
        )
    elif status == HistoricalDecisionRobustnessStatus.SENSITIVE:
        a_shapes = (SideDecisionShape.UNIFORM_GAIN, SideDecisionShape.UNIFORM_LOSS)
        b_shapes = (SideDecisionShape.UNIFORM_LOSS, SideDecisionShape.UNIFORM_GAIN)
        bilateral = (
            BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
            BilateralDecisionShape.SIDE_B_GAIN_SIDE_A_LOSS,
        )
    else:
        a_shapes = (SideDecisionShape.INCOMPLETE,)
        b_shapes = (SideDecisionShape.UNIFORM_LOSS,)
        bilateral = (BilateralDecisionShape.MIXED_OR_INCOMPLETE,)
    return HistoricalDecisionRobustness(
        proposal_id=transaction_id,
        status=status,
        scenario_ids=tuple(f"s{i}" for i in range(len(a_shapes))),
        side_a_team_id="A",
        side_b_team_id="B",
        side_a_shapes=a_shapes,
        side_b_shapes=b_shapes,
        bilateral_shapes=bilateral,
        model_versions=("decision-v1",),
        reason="test robustness",
    )


def test_complete_probabilistic_trade_is_ready_for_decision_before_robustness() -> None:
    readiness = complete_readiness("t1", mode=HistoricalEvidenceMode.PROBABILISTIC)
    progress = classify_historical_trade_progress(readiness)
    assert progress.status == HistoricalTradeProgressStatus.READY_FOR_DECISION
    assert progress.probabilistic_asset_count == 1


def test_robust_uncertain_trade_advances_to_grade_envelope_not_directly_to_robust_grade() -> None:
    readiness = complete_readiness("t2", mode=HistoricalEvidenceMode.SENSITIVITY_ONLY)
    progress = classify_historical_trade_progress(
        readiness,
        robustness=robustness("t2", HistoricalDecisionRobustnessStatus.ROBUST),
    )
    assert progress.status == HistoricalTradeProgressStatus.READY_FOR_GRADE_ENVELOPE
    assert progress.sensitivity_only_asset_count == 1


def test_sensitive_trade_stays_visible_without_being_called_incomplete() -> None:
    readiness = complete_readiness("t3", mode=HistoricalEvidenceMode.SENSITIVITY_ONLY)
    progress = classify_historical_trade_progress(
        readiness,
        robustness=robustness("t3", HistoricalDecisionRobustnessStatus.SENSITIVE),
    )
    assert progress.status == HistoricalTradeProgressStatus.SENSITIVITY_DEPENDENT


def test_missing_asset_evidence_blocks_before_decision() -> None:
    progress = classify_historical_trade_progress(missing_readiness("t4"))
    assert progress.status == HistoricalTradeProgressStatus.EVIDENCE_INCOMPLETE


def test_batch_summary_separates_remaining_work() -> None:
    readiness = (
        complete_readiness("a", mode=HistoricalEvidenceMode.PROBABILISTIC),
        complete_readiness("b", mode=HistoricalEvidenceMode.SENSITIVITY_ONLY),
        complete_readiness("c", mode=HistoricalEvidenceMode.EXACT),
        missing_readiness("d"),
    )
    summary = summarize_historical_trade_progress(
        readiness,
        robustness_by_transaction_id={
            "b": robustness("b", HistoricalDecisionRobustnessStatus.SENSITIVE),
            "c": robustness("c", HistoricalDecisionRobustnessStatus.ROBUST),
        },
    )
    assert summary.trade_count == 4
    counts = dict(summary.status_counts)
    assert counts[HistoricalTradeProgressStatus.READY_FOR_DECISION] == 1
    assert counts[HistoricalTradeProgressStatus.SENSITIVITY_DEPENDENT] == 1
    assert counts[HistoricalTradeProgressStatus.READY_FOR_GRADE_ENVELOPE] == 1
    assert counts[HistoricalTradeProgressStatus.EVIDENCE_INCOMPLETE] == 1


def test_rejects_stale_robustness_result_for_unknown_trade() -> None:
    with pytest.raises(ValueError, match="unknown transactions"):
        summarize_historical_trade_progress(
            (complete_readiness("known", mode=HistoricalEvidenceMode.EXACT),),
            robustness_by_transaction_id={
                "stale": robustness("stale", HistoricalDecisionRobustnessStatus.ROBUST)
            },
        )
