from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from fsffl.state.models import FrozenModel

from .decision_quality import DecisionQualityComponent
from .decision_quality_normalization import (
    DecisionQualityNormalizationPolicy,
    normalize_decision_quality_component,
)
from .economic_net import EconomicNetStatus, TradeLegEconomicNet
from .evaluation import TradeSideEvaluation


class EconomicDecisionMetric(StrEnum):
    MARKET_NET = "market_net"
    INTRINSIC_NET = "intrinsic_net"


class CompetitiveDecisionMetric(StrEnum):
    EXPECTED_WINS = "expected_wins"
    PLAYOFF_PROBABILITY = "playoff_probability"
    FIRST_PLACE_PROBABILITY = "first_place_probability"


class ResilienceDecisionMetric(StrEnum):
    LARGEST_SINGLE_PLAYER_LINEUP_DROP = "largest_single_player_lineup_drop"


class DecisionQualityChannelSet(FrozenModel):
    """Non-overlapping normalized evidence for one side of a historical trade."""

    team_id: str
    components: tuple[DecisionQualityComponent, ...]


def _require_policy_identity(
    policy: DecisionQualityNormalizationPolicy,
    *,
    authority_id: str,
    overlap_group: str,
) -> None:
    if policy.authority_id != authority_id:
        raise ValueError(
            f"normalization policy authority_id must be {authority_id!r} for this channel"
        )
    if policy.overlap_group != overlap_group:
        raise ValueError(
            f"normalization policy overlap_group must be {overlap_group!r} for this channel"
        )


def economic_decision_quality_component(
    *,
    economic_net: TradeLegEconomicNet,
    metric: EconomicDecisionMetric,
    as_of: datetime,
    confidence: float,
    policy: DecisionQualityNormalizationPolicy,
    evidence_through: datetime,
) -> DecisionQualityComponent:
    """Normalize exactly one economic concept for a trade side.

    Market and intrinsic values deliberately share the same overlap group. A
    caller may choose one of them for a score policy, but cannot count both as
    independent channels through the standard decision-quality assembly path.
    """

    _require_policy_identity(
        policy,
        authority_id="trade_decision:economic_net",
        overlap_group="economic_value",
    )
    selected = economic_net.market if metric == EconomicDecisionMetric.MARKET_NET else economic_net.intrinsic
    if selected.status != EconomicNetStatus.COMPLETE or selected.mean_delta is None:
        raise ValueError("economic decision-quality component requires a complete economic net")
    return normalize_decision_quality_component(
        raw_value=selected.mean_delta,
        as_of=as_of,
        confidence=confidence,
        policy=policy,
        evidence_through=evidence_through,
    )


def competitive_decision_quality_component(
    *,
    evaluation: TradeSideEvaluation,
    metric: CompetitiveDecisionMetric,
    as_of: datetime,
    confidence: float,
    policy: DecisionQualityNormalizationPolicy,
) -> DecisionQualityComponent:
    """Normalize one representative competitive outcome metric.

    Expected wins, playoff probability and first-place probability are alternate
    views of the same competitive-outcome authority, not three independent score
    components. The selected metric is policy/configuration, never league code.
    """

    _require_policy_identity(
        policy,
        authority_id="team_utility:competitive_outcome",
        overlap_group="competitive_outcome",
    )
    competitive = evaluation.delta.competitive
    if competitive is None:
        raise ValueError("competitive decision-quality component requires competitive outcome evidence")
    raw_value = getattr(competitive, metric.value)
    if raw_value is None:
        raise ValueError(f"competitive metric {metric.value!r} is unavailable")
    return normalize_decision_quality_component(
        raw_value=raw_value,
        as_of=as_of,
        confidence=confidence,
        policy=policy,
        evidence_through=evaluation.delta.scenario_as_of,
    )


def resilience_decision_quality_component(
    *,
    evaluation: TradeSideEvaluation,
    metric: ResilienceDecisionMetric,
    as_of: datetime,
    confidence: float,
    policy: DecisionQualityNormalizationPolicy,
) -> DecisionQualityComponent:
    """Normalize one roster-resilience metric with explicit orientation.

    ``largest_single_player_lineup_drop`` is a loss magnitude, so a larger raw
    delta is worse. The adapter negates it before normalization so all generic
    normalization policies retain the invariant that larger oriented raw values
    are better for the focal team.
    """

    _require_policy_identity(
        policy,
        authority_id="team_utility:roster_resilience",
        overlap_group="roster_resilience",
    )
    resilience = evaluation.delta.resilience
    if resilience is None:
        raise ValueError("resilience decision-quality component requires roster-resilience evidence")
    if metric != ResilienceDecisionMetric.LARGEST_SINGLE_PLAYER_LINEUP_DROP:
        raise ValueError(f"unsupported resilience decision metric: {metric}")
    raw = resilience.largest_single_player_lineup_drop
    if raw is None:
        raise ValueError("largest_single_player_lineup_drop is unavailable")
    return normalize_decision_quality_component(
        raw_value=-raw,
        as_of=as_of,
        confidence=confidence,
        policy=policy,
        evidence_through=evaluation.delta.scenario_as_of,
    )


def assemble_decision_quality_channels(
    *,
    team_id: str,
    components: tuple[DecisionQualityComponent, ...],
) -> DecisionQualityChannelSet:
    """Fail closed if a caller attempts to assemble overlapping score channels."""

    if not team_id.strip():
        raise ValueError("team_id cannot be blank")
    if not components:
        raise ValueError("decision-quality channel set cannot be empty")
    authorities = [item.authority_id for item in components]
    if len(authorities) != len(set(authorities)):
        raise ValueError("decision-quality channel set cannot count the same authority twice")
    overlaps = [item.overlap_group for item in components]
    if len(overlaps) != len(set(overlaps)):
        raise ValueError("decision-quality channel set cannot contain overlapping components")
    return DecisionQualityChannelSet(team_id=team_id, components=components)
