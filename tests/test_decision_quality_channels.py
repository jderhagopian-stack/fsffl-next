from datetime import UTC, datetime

import pytest

from fsffl.team_utility.scenario import (
    CompetitiveOutcomeDelta,
    RosterResilienceDelta,
    TeamScenarioDelta,
)
from fsffl.trade_decision.decision_quality_channels import (
    CompetitiveDecisionMetric,
    EconomicDecisionMetric,
    ResilienceDecisionMetric,
    assemble_decision_quality_channels,
    competitive_decision_quality_component,
    economic_decision_quality_component,
    resilience_decision_quality_component,
)
from fsffl.trade_decision.decision_quality_normalization import (
    DecisionQualityNormalizationPoint,
    DecisionQualityNormalizationPolicy,
)
from fsffl.trade_decision.economic_net import (
    EconomicNetStatus,
    ExpectedEconomicNetDelta,
    TradeLegEconomicNet,
)
from fsffl.trade_decision.economics import EconomicConcept
from fsffl.trade_decision.evaluation import TradeSideEvaluation
from fsffl.value.models import ValueScale


AS_OF = datetime(2026, 7, 11, tzinfo=UTC)
SCALE = ValueScale(scale_id="research", version="v1", unit_label="points")


def normalization(component_id: str, authority_id: str, overlap_group: str) -> DecisionQualityNormalizationPolicy:
    return DecisionQualityNormalizationPolicy(
        component_id=component_id,
        authority_id=authority_id,
        overlap_group=overlap_group,
        points=(
            DecisionQualityNormalizationPoint(raw_value=-10, score_lower=10, score_center=20, score_upper=30),
            DecisionQualityNormalizationPoint(raw_value=0, score_lower=45, score_center=50, score_upper=55),
            DecisionQualityNormalizationPoint(raw_value=10, score_lower=70, score_center=80, score_upper=90),
        ),
        evidence_through=datetime(2026, 1, 1, tzinfo=UTC),
        model_version=f"{component_id}-norm-v1",
        provenance="tests:explicit-policy",
    )


def evaluation() -> TradeSideEvaluation:
    return TradeSideEvaluation(
        team_id="team-a",
        delta=TeamScenarioDelta(
            team_id="team-a",
            baseline_as_of=AS_OF,
            scenario_as_of=AS_OF,
            competitive=CompetitiveOutcomeDelta(
                expected_wins=1.0,
                playoff_probability=0.05,
                first_place_probability=0.02,
            ),
            resilience=RosterResilienceDelta(
                largest_single_player_lineup_drop=-2.0,
            ),
            asset_portfolio=None,
            calculated_state_before="competitive",
            calculated_state_after="competitive",
            model_version="test-delta-v1",
        ),
    )


def economic_net() -> TradeLegEconomicNet:
    market = ExpectedEconomicNetDelta(
        concept=EconomicConcept.MARKET_PRICE,
        mean_delta=4.0,
        scale=SCALE,
        status=EconomicNetStatus.COMPLETE,
        sent_mean=10,
        received_mean=14,
        model_versions=("market-v1",),
    )
    intrinsic = ExpectedEconomicNetDelta(
        concept=EconomicConcept.INTRINSIC_VALUE,
        mean_delta=3.0,
        scale=SCALE,
        status=EconomicNetStatus.COMPLETE,
        sent_mean=11,
        received_mean=14,
        model_versions=("intrinsic-v1",),
    )
    return TradeLegEconomicNet(team_id="team-a", market=market, intrinsic=intrinsic)


def test_channel_adapters_create_nonoverlapping_components_with_correct_orientation() -> None:
    economic = economic_decision_quality_component(
        economic_net=economic_net(),
        metric=EconomicDecisionMetric.MARKET_NET,
        as_of=AS_OF,
        confidence=0.9,
        policy=normalization("economic", "trade_decision:economic_net", "economic_value"),
        evidence_through=AS_OF,
    )
    competitive = competitive_decision_quality_component(
        evaluation=evaluation(),
        metric=CompetitiveDecisionMetric.EXPECTED_WINS,
        as_of=AS_OF,
        confidence=0.8,
        policy=normalization("competitive", "team_utility:competitive_outcome", "competitive_outcome"),
    )
    resilience = resilience_decision_quality_component(
        evaluation=evaluation(),
        metric=ResilienceDecisionMetric.LARGEST_SINGLE_PLAYER_LINEUP_DROP,
        as_of=AS_OF,
        confidence=0.7,
        policy=normalization("resilience", "team_utility:roster_resilience", "roster_resilience"),
    )

    channels = assemble_decision_quality_channels(
        team_id="team-a",
        components=(economic, competitive, resilience),
    )
    assert len(channels.components) == 3
    assert resilience.score_center > 50  # a smaller lineup-drop exposure is beneficial
    assert economic.evidence_through == AS_OF


def test_standard_assembly_rejects_multiple_metrics_from_same_competitive_authority() -> None:
    policy_a = normalization("wins", "team_utility:competitive_outcome", "competitive_outcome")
    policy_b = normalization("playoffs", "team_utility:competitive_outcome", "competitive_outcome")
    wins = competitive_decision_quality_component(
        evaluation=evaluation(),
        metric=CompetitiveDecisionMetric.EXPECTED_WINS,
        as_of=AS_OF,
        confidence=1.0,
        policy=policy_a,
    )
    playoffs = competitive_decision_quality_component(
        evaluation=evaluation(),
        metric=CompetitiveDecisionMetric.PLAYOFF_PROBABILITY,
        as_of=AS_OF,
        confidence=1.0,
        policy=policy_b,
    )
    with pytest.raises(ValueError, match="same authority twice"):
        assemble_decision_quality_channels(team_id="team-a", components=(wins, playoffs))


def test_economic_adapter_rejects_incomplete_package_evidence() -> None:
    net = economic_net().model_copy(
        update={
            "market": ExpectedEconomicNetDelta(
                concept=EconomicConcept.MARKET_PRICE,
                status=EconomicNetStatus.INCOMPLETE,
                sent_mean=10,
                received_mean=14,
                missing_asset_ids=("pick:x",),
            )
        }
    )
    with pytest.raises(ValueError, match="complete economic net"):
        economic_decision_quality_component(
            economic_net=net,
            metric=EconomicDecisionMetric.MARKET_NET,
            as_of=AS_OF,
            confidence=1.0,
            policy=normalization("economic", "trade_decision:economic_net", "economic_value"),
            evidence_through=AS_OF,
        )
