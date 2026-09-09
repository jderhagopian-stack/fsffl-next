from datetime import UTC, datetime

from fsffl.behavioral import (
    BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection,
    BehavioralLikelihoodEstimate,
    BehavioralProbabilityBasis,
    OwnerBehaviorProfile,
)
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision.acceptance import AcceptanceModelStatus
from fsffl.trade_decision.behavioral import bind_owner_behavior_evidence
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg


AS_OF = datetime(2026, 9, 8, 12, tzinfo=UTC)


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="proposal-1",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="team-a", sends=(PlayerAsset(player_id="player-a"),)),
        side_b=TradeLeg(team_id="team-b", sends=(PlayerAsset(player_id="player-b"),)),
    )


def _profile() -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="league-family",
        owner_id="owner-b",
        as_of=AS_OF,
        first_observed_at=datetime(2024, 9, 1, tzinfo=UTC),
        event_count=12,
        trade_count=6,
        waiver_count=4,
        free_agent_count=2,
        consolidation_trade_count=3,
        diversification_trade_count=2,
        balanced_trade_count=1,
        acquired_pick_count=2,
        disposed_pick_count=4,
        seasons_observed=(2024, 2025, 2026),
    )


def test_raw_behavior_history_remains_valid_without_inventing_probability() -> None:
    view = bind_owner_behavior_evidence(
        _proposal(),
        accepting_team_id="team-b",
        profile=_profile(),
    )

    assert view.status == AcceptanceModelStatus.NOT_ESTIMATED
    assert view.estimate is None
    assert len(view.evidence.items) == 1


def test_governed_inferred_probability_passes_through_as_provisional_decision_evidence() -> None:
    likelihood = BehavioralLikelihoodEstimate(
        owner_id="owner-b",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.INFERRED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        observed_trade_count=6,
        acceptance_probability=0.61,
        probability_interval_low=0.37,
        probability_interval_high=0.78,
        probability_basis=BehavioralProbabilityBasis.INFERRED,
        probability_method="bounded-contextual-inference",
        confidence_score=0.44,
        inference_model_version="behavioral-inference-v1",
    )

    view = bind_owner_behavior_evidence(
        _proposal(),
        accepting_team_id="team-b",
        profile=_profile(),
        likelihood=likelihood,
    )

    assert view.status == AcceptanceModelStatus.PROVISIONAL_GOVERNED
    assert view.estimate is not None
    assert view.estimate.probability_mean == 0.61
    assert view.estimate.probability_p10 == 0.37
    assert view.estimate.probability_p90 == 0.78
    assert view.estimate.model_version == "behavioral-inference-v1"
    assert len(view.evidence.items) == 2


def test_calibrated_behavior_does_not_auto_promote_decision_acceptance_authority() -> None:
    likelihood = BehavioralLikelihoodEstimate(
        owner_id="owner-b",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.CALIBRATED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        observed_trade_count=24,
        acceptance_probability=0.64,
        probability_interval_low=0.52,
        probability_interval_high=0.74,
        probability_basis=BehavioralProbabilityBasis.CALIBRATED,
        probability_method="backtested-owner-response-model",
        confidence_score=0.81,
        calibration_model_version="behavioral-calibration-v1",
    )

    view = bind_owner_behavior_evidence(
        _proposal(),
        accepting_team_id="team-b",
        profile=_profile(),
        likelihood=likelihood,
    )

    assert view.status == AcceptanceModelStatus.PROVISIONAL_GOVERNED
    assert view.estimate is not None
    assert view.estimate.model_version == "behavioral-calibration-v1"


def test_binding_is_pass_through_not_a_second_value_or_multiplicative_path() -> None:
    source = open("src/fsffl/trade_decision/behavioral.py", encoding="utf-8").read().lower()
    assert "pass-through only" in source
    assert "neither adds another team-need adjustment" in source
    assert "multiplies this probability" in source
    assert "universal market" in source
