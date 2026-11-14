"""Bounded search geometry. Orders are hypotheses, never Value or Decision truth."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations, zip_longest
from typing import Annotated, Iterator

from pydantic import Field

from fsffl.state.models import Asset, FaabAsset, FrozenModel
from .trade_universe import TeamTradeInventory, TradePackageSeed, canonical_package_id
from .trade_pairs import TradeProposalSeed, generate_bilateral_trade_proposals, TradePairSearchPolicy


class StrategicSearchBounds(FrozenModel):
    ingredients_per_side: Annotated[int, Field(ge=2, le=12)] = 12
    max_assets_per_side: Annotated[int, Field(ge=1, le=8)] = 8
    max_total_assets: Annotated[int, Field(ge=2, le=16)] = 10
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
    # Extend only the visited prefixes of two lazy combination streams. Never
    # materialize either package universe or their Cartesian product.
    left, right = iter(left), iter(right)
    cached_left, cached_right = [], []
    left_done = right_done = False
    diagonal = 0
    while True:
        if not left_done and len(cached_left) <= diagonal:
            try: cached_left.append(next(left))
            except StopIteration: left_done = True
        if not right_done and len(cached_right) <= diagonal:
            try: cached_right.append(next(right))
            except StopIteration: right_done = True
        if not cached_left or not cached_right:
            return
        for a in range(max(0, diagonal - len(cached_right) + 1), min(len(cached_left), diagonal + 1)):
            yield cached_left[a], cached_right[diagonal - a]
        if left_done and right_done and diagonal >= len(cached_left) + len(cached_right) - 2:
            return
        diagonal += 1


def _package_stream(inventory, size, required):
    if required is None:
        bundles = combinations(inventory.assets, size)
    else:
        extras = tuple(a for a in inventory.assets if a != required)
        bundles = ((required, *rest) for rest in combinations(extras, size - 1))
    for assets in bundles:
        if sum(isinstance(asset, FaabAsset) for asset in assets) > 1:
            continue
        yield TradePackageSeed(team_id=inventory.team_id, assets=assets,
                              canonical_id=canonical_package_id(inventory.team_id, assets))


def _shapes(bounds, left_count, right_count):
    # Alternate total sizes and send/receive orientations. A bounded first batch
    # must encounter both small swaps and larger consolidation/diversification.
    by_total = []
    for total in range(2, bounds.max_total_assets + 1):
        group = [(a, total - a) for a in range(1, min(bounds.max_assets_per_side, left_count) + 1)
                 if 1 <= total - a <= min(bounds.max_assets_per_side, right_count)]
        alternating = []
        while group:
            alternating.append(group.pop(0))
            if group: alternating.append(group.pop())
        if alternating: by_total.append(alternating)
    return tuple(shape for row in zip_longest(*by_total) for shape in row if shape is not None)


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
    shapes = _shapes(bounds, len(inventory_a.assets), len(inventory_b.assets))
    if not shapes:
        return
    shape_offset %= len(shapes)
    shapes = shapes[shape_offset:] + shapes[:shape_offset]
    queues = deque()
    for sent, received in shapes:
        queues.append(_diagonal_pairs(_package_stream(inventory_a, sent, lane.required_send),
                                      _package_stream(inventory_b, received, lane.required_receive)))
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
    queues = deque((lane, _lane_pairs(lane,bounds=bounds,as_of=as_of,shape_offset=i))
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
        'max_assets_per_side':bounds.max_assets_per_side, 'max_total_assets':bounds.max_total_assets,
        'package_enumeration':'lazy_cardinality_streams',
        'max_candidates':bounds.max_candidates, 'max_pair_visits':bounds.max_pair_visits,
        'shapes':dict(Counter(f'{len(s.seed.proposal.side_a.sends)}_for_{len(s.seed.proposal.side_b.sends)}' for s in seeds)),
        'hypotheses':dict(Counter(h for s in seeds for h in s.hypotheses)),
        'interpretation':'Deterministic hypothesis sample; no economic cutoff, global optimum or acceptance claim',
    }
