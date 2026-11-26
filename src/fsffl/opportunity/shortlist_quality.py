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


def unresolved_future_window(row):
    """Do not sell a narrow-window swap as a general inferred future upgrade.

    A 3-Year gain with both a Current and Career loss can be intentional, but
    inferred posture alone does not establish that preference. Keep it for review;
    explicit focal direction and final Decision authority remain intact.
    """
    if '_unresolved_future_window' in row:
        return row['_unresolved_future_window'] is True
    assessment=row.get('objective_assessment') or {}
    for side,screen_side in (('side_a','focal'),('side_b','counterparty')):
        context=(assessment.get(side) or {}).get('context') or {}
        if context.get('source')!='calculated_state_posture_hypothesis_v1' or context.get('explicitly_directed'):
            continue
        current=((row.get('preliminary_decision_screen') or {}).get(screen_side) or {}).get('starter_points_delta')
        values=[]
        for h in ('three_year','career'):
            net=(((row.get('horizon_asset_economics') or {}).get(h) or {}).get('roster_adjusted') or {}).get(side) or {}
            values.append(net.get('roster_adjusted_intrinsic_delta') if net.get('status')=='complete' else None)
        if _number(current) and all(_number(v) for v in values) and current < -1e-9 and values[0]>1e-9 and values[1] < -1e-9:
            return True
    return False


def inferred_timeline_choice(row):
    """An inferred balanced lens permits a visible, evidence-backed sacrifice.

    Explicit directions remain untouched. The other owner still needs a gain
    without a conflicting requested loss; this is a search choice, not SUPPORT.
    """
    if '_inferred_timeline_choice' in row:
        return row['_inferred_timeline_choice'] is True
    if (row.get('display_context') or {}).get('group') != 'priority_tradeoff':
        return False
    assessment=row.get('objective_assessment') or {}
    context=(assessment.get('side_a') or {}).get('context') or {}
    if context.get('source')!='calculated_state_posture_hypothesis_v1' or context.get('explicitly_directed'):
        return False
    if len(context.get('objectives',()))<2:
        return False
    partner=assessment.get('side_b') or {}
    directions=[]
    for goal in (partner.get('context') or {}).get('objectives',()):
        if goal=='current_competitiveness':
            value=((row.get('preliminary_decision_screen') or {}).get('counterparty') or {}).get('starter_points_delta')
            if not _number(value):return False
            directions.append((value>1e-9)-(value < -1e-9))
        else:
            metrics=[m for m in partner.get('metrics',()) if m.get('objective')==goal]
            if not metrics:return False
            for metric in metrics:
                value=metric.get('delta')
                if not metric.get('authoritative') or not _number(value):return False
                directions.append(((value>1e-9)-(value < -1e-9))*(1 if metric.get('higher_is_better',True) else -1))
    return bool(directions) and 1 in directions and -1 not in directions


def goal_order(row):
    return row.get('_shortlist_goals') or ((row.get('objective_assessment') or {}).get('side_a') or {}).get('context',{}).get('objectives') or ('current_competitiveness',)


