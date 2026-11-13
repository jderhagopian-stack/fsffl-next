/* Explore composes published Search/Decision evidence. No valuation or outcome model. */
(function(){
  'use strict';
  const GOALS={current_competitiveness:'Win now',three_year_contribution:'Build over 3 years',career_contribution:'Build for the long term'};
  const ALL=Object.keys(GOALS);
  const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const signed=(v,d=1)=>{if(!finite(v))return 'Unavailable';const rounded=Number(v.toFixed(d));return(rounded>0?'+':'')+(rounded===0?0:v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});};
  const ctx=()=>typeof state!=='undefined'?state.context||{}:{};
  const contextKey=()=>JSON.stringify([ctx().user_id,ctx().league_id,ctx().team_id,ctx().state_id,ctx().capability_readiness?.publication?.generation_id||ctx().publication_generation_id]);
  const fresh=()=>({key:contextKey(),sequence:0,result:null,browser:null,busy:false,inFlight:false,started:false,error:'',browserError:'',mode:'automatic',goal:ALL[0],partner:'',position:'',target:'',protected:[],expanded:false,dirty:false});
  let view=fresh(),host=null;
  function reconcile(){if(view.key!==contextKey())view=fresh();}
  function visibleHost(){return host?.isConnected&&typeof state!=='undefined'&&state.route==='opportunities'&&host.id==='market-ns-body'&&window.fsfflMarketNorthStar?.activeTab?.()==='for_you';}
  const asset=ref=>[view.browser?.focal_team,...(view.browser?.counterparties||[])].filter(Boolean).flatMap(t=>t.assets||[]).find(a=>a.asset_ref===ref);
  const teamName=id=>(view.browser?.counterparties||[]).find(t=>t.team_id===id)?.display_name||'Other franchise';
  const option=(v,label,selected)=>`<option value="${esc(v)}"${selected===v?' selected':''}>${esc(label)}</option>`;
  function instructions(){
    if(view.mode==='automatic'&&!view.protected.length)return null;
    const objectives=view.mode==='automatic'?view.result?.priority_context?.objectives:(view.goal==='all'?ALL:[view.goal]);
    if(!objectives?.length)throw new Error('Run automatic discovery before adding protections, or choose priorities.');
    return{objectives,protected_player_ids:[...view.protected]};
  }
  function requestBody(){const body={max_candidates:80,evaluation_budget:8};const goals=instructions();if(goals)body.search_instructions=goals;if(view.partner)body.counterparty_team_id=view.partner;if(view.position)body.target_position=view.position;if(view.target)body.target_asset_ref=view.target;return body;}
  function priorities(context){return(context?.objectives||[]).map(g=>GOALS[g]||g.replaceAll('_',' ')).join(' / ')||'Direction unavailable';}
  function direction(){
    const inferred=view.result?.priority_context;
    return `<section class="se-direction"><div class="se-row"><p class="eyebrow">Your Direction</p><small>You’re in control</small></div><div class="se-modes" role="group" aria-label="Search direction">${[['automatic','Automatic'],['custom','Set priorities']].map(([key,label])=>`<button type="button" data-se-mode="${key}" aria-pressed="${view.mode===key}">${label}</button>`).join('')}</div>${view.mode==='custom'?`<label class="se-field"><span>Your priority</span><select data-se-goal>${Object.entries(GOALS).map(([g,label])=>option(g,label,view.goal)).join('')}${option('all','Compare all horizons',view.goal)}</select></label><p>Prioritize your chosen horizon. Keep the sacrifices visible.</p>`:`<span class="se-direction-label">${esc(inferred?priorities(inferred):'Let team context guide discovery')}</span><p>Inferred from competitive state. Override it at any time; owner preferences are not confirmed.</p>`}</section>`;
  }
  function refinements(){
    const others=(view.browser?.counterparties||[]).filter(t=>!view.partner||t.team_id===view.partner);
    const assets=others.flatMap(t=>(t.assets||[]).filter(a=>!view.position||a.detail===view.position).map(a=>({...a,team:t.display_name})));
    const positions=[...new Set((view.browser?.counterparties||[]).flatMap(t=>(t.assets||[]).filter(a=>a.asset_kind==='player').map(a=>a.detail)).filter(Boolean))].sort();
    return `<details class="se-refine"${view.expanded?' open':''}><summary><span><b>Refine your search</b><small>Target a position, protect assets, or choose a partner.</small></span><span aria-hidden="true">＋</span></summary><div class="se-refine-fields">${view.browserError?`<p role="alert">${esc(view.browserError)}</p>`:''}<label class="se-field"><span>Target position</span><select data-se-position${!view.browser?' disabled':''}>${option('','Any position',view.position)}${positions.map(p=>option(p,p,view.position)).join('')}</select></label><label class="se-field"><span>Trade partner</span><select data-se-partner${!view.browser?' disabled':''}>${option('','Across the league',view.partner)}${(view.browser?.counterparties||[]).map(t=>option(t.team_id,t.display_name,view.partner)).join('')}</select></label><label class="se-field"><span>Target an asset</span><select data-se-target${!view.browser?' disabled':''}>${option('','No specific target',view.target)}${assets.map(a=>option(a.asset_ref,a.label+' · '+a.team,view.target)).join('')}</select></label><fieldset class="se-protect"><legend>Keep these players</legend><p>Protected players cannot be sent or included in required cuts.</p>${(view.browser?.focal_team?.assets||[]).filter(a=>a.player_id).map(a=>`<label><input type="checkbox" data-se-protect="${esc(a.player_id)}"${view.protected.includes(a.player_id)?' checked':''}><span>${esc(a.label)}</span></label>`).join('')}</fieldset></div></details>`;
  }
  function metric(label,value,unit){return `<div class="se-metric"><span>${esc(label)}</span><strong class="${finite(value)?(value>0?'se-gain':value<0?'se-loss':''):''}">${finite(value)?esc(signed(value)):'—'}</strong><small>${!finite(value)?'Unavailable · ':''}${esc(unit)}</small></div>`;}
  function side(row,label,title){
    const assessment=row.objective_assessment?.[label];
    const current=row.preliminary_decision_screen;
    const screened=row.evidence_status==='pre_simulation_screened';
    const weekly=current?.current_points_basis==='remaining_regular_season_weekly_mean';
    const points=screened?current?.[label==='side_a'?'focal':'counterparty']?.starter_points_delta:null;
    const native=h=>{const a=row.horizon_asset_economics?.[h]?.roster_adjusted?.[label];return a?.status==='complete'?a.roster_adjusted_intrinsic_delta:null;};
    const market=row.roster_adjusted_market_net?.[label];
    const marketDelta=screened&&market?.status==='complete'?market.roster_adjusted_market_delta:null;
    const status={aligns_with_priorities:'Direction aligns with priorities',conflicts_with_priorities:'Conflicts with priorities',mixed:'Gains and sacrifices within priorities',incomplete:'Some priority effects remain unresolved',constraints_violated:'Protected-player constraint violated',unchanged:'No directional priority change'}[assessment?.status]||'Needs deeper evaluation';
    return `<section class="se-side"><h3>${esc(title)}</h3><p class="se-context">${esc(assessment?.context?.explicitly_directed?'Your chosen direction: ':'Inferred direction: ')}${esc(priorities(assessment?.context))}</p><div class="se-metrics">${metric('Current lineup',points,weekly?'points / remaining regular-season week':'points / optimized horizon')}${metric('3-Year contribution',native('three_year'),'raw Shapley contribution')}${metric('Career contribution',native('career'),'raw Shapley contribution')}</div><p class="se-status">${esc(status)}</p><p class="se-market">Net Market change after cuts: <b>${esc(signed(marketDelta,0))}</b></p>${market?.required_cut_count?`<p class="se-caution">${esc(market.required_cut_count)} required roster cut(s) included in the accounting.</p>`:''}${assessment?.protected_players_lost?.length?'<p class="se-caution">A protected player would be lost. Change this package before evaluating.</p>':''}</section>`;
  }
  function packageAssets(items){return(items||[]).map(a=>{const info=asset(a.asset_ref);return `<div class="se-asset"><span class="se-avatar" aria-hidden="true">${esc((info?.detail||info?.asset_kind||'Asset').slice(0,4))}</span><div><b>${info?.player_id?`<button type="button" class="pi-player-link" data-player-intelligence-id="${esc(info.player_id)}">${esc(a.label||info.label)}</button>`:esc(a.label||a.asset_ref)}</b><small>${esc(info?.detail||info?.asset_kind||'Asset')}</small></div></div>`;}).join('');}
  const hypotheses={roster_fit:'Roster construction',three_year_contribution:'3-Year contribution',career_contribution:'Career contribution',rank_disagreement_three_year_contribution:'Intrinsic / Market rank disagreement',rank_disagreement_career_contribution:'Intrinsic / Market rank disagreement',package_structure:'Package structure',feedback_repair:'Alternative package'};
  function card(row,rows){
    const index=rows.indexOf(row);
    const name=teamName(row.counterparty_team_id);
    const lineages=row.repair_lineages||[];
    const related=rows.filter(other=>other.point_id!==row.point_id&&(lineages.some(l=>l.root_point_id===other.point_id||l.parent_point_id===other.point_id)||(other.repair_lineages||[]).some(l=>l.root_point_id===row.point_id||l.parent_point_id===row.point_id)));
    const blocked=['side_a','side_b'].some(s=>row.objective_assessment?.[s]?.protected_players_lost?.length);
    return `<article class="se-card"><header><div class="se-row"><span class="eyebrow">${esc(row.evaluation_kind==='repair'?'Alternative to investigate':'Opportunity to investigate')}</span><small>${esc(name)}</small></div><h2>Explore ${(row.receive||[]).map(a=>esc(a.label||a.asset_ref)).join(' + ')}</h2><p>${esc((row.hypotheses||[]).map(h=>hypotheses[h]||h.replaceAll('_',' ')).join(' · '))}</p></header><div class="se-card-body"><p class="eyebrow">You receive</p>${packageAssets(row.receive)}<p class="eyebrow se-send">In exchange for</p>${packageAssets(row.send)}${side(row,'side_a','What changes for you')}${side(row,'side_b','Why '+name+' might consider it')}<p class="se-caution">Both sides’ gains and costs are shown separately. A benefit on one horizon can come with a sacrifice on another. Owner willingness is unknown.</p>${related.length?`<details class="se-alternatives"><summary>Compare linked package alternatives</summary>${related.map(other=>`<div><b>You give:</b> ${esc((other.send||[]).map(a=>a.label).join(' + '))}<br><b>You get:</b> ${esc((other.receive||[]).map(a=>a.label).join(' + '))}<p>${esc(other.evidence_status==='pre_simulation_screened'?'Preliminary effects are shown in its own card.':'Effects are incomplete; no benefit is assumed.')}</p><button type="button" class="text-button" data-se-compare="${rows.indexOf(other)}">View this alternative</button></div>`).join('')}<p>These are explored alternatives, not a guarantee of the best possible package.</p></details>`:''}<p class="se-footnote">Lineup changes are preliminary. Wins, playoff odds and championship impact require Simulation in Trade Center. Native contribution is not total franchise utility; horizons overlap and must not be added.</p><button type="button" class="primary-button se-evaluate" data-se-evaluate="${index}"${blocked?' disabled':''}>Evaluate in Trade Center →</button></div></article>`;
  }
  function results(){
    if(view.dirty)return '<div class="se-empty" role="status"><b>Your search has changed.</b><p>Run discovery to see opportunities for these settings.</p></div>';
    if(view.busy)return '<div class="se-empty" role="status"><b>Looking for complementary interests…</b><p>Comparing bounded packages and both teams’ tradeoffs.</p></div>';
    if(view.error)return `<div class="se-empty" role="alert"><b>Discovery couldn’t complete.</b><p>${esc(view.error)}</p><p>Your settings are preserved. Try again when intelligence work is available.</p></div>`;
    if(!view.result)return '';
    const rows=view.result.candidate_packages||[];
    const screened=rows.filter(r=>r.evidence_status==='pre_simulation_screened');
    const others=rows.filter(r=>r.evidence_status!=='pre_simulation_screened');
    return `<section class="se-results"><p class="eyebrow">Opportunities to investigate</p><h2>See the upside. Know the cost.</h2><p class="se-footnote">${screened.length} preliminarily evaluated packages. Search order is preserved; these are not confirmed mutually beneficial recommendations.</p>${screened.length?screened.map(r=>card(r,rows)).join(''):'<div class="se-empty"><b>No complete preliminary package yet.</b><p>This bounded search does not establish that no useful trade exists. Broaden the constraints or inspect incomplete candidates below.</p></div>'}${others.length?`<details class="se-more"><summary>${others.length} additional candidates with incomplete evaluation</summary><p>Structural hypotheses or unavailable screens. Effects remain unknown.</p>${others.map(r=>card(r,rows)).join('')}</details>`:''}<details class="se-evidence"><summary>Search coverage & evidence</summary><p>At most 80 packages and 8 detailed preliminary screens per search. No automatic full-season simulation. Missing values remain unavailable. Team priorities are inferred unless you direct the search; historical owner behavior has not been used to learn preferences.</p><p>State: ${esc(view.result.league_state_id)}<br>Publication: ${esc(view.result.publication_generation_id||'Unavailable')}</p><p>Owner willingness and statistical significance are unconfirmed. Market context is separate from contribution and competitive outcomes.</p></details></section>`;
  }
  function paint(){
    if(!visibleHost())return;
    host.innerHTML=`<div class="strategic-explore">${direction()}${refinements()}<button type="button" class="primary-button se-search" data-se-run${view.busy?' disabled':''}>${view.busy?'Discovering…':'Find opportunities'}</button>${results()}</div>`;
    wire();
  }
  function changed(){view.expanded=host?.querySelector('.se-refine')?.open??view.expanded;view.sequence+=1;view.dirty=true;paint();}
  function wire(){
    host.querySelectorAll('[data-se-mode]').forEach(b=>b.addEventListener('click',()=>{if(view.mode===b.dataset.seMode)return;view.mode=b.dataset.seMode;changed();}));
    host.querySelector('[data-se-goal]')?.addEventListener('change',e=>{view.goal=e.target.value;changed();});
    host.querySelector('.se-refine')?.addEventListener('toggle',e=>{if(e.target.isConnected)view.expanded=e.target.open;});
    for(const name of ['position','partner','target'])host.querySelector('[data-se-'+name+']')?.addEventListener('change',e=>{view[name]=e.target.value;if(name!=='target')view.target='';changed();});
    host.querySelectorAll('[data-se-protect]').forEach(b=>b.addEventListener('change',()=>{const set=new Set(view.protected);b.checked?set.add(b.dataset.seProtect):set.delete(b.dataset.seProtect);view.protected=[...set];changed();}));
    host.querySelector('[data-se-run]')?.addEventListener('click',run);
    host.querySelectorAll('[data-se-evaluate]').forEach(b=>b.addEventListener('click',()=>{
      if(view.dirty||view.key!==contextKey())return;
      const row=view.result?.candidate_packages?.[Number(b.dataset.seEvaluate)];
      if(row)window.fsfflOpenOpportunityInTradeCenter?.({...row,league_state_id:view.result.league_state_id,counterparty_name:teamName(row.counterparty_team_id)});
    }));
    host.querySelectorAll('[data-se-compare]').forEach(b=>b.addEventListener('click',()=>{
      const i=b.dataset.seCompare,target=host.querySelector('[data-se-evaluate="'+i+'"]')?.closest('.se-card');
      if(target){let parent=target.parentElement;while(parent&&parent!==host){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}target.scrollIntoView({behavior:'smooth',block:'start'});}
    }));
  }
  async function run(){
    reconcile();if(view.inFlight||!ctx().team_id||!ctx().state_id)return;
    let body;try{body=requestBody();}catch(error){view.error=error.message;view.dirty=false;paint();return;}
    const current=view,key=view.key,id=++view.sequence;
    const active=()=>view===current&&contextKey()===key&&id===view.sequence;
    view.started=true;view.busy=true;view.inFlight=true;view.error='';view.dirty=false;paint();
    // One request per submitted search; no polling, automatic retries or Simulation.
    try{
      const result=await api('/api/opportunities/strategic-discover',{method:'POST',body:JSON.stringify(body)});
      if(!active())return;
      const generation=ctx().capability_readiness?.publication?.generation_id||ctx().publication_generation_id;
      if(result.league_state_id!==ctx().state_id||result.focal_team_id!==ctx().team_id||(generation&&result.publication_generation_id!==generation))throw new Error('League intelligence changed. Reload Explore for current evidence.');
      view.result=result;
    }catch(error){if(active()){view.error=error?.message||'Please retry discovery.';view.result=null;}}
    finally{if(view===current&&contextKey()===key){view.inFlight=false;view.busy=false;paint();}}
  }
  async function loadBrowser(){
    const current=view,key=view.key;
    try{const browser=await api('/api/trade-center/browser');if(view!==current||key!==contextKey())return;if(browser.state_id!==ctx().state_id||browser.focal_team?.team_id!==ctx().team_id)throw new Error('League ownership changed. Reload Explore.');view.browser=browser;}
    catch(error){if(view===current&&key===contextKey())view.browserError=error?.message||'Search controls are unavailable.';}
    if(view===current)paint();
  }
  function render(body){
    reconcile();host=body;
    if(!ctx().league_id||!ctx().team_id||!ctx().state_id){host.innerHTML='<div class="se-empty"><b>Connect a league and choose your franchise to discover trades.</b></div>';return;}
    paint();if(!view.started){void loadBrowser();void run();}
  }
  window.fsfflStrategicExplore={render,run,priorities};
  window.addEventListener('fsffl:product-context-updated',()=>{reconcile();});
})();
