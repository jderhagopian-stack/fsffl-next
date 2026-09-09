(function(){
  const STORAGE_KEY='fsffl.tradeFinderPosture';
  const DEFAULT='default_calculated';
  let latestMeta=null;
  const originalFetch=window.fetch.bind(window);

  function selectedPosture(){
    try{return localStorage.getItem(STORAGE_KEY)||DEFAULT}catch(_){return DEFAULT}
  }

  function rememberPosture(value){
    try{localStorage.setItem(STORAGE_KEY,value)}catch(_){}
  }

  function workspaceRequest(input){
    const url=typeof input==='string'?input:(input&&input.url)||'';
    return String(url).includes('/api/opportunities/workspace');
  }

  function applyServerPostureView(payload){
    const discovery=payload&&payload.trade_discovery;
    const views=discovery&&discovery.posture_views;
    if(!views||typeof views!=='object')return payload;
    const requested=selectedPosture();
    const view=views[requested]||views[DEFAULT];
    if(!view)return payload;
    latestMeta=view.posture||payload.search_posture||null;
    return {
      ...payload,
      search_posture:latestMeta,
      trade_discovery:{
        ...discovery,
        candidates:Array.isArray(view.candidates)?view.candidates:discovery.candidates,
        spotlights:view.spotlights||discovery.spotlights,
        active_posture:requested
      }
    };
  }

  window.fetch=async function(input,init){
    const response=await originalFetch(input,init);
    if(!workspaceRequest(input)||!response.ok)return response;
    const contentType=response.headers.get('content-type')||'';
    if(!contentType.includes('application/json'))return response;
    try{
      const payload=applyServerPostureView(await response.clone().json());
      return new Response(JSON.stringify(payload),{
        status:response.status,
        statusText:response.statusText,
        headers:response.headers
      });
    }catch(_){return response}
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
    control.innerHTML='<label><span>What are you trying to do?</span><select id="opp-posture-select">'+options.map(row=>'<option value="'+String(row.value)+'"'+(row.value===selected?' selected':'')+'>'+String(row.label)+'</option>').join('')+'</select></label><small><strong>Calculated state:</strong> '+calculated+' · <strong>Search lens:</strong> '+effective+'. This changes Trade Finder discovery order only; it does not rewrite FSFFL Value, calculated state, Decision truth, or acceptance probability.</small>';
    control.querySelector('#opp-posture-select')?.addEventListener('change',event=>{
      rememberPosture(event.target.value||DEFAULT);
      if(typeof loadOpportunityWorkspace==='function')loadOpportunityWorkspace({showLoading:false});
      else window.location.reload();
    });
  }

  const observer=new MutationObserver(renderControl);
  document.addEventListener('DOMContentLoaded',()=>{
    observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','class']});
    renderControl();
  });
})();
