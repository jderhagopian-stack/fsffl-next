from dataclasses import replace
from types import SimpleNamespace

import pytest

from fsffl.product.strategic_discovery import StrategicDiscoveryRequest,_matches_target,build_strategic_discovery,prepare_discovery
from tests.test_strategic_discovery import governed_runtime_fixture


def option(kind='player',age=26.,position='WR'):
    return SimpleNamespace(asset_kind=kind,age_years=age,detail=position)


@pytest.mark.parametrize('age,accepted',[(25,True),(26,True),(26.99,True),(27,False),(None,False),(float('inf'),False)])
def test_whole_age_cutoff_and_unknown_age(age,accepted):
    request=StrategicDiscoveryRequest(target_asset_kinds=['player'],target_player_max_age=26)
    assert _matches_target(option(age=age),request) is accepted


def test_multiple_asset_kinds_are_alternatives_and_player_filters_intersect():
    request=StrategicDiscoveryRequest(target_asset_kinds=['player','pick'],target_player_max_age=26,target_position='WR')
    assert _matches_target(option('pick',None,None),request)
    assert _matches_target(option(age=25),request)
    assert not _matches_target(option(age=28),request)
    assert not _matches_target(option(age=25,position='RB'),request)
    # Existing position-only callers continue to search players, not picks.
    assert not _matches_target(option('pick',None,None),StrategicDiscoveryRequest(target_position='WR'))


@pytest.mark.parametrize('kinds,young',[(['player'],True),(['pick'],False),(['player','pick'],True)])
def test_preferences_filter_generation_with_multiple_priorities_and_protections(kinds,young):
    runtime,_=governed_runtime_fixture(team_count=4)
    states=tuple(p.model_copy(update={'age_years':26.5 if int(p.player_id.split('-')[1])%2==0 else 28.}) for p in runtime.league_state.player_states)
    runtime=replace(runtime,league_state=runtime.league_state.model_copy(update={'player_states':states}))
    request=StrategicDiscoveryRequest(target_asset_kinds=kinds,target_player_max_age=26 if young else None,
        target_position='WR',counterparty_team_id='t1',evaluation_budget=0,
        search_instructions={'objectives':['current_competitiveness','career_contribution'],'protected_player_ids':['t0-0']})
    result=build_strategic_discovery(runtime,request)
    rows=result['candidate_packages'];assert rows
    players={p.player_id:p for p in runtime.league_state.players};ages={p.player_id:p.age_years for p in states}
    for row in rows:
        assert row['counterparty_team_id']=='t1'
        assert all(a['asset_ref']!='player:t0-0' for a in row['send'])
        for received in row['receive']:
            kind,pid=received['asset_ref'].split(':',1);assert kind in kinds
            if kind=='player':assert ages[pid]<27 and players[pid].position.value=='WR'
        assert row['trade_center_request']['search_instructions']['objectives']==['current_competitiveness','career_contribution']
    assert result['diagnostics']['pair_visits']<=640


def test_exact_target_conflict_is_rejected_instead_of_relaxing_preferences():
    runtime,_=governed_runtime_fixture(team_count=4)
    with pytest.raises(ValueError,match='target asset'):
        prepare_discovery(runtime,StrategicDiscoveryRequest(target_asset_ref='player:t1-6',target_asset_kinds=['pick']))


def test_empty_or_duplicate_asset_preferences_are_rejected():
    runtime,_=governed_runtime_fixture(team_count=4)
    for kinds in ([],['pick','pick']):
        with pytest.raises(ValueError):prepare_discovery(runtime,StrategicDiscoveryRequest(target_asset_kinds=kinds))


def test_ui_sends_combined_priorities_and_asset_filters_on_find_more():
    import shutil,subprocess
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const handlers={},pending=[],calls=[];
const priority={dataset:{sePriority:'career_contribution'},checked:true,addEventListener:(e,f)=>handlers.priority=f};
const mode={dataset:{seMode:'custom'},addEventListener:(e,f)=>handlers.custom=f};
const host={id:'market-ns-body',isConnected:true,innerHTML:'',querySelector:s=>({addEventListener:(e,f)=>handlers[s]=f}),querySelectorAll:s=>s==='[data-se-priority]'?[priority]:s==='[data-se-mode]'?[mode]:[]};
const c={state:{route:'opportunities',context:{user_id:'u',league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},window:{fsfflMarketNorthStar:{activeTab:()=> 'trade_finder'},addEventListener:()=>{}},JSON,Set,Map,Promise,
api:(path,opts)=>{if(path.endsWith('/browser'))return Promise.resolve({state_id:'s',focal_team:{team_id:'a',assets:[]},counterparties:[]});calls.push(JSON.parse(opts.body));return new Promise(resolve=>pending.push(resolve));}};
vm.createContext(c);vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8'),c);
const ui=c.window.fsfflStrategicExplore,flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 ui.render(host,null,{directed:true});await flush();handlers.custom();handlers.priority();
 handlers['[data-se-young]']({target:{checked:true}});handlers['[data-se-picks]']({target:{checked:true}});
 handlers['[data-se-position]']({target:{value:'WR'}});
 const first=ui.run();await flush();
 assert.deepEqual(calls[0].search_instructions.objectives,['current_competitiveness','career_contribution']);
 assert.deepEqual(calls[0].target_asset_kinds,['player','pick']);assert.equal(calls[0].target_player_max_age,26);assert.equal(calls[0].target_position,'WR');
 pending.shift()({league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[],search_progress:{stop_reason:'shortlist_ready',next_token:'next'}});await first;
 const more=ui.run({continueSearch:true});await flush();assert.equal(calls[1].continuation_token,'next');
 assert.deepEqual(calls[1].target_asset_kinds,calls[0].target_asset_kinds);assert.deepEqual(calls[1].search_instructions,calls[0].search_instructions);
 pending.shift()({league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[]});await more;
 ui.applyIntent('target','player:specific');ui.render(host,null,{directed:true});const target=ui.run();await flush();
 assert.equal(calls[2].target_asset_ref,'player:specific');assert(!calls[2].target_asset_kinds);assert(!calls[2].target_player_max_age);
 pending.shift()({league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[]});await target;
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    result=subprocess.run([node,'-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
