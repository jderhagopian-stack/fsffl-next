"""Bounded package construction around existing ranked strategic hypotheses.

Market totals only locate a plausible negotiating envelope. They never score a
franchise improvement, price an asset, or grant Decision authority.
"""
from bisect import bisect_left, bisect_right
from collections import deque, Counter
from itertools import combinations, zip_longest
from math import isfinite

from fsffl.state.models import FaabAsset, PlayerAsset, PickAsset
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



def _funded_offer(assets, required, target, *, bounds, values, tolerance, pick_rounds):
    """One categorical player+two-later-pick alternative, not a price score.

    Use a separate term window bounded by the existing twelve ingredients,
    including at most four later picks, so a player-heavy ordinary prefix
    cannot hide every funding option. At most48 cheap price checks per anchor;
    every emitted alternative still consumes the existing global visit budget. Round evidence comes
    from canonical State; IDs are never parsed to infer a pick's round.
    """
    if bounds.ingredients_per_side < 3 or bounds.max_assets_per_side < 3 or bounds.max_total_assets < 4:
        return None
    if len(target) != 1 or not isinstance(target[0], PlayerAsset):
        return None
    if required is not None and not isinstance(required, (PlayerAsset, PickAsset)):
        return None
    groups = {}
    for a in assets:
        if isinstance(a, PickAsset) and pick_rounds.get(a, 0) >= 2 and values.get(a, 0) > 0:
            groups.setdefault(pick_rounds[a], []).append(a)
    picks = [a for row in zip_longest(*(groups[r] for r in sorted(groups))) for a in row if a is not None]
    if isinstance(required, PickAsset):
        if required not in picks: return None
        picks = [required, *(a for a in picks if a != required)]
    picks = picks[:min(4, bounds.ingredients_per_side - 1)]
    if len(picks) < 2: return None
    players = [a for a in assets if isinstance(a, PlayerAsset)]
    if isinstance(required, PlayerAsset):
        if required not in players: return None
        players = [required, *(a for a in players if a != required)]
    players = players[:bounds.ingredients_per_side - len(picks)]
    pairs = sorted(combinations(picks, 2), key=lambda p: pick_rounds[p[0]] == pick_rounds[p[1]])
    total = sum(values[a] for a in target)
    for player in players:
        for pair in pairs:
            offer = (player, *pair)
            if required is not None and required not in offer: continue
            if not all(a in values and isfinite(values[a]) and values[a] >= 0 for a in offer): continue
            if abs(sum(values[a] for a in offer) - total) <= tolerance:
                return offer
    return None


def _lane_stream(lane, *, bounds, values, tolerance, pick_rounds=None):
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
    def direction(targets, offers, required_target, required_offer, reverse, all_offers):
        index = indexed(offers, required_offer)
        totals = [row[0] for row in index]
        for target in _bundles(targets, required_target):
            if not all(known(a) for a in target):
                continue
            total = sum(values[a] for a in target)
            lo, hi = bisect_left(totals, total-tolerance), bisect_right(totals, total+tolerance)
            # Hypothesis order and minimal complexity, not closest-price ranking.
            funded = _funded_offer(all_offers, required_offer, target, bounds=bounds,
                values=values, tolerance=tolerance, pick_rounds=pick_rounds or {})
            seen_sizes=Counter()
            for _, _, offer in sorted(index[lo:hi], key=lambda row: (len(row[2]), row[1])):
                if seen_sizes[len(offer)] >= 2: continue
                seen_sizes[len(offer)] += 1
                yield (target, offer) if reverse else (offer, target)
                if funded is not None:
                    yield (target, funded) if reverse else (funded, target)
                    funded = None
            # A larger bundle earns its size by reaching the same envelope when
            # no smaller bundle can. Stop adding assets as soon as it is reached.
            if lo != hi:
                continue
            if funded is not None:
                yield (target, funded) if reverse else (funded, target)
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
    streams = deque((direction(right, left, lane.required_receive, lane.required_send, False, lane.focal.assets),
                     direction(left, right, lane.required_send, lane.required_receive, True, lane.counterparty.assets)))
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


