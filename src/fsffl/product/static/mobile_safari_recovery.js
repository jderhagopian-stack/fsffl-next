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
      if(current?.league_external_id!==leagueId)return null;
      if(['queued','running'].includes(current.status))return current;
      if(current.status==='completed'&&current.operation===operation)return current;
      if(current.status==='failed'&&current.operation===operation)return current;
    }catch(error){
      if(!isTransportError(error))throw error;
    }
    return null;
  }

  async function startBackgroundImport(leagueId,operation='connect',attachOnly=false){
    const existing=await recoverCurrentJob(leagueId,operation);
    if(existing&&(['queued','running'].includes(existing.status)||(attachOnly&&['completed','failed'].includes(existing.status))))return existing;
    if(attachOnly)return null;
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

  async function usableConnectedContext(leagueId){
    try{
      const context=await resilientApi('/api/product-context',{},1);
      return contextMatchesLeague(context,leagueId)&&context?.state_id?context:null;
    }catch(error){
      if(isTransportError(error))return null;
      throw error;
    }
  }

  async function performBackgroundImport(leagueId,onProgress,operation='connect',attachOnly=false){
    let job=await startBackgroundImport(leagueId,operation,attachOnly);
    if(!job&&attachOnly){
      const current=await usableConnectedContext(leagueId);
      if(current)return current;
      throw new Error('The in-progress league refresh is no longer available.');
    }
    const deadline=Date.now()+120000;
    let consecutiveTransportFailures=0;
    let pollDelay=700;
    let nextContextProbeAt=0;
    while(Date.now()<deadline){
      onProgress?.(job);

      // Connect becomes usable as soon as canonical State is active in memory. The
      // server may still be checkpointing that State or starting enrichment, but
      // neither durable persistence nor intelligence publication belongs on the
      // first-load navigation barrier.
      if(operation==='connect'&&Date.now()>=nextContextProbeAt){
        nextContextProbeAt=Date.now()+500;
        const usable=await usableConnectedContext(leagueId);
        if(usable)return usable;
      }

      if(job?.status==='completed'){
        const context=await resilientApi('/api/product-context',{},3);
        if(operation!=='connect'||(contextMatchesLeague(context,leagueId)&&context?.state_id))return context;
        throw new Error('League import completed without activating the requested Sleeper league.');
      }
      if(job?.status==='failed')throw new Error(job.error||'Sleeper league import failed');

      await sleep(document.visibilityState==='hidden'?Math.max(1500,pollDelay):pollDelay);
      pollDelay=Math.min(2200,Math.round(pollDelay*1.35));
      try{
        const current=await api('/api/connect/sleeper/background/current');
        if(current?.league_external_id&&current.league_external_id!==leagueId){
          throw new Error('Another league connection replaced this request.');
        }
        job=current;
        consecutiveTransportFailures=0;
      }catch(error){
        if(!isTransportError(error))throw error;
        consecutiveTransportFailures+=1;
        if(consecutiveTransportFailures>=8)throw new Error('Connection to the server was interrupted. Please try again.');
      }
    }
    throw new Error('League import is taking longer than expected. Please try again in a moment.');
  }

  function waitForBackgroundImport(leagueId,onProgress,operation='connect',attachOnly=false){
    // The server already treats a same-user/same-league connect or refresh as one
    // single-flight job. Mirror that contract in the browser so startup recovery,
    // manual connect and stale-while-revalidate cannot create competing poll loops.
    if(activeConnectPromise&&activeLeagueId===leagueId)return activeConnectPromise;
    const run=performBackgroundImport(leagueId,onProgress,operation,attachOnly);
    activeLeagueId=leagueId;
    activeConnectPromise=run;
    run.finally(()=>{
      if(activeConnectPromise===run){
        activeConnectPromise=null;
        activeLeagueId=null;
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

  function selectedTeamName(context){
    const selectedId=context?.team_id;
    return (context?.teams||[]).find(team=>team.team_id===selectedId)?.display_name||null;
  }

  async function restoreSelectedTeam(context){
    const teamId=localStorage.getItem(TEAM_KEY);
    if(teamId&&(context.teams||[]).some(team=>team.team_id===teamId)){
      if(context.team_id===teamId)return context;
      return resilientApi('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})},2);
    }
    if(teamId)localStorage.removeItem(TEAM_KEY);
    return context;
  }

  async function refreshStoredLeague(leagueId,baselineStateId,attachOnly=false,operation='refresh'){
    publishSyncState('checking');
    try{
      const refreshed=attachOnly?await waitForBackgroundImport(leagueId,null,operation,true):await waitForBackgroundImport(leagueId,null,'refresh');
      if(refreshed?.state_id&&refreshed.state_id!==baselineStateId){
        const selected=await restoreSelectedTeam(refreshed);
        applyConnectedContext(selected);
      }
      publishSyncState('current');
    }catch(error){
      // Stored state remains usable. Revalidation failure should not evict the user
      // from an already-restored league session.
      publishSyncState('stale','Refresh unavailable. Continuing with the last valid stored league.');
      console.warn('FSFFL background league refresh failed; using stored state',error);
    }
  }

  async function refreshStoredLeagueIfDue(leagueId,baselineStateId,afterConnect=false){
    // Session restore is read-first. The endpoint uses the existing persisted
    // Sleeper sync cursor + cheap provider probe and never starts provider work.
    // If freshness cannot be established, leave the published State untouched;
    // explicit refresh and missing-State connect recovery remain available.
    try{
      const freshness=await resilientApi(
        '/api/connect/sleeper/background/freshness?league_external_id='+encodeURIComponent(leagueId),
        {},
        2,
      );
      if(freshness?.connect_in_progress===true){
        await refreshStoredLeague(leagueId,baselineStateId,true,'connect');
        if(!afterConnect)await refreshStoredLeagueIfDue(leagueId,state?.context?.state_id||baselineStateId,true);
        return;
      }
      if(freshness?.refresh_in_progress===true){
        await refreshStoredLeague(leagueId,baselineStateId,true);
        return;
      }
      let latestStateId=baselineStateId;
      try{
        const latest=await resilientApi('/api/product-context',{},2);
        if(contextMatchesLeague(latest,leagueId)&&latest?.state_id){
          latestStateId=latest.state_id;
          if(latestStateId!==baselineStateId){
            const selected=await restoreSelectedTeam(latest);
            applyConnectedContext(selected);
          }
        }
      }catch(error){
        console.info('FSFFL post-freshness context check unavailable; preserving current State',error);
      }
      if(freshness?.refresh_due===true)void refreshStoredLeague(leagueId,latestStateId);
    }catch(error){
      console.info('FSFFL saved-session freshness check unavailable; preserving current State',error);
    }
  }

  async function restoreSavedSession(){
    if(restoreInFlight)return false;
    const leagueId=localStorage.getItem(LEAGUE_KEY);
    if(!leagueId)return false;
    const started=now();
    restoreInFlight=true;
    try{
      // Stale-while-revalidate is now read-first: restore durable State first. A
      // lightweight governed freshness read may schedule a provider refresh,
      // but ordinary restore itself is not a provider refresh.
      let context=await resilientApi('/api/product-context',{},3);
      if(contextMatchesLeague(context,leagueId)&&context.state_id){
        context=await restoreSelectedTeam(context);
        applyConnectedContext(context);
        window.fsfflEnsureIntelligenceAfterTeamSelection?.();
        if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
        recordLatency('restore_ready',started,'success','durable_restore');
        void refreshStoredLeagueIfDue(leagueId,context.state_id);
        return true;
      }

      // First connection (or a missing durable snapshot) still uses the governed
      // server-owned import path and waits only until canonical league State is usable.
      context=await waitForBackgroundImport(leagueId,null,'connect');
      context=await restoreSelectedTeam(context);
      applyConnectedContext(context);
      window.fsfflEnsureIntelligenceAfterTeamSelection?.();
      if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
      publishSyncState('current');
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
    const activeBefore=(state.context?.league_id||'').replace(/^sleeper:/,'');
    const promptText=activeBefore
      ? 'Enter a different Sleeper league ID. Current league: '+activeBefore
      : 'Enter your Sleeper league ID';
    const leagueId=window.prompt(promptText);
    if(!leagueId?.trim())return;
    const normalized=leagueId.trim();
    const started=now();
    const previousLeagueId=localStorage.getItem(LEAGUE_KEY);
    const previousTeamId=localStorage.getItem(TEAM_KEY);
    interactiveConnectInFlight=true;
    const button=document.querySelector('#connect-button');
    const original=button?.textContent||'Connect Sleeper League';

    // Acknowledgement must happen before any server read. A slow restore/context
    // request must never make a submitted league ID look ignored on mobile Safari.
    if(button){button.disabled=true;button.textContent='Starting import…'}
    publishSyncState('checking','Starting import…');

    try{
      // Manual Connect always owns the idempotent background handoff. Even when
      // this browser already knows the requested league identity, re-applying
      // canonical context is the recovery path for a visually stale Safari shell.

      const context=await waitForBackgroundImport(normalized,job=>{
        const loading=job?.status==='running';
        if(button)button.textContent=loading?'Loading league…':'Starting import…';
        publishSyncState('checking',loading?'Loading league…':'Starting import…');
      },'connect');
      if(!contextMatchesLeague(context,normalized)||!context?.state_id){
        throw new Error('The requested Sleeper league did not become active.');
      }

      // Manual first-connect/switch is an explicit new choice, not session restore.
      // Never silently reuse a browser-local team from another or prior session.
      localStorage.setItem(LEAGUE_KEY,normalized);
      localStorage.removeItem(TEAM_KEY);
      applyConnectedContext(context);
      window.fsfflSharedReadiness?.refresh();
      publishSyncState(
        'current',
        'League is ready. Select the franchise you manage to continue.'
      );
      recordLatency('first_connect_ready',started,'success','requested='+normalized+';active='+String(context.league_id||''));
    }catch(error){
      if(previousLeagueId===null)localStorage.removeItem(LEAGUE_KEY);
      else localStorage.setItem(LEAGUE_KEY,previousLeagueId);
      if(previousTeamId===null)localStorage.removeItem(TEAM_KEY);
      else localStorage.setItem(TEAM_KEY,previousTeamId);
      publishSyncState('stale','League connection failed. '+String(error?.message||error));
      recordLatency('first_connect_ready',started,'failed','requested='+normalized+';'+String(error?.message||error));
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
