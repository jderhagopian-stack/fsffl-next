"""Compare like-for-like screened effects; no new value, utility or Decision score."""
from math import isfinite


def _number(value):
    return value if isinstance(value,(float,int)) and not isinstance(value,bool) and isfinite(value) else None


def counter_effects(result, focal_id, other_id):
    screen=result.get('preliminary_bilateral_screen') or {}
    horizons=result.get('horizon_asset_economics') or {}
    effects={}
    for team,key,screen_key in ((focal_id,'side_a','focal'),(other_id,'side_b','counterparty')):
        values={'current':_number((screen.get(screen_key) or {}).get('starter_points_delta'))}
        for horizon in ('three_year','career'):
            row=(((horizons.get(horizon) or {}).get('roster_adjusted') or {}).get(key)) or {}
            values[horizon]=_number(row.get('roster_adjusted_intrinsic_delta')) if row.get('team_id')==team and row.get('status')=='complete' else None
        effects[team]=values
    return {'basis':screen.get('current_points_basis'),'teams':effects}


def review_counter(seed, candidate, *, display_group):
    improved=[];worsened=[];new_losses=[];missing=[]
    for team,values in seed['teams'].items():
        for metric,before in values.items():
            after=candidate['teams'].get(team,{}).get(metric)
            if before is None or after is None or (metric=='current' and (seed['basis'] not in ('remaining_regular_season_weekly_mean','optimized_horizon_lineup') or seed['basis']!=candidate['basis'])):
                missing.append({'team_id':team,'metric':metric});continue
            row={'team_id':team,'metric':metric,'before':before,'after':after}
            # The existing preliminary Current screen uses 1e-9 solely as a
            # floating-point guard. Native horizons retain their own strict sign.
            tolerance=1e-9 if metric=='current' else 0.
            if before < -tolerance:
                if after>before+tolerance:improved.append({**row,'resolved':after>=-tolerance})
                elif after<before-tolerance:worsened.append(row)
            elif after < -tolerance:new_losses.append(row)
    eligible=display_group in ('preliminary_fit','priority_tradeoff')
    status=('incomplete' if missing else 'improves_terms' if eligible and improved and not worsened and not new_losses
            else 'alternative' if eligible and not improved and not worsened and not new_losses
            else 'tradeoff' if eligible and improved else 'needs_work')
    return {'status':status,'improved':improved,'worsened':worsened,'new_losses':new_losses,
        'missing':missing,'display_group':display_group,'effects':candidate,
        'decision_effect':'no_disposition_change','simulation_backed':False}
