from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .economic_net import BilateralTradeEconomicNet, EconomicNetStatus
from .materiality import EconomicMaterialityPolicy, MaterialityDirection, classify_positive_delta


class HistoricalEconomicRobustnessStatus(StrEnum):
    ROBUST = "robust"
    SENSITIVE = "sensitive"
    INCOMPLETE = "incomplete"


class HistoricalEconomicScenario(FrozenModel):
    scenario_id: str
    scenario_as_of: datetime
    economic_net: BilateralTradeEconomicNet

    @field_validator("scenario_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical economic scenario_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_id(self) -> "HistoricalEconomicScenario":
        if not self.scenario_id.strip():
            raise ValueError("historical economic scenario_id cannot be blank")
        return self


class HistoricalEconomicScenarioShape(FrozenModel):
    scenario_id: str
    side_a_market: MaterialityDirection
    side_a_intrinsic: MaterialityDirection
    side_b_market: MaterialityDirection
    side_b_intrinsic: MaterialityDirection
    economic_net_model_version: str


class HistoricalEconomicRobustness(FrozenModel):
    proposal_id: str
    status: HistoricalEconomicRobustnessStatus
    scenario_shapes: tuple[HistoricalEconomicScenarioShape, ...]
    materiality_policy_version: str
    reason: str
    model_version: str = "historical-economic-robustness-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "HistoricalEconomicRobustness":
        if any(not value.strip() for value in (
            self.proposal_id,
            self.materiality_policy_version,
            self.reason,
            self.model_version,
        )):
            raise ValueError("historical economic robustness metadata cannot be blank")
        if not self.scenario_shapes:
            raise ValueError("historical economic robustness requires scenario shapes")
        return self


def _direction(net, policy: EconomicMaterialityPolicy) -> MaterialityDirection:
    if net.status != EconomicNetStatus.COMPLETE:
        return MaterialityDirection.UNAVAILABLE
    if net.scale != policy.scale:
        raise ValueError("economic robustness policy scale must match economic net scale")
    return classify_positive_delta(net.mean_delta, absolute_threshold=policy.mean_value_abs)


def assess_historical_economic_robustness(
    scenarios: tuple[HistoricalEconomicScenario, ...],
    *,
    policy: EconomicMaterialityPolicy,
    model_version: str = "historical-economic-robustness-v1",
) -> HistoricalEconomicRobustness:
    """Test whether economic conclusions survive explicit package/value scenarios.

    Examples include additive package economics versus one or more governed
    concentration challengers, or lower/center/upper historical pick coordinates.
    The underlying asset values remain untouched. A scenario is robust only when
    material gain/loss/immaterial classifications are identical across all supplied
    scenarios for both sides and both economic concepts.
    """

    if not scenarios:
        raise ValueError("historical economic robustness requires at least one scenario")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    proposal_ids = {scenario.economic_net.proposal_id for scenario in scenarios}
    if len(proposal_ids) != 1:
        raise ValueError("historical economic scenarios must describe one proposal")
    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("historical economic scenario ids must be unique")
    if any(policy.evidence_through > scenario.scenario_as_of for scenario in scenarios):
        raise ValueError("economic materiality policy uses evidence unavailable at scenario cutoff")

    first = scenarios[0].economic_net
    side_a_id = first.side_a.team_id
    side_b_id = first.side_b.team_id
    for scenario in scenarios[1:]:
        net = scenario.economic_net
        if net.side_a.team_id != side_a_id or net.side_b.team_id != side_b_id:
            raise ValueError("historical economic scenarios must preserve side identities")

    shapes = tuple(
        HistoricalEconomicScenarioShape(
            scenario_id=scenario.scenario_id,
            side_a_market=_direction(scenario.economic_net.side_a.market, policy),
            side_a_intrinsic=_direction(scenario.economic_net.side_a.intrinsic, policy),
            side_b_market=_direction(scenario.economic_net.side_b.market, policy),
            side_b_intrinsic=_direction(scenario.economic_net.side_b.intrinsic, policy),
            economic_net_model_version=scenario.economic_net.model_version,
        )
        for scenario in scenarios
    )

    direction_rows = tuple(
        (shape.side_a_market, shape.side_a_intrinsic, shape.side_b_market, shape.side_b_intrinsic)
        for shape in shapes
    )
    if any(MaterialityDirection.UNAVAILABLE in row for row in direction_rows):
        status = HistoricalEconomicRobustnessStatus.INCOMPLETE
        reason = "one or more economic concepts is unavailable in a supplied PIT scenario"
    elif len(set(direction_rows)) == 1:
        status = HistoricalEconomicRobustnessStatus.ROBUST
        reason = "economic materiality classification is stable across all supplied PIT scenarios"
    else:
        status = HistoricalEconomicRobustnessStatus.SENSITIVE
        reason = "economic materiality classification changes across plausible PIT scenarios"

    return HistoricalEconomicRobustness(
        proposal_id=next(iter(proposal_ids)),
        status=status,
        scenario_shapes=shapes,
        materiality_policy_version=policy.model_version,
        reason=reason,
        model_version=model_version,
    )
