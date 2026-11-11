"""Directional goal assessment beside, never in place of, calculated Decision."""
from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import model_validator

from fsffl.state.models import FrozenModel


class TradeObjective(StrEnum):
    CURRENT = "current_competitiveness"
    THREE_YEAR = "three_year_contribution"
    CAREER = "career_contribution"
    RESILIENCE = "resilience"
    MARKET = "market_capital"


class ObjectiveDirection(StrEnum):
    GAIN = "gain"
    LOSS = "loss"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class OwnerObjectiveContext(FrozenModel):
    team_id: str
    objectives: tuple[TradeObjective, ...]
    source: str
    explicitly_directed: bool = False
    calculated_competitive_state: str | None = None
    inferred_posture: str | None = None
    protected_player_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_context(self):
        if not self.team_id.strip() or not self.source.strip() or not self.objectives:
            raise ValueError("team, source and at least one objective are required")
        if len(set(self.objectives)) != len(self.objectives):
            raise ValueError("objectives must be distinct")
        if len(set(self.protected_player_ids)) != len(self.protected_player_ids):
            raise ValueError("protected players must be distinct")
        if any(not pid.strip() for pid in self.protected_player_ids):
            raise ValueError("protected player identifiers cannot be blank")
        return self


class ObjectiveMetric(FrozenModel):
    objective: TradeObjective
    metric: str
    unit: str
    source_identity: str
    delta: float | None = None
    higher_is_better: bool = True
    authoritative: bool = False

    @model_validator(mode="after")
    def validate_metric(self):
        if not all(s.strip() for s in (self.metric, self.unit, self.source_identity)):
            raise ValueError("metric, native unit and source identity are required")
        if self.delta is not None and not isfinite(self.delta):
            raise ValueError("objective deltas must be finite or missing")
        return self

    def direction(self) -> ObjectiveDirection:
        if self.delta is None or not self.authoritative:
            return ObjectiveDirection.UNKNOWN
        if self.delta == 0:
            return ObjectiveDirection.UNCHANGED
        return ObjectiveDirection.GAIN if (self.delta > 0) == self.higher_is_better else ObjectiveDirection.LOSS


class SideObjectiveAssessment(FrozenModel):
    context: OwnerObjectiveContext
    status: str
    gains: tuple[ObjectiveMetric, ...]
    sacrifices: tuple[ObjectiveMetric, ...]
    unresolved: tuple[TradeObjective, ...]
    protected_players_lost: tuple[str, ...]
    directional_only: bool = True
    decision_effect: str = "no_disposition_change"
    model_version: str = "next5-directional-objectives-v1"


def assess_owner_objectives(
    context: OwnerObjectiveContext,
    metrics: tuple[ObjectiveMetric, ...],
    *,
    sent_player_ids: tuple[str, ...] = (),
    cut_player_ids: tuple[str, ...] = (),
) -> SideObjectiveAssessment:
    """Report all tradeoffs, with no cross-unit arithmetic or significance claim.

    A metric vector can conflict internally (e.g. wins versus playoff odds).
    Missing/preview channels remain unresolved. Alignment is not a final action
    recommendation or a claim about another owner's willingness.
    """
    if len({(m.objective, m.metric) for m in metrics}) != len(metrics):
        raise ValueError("objective metric channels must be distinct")
    gains = tuple(m for m in metrics if m.direction() == ObjectiveDirection.GAIN)
    losses = tuple(m for m in metrics if m.direction() == ObjectiveDirection.LOSS)
    unresolved = tuple(goal for goal in context.objectives if
        not any(m.objective == goal for m in metrics)
        or any(m.objective == goal and m.direction() == ObjectiveDirection.UNKNOWN for m in metrics))
    lost = tuple(sorted(set(context.protected_player_ids) & (set(sent_player_ids) | set(cut_player_ids))))
    priority_gain = any(m.objective in context.objectives for m in gains)
    priority_loss = any(m.objective in context.objectives for m in losses)
    if lost:
        status = "constraints_violated"
    elif unresolved:
        status = "incomplete"
    elif priority_gain and priority_loss:
        status = "mixed"
    elif priority_loss:
        status = "conflicts_with_priorities"
    elif priority_gain:
        status = "aligns_with_priorities"
    else:
        status = "unchanged"
    return SideObjectiveAssessment(
        context=context, status=status, gains=gains, sacrifices=losses,
        unresolved=unresolved, protected_players_lost=lost,
    )
