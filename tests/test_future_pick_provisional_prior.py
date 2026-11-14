from dataclasses import replace
from datetime import timedelta
import shutil
import subprocess

import pytest

from fsffl.forecast.future_pick_position_prior import (
    FuturePickPositionPrior, FUTURE_PICK_POSITION_POLICY as POLICY,
    FUTURE_PICK_POSITION_AVAILABLE_AT as AVAILABLE,
)
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values, bind_trade_intrinsic_values
from fsffl.product.presentation_continuity import PresentationContinuityStore, HOME_SURFACE
from fsffl.value.native_pick_prior import NativePickPriorReference, NativePickPriorRelease
from fsffl.persistence.native_pick_prior import persist_native_pick_release
from fsffl.state.models import DraftPick, PickOwnership, PickAsset
from fsffl.trade_decision.models import TradeLeg
from tests.test_native_pick_prior_production import fixture as base_fixture, MemoryPersistence


def fixture():
    runtime,record,proposal,release=base_fixture()
    state=runtime.league_state
    additions=tuple(DraftPick(pick_id=f'pick:{year}:{origin}',league_id=state.league.league_id,
        season=year,round=1,original_team_id=origin) for year in (2028,2029) for origin in ('alpha','beta'))
    state=state.model_copy(update={'as_of':AVAILABLE+timedelta(seconds=1),
        'draft_picks':state.draft_picks+additions,'pick_ownership':state.pick_ownership+tuple(
            PickOwnership(pick_id=p.pick_id,owner_team_id=p.original_team_id) for p in additions)})
    runtime=replace(runtime,league_state=state)
    runtime.simulation_analytics.league_view.context.league_state_id=state.state_id
    record.league_state_id=state.state_id
    proposal=proposal.model_copy(update={'as_of':state.as_of,'side_a':TradeLeg(team_id='alpha',
        sends=(PickAsset(pick_id='pick:2028:alpha'),))})
    return runtime,record,proposal,release


def read(runtime,record,release,policy=POLICY,fingerprint='sim'):
    return read_published_trade_horizon_values(runtime,player_ids=frozenset({'a1','b1'}),record=record,
        publication_validator=lambda c,r:True,pick_release=release,pick_simulation_fingerprint=fingerprint,
        pick_projection_policy=policy)


@pytest.mark.parametrize('teams',[2,10,12,14])
def test_neutral_position_prior_has_full_support_and_no_simulation_claim(teams):
    prior=FuturePickPositionPrior(team_count=teams,draft_season=2029)
    assert sum(p for _,p in prior.probabilities())==pytest.approx(1)
    assert [s for s,_ in prior.probabilities()]==list(range(1,teams+1))
    assert len(set(p for _,p in prior.probabilities()))==1
    assert prior.evidence_kind=='bounded_provisional_exchangeability'
    assert 'simulation_count' not in prior.model_dump()


def test_later_values_reuse_frozen_slots_with_literal_calendar_and_scenario_range():
    runtime,record,proposal,release=fixture();before=release.model_dump_json()
    projection=read(runtime,record,release)
    assert projection.pick_values['three_year']['pick:2028:alpha']==pytest.approx(55*.85**2)
    assert projection.pick_values['three_year']['pick:2029:alpha']==0
    assert projection.pick_values['career']['pick:2028:alpha']==132
    assert projection.pick_values['career']['pick:2029:alpha']==132  # accepted undiscounted Career
    source=projection.pick_sources['pick:2028:alpha']
    assert (source['career_slot_low'],source['career_slot_high'])==(24,240)
    assert source['three_year_slot_low']==pytest.approx(10*.85**2)
    assert source['three_year_slot_high']==pytest.approx(100*.85**2)
    assert source['simulation_input_fingerprint'] is None
    assert source['probability_basis']=='exchangeable_future_slot_prior'
    assert source['range_basis']=='possible_slot_reference_values_not_predictive_interval'
    result=bind_trade_intrinsic_values(runtime,proposal,projection)
    assert result['status']=='complete' and result['career']['package_uncertainty'] is None
    assert result['career']['side_a']['sent_mean']==132
    assert result['career']['side_a']['mean_delta']==-result['career']['side_b']['mean_delta']
    assert release.model_dump_json()==before


@pytest.mark.parametrize('simulation',['missing','wrong_state','wrong_fingerprint','preview','no_origin'])
def test_later_prior_is_independent_of_next_draft_simulation_but_never_relabels_it(simulation):
    runtime,record,proposal,release=fixture();fingerprint='sim'
    if simulation=='missing':runtime=replace(runtime,simulation_analytics=None)
    if simulation=='wrong_state':runtime.simulation_analytics.league_view.context.league_state_id='wrong'
    if simulation=='wrong_fingerprint':fingerprint='wrong'
    if simulation=='preview':runtime.simulation_analytics.simulation_result.simulation_count=100
    if simulation=='no_origin':runtime.simulation_analytics.simulation_result.future_pick_distributions=()
    projection=read(runtime,record,release,fingerprint=fingerprint)
    assert 'pick:alpha' not in projection.pick_values['career']
    assert projection.pick_values['career']['pick:2029:alpha']==132
    assert 'native_pick_simulation_fingerprint' not in projection.source
    assert bind_trade_intrinsic_values(runtime,proposal,projection)['status']=='complete'


