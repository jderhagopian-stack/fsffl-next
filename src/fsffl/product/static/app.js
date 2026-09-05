const state={route:"league",context:null,leagueView:null};

function qs(selector){return document.querySelector(selector)}
function qsa(selector){return [...document.querySelectorAll(selector)]}

async function api(path,options={}){
  const response=await fetch(path,{headers:{'Accept':'application/json','Content-Type':'application/json',...(options.headers||{})},...options});
  if(!response.ok){
    let detail=`HTTP ${response.status}`;
    try{const payload=await response.json();detail=payload.detail||detail}catch(_){/* ignore */}
    throw new Error(detail);
  }
  return response.json();
}

async function loadContext(){
  try{
    state.context=await api('/api/product-context');
    applyContext();
  }catch(error){
    console.error('Unable to load product context',error);
  }
}

function applyContext(){
  updateEvidence();
  populateSelectors();
  updateNavigationLocks();
  if(state.context?.league_id)loadLeagueMetric(qs('#metric-select')?.value||'expected_wins');
}

function updateEvidence(){
  const label=qs('#evidence-label');
  if(!label||!state.context)return;
  label.textContent=state.context.league_id?`State ${String(state.context.state_id||'loading').slice(0,12)}…`:'No league loaded';
  const dot=label.closest('.evidence-pill')?.querySelector('.dot');
  if(dot)dot.style.background=state.context.league_id?'#a7f3d0':'#64748b';
}

function populateSelectors(){
  const leagueSelect=qs('#league-select');
  const teamSelect=qs('#team-select');
  if(!leagueSelect||!teamSelect||!state.context)return;

  leagueSelect.innerHTML='';
  if(state.context.league_id){
    const option=document.createElement('option');option.value=state.context.league_id;option.textContent=state.context.league_name||state.context.league_id;leagueSelect.appendChild(option);
  }else{
    const option=document.createElement('option');option.value='';option.textContent='Connect league';leagueSelect.appendChild(option);
  }

  teamSelect.innerHTML='<option value="">Select team</option>';
  (state.context.teams||[]).forEach(team=>{
    const option=document.createElement('option');option.value=team.team_id;option.textContent=team.display_name;if(team.team_id===state.context.team_id)option.selected=true;teamSelect.appendChild(option);
  });
  teamSelect.disabled=!state.context.league_id;
}

function updateNavigationLocks(){
  const hasTeam=Boolean(state.context?.team_id);
  qsa('.nav-item').forEach(item=>{
    const teamScoped=['my_team','trade_center','opportunities'].includes(item.dataset.route);
    item.classList.toggle('locked',teamScoped&&!hasTeam);
    const hint=item.querySelector('small');
    if(hint&&teamScoped)hint.textContent=hasTeam?'':'Select team';
  });
}

