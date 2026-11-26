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
    """Either owner may weigh inferred priorities; explicit sacrifices stay review.

    Consume Decision's existing per-owner directional interpretation, not another
    priority model. Full Current funding is checked separately before leading.
    """
    if '_inferred_timeline_choice' in row:
        return row['_inferred_timeline_choice'] is True
    display=row.get('display_context') or {}
    if display.get('group')!='priority_tradeoff':return False
    effects=display.get('priority_effects') or {}
    assessment=row.get('objective_assessment') or {}
    if set(effects)!= {'side_a','side_b'}:return False
    for side,effect in effects.items():
        if not effect.get('gain') or effect.get('unknown'):return False
        if not effect.get('loss'):continue
        context=(assessment.get(side) or {}).get('context') or {}
        if context.get('source')!='calculated_state_posture_hypothesis_v1' or context.get('explicitly_directed'):
            return False
    return True


def goal_order(row):
    if row.get('_shortlist_goals'):return row['_shortlist_goals']
    context=((row.get('objective_assessment') or {}).get('side_a') or {}).get('context') or {}
    from .strategic_goals import exploration_goals
    return exploration_goals(context.get('objectives') or ('current_competitiveness',),
        inferred=context.get('source')=='calculated_state_posture_hypothesis_v1' and not context.get('explicitly_directed'),
        team_id=context.get('team_id') or row.get('focal_team_id',''))


def comparison_effects(row):
    """Full outcomes and the lineup approximation inhabit DIFFERENT domains."""
    native=focal_effects(row)
    if native is None:return None
    proof=row.get('screen_confirmation') or {}
    if not proof:return ('preliminary',),native,()
    fields=('source_state_id','publication_generation_id','baseline_simulation_input_fingerprint',
            'native_input_fingerprint','competitive_policy_version')
    team=row.get('focal_team_id') or (((row.get('objective_assessment') or {}).get('side_a') or {}).get('context') or {}).get('team_id')
    competitive=(proof.get('competitive') or {}).get(team) or {}
    values=tuple(competitive.get(k) for k in ('expected_wins','playoff_probability','first_place_probability','championship_probability'))
    if (proof.get('status')!='verified' or proof.get('simulation_count')!=50_000
            or not all(proof.get(k) for k in fields) or not all(_number(v) for v in values)):
        return None  # Never fall back to a weaker proxy when full evidence is incomplete.
    resilience=(proof.get('resilience') or {}).get(team)
    if not _number(resilience):return None
    material=next((v for v in proof.get('material',{}).values() if isinstance(v,dict) and v.get('team_id')==team),{})
    bands=tuple(material.get(k) for k in ('expected_wins','playoff_probability','first_place_probability','championship_probability','largest_single_player_lineup_drop'))
    return ('confirmed',*(proof[k] for k in fields),proof['simulation_count']),(*values,-resilience,*native[1:]),bands


def _dominates(left,right,market_tolerance,competitive_policy=None):
    if left is None or right is None or left[0]!=right[0]:return False
    a,b=left[1],right[1]
    competitive_equal=False;resilience_equal=False
    if left[0][0]=='confirmed' and competitive_policy is not None and left[0][-2]==competitive_policy.model_version:
        from fsffl.trade_decision.materiality import classify_positive_delta, MaterialityDirection
        thresholds=(competitive_policy.expected_wins_abs,competitive_policy.playoff_probability_abs,
            competitive_policy.first_place_probability_abs,competitive_policy.championship_probability_abs)
        known={'immaterial','material_gain','material_loss'}
        same_bands=left[2][:4]==right[2][:4] and all(b in known for b in left[2][:4])
        competitive_equal=same_bands and all(t is not None and classify_positive_delta(x-y,absolute_threshold=t)==MaterialityDirection.IMMATERIAL
            for x,y,t in zip(a[:4],b[:4],thresholds))
        resilience_equal=(left[2][4]==right[2][4] and left[2][4] in known and classify_positive_delta(a[4]-b[4],absolute_threshold=competitive_policy.lineup_drop_abs)==MaterialityDirection.IMMATERIAL)
    ignored=set(range(4)) if competitive_equal else set()
    if resilience_equal:ignored.add(4)
    relevant=[i for i in range(len(a)-1) if i not in ignored]
    # Existing Decision indifference can establish comparable Current benefit;
    # a strictly smaller future price can then win. No odds-to-Career exchange
    # rate is inferred. Outside that band use independent Pareto coordinates.
    return (all(a[i]>=b[i]-1e-9 for i in relevant) and a[-1]>=b[-1]-market_tolerance-1e-9
        and (any(a[i]>b[i]+1e-9 for i in relevant) or a[-1]>b[-1]+market_tolerance+1e-9))


