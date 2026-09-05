from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .frontier import BilateralFrontierPoint, expand_adjacent_packages, make_frontier_point
from .models import OpportunityCandidate
from .trade_universe import TeamTradeInventory, TradeSearchBounds


class FrontierSearchPolicy(FrozenModel):
    max_depth: Annotated[int, Field(ge=0, le=10)] = 3
    max_evaluations: Annotated[int, Field(ge=1, le=10000)] = 250
    expand_focal_side: bool = True
    expand_counterparty_side: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> "FrontierSearchPolicy":
        if not (self.expand_focal_side or self.expand_counterparty_side):
            raise ValueError("frontier search must expand at least one trade side")
        return self


class EvaluatedFrontierPoint(FrozenModel):
    point: BilateralFrontierPoint
    candidate: OpportunityCandidate
    depth: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def validate_identity(self) -> "EvaluatedFrontierPoint":
        if self.candidate.candidate_id != self.point.point_id:
            raise ValueError("frontier candidate identity must equal canonical point identity")
        if self.candidate.focal_team_id != self.point.focal_package.team_id:
            raise ValueError("frontier candidate focal team must match focal package")
        return self


class FrontierSearchResult(FrozenModel):
    seed_point_id: str
    evaluated: tuple[EvaluatedFrontierPoint, ...]
    exhausted: bool
    max_depth_reached: int
    search_model_version: str = "next6-frontier-search-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "FrontierSearchResult":
        if not self.seed_point_id.strip() or not self.search_model_version.strip():
            raise ValueError("frontier search identifiers cannot be blank")
        ids = [item.point.point_id for item in self.evaluated]
        if len(ids) != len(set(ids)):
            raise ValueError("frontier search may evaluate each point only once")
        return self


def _neighbor_points(
    point: BilateralFrontierPoint,
    *,
    focal_inventory: TeamTradeInventory,
    counterparty_inventory: TeamTradeInventory,
    bounds: TradeSearchBounds,
    policy: FrontierSearchPolicy,
) -> tuple[BilateralFrontierPoint, ...]:
    neighbors: dict[str, BilateralFrontierPoint] = {}

    if policy.expand_focal_side:
        for neighbor in expand_adjacent_packages(
            point.focal_package,
            inventory=focal_inventory,
            bounds=bounds,
        ):
            next_point = make_frontier_point(neighbor.package, point.counterparty_package)
            neighbors[next_point.point_id] = next_point

    if policy.expand_counterparty_side:
        for neighbor in expand_adjacent_packages(
            point.counterparty_package,
            inventory=counterparty_inventory,
            bounds=bounds,
        ):
            next_point = make_frontier_point(point.focal_package, neighbor.package)
            neighbors[next_point.point_id] = next_point

    return tuple(neighbors[key] for key in sorted(neighbors))


def explore_negotiation_frontier(
    seed: BilateralFrontierPoint,
    *,
    focal_inventory: TeamTradeInventory,
    counterparty_inventory: TeamTradeInventory,
    bounds: TradeSearchBounds,
    evaluator: Callable[[BilateralFrontierPoint], OpportunityCandidate],
    policy: FrontierSearchPolicy = FrontierSearchPolicy(),
    search_model_version: str = "next6-frontier-search-v1",
) -> FrontierSearchResult:
    """Breadth-first bounded frontier search that does not stop on bad early offers.

    Search geometry is independent of candidate evaluation. A diagnostic-only,
    counterparty-dominated, or unknown-acceptance point does not terminate expansion.
    The evaluator remains responsible for routing each point through authoritative
    NEXT-5 logic; this search function never changes value, utility, or acceptance.
    """

    if focal_inventory.team_id != seed.focal_package.team_id:
        raise ValueError("focal inventory must match seed focal package")
    if counterparty_inventory.team_id != seed.counterparty_package.team_id:
        raise ValueError("counterparty inventory must match seed counterparty package")
    if not search_model_version.strip():
        raise ValueError("search_model_version cannot be blank")

    queue = deque([(seed, 0)])
    queued = {seed.point_id}
    visited: set[str] = set()
    evaluated: list[EvaluatedFrontierPoint] = []
    max_depth_reached = 0
    budget_hit = False

    while queue:
        if len(evaluated) >= policy.max_evaluations:
            budget_hit = True
            break

        point, depth = queue.popleft()
        if point.point_id in visited:
            continue
        visited.add(point.point_id)
        max_depth_reached = max(max_depth_reached, depth)

        candidate = evaluator(point)
        evaluated.append(EvaluatedFrontierPoint(point=point, candidate=candidate, depth=depth))

        if depth >= policy.max_depth:
            continue

        for neighbor in _neighbor_points(
            point,
            focal_inventory=focal_inventory,
            counterparty_inventory=counterparty_inventory,
            bounds=bounds,
            policy=policy,
        ):
            if neighbor.point_id in visited or neighbor.point_id in queued:
                continue
            queue.append((neighbor, depth + 1))
            queued.add(neighbor.point_id)

    return FrontierSearchResult(
        seed_point_id=seed.point_id,
        evaluated=tuple(evaluated),
        exhausted=not budget_hit and not queue,
        max_depth_reached=max_depth_reached,
        search_model_version=search_model_version,
    )
