let fsfflJobStartInFlight=false;
let fsfflCurrentJobId=null;
let fsfflJobStateId=null;
let fsfflSettledStateId=null;

function setForecastRefreshMessage(message){
  const title=document.querySelector('#runtime-status-title');
  if(title)title.textContent=message;
}

function phaseMessage(payload){
  if(payload?.error)return `Intelligence refresh failed: ${payload.error}`;
  if(payload?.message)return payload.message;
  return 'Checking intelligence refresh status…';
}

function intelligencePipelineReady(context){
  return Boolean(context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);
}

function reflectAuthoritativeValueReadiness(context){
  if(!context?.value_ready)return;
  document.querySelectorAll('#runtime-stage-grid .runtime-stage').forEach(node=>{
    const label=node.querySelector('strong')?.textContent?.trim().toLowerCase();
    if(label!=='value')return;
    node.classList.remove('pending','blocked','unavailable','waiting_for_input','not_configured');
    node.classList.add('ready');
    const mark=node.querySelector('.runtime-stage-mark');
    if(mark)mark.textContent='✓';
    const detail=node.querySelector('small');
    if(detail){
      const coverage=typeof context.value_coverage==='number'?` (${(context.value_coverage*100).toFixed(1)}% roster coverage)`:'';
      detail.textContent=`Governed NEXT-3 current market values are attached${coverage}.`;
    }
  });
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
  setTimeout(()=>reflectAuthoritativeValueReadiness(context),0);
}

async function settleCompletedJob(){
  const context=await api('/api/product-context');
  state.context=context;
  state.intelligence=null;
  fsfflSettledStateId=context.state_id||null;
  fsfflCurrentJobId=null;
  fsfflJobStateId=null;
  applyContext();
  setTimeout(()=>reflectAuthoritativeValueReadiness(context),0);
  if(context.value_ready){
    setForecastRefreshMessage('Intelligence refresh complete.');
  }else{
    setForecastRefreshMessage('Forecast and simulation are ready; Value finished without an authoritative estimate set.');
  }
}

function settleFailedJob(payload){
  fsfflSettledStateId=state?.context?.state_id||fsfflJobStateId||null;
  fsfflCurrentJobId=null;
  fsfflJobStateId=null;
  setForecastRefreshMessage(phaseMessage(payload));
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
    reflectAuthoritativeValueReadiness(state.context);

    if(payload.status==='completed'){
      await settleCompletedJob();
      return;
    }

    if(payload.status==='failed'){
      console.error('FSFFL intelligence job failed',payload.error);
      settleFailedJob(payload);
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
  if(fsfflSettledStateId&&fsfflSettledStateId===stateId)return;
  if(fsfflCurrentJobId&&fsfflJobStateId===stateId)return;

  fsfflJobStartInFlight=true;
  fsfflSettledStateId=null;
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
  reflectAuthoritativeValueReadiness(state.context);
  if(intelligencePipelineReady(state.context))return;
  if(fsfflSettledStateId&&fsfflSettledStateId===state.context.state_id)return;
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
      reflectAuthoritativeValueReadiness(state.context);
      if(payload.status==='completed'){
        await settleCompletedJob();
      }else if(payload.status==='failed'){
        settleFailedJob(payload);
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
