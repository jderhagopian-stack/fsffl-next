"""Bounded search geometry. Orders are hypotheses, never Value or Decision truth."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Iterator

from pydantic import Field

from fsffl.state.models import Asset, FrozenModel
from .trade_universe import TeamTradeInventory, TradeSearchBounds, enumerate_trade_packages
from .trade_pairs import TradeProposalSeed, generate_bilateral_trade_proposals, TradePairSearchPolicy


class StrategicSearchBounds(FrozenModel):
    ingredients_per_side: Annotated[int, Field(ge=2, le=6)] = 6
    max_candidates: Annotated[int, Field(ge=1, le=640)] = 80
    max_pair_visits: Annotated[int, Field(ge=1, le=640)] = 640


@dataclass(frozen=True)
class StrategicPackageLane:
    name: str
    focal: TeamTradeInventory
    counterparty: TeamTradeInventory
    required_receive: Asset | None = None
    required_send: Asset | None = None


@dataclass(frozen=True)
class StrategicSeed:
    seed: TradeProposalSeed
    hypotheses: tuple[str, ...]


def _diagonal_pairs(left, right):
    # Traverse both ordered axes without an aggregate rank/utility score.
    for diagonal in range(len(left) + len(right) - 1):
        for a in range(max(0, diagonal - len(right) + 1), min(len(left), diagonal + 1)):
            yield left[a], right[diagonal - a]


def _lane_pairs(lane, *, bounds, as_of, shape_offset):
    sent = lane.focal.assets
    if lane.required_send is not None:
        if lane.required_send not in sent:
            return
        sent = (lane.required_send, *(a for a in sent if a != lane.required_send))
    inventory_a = lane.focal.model_copy(update={'assets': sent[:bounds.ingredients_per_side]})
    received = lane.counterparty.assets
    if lane.required_receive is not None:
        if lane.required_receive not in received:
            return
        received = (lane.required_receive, *(a for a in received if a != lane.required_receive))
    inventory_b = lane.counterparty.model_copy(update={'assets': received[:bounds.ingredients_per_side]})
    package_bounds = TradeSearchBounds(max_assets_per_side=2)
    # The ingredient cap applies BEFORE either combinations or pair generation.
    packs_a = enumerate_trade_packages(inventory_a, bounds=package_bounds)
    packs_b = enumerate_trade_packages(inventory_b, bounds=package_bounds)
    def ordered(packages, inventory):
        order = {asset: i for i, asset in enumerate(inventory.assets)}
        return sorted(packages, key=lambda p: tuple(sorted(order[a] for a in p.assets)))
    packs_a, packs_b = ordered(packs_a, inventory_a), ordered(packs_b, inventory_b)
    shapes = ((1,1), (2,1), (1,2), (2,2))
    shapes = shapes[shape_offset:] + shapes[:shape_offset]
    queues = deque()
    for sent, received in shapes:
        a = tuple(p for p in packs_a if len(p.assets) == sent and
            (lane.required_send is None or lane.required_send in p.assets))
        b = tuple(p for p in packs_b if len(p.assets) == received and
            (lane.required_receive is None or lane.required_receive in p.assets))
        if a and b:
            queues.append(iter(_diagonal_pairs(a,b)))
    while queues:
        iterator = queues.popleft()
        try:
            a,b = next(iterator)
        except StopIteration:
            continue
        # Reuse canonical NEXT6 proposal identity and owned-package contracts.
        pair = generate_bilateral_trade_proposals((a,), (b,), as_of=as_of,
            policy=TradePairSearchPolicy(max_candidate_pairs=1)).proposals[0]
        yield pair
        queues.append(iterator)


def generate_strategic_packages(
    lanes: tuple[StrategicPackageLane, ...], *, as_of: datetime,
    bounds: StrategicSearchBounds = StrategicSearchBounds(),
) -> tuple[tuple[StrategicSeed, ...], dict[str, object]]:
    if as_of.tzinfo is None:
        raise ValueError('search time must be timezone-aware')
    if len({(lane.name, lane.counterparty.team_id) for lane in lanes}) != len(lanes):
        raise ValueError('lane/counterparty groups must be unique')
    focal_ids = {lane.focal.team_id for lane in lanes}
    if len(focal_ids) > 1 or any(l.focal.team_id == l.counterparty.team_id for l in lanes):
        raise ValueError('search lanes require one focal team and distinct counterparties')
    queues = deque((lane, _lane_pairs(lane,bounds=bounds,as_of=as_of,shape_offset=i%4))
                   for i,lane in enumerate(lanes))
    by_id = {}
    hypotheses = {}
    visits = duplicates = 0
    groups_visited = set()
    while queues and visits < bounds.max_pair_visits and len(by_id) < bounds.max_candidates:
        lane, iterator = queues.popleft()
        try:
            seed = next(iterator)
        except StopIteration:
            continue
        visits += 1
        groups_visited.add((lane.name, lane.counterparty.team_id))
        if seed.point_id in by_id:
            duplicates += 1
            hypotheses[seed.point_id].add(lane.name)
        else:
            by_id[seed.point_id] = seed
            hypotheses[seed.point_id] = {lane.name}
        queues.append((lane, iterator))
    seeds = tuple(StrategicSeed(seed, tuple(sorted(hypotheses[key]))) for key,seed in by_id.items())
    return seeds, {
        'candidate_count':len(seeds), 'pair_visits':visits, 'duplicate_pair_visits':duplicates,
        'lane_groups_available':len(lanes), 'lane_groups_visited':len(groups_visited),
        'counterparties_visited':len({team for _,team in groups_visited}),
        'stopped_at_budget':bool(queues), 'exhaustive_league_search':False,
        'ingredient_limit_before_enumeration':bounds.ingredients_per_side,
        'max_candidates':bounds.max_candidates, 'max_pair_visits':bounds.max_pair_visits,
        'shapes':dict(Counter(f'{len(s.seed.proposal.side_a.sends)}_for_{len(s.seed.proposal.side_b.sends)}' for s in seeds)),
        'hypotheses':dict(Counter(h for s in seeds for h in s.hypotheses)),
        'interpretation':'Deterministic hypothesis sample; no economic cutoff, global optimum or acceptance claim',
    }
