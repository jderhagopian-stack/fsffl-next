"""Curate evaluated search alternatives without choosing a cross-horizon price.

Decision's directional tradeoff is evidence to inspect, not permission to promote
any positive coordinate. Search optimizes the focal owner's alternatives subject
to both-owner priority compatibility, preserving every evaluated package.
"""
from math import isfinite


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def focal_effects(row):
    """Comparable native coordinates, never a sum or a composite score."""
    saved=row.get('_shortlist_effects')
    if isinstance(saved,(list,tuple)) and len(saved)==4 and all(_number(v) for v in saved):
        return tuple(saved)
    screen = row.get('preliminary_decision_screen') or {}
    if screen.get('current_points_basis') != 'remaining_regular_season_weekly_mean':
        return None
    values = [(screen.get('focal') or {}).get('starter_points_delta')]
    for horizon in ('three_year', 'career'):
        side = (((row.get('horizon_asset_economics') or {}).get(horizon) or {}).get('roster_adjusted') or {}).get('side_a') or {}
        if side.get('status') != 'complete':
            return None
        values.append(side.get('roster_adjusted_intrinsic_delta'))
    market = (row.get('roster_adjusted_market_net') or {}).get('side_a') or {}
    if market.get('status') != 'complete':
        return None
    values.append(market.get('roster_adjusted_market_delta'))
    return tuple(values) if all(_number(v) for v in values) else None


def curate_shortlist(rows):
    """Only demonstrated priority fits lead automatically; unresolved terms stay.

    In particular, no magnitude of gain in one unit automatically pays for a loss
    in another. The existing directional group and final Decision remain intact.
    A focused future direction can qualify with a visible Current sacrifice.
    """
    for row in rows:
        group = (row.get('display_context') or {}).get('group')
        row['shortlist_quality'] = {
            'status': 'shortlist' if group == 'preliminary_fit' else
                      'needs_terms' if group == 'priority_tradeoff' else 'review',
            'reason': 'priority_compatible' if group == 'preliminary_fit' else
                      'selected_priority_conflict' if group == 'priority_tradeoff' else 'existing_screen',
            'replaced_by_point_ids': [], 'alternative_point_ids': [],
            'authority': 'search_curation', 'decision_changed': False,
            'model_version': 'discovery-shortlist-v1:native-coordinate-alternatives',
        }
    # Counterparty compatibility is a constraint, not a goal to maximize the
    # other owner's gain at the managed owner's expense. Only already fitting
    # alternatives compete; different units remain separate Pareto coordinates.
    comparable = [(r, focal_effects(r)) for r in rows
                  if r['shortlist_quality']['status'] == 'shortlist']
    comparable = [(r, v) for r, v in comparable if v is not None]
    for row, values in comparable:
        better = [other['point_id'] for other, candidate in comparable
                  if other is not row and all(a >= b - 1e-9 for a, b in zip(candidate, values))
                  and any(a > b + 1e-9 for a, b in zip(candidate, values))]
        if better:
            row['shortlist_quality'].update(status='alternative', reason='better_focal_alternative', replaced_by_point_ids=better)
    # Fold identical focal exchanges only AFTER both owners have actually been
    # screened. Different counterparties' cuts/preferences are never assumed equal.
    groups = {}
    for row, values in comparable:
        if row['shortlist_quality']['status'] != 'shortlist':
            continue
        family = row.get('focal_package_family')
        if family is not None:
            groups.setdefault((family, values), []).append(row)
    for group in groups.values():
        first, *alternatives = group
        first['shortlist_quality']['alternative_point_ids'] = [r['point_id'] for r in alternatives]
        for row in alternatives:
            row['shortlist_quality'].update(status='alternative', reason='equivalent_focal_exchange', replaced_by_point_ids=[first['point_id']])


def shortlist_receipt(row):
    """Small cursor receipt, not a retained State/model/response graph."""
    return {'point_id': row['point_id'],
            'display_context': {'group': (row.get('display_context') or {}).get('group')},
            'focal_package_family': row.get('focal_package_family'),
            '_shortlist_effects': focal_effects(row)}
