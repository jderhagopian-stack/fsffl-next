"""Bounded native-horizon compensation hypotheses using existing owned assets."""
from math import isfinite
from fsffl.opportunity.frontier import make_frontier_point
from fsffl.opportunity.trade_universe import TradePackageSeed, canonical_package_id
from fsffl.state.models import PlayerAsset, PickAsset

_HORIZONS = {'three_year_contribution': 'three_year', 'career_contribution': 'career'}


def compensation_path(runtime, root, read, *, inventories, visits, max_steps=2, feedback=None, market_values=None, economic_tolerance=None):
    """Offer one/two assets to repair an observed requested native loss.

    Every child consumes the caller's normal full roster/cut/lineup screen. No
    provisional gain is called compensation until that screen confirms it.
    Existing 8-per-side/10-total geometry and protected/target filters still apply.
    """
    if read is None or root.get('evidence_status') != 'pre_simulation_screened':
        return
    assessment = root.get('objective_assessment') or {}
    if any((assessment.get(s) or {}).get('protected_players_lost') for s in ('side_a', 'side_b')):
        return
    legs = [[a['asset_ref'] for a in root['send']], [a['asset_ref'] for a in root['receive']]]
    teams = [runtime.selected_team_id, root['counterparty_team_id']]
    if len(set(teams))!=2 or any(t not in inventories for t in teams):return
    def value(asset, horizon):
        values = read.values if isinstance(asset, PlayerAsset) else read.pick_values
        key = asset.player_id if isinstance(asset, PlayerAsset) else asset.pick_id
        if isinstance(asset,PickAsset) and key not in getattr(read,'pick_sources',{}):return None
        number = values.get(horizon, {}).get(key)
        return number if isinstance(number, (int, float)) and isfinite(number) else None
    def ref(asset):
        return ('player:' + asset.player_id) if isinstance(asset, PlayerAsset) else ('pick:' + asset.pick_id)
    for recipient, label in enumerate(('side_a', 'side_b')):
        goals = (assessment.get(label, {}).get('context') or {}).get('objectives', ())
        deltas = {}
        for goal in goals:
            if goal not in _HORIZONS:
                continue
            horizon = _HORIZONS[goal]
            side = ((((root.get('horizon_asset_economics') or {}).get(horizon) or {}).get('roster_adjusted') or {}).get(label) or {})
            d = side.get('roster_adjusted_intrinsic_delta')
            if side.get('status') != 'complete' or not isinstance(d, (int, float)) or not isfinite(d):
                return
            deltas[horizon] = d
        if not any(d < -1e-9 for d in deltas.values()):
            continue
        donor = 1 - recipient
        lookups = [{ref(a):a for a in inventories[t].assets if isinstance(a,(PlayerAsset,PickAsset))} for t in teams]
        # Do not retain runtime/State objects outside this request. Ingredients
        # come from the caller's already filtered, protected inventories.
        packages = [[lookup.get(key) for key in leg] for lookup,leg in zip(lookups,legs)]
        if any(a is None for leg in packages for a in leg):
            return
        available = [a for a in inventories[teams[donor]].assets
                     if isinstance(a, (PlayerAsset, PickAsset)) and a not in packages[donor]
                     and all(value(a, h) is not None for h in deltas)]
        used = []
        parent = root['point_id']
        for depth in range(1, max_steps + 1):
            if len(packages[donor]) >= 8 or sum(map(len, packages)) >= 10:
                return
            loss = [h for h, d in deltas.items() if d < -1e-9]
            if not loss:
                return
            def within_market_envelope(asset):
                if market_values is None or economic_tolerance is None:return True
                proposed=[list(leg) for leg in packages]
                proposed[donor].append(asset)
                def price(a):return market_values.get(a.player_id if isinstance(a,PlayerAsset) else a.pick_id)
                if any(price(a) is None for leg in proposed for a in leg):return True
                totals=[sum(price(a) for a in leg) for leg in proposed]
                return abs(totals[0]-totals[1])<=economic_tolerance
            candidates = [a for a in available if a not in used and all(value(a, h) > 0 for h in loss)
                          and within_market_envelope(a)]
            if not candidates:
                return
            # First seek one asset that covers all remaining native deficits.
            # Among those, use the smallest surplus in the requested horizon
            # order; no arithmetic combines different horizon units.
            def key(a):
                return (not all(value(a, h) >= -deltas[h] for h in loss),
                        tuple(abs(value(a, h) + deltas[h]) for h in loss), ref(a))
            asset = min(candidates, key=key)
            if not visits.visit():
                return
            used.append(asset); packages[donor].append(asset)
            for h in deltas:
                deltas[h] += value(asset, h)
            seeds = [TradePackageSeed(team_id=t, assets=tuple(a), canonical_id=canonical_package_id(t, a)) for t, a in zip(teams, packages)]
            point = make_frontier_point(*seeds)
            yield point, {'root_point_id': root['point_id'], 'parent_point_id': parent,
                          'move': 'add_native_compensation', 'depth': depth,
                          'recipient_team_id': teams[recipient], 'hypothesis_only': True}
            parent = point.point_id
            actual=feedback(point.point_id) if feedback is not None else None
            if actual is not None:
                if actual.get('evidence_status')!='pre_simulation_screened':return
                for h in deltas:
                    side=((((actual.get('horizon_asset_economics') or {}).get(h) or {}).get('roster_adjusted') or {}).get(label) or {})
                    d=side.get('roster_adjusted_intrinsic_delta')
                    if side.get('status')!='complete' or not isinstance(d,(int,float)) or not isfinite(d):return
                    deltas[h]=d
        return
