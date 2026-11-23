"""Cheap, request-local counter hypotheses; all selected packages are evaluated.

Raw asset arithmetic orders search only. It excludes mandatory cuts, lineup
interaction and uncertainty, so it must never be shown as a transaction effect.
No dimensions are added together or converted into a common score.
"""
from collections import deque
from math import isfinite


def _key(asset):
    return f'{asset.kind}:{asset.player_id if asset.kind == "player" else asset.pick_id}'


def order_counter_hypotheses(seed, neighbors, *, seed_effects, published, starters, history_matches=None):
    """Interleave distinct repair questions, then small structural alternatives.

    Each native horizon/team cost gets its own queue, ordered by closing the original
    shortfall with the least extra compensation in that same horizon. Current-loss queues try retaining a
    traded starter and substituting bench/pick compensation. This is a hypothesis,
    not an assertion that bench players are expendable or that cuts are harmless.
    The existing optimizer, cuts, priorities and counter review decide the result.
    """
    if not seed_effects or not neighbors:
        return neighbors
    teams = (seed.focal_package.team_id, seed.counterparty_package.team_id)
    def packages(point):
        return (point.focal_package, point.counterparty_package)
    original = tuple({_key(a): a for a in p.assets} for p in packages(seed))
    def native_net(point, horizon, side):
        totals = []
        for package in packages(point):
            values = []
            for a in package.assets:
                if a.kind not in ('player', 'pick'):
                    return None
                table = published.values if a.kind == 'player' else published.pick_values
                value = table.get(horizon, {}).get(a.player_id if a.kind == 'player' else a.pick_id)
                if value is None or not isfinite(value):
                    return None
                values.append(value)
            totals.append(sum(values))
        return totals[1-side] - totals[side]
    # Smaller structures remain available, even if no repair can be inferred.
    def structural(point):
        return (sum(len(p.assets) for p in packages(point)), point.point_id)
    ordered = sorted(neighbors, key=structural)
    queues = []
    for side, team in enumerate(teams):
        effects = seed_effects['teams'].get(team, {})
        if effects.get('current') is not None and effects['current'] < -1e-9:
            sent_starters = {a.player_id for a in original[side].values()
                             if a.kind == 'player' and a.player_id in starters.get(team, frozenset())}
            options = []
            for point in ordered:
                offered = {_key(a): a for a in packages(point)[side].assets}
                retained = any(f'player:{pid}' not in offered for pid in sent_starters)
                additions = [a for k,a in offered.items() if k not in original[side]]
                if retained and all(a.kind == 'pick' or (a.kind == 'player' and
                    a.player_id not in starters.get(team, frozenset())) for a in additions):
                    options.append(point)
            if options:
                queues.append(deque(options))
        for horizon in ('three_year', 'career'):
            loss = effects.get(horizon)
            base = native_net(seed, horizon, side)
            if loss is None or loss >= 0 or base is None:
                continue
            repairs = []
            for point in ordered:
                net = native_net(point, horizon, side)
                if net is not None and net > base:
                    change = net-base
                    # First try closing this particular shortfall; then partial
                    # repair. Only like-unit differences enter this ordering.
                    repairs.append(((0, change + loss) if change >= -loss else
                                    (1, -loss - change), structural(point), point))
            if repairs:
                queues.append(deque(p for _,_,p in sorted(repairs, key=lambda row:row[:2])))
    # Round robin avoids allowing one horizon or franchise to consume the budget.
    # A generic lane keeps alternative structures reachable, not only hypotheses.
    if history_matches:
        # A universal match duplicates the structural queue and takes another
        # round-robin turn without adding an independent search question.
        # Keep selective precedents; absence never excludes an unfamiliar deal.
        from fsffl.trade_decision.contextual_precedents import precedent_category
        observed = sorted((p for p in ordered if history_matches.get(p.point_id)),
            key=lambda p:(precedent_category(history_matches[p.point_id]),structural(p)))
        if 0 < len(observed) < len(ordered) or (observed and observed!=ordered):
            queues.append(deque(observed))
    queues.append(deque(ordered))
    result = []
    seen = set()
    while queues:
        pending = []
        for queue in queues:
            while queue and queue[0].point_id in seen:
                queue.popleft()
            if queue:
                point = queue.popleft()
                seen.add(point.point_id)
                result.append(point)
            if queue:
                pending.append(queue)
        queues = pending
    return tuple(result)
