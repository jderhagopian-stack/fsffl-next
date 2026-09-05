let fsfflForecastRefreshInFlight=false;
let fsfflForecastAttemptedState=null;
let fsfflForecastRetryAt=0;

function setForecastRefreshMessage(message){
  const summary=document.querySelector('#runtime-status-summary');
  if(summary)summary.textContent=message;
}

async function maybeRefreshFsfflForecasts(){
  // Forecast evidence is league-wide. Managed-team selection is intentionally
  // not a prerequisite; team choice only scopes downstream team/product views.
  // A refresh is not complete until both forecast evidence and simulation are
  // ready. This lets the beta recover after a reload/network interruption that
  // occurs after NEXT-2 is stored but before the 50,000-run NEXT-4 simulation is
  // attached.
  if(fsfflForecastRefreshInFlight||!state?.context?.league_id)return;
  if(state.context.forecast_ready&&state.context.simulation_ready)return;
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
    if(payload.simulation_ready){
      fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
    }else{
      // Forecast evidence may be valid even when a state-generation race makes
      // a simulation result stale. Retry against the current canonical state.
      fsfflForecastRetryAt=Date.now()+5000;
      setForecastRefreshMessage('Forecasts ready. Simulation will retry against the current league state…');
    }
  }catch(error){
    console.error('Unable to refresh FSFFL forecasts',error);
    fsfflForecastRetryAt=Date.now()+30000;
    setForecastRefreshMessage(`Intelligence refresh interrupted: ${error.message}. Retrying automatically…`);
  }finally{
    fsfflForecastRefreshInFlight=false;
  }
}

setInterval(maybeRefreshFsfflForecasts,1500);
window.addEventListener('load',maybeRefreshFsfflForecasts);
