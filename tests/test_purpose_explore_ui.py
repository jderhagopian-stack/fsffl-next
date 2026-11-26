"""The product explains intent without inventing owner willingness or benefits."""
import shutil,subprocess
import pytest


def test_card_reason_uses_same_state_purpose_and_observed_history_only():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const host={id:'market-ns-body',isConnected:true,innerHTML:'',querySelector:()=>({addEventListener:()=>{}}),querySelectorAll:()=>[]};
const p={kind:'observed_acquisition',team_id:'b',partner_team_id:'a',source_state_id:'s',position:'WR',interest_kind:'position',observed_trade_count:3,result:'observed_history_only'};
const row={point_id:'p',focal_team_id:'a',counterparty_team_id:'b',send:[{asset_ref:'player:wr',label:'A receiver'}],receive:[{asset_ref:'player:rb',label:'A runner'}],discovery_purposes:[p],display_context:{group:'preliminary_fit'}};
const response={league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[row]};
const c={state:{route:'opportunities',context:{user_id:'u',league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},
window:{fsfflMarketNorthStar:{activeTab:()=> 'for_you'},addEventListener:()=>{}},JSON,Map,Set,Promise,
api:async path=>path.endsWith('/browser')?{state_id:'s',focal_team:{team_id:'a',assets:[]},counterparties:[]}:response};
vm.createContext(c);vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8'),c);
(async()=>{c.window.fsfflStrategicExplore.render(host);await new Promise(r=>setImmediate(r));
assert(!host.innerHTML.includes('Try a WR-led offer'));
assert(!host.innerHTML.includes('They have traded for receivers in 3 recorded trades.'));
row.discovery_purposes.push({kind:'improve_lineup',source_state_id:'s',position:'RB',result:'lineup_gain'});
c.window.fsfflStrategicExplore.render(host);assert(host.innerHTML.includes('More RB points now'));
assert(!host.innerHTML.includes('will accept'));
p.source_state_id='foreign';c.window.fsfflStrategicExplore.render(host);
assert(!host.innerHTML.includes('Try a WR-led offer'));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    subprocess.run([node,'-e',script],check=True,capture_output=True,text=True)
