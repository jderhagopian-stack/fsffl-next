let fsfflForecastRefreshInFlight=false;
let fsfflForecastAttemptedState=null;
let fsfflForecastRetryAt=0;

function setForecastRefreshMessage(message){
  const summary=document.querySelector('#runtime-status-summary');
  if(summary)summary.textContent=message;
}

async function maybeRefreshFsfflForecasts(){
  if(fsfflForecastRefreshInFlight||!state?.context?.league_id||!state?.context?.team_id)return;
  if(state.context.forecast_ready)return;
  const stateId=state.context.state_id||'loaded';
  const now=Date.now();
  if(fsfflForecastAttemptedState===stateId&&now<fsfflForecastRetryAt)return;
  fsfflForecastAttemptedState=stateId;
  fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
  fsfflForecastRefreshInFlight=true;
  setForecastRefreshMessage('Building FSFFL multi-source projections…');
  try{
    const payload=await api('/api/intelligence/refresh-forecasts',{method:'POST'});
    state.context=payload;
    state.intelligence=null;
    fsfflForecastRetryAt=Number.POSITIVE_INFINITY;
    applyContext();
  }catch(error){
    console.error('Unable to refresh FSFFL forecasts',error);
    fsfflForecastRetryAt=Date.now()+30000;
    setForecastRefreshMessage(`Forecast refresh stopped: ${error.message}. Retrying automatically…`);
  }finally{
    fsfflForecastRefreshInFlight=false;
  }
}

setInterval(maybeRefreshFsfflForecasts,1500);
window.addEventListener('load',maybeRefreshFsfflForecasts);
