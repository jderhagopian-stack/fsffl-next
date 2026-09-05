const state={route:"league",context:null,leagueView:null};

function qs(selector){return document.querySelector(selector)}
function qsa(selector){return [...document.querySelectorAll(selector)]}

async function loadContext(){
  try{
    const response=await fetch('/api/product-context',{headers:{'Accept':'application/json'}});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    state.context=await response.json();
    updateEvidence();
  }catch(error){
    console.error('Unable to load product context',error);
  }
}

function updateEvidence(){
  const label=qs('#evidence-label');
  if(!label||!state.context) return;
  label.textContent=state.context.league_id?`State ${state.context.state_id||'loading'}`:'No league loaded';
}

function setRoute(route){
  state.route=route;
  qsa('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.route===route));
  const sidebar=qs('.sidebar');
  if(sidebar) sidebar.classList.remove('open');
}

function wireNavigation(){
  qsa('[data-route],[data-route-link]').forEach(button=>{
    button.addEventListener('click',()=>{
      const route=button.dataset.route||button.dataset.routeLink;
      if(button.classList.contains('locked')) return;
      setRoute(route);
    });
  });
  const mobile=qs('#mobile-menu');
  if(mobile) mobile.addEventListener('click',()=>qs('.sidebar')?.classList.toggle('open'));
}

function clearChart(container){while(container.firstChild)container.removeChild(container.firstChild)}

function renderBarChart(spec){
  const container=qs('#league-chart');
  if(!container||!spec?.series?.length)return;
  clearChart(container);
  container.className='';
  const points=spec.series[0].points.filter(point=>typeof point.y==='number');
  if(!points.length){container.textContent='No comparable data available.';return;}

  const width=900,height=310,pad={top:24,right:18,bottom:72,left:50};
  const innerW=width-pad.left-pad.right,innerH=height-pad.top-pad.bottom;
  const max=Math.max(...points.map(point=>point.y),0);
  const min=Math.min(...points.map(point=>point.y),0);
  const span=Math.max(max-min,1e-9);
  const barGap=8;
  const barW=Math.max(14,(innerW-(points.length-1)*barGap)/points.length);
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.classList.add('chart-svg');

  const axis=document.createElementNS(ns,'line');
  axis.setAttribute('x1',pad.left);axis.setAttribute('x2',width-pad.right);axis.setAttribute('y1',pad.top+innerH);axis.setAttribute('y2',pad.top+innerH);axis.classList.add('chart-axis');svg.appendChild(axis);

  const tooltip=document.createElement('div');tooltip.className='chart-tooltip';document.body.appendChild(tooltip);

  points.forEach((point,index)=>{
    const normalized=(point.y-min)/span;
    const h=Math.max(2,normalized*innerH);
    const x=pad.left+index*(barW+barGap);
    const y=pad.top+innerH-h;
    const rect=document.createElementNS(ns,'rect');
    rect.setAttribute('x',x);rect.setAttribute('y',y);rect.setAttribute('width',barW);rect.setAttribute('height',h);rect.setAttribute('rx',Math.min(6,barW/4));rect.classList.add('chart-bar');
    rect.addEventListener('mousemove',event=>{tooltip.style.display='block';tooltip.style.left=`${event.clientX+12}px`;tooltip.style.top=`${event.clientY+12}px`;tooltip.textContent=`${point.label}: ${point.y}`;});
    rect.addEventListener('mouseleave',()=>{tooltip.style.display='none'});
    if(point.drilldown_ref)rect.addEventListener('click',()=>window.dispatchEvent(new CustomEvent('fsffl:drilldown',{detail:point.drilldown_ref})));
    svg.appendChild(rect);

    const label=document.createElementNS(ns,'text');label.setAttribute('x',x+barW/2);label.setAttribute('y',height-44);label.setAttribute('text-anchor','end');label.setAttribute('transform',`rotate(-30 ${x+barW/2} ${height-44})`);label.textContent=point.label;label.classList.add('chart-label');svg.appendChild(label);
  });

  container.appendChild(svg);
}

async function loadLeagueMetric(metric){
  if(!state.context?.league_id)return;
  try{
    const response=await fetch(`/api/league/chart?metric=${encodeURIComponent(metric)}`);
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    renderBarChart(await response.json());
  }catch(error){console.error('Unable to load league metric',error)}
}

function wireMetricSelector(){
  const select=qs('#metric-select');
  if(!select)return;
  select.addEventListener('change',()=>loadLeagueMetric(select.value));
}

function wireConnectButton(){
  const button=qs('#connect-button');
  if(!button)return;
  button.addEventListener('click',()=>{
    window.dispatchEvent(new CustomEvent('fsffl:connect-provider'));
  });
}

window.addEventListener('fsffl:drilldown',event=>console.info('Drilldown requested',event.detail));
window.addEventListener('fsffl:connect-provider',()=>console.info('Provider connection flow not yet configured'));

wireNavigation();wireMetricSelector();wireConnectButton();loadContext();
