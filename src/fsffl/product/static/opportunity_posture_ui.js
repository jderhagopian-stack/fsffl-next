(function(){
  const STORAGE_KEY='fsffl.tradeFinderPosture';
  const DEFAULT='default_calculated';
  let latestMeta=null;
  let observerStarted=false;
  let renderQueued=false;
  let applyingWorkspace=false;
  let canonicalCandidates=null;
  let canonicalWorkspaceKey=null;

  function selectedPosture(){
    try{return localStorage.getItem(STORAGE_KEY)||DEFAULT}catch(_){return DEFAULT}
  }

  function rememberPosture(value){
    try{localStorage.setItem(STORAGE_KEY,value)}catch(_){}
  }

  function workspaceKey(payload){
    return `${payload?.league_state_id||''}|${payload?.focal_team_id||''}|${payload?.as_of||''}`;
  }

  function canonicalCandidatesFor(payload,discovery){
    const key=workspaceKey(payload);
    const freshServerPayload=!discovery?.active_posture;
    if(freshServerPayload||canonicalWorkspaceKey!==key||!Array.isArray(canonicalCandidates)){
      canonicalWorkspaceKey=key;
      canonicalCandidates=Array.isArray(discovery?.candidates)?discovery.candidates:[];
    }
    return canonicalCandidates;
  }

  function orderedCandidates(canonical,view){
    if(Array.isArray(view?.candidate_indices)){
      const ordered=[];
      for(const rawIndex of view.candidate_indices){
        const index=Number(rawIndex);
        if(Number.isInteger(index)&&index>=0&&index<canonical.length)ordered.push(canonical[index]);
      }
      if(ordered.length===view.candidate_indices.length)return ordered;
    }
    return Array.isArray(view?.candidates)?view.candidates:canonical;
  }

  function applyServerPostureView(payload){
    const discovery=payload&&payload.trade_discovery;
    const views=discovery&&discovery.posture_views;
    if(!views||typeof views!=='object')return payload;
    const requested=selectedPosture();
    const view=views[requested]||views[DEFAULT];
    if(!view)return payload;
    latestMeta=view.posture||payload.search_posture||null;
    const canonical=canonicalCandidatesFor(payload,discovery);
    if(discovery.active_posture===requested&&payload.search_posture===latestMeta)return payload;
    return {
      ...payload,
      search_posture:latestMeta,
      trade_discovery:{
        ...discovery,
        candidates:orderedCandidates(canonical,view),
        spotlights:view.spotlights||discovery.spotlights,
        active_posture:requested
      }
    };
  }

  function applyCurrentWorkspace(){
    if(applyingWorkspace||typeof fsfflOpportunityState==='undefined'||!fsfflOpportunityState.payload)return false;
    const updated=applyServerPostureView(fsfflOpportunityState.payload);
    if(updated===fsfflOpportunityState.payload)return false;
    applyingWorkspace=true;
    try{
      fsfflOpportunityState.payload=updated;
      if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace();
    }finally{
      applyingWorkspace=false;
    }
    return true;
  }

  window.fsfflOpportunityPosture={
    selectedPosture,
    applyWorkspace:applyServerPostureView,
    applyCurrentWorkspace
  };

  function activeOpportunityScreen(){
    const screen=document.querySelector('#generic-screen');
    if(!screen||screen.hidden)return null;
    const nav=document.querySelector('[data-route="opportunities"].active');
    if(!nav)return null;
    return screen.querySelector('.panel');
  }

  function installStyles(){
    if(document.getElementById('opp-posture-style'))return;
    const style=document.createElement('style');
    style.id='opp-posture-style';
    style.textContent='.opp-posture-control{margin:0 0 1rem;padding:.9rem 1rem;border:1px solid rgba(148,163,184,.22);border-radius:14px;background:rgba(15,23,42,.42)}.opp-posture-control label{display:grid;gap:.35rem}.opp-posture-control span{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;opacity:.72}.opp-posture-control select{width:100%;max-width:360px}.opp-posture-control small{display:block;margin-top:.45rem;line-height:1.35;opacity:.78}.opp-posture-control strong{font-weight:700}';
    document.head.appendChild(style);
  }

  function renderControl(){
    const panel=activeOpportunityScreen();
    if(!panel||!latestMeta)return;
    installStyles();
    let control=panel.querySelector('#opp-posture-control');
    if(!control){
      control=document.createElement('div');
      control.id='opp-posture-control';
      control.className='opp-posture-control';
      panel.prepend(control);
    }
    const options=Array.isArray(latestMeta.available_postures)?latestMeta.available_postures:[];
    const selected=selectedPosture();
    const calculated=String(latestMeta.calculated_competitive_state||'unknown').replaceAll('_',' ');
    const effective=String(latestMeta.effective_posture||'balanced').replaceAll('_',' ');
    const markup='<label><span>What are you trying to do?</span><select id="opp-posture-select">'+options.map(row=>'<option value="'+String(row.value)+'"'+(row.value===selected?' selected':'')+'>'+String(row.label)+'</option>').join('')+'</select></label><small><strong>Calculated state:</strong> '+calculated+' · <strong>Search lens:</strong> '+effective+'. This changes Trade Finder discovery order only; it does not rewrite FSFFL Value, calculated state, Decision truth, or acceptance probability.</small>';
    if(control.innerHTML===markup)return;
    control.innerHTML=markup;
    control.querySelector('#opp-posture-select')?.addEventListener('change',event=>{
      rememberPosture(event.target.value||DEFAULT);
      applyCurrentWorkspace();
      queueRender();
    });
  }

  const observer=new MutationObserver(()=>queueRender());

  function observe(){
    const screen=document.querySelector('#generic-screen');
    if(!screen)return;
    observer.observe(screen,{subtree:true,childList:true});
    observerStarted=true;
  }

  function renderSafely(){
    renderQueued=false;
    if(observerStarted){observer.disconnect();observerStarted=false}
    try{
      applyCurrentWorkspace();
      renderControl();
    }finally{
      observe();
    }
  }

  function queueRender(){
    if(renderQueued)return;
    renderQueued=true;
    requestAnimationFrame(renderSafely);
  }

  document.addEventListener('click',event=>{
    if(event.target?.closest?.('[data-route="opportunities"]'))queueRender();
  });

  document.addEventListener('DOMContentLoaded',()=>{
    observe();
    queueRender();
  });
})();