def rank_choices(rows):
    """Rotate native objective orders; no weighted or universal score."""
    choices=[r for r in rows if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')]
    goals=next((goal_order(r) for r in choices),())
    axes={'current_competitiveness':0,'three_year_contribution':1,'career_contribution':2,'market_capital':3}
    orders=[sorted((r for r in choices if (focal_effects(r) or (float('-inf'),)*4)[axes[g]]>1e-9),key=lambda r:(-(focal_effects(r) or (float('-inf'),)*4)[axes[g]],r['point_id']))
            for g in goals if g in axes]
    seen=set();rank=0
    while any(orders):
        for order in orders:
            while order and order[0]['point_id'] in seen:order.pop(0)
            if not order:continue
            row=order.pop(0);seen.add(row['point_id'])
            row['shortlist_quality']['rank']=rank;rank+=1


def curate_shortlist(rows, *, market_tolerance=0.0, require_current_confirmation=False):
    """Lead with priority fits and explicit tradeoff choices under inferred goals.

    In particular, no magnitude of gain in one unit automatically pays for a loss
    in another. The existing directional group and final Decision remain intact.
    A focused future direction can qualify with a visible Current sacrifice.
    """
    if not _number(market_tolerance) or market_tolerance<0:
        raise ValueError('Market indifference requires a finite nonnegative upstream threshold')
    for row in rows:
        group = (row.get('display_context') or {}).get('group')
        row['shortlist_quality'] = {
            'status': 'review' if unresolved_future_window(row) else 'strategic_tradeoff' if inferred_timeline_choice(row) else 'shortlist' if group == 'preliminary_fit' else
                      'needs_terms' if group == 'priority_tradeoff' else 'review',
            'reason': 'unconfirmed_future_window_preference' if unresolved_future_window(row) else 'inferred_timeline_choice' if inferred_timeline_choice(row) else 'priority_compatible' if group == 'preliminary_fit' else
                      'selected_priority_conflict' if group == 'priority_tradeoff' else 'existing_screen',
            'replaced_by_point_ids': [], 'alternative_point_ids': [],
            'authority': 'search_curation', 'decision_changed': False,
            'market_indifference_threshold':market_tolerance,
            'model_version': 'discovery-shortlist-v2:inferred-timeline-choices',
        }
    from .confirmation_quality import apply_confirmation_status
    apply_confirmation_status(rows,require_confirmation=require_current_confirmation)
    # Counterparty compatibility is a constraint, not a goal to maximize the
    # other owner's gain at the managed owner's expense. Only already fitting
    # alternatives compete; different units remain separate Pareto coordinates.
    comparable = [(r, focal_effects(r)) for r in rows
                  if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')]
    comparable = [(r, v) for r, v in comparable if v is not None]
    for row, values in comparable:
        better = [other['point_id'] for other, candidate in comparable
                  if other is not row and all(a >= b - 1e-9 for a, b in zip(candidate[:3], values[:3]))
                  and candidate[3]>=values[3]-market_tolerance-1e-9
                  and (any(a > b + 1e-9 for a, b in zip(candidate[:3],values[:3]))
                       or candidate[3]>values[3]+market_tolerance+1e-9)]
        if better:
            row['shortlist_quality'].update(status='alternative', reason='better_focal_alternative', replaced_by_point_ids=better)
    # Fold identical focal exchanges only AFTER both owners have actually been
    # screened. Different counterparties' cuts/preferences are never assumed equal.
    groups = {}
    for row, values in comparable:
        if row['shortlist_quality']['status'] not in ('shortlist','strategic_tradeoff'):
            continue
        family = row.get('focal_package_family')
        if family is not None:
            groups.setdefault((family, values), []).append(row)
    for group in groups.values():
        first, *alternatives = group
        first['shortlist_quality']['alternative_point_ids'] = [r['point_id'] for r in alternatives]
        for row in alternatives:
            row['shortlist_quality'].update(status='alternative', reason='equivalent_focal_exchange', replaced_by_point_ids=[first['point_id']])


    targets={}
    for row in rows:
        if row['shortlist_quality']['status'] not in ('shortlist','strategic_tradeoff'):
            continue
        target=row.get('_receiving_target') or tuple(sorted(a['asset_ref'] for a in row.get('receive',())))
        if not target:continue
        targets.setdefault(tuple(target),[]).append(row)
    for alternatives in targets.values():
        if len(alternatives)<2:continue
        axis={'current_competitiveness':0,'three_year_contribution':1,'career_contribution':2,'market_capital':3}.get(goal_order(alternatives[0])[0],0)
        axes={'current_competitiveness':0,'three_year_contribution':1,'career_contribution':2,'market_capital':3}
        priority_axes=tuple(dict.fromkeys((axis,*(axes[g] for g in goal_order(alternatives[0]) if g in axes),3)))
        alternatives.sort(key=lambda r:(tuple(-round((focal_effects(r) or (float('-inf'),)*4)[a],9) for a in priority_axes),r['point_id']))
        first,*rest=alternatives
        for other in rest:
            other['shortlist_quality'].update(status='alternative',reason='same_acquisition_different_terms',replaced_by_point_ids=[first['point_id']])
            first['shortlist_quality']['alternative_point_ids'].append(other['point_id'])
    rank_choices(rows)


def shortlist_receipt(row):
    """Small cursor receipt, not a retained State/model/response graph."""
    from .confirmation_quality import current_required_teams
    return {'point_id': row['point_id'],
            '_current_required_teams':current_required_teams(row),
            'screen_confirmation':row.get('screen_confirmation'),
            'counterparty_team_id':row.get('counterparty_team_id'),
            'send':[{'asset_ref':a['asset_ref']} for a in row.get('send',())],
            'receive':[{'asset_ref':a['asset_ref']} for a in row.get('receive',())],
            'roster_legality':[{'team_id':r['team_id'],'cuts':[{'player_id':c['player_id']} for c in r.get('cuts',())]} for r in row.get('roster_legality',())],
            'display_context': {'group': (row.get('display_context') or {}).get('group')},
            '_inferred_timeline_choice':inferred_timeline_choice(row),
            '_unresolved_future_window':unresolved_future_window(row),
            '_shortlist_goals':goal_order(row),
            '_receiving_target':row.get('_receiving_target') or sorted(a['asset_ref'] for a in row.get('receive',())),
            'focal_package_family': row.get('focal_package_family'),
            '_shortlist_effects': focal_effects(row)}
