/* Phase 3 commercial cold-path delivery.
 * Presentation coordinates existing server-owned Search, Decision and Simulation truth.
 * It never computes a replacement value, trade decision, or competitive outcome.
 */
(function(){
  'use strict';
  const VERSION='20260913-phase3-latency1';
  let marketInstalled=false;
  let tradeGeneration=0;
  let activeTradeKey=null;

  function productState(){try{return typeof state!=='undefined'?state:null}catch(_){return null}}
  function opportunityStore(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function contextKey(){const c=productState()?.context||{};return`${c.league_id||''}|${c.team_id||''}|${c.state_id||''}`}
  function stableDraft(){try{if(typeof tradeDraftPayload!=='function')return null;const p=tradeDraftPayload();return{counterparty_team_id:p.counterparty_team_id,focal_asset_refs:[...(p.focal_asset_refs||[])].sort(),counterparty_asset_refs:[...(p.counterparty_asset_refs||[])].sort()}}catch(_){return null}}
  function draftKey(){const p=stableDraft();return p?`${contextKey()}|${p.counterparty_team_id}|${p.focal_asset_refs.join(',')}|${p.counterparty_asset_refs.join(',')}`:null}
  function currentTrade(generation,key){return generation===tradeGeneration&&key===draftKey()}
  function responseMatchesState(result,expectedStateId){return !expectedStateId||result?.state_id_before===expectedStateId}
  function currentStateId(){return productState()?.context?.state_id||null}
  function esc(value){try{return typeof escapeHtml==='function'?escapeHtml(value):String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}catch(_){return String(value??'')}}
  function request(path,options){return api(path,options)}

  function renderQuickTrade(result){
    const host=document.querySelector('#trade-analysis-empty');if(!host)return;
    const sides=[result.economics?.side_a,result.economics?.side_b].filter(Boolean);
    const sideCards=sides.map(side=>{let team=side.team_id;try{if(typeof tradeTeamName==='function')team=tradeTeamName(side.team_id)}catch(_){}const format=value=>{try{return typeof fmtNumber==='function'?fmtNumber(value,2):value??'—'}catch(_){return value??'—'}};return`<article class="fsffl-progressive-side"><strong>${esc(team)}</strong><div><span>Market evidence sent</span><b>${esc(format(side.sent_market?.mean_value))}</b></div><div><span>Market evidence received</span><b>${esc(format(side.received_market?.mean_value))}</b></div></article>`}).join('');
    host.innerHTML=`<section class="fsffl-progressive-answer" data-progressive-stage="quick"><header><div><p class="eyebrow">Quick view ready</p><h3>Package evidence is ready while the deeper roster analysis runs.</h3></div><span class="status-chip">Partial</span></header><p>Canonical ownership and the proposed changed state are valid. These package economics come from the existing governed Value/Trade economics path; they are not a final trade recommendation.</p><div class="fsffl-progressive-sides">${sideCards||'<p>Package Value evidence is currently unavailable.</p>'}</div><div class="fsffl-progressive-next"><strong>Still calculating</strong><span>Roster and lineup consequences → full 50,000-run season simulation</span></div></section>`;
  }

  function appendProgress(message,kind='working'){
    const host=document.querySelector('#trade-analysis-empty');if(!host)return;
    let node=host.querySelector('.fsffl-progressive-status');
    if(!node){node=document.createElement('div');node.className='fsffl-progressive-status';host.appendChild(node)}
    node.dataset.kind=kind;node.textContent=message;
  }

  function resetTradeForContext(){
    tradeGeneration+=1;activeTradeKey=null;
    const button=document.querySelector('#analyze-trade');
    if(button){button.textContent='Analyze Trade';try{if(typeof updateAnalyzeTradeState==='function')updateAnalyzeTradeState()}catch(_){button.disabled=false}}
  }

  async function runProgressiveTrade(event){
    const button=event.target?.closest?.('#analyze-trade');if(!button||button.disabled)return;
    event.preventDefault();event.stopImmediatePropagation();
    const key=draftKey(),payload=stableDraft(),startingStateId=currentStateId();if(!key||!payload)return;
    if(activeTradeKey===key)return;
    const generation=++tradeGeneration;activeTradeKey=key;
    button.disabled=true;button.textContent='Checking trade…';
    try{if(typeof invalidateTradeScenario==='function')invalidateTradeScenario()}catch(_){}
    const host=document.querySelector('#trade-analysis-empty');if(host)host.innerHTML='<div class="fsffl-progressive-loading"><p class="eyebrow">Checking this trade</p><h3>Building the quick governed view…</h3></div>';
    try{
      const quick=await request('/api/trade-center/quick',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      if(!responseMatchesState(quick,startingStateId))throw new Error('League data changed while this trade was starting. Run the analysis again on the updated league state.');
      const flowStateId=quick.state_id_before||startingStateId;
      renderQuickTrade(quick);
      button.textContent='Full roster analysis running…';

      const analysis=await request('/api/trade-center/analyze',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      if(!responseMatchesState(analysis,flowStateId))throw new Error('League data changed during roster analysis. The earlier quick view remains scoped to the prior state; run this trade again.');
      if(typeof renderTradeAnalysis==='function')renderTradeAnalysis(analysis);
      ['#simulate-trade','#explore-price'].forEach(selector=>{const action=document.querySelector(selector);if(action)action.disabled=false});
      appendProgress('Roster analysis ready. Full 50,000-run season simulation running…');
      button.textContent='Full simulation running…';

      const simulation=await request('/api/trade-center/simulate',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      if(!responseMatchesState(simulation,flowStateId))throw new Error('League data changed before the full simulation finished. The prior-stage evidence remains scoped to the earlier state; run this trade again.');
      if(typeof renderTradeSimulationResult==='function')renderTradeSimulationResult(simulation);
      appendProgress(simulation.scenario_cache_hit?'Full analysis ready · exact Simulation result reused.':'Full analysis ready · 50,000-run simulation complete.','ready');
    }catch(error){
      if(!currentTrade(generation,key))return;
      if(document.querySelector('.fsffl-progressive-answer'))appendProgress(`Deeper analysis could not finish: ${error.message}. The quick package evidence above remains valid for its stated scope.`,'error');
      else if(host)host.innerHTML=`<div class="chart-empty"><p>Trade analysis is unavailable: ${esc(error.message)}</p></div>`;
    }finally{
      if(generation===tradeGeneration){activeTradeKey=null;button.textContent='Analyze Trade';try{if(typeof updateAnalyzeTradeState==='function')updateAnalyzeTradeState()}catch(_){button.disabled=false}}
    }
  }

  function installTrade(){window.addEventListener('click',runProgressiveTrade,true)}

  function installMarketWrapper(){
    let available=false;try{available=typeof loadOpportunityWorkspace==='function'&&typeof oppContextSnapshot==='function'}catch(_){}
    if(marketInstalled||!available)return;
    marketInstalled=true;
    const progressive=async function({showLoading=true}={}){
      const store=opportunityStore();if(!store||store.loading)return;
      const captured=oppContextSnapshot(),requestId=++store.requestSequence;
      store.loading=true;try{oppCancelRetry()}catch(_){}if(showLoading)try{oppLoading()}catch(_){}
      const contextStillCurrent=()=>requestId===store.requestSequence&&oppContextSnapshot().key===captured.key;
      try{
        const sideEvidence=Promise.all([
          request('/api/behavioral/profiles').catch(()=>({status:'unavailable',profiles:[]})),
          captured.teamId?request('/api/my-team').catch(()=>null):Promise.resolve(null),
        ]);
        const quick=await request('/api/opportunities/workspace/quick');
        if(!contextStillCurrent()||!oppPayloadMatchesCapturedContext(quick,captured))return;
        const[behavior,team]=await sideEvidence;if(!contextStillCurrent())return;
        store.payload=quick;store.behavior=behavior;store.team=team;store.loading=false;
        renderOpportunityWorkspace();
        const panel=document.querySelector('#generic-screen .panel');
        panel?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress"><strong>Quick view ready</strong><span>More bilateral trade evidence is loading.</span></div>');

        request('/api/opportunities/workspace').then(full=>{
          if(!contextStillCurrent()||!oppPayloadMatchesCapturedContext(full,captured))return;
          store.payload=full;renderOpportunityWorkspace();
          const current=document.querySelector('#generic-screen .panel');
          current?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress ready"><strong>Updated analysis ready</strong><span>Bounded bilateral Decision evidence has been added.</span></div>');
        }).catch(()=>{
          if(!contextStillCurrent())return;
          const current=document.querySelector('#generic-screen .panel');
          current?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress"><strong>Quick view remains available</strong><span>Deeper bilateral evidence could not finish.</span></div>');
        });
      }catch(error){if(contextStillCurrent())try{oppError(error.message)}catch(_){}}finally{if(requestId===store.requestSequence)store.loading=false}
    };
    window.loadOpportunityWorkspace=progressive;window.renderFsfflOpportunities=progressive;
    try{loadOpportunityWorkspace=progressive}catch(_){/* lexical global may not be assignable */}
  }

  function installMarket(){
    let original=null;try{original=typeof ensureOpportunitiesScript==='function'?ensureOpportunitiesScript:null}catch(_){}
    if(typeof original==='function'&&!original.__fsfflProgressive){
      const wrapped=function(){return original().then(()=>{installMarketWrapper()})};wrapped.__fsfflProgressive=true;
      window.ensureOpportunitiesScript=wrapped;try{ensureOpportunitiesScript=wrapped}catch(_){/* fallback polling below */}
    }
    const timer=setInterval(()=>{installMarketWrapper();if(marketInstalled)clearInterval(timer)},50);
    setTimeout(()=>clearInterval(timer),15000);
  }

  window.addEventListener('fsffl:product-context-updated',resetTradeForContext);
  installTrade();installMarket();
  window.fsfflProgressiveDelivery={version:VERSION,installMarketWrapper};
})();
