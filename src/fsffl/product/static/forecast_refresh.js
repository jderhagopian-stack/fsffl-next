let fsfflForecastRefreshInFlight=false;
let fsfflForecastAttemptedState=null;
let fsfflForecastRetryAt=0;
let fsfflSimulationPollUntil=0;
let fsfflLastSimulationReady=null;

function setForecastRefreshMessage(message){
  const summary=document.querySelector('#runtime-status-summary');
  if(summary)summary.textContent=message;
}

function reconcileSimulationRuntimeState(){
  // The private beta store is intentionally in-memory. A Render/runtime restart
  // can therefore make server-side simulation evidence disappear while an open
  // browser still remembers that the same immutable LeagueState already finished.
  // In that exact transition, clear only the client retry bookkeeping so the
  // authoritative server workflow can be started again. This does not weaken the
  // server's state-id guard and does not create a second model authority.
  const simulationReady=Boolean(state?.context?.simulation_ready);
  if(fsfflLastSimulationReady===true&&!simulationReady){
    fsfflForecastAttemptedState=null;
    fsfflForecastRetryAt=0;
    fsfflSimulationPollUntil=0;
  }
  fsfflLastSimulationReady=simulationReady;
}

async function pollExistingSimulation(){
  if(!state?.context?.league_id||Date.now()>fsfflSimulationPollUntil)return false;
  try{
    const payload=await api('/api/product-context');
    state.context=payload;
    state.intelligence=null;
    applyContext();
    reconcileSimulationRuntimeState();
    if(payload.simulation_ready){
      fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
      fsfflSimulationPollUntil=0;
      setForecastRefreshMessage('FSFFL simulation ready.');
      return true;
    }
    if(payload.forecast_ready){
      setForecastRefreshMessage('Forecasts ready. 50,000-run simulation is still finishing on the server…');
      return false;
    }
  }catch(error){
    console.error('Unable to poll FSFFL simulation status',error);
  }
  return false;
}

async function maybeRefreshFsfflForecasts(){
  // Forecast evidence is league-wide. Managed-team selection is intentionally
  // not a prerequisite; team choice only scopes downstream team/product views.
  // Mobile browsers can drop a long-running HTTP request before the 50,000-run
  // simulation finishes. After such an interruption, poll the existing server
  // work instead of launching a second state/forecast refresh that could make the
  // first simulation stale against a newer immutable LeagueState.
  if(fsfflForecastRefreshInFlight||!state?.context?.league_id)return;
  reconcileSimulationRuntimeState();
  if(state.context.forecast_ready&&state.context.simulation_ready)return;

  if(fsfflSimulationPollUntil>Date.now()){
    await pollExistingSimulation();
    return;
  }

  const stateId=state.context.state_id||'loaded';
  const now=Date.now();
  if(fsfflForecastAttemptedState===stateId&&now<fsfflForecastRetryAt)return;
  fsfflForecastAttemptedState=stateId;
  fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
  fsfflForecastRefreshInFlight=true;
  setForecastRefreshMessage(
    state.context.forecast_ready
      ? 'Forecasts ready. Building 50,000-run FSFFL simulation…'
      : 'Building FSFFL multi-source projections…'
  );
  try{
    const payload=await api('/api/intelligence/refresh-forecasts',{method:'POST'});
    state.context=payload;
    state.intelligence=null;
    applyContext();
    reconcileSimulationRuntimeState();
    if(payload.simulation_ready){
      fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
      fsfflSimulationPollUntil=0;
    }else{
      fsfflSimulationPollUntil=Date.now()+180000;
      fsfflForecastRetryAt=fsfflSimulationPollUntil;
      setForecastRefreshMessage('Forecasts ready. 50,000-run simulation is finishing on the server…');
    }
  }catch(error){
    console.error('Unable to refresh FSFFL forecasts',error);
    // A mobile/network timeout does not prove the server-side simulation failed.
    // Give the original request up to three minutes to finish and attach before
    // permitting another full refresh against a newer canonical state.
    fsfflSimulationPollUntil=Date.now()+180000;
    fsfflForecastRetryAt=fsfflSimulationPollUntil;
    setForecastRefreshMessage(`Connection interrupted (${error.message}). Checking the existing simulation instead of restarting it…`);
  }finally{
    fsfflForecastRefreshInFlight=false;
  }
}

setInterval(maybeRefreshFsfflForecasts,1500);
window.addEventListener('load',maybeRefreshFsfflForecasts);
