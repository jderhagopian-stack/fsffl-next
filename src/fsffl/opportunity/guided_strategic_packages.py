"""Bounded package construction around existing ranked strategic hypotheses.

Market totals only locate a plausible negotiating envelope. They never score a
franchise improvement, price an asset, or grant Decision authority.
"""
from bisect import bisect_left, bisect_right
from collections import deque
from itertools import combinations, zip_longest
from math import isfinite

from fsffl.state.models import FaabAsset
from .strategic_packages import StrategicSeed, generate_strategic_packages
from .trade_universe import TradePackageSeed, canonical_package_id
from .trade_pairs import generate_bilateral_trade_proposals, TradePairSearchPolicy


def _ingredients(inventory, required, limit):
    if required is not None:
        if required not in inventory.assets:
            return ()
        return (required, *(a for a in inventory.assets if a != required))[:limit]
    return inventory.assets[:limit]


def _bundles(assets, required):
    singles=((a,) for a in assets if required is None or a == required)
    pairs=(g for g in combinations(assets, 2) if (required is None or required in g)
           and sum(isinstance(a, FaabAsset) for a in g) <= 1)
    for row in zip_longest(singles, pairs):
        yield from (group for group in row if group is not None)


def _lane_stream(lane, *, bounds, values, tolerance):
    left = _ingredients(lane.focal, lane.required_send, bounds.ingredients_per_side)
    right = _ingredients(lane.counterparty, lane.required_receive, bounds.ingredients_per_side)
    if not left or not right:
        return
    def known(a):
        return a in values and isfinite(values[a]) and values[a] >= 0
    # At most 78 lightweight bundles for 12 ingredients, never a Cartesian table.
    def indexed(assets, required):
        return sorted(((sum(values[a] for a in group), i, group)
            for i, group in enumerate(_bundles(assets, required)) if all(known(a) for a in group)),
            key=lambda row: (row[0], row[1]))
    def direction(targets, offers, required_target, required_offer, reverse):
        index = indexed(offers, required_offer)
        totals = [row[0] for row in index]
        for target in _bundles(targets, required_target):
            if not all(known(a) for a in target):
                continue
            total = sum(values[a] for a in target)
            lo, hi = bisect_left(totals, total-tolerance), bisect_right(totals, total+tolerance)
            # Hypothesis order and minimal complexity, not closest-price ranking.
            seen_sizes=set()
            for _, _, offer in sorted(index[lo:hi], key=lambda row: (len(row[2]), row[1])):
                if len(offer) in seen_sizes: continue
                seen_sizes.add(len(offer))
                yield (target, offer) if reverse else (offer, target)
            # A larger bundle earns its size by reaching the same envelope when
            # no smaller bundle can. Stop adding assets as soon as it is reached.
            if lo != hi:
                continue
            for start in offers:
                group = [start]
                if required_offer is not None and required_offer != start:
                    group.append(required_offer)
                if sum(isinstance(a, FaabAsset) for a in group)>1 or not all(known(a) for a in group):
                    continue
                amount = sum(values[a] for a in group)
                for extra in offers:
                    if amount >= total-tolerance:
                        break
                    if (extra in group or not known(extra) or amount+values[extra] > total+tolerance
                        or len(group) >= bounds.max_assets_per_side
                        or len(group)+len(target) >= bounds.max_total_assets
                        or isinstance(extra, FaabAsset) and any(isinstance(a, FaabAsset) for a in group)):
                        continue
                    group.append(extra); amount += values[extra]
                if len(group)>2 and total-tolerance <= amount <= total+tolerance:
                    yield (target, tuple(group)) if reverse else (tuple(group), target)
    streams = deque((direction(right, left, lane.required_receive, lane.required_send, False),
                     direction(left, right, lane.required_send, lane.required_receive, True)))
    while streams:
        stream = streams.popleft()
        try:
            send, receive = next(stream)
        except StopIteration:
            continue
        if (max(len(send), len(receive)) <= bounds.max_assets_per_side
            and len(send)+len(receive) <= bounds.max_total_assets):
            yield send, receive
        streams.append(stream)


def generate_guided_strategic_packages(lanes, *, as_of, bounds, market_values, economic_tolerance):
    if as_of.tzinfo is None: raise ValueError('search time must be timezone-aware')
    if economic_tolerance is not None and (not isfinite(economic_tolerance) or economic_tolerance<0): raise ValueError('economic tolerance must be finite and nonnegative')
    if not market_values or economic_tolerance is None:
        return generate_strategic_packages(lanes, as_of=as_of, bounds=bounds)
    # A small exploration reserve retains unusual large structures; most visits
    # construct purposeful packages. This is a compute allocation, not a score.
    exploration = max(1, bounds.max_pair_visits // 8)
    guided_limit = bounds.max_pair_visits-exploration
    queues = deque((lane, _lane_stream(lane, bounds=bounds, values=market_values,
                                      tolerance=economic_tolerance)) for lane in lanes)
    by_id = {}; hypotheses = {}; visits = 0; groups = set()
    while queues and visits < guided_limit and len(by_id) < bounds.max_candidates:
        lane, stream = queues.popleft()
        try:
            send, receive = next(stream)
        except StopIteration:
            continue
        visits += 1; groups.add((lane.name, lane.counterparty.team_id))
        packages = [TradePackageSeed(team_id=team, assets=assets, canonical_id=canonical_package_id(team, assets))
                    for team, assets in ((lane.focal.team_id, send), (lane.counterparty.team_id, receive))]
        seed = generate_bilateral_trade_proposals((packages[0],), (packages[1],), as_of=as_of,
            policy=TradePairSearchPolicy(max_candidate_pairs=1)).proposals[0]
        by_id.setdefault(seed.point_id, seed)
        hypotheses.setdefault(seed.point_id, set()).add(lane.name)
        queues.append((lane, stream))
    extra, diagnostics = generate_strategic_packages(lanes, as_of=as_of,
        bounds=bounds.model_copy(update={'max_pair_visits':bounds.max_pair_visits-visits,
                                        'max_candidates':bounds.max_candidates}))
    for row in extra:
        if row.seed.point_id not in by_id and len(by_id) >= bounds.max_candidates:
            break
        by_id.setdefault(row.seed.point_id, row.seed)
        hypotheses.setdefault(row.seed.point_id, set()).update(row.hypotheses)
    from collections import Counter
    seeds = tuple(StrategicSeed(seed, tuple(sorted(hypotheses[key]))) for key, seed in by_id.items())
    return seeds, {**diagnostics, 'candidate_count':len(seeds),
        'pair_visits':visits+diagnostics['pair_visits'], 'duplicate_pair_visits':visits+diagnostics['pair_visits']-len(seeds), 'guided_pair_visits':visits,
        'exploration_pair_visits':diagnostics['pair_visits'],
        'counterparties_visited':len({team for _,team in groups} | {s.seed.proposal.side_b.team_id for s in extra}),
        'shapes':dict(Counter(f'{len(s.seed.proposal.side_a.sends)}_for_{len(s.seed.proposal.side_b.sends)}' for s in seeds)),
        'hypotheses':dict(Counter(h for s in seeds for h in s.hypotheses)),
        'package_enumeration':'bounded_guided_packages_with_lazy_exploration',
        'interpretation':'Market envelope screens negotiation structure only; Decision evaluates actual team gains and costs'}
