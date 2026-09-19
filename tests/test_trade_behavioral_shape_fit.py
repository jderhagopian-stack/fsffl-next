from datetime import UTC, datetime

from fsffl.behavioral import (
    BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection,
    BehavioralLikelihoodEstimate,
    BehavioralProbabilityBasis,
    BehavioralTradeShape,
    OwnerBehaviorProfile,
    OwnerTradeShapePreference,
    OwnerTradeShapePreferenceProfile,
)
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision import assess_owner_trade_shape_proposal_fit
from fsffl.trade_decision.acceptance import AcceptanceModelStatus
from fsffl.trade_decision.behavioral import bind_owner_behavior_evidence
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg


AS_OF = datetime(2026, 9, 8, 12, tzinfo=UTC)
PROFILE_AS_OF = datetime(2026, 9, 7, 12, tzinfo=UTC)


def proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="proposal-shape",
        as_of=AS_OF,
        side_a=TradeLeg(
            team_id="team-a",
            sends=(PlayerAsset(player_id="a-1"), PlayerAsset(player_id="a-2")),
        ),
        side_b=TradeLeg(team_id="team-b", sends=(PlayerAsset(player_id="b-1"),)),
    )


def raw_profile(owner_id: str = "owner-a") -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="family",
        owner_id=owner_id,
        as_of=PROFILE_AS_OF,
        first_observed_at=datetime(2024, 9, 1, tzinfo=UTC),
        event_count=10,
        trade_count=10,
        waiver_count=0,
        free_agent_count=0,
        consolidation_trade_count=6,
        diversification_trade_count=2,
        balanced_trade_count=2,
        seasons_observed=(2024, 2025, 2026),
    )


def shape_profile(owner_id: str = "owner-a") -> OwnerTradeShapePreferenceProfile:
    rows = (
        OwnerTradeShapePreference(
            shape=BehavioralTradeShape.CONSOLIDATION,
            observed_share=0.60,
            context_expected_share=0.40,
            raw_residual_share=0.20,
            shrunk_residual_share=0.15,
            status="estimated",
        ),
        OwnerTradeShapePreference(
            shape=BehavioralTradeShape.DIVERSIFICATION,
            observed_share=0.20,
            context_expected_share=0.35,
            raw_residual_share=-0.15,
            shrunk_residual_share=-0.1125,
            status="estimated",
        ),
        OwnerTradeShapePreference(
            shape=BehavioralTradeShape.BALANCED,
            observed_share=0.20,
            context_expected_share=0.25,
            raw_residual_share=-0.05,
            shrunk_residual_share=-0.0375,
            status="estimated",
        ),
    )
    return OwnerTradeShapePreferenceProfile(
        owner_id=owner_id,
        league_family_id="family",
        as_of=PROFILE_AS_OF,
        shapes=rows,
        eligible_trade_count=10,
        estimated_trade_count=8,
        coverage_rate=0.8,
        confidence=0.75,
        context_policy_parameter_id="shape-context-v1",
        residual_policy_parameter_id="shape-residual-v1",
        context_model_version="behavioral-trade-shape-context-knn-v1",
    )


def test_shape_fit_uses_accepting_team_perspective() -> None:
    trade = proposal()

    side_a = assess_owner_trade_shape_proposal_fit(
        trade, accepting_team_id="team-a", owner_id="owner-a", profile=shape_profile("owner-a")
    )
    side_b = assess_owner_trade_shape_proposal_fit(
        trade, accepting_team_id="team-b", owner_id="owner-b", profile=shape_profile("owner-b")
    )

    assert side_a.proposed_shape == BehavioralTradeShape.CONSOLIDATION
    assert side_a.residual_share == 0.15
    assert side_a.historical_coverage_rate == 0.8
    assert side_b.proposed_shape == BehavioralTradeShape.DIVERSIFICATION
    assert side_b.residual_share == -0.1125


def test_shape_fit_is_evidence_only_when_no_probability_exists() -> None:
    trade = proposal()
    fit = assess_owner_trade_shape_proposal_fit(
        trade, accepting_team_id="team-a", owner_id="owner-a", profile=shape_profile()
    )
    view = bind_owner_behavior_evidence(
        trade,
        accepting_team_id="team-a",
        profile=raw_profile(),
        trade_shape_fit=fit,
    )

    assert view.status == AcceptanceModelStatus.NOT_ESTIMATED
    assert view.estimate is None
    assert len(view.evidence.items) == 2
    description = view.evidence.items[1].description
    assert "consolidation" in description
    assert "context-controlled residual=0.150" in description
    assert "historical coverage=0.800" in description


def test_shape_fit_does_not_change_governed_probability() -> None:
    trade = proposal()
    likelihood = BehavioralLikelihoodEstimate(
        owner_id="owner-a",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.INFERRED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        observed_trade_count=10,
        acceptance_probability=0.61,
        probability_interval_low=0.38,
        probability_interval_high=0.79,
        probability_basis=BehavioralProbabilityBasis.INFERRED,
        probability_method="test-inference",
        confidence_score=0.45,
        inference_model_version="behavioral-inference-test-v1",
    )
    without_shape = bind_owner_behavior_evidence(
        trade, accepting_team_id="team-a", profile=raw_profile(), likelihood=likelihood
    )
    fit = assess_owner_trade_shape_proposal_fit(
        trade, accepting_team_id="team-a", owner_id="owner-a", profile=shape_profile()
    )
    with_shape = bind_owner_behavior_evidence(
        trade,
        accepting_team_id="team-a",
        profile=raw_profile(),
        likelihood=likelihood,
        trade_shape_fit=fit,
    )

    assert without_shape.estimate is not None
    assert with_shape.estimate is not None
    assert with_shape.estimate.probability_mean == without_shape.estimate.probability_mean == 0.61
    assert with_shape.estimate.probability_p10 == without_shape.estimate.probability_p10 == 0.38
    assert with_shape.estimate.probability_p90 == without_shape.estimate.probability_p90 == 0.79
    assert len(with_shape.evidence.items) == len(without_shape.evidence.items) + 1


def test_future_shape_profile_is_rejected() -> None:
    future = shape_profile().model_copy(update={"as_of": datetime(2026, 9, 9, 12, tzinfo=UTC)})
    try:
        assess_owner_trade_shape_proposal_fit(
            proposal(), accepting_team_id="team-a", owner_id="owner-a", profile=future
        )
    except ValueError as exc:
        assert "after proposal cutoff" in str(exc)
    else:
        raise AssertionError("future Behavioral shape evidence must be rejected")


def test_binding_source_marks_shape_fit_as_evidence_only() -> None:
    source = open("src/fsffl/trade_decision/behavioral.py", encoding="utf-8").read().lower()
    assert "trade-shape fit is" in source
    assert "evidence only" in source
    assert "incorporated exactly once" in source
