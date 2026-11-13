"""Categorical first-read organization, without changing Decision or Search order.

The current lineup coordinate is explicitly a preliminary proxy, never an outcome.
Known priority losses remain visible even when final competitive effects are unknown.
"""
from math import isfinite


def discovery_display_context(row):
    if row.get('evidence_status') != 'pre_simulation_screened':
        return {'group': 'needs_evidence', 'reason': 'Preliminary effects are incomplete.'}
    assessment = row.get('objective_assessment') or {}
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
                directions.append(None if not known else (value > 0) - (value < 0))
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
            return {**common, 'group': 'priority_tradeoff',
                    'reason': 'Both sides have preliminary priority gains, with sacrifices that need review.'}
        return {**common, 'group': 'preliminary_fit',
                'reason': 'Both sides have preliminary priority gains and no known loss in their requested priorities.'}
    return {**common, 'group': 'needs_evidence',
            'reason': 'Priority benefits remain incomplete or no gain has been demonstrated for both sides.'}
