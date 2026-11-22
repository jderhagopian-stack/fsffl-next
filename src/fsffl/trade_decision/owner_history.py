"""Bind completed-trade observations to an exact package; no willingness model."""
from collections import Counter


def describe_owner_package_history(proposal, *, team_id, profile, player_positions,
                                   source_state_id, other_owner_id=None):
    base = {'team_id':team_id, 'source_state_id':source_state_id,
            'evidence_basis':'completed_trades_only', 'rejected_offers_observed':False,
            'acceptance_probability':None, 'willingness_inferred':False,
            'preference_inferred':False, 'decision_effect':'no_disposition_change',
            'model_version':'completed-package-history-v1', 'facts':[],
            'matching_features':[], 'observations':[]}
    legs = {leg.team_id:leg for leg in (proposal.side_a, proposal.side_b)}
    if team_id not in legs:
        raise ValueError('History team must belong to the proposal')
    if profile is None or profile.as_of > proposal.as_of:
        return {**base,'status':'unavailable','reason':'no_admissible_profile'}
    acquired = next(leg.sends for tid,leg in legs.items() if tid != team_id)
    disposed = legs[team_id].sends
    shape = ('consolidation' if len(acquired)<len(disposed) else
             'diversification' if len(acquired)>len(disposed) else 'balanced')
    count = {'consolidation':profile.consolidation_trade_count,
             'diversification':profile.diversification_trade_count,
             'balanced':profile.balanced_trade_count}[shape]
    shape_words = {'consolidation':'sending more assets for fewer',
                   'diversification':'receiving more assets than they send',
                   'balanced':'exchanging the same number of assets'}
    facts=[]; matches=[]; observations=[]
    if count:
        facts.append(f'They completed {count} of their {profile.trade_count} recorded trades {shape_words[shape]}, as they would here.')
        matches.append('package_shape')
        observations.append({'kind':'package_shape','shape':shape,'count':count,'trade_count':profile.trade_count})
    activity=profile.completed_trade_activity
    pick_count=sum(a.kind=='pick' for a in acquired)
    if activity is not None and pick_count and activity.trades_acquiring_picks:
        facts.append(f'They acquired draft picks in {activity.trades_acquiring_picks} of their {profile.trade_count} recorded trades. This deal also sends them picks.')
        matches.append('acquire_picks')
        observations.append({'kind':'acquire_picks','count':activity.trades_acquiring_picks,'trade_count':profile.trade_count})
    if activity is not None and any(a.kind=='pick' for a in disposed) and activity.trades_sending_picks:
        facts.append(f'They sent draft picks in {activity.trades_sending_picks} of their {profile.trade_count} recorded trades, as they would here.')
        matches.append('send_picks')
        observations.append({'kind':'send_picks','count':activity.trades_sending_picks,'trade_count':profile.trade_count})
    positions=Counter(player_positions.get(a.player_id) for a in acquired if a.kind=='player')
    if activity is not None:
        for position in sorted(p for p in positions if p):
            buys=activity.acquired_positions.get(position,0)
            if buys:
                facts.append(f'They acquired {buys} {position} player(s) in recorded trades. This package also includes {position} players for them.')
                matches.append('acquire_'+position)
                observations.append({'kind':'acquire_position','position':position,'count':buys})
    prior=profile.counterparty_trade_counts.get(other_owner_id,0) if other_owner_id else 0
    if prior:
        facts.append(f'These owners completed {prior} recorded trade(s) with each other.')
        observations.append({'kind':'counterparty','count':prior})
    return {**base,'status':'observed' if profile.trade_count else 'no_completed_trades',
            'owner_id':profile.owner_id,'league_family_id':profile.league_family_id,
            'as_of':profile.as_of.isoformat(),'profile_model_version':profile.model_version,
            'completed_trade_count':profile.trade_count,'proposed_shape':shape,
            'observed_shape_count':count,'trade_asset_detail_available':activity is not None,
            'facts':facts[:3],'matching_features':matches,
            'observations_version':'package-observations-v1',
            'observations':sorted(observations,key=lambda row: {'acquire_picks':0,'send_picks':0,
                'acquire_position':1,'counterparty':2,'package_shape':3}[row['kind']])}
