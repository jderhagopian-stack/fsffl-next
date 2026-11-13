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
  const fresh=()=>({key:contextKey(),sequence:0,result:null,browser:null,busy:false,inFlight:false,pauseRequested:false,pendingBatch:null,started:false,error:'',browserError:'',browserLoading:false,mode:'automatic',goal:ALL[0],partner:'',position:'',target:'',offer:'',protected:[],directed:false,intentKey:'',expanded:false,dirty:false});
  let view=fresh(),host=null;
  function reconcile(){if(view.key!==contextKey())view=fresh();}
  function visibleHost(){return host?.isConnected&&typeof state!=='undefined'&&state.route==='opportunities'&&host.id==='market-ns-body'&&['for_you','trade_finder'].includes(window.fsfflMarketNorthStar?.activeTab?.());}
  const asset=ref=>[view.browser?.focal_team,...(view.browser?.counterparties||[])].filter(Boolean).flatMap(t=>t.assets||[]).find(a=>a.asset_ref===ref);
  const teamName=id=>(view.browser?.counterparties||[]).find(t=>t.team_id===id)?.display_name||'Other franchise';
  const option=(v,label,selected)=>`<option value="${esc(v)}"${selected===v?' selected':''}>${esc(label)}</option>`;
  function instructions(){
    if(view.mode==='automatic')return view.protected.length?{protected_player_ids:[...view.protected]}:null;
    return{objectives:view.goal==='all'?ALL:[view.goal],protected_player_ids:[...view.protected]};
  }
  function requestBody(){const body={max_candidates:80,evaluation_budget:8};const goals=instructions();if(goals)body.search_instructions=goals;if(view.partner)body.counterparty_team_id=view.partner;if(view.position)body.target_position=view.position;if(view.target)body.target_asset_ref=view.target;if(view.offer)body.offered_asset_ref=view.offer;return body;}
  function priorities(context){return(context?.objectives||[]).map(g=>GOALS[g]||g.replaceAll('_',' ')).join(' / ')||'Direction unavailable';}
  const stateNames={contender:'Contender',competitive:'Competitive',developing:'Developing',rebuilding:'Rebuilding',unknown:'Unavailable'};
  const postureNames={win_now:'Win now',balanced:'Balanced',retool:'Build over 3 years',rebuild:'Build for the long term'};
  const pct=value=>finite(value)?(value*100).toFixed(1)+'%':'Unavailable';
  function direction(){
    const competitive=view.result?.competitive_context;
    const priority=view.result?.priority_context;
    const calculated=competitive?.calculated_competitive_state||(!priority?.explicitly_directed?priority?.calculated_competitive_state:null)||'unknown';
    const posture=competitive?.default_search_posture||(!priority?.explicitly_directed?priority?.inferred_posture:null);
    const inferred=priority?.explicitly_directed?null:priority;
    const lens=calculated==='unknown'?'Compare all horizons · state unavailable':postureNames[posture]||'Direction preparing';
    return `<section class="se-direction"><div class="se-row"><p class="eyebrow">Your Direction</p><small>You’re in control</small></div><div class="se-competitive"><span>Calculated competitive state</span><strong>${esc(stateNames[calculated]||calculated)}</strong>${competitive?`<p>Playoff chance <b>${pct(competitive.playoff_probability)}</b> · Championship chance <b>${pct(competitive.championship_probability)}</b></p>`:''}</div><div class="se-modes" role="group" aria-label="Search direction">${[['automatic','Automatic'],['custom','Set priorities']].map(([key,label])=>`<button type="button" data-se-mode="${key}" aria-pressed="${view.mode===key}">${label}</button>`).join('')}</div>${view.mode==='custom'?`<label class="se-field"><span>Your priority</span><select data-se-goal>${Object.entries(GOALS).map(([g,label])=>option(g,label,view.goal)).join('')}${option('all','Compare all horizons',view.goal)}</select></label><p>Your instruction overrides the automatic search direction. The calculated state stays unchanged.</p>`:`<span class="se-direction-label">Automatic lens: ${esc(lens)}</span><p>${esc(inferred?priorities(inferred):'Server priorities will be shown after discovery.')}</p><p>${calculated==='unknown'?'No competitive-state inference is available; all horizons remain explicit.':'Competitive state informs this default lens; it does not establish your personal goals.'}</p>`}<details class="se-evidence"><summary>How this direction is determined</summary><p>Current policy uses league-relative playoff and regular-season first-place odds. Contender maps to Win now; Competitive to Balanced; Developing to 3-Year; Rebuilding to Career. The classification is provisional. Championship odds are shown separately.</p><p>Balanced compares Current, 3-Year and Career without blending them into a score. Known losses remain visible. You can select a different direction; owner preferences and willingness are not confirmed.</p></details></section>`;
  }
  function refinements(){
    const others=(view.browser?.counterparties||[]).filter(t=>!view.partner||t.team_id===view.partner);
    const assets=others.flatMap(t=>(t.assets||[]).filter(a=>!view.position||a.detail===view.position).map(a=>({...a,team:t.display_name})));
    const positions=[...new Set((view.browser?.counterparties||[]).flatMap(t=>(t.assets||[]).filter(a=>a.asset_kind==='player').map(a=>a.detail)).filter(Boolean))].sort();
    return `<details class="se-refine"${view.expanded?' open':''}><summary><span><b>Refine your search</b><small>Target or offer an asset, protect players, or choose a partner.</small></span><span aria-hidden="true">＋</span></summary><div class="se-refine-fields">${view.browserError?`<p role="alert">${esc(view.browserError)}</p>`:''}<label class="se-field"><span>Target position</span><select data-se-position${!view.browser?' disabled':''}>${option('','Any position',view.position)}${positions.map(p=>option(p,p,view.position)).join('')}</select></label><label class="se-field"><span>Trade partner</span><select data-se-partner${!view.browser?' disabled':''}>${option('','Across the league',view.partner)}${(view.browser?.counterparties||[]).map(t=>option(t.team_id,t.display_name,view.partner)).join('')}</select></label><label class="se-field"><span>Target an asset</span><select data-se-target${!view.browser?' disabled':''}>${option('','No specific target',view.target)}${assets.map(a=>option(a.asset_ref,a.label+' · '+a.team,view.target)).join('')}</select></label><label class="se-field"><span>Offer / shop an asset</span><select data-se-offer${!view.browser?' disabled':''}>${option('','No required outgoing asset',view.offer)}${(view.browser?.focal_team?.assets||[]).map(a=>option(a.asset_ref,a.label,view.offer)).join('')}</select></label><fieldset class="se-protect"><legend>Keep these players</legend><p>Protected players cannot be sent or included in required cuts.</p>${(view.browser?.focal_team?.assets||[]).filter(a=>a.player_id).map(a=>`<label><input type="checkbox" data-se-protect="${esc(a.player_id)}"${view.protected.includes(a.player_id)?' checked':''}><span>${esc(a.label)}</span></label>`).join('')}</fieldset></div></details>`;
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
    const competitive=view.result?.team_competitive_contexts?.[assessment?.context?.team_id];
    const calculated=competitive?.calculated_competitive_state||assessment?.context?.calculated_competitive_state||'unknown';
    const status={aligns_with_priorities:'Direction aligns with priorities',conflicts_with_priorities:'Conflicts with priorities',mixed:'Gains and sacrifices within priorities',incomplete:'Some priority effects remain unresolved',constraints_violated:'Protected-player constraint violated',unchanged:'No directional priority change'}[assessment?.status]||'Needs deeper evaluation';
    return `<section class="se-side"><h3>${esc(title)}</h3><p class="se-context">Calculated state: <b>${esc(stateNames[calculated]||calculated)}</b></p><p class="se-context">${esc(assessment?.context?.explicitly_directed?'Your chosen direction: ':'Inferred direction: ')}${esc(priorities(assessment?.context))}</p><div class="se-metrics">${metric('Current lineup',points,weekly?'points / remaining regular-season week':'points / optimized horizon')}${metric('3-Year contribution',native('three_year'),'raw Shapley contribution')}${metric('Career contribution',native('career'),'raw Shapley contribution')}</div><p class="se-status">${esc(status)}</p><p class="se-market">Net Market change after cuts: <b>${esc(signed(marketDelta,0))}</b></p>${market?.required_cut_count?`<p class="se-caution">${esc(market.required_cut_count)} required roster cut(s) included in the accounting.</p>`:''}${assessment?.protected_players_lost?.length?'<p class="se-caution">A protected player would be lost. Change this package before evaluating.</p>':''}</section>`;
  }
  function packageAssets(items){return(items||[]).map(a=>{const info=asset(a.asset_ref),pick=view.result?.pick_evidence?.[a.asset_ref];return `<div class="se-asset"><span class="se-avatar" aria-hidden="true">${esc((info?.detail||info?.asset_kind||'Asset').slice(0,4))}</span><div><b>${info?.player_id?`<button type="button" class="pi-player-link" data-player-intelligence-id="${esc(info.player_id)}">${esc(a.label||info.label)}</button>`:esc(a.label||a.asset_ref)}</b><small>${esc(info?.detail||info?.asset_kind||'Asset')}</small>${pick?`<small>${finite(pick.expected_slot)?'Current projected slot '+pick.expected_slot.toFixed(1)+' · before trade / uncertain':'Draft slot unavailable'} · 3-Year / Career Intrinsic unavailable</small>`:''}</div></div>`;}).join('');}
  const hypotheses={roster_fit:'Roster construction',three_year_contribution:'3-Year contribution',career_contribution:'Career contribution',rank_disagreement_three_year_contribution:'Intrinsic / Market rank disagreement',rank_disagreement_career_contribution:'Intrinsic / Market rank disagreement',package_structure:'Package structure',feedback_repair:'Alternative package'};
  function card(row,rows){
    const index=rows.indexOf(row);
    const name=teamName(row.counterparty_team_id);
    const lineages=row.repair_lineages||[];
    const related=rows.filter(other=>other.point_id!==row.point_id&&((row.linked_prior_point_ids||[]).includes(other.point_id)||lineages.some(l=>l.root_point_id===other.point_id||l.parent_point_id===other.point_id)||(other.repair_lineages||[]).some(l=>l.root_point_id===row.point_id||l.parent_point_id===row.point_id)));
    const blocked=['side_a','side_b'].some(s=>row.objective_assessment?.[s]?.protected_players_lost?.length);
    return `<article class="se-card" data-se-group="${esc(row.display_context?.group||'needs_evidence')}"><header><div class="se-row"><span class="eyebrow">${esc(row.display_context?.group==='priority_concern'?'Priority concern':row.evaluation_kind==='repair'?'Alternative to investigate':'Opportunity to investigate')}</span><small>${esc(name)}</small></div><h2>Explore ${(row.receive||[]).map(a=>esc(a.label||a.asset_ref)).join(' + ')}</h2><p>${esc((row.hypotheses||[]).map(h=>hypotheses[h]||h.replaceAll('_',' ')).join(' · '))}</p></header><div class="se-card-body">${row.display_context?.reason?`<p class="se-fit-note">${esc(row.display_context.reason)}</p>`:''}<p class="eyebrow">You receive</p>${packageAssets(row.receive)}<p class="eyebrow se-send">In exchange for</p>${packageAssets(row.send)}${side(row,'side_a','What changes for you')}${side(row,'side_b','Why '+name+' might consider it')}<p class="se-caution">Both sides’ gains and costs are shown separately. A benefit on one horizon can come with a sacrifice on another. Owner willingness is unknown.</p>${related.length?`<details class="se-alternatives"><summary>Compare linked package alternatives</summary>${related.map(other=>`<div><b>You give:</b> ${esc((other.send||[]).map(a=>a.label).join(' + '))}<br><b>You get:</b> ${esc((other.receive||[]).map(a=>a.label).join(' + '))}<p>${esc(other.evidence_status==='pre_simulation_screened'?'Preliminary effects are shown in its own card.':'Effects are incomplete; no benefit is assumed.')}</p><button type="button" class="text-button" data-se-compare="${rows.indexOf(other)}">View this alternative</button></div>`).join('')}<p>These are explored alternatives, not a guarantee of the best possible package.</p></details>`:''}<p class="se-footnote">Lineup changes are preliminary. Wins, playoff odds and championship impact require Simulation in Trade Center. Native contribution is not total franchise utility; horizons overlap and must not be added.</p><button type="button" class="primary-button se-evaluate" data-se-evaluate="${index}"${blocked?' disabled':''}>Evaluate in Trade Center →</button></div></article>`;
  }
  function results(){
    if(view.dirty)return '<div class="se-empty" role="status"><b>Your search has changed.</b><p>Run discovery to see opportunities for these settings.</p></div>';
    if(view.busy&&!view.result)return '<div class="se-empty" role="status"><b>Looking for complementary interests…</b><p>Comparing bounded packages and both teams’ tradeoffs.</p></div>';
    if(view.error&&!view.result)return `<div class="se-empty" role="alert"><b>Discovery couldn’t complete.</b><p>${esc(view.error)}</p><p>Your settings are preserved. Try again when intelligence work is available.</p></div>`;
    if(!view.result)return '';
    const rows=view.result.candidate_packages||[];
    const fits=rows.filter(r=>r.display_context?.group==='preliminary_fit');
    const tradeoffs=rows.filter(r=>r.display_context?.group==='priority_tradeoff');
    const concerns=rows.filter(r=>r.display_context?.group==='priority_concern');
    const others=rows.filter(r=>!['preliminary_fit','priority_tradeoff','priority_concern'].includes(r.display_context?.group));
    return `${progressMarkup()}<section class="se-results"><p class="eyebrow">Opportunities to investigate</p><h2>See the upside. Know the cost.</h2><p class="se-footnote">Grouped by both teams’ requested priorities. Preliminary lineup evidence is a proxy; final competitive effects and owner willingness remain unconfirmed.</p>${fits.length?fits.map(r=>card(r,rows)).join(''):'<div class="se-empty"><b>No preliminary fit established yet.</b><p>This bounded search has not established gains without priority losses for both sides. Review the tradeoffs below or choose a more specific direction.</p></div>'}${tradeoffs.length?`<section class="se-tradeoffs"><h3>Tradeoffs to review</h3><p class="se-footnote">These packages improve some requested priorities while sacrificing others. They are not clear fits for the full selected lens.</p>${tradeoffs.map(r=>card(r,rows)).join('')}</section>`:''}${concerns.length?`<details class="se-more" data-se-concerns><summary>${concerns.length} packages with known priority losses</summary><p>Retained for comparison and repair history. A Market gain does not establish a benefit to your selected priorities.</p>${concerns.map(r=>card(r,rows)).join('')}</details>`:''}${others.length?`<details class="se-more"><summary>${others.length} additional candidates with incomplete evaluation</summary><p>Effects or benefits to both sides remain unconfirmed.</p>${others.map(r=>card(r,rows)).join('')}</details>`:''}<details class="se-evidence"><summary>Search coverage & evidence</summary><p>At most 80 displayed packages; up to 8 preliminary screens per batch and 32 per search. Pick packages are included, but native pick Intrinsic remains unavailable. Automatic repairs currently use players only. Order within each group is preserved. No automatic full-season simulation. Missing values remain unavailable. Team goals are inferred unless you direct the search; historical owner behavior has not been used to learn preferences.</p><p>State: ${esc(view.result.league_state_id)}<br>Publication: ${esc(view.result.publication_generation_id||'Unavailable')}</p><p>Native contribution is not full franchise utility. Market context is separate from contribution and competitive outcomes. These groups do not change Decision authority or establish a final recommendation.</p></details></section>`;
  }

  function paint(){
    if(!visibleHost())return;
    host.innerHTML=`<div class="strategic-explore">${view.directed?'<section class="se-section-head"><p class="eyebrow">Directed search</p><h2>Shop an asset or target a move</h2><p class="se-footnote">The same discovery engine, with your chosen constraints.</p></section>':''}${direction()}${refinements()}<button type="button" class="primary-button se-search" data-se-run${view.busy?' disabled':''}>${view.busy?'Discovering…':'Find opportunities'}</button>${results()}</div>`;
    wire();
  }
  function changed(){view.expanded=host?.querySelector('.se-refine')?.open??view.expanded;view.sequence+=1;view.dirty=true;paint();}
  function wire(){
    host.querySelectorAll('[data-se-mode]').forEach(b=>b.addEventListener('click',()=>{if(view.mode===b.dataset.seMode)return;view.mode=b.dataset.seMode;changed();}));
    host.querySelector('[data-se-goal]')?.addEventListener('change',e=>{view.goal=e.target.value;changed();});
    host.querySelector('.se-refine')?.addEventListener('toggle',e=>{if(e.target.isConnected)view.expanded=e.target.open;});
    for(const name of ['position','partner','target','offer'])host.querySelector('[data-se-'+name+']')?.addEventListener('change',e=>{view[name]=e.target.value;if(['position','partner'].includes(name))view.target='';changed();});
    host.querySelectorAll('[data-se-protect]').forEach(b=>b.addEventListener('change',()=>{const set=new Set(view.protected);b.checked?set.add(b.dataset.seProtect):set.delete(b.dataset.seProtect);view.protected=[...set];changed();}));
    host.querySelector('[data-se-run]')?.addEventListener('click',()=>run());
    host.querySelector('[data-se-more]')?.addEventListener('click',()=>run({continueSearch:true}));
    host.querySelector('[data-se-pause]')?.addEventListener('click',()=>{view.pauseRequested=true;paint();});
    host.querySelectorAll('[data-se-evaluate]').forEach(b=>b.addEventListener('click',async()=>{
      if(view.dirty||view.key!==contextKey())return;
      const row=view.result?.candidate_packages?.[Number(b.dataset.seEvaluate)];
      const captured=view;view.pauseRequested=true;
      if(view.pendingBatch){try{await view.pendingBatch}catch(_){}}
      if(view!==captured||view.dirty||view.key!==contextKey())return;
      if(row)window.fsfflOpenOpportunityInTradeCenter?.({...row,league_state_id:view.result.league_state_id,counterparty_name:teamName(row.counterparty_team_id)});
    }));
    host.querySelectorAll('[data-se-compare]').forEach(b=>b.addEventListener('click',()=>{
      const i=b.dataset.seCompare,target=host.querySelector('[data-se-evaluate="'+i+'"]')?.closest('.se-card');
      if(target){let parent=target.parentElement;while(parent&&parent!==host){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}target.scrollIntoView({behavior:'smooth',block:'start'});}
    }));
  }
  function progressMarkup(){
    const p=view.result?.search_progress;
    if(!p)return '';
    const stop={shortlist_ready:'Preliminary shortlist ready',screening_limit:'Screening limit reached',pool_exhausted:'Bounded candidate pool exhausted',screening_disabled:'Screening disabled',continue:'More packages available'};
    return `<div class="se-progress" role="status"><b>${p.total_screened} packages evaluated · ${p.preliminary_fit_count} preliminary fits</b><p>${view.busy?(view.pauseRequested?'Finishing this batch, then pausing…':'Continuing in small batches…'):esc(stop[p.stop_reason]||'Search complete')} · up to ${p.max_total_screens} evaluations. These are preliminary fits, not confirmed beneficial trades.</p>${view.error?`<p role="alert">${esc(view.error)} Completed results are preserved.</p>`:''}${view.busy?'<button type="button" class="text-button" data-se-pause>Pause after this batch</button>':p.next_token?'<button type="button" class="secondary-button" data-se-more>Evaluate more packages</button>':''}</div>`;
  }
  function mergeBatch(previous,result){
    if(!previous)return result;
    const merged=new Map((previous.candidate_packages||[]).map(r=>[r.point_id,r]));
    for(const row of result.candidate_packages||[]){
      const old=merged.get(row.point_id);
      if(!old||!old.evaluation_kind||row.evaluation_kind)merged.set(row.point_id,row);
    }
    const all=[...merged.values()],evaluated=all.filter(r=>r.evaluation_kind);
    return {...result,pick_evidence:{...(previous.pick_evidence||{}),...(result.pick_evidence||{})},candidate_packages:[...evaluated,...all.filter(r=>!r.evaluation_kind)].slice(0,80)};
  }
  async function run({continueSearch=false}={}){
    reconcile();if(view.inFlight||!ctx().team_id||!ctx().state_id)return;
    if(continueSearch&&view.dirty)return;
    if(!view.browser)void loadBrowser();
    let body;try{body=requestBody();}catch(error){view.error=error.message;view.dirty=false;paint();return;}
    const current=view,key=view.key,id=++view.sequence;
    const active=()=>view===current&&contextKey()===key&&id===view.sequence&&state.route==='opportunities'&&['for_you','trade_finder'].includes(window.fsfflMarketNorthStar?.activeTab?.());
    let token=continueSearch?view.result?.search_progress?.next_token:null;
    if(continueSearch&&!token)return;
    if(!continueSearch)view.result=null;
    view.started=true;view.busy=true;view.inFlight=true;view.pauseRequested=false;view.error='';view.dirty=false;paint();
    // Sequential distinct batches only: no background polling, retry loop or Simulation.
    try{
      for(let batch=0;batch<4;batch++){
        view.pendingBatch=api('/api/opportunities/strategic-discover',{method:'POST',body:JSON.stringify({...body,...(token?{continuation_token:token}:{})})});
        const result=await view.pendingBatch;view.pendingBatch=null;
        if(!active())return;
        const generation=ctx().capability_readiness?.publication?.generation_id||ctx().publication_generation_id;
        if(result.league_state_id!==ctx().state_id||result.focal_team_id!==ctx().team_id||(generation&&result.publication_generation_id!==generation))throw new Error('League intelligence changed. Reload Explore for current evidence.');
        view.result=mergeBatch(view.result,result);paint();
        const progress=result.search_progress;
        token=progress?.next_token;
        if(view.pauseRequested||!token||progress.stop_reason!=='continue')break;
      }
    }catch(error){if(active())view.error=error?.message||'Please retry discovery.';}
    finally{if(view===current&&contextKey()===key){view.inFlight=false;view.pendingBatch=null;view.busy=false;paint();}}
  }
  async function loadBrowser(){
    if(view.browser||view.browserLoading)return;
    view.browserLoading=true;
    const current=view,key=view.key;
    try{const browser=await api('/api/trade-center/browser');if(view!==current||key!==contextKey())return;if(browser.state_id!==ctx().state_id||browser.focal_team?.team_id!==ctx().team_id)throw new Error('League ownership changed. Reload Explore.');view.browser=browser;}
    catch(error){if(view===current&&key===contextKey())view.browserError=error?.message||'Search controls are unavailable.';}
    if(view===current){view.browserLoading=false;paint();}
  }
  function render(body,payload,{directed=false}={}){
    reconcile();host=body;
    if(directed&&!view.directed)view.expanded=true;
    view.directed=directed;
    const intent=window.fsfflMarketIntent?.selected?.();
    const intentKey=JSON.stringify(intent||{});
    if(directed&&intent?.value&&view.intentKey!==intentKey){
      view.intentKey=intentKey;
      view.offer='';view.target='';view.position='';view.partner='';
      if(intent.intent==='shop')view.offer=intent.value;
      if(intent.intent==='target')view.target=intent.value;
      if(intent.intent==='position')view.position=intent.value;
      if(intent.intent==='owner')view.partner=intent.value;
      view.sequence+=1;view.dirty=true;
    }
    if(!ctx().league_id||!ctx().team_id||!ctx().state_id){host.innerHTML='<div class="se-empty"><b>Connect a league and choose your franchise to discover trades.</b></div>';return;}
    paint();if(!view.started){void loadBrowser();if(!directed&&!view.dirty)void run();}
  }
  window.fsfflStrategicExplore={render,run,priorities};
  window.addEventListener('fsffl:product-context-updated',()=>{reconcile();});
})();
