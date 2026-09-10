// Safari resume-specific recovery remains disabled while the base page is stabilized.
// This module owns the hosted mobile-safe Sleeper session flow. Stored league state
// is restored first; provider revalidation runs afterward without blocking navigation.
window.fsfflMobileSafariRecoveryDisabled=true;

(function(){
  const LEAGUE_KEY='fsffl:last-sleeper-league';
  const TEAM_KEY='fsffl:last-team';
  let interactiveConnectInFlight=false;
  let restoreInFlight=false;
  let activeLeagueId=null;
  let activeOperation=null;
  let activeConnectPromise=null;

  const now=()=>window.performance?.now?.()??Date.now();
  const recordLatency=(operation,started,outcome='success',detail=null)=>{
    const elapsed=Math.max(0,now()-started);
    fetch('/api/performance/latency',{
      method:'POST',
      headers:{'Accept':'application/json','Content-Type':'application/json'},
      body:JSON.stringify({operation,elapsed_ms:elapsed,outcome,detail}),
      keepalive:true,
    }).catch(()=>{});
  };
  const loadLatencyObserver=()=>{
    if(document.querySelector('script[data-fsffl-phase1-latency]'))return;
    const script=document.createElement('script');
    script.src='/static/phase1_latency.js?v=20260909-phase1-latency1';
    script.defer=true;
    script.dataset.fsfflPhase1Latency='true';
    document.head.appendChild(script);
  };
  loadLatencyObserver();

  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const isTransportError=error=>/Load failed|Failed to fetch|Network request failed|network error/i.test(String(error?.message||''));
  const contextMatchesLeague=(context,leagueId)=>context?.league_id===`sleeper:${leagueId}`;

  async function resilientApi(path,options={},attempts=2){
    let lastError=null;
    for(let attempt=0;attempt<attempts;attempt+=1){
      try{return await api(path,options)}catch(error){
        lastError=error;
        if(!isTransportError(error)||attempt===attempts-1)throw error;
        await sleep(400*(attempt+1));
      }
    }
    throw lastError||new Error('Request failed');
  }

  async function recoverCurrentJob(leagueId,operation){
    try{
      const current=await resilientApi('/api/connect/sleeper/background/current',{},2);
      if(
        current?.league_external_id===leagueId&&
        ['queued','running','completed'].includes(current.status)&&
        (!operation||!current.operation||current.operation===operation)
      )return current;
    }catch(error){
      if(!isTransportError(error))throw error;
    }
    return null;
  }

  async function startBackgroundImport(leagueId,operation='connect'){
    const existing=await recoverCurrentJob(leagueId,operation);
    if(existing&&['queued','running'].includes(existing.status))return existing;
    const endpoint=operation==='refresh'
      ?'/api/connect/sleeper/background/refresh'
      :'/api/connect/sleeper/background';
    try{
      return await resilientApi(endpoint,{
        method:'POST',
        body:JSON.stringify({league_external_id:leagueId}),
      },2);
    }catch(error){
      if(!isTransportError(error))throw error;
      const recovered=await recoverCurrentJob(leagueId,operation);
      if(recovered)return recovered;
      throw error;
    }
  }

  async function performBackgroundImport(leagueId,onProgress,operation='connect'){
    let job=await startBackgroundImport(leagueId,operation);
    const deadline=Date.now()+120000;
    let consecutiveTransportFailures=0;
    while(Date.now()<deadline){
      onProgress?.(job);
      if(job?.status==='completed')return resilientApi('/api/product-context',{},3);
      if(job?.status==='failed')throw new Error(job.error||'Sleeper league import failed');
      await sleep(document.visibilityState==='hidden'?1200:550);
      try{
        job=await api('/api/connect/sleeper/background/current');
        consecutiveTransportFailures=0;
      }catch(error){
        if(!isTransportError(error))throw error;
        consecutiveTransportFailures+=1;
        if(consecutiveTransportFailures>=8)throw new Error('Connection to the server was interrupted. Please try again.');
      }
    }
    throw new Error('League import is taking longer than expected. Please try again in a moment.');
  }

  function waitForBackgroundImport(leagueId,onProgress,operation='connect'){
    if(
      activeConnectPromise&&
      activeLeagueId===leagueId&&
      activeOperation===operation
    )return activeConnectPromise;
    const run=performBackgroundImport(leagueId,onProgress,operation);
    activeLeagueId=leagueId;
    activeOperation=operation;
    activeConnectPromise=run;
    run.finally(()=>{
      if(activeConnectPromise===run){
        activeConnectPromise=null;
        activeLeagueId=null;
        activeOperation=null;
      }
    }).catch(()=>{});
    return run;
  }

  function applyConnectedContext(context){
    state.context=context;
    state.teamView=null;
    state.valueCatalog=null;
    state.intelligence=null;
    applyContext();
  }

  async function restoreSelectedTeam(context){
    const teamId=localStorage.getItem(TEAM_KEY);
    if(teamId&&(context.teams||[]).some(team=>team.team_id===teamId)&&context.team_id!==teamId){
      return resilientApi('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})},2);
    }
    return context;
  }

  async function refreshStoredLeague(leagueId,baselineStateId){
    try{
      const refreshed=await waitForBackgroundImport(leagueId,null,'refresh');
      if(refreshed?.state_id&&refreshed.state_id!==baselineStateId){
        const selected=await restoreSelectedTeam(refreshed);
        applyConnectedContext(selected);
      }
    }catch(error){
      // Stored state remains usable. Revalidation failure should not evict the user
      // from an already-restored league session.
      console.warn('FSFFL background league refresh failed; using stored state',error);
    }
  }

  async function restoreSavedSession(){
    if(restoreInFlight)return false;
    const leagueId=localStorage.getItem(LEAGUE_KEY);
    if(!leagueId)return false;
    const started=now();
    restoreInFlight=true;
    try{
      // Stale-while-revalidate: let the durable runtime restore itself and render
      // immediately before any provider acquisition begins.
      let context=await resilientApi('/api/product-context',{},3);
      if(contextMatchesLeague(context,leagueId)&&context.state_id){
        context=await restoreSelectedTeam(context);
        applyConnectedContext(context);
        if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
        recordLatency('restore_ready',started,'success','durable_restore');
        void refreshStoredLeague(leagueId,context.state_id);
        return true;
      }

      // First connection (or a missing durable snapshot) still uses the governed
      // server-owned import path and waits only because no usable league exists yet.
      context=await waitForBackgroundImport(leagueId,null,'connect');
      context=await restoreSelectedTeam(context);
      applyConnectedContext(context);
      if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
      recordLatency('restore_ready',started,'success','provider_fallback');
      return true;
    }catch(error){
      recordLatency('restore_ready',started,'failed',String(error?.message||error));
      console.error('Unable to restore previous FSFFL session',error);
      return false;
    }finally{
      restoreInFlight=false;
    }
  }

  async function interactiveConnect(){
    if(interactiveConnectInFlight)return;
    const leagueId=window.prompt('Enter your Sleeper league ID');
    if(!leagueId?.trim())return;
    const normalized=leagueId.trim();
    const started=now();
    localStorage.setItem(LEAGUE_KEY,normalized);
    interactiveConnectInFlight=true;
    const button=document.querySelector('#connect-button');
    const original=button?.textContent||'Connect Sleeper League';
    if(button){button.disabled=true;button.textContent='Starting import…'}
    try{
      const context=await waitForBackgroundImport(normalized,job=>{
        if(button)button.textContent=job?.status==='running'?'Loading league…':'Starting import…';
      },'connect');
      applyConnectedContext(context);
      recordLatency('first_connect_ready',started,'success');
    }catch(error){
      recordLatency('first_connect_ready',started,'failed',String(error?.message||error));
      window.alert(`Could not connect league: ${error.message}`);
    }finally{
      interactiveConnectInFlight=false;
      if(button){button.disabled=false;button.textContent=original}
    }
  }

  window.fsfflRestoreSession=restoreSavedSession;
  window.fsfflHostedConnectSleeper=interactiveConnect;

  document.addEventListener('click',event=>{
    const button=event.target?.closest?.('#connect-button');
    if(!button)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    void interactiveConnect();
  },true);
})();
