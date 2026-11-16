from datetime import timedelta
from types import SimpleNamespace

from fsffl.behavioral.models import BehavioralAsset, BehavioralEventKind
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.product.behavioral_fit_runtime import build_trade_behavioral_fit
from fsffl.product.owner_history_runtime import build_trade_owner_history
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.trade_decision.owner_history import describe_owner_package_history
from fsffl.state.models import PlayerAsset, PickAsset
from tests.test_behavioral_intelligence import _event


def history():
    wr=BehavioralAsset(kind='player',asset_ref='player:wr',position='WR')
    rb=BehavioralAsset(kind='player',asset_ref='player:rb',position='RB')
    pick=BehavioralAsset(kind='pick',asset_ref='pick:p',pick_season=2027,pick_round=1)
    trade=_event('trade',acquired=(wr,),disposed=(rb,pick))
    waiver=_event('waiver',acquired=(rb,pick),disposed=()).model_copy(update={'kind':BehavioralEventKind.WAIVER})
    future=_event('future',acquired=(rb,),disposed=(pick,)).model_copy(update={'occurred_at':trade.occurred_at+timedelta(days=40)})
    cutoff=trade.occurred_at+timedelta(days=1)
    return build_owner_behavior_profiles((trade,waiver,future),as_of=cutoff)[0]


def proposal(profile, incoming=(PlayerAsset(player_id='wr'),), outgoing=(PlayerAsset(player_id='rb'),PickAsset(pick_id='p'))):
    return BilateralTradeProposal(proposal_id='test',as_of=profile.as_of,
        side_a=TradeLeg(team_id='a',sends=incoming),side_b=TradeLeg(team_id='b',sends=outgoing))


def describe(profile,p=None):
    return describe_owner_package_history(p or proposal(profile),team_id='b',profile=profile,
        player_positions={'wr':'WR','rb':'RB'},source_state_id='state')


def test_trade_only_observations_exclude_waivers_and_future_events():
    profile=history()
    assert profile.event_count==2 and profile.trade_count==1 and profile.waiver_count==1
    assert profile.acquired_positions=={'WR':1,'RB':1}  # Existing descriptive total preserved.
    activity=profile.completed_trade_activity
    assert activity.acquired_positions=={'WR':1} and activity.acquired_pick_count==0
    assert activity.disposed_pick_count==1 and activity.trades_sending_picks==1
    row=describe(profile)
    assert row['matching_features']==['package_shape','send_picks','acquire_WR']
    assert not row['willingness_inferred'] and not row['preference_inferred']
    assert row['acceptance_probability'] is None and not row['rejected_offers_observed']
    assert row['completed_trade_count']==1


def test_unobserved_package_is_not_rejection_or_aversion():
    profile=history()
    p=proposal(profile,incoming=(PlayerAsset(player_id='rb'),PickAsset(pick_id='q')),
               outgoing=(PlayerAsset(player_id='wr'),))
    row=describe(profile,p)
    assert row['status']=='observed' and row['matching_features']==[]
    assert row['facts']==[]
    runtime=SimpleNamespace(league_state=SimpleNamespace(state_id='state',players=()))
    fit=build_trade_behavioral_fit(runtime,p,focal_team_id='a',counterparty_profile=profile)
    assert fit.direction.value=='neutral' and fit.evidence_level.value=='observed'
    assert fit.acceptance_probability is None


def test_legacy_profiles_do_not_relabel_mixed_activity_as_completed_trade_evidence():
    profile=history().model_copy(update={'completed_trade_activity':None})
    row=describe(profile)
    assert row['matching_features']==['package_shape']
    assert not row['trade_asset_detail_available']
    assert all('WR' not in fact and 'picks' not in fact for fact in row['facts'])
    assert type(profile).model_validate_json(profile.model_dump_json())==profile


def test_future_profile_and_missing_history_stay_unavailable():
    profile=history();p=proposal(profile).model_copy(update={'as_of':profile.as_of-timedelta(seconds=1)})
    assert describe(profile,p)['status']=='unavailable'
    assert describe_owner_package_history(p,team_id='b',profile=None,player_positions={},source_state_id='state')['facts']==[]


def test_shared_runtime_binds_each_side_to_its_own_history_and_state():
    profile=history();p=proposal(profile)
    runtime=SimpleNamespace(league_state=SimpleNamespace(state_id='exact',players=(),as_of=profile.as_of))
    other=profile.model_copy(update={'owner_id':'other','balanced_trade_count':1,'consolidation_trade_count':0})
    result=build_trade_owner_history(runtime,p,profiles={'a':other,'b':profile},player_positions={'wr':'WR','rb':'RB'})
    assert result['b']['matching_features']==describe(profile)['matching_features']
    assert result['a']['owner_id']=='other' and result['b']['owner_id']=='owner-a'
    assert all(r['source_state_id']=='exact' for r in result.values())
    assert result['a']['proposed_shape']=='diversification'


