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

  function contextKey(){const c=window.state?.context||{};return`${c.league_id||''}|${c.team_id||''}|${c.state_id||''}`}
  function stableDraft(){if(typeof window.tradeDraftPayload!=='function')return null;const p=window.tradeDraftPayload();return{counterparty_team_id:p.counterparty_team_id,focal_asset_refs:[...(p.focal_asset_refs||[])].sort(),counterparty_asset_refs:[...(p.counterparty_asset_refs||[])].sort()}}
  function draftKey(){const p=stableDraft();return p?`${contextKey()}|${p.counterparty_team_id}|${p.focal_asset_refs.join(',')}|${p.counterparty_asset_refs.join(',')}`:null}
  function currentTrade(generation,key){return generation===tradeGeneration&&key===draftKey()}
  function esc(value){return typeof window.escapeHtml==='function'?window.escapeHtml(value):String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}

  function renderQuickTrade(result){
    const host=document.querySelector('#trade-analysis-empty');if(!host)return;
    const sides=[result.economics?.side_a,result.economics?.side_b].filter(Boolean);
    const sideCards=sides.map(side=>`<article class="fsffl-progressive-side"><strong>${esc(window.tradeTeamName?.(side.team_id)||side.team_id)}</strong><div><span>Market evidence sent</span><b>${esc(window.fmtNumber?.(side.sent_market?.mean_value,2)??side.sent_market?.mean_value??'—')}</b></div><div><span>Market evidence received</span><b>${esc(window.fmtNumber?.(side.received_market?.mean_value,2)??side.received_market?.mean_value??'—')}</b></div></article>`).join('');
    host.innerHTML=`<section class="fsffl-progressive-answer" data-progressive-stage="quick"><header><div><p class="eyebrow">Quick view ready</p><h3>Package evidence is ready while the deeper roster analysis runs.</h3></div><span class="status-chip">Partial</span></header><p>Canonical ownership and the proposed changed state are valid. These package economics come from the existing governed Value/Trade economics path; they are not a final trade recommendation.</p><div class="fsffl-progressive-sides">${sideCards||'<p>Package Value evidence is currently unavailable.</p>'}</div><div class="fsffl-progressive-next"><strong>Still calculating</strong><span>Roster and lineup consequences → full 50,000-run season simulation</span></div></section>`;
  }

  function appendProgress(message,kind='working'){
    const host=document.querySelector('#trade-analysis-empty');if(!host)return;
    let node=host.querySelector('.fsffl-progressive-status');
    if(!node){node=document.createElement('div');node.className='fsffl-progressive-status';host.appendChild(node)}
    node.dataset.kind=kind;node.textContent=message;
  }

  async function runProgressiveTrade(event){
    const button=event.target?.closest?.('#analyze-trade');if(!button||button.disabled)return;
    event.preventDefault();event.stopImmediatePropagation();
    const key=draftKey(),payload=stableDraft();if(!key||!payload)return;
    if(activeTradeKey===key)return;
    const generation=++tradeGeneration;activeTradeKey=key;
    button.disabled=true;button.textContent='Checking trade…';
    if(typeof window.invalidateTradeScenario==='function')window.invalidateTradeScenario();
    const host=document.querySelector('#trade-analysis-empty');if(host)host.innerHTML='<div class="fsffl-progressive-loading"><p class="eyebrow">Checking this trade</p><h3>Building the quick governed view…</h3></div>';
    try{
      const quick=await window.api('/api/trade-center/quick',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      renderQuickTrade(quick);
      button.textContent='Full roster analysis running…';

      const analysis=await window.api('/api/trade-center/analyze',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      window.renderTradeAnalysis?.(analysis);
      ['#simulate-trade','#explore-price'].forEach(selector=>{const action=document.querySelector(selector);if(action)action.disabled=false});
      appendProgress('Roster analysis ready. Full 50,000-run season simulation running…');
      button.textContent='Full simulation running…';

      const simulation=await window.api('/api/trade-center/simulate',{method:'POST',body:JSON.stringify(payload)});
      if(!currentTrade(generation,key))return;
      window.renderTradeSimulationResult?.(simulation);
      appendProgress(simulation.scenario_cache_hit?'Full analysis ready · exact prior simulation reused.':'Full analysis ready · 50,000-run simulation complete.','ready');
    }catch(error){
      if(!currentTrade(generation,key))return;
      if(document.querySelector('.fsffl-progressive-answer'))appendProgress(`Deeper analysis could not finish: ${error.message}. The quick package evidence above remains valid for its stated scope.`,'error');
      else if(host)host.innerHTML=`<div class="chart-empty"><p>Trade analysis is unavailable: ${esc(error.message)}</p></div>`;
    }finally{
      if(generation===tradeGeneration){activeTradeKey=null;button.textContent='Analyze Trade';if(typeof window.updateAnalyzeTradeState==='function')window.updateAnalyzeTradeState()}
    }
  }

  function installTrade(){window.addEventListener('click',runProgressiveTrade,true)}

  function installMarketWrapper(){
    if(marketInstalled||typeof window.loadOpportunityWorkspace!=='function'||typeof window.oppContextSnapshot!=='function')return;
    marketInstalled=true;
    const progressive=async function({showLoading=true}={}){
      const store=window.fsfflOpportunityState;if(!store||store.loading)return;
      const captured=window.oppContextSnapshot(),requestId=++store.requestSequence;
      store.loading=true;window.oppCancelRetry?.();if(showLoading)window.oppLoading?.();
      const contextStillCurrent=()=>requestId===store.requestSequence&&window.oppContextSnapshot().key===captured.key;
      try{
        const sideEvidence=Promise.all([
          window.api('/api/behavioral/profiles').catch(()=>({status:'unavailable',profiles:[]})),
          captured.teamId?window.api('/api/my-team').catch(()=>null):Promise.resolve(null),
        ]);
        const quick=await window.api('/api/opportunities/workspace/quick');
        if(!contextStillCurrent()||!window.oppPayloadMatchesCapturedContext(quick,captured))return;
        const[behavior,team]=await sideEvidence;if(!contextStillCurrent())return;
        store.payload=quick;store.behavior=behavior;store.team=team;store.loading=false;
        window.renderOpportunityWorkspace?.();
        const panel=document.querySelector('#generic-screen .panel');
        panel?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress"><strong>Quick view ready</strong><span>More bilateral trade evidence is loading.</span></div>');

        window.api('/api/opportunities/workspace').then(full=>{
          if(!contextStillCurrent()||!window.oppPayloadMatchesCapturedContext(full,captured))return;
          store.payload=full;window.renderOpportunityWorkspace?.();
          const current=document.querySelector('#generic-screen .panel');
          current?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress ready"><strong>Updated analysis ready</strong><span>Bounded bilateral Decision evidence has been added.</span></div>');
        }).catch(()=>{
          if(!contextStillCurrent())return;
          const current=document.querySelector('#generic-screen .panel');
          current?.insertAdjacentHTML('afterbegin','<div class="fsffl-market-progress"><strong>Quick view remains available</strong><span>Deeper bilateral evidence could not finish.</span></div>');
        });
      }catch(error){if(contextStillCurrent())window.oppError?.(error.message)}finally{if(requestId===store.requestSequence)store.loading=false}
    };
    window.loadOpportunityWorkspace=progressive;window.renderFsfflOpportunities=progressive;
    try{loadOpportunityWorkspace=progressive}catch(_){/* global binding may be read-only in some browsers */}
  }

  function installMarket(){
    const original=window.ensureOpportunitiesScript;
    if(typeof original==='function'&&!original.__fsfflProgressive){
      const wrapped=function(){return original().then(()=>{installMarketWrapper()})};wrapped.__fsfflProgressive=true;
      window.ensureOpportunitiesScript=wrapped;try{ensureOpportunitiesScript=wrapped}catch(_){/* global binding fallback */}
    }
    const timer=setInterval(()=>{installMarketWrapper();if(marketInstalled)clearInterval(timer)},50);
    setTimeout(()=>clearInterval(timer),15000);
  }

  window.addEventListener('fsffl:product-context-updated',()=>{tradeGeneration+=1;activeTradeKey=null});
  installTrade();installMarket();
  window.fsfflProgressiveDelivery={version:VERSION,installMarketWrapper};
})();
