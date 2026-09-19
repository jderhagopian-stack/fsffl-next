/* Market/session recovery guard.
 * This module does not create Search, Value, Decision or Simulation truth. It only
 * reconciles browser context with the current persisted product context when the
 * Opportunity workspace silently loses a State race, and keeps an explicit league
 * reconnect path available even when a persisted league is already selected.
 */
(function(){
  const CONNECT_VALUE='__fsffl_connect_league__';
  let opportunityPatched=false;
  let reconcileInFlight=false;
  let lastReconcileKey='';

  function contextKey(context){return `${context?.league_id||''}|${context?.team_id||''}|${context?.state_id||''}`}
  function onMarket(){try{return state?.route==='opportunities'}catch(_){return false}}
  function panel(){return document.querySelector('#generic-screen .panel')}
  function loadingPanel(){const node=panel();return Boolean(node&&/Checking current opportunity evidence/i.test(node.textContent||''))}
  function invokeLeagueConnect(){
    if(typeof window.fsfflHostedConnectSleeper==='function'){void window.fsfflHostedConnectSleeper();return}
    if(typeof connectSleeper==='function'){void connectSleeper()}
  }

  function ensureLeagueRecoveryOption(){
    const select=document.querySelector('#league-select');
    if(!select)return;
    if(!select.querySelector(`option[value="${CONNECT_VALUE}"]`)){
      const option=document.createElement('option');
      option.value=CONNECT_VALUE;
      option.textContent=state?.context?.league_id?'Connect / change league…':'Connect league…';
      select.appendChild(option);
    }
  }

  function recoveryMarkup(message){
    return `<div class="market-recovery-actions" data-market-recovery><p>${String(message||'Market is taking longer than expected.').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}</p><div><button type="button" class="secondary-button" data-market-retry>Retry Market</button><button type="button" class="text-button" data-market-reconnect>Connect / change league</button></div></div>`;
  }

  function installRecoveryActions(message){
    if(!onMarket())return;
    const host=panel();if(!host)return;
    let recovery=host.querySelector('[data-market-recovery]');
    if(!recovery){host.insertAdjacentHTML('beforeend',recoveryMarkup(message));recovery=host.querySelector('[data-market-recovery]')}
    recovery?.querySelector('[data-market-retry]')?.addEventListener('click',()=>void reconcileMarketContext(true),{once:true});
    recovery?.querySelector('[data-market-reconnect]')?.addEventListener('click',invokeLeagueConnect,{once:true});
  }

  async function reconcileMarketContext(force=false){
    if(reconcileInFlight)return;
    reconcileInFlight=true;
    try{
      const before=contextKey(state?.context);
      if(!force&&before&&lastReconcileKey===before)return;
      lastReconcileKey=before;
      const current=await api('/api/product-context');
      const after=contextKey(current);
      if(current?.league_id&&current?.team_id&&after!==before){
        state.context=current;
        if(typeof applyContext==='function')applyContext();
        return;
      }
      if(!current?.league_id){
        installRecoveryActions('No current league session is available. Reconnect a Sleeper league to continue.');
        return;
      }
      if(!current?.team_id){
        installRecoveryActions('Your league is available, but FSFFL needs a managed team before Market can run.');
        return;
      }
      if(typeof loadOpportunityWorkspace==='function'){
        await loadOpportunityWorkspace({showLoading:false});
      }
      if(loadingPanel())installRecoveryActions('Market could not reconcile the current league snapshot automatically. Retry, or reconnect/change the league.');
    }catch(error){
      installRecoveryActions(`Market recovery could not complete: ${error?.message||error}`);
    }finally{
      reconcileInFlight=false;
    }
  }

  function patchOpportunityModule(){
    if(opportunityPatched||typeof loadOpportunityWorkspace!=='function'||typeof oppLoading!=='function')return;
    opportunityPatched=true;
    const originalLoading=oppLoading;
    oppLoading=function(){
      originalLoading();
      installRecoveryActions('FSFFL is checking the saved league and current evidence. If this does not resolve, retry or reconnect the league.');
    };
    const originalLoad=loadOpportunityWorkspace;
    const guarded=async function(options={}){
      const watchdog=setTimeout(()=>{if(onMarket()&&loadingPanel())installRecoveryActions('Market is still waiting on the current league snapshot. You can retry without losing the saved league, or reconnect it.')},12000);
      try{
        const result=await originalLoad(options);
        const hasPayload=typeof fsfflOpportunityState!=='undefined'&&Boolean(fsfflOpportunityState.payload);
        const stillLoading=typeof fsfflOpportunityState!=='undefined'&&Boolean(fsfflOpportunityState.loading);
        if(onMarket()&&!hasPayload&&!stillLoading&&loadingPanel())setTimeout(()=>void reconcileMarketContext(false),0);
        return result;
      }finally{clearTimeout(watchdog)}
    };
    loadOpportunityWorkspace=guarded;
    window.renderFsfflOpportunities=guarded;
  }

  function installOpportunityHook(){
    if(typeof ensureOpportunitiesScript==='function'&&!ensureOpportunitiesScript.fsfflRecoveryWrapped){
      const originalEnsure=ensureOpportunitiesScript;
      const wrapped=function(){return originalEnsure.apply(this,arguments).then(result=>{patchOpportunityModule();return result})};
      wrapped.fsfflRecoveryWrapped=true;
      ensureOpportunitiesScript=wrapped;
    }
    patchOpportunityModule();
  }

  function installSelectorHook(){
    if(typeof populateSelectors==='function'&&!populateSelectors.fsfflRecoveryWrapped){
      const original=populateSelectors;
      const wrapped=function(){const result=original.apply(this,arguments);ensureLeagueRecoveryOption();return result};
      wrapped.fsfflRecoveryWrapped=true;
      populateSelectors=wrapped;
    }
    ensureLeagueRecoveryOption();
  }

  document.addEventListener('change',event=>{
    const select=event.target?.closest?.('#league-select');
    if(!select||select.value!==CONNECT_VALUE)return;
    select.value=state?.context?.league_id||'';
    invokeLeagueConnect();
  },true);
  window.addEventListener('fsffl:product-context-updated',()=>{ensureLeagueRecoveryOption();if(onMarket())setTimeout(()=>{installOpportunityHook();if(loadingPanel())void reconcileMarketContext(false)},0)});
  document.addEventListener('click',event=>{if(event.target?.closest?.('[data-route="opportunities"],[data-direct-route="opportunities"]'))setTimeout(()=>{installOpportunityHook();if(loadingPanel())void reconcileMarketContext(false)},0)},true);

  const style=document.createElement('style');
  style.textContent='.market-recovery-actions{margin-top:18px;padding-top:14px;border-top:1px solid rgba(137,171,205,.14);display:grid;gap:10px}.market-recovery-actions p{margin:0;color:var(--muted);font-size:12px;line-height:1.45}.market-recovery-actions>div{display:flex;gap:10px;align-items:center;flex-wrap:wrap}@media(max-width:720px){.market-recovery-actions>div{align-items:stretch;flex-direction:column}.market-recovery-actions button{width:100%}}';
  document.head.appendChild(style);
  window.fsfflReconnectLeague=invokeLeagueConnect;
  window.fsfflRecoverMarket=()=>reconcileMarketContext(true);

  installSelectorHook();
  installOpportunityHook();
  window.addEventListener('load',()=>{installSelectorHook();installOpportunityHook();ensureLeagueRecoveryOption()},{once:true});
})();
