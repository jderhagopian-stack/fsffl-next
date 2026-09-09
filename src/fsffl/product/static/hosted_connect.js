(function(){
  const LEAGUE_KEY='fsffl:last-sleeper-league';
  const TEAM_KEY='fsffl:last-team';
  let interactiveConnectInFlight=false;
  let restoreInFlight=false;

  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const isTransportError=error=>/Load failed|Failed to fetch|Network request failed|network error/i.test(String(error?.message||''));

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

  async function recoverCurrentJob(leagueId){
    try{
      const current=await resilientApi('/api/connect/sleeper/background/current',{},2);
      if(current?.league_external_id===leagueId&&['queued','running','completed'].includes(current.status))return current;
    }catch(error){
      if(!isTransportError(error))throw error;
    }
    return null;
  }

  async function startBackgroundImport(leagueId){
    try{
      return await resilientApi('/api/connect/sleeper/background',{
        method:'POST',
        body:JSON.stringify({league_external_id:leagueId}),
      },2);
    }catch(error){
      if(!isTransportError(error))throw error;
      const recovered=await recoverCurrentJob(leagueId);
      if(recovered)return recovered;
      throw error;
    }
  }

  async function waitForBackgroundImport(leagueId,onProgress){
    let job=await startBackgroundImport(leagueId);
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

  function applyConnectedContext(context){
    state.context=context;
    state.teamView=null;
    state.valueCatalog=null;
    state.intelligence=null;
    applyContext();
  }

  async function restoreSavedSession(){
    if(restoreInFlight)return false;
    const leagueId=localStorage.getItem(LEAGUE_KEY);
    if(!leagueId)return false;
    restoreInFlight=true;
    try{
      let context=await waitForBackgroundImport(leagueId);
      const teamId=localStorage.getItem(TEAM_KEY);
      if(teamId&&(context.teams||[]).some(team=>team.team_id===teamId)){
        context=await resilientApi('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})},2);
      }
      applyConnectedContext(context);
      if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
      return true;
    }catch(error){
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
    localStorage.setItem(LEAGUE_KEY,normalized);
    interactiveConnectInFlight=true;
    const button=document.querySelector('#connect-button');
    const original=button?.textContent||'Connect Sleeper League';
    if(button){button.disabled=true;button.textContent='Starting import…'}
    try{
      const context=await waitForBackgroundImport(normalized,job=>{
        if(button)button.textContent=job?.status==='running'?'Loading league…':'Starting import…';
      });
      applyConnectedContext(context);
    }catch(error){
      window.alert(`Could not connect league: ${error.message}`);
    }finally{
      interactiveConnectInFlight=false;
      if(button){button.disabled=false;button.textContent=original}
    }
  }

  // Replace the synchronous session-recovery path before its startup timer fires.
  window.fsfflRestoreSession=restoreSavedSession;
  window.fsfflHostedConnectSleeper=interactiveConnect;

  // Capture before the legacy target listener so hosted beta never opens the
  // long-lived synchronous /api/connect/sleeper request from mobile Safari.
  document.addEventListener('click',event=>{
    const button=event.target?.closest?.('#connect-button');
    if(!button)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    void interactiveConnect();
  },true);
})();
