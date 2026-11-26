"""Bounded finalist checks consume existing Trade Center authority, not a score."""
from .market_discovery_runtime import _proposal_from_row
from .trade_intrinsic_evidence import bind_trade_intrinsic_values
from .trade_objectives import validate_search_instructions, build_trade_objective_assessment
from .trade_simulation_runtime import build_post_trade_simulation_comparison
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution

from fsffl.opportunity.confirmation_quality import current_required_teams

COMPETITIVE_METRICS=('expected_wins','playoff_probability','first_place_probability','championship_probability')
FINALIST_WORKING_RESERVE_BYTES=48*1024*1024  # Admission reserve, not model materiality.


def evaluate_finalist(runtime,row,read,instructions,*,simulation_loader,memory_budget_bytes,reclaim):
    """One exact 50k confirmation, within the existing serialized admission path.

    A Current-only case must have a material competitive gain for the relevant
    owner. Future asset gains remain directional evidence, never future utility.
    """
    from .resource_coordinator import current_rss_bytes
    baseline=runtime.simulation_analytics
    if baseline is None or baseline.simulation_result.simulation_count!=50_000 or read is None:
        return {'status':'unavailable','reason':'complete_published_inputs_required'}
    reclaim('discovery-finalist-confirmation')
    observed_rss=current_rss_bytes()
    if observed_rss<=0 or observed_rss+FINALIST_WORKING_RESERVE_BYTES>memory_budget_bytes:
        return {'status':'deferred','reason':'resource_headroom'}
    proposal=_proposal_from_row(runtime,row,prefix='discovery-confirmation')
    validate_search_instructions(runtime,proposal,instructions)
    if not set(current_required_teams(row))<={proposal.side_a.team_id,proposal.side_b.team_id}:
        return {'status':'unavailable','reason':'priority_team_identity_unavailable'}
    result=build_post_trade_simulation_comparison(runtime,proposal,
        focal_team_id=runtime.selected_team_id,simulation_loader=simulation_loader)
    if not result.get('scenario_computation',{}).get('authoritative') or result.get('scenario_simulation_count')!=50_000:
        return {'status':'unavailable','reason':'authoritative_confirmation_required'}
    cuts=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality'])
    result['horizon_asset_economics']=bind_trade_intrinsic_values(runtime,proposal,read,roster_resolutions=cuts)
    assessment=build_trade_objective_assessment(runtime,proposal,result,instructions)
    def cut_ids(rows):return {r['team_id']:sorted(c['player_id'] for c in r.get('cuts',())) for r in rows}
    # A full check may resolve different cuts. Do not keep the old native effects
    # or silently promote a protected loss on the strength of the earlier screen.
    if cut_ids(row.get('roster_legality',()))!=cut_ids(result['roster_legality']) or any(assessment[s].get('protected_players_lost') for s in ('side_a','side_b')):
        return {'status':'review','reason':'confirmed_roster_consequences_changed'}
    material=result['material_assessment'];required=set(current_required_teams(row));failures=[];conflicts=[];unknown=[]
    for side in ('side_a','side_b'):
        effect=material[side]
        if effect['team_id'] not in required:continue
        if all(effect.get(k) in (None,'unavailable') for k in COMPETITIVE_METRICS):unknown.append(effect['team_id'])
        elif not any(effect.get(k)=='material_gain' for k in COMPETITIVE_METRICS):failures.append(effect['team_id'])
        elif any(effect.get(k)=='material_loss' for k in COMPETITIVE_METRICS):conflicts.append(effect['team_id'])
    return {'status':'unavailable' if unknown else 'not_worthwhile' if failures else 'review' if conflicts else 'verified',
        'reason':'competitive_evidence_unavailable' if unknown else 'current_gain_not_demonstrated' if failures else 'competitive_tradeoff_requires_review' if conflicts else 'material_current_case',
        'limiting_team_ids':unknown or failures or conflicts,'source_state_id':runtime.league_state.state_id,
        'publication_generation_id':runtime.publication_generation_id,
        'simulation_count':result['scenario_simulation_count'],
        'scenario_state_id':result['state_id_after'],
        'competitive_policy_version':material['competitive_policy_version'],
        'baseline_simulation_input_fingerprint':baseline.simulation_result.simulation_input_fingerprint,
        'native_input_fingerprint':read.source.get('input_fingerprint'),
        'cache_hit':result['scenario_computation']['cache_hit'],
        'execution_mode':result['scenario_computation']['execution_mode'],
        'competitive':{d['team_id']:d['competitive'] for d in result['team_deltas']},
        'material':{s:material[s] for s in ('side_a','side_b')},
        'authority':'existing_NEXT4_Simulation_and_NEXT5_materiality',
        'future_franchise_utility_estimated':False,'acceptance_probability':None}


