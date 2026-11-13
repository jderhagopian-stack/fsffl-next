from pathlib import Path
import shutil
import subprocess
import pytest


def test_sequential_batches_pause_resume_merge_and_shared_directed_search():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const controls={},events={},pending=[],calls=[];let tab='for_you';
const control=key=>({addEventListener:(event,fn)=>controls[key]=fn});
const host={id:'market-ns-body',isConnected:true,innerHTML:'',querySelector:s=>control(s),querySelectorAll:()=>[]};
const c={state:{route:'opportunities',context:{user_id:'u',league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},
window:{fsfflMarketNorthStar:{activeTab:()=>tab},addEventListener:(key,fn)=>events[key]=fn},console,JSON,Set,Map,Promise,
api:(path,options)=>{calls.push({path,options});return path.endsWith('/browser')?Promise.resolve({state_id:'s',focal_team:{team_id:'a',assets:[]},counterparties:[]}):new Promise(resolve=>pending.push(resolve));}};
vm.createContext(c);vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8'),c);
const ui=c.window.fsfflStrategicExplore,flush=()=>new Promise(r=>setImmediate(r));
const row=(id,label,evaluated=true)=>({point_id:id,counterparty_team_id:'b',send:[],receive:[{asset_ref:'player:'+id,label}],...(evaluated?{evaluation_kind:'root'}:{}),display_context:{group:evaluated?'preliminary_fit':'needs_evidence'}});
const response=(batch,rows,next)=>({league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:rows,
search_progress:{total_screened:batch*8,max_total_screens:32,preliminary_fit_count:batch,shortlist_target:4,next_token:next,stop_reason:next?'continue':'screening_limit'}});
(async()=>{
 ui.render(host);await flush();assert.equal(pending.length,1);
 pending.shift()(response(1,[row('first','First valid result')],'one'));await flush();
 assert(host.innerHTML.includes('First valid result'));assert(host.innerHTML.includes('8 packages evaluated'));
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).continuation_token,'one');
 controls['[data-se-pause]']();
 pending.shift()(response(2,[row('first','Must not downgrade',false),row('second','Second valid result')],'two'));await flush();
 assert(!pending.length);assert(host.innerHTML.includes('First valid result'));assert(!host.innerHTML.includes('Must not downgrade'));
 assert(host.innerHTML.includes('Second valid result'));assert(host.innerHTML.includes('16 packages evaluated'));
 controls['[data-se-more]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).continuation_token,'two');
 pending.shift()(response(3,[row('third','Third valid result')],'three'));await flush();
 pending.shift()(response(4,[row('fourth','Fourth valid result')],null));await flush();
 assert(!pending.length);assert(host.innerHTML.includes('32 packages evaluated'));assert(host.innerHTML.includes('First valid result'));
 tab='trade_finder';ui.render(host,null,{directed:true});assert(host.innerHTML.includes('Directed search'));
 controls['[data-se-offer]']({target:{value:'pick:owned'}});controls['[data-se-run]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).offered_asset_ref,'pick:owned');
 const quality=response(1,[row('fifth','Directed result')],'next');quality.search_progress.stop_reason='shortlist_ready';quality.search_progress.preliminary_fit_count=4;
 pending.shift()(quality);await flush();assert(!pending.length);assert(host.innerHTML.includes('Directed result'));
 // Changing route stops continuation; it cannot run invisibly behind Trade Center.
 controls['[data-se-more]']();await flush();c.state.route='trade_center';
 pending.shift()(response(2,[],'unwanted'));await flush();assert(!pending.length);
 assert(!calls.some(c=>c.path.includes('simulate')));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    result=subprocess.run([node,'-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_trade_finder_delegates_to_same_discovery_consumer():
    source=Path('src/fsffl/product/static/north_star_market.js').read_text()
    finder=source.split('function renderTradeFinder(body,payload){',1)[1].split('\n',2)[1]
    assert 'fsfflStrategicExplore.render(body,payload,{directed:true})' in finder
