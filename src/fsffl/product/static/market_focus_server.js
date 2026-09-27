/* Server-owned Market Focus submission lifecycle.
 * Controls configure a request; only explicit submit launches focused Search.
 * State, Value, Decision and acceptance semantics remain unchanged.
 */
(function(){
  let requestSeq=0,queued=false,busy=false,dirty=false,error="",submitted=null,completed=null,enrichmentTimer=null,enrichmentJobId=null;

  function stateRef(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function selected(){
    const posture=window.fsfflOpportunityPosture?.selectedPosture?.()||'default_calculated';
    const intent=window.fsfflMarketIntent?.selected?.()||{intent:'',value:''};
    return{posture,intent:intent.intent||'',value:intent.value||''};
  }
  const keyOf=value=>[value?.posture||'',value?.intent||'',value?.value||''].join('|');
  const requiresValue=value=>["position","shop","target","owner"].includes(value?.intent||'');
  const baseline=value=>(value?.posture||'default_calculated')==='default_calculated'&&!(value?.intent||'')&&!(value?.value||'');
  function onMarket(){try{return Boolean(window.state?.route==='opportunities'||state?.route==='opportunities')}catch(_){return false}}
  function status(){
    const configured=selected();
    const configuredKey=keyOf(configured);
    const completedKey=keyOf(completed);
    return{
      busy,
      dirty:dirty||(!baseline(configured)&&completedKey!==configuredKey),
      needs_submit:dirty||(!baseline(configured)&&completedKey!==configuredKey),
      error,
      configured:{...configured},
      submitted:submitted?{...submitted}:null,
      completed:completed?{...completed}:null,
      missing_required_value:requiresValue(configured)&&!configured.value
    };
  }
  function notify(){
    window.dispatchEvent(new CustomEvent('fsffl:market-focus-state-changed',{detail:status()}));
    schedule();
  }
  function stopEnrichment(){
    if(enrichmentTimer){clearTimeout(enrichmentTimer);enrichmentTimer=null}
    enrichmentJobId=null;
  }
  function enrichmentStatus(payload){
    return payload?.decision_enrichment||{};
  }
  async function pollEnrichment(jobId,requestId,submittedKey){
    if(!jobId||requestId!==requestSeq||!onMarket())return;
    enrichmentJobId=jobId;
    try{
      const record=await api('/api/opportunities/focused-enrichment/'+encodeURIComponent(jobId));
      if(requestId!==requestSeq||!onMarket()||enrichmentJobId!==jobId)return;
      const status=String(record?.status||'');
      if(status==='completed'&&record?.result){
        const s=stateRef(),payload=record.result,context=window.state?.context||state?.context||{};
        if(!s||keyOf(selected())!==submittedKey)return;
        if(payload?.league_state_id&&context.state_id&&payload.league_state_id!==context.state_id)return;
        if(payload?.focal_team_id&&context.team_id&&payload.focal_team_id!==context.team_id)return;
        s.payload=payload;
        if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace();
        window.dispatchEvent(new CustomEvent('fsffl:market-decision-enrichment-applied',{detail:{job_id:jobId}}));
        stopEnrichment();
        return;
      }
      if(status==='failed'||status==='interrupted'){
        stopEnrichment();
        window.dispatchEvent(new CustomEvent('fsffl:market-decision-enrichment-settled',{detail:{job_id:jobId,status,error:record?.error||''}}));
        return;
      }
      enrichmentTimer=setTimeout(()=>pollEnrichment(jobId,requestId,submittedKey),750);
    }catch(_error){
      if(requestId!==requestSeq||enrichmentJobId!==jobId)return;
      enrichmentTimer=setTimeout(()=>pollEnrichment(jobId,requestId,submittedKey),1200);
    }
  }
  function setBusy(next){
    busy=Boolean(next);
    const control=document.querySelector('#opp-posture-control');if(!control)return;
    control.classList.toggle('ns-focus-refreshing',busy);
    control.setAttribute('aria-busy',busy?'true':'false');
    let node=control.querySelector('.ns-focus-refresh-status');
    if(!node){node=document.createElement('div');node.className='ns-focus-refresh-status';control.appendChild(node)}
    node.textContent=busy?'Finding opportunities…':(error?error:'');
  }
  function updateMethods(){
    const p=document.querySelector('#opp-posture-control .opp-posture-methods p');if(!p)return;
    p.textContent='Market Focus submits structural Search explicitly. Structural results return first; bounded bilateral Decision enrichment is progressive in the background. Deep Simulation remains an explicit offer drill-down. Value coordinates, Decision truth and acceptance uncertainty do not change.';
  }
  function markConfigured(){
    requestSeq+=1;
    stopEnrichment();
    dirty=true;
    error="";
    if(busy)setBusy(false);
    notify();
  }
  async function submit(){
    if(!onMarket())return;
    const s=stateRef();if(!s?.payload||s.payload.status!=='ready')return;
    const configured=selected();
    if(requiresValue(configured)&&!configured.value){
      error='Choose the required search value before finding opportunities.';
      dirty=true;
      notify();
      return;
    }
    const id=++requestSeq;
    const submittedKey=keyOf(configured);
    submitted={...configured};
    completed=null;
    dirty=false;
    error="";
    setBusy(true);
    notify();
    try{
      const params=new URLSearchParams(configured);
      const payload=await api(`/api/opportunities/focused-workspace?${params.toString()}`);
      if(id!==requestSeq||!onMarket())return;
      if(keyOf(selected())!==submittedKey){dirty=true;return}
      const context=window.state?.context||state?.context||{};
      if(payload?.league_state_id&&context.state_id&&payload.league_state_id!==context.state_id)return;
      if(payload?.focal_team_id&&context.team_id&&payload.focal_team_id!==context.team_id)return;
      const applied=payload?.trade_discovery?.focus||{};
      if(
        String(applied.intent||"")!==String(configured.intent||"")||
        String(applied.value||"")!==String(configured.value||"")||
        String(applied.posture||"")!==String(configured.posture||"")
      )return;
      s.payload=payload;
      s.nsSelectedTradeKey='';s.nsVisibleCount=4;s.tradeEvaluation=null;s.tradeEvaluationKey=null;
      completed={...configured,outcome:payload?.trade_discovery?.focus_outcome||null};
      if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace();
      window.dispatchEvent(new CustomEvent('fsffl:market-focus-applied',{detail:{...applied,outcome:completed.outcome}}));
      const enrich=enrichmentStatus(payload);
      if(enrich?.job_id&&['queued','running'].includes(String(enrich.status||''))){
        void pollEnrichment(String(enrich.job_id),id,submittedKey);
      }
    }catch(err){
      if(id!==requestSeq)return;
      error=`Unable to run this search: ${err?.message||String(err)}`;
      dirty=true;
    }finally{
      if(id===requestSeq){setBusy(false);notify()}
      updateMethods();
    }
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;updateMethods()})}

  window.fsfflMarketFocus={submit,refresh:submit,selected,status,markConfigured};
  window.addEventListener('fsffl:market-intent-changed',markConfigured);
  window.addEventListener('fsffl:market-rendered',schedule);
  window.addEventListener('fsffl:product-context-updated',()=>{requestSeq+=1;stopEnrichment();busy=false;dirty=false;error="";submitted=null;completed=null;notify()});
  document.addEventListener('DOMContentLoaded',schedule);
})();
