let fsfflForecastRefreshInFlight=false;
let fsfflForecastAttemptedState=null;

function setForecastRefreshMessage(message){
  const summary=document.querySelector('#runtime-status-summary');
  if(summary)summary.textContent=message;
}

async function maybeRefreshFsfflForecasts(){
  if(fsfflForecastRefreshInFlight||!state?.context?.league_id||!state?.context?.team_id)return;
  if(state.context.forecast_ready)return;
  const stateId=state.context.state_id||'loaded';
  if(fsfflForecastAttemptedState===stateId)return;
  fsfflForecastAttemptedState=stateId;
  fsfflForecastRefreshInFlight=true;
  setForecastRefreshMessage('Building FSFFL multi-source projections…');
  try{
    const payload=await api('/api/intelligence/refresh-forecasts',{method:'POST'});
    state.context=payload;
    state.intelligence=null;
    applyContext();
  }catch(error){
    console.error('Unable to refresh FSFFL forecasts',error);
    setForecastRefreshMessage(`Forecast refresh stopped: ${error.message}`);
  }finally{
    fsfflForecastRefreshInFlight=false;
  }
}

setInterval(maybeRefreshFsfflForecasts,1500);
window.addEventListener('load',maybeRefreshFsfflForecasts);
