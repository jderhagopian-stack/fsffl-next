// Safari resume-specific recovery remains disabled while the base page is stabilized.
// This module owns the hosted mobile-safe Sleeper session flow. Stored league state
// is restored first; provider revalidation runs afterward without blocking navigation.
window.fsfflMobileSafariRecoveryDisabled=true;

(function(){
  const LEAGUE_KEY='fsffl:last-sleeper-league';
  const TEAM_KEY='fsffl:last-team';
  const VISIBLE_POLL_MS=1500;
  const HIDDEN_POLL_MS=2500;
  const IMPORT_DEADLINE_MS=180000;
  let interactiveConnectInFlight=false;
  let restorePromise=null;
  let activeTask=null;

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
  const loadHelper=(selector,src,datasetKey)=>{
    if(document.querySelector(selector))return;
    const script=document.createElement('script');
    script.src=src;
    script.defer=true;
    script.dataset[datasetKey]='true';
    document.head.appendChild(script);
  };
  loadHelper('script[data-fsffl-phase1-latency]','/static/phase1_latency.js?v=20260909-phase1-latency1','fsfflPhase1Latency');
  loadHelper('script[data-fsffl-sync-state]','/static/phase1_sync_state.js?v=20260909-phase1-sync1','fsfflSyncState');
  const publishSyncState=(syncState,message=null)=>{
    const detail={state:syncState,message};
    window.fsfflPendingSyncState=detail;
    if(window.fsfflSyncState?.set)window.fsfflSyncState.set(syncState,message);
    window.dispatchEvent(new CustomEvent('fsffl:sync-state',{detail}));
  };

  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const isTransportError=error=>/Load failed|Failed to fetch|Network request failed|network error/i.test(String(error?.message||''));
  const contextMatchesLeague=(context,leagueId)=>context?.league_id===`sleeper:${leagueId}`;
  const usableContext=(context,leagueId)=>contextMatchesLeague(context,leagueId)&&Boolean(context?.state_id);

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
    // A connect request is unnecessary once canonical persisted state is already usable.
    // Returning it immediately prevents a restore fallback from attaching itself to a
    // secondary refresh job that may still be hydrating intelligence.
    if(operation==='connect'){
      try{
        const context=await resilientApi('/api/product-context',{},2);
        if(usableContext(context,leagueId))return {status:'completed',operation:'connect',league_external_id:leagueId};
      }catch(_){}
    }
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
    const deadline=Date.now()+IMPORT_DEADLINE_MS;
    let consecutiveTransportFailures=0;
    while(Date.now()<deadline){
      onProgress?.(job);
      if(job?.status==='completed')return resilientApi('/api/product-context',{},3);
      if(job?.status==='failed')throw new Error(job.error||'Sleeper league import failed');
      await sleep(document.visibilityState==='hidden'?HIDDEN_POLL_MS:VISIBLE_POLL_MS);
      try{
        job=await api('/api/connect/sleeper/background/current');
        consecutiveTransportFailures=0;
        if(job?.league_external_id&&job.league_external_id!==leagueId){
          throw new Error('Another league import replaced this job. Please try again.');
        }
        if(job?.operation&&job.operation!==operation){
          // Never treat a refresh as completion of connect (or vice versa). The old
          // flow could bind a connect waiter to a long-running refresh and eventually
          // show the 120-second blocking failure despite usable canonical state.
          throw new Error('Another league update is already in progress.');
        }
      }catch(error){
        if(!isTransportError(error))throw error;
        consecutiveTransportFailures+=1;
        if(consecutiveTransportFailures>=8)throw new Error('Connection to the server was interrupted. Please try again.');
      }
    }
    throw new Error('League import is still running. Your saved league will remain available while FSFFL finishes syncing.');
  }

  async function waitForBackgroundImport(leagueId,onProgress,operation='connect'){
    if(activeTask){
      if(activeTask.leagueId===leagueId&&activeTask.operation===operation)return activeTask.promise;
      // Serialize hosted work in this browser. Different operations are not allowed
      // to create competing poll loops or race the single server-side current-job slot.
      try{await activeTask.promise}catch(_){}
      if(operation==='connect'){
        try{
          const context=await resilientApi('/api/product-context',{},2);
          if(usableContext(context,leagueId))return context;
        }catch(_){}
      }
    }
    const run=performBackgroundImport(leagueId,onProgress,operation);
    const task={leagueId,operation,promise:run};
    activeTask=task;
    run.finally(()=>{if(activeTask===task)activeTask=null}).catch(()=>{});
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
    publishSyncState('checking');
    try{
      const refreshed=await waitForBackgroundImport(leagueId,null,'refresh');
      if(refreshed?.state_id&&refreshed.state_id!==baselineStateId){
        const selected=await restoreSelectedTeam(refreshed);
        applyConnectedContext(selected);
      }
      publishSyncState('current');
    }catch(error){
      // Values and behavioral intelligence are secondary to canonical league state.
      // Revalidation failure must never evict a usable restored session.
      publishSyncState('stale','Refresh unavailable. Continuing with the last valid stored league.');
      console.warn('FSFFL background league refresh failed; using stored state',error);
    }
  }

  async function doRestoreSavedSession(){
    const leagueId=localStorage.getItem(LEAGUE_KEY);
    if(!leagueId)return false;
    const started=now();
    try{
      // Stale-while-revalidate: render durable canonical state before provider work.
      let context=await resilientApi('/api/product-context',{},3);
      if(usableContext(context,leagueId)){
        context=await restoreSelectedTeam(context);
        applyConnectedContext(context);
        if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
        recordLatency('restore_ready',started,'success','durable_restore');
        void refreshStoredLeague(leagueId,context.state_id);
        return true;
      }

      // First connection (or missing durable snapshot) waits because there is no
      // canonical league state to present yet.
      context=await waitForBackgroundImport(leagueId,null,'connect');
      context=await restoreSelectedTeam(context);
      applyConnectedContext(context);
      if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
      publishSyncState('current');
      recordLatency('restore_ready',started,'success','provider_fallback');
      return true;
    }catch(error){
      recordLatency('restore_ready',started,'failed',String(error?.message||error));
      console.error('Unable to restore previous FSFFL session',error);
      return false;
    }
  }

  function restoreSavedSession(){
    // All callers join the same restore promise. This is important on iOS/Safari,
    // where load/resume/API recovery hooks can fire nearly together.
    if(restorePromise)return restorePromise;
    const run=doRestoreSavedSession();
    restorePromise=run;
    run.finally(()=>{if(restorePromise===run)restorePromise=null}).catch(()=>{});
    return run;
  }

  async function interactiveConnect(){
    if(interactiveConnectInFlight)return;
    if(restorePromise){
      const restored=await restorePromise.catch(()=>false);
      if(restored)return;
    }
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
      publishSyncState('current');
      recordLatency('first_connect_ready',started,'success');
    }catch(error){
      // One last canonical-state check prevents a secondary background failure from
      // becoming a blocking league-connect error after the league is already usable.
      try{
        const context=await resilientApi('/api/product-context',{},2);
        if(usableContext(context,normalized)){
          applyConnectedContext(await restoreSelectedTeam(context));
          publishSyncState('stale','League loaded. Some background data is still refreshing.');
          recordLatency('first_connect_ready',started,'success','canonical_state_recovered');
          return;
        }
      }catch(_){}
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