@pytest.mark.parametrize('failure',['absent_policy','wrong_policy','before_policy','wrong_rules','missing_release'])
def test_policy_and_economic_scope_are_not_implicitly_upgraded(failure):
    runtime,record,proposal,release=fixture();policy=POLICY
    if failure=='absent_policy':policy=None
    if failure=='wrong_policy':policy='unknown'
    if failure=='before_policy':
        state=runtime.league_state.model_copy(update={'as_of':AVAILABLE-timedelta(seconds=1)})
        runtime=replace(runtime,league_state=state);record.league_state_id=state.state_id
        runtime.simulation_analytics.league_view.context.league_state_id=state.state_id
    if failure=='wrong_rules':release=release.model_copy(update={'rules_signature':'other'})
    if failure=='missing_release':release=None
    projection=read(runtime,record,release,policy)
    assert 'pick:2028:alpha' not in projection.pick_values['career']
    assert projection.values['career']  # player channels preserved


def test_neutral_round_calculation_is_reused_across_origins(monkeypatch):
    runtime,record,_,release=fixture();original=NativePickPriorRelease.future_round_reference;calls=[]
    def counted(self,**kwargs):
        calls.append((kwargs['prior'].draft_season,kwargs['round_number'],kwargs['horizon']))
        return original(self,**kwargs)
    monkeypatch.setattr(NativePickPriorRelease,'future_round_reference',counted)
    projection=read(runtime,record,release)
    assert len(calls)==4 and len(set(calls))==4
    assert projection.pick_values['career']['pick:2028:alpha']==projection.pick_values['career']['pick:2028:beta']


def test_publication_pins_new_policy_and_old_manifests_keep_their_original_behavior(monkeypatch):
    runtime,record,_,release=fixture();runtime=replace(runtime,simulation_analytics=None)
    store=MemoryPersistence();persist_native_pick_release(store,release);continuity=PresentationContinuityStore(store)
    monkeypatch.setattr('fsffl.product.presentation_continuity.packaged_native_pick_reference',
        lambda:NativePickPriorReference(release_id=release.release_id,scope_key=release.economic_scope_key,
            evaluation_season=2026,team_count=2,released_at=release.released_at))
    promotion=continuity.promote(user_id=runtime.user_id,runtime=runtime,builders=((HOME_SURFACE,lambda:{'status':'ready'}),))
    runtime=replace(runtime,publication_generation_id=promotion.publication_generation_id)
    assert continuity.native_pick_generation_binding(runtime)==(release,None,POLICY)
    manifest=store.artifacts[-1];before_reads=store.read_count
    assert continuity.native_pick_generation_binding(runtime)==(release,None,POLICY)
    assert store.read_count==before_reads
    old=dict(manifest.payload);old.pop('native_pick_projection_policy')
    continuity._remember_snapshot_manifest(user_id=runtime.user_id,league_id=runtime.league_state.league.league_id,
        league_state_id=runtime.league_state.state_id,selected_team_id=runtime.selected_team_id,manifest_payload=old)
    assert continuity.native_pick_generation_binding(runtime)==(release,None,None)


def test_discovery_exposes_uncertain_slot_and_range_without_promoting_a_recommendation():
    from fsffl.product.strategic_discovery import StrategicDiscoveryRequest,build_strategic_discovery
    runtime,record,_,release=fixture();projection=read(runtime,record,release)
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(max_candidates=8,evaluation_budget=0,
        target_asset_ref='pick:pick:2029:beta',search_instructions={'objectives':['career_contribution']}),read=projection)
    pick=result['pick_evidence']['pick:pick:2029:beta']
    assert pick['slot_uncertain_prior'] and pick['outside_three_year_window']
    assert pick['intrinsic_slot_ranges']['career']=={'low':24,'high':240}
    assert result['candidate_packages'] and all(r['action_authority']=='diagnostic_only' for r in result['candidate_packages'])
    assert result['diagnostics']['changed_state_simulation_calls']==0


def test_pick_range_presentation_distinguishes_slot_scenarios_from_total_uncertainty():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    program=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let source=fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8');
source=source.replace('window.fsfflStrategicExplore={render,run,priorities,applyIntent};',
 'window.rangeTest=(pick)=>{view.result={pick_evidence:{"pick:test":pick}};return packageAssets([{asset_ref:"pick:test",label:"Future pick"}]);};');
const sandbox={window:{addEventListener:()=>{}},console};vm.createContext(sandbox);vm.runInContext(source,sandbox);
const html=sandbox.window.rangeTest({slot_uncertain_prior:true,three_year_intrinsic_status:'bounded_provisional',
 outside_three_year_window:true,career_intrinsic:132,intrinsic_slot_ranges:{career:{low:24,high:240}}});
assert(html.includes('Slot uncertain'));assert(!html.includes('Projected slot'));
assert(html.includes('Value by draft slot'));assert(html.includes('24–240 by slot'));
assert(html.includes('outside the current window'));assert(html.includes('Raw Intrinsic contribution'));
assert(!html.includes('confidence interval'));assert(!html.includes('50,000'));
'''
    result=subprocess.run([node,'-e',program],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