def _current_order(choices):
    """Competitive Pareto layers; incomparable outcomes retain stable alternatives."""
    remaining=list(choices);ordered=[]
    def packet(r):
        value=comparison_effects(r)
        if value is None:return None
        domain,coordinates=value[:2]
        return domain,coordinates[:4] if domain[0]=='confirmed' else coordinates[:1]
    while remaining:
        front=[r for r in remaining if not any(o is not r and packet(o) is not None and packet(r) is not None
            and packet(o)[0]==packet(r)[0] and all(x>=y-1e-9 for x,y in zip(packet(o)[1],packet(r)[1]))
            and any(x>y+1e-9 for x,y in zip(packet(o)[1],packet(r)[1])) for o in remaining)]
        front.sort(key=lambda r:r['point_id']);ordered.extend(front)
        remaining=[r for r in remaining if r not in front]
    return ordered


def rank_choices(rows):
    """Rotate independent goal orders; no present/future conversion or master score."""
    choices=[r for r in rows if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')]
    goals=next((goal_order(r) for r in choices),())
    axes={'current_competitiveness':0,'three_year_contribution':1,'career_contribution':2,'market_capital':3}
    orders=[]
    for g in goals:
        if g not in axes:continue
        eligible=[r for r in choices if (focal_effects(r) or (float('-inf'),)*4)[axes[g]]>1e-9]
        if g=='current_competitiveness':
            # Eligibility of a confirmed Current direction also consumes actual
            # competitive gains, not the sign of its old weekly proxy.
            confirmed=[]
            for row in choices:
                packet=comparison_effects(row)
                if packet is None or packet[0][0]!='confirmed':continue
                team=row.get('focal_team_id') or (((row.get('objective_assessment') or {}).get('side_a') or {}).get('context') or {}).get('team_id')
                material=next((v for v in (row.get('screen_confirmation') or {}).get('material',{}).values()
                    if isinstance(v,dict) and v.get('team_id')==team),{})
                effects=[material.get(k) for k in ('expected_wins','playoff_probability','first_place_probability','championship_probability')]
                if 'material_gain' in effects and 'material_loss' not in effects:confirmed.append(row)
            eligible=confirmed+[r for r in eligible if not r.get('screen_confirmation')]
            orders.append(_current_order(eligible))
        else:orders.append(sorted(eligible,key=lambda r:(-focal_effects(r)[axes[g]],r['point_id'])))
    seen=set();rank=0
    while any(orders):
        for order in orders:
            while order and order[0]['point_id'] in seen:order.pop(0)
            if not order:continue
            row=order.pop(0);seen.add(row['point_id']);row['shortlist_quality']['rank']=rank;rank+=1
    # A zero-Current depth conversion is a separate intentional future option.
    for row in sorted(choices,key=lambda r:r['point_id']):
        if row['point_id'] not in seen:
            row['shortlist_quality']['rank']=rank;rank+=1


def curate_shortlist(rows, *, market_tolerance=0.0, require_current_confirmation=False, competitive_policy=None):
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
            'status': 'review' if unresolved_future_window(row) else 'strategic_tradeoff' if inferred_timeline_choice(row) else 'shortlist' if group in ('preliminary_fit','depth_conversion_hypothesis') else
                      'needs_terms' if group == 'priority_tradeoff' else 'review',
            'reason': 'unconfirmed_future_window_preference' if unresolved_future_window(row) else 'inferred_timeline_choice' if inferred_timeline_choice(row) else 'bench_depth_future_hypothesis' if group == 'depth_conversion_hypothesis' else 'priority_compatible' if group == 'preliminary_fit' else
                      'selected_priority_conflict' if group == 'priority_tradeoff' else 'existing_screen',
            'replaced_by_point_ids': [], 'alternative_point_ids': [],
            'authority': 'search_curation', 'decision_changed': False,
            'market_indifference_threshold':market_tolerance,
            'model_version': 'discovery-shortlist-v3:competitive-evidence-and-independent-goals',
        }
    from .confirmation_quality import apply_confirmation_status
    apply_confirmation_status(rows,require_confirmation=require_current_confirmation)
    # Counterparty compatibility is a constraint, not a goal to maximize the
    # other owner's gain at the managed owner's expense. Only already fitting
    # alternatives compete; different units remain separate Pareto coordinates.
    comparable = [(r, comparison_effects(r)) for r in rows
                  if r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff')]
    comparable = [(r, v) for r, v in comparable if v is not None]
    for row, values in comparable:
        better = [other['point_id'] for other, candidate in comparable
                  if other is not row and _dominates(candidate,values,market_tolerance,competitive_policy)]
        if better:
            row['shortlist_quality'].update(status='alternative', reason='better_focal_alternative', replaced_by_point_ids=better,
                comparison_basis=values[0][0])
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
        # Different payments can be real timeline choices for the SAME target.
        # Dominance above removes genuinely worse terms; link the rest without
        # letting an arbitrary first goal erase an incomparable strategic choice.
        for row in alternatives:
            row['shortlist_quality']['alternative_point_ids'].extend(
                r['point_id'] for r in alternatives if r is not row)
    rank_choices(rows)


def shortlist_receipt(row):
    """Small cursor receipt, not a retained State/model/response graph."""
    from .confirmation_quality import current_required_teams
    return {'point_id': row['point_id'],
            '_current_required_teams':current_required_teams(row),
            'screen_confirmation':row.get('screen_confirmation'),
            'focal_team_id':row.get('focal_team_id'),
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
