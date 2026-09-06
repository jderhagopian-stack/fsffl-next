let fsfflJobStartInFlight=false;
let fsfflCurrentJobId=null;
let fsfflJobStateId=null;
let fsfflSettledStateId=null;
let fsfflSessionStartedJobId=null;

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

function ensureIntelligenceRefreshButton(){
  const header=document.querySelector('#runtime-status .panel-header');
  if(!header)return null;
  let button=document.querySelector('#refresh-intelligence');
  if(button)return button;
  button=document.createElement('button');
  button.id='refresh-intelligence';
  button.type='button';
  button.className='secondary-button';
  button.textContent='Refresh Intelligence';
  button.hidden=true;
  button.addEventListener('click',manualIntelligenceRefresh);
  header.appendChild(button);
  return button;
}

function reflectRefreshAction(context,{running=false}={}){
  const button=ensureIntelligenceRefreshButton();
  if(!button)return;
  if(!context?.league_id){button.hidden=true;return}
  const ready=intelligencePipelineReady(context);
  button.hidden=ready||running;
  button.disabled=running||fsfflJobStartInFlight;
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
  setTimeout(()=>{
    reflectAuthoritativeValueReadiness(context);
    reflectRefreshAction(context,{running:Boolean(fsfflCurrentJobId)});
  },0);
}

async function settleCompletedJob(){
  const context=await api('/api/product-context');
  state.context=context;
  state.intelligence=null;
  fsfflCurrentJobId=null;
  fsfflJobStateId=null;
  fsfflSessionStartedJobId=null;
  fsfflSettledStateId=context.state_id||null;
  applyContext();
  setTimeout(()=>{
    reflectAuthoritativeValueReadiness(context);
    reflectRefreshAction(context);
  },0);
  if(intelligencePipelineReady(context)){
    setForecastRefreshMessage('Core intelligence is ready.');
  }else if(context.forecast_ready&&context.simulation_ready&&!context.value_ready){
    setForecastRefreshMessage('Forecast and simulation are ready; Value finished without an authoritative estimate set. Refresh Intelligence to retry.');
  }else{
    setForecastRefreshMessage('Core intelligence is incomplete. Use Refresh Intelligence to retry the missing governed evidence.');
  }
}

function settleFailedJob(payload){
  fsfflSettledStateId=state?.context?.state_id||fsfflJobStateId||null;
  fsfflCurrentJobId=null;
  fsfflJobStateId=null;
  fsfflSessionStartedJobId=null;
  setForecastRefreshMessage(phaseMessage(payload));
  reflectRefreshAction(state.context);
}

async function manualIntelligenceRefresh(){
  if(!state?.context?.league_id||fsfflJobStartInFlight)return;
  fsfflSettledStateId=null;
  fsfflCurrentJobId=null;
  fsfflJobStateId=null;
  fsfflSessionStartedJobId=null;
  await maybeStartIntelligenceJob({manual:true});
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
    reflectRefreshAction(state.context,{running:payload.status==='queued'||payload.status==='running'});

    if(payload.status==='completed'){
      await settleCompletedJob();
      return;
    }

    if(payload.status==='failed'){
      console.error('FSFFL intelligence job failed',payload.error);
      settleFailedJob(payload);
      return;
    }
  }catch(error){
    console.error('Unable to poll FSFFL intelligence job',error);
    setForecastRefreshMessage(`Unable to check server job status (${error.message}). Retrying…`);
    reflectRefreshAction(state.context);
  }
}

async function maybeStartIntelligenceJob({manual=false}={}){
  if(fsfflJobStartInFlight||!state?.context?.league_id)return;
  if(intelligencePipelineReady(state.context)){
    reflectRefreshAction(state.context);
    return;
  }

  const stateId=state.context.state_id||'loaded';
  if(!manual&&fsfflSettledStateId&&fsfflSettledStateId===stateId){
    reflectRefreshAction(state.context);
    return;
  }
  if(fsfflCurrentJobId&&fsfflJobStateId===stateId)return;

  fsfflJobStartInFlight=true;
  fsfflSettledStateId=null;
  setForecastRefreshMessage('Starting server-side intelligence refresh…');
  reflectRefreshAction(state.context,{running:true});
  try{
    const payload=await api('/api/intelligence/jobs',{method:'POST'});
    fsfflCurrentJobId=payload.job_id||null;
    fsfflSessionStartedJobId=payload.job_id||null;
    fsfflJobStateId=payload.league_state_id||stateId;
    setForecastRefreshMessage(phaseMessage(payload));
  }catch(error){
    console.error('Unable to start FSFFL intelligence job',error);
    fsfflSettledStateId=stateId;
    setForecastRefreshMessage(`Unable to start intelligence refresh (${error.message}). Use Refresh Intelligence to retry.`);
  }finally{
    fsfflJobStartInFlight=false;
    reflectRefreshAction(state.context,{running:Boolean(fsfflCurrentJobId)});
  }
}

async function maintainFsfflIntelligence(){
  if(!state?.context?.league_id)return;
  reflectAuthoritativeValueReadiness(state.context);
  if(intelligencePipelineReady(state.context)){
    reflectRefreshAction(state.context);
    return;
  }
  if(fsfflSettledStateId&&fsfflSettledStateId===state.context.state_id){
    reflectRefreshAction(state.context);
    return;
  }
  if(fsfflCurrentJobId){
    await pollIntelligenceJob();
    return;
  }

  try{
    const previousContext=state.context;
    const payload=await api('/api/intelligence/jobs/current');
    state.context={...state.context,...payload};
    await refreshVisibleEvidenceIfAdvanced(previousContext,payload);

    if(payload.job_id&&(payload.status==='queued'||payload.status==='running')){
      fsfflCurrentJobId=payload.job_id;
      fsfflJobStateId=payload.league_state_id||null;
      setForecastRefreshMessage(phaseMessage(payload));
      reflectRefreshAction(state.context,{running:true});
      return;
    }

    if(payload.job_id&&payload.status==='completed'){
      if(intelligencePipelineReady(state.context)){
        await settleCompletedJob();
        return;
      }
      if(fsfflSessionStartedJobId===payload.job_id){
        await settleCompletedJob();
        return;
      }
      // A completed job discovered after the current state is already partial must
      // not suppress a fresh enrichment attempt for this browser session.
      fsfflCurrentJobId=null;
      fsfflJobStateId=null;
      await maybeStartIntelligenceJob();
      return;
    }

    if(payload.job_id&&payload.status==='failed'){
      if(fsfflSessionStartedJobId===payload.job_id){
        settleFailedJob(payload);
        return;
      }
      fsfflCurrentJobId=null;
      fsfflJobStateId=null;
      await maybeStartIntelligenceJob();
      return;
    }
  }catch(error){
    console.error('Unable to discover FSFFL intelligence job',error);
  }
  await maybeStartIntelligenceJob();
}

setInterval(maintainFsfflIntelligence,2500);
window.addEventListener('load',()=>{
  ensureIntelligenceRefreshButton();
  maintainFsfflIntelligence();
});
