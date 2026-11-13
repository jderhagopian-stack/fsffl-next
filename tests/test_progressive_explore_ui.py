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
search_progress:{total_screened:batch*8,max_total_screens:80,preliminary_fit_count:batch,shortlist_target:4,next_token:next,stop_reason:next?'continue':'screening_limit'}});
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
 const shortlisted=response(4,[row('fourth','Fourth valid result')],'four');shortlisted.search_progress.stop_reason='shortlist_ready';
 pending.shift()(shortlisted);await flush();
 assert(!pending.length);assert(host.innerHTML.includes('32 packages evaluated'));assert(host.innerHTML.includes('First valid result'));
 assert(host.innerHTML.includes('Find More'));controls['[data-se-more]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).continuation_token,'four');
 pending.shift()(response(5,[row('new','New after thirty-two')],null));await flush();
 assert(host.innerHTML.includes('40 packages evaluated'));assert(host.innerHTML.includes('First valid result'));
 assert(host.innerHTML.includes('New after thirty-two'));
 controls['[data-se-different]']();assert(!pending.length);assert(host.innerHTML.includes('New after thirty-two'));
 tab='trade_finder';ui.render(host,null,{directed:true});assert(host.innerHTML.includes('Offer / shop an asset'));assert(!host.innerHTML.includes('Directed search'));
 controls['[data-se-offer]']({target:{value:'pick:owned'}});controls['[data-se-run]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).offered_asset_ref,'pick:owned');
 const quality=response(1,[row('fifth','Directed result')],'next');quality.search_progress.stop_reason='shortlist_ready';quality.search_progress.preliminary_fit_count=4;
 pending.shift()(quality);await flush();assert(!pending.length);assert(host.innerHTML.includes('Directed result'));
 // Repeated explicit links override local edits; repaints do not.
 ui.applyIntent('shop','player:A');ui.render(host,null,{directed:true});
 controls['[data-se-offer]']({target:{value:'player:B'}});ui.render(host,null,{directed:true});
 controls['[data-se-run]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).offered_asset_ref,'player:B');
 pending.shift()(quality);await flush();
 ui.applyIntent('shop','player:A');ui.render(host,null,{directed:true});controls['[data-se-run]']();await flush();
 assert.equal(JSON.parse(calls.filter(c=>c.options).at(-1).options.body).offered_asset_ref,'player:A');
 pending.shift()(quality);await flush();
 ui.applyIntent('target','player:T');ui.render(host,null,{directed:true});
 controls['[data-se-target]']({target:{value:'player:other'}});ui.render(host,null,{directed:true});
 ui.applyIntent('target','player:T');ui.render(host,null,{directed:true});controls['[data-se-run]']();await flush();
 const targeted=JSON.parse(calls.filter(c=>c.options).at(-1).options.body);
 assert.equal(targeted.target_asset_ref,'player:T');assert(!targeted.offered_asset_ref);
 pending.shift()(quality);await flush();
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


def test_explicit_navigation_consumption_applies_the_intent_once():
    source=Path('src/fsffl/product/static/north_star_market.js').read_text()
    consume=source.split('function consumeMarketDeepLink(){',1)[1].split('function openTab(',1)[0]
    assert 'fsfflConsumeDeepLinkIntent' in consume
    assert 'fsfflStrategicExplore?.applyIntent?.(pending.marketIntent,pending.marketValue' in consume


def test_find_more_retains_eighty_screens_with_bounded_actions_and_concrete_explanations():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const controls={},pending=[],calls=[];
const host={id:'market-ns-body',isConnected:true,innerHTML:'',querySelector:s=>({addEventListener:(event,fn)=>controls[s]=fn}),querySelectorAll:()=>[]};
const c={state:{route:'opportunities',context:{user_id:'u',league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},window:{fsfflMarketNorthStar:{activeTab:()=> 'for_you'},addEventListener:()=>{}},JSON,Map,Set,Promise,
api:(path,options)=>{if(path.endsWith('/browser'))return Promise.resolve({state_id:'s',focal_team:{team_id:'a',assets:[]},counterparties:[]});calls.push(JSON.parse(options.body));return new Promise(resolve=>pending.push(resolve));}};
vm.createContext(c);vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8'),c);
const flush=()=>new Promise(r=>setImmediate(r));
function result(batch){return {league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',
search_progress:{total_screened:batch*8,max_total_screens:80,preliminary_fit_count:0,next_token:batch<10?'token'+batch:null,stop_reason:batch<10?'continue':'screening_limit'},
candidate_packages:Array.from({length:8},(_,i)=>({point_id:'p'+((batch-1)*8+i),counterparty_team_id:'b',send:[],receive:[{asset_ref:'player:p'+((batch-1)*8+i),label:'Asset '+((batch-1)*8+i)}],evaluation_kind:'root',display_context:{group:'priority_tradeoff'},evidence_status:'pre_simulation_screened',
objective_assessment:{side_a:{context:{team_id:'a'}}},position_strength_comparisons:{a:{positions:[{position:'RB',expected_points_delta:5},{position:'WR',expected_points_delta:-1}]}},
horizon_asset_economics:{career:{roster_adjusted:{side_a:{status:'complete',roster_adjusted_intrinsic_delta:-20}}}}}))};}
(async()=>{
 c.window.fsfflStrategicExplore.render(host);await flush();
 for(let batch=1;batch<=4;batch++){assert.equal(pending.length,1);pending.shift()(result(batch));await flush();}
 assert(!pending.length);assert.equal(calls.length,4);assert(host.innerHTML.includes('Find More'));
 controls['[data-se-more]']();await flush();
 for(let batch=5;batch<=8;batch++){pending.shift()(result(batch));await flush();}
 assert(!pending.length);assert.equal(calls.length,8);assert.equal(calls[4].continuation_token,'token4');
 controls['[data-se-more]']();await flush();
 for(let batch=9;batch<=10;batch++){pending.shift()(result(batch));await flush();}
 assert(!pending.length);assert.equal(calls.length,10);assert.equal((host.innerHTML.match(/class="se-card"/g)||[]).length,80);
 assert(host.innerHTML.includes('Asset 0')&&host.innerHTML.includes('Asset 79'));
 assert(host.innerHTML.includes('Stronger RB lineup; less WR lineup production; gives up Career contribution.'));
 assert(!host.innerHTML.includes('Both sides’ gains and costs are shown separately'));
 assert(!host.innerHTML.includes('Lineup changes are preliminary.'));
 assert(!host.innerHTML.includes('data-se-more>Find More'));assert(host.innerHTML.includes('Explore different options'));
 controls['[data-se-different]']();assert.equal(calls.length,10);assert(host.innerHTML.includes('Asset 0'));
})().catch(e=>{console.error(e);process.exitCode=1});
"""
    result=subprocess.run([node,'-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
