from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .models import ActionAuthority, EvidenceCompleteness, OpportunityCandidate


class ObjectiveDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class OpportunityObjective(FrozenModel):
    """One explicit search-ordering objective supplied by authoritative evidence."""

    name: str
    value: float
    direction: ObjectiveDirection

    @model_validator(mode="after")
    def validate_objective(self) -> "OpportunityObjective":
        if not self.name.strip():
            raise ValueError("objective name cannot be blank")
        return self


class OrderedOpportunityPoint(FrozenModel):
    candidate: OpportunityCandidate
    objectives: tuple[OpportunityObjective, ...]

    @model_validator(mode="after")
    def validate_point(self) -> "OrderedOpportunityPoint":
        names = [objective.name for objective in self.objectives]
        if not names:
            raise ValueError("ordered opportunity point requires at least one objective")
        if len(names) != len(set(names)):
            raise ValueError("objective names must be unique within a point")
        return self


def _objective_map(point: OrderedOpportunityPoint) -> dict[str, OpportunityObjective]:
    return {objective.name: objective for objective in point.objectives}


def dominates(left: OrderedOpportunityPoint, right: OrderedOpportunityPoint) -> bool:
    """Return whether left Pareto-dominates right under identical named objectives.

    Action authority and evidence completeness are deliberately not converted into
    numeric weights here. Callers may tier by those categorical states separately.
    """

    left_map = _objective_map(left)
    right_map = _objective_map(right)
    if set(left_map) != set(right_map):
        raise ValueError("Pareto comparison requires identical objective names")

    weakly_better = True
    strictly_better = False
    for name in sorted(left_map):
        a = left_map[name]
        b = right_map[name]
        if a.direction != b.direction:
            raise ValueError("Pareto comparison requires identical objective directions")
        if a.direction == ObjectiveDirection.MAXIMIZE:
            weakly_better &= a.value >= b.value
            strictly_better |= a.value > b.value
        else:
            weakly_better &= a.value <= b.value
            strictly_better |= a.value < b.value
    return bool(weakly_better and strictly_better)


def pareto_front(points: tuple[OrderedOpportunityPoint, ...]) -> tuple[OrderedOpportunityPoint, ...]:
    """Return deterministic non-dominated opportunities without scalar ranking."""

    if not points:
        return ()
    survivors: list[OrderedOpportunityPoint] = []
    for candidate in points:
        if any(
            other.candidate.candidate_id != candidate.candidate.candidate_id
            and dominates(other, candidate)
            for other in points
        ):
            continue
        survivors.append(candidate)
    return tuple(sorted(survivors, key=lambda point: point.candidate.candidate_id))


def authority_tier(candidate: OpportunityCandidate) -> tuple[int, int]:
    """Categorical search tier only; not a trade-value or utility score.

    Higher authority and more complete evidence are surfaced first. This function
    does not compare the substantive football/economic objectives inside a tier.
    """

    authority_rank = {
        ActionAuthority.ACTIONABLE: 3,
        ActionAuthority.MARKET_TEST_ONLY: 2,
        ActionAuthority.DIAGNOSTIC_ONLY: 1,
        ActionAuthority.NONE: 0,
    }[candidate.action_authority]
    evidence_rank = {
        EvidenceCompleteness.COMPLETE: 2,
        EvidenceCompleteness.PARTIAL: 1,
        EvidenceCompleteness.INSUFFICIENT: 0,
    }[candidate.evidence_completeness]
    return authority_rank, evidence_rank
