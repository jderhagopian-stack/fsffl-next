"""Decision-owned preliminary priority interpretation; no final action authority.

Current/market-only dominance is not dominance over requested future objectives.
Asset contribution is not optimized franchise utility. Mixed priorities stay mixed.
"""
from math import isfinite


def _priority_group(row):
    if row.get('evidence_status') != 'pre_simulation_screened':
        return {'group': 'needs_evidence', 'limiting_gate':'incomplete_screen', 'reason': 'Preliminary effects are incomplete.'}
    assessment = row.get('objective_assessment') or {}
    screen=row.get('preliminary_decision_screen') or {}
    if row.get('preliminary_economic_band') in ('focal_economic_strain','counterparty_economic_strain'):
        return {'group':'priority_concern','limiting_gate':'market_feasibility','reason':'The package needs better terms before it is a plausible opportunity.'}

    sides = []
    uses_proxy = False
    for key, screen_side in (('side_a', 'focal'), ('side_b', 'counterparty')):
        side = assessment.get(key) or {}
        if side.get('protected_players_lost'):
            return {'group': 'priority_concern', 'limiting_gate':'protected_asset', 'reason': 'A protected player would be lost.'}
        goals = (side.get('context') or {}).get('objectives') or ()
        directions = []
        for goal in goals:
            if goal == 'current_competitiveness':
                screen = row.get('preliminary_decision_screen') or {}
                value = (screen.get(screen_side) or {}).get('starter_points_delta')
                known = (screen.get('current_points_basis') in (
                    'remaining_regular_season_weekly_mean', 'optimized_horizon_lineup')
                    and isinstance(value, (float, int)) and isfinite(value))
                directions.append(None if not known else (value > 1e-9) - (value < -1e-9))
                uses_proxy = uses_proxy or known
            else:
                metrics = [m for m in side.get('metrics', ()) if m.get('objective') == goal]
                if not metrics:
                    directions.append(None)
                for metric in metrics:
                    value = metric.get('delta')
                    if not metric.get('authoritative') or not isinstance(value, (float, int)) or not isfinite(value):
                        directions.append(None)
                    else:
                        direction = (value > 0) - (value < 0)
                        directions.append(direction if metric.get('higher_is_better', True) else -direction)
        sides.append({'gain': 1 in directions, 'loss': -1 in directions,
                      'unknown': not goals or None in directions})
    common = {'current_uses_lineup_proxy': uses_proxy, 'decision_effect': 'no_disposition_change'}
    if any(s['loss'] and not s['gain'] for s in sides):
        return {**common, 'group': 'priority_concern',
                'limiting_gate':'priority_loss_without_offset', 'reason': 'Known losses in a franchise’s requested priorities, with no demonstrated offset in those priorities.'}
    if all(s['gain'] and not s['unknown'] for s in sides):
        if any(s['loss'] for s in sides):
            # A calendar-window swap between future ledgers does not establish
            # a useful Current-priority franchise improvement. Keep it available
            # for explicit review rather than leading the shortlist.
            for key,screen_side in (('side_a','focal'),('side_b','counterparty')):
                assessed=assessment.get(key) or {}
                goals=(assessed.get('context') or {}).get('objectives') or ()
                points=(screen.get(screen_side) or {}).get('starter_points_delta')
                future_loss=any(m.get('objective') in goals and m.get('objective') in ('three_year_contribution','career_contribution')
                    and m.get('authoritative') and isinstance(m.get('delta'),(float,int)) and m['delta'] < -1e-9 for m in assessed.get('metrics',()))
                if ('current_competitiveness' in goals and isinstance(points,(float,int))
                    and abs(points)<=1e-9 and future_loss):
                    return {**common,'group':'needs_evidence','limiting_gate':'no_current_offset_for_future_loss','reason':'Future contribution tradeoffs without a Current lineup benefit need further review.'}
            return {**common, 'group': 'priority_tradeoff',
                    'limiting_gate':'mixed_priority_effects', 'reason': 'Both sides have preliminary priority gains, with sacrifices that need review.'}
        return {**common, 'group': 'preliminary_fit',
                'limiting_gate':'requested_priority_gains', 'reason': 'Both sides have preliminary priority gains and no known loss in their requested priorities.'}
    return {**common, 'group': 'needs_evidence',
            'limiting_gate':'unresolved_priority_gain', 'reason': 'Priority benefits remain incomplete or no gain has been demonstrated for both sides.'}


def assess_discovery_priorities(row):
    """Consume the existing native channels without scoring across horizons.

    Market feasibility remains a separate constraint. Protected assets and known
    requested losses without offsets cannot be promoted. Missing evidence stays
    unresolved; the Current coordinate is only the existing lineup proxy.
    """
    result=_priority_group(row)
    screen=row.get('preliminary_decision_screen') or {}
    old_veto=(row.get('evidence_status')=='pre_simulation_screened' and any(
        (screen.get(side) or {}).get('shape')=='dominated' for side in ('focal','counterparty')))
    legacy='priority_concern' if old_veto else result['group']
    return {**result,'authority':'decision','model_version':'priority-aware-discovery-v1',
        'legacy_group':legacy,'current_market_veto_removed':legacy!=result['group'],
        'future_measure':'cut_adjusted_asset_contribution',
        'future_roster_utility_estimated':False,'confirmed_mutual_benefit':False}