def test_state_cache_replaces_wrong_family_or_future_owner_mapping():
    from dataclasses import replace
    from fsffl.product.behavioral_runtime import _publish_profiles_for_state,cached_behavior_profile_for_team
    from fsffl.behavioral.service import BehavioralSyncResult
    from fsffl.state.models import ProviderRef
    from tests.test_state_foundation import make_state
    state=make_state()
    team=state.teams[0]
    team=team.model_copy(update={'provider_refs':(ProviderRef(provider='sleeper',external_id='1'),)})
    state=state.model_copy(update={'teams':(team,*state.teams[1:])})
    profile=history().model_copy(update={'as_of':state.as_of})
    result=BehavioralSyncResult(league_family_id=profile.league_family_id,profile_count=1,total_event_count=2,
        inserted_event_count=0,reused_historical_league_ids=(),scanned_league_ids=(),
        current_owner_by_roster=((1,profile.owner_id),),profiles=(profile,))
    _publish_profiles_for_state(state,result)
    assert cached_behavior_profile_for_team(state,team.team_id)==profile
    _publish_profiles_for_state(state,replace(result,league_family_id='different-family'))
    assert cached_behavior_profile_for_team(state,team.team_id) is None
    _publish_profiles_for_state(state,result)
    _publish_profiles_for_state(state,replace(result,profiles=(profile.model_copy(update={'as_of':state.as_of+timedelta(seconds=1)}),)))
    assert cached_behavior_profile_for_team(state,team.team_id) is None


def test_discovery_history_tie_break_never_overrides_economics_or_directed_gain():
    from copy import deepcopy
    from fsffl.product.strategic_discovery import _representative_indices
    def row(name,band='robust_or_ordinary',gain=True,match=False):
        return {'point_id':name,'send':[{'asset_ref':'player:a'}],'receive':[{'asset_ref':'player:b'}],
            'counterparty_team_id':'b','hypotheses':['same'],'preliminary_economic_band':band,
            'joint_priority_gain_hypothesis':gain,
            'owner_history':{'b':{'matching_features':['package_shape'] if match else []}}}
    ordinary=row('unobserved');observed=row('observed',match=True)
    before=deepcopy([ordinary,observed])
    assert _representative_indices([ordinary,observed],2)==[1,0]
    assert _representative_indices([ordinary,row('strained',band='counterparty_economic_strain',match=True)],1)==[0]
    assert _representative_indices([ordinary,row('no_gain',gain=False,match=True)],1)==[0]
    assert [ordinary,observed]==before  # No filtering, values or priorities changed.


def test_counter_positive_history_lane_keeps_unfamiliar_packages_reachable():
    from fsffl.product.counter_search import order_counter_hypotheses
    from fsffl.opportunity.frontier import make_frontier_point
    from tests.test_opportunity_frontier_search import _seed
    a,b,c=(PlayerAsset(player_id=p) for p in ('a','b','c'))
    seed=make_frontier_point(_seed('a',a),_seed('b',b))
    unfamiliar=make_frontier_point(_seed('a',a,c),seed.counterparty_package)
    observed=make_frontier_point(_seed('a',c),seed.counterparty_package)
    pub=SimpleNamespace(values={},pick_values={})
    result=order_counter_hypotheses(seed,(unfamiliar,observed),seed_effects={'teams':{}},
        published=pub,starters={},history_matches={observed.point_id:['package_shape']})
    assert result==(observed,unfamiliar)


def test_request_local_history_preparation_reuses_state_identity_and_fences_other_state():
    from fsffl.product.owner_history_runtime import prepare_trade_owner_history
    import pytest
    profile=history();p=proposal(profile)
    class CountedState:
        as_of=profile.as_of
        players=()
        fingerprints=0
        @property
        def state_id(self):
            self.fingerprints+=1
            return 'exact'
    state=CountedState();runtime=SimpleNamespace(league_state=state)
    context=prepare_trade_owner_history(runtime,profiles={'a':profile,'b':profile},player_positions={'wr':'WR'})
    for _ in range(20):
        result=build_trade_owner_history(runtime,p,context=context)
        assert result['b']['source_state_id']=='exact'
    assert state.fingerprints==1
    with pytest.raises(ValueError,match='exact request State'):
        build_trade_owner_history(SimpleNamespace(league_state=CountedState()),p,context=context)
    with pytest.raises(ValueError,match='cutoff'):
        build_trade_owner_history(runtime,p.model_copy(update={'as_of':p.as_of-timedelta(seconds=1)}),context=context)