function setRoute(route){
  state.route=route;
  qsa('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.route===route));
  qs('.sidebar')?.classList.remove('open');
}

function wireNavigation(){
  qsa('[data-route],[data-route-link]').forEach(button=>{
    button.addEventListener('click',()=>{
      const route=button.dataset.route||button.dataset.routeLink;
      const nav=qsa('.nav-item').find(item=>item.dataset.route===route);
      if(nav?.classList.contains('locked'))return;
      setRoute(route);
    });
  });
  qs('#mobile-menu')?.addEventListener('click',()=>qs('.sidebar')?.classList.toggle('open'));
}

function clearChart(container){while(container.firstChild)container.removeChild(container.firstChild)}
function showChartMessage(message){const container=qs('#league-chart');if(!container)return;clearChart(container);container.className='chart-empty';const p=document.createElement('p');p.textContent=message;container.appendChild(p)}

function renderBarChart(spec){
  const container=qs('#league-chart');
  if(!container||!spec?.series?.length)return;
  clearChart(container);container.className='';
  const points=spec.series[0].points.filter(point=>typeof point.y==='number');
  if(!points.length){showChartMessage('No comparable data available.');return;}

  const width=900,height=310,pad={top:24,right:18,bottom:72,left:50};
  const innerW=width-pad.left-pad.right,innerH=height-pad.top-pad.bottom;
  const max=Math.max(...points.map(point=>point.y),0),min=Math.min(...points.map(point=>point.y),0),span=Math.max(max-min,1e-9);
  const barGap=8,barW=Math.max(14,(innerW-(points.length-1)*barGap)/points.length);
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.classList.add('chart-svg');
  const axis=document.createElementNS(ns,'line');axis.setAttribute('x1',pad.left);axis.setAttribute('x2',width-pad.right);axis.setAttribute('y1',pad.top+innerH);axis.setAttribute('y2',pad.top+innerH);axis.classList.add('chart-axis');svg.appendChild(axis);
  const tooltip=document.createElement('div');tooltip.className='chart-tooltip';document.body.appendChild(tooltip);

  points.forEach((point,index)=>{
    const normalized=(point.y-min)/span,h=Math.max(2,normalized*innerH),x=pad.left+index*(barW+barGap),y=pad.top+innerH-h;
    const rect=document.createElementNS(ns,'rect');rect.setAttribute('x',x);rect.setAttribute('y',y);rect.setAttribute('width',barW);rect.setAttribute('height',h);rect.setAttribute('rx',Math.min(6,barW/4));rect.classList.add('chart-bar');
    rect.addEventListener('mousemove',event=>{tooltip.style.display='block';tooltip.style.left=`${event.clientX+12}px`;tooltip.style.top=`${event.clientY+12}px`;tooltip.textContent=`${point.label}: ${point.y}`});rect.addEventListener('mouseleave',()=>tooltip.style.display='none');
    if(point.drilldown_ref)rect.addEventListener('click',()=>window.dispatchEvent(new CustomEvent('fsffl:drilldown',{detail:point.drilldown_ref})));svg.appendChild(rect);
    const label=document.createElementNS(ns,'text');label.setAttribute('x',x+barW/2);label.setAttribute('y',height-44);label.setAttribute('text-anchor','end');label.setAttribute('transform',`rotate(-30 ${x+barW/2} ${height-44})`);label.textContent=point.label;label.classList.add('chart-label');svg.appendChild(label);
  });
  container.appendChild(svg);
}

async function loadLeagueMetric(metric){
  if(!state.context?.league_id)return;
  try{renderBarChart(await api(`/api/league/chart?metric=${encodeURIComponent(metric)}`))}
  catch(error){showChartMessage(`League loaded. ${error.message}.`)}
}

function wireMetricSelector(){qs('#metric-select')?.addEventListener('change',event=>loadLeagueMetric(event.target.value))}

async function connectSleeper(){
  const leagueId=window.prompt('Enter your Sleeper league ID');
  if(!leagueId?.trim())return;
  const button=qs('#connect-button'),original=button?.textContent;
  if(button){button.disabled=true;button.textContent='Connecting…'}
  try{
    state.context=await api('/api/connect/sleeper',{method:'POST',body:JSON.stringify({league_external_id:leagueId.trim()})});
    applyContext();
  }catch(error){window.alert(`Could not connect league: ${error.message}`)}
  finally{if(button){button.disabled=false;button.textContent=original}}
}

async function selectTeam(teamId){
  if(!teamId)return;
  try{state.context=await api('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})});applyContext()}
  catch(error){window.alert(`Could not select team: ${error.message}`)}
}

function wireConnectButton(){qs('#connect-button')?.addEventListener('click',connectSleeper);qs('#team-select')?.addEventListener('change',event=>selectTeam(event.target.value))}

window.addEventListener('fsffl:drilldown',event=>console.info('Drilldown requested',event.detail));
wireNavigation();wireMetricSelector();wireConnectButton();loadContext();
