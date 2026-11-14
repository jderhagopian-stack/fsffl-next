"""Reuse canonical picks and published slot evidence without inventing Intrinsic."""
from .pick_location_runtime import build_next_season_pick_projections
from .trade_value_adapter import cardinal_market_profiles


def discovery_pick_context(runtime, rows, *, read=None):
    refs={a['asset_ref'] for row in rows for a in (*row['send'],*row['receive']) if a['asset_ref'].startswith('pick:')}
    if not refs:
        return {}
    state=runtime.league_state
    owners={p.pick_id:p.owner_team_id for p in state.pick_ownership}
    profiles=cardinal_market_profiles(runtime.value_evidence)
    baseline=runtime.simulation_analytics
    projections={}
    if baseline is not None and getattr(getattr(baseline,'scenario_preparation',None),'source_state_id',None)==state.state_id:
        projections={p.pick_id:p for p in build_next_season_pick_projections(state,baseline.simulation_result,
            variant_values=getattr(runtime.value_evidence,'pick_variant_market_values',()))}
    result={}
    for pick in state.draft_picks:
        ref='pick:'+pick.pick_id
        if ref not in refs:
            continue
        profile=profiles.get(pick.pick_id)
        market=profile.market_price if profile is not None and profile.asset_kind=='pick' else None
        projection=projections.get(pick.pick_id)
        native = read.pick_sources.get(pick.pick_id) if read is not None else None
        result[ref]={'pick_id':pick.pick_id,'season':pick.season,'round':pick.round,
            'original_team_id':pick.original_team_id,'owner_team_id':owners.get(pick.pick_id),
            'market_value':market.distribution.mean if market else None,
            'market_unit':market.scale.unit_label if market else None,
            'expected_slot':projection.expected_slot if projection else None,
            'slot_source':projection.authority_status if projection else 'unavailable',
            'slot_model_version':projection.simulation_model_version if projection else None,
            'three_year_intrinsic_status':'bounded_provisional' if native else 'unavailable',
            'career_intrinsic_status':'bounded_provisional' if native else 'unavailable',
            'three_year_intrinsic':read.pick_values['three_year'].get(pick.pick_id) if native else None,
            'career_intrinsic':read.pick_values['career'].get(pick.pick_id) if native else None,
            'native_source':dict(native) if native else None,
            'intrinsic_slot_ranges':{h:{'low':native[h+'_slot_low'],'high':native[h+'_slot_high']}
                for h in ('three_year','career') if native is not None and h+'_slot_low' in native},
            'slot_uncertain_prior':bool(native and native.get('probability_basis')=='exchangeable_future_slot_prior'),
            'outside_three_year_window':bool(native and native.get('three_year_point_basis')=='calendar_structural_zero'),
            'interpretation':'Preliminary draft-pick estimate' if native else 'Pick Intrinsic unavailable'}
    return result
