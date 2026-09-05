from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .economic_net import BilateralTradeEconomicNet, EconomicNetStatus
from .evaluation import BilateralTradeEvaluation, TradeSideEvaluation
from .materiality import (
    CompetitiveMaterialityPolicy,
    EconomicMaterialityPolicy,
    MaterialityDirection,
    classify_negative_delta,
    classify_positive_delta,
)


class SideMaterialAssessment(FrozenModel):
    team_id: str
    expected_wins: MaterialityDirection
    playoff_probability: MaterialityDirection
    first_place_probability: MaterialityDirection
    largest_single_player_lineup_drop: MaterialityDirection
    market_value: MaterialityDirection
    intrinsic_value: MaterialityDirection


class BilateralMaterialAssessment(FrozenModel):
    proposal_id: str
    side_a: SideMaterialAssessment
    side_b: SideMaterialAssessment
    competitive_policy_version: str
    economic_policy_version: str
    model_version: str = "next5-material-assessment-v1"

    @model_validator(mode="after")
    def validate_assessment(self) -> "BilateralMaterialAssessment":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("material assessment identifiers cannot be blank")
        if not self.competitive_policy_version.strip() or not self.economic_policy_version.strip():
            raise ValueError("material assessment must record policy versions")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("bilateral material assessment requires distinct teams")
        return self


def _economic_direction(net, policy: EconomicMaterialityPolicy) -> MaterialityDirection:
    if net.status != EconomicNetStatus.COMPLETE:
        return MaterialityDirection.UNAVAILABLE
    if net.scale != policy.scale:
        raise ValueError("economic materiality policy scale must match economic net scale/version")
    return classify_positive_delta(net.mean_delta, absolute_threshold=policy.mean_value_abs)


def _side_assessment(
    evaluation: TradeSideEvaluation,
    economic_net,
    *,
    competitive_policy: CompetitiveMaterialityPolicy,
    economic_policy: EconomicMaterialityPolicy,
) -> SideMaterialAssessment:
    delta = evaluation.delta
    competitive = delta.competitive
    resilience = delta.resilience

    return SideMaterialAssessment(
        team_id=evaluation.team_id,
        expected_wins=classify_positive_delta(
            competitive.expected_wins if competitive else None,
            absolute_threshold=competitive_policy.expected_wins_abs,
        ),
        playoff_probability=classify_positive_delta(
            competitive.playoff_probability if competitive else None,
            absolute_threshold=competitive_policy.playoff_probability_abs,
        ),
        first_place_probability=classify_positive_delta(
            competitive.first_place_probability if competitive else None,
            absolute_threshold=competitive_policy.first_place_probability_abs,
        ),
        largest_single_player_lineup_drop=classify_negative_delta(
            resilience.largest_single_player_lineup_drop if resilience else None,
            absolute_threshold=competitive_policy.lineup_drop_abs,
        ),
        market_value=_economic_direction(economic_net.market, economic_policy),
        intrinsic_value=_economic_direction(economic_net.intrinsic, economic_policy),
    )


def assess_bilateral_materiality(
    evaluation: BilateralTradeEvaluation,
    economic_net: BilateralTradeEconomicNet,
    *,
    competitive_policy: CompetitiveMaterialityPolicy,
    economic_policy: EconomicMaterialityPolicy,
    model_version: str = "next5-material-assessment-v1",
) -> BilateralMaterialAssessment:
    """Apply explicit, versioned materiality policies to bilateral deltas.

    The function does not choose thresholds, combine channels, infer owner intent,
    estimate acceptance, or recommend action. Policy evidence dates may not postdate
    the trade scenario cutoff.
    """

    if evaluation.proposal_id != economic_net.proposal_id:
        raise ValueError("material assessment inputs must describe the same proposal")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    cutoff = min(
        evaluation.side_a.delta.scenario_as_of,
        evaluation.side_b.delta.scenario_as_of,
    )
    if competitive_policy.evidence_through > cutoff:
        raise ValueError("competitive materiality policy uses future evidence")
    if economic_policy.evidence_through > cutoff:
        raise ValueError("economic materiality policy uses future evidence")

    if evaluation.side_a.team_id != economic_net.side_a.team_id:
        raise ValueError("side A economic net must match evaluation side A")
    if evaluation.side_b.team_id != economic_net.side_b.team_id:
        raise ValueError("side B economic net must match evaluation side B")

    return BilateralMaterialAssessment(
        proposal_id=evaluation.proposal_id,
        side_a=_side_assessment(
            evaluation.side_a,
            economic_net.side_a,
            competitive_policy=competitive_policy,
            economic_policy=economic_policy,
        ),
        side_b=_side_assessment(
            evaluation.side_b,
            economic_net.side_b,
            competitive_policy=competitive_policy,
            economic_policy=economic_policy,
        ),
        competitive_policy_version=competitive_policy.model_version,
        economic_policy_version=economic_policy.model_version,
        model_version=model_version,
    )
