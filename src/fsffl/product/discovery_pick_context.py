"""Reuse canonical picks and published slot evidence without inventing Intrinsic."""
from .pick_location_runtime import build_next_season_pick_projections
from .trade_value_adapter import cardinal_market_profiles


def discovery_pick_context(runtime, rows):
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
        result[ref]={'pick_id':pick.pick_id,'season':pick.season,'round':pick.round,
            'original_team_id':pick.original_team_id,'owner_team_id':owners.get(pick.pick_id),
            'market_value':market.distribution.mean if market else None,
            'market_unit':market.scale.unit_label if market else None,
            'expected_slot':projection.expected_slot if projection else None,
            'slot_source':projection.authority_status if projection else 'unavailable',
            'slot_model_version':projection.simulation_model_version if projection else None,
            'three_year_intrinsic_status':'unavailable','career_intrinsic_status':'unavailable',
            'interpretation':'Draft-capital and slot evidence are separate from raw Shapley contribution; missing pick Intrinsic is not zero.'}
    return result