def generate_guided_strategic_packages(lanes, *, as_of, bounds, market_values, economic_tolerance, pick_rounds=None):
    if as_of.tzinfo is None: raise ValueError('search time must be timezone-aware')
    if economic_tolerance is not None and (not isfinite(economic_tolerance) or economic_tolerance<0): raise ValueError('economic tolerance must be finite and nonnegative')
    if not market_values or economic_tolerance is None:
        return generate_strategic_packages(lanes, as_of=as_of, bounds=bounds)
    # A small exploration reserve retains unusual large structures; most visits
    # construct purposeful packages. This is a compute allocation, not a score.
    exploration = max(1, bounds.max_pair_visits // 8)
    guided_limit = bounds.max_pair_visits-exploration
    def path(lane):
        return ('owner_history' if lane.purpose.kind=='observed_acquisition' else 'team_purpose') if lane.purpose else 'ordinary'
    queues={name:deque() for name in ('ordinary','team_purpose','owner_history')}
    for lane in lanes:
        queues[path(lane)].append((lane,_lane_stream(lane,bounds=bounds,values=market_values,tolerance=economic_tolerance,pick_rounds=pick_rounds)))
    # Resource allocation only: ordinary discovery keeps half the guided turns
    # when all paths have work. Empty paths yield their turns to available work.
    schedule=deque(('ordinary','ordinary','team_purpose','owner_history'))
    by_id = {}; hypotheses = {}; visits = 0; groups = set(); path_visits=Counter()
    while any(queues.values()) and visits < guided_limit and len(by_id) < bounds.max_candidates:
        name=schedule[0];schedule.rotate(-1)
        if not queues[name]:continue
        lane, stream = queues[name].popleft()
        try:
            send, receive = next(stream)
        except StopIteration:
            continue
        visits += 1; path_visits[name]+=1; groups.add((lane.name, lane.counterparty.team_id))
        packages = [TradePackageSeed(team_id=team, assets=assets, canonical_id=canonical_package_id(team, assets))
                    for team, assets in ((lane.focal.team_id, send), (lane.counterparty.team_id, receive))]
        seed = generate_bilateral_trade_proposals((packages[0],), (packages[1],), as_of=as_of,
            policy=TradePairSearchPolicy(max_candidate_pairs=1)).proposals[0]
        by_id.setdefault(seed.point_id, seed)
        hypotheses.setdefault(seed.point_id, set()).add(lane.name)
        for leg in (send, receive):
            late = [a for a in leg if isinstance(a, PickAsset)]
            if len(leg)==3 and len(late)==2 and any(isinstance(a,PlayerAsset) for a in leg) and all((pick_rounds or {}).get(a,0)>=2 for a in late):
                hypotheses[seed.point_id].add('funded_later_pick_terms')
        queues[name].append((lane, stream))
    extra, diagnostics = generate_strategic_packages(lanes, as_of=as_of,
        bounds=bounds.model_copy(update={'max_pair_visits':bounds.max_pair_visits-visits,
                                        'max_candidates':bounds.max_candidates}))
    for row in extra:
        if row.seed.point_id not in by_id and len(by_id) >= bounds.max_candidates:
            break
        by_id.setdefault(row.seed.point_id, row.seed)
        hypotheses.setdefault(row.seed.point_id, set()).update(row.hypotheses)
    seeds = tuple(StrategicSeed(seed, tuple(sorted(hypotheses[key]))) for key, seed in by_id.items())
    return seeds, {**diagnostics, 'candidate_count':len(seeds),
        'pair_visits':visits+diagnostics['pair_visits'], 'duplicate_pair_visits':visits+diagnostics['pair_visits']-len(seeds), 'guided_pair_visits':visits,
        'exploration_pair_visits':diagnostics['pair_visits'], 'guided_path_visits':dict(path_visits), 'funded_term_window_limit':bounds.ingredients_per_side,
        'counterparties_visited':len({team for _,team in groups} | {s.seed.proposal.side_b.team_id for s in extra}),
        'shapes':dict(Counter(f'{len(s.seed.proposal.side_a.sends)}_for_{len(s.seed.proposal.side_b.sends)}' for s in seeds)),
        'hypotheses':dict(Counter(h for s in seeds for h in s.hypotheses)),
        'package_enumeration':'bounded_guided_packages_with_lazy_exploration',
        'interpretation':'Market envelope screens negotiation structure only; Decision evaluates actual team gains and costs'}
