(function(){
  const STORAGE_KEY='fsffl.tradeFinderPosture';
  const DEFAULT='default_calculated';
  const CONSUMER_LABELS={
    default_calculated:'Best for my team',
    win_now:'Build for a Championship',
    balanced:'Balanced Trade',
    retool:'Get Younger',
    rebuild:'Rebuild'
  };
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
    let active=false;
    try{active=Boolean(window.state?.route==='opportunities'||state?.route==='opportunities')}catch(_){active=false}
    if(!active&&!document.querySelector('[data-route="opportunities"].active'))return null;
    return screen.querySelector('.panel');
  }

  function consumerLabel(value,fallback){return CONSUMER_LABELS[value]||fallback||String(value||'').replaceAll('_',' ')}
  function stateLabel(value){const text=String(value||'unknown').replaceAll('_',' ');return text.charAt(0).toUpperCase()+text.slice(1)}

  function installStyles(){
    if(document.getElementById('opp-posture-style'))return;
    const style=document.createElement('style');
    style.id='opp-posture-style';
    style.textContent=`
      .opp-posture-control{margin:0 0 12px;padding:13px 14px;border:1px solid rgba(104,168,224,.2);border-radius:14px;background:linear-gradient(120deg,rgba(19,48,75,.88),rgba(8,20,33,.96));box-shadow:inset 3px 0 0 rgba(84,174,255,.72)}
      .opp-posture-control label{display:grid;grid-template-columns:minmax(0,1fr) minmax(210px,340px);gap:14px;align-items:center}
      .opp-posture-copy{display:grid;gap:3px}.opp-posture-kicker{font-size:7px;text-transform:uppercase;letter-spacing:.12em;color:#72a9d6}.opp-posture-title{font-size:13px;font-weight:800;letter-spacing:-.02em;color:#e6f2fd}.opp-posture-copy small{font-size:8px;line-height:1.35;color:#8198ad}
      .opp-posture-control select{width:100%;min-height:42px;border:1px solid rgba(104,168,224,.23);border-radius:10px;background:#0b1827;color:#edf7ff;padding:0 34px 0 11px;font-weight:750}
      .opp-posture-methods{margin-top:8px;border-top:1px solid rgba(137,171,205,.08)}.opp-posture-methods summary{padding-top:8px;font-size:7px;color:#6f879d;cursor:pointer}.opp-posture-methods p{margin:5px 0 0;font-size:7px;line-height:1.45;color:#667d91}
      @media(max-width:760px){.opp-posture-control{padding:12px}.opp-posture-control label{grid-template-columns:1fr;gap:9px}.opp-posture-title{font-size:12px}.opp-posture-control select{min-height:44px;font-size:12px}}
    `;
    document.head.appendChild(style);
  }

  function renderControl(){
    const panel=activeOpportunityScreen();
    if(!panel||!latestMeta)return;
    installStyles();
    let control=panel.querySelector('#opp-posture-control');
    const deck=panel.querySelector('.ns-market-deck');
    if(!control){
      control=document.createElement('div');
      control.id='opp-posture-control';
      control.className='opp-posture-control';
    }
    if(deck&&control.parentElement!==deck)deck.prepend(control);else if(!deck&&control.parentElement!==panel)panel.prepend(control);
    const options=Array.isArray(latestMeta.available_postures)?latestMeta.available_postures:[];
    const selected=selectedPosture();
    const calculated=stateLabel(latestMeta.calculated_competitive_state);
    const effective=consumerLabel(latestMeta.effective_posture,String(latestMeta.effective_posture||'balanced'));
    const defaultCopy=selected===DEFAULT?`Based on your ${calculated.toLowerCase()} competitive profile.`:`You are steering Market toward ${consumerLabel(selected)}.`;
    const markup='<label><span class="opp-posture-copy"><span class="opp-posture-kicker">Market focus</span><span class="opp-posture-title">What are you trying to do?</span><small>'+defaultCopy+'</small></span><select id="opp-posture-select" aria-label="What are you trying to do?">'+options.map(row=>'<option value="'+String(row.value)+'"'+(row.value===selected?' selected':'')+'>'+consumerLabel(row.value,row.label)+'</option>').join('')+'</select></label><details class="opp-posture-methods"><summary>How this changes suggestions</summary><p>Your calculated competitive state stays '+calculated+'. This changes Trade Finder discovery order only, using the server-published Market focus. Current Value, Decision results and owner-history evidence are unchanged. Active focus: '+effective+'.</p></details>';
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
  window.addEventListener('fsffl:product-context-updated',queueRender);
  document.addEventListener('DOMContentLoaded',()=>{
    observe();
    queueRender();
  });
})();
