let fsfflJobStartInFlight=false;
let fsfflCurrentJobId=null;
let fsfflJobStateId=null;

function setForecastRefreshMessage(message){
  const summary=document.querySelector('#runtime-status-summary');
  if(summary)summary.textContent=message;
}

function phaseMessage(payload){
  if(payload?.error)return `Intelligence refresh failed: ${payload.error}`;
  if(payload?.message)return payload.message;
  return 'Checking intelligence refresh status…';
}

function intelligencePipelineReady(context){
  return Boolean(context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);
}

async function refreshVisibleEvidenceIfAdvanced(previousContext,payload){
  const advanced=(
    (!previousContext?.forecast_ready&&payload.forecast_ready)||
    (!previousContext?.simulation_ready&&payload.simulation_ready)||
    (!previousContext?.value_ready&&payload.value_ready)
  );
  if(!advanced)return;

  const context=await api('/api/product-context');
  state.context=context;
  state.intelligence=null;
  applyContext();
}

async function pollIntelligenceJob(){
  if(!state?.context?.league_id)return;
  try{
    const previousContext=state.context;
    const payload=await api('/api/intelligence/jobs/current');
    state.context={...state.context,...payload};
    fsfflCurrentJobId=payload.job_id||null;
    fsfflJobStateId=payload.league_state_id||null;

    await refreshVisibleEvidenceIfAdvanced(previousContext,payload);
    setForecastRefreshMessage(phaseMessage(payload));

    if(payload.status==='completed'){
      const context=await api('/api/product-context');
      state.context=context;
      state.intelligence=null;
      applyContext();
      setForecastRefreshMessage('Forecasts, 50,000-run simulation, and NEXT-3 market values are ready.');
      return;
    }

    if(payload.status==='failed'){
      console.error('FSFFL intelligence job failed',payload.error);
      return;
    }

    if(payload.status==='queued'||payload.status==='running')return;

    await maybeStartIntelligenceJob();
  }catch(error){
    console.error('Unable to poll FSFFL intelligence job',error);
    setForecastRefreshMessage(`Unable to check server job status (${error.message}). Retrying…`);
  }
}

async function maybeStartIntelligenceJob(){
  if(fsfflJobStartInFlight||!state?.context?.league_id)return;
  if(intelligencePipelineReady(state.context))return;

  const stateId=state.context.state_id||'loaded';
  if(fsfflCurrentJobId&&fsfflJobStateId===stateId)return;

  fsfflJobStartInFlight=true;
  setForecastRefreshMessage('Starting server-side intelligence refresh…');
  try{
    const payload=await api('/api/intelligence/jobs',{method:'POST'});
    fsfflCurrentJobId=payload.job_id||null;
    fsfflJobStateId=payload.league_state_id||stateId;
    setForecastRefreshMessage(phaseMessage(payload));
  }catch(error){
    console.error('Unable to start FSFFL intelligence job',error);
    setForecastRefreshMessage(`Unable to start intelligence refresh (${error.message}). Retrying…`);
  }finally{
    fsfflJobStartInFlight=false;
  }
}

async function maintainFsfflIntelligence(){
  if(!state?.context?.league_id)return;
  if(intelligencePipelineReady(state.context))return;
  if(fsfflCurrentJobId){
    await pollIntelligenceJob();
    return;
  }
  try{
    const previousContext=state.context;
    const payload=await api('/api/intelligence/jobs/current');
    state.context={...state.context,...payload};
    if(payload.job_id){
      fsfflCurrentJobId=payload.job_id;
      fsfflJobStateId=payload.league_state_id||null;
      await refreshVisibleEvidenceIfAdvanced(previousContext,payload);
      setForecastRefreshMessage(phaseMessage(payload));
      if(payload.status==='completed'){
        const context=await api('/api/product-context');
        state.context=context;
        state.intelligence=null;
        applyContext();
      }
      return;
    }
  }catch(error){
    console.error('Unable to discover FSFFL intelligence job',error);
  }
  await maybeStartIntelligenceJob();
}

setInterval(maintainFsfflIntelligence,2500);
window.addEventListener('load',maintainFsfflIntelligence);
