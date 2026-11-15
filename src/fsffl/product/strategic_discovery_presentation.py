"""Categorical first-read organization, without changing Decision or Search order.

The current lineup coordinate is explicitly a preliminary proxy, never an outcome.
Known priority losses remain visible even when final competitive effects are unknown.
"""
from math import isfinite


def discovery_display_context(row):
    if row.get('evidence_status') != 'pre_simulation_screened':
        return {'group': 'needs_evidence', 'reason': 'Preliminary effects are incomplete.'}
    assessment = row.get('objective_assessment') or {}
    screen=row.get('preliminary_decision_screen') or {}
    if (row.get('preliminary_economic_band') in ('focal_economic_strain','counterparty_economic_strain')
        or any((screen.get(side) or {}).get('shape') == 'dominated' for side in ('focal','counterparty'))):
        return {'group':'priority_concern','reason':'The package needs better terms before it is a plausible opportunity.'}

    sides = []
    uses_proxy = False
    for key, screen_side in (('side_a', 'focal'), ('side_b', 'counterparty')):
        side = assessment.get(key) or {}
        if side.get('protected_players_lost'):
            return {'group': 'priority_concern', 'reason': 'A protected player would be lost.'}
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
                'reason': 'Known losses in a franchise’s requested priorities, with no demonstrated offset in those priorities.'}
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
                    return {**common,'group':'needs_evidence','reason':'Future contribution tradeoffs without a Current lineup benefit need further review.'}
            return {**common, 'group': 'priority_tradeoff',
                    'reason': 'Both sides have preliminary priority gains, with sacrifices that need review.'}
        return {**common, 'group': 'preliminary_fit',
                'reason': 'Both sides have preliminary priority gains and no known loss in their requested priorities.'}
    return {**common, 'group': 'needs_evidence',
            'reason': 'Priority benefits remain incomplete or no gain has been demonstrated for both sides.'}
