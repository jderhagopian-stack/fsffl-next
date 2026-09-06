const fsfflProductRoutes=[
  {route:'league',label:'Home'},
  {route:'my_team',label:'My Team',teamScoped:true},
  {route:'players_assets',label:'Players & Assets'},
  {route:'league_comparison',label:'League Comparison'},
  {route:'trade_center',label:'Trade Center',teamScoped:true},
  {route:'opportunities',label:'Opportunities',teamScoped:true},
  {route:'what_if',label:'What-If',teamScoped:true},
  {route:'simulator',label:'Simulator'},
  {route:'analytics',label:'Analytics Explorer'},
  {route:'reports',label:'Reports'}
];

const fsfflProductSurfaceCopy={
  players_assets:['Players & Assets','Search the entire league market.','Search, filter and sort canonical league ownership with authoritative FSFFL Value and separate market-position evidence, without creating a second valuation path.'],
  league_comparison:['League Comparison','Compare every franchise live.','Interactive rankings, tiles and charts expose projected scoring, expected wins, playoff odds, market portfolio and pick inventory from authoritative Analytics outputs.'],
  what_if:['Alternate History / What-If','Change one thing. Re-run the consequences.','Counterfactual scenarios will create a changed point-in-time State and then reuse Forecast, Value, Decision and Simulation authority to show what would have changed.'],
  simulator:['Simulator','Test the future before acting.','Scenario controls will expose governed NEXT-4 competitive outcomes for lineup, roster, injury and transaction scenarios. Expensive simulation work will remain server-owned, reusable and cacheable.'],
  analytics:['Analytics Explorer','Compare the whole league without hunting for answers.','Search and sort authoritative team-level outputs from State, Forecast, Value and Simulation.'],
  reports:['Reports','Decision intelligence, explained clearly.','Polished reports will render from the same structured authoritative outputs used throughout the product, with no parallel calculation path.']
};

let leagueComparisonScriptPromise=null;
function ensureLeagueComparisonScript(){
  if(typeof window.renderFsfflLeagueComparison==='function')return Promise.resolve();
  if(leagueComparisonScriptPromise)return leagueComparisonScriptPromise;
  leagueComparisonScriptPromise=new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src='/static/league_comparison.js';
    script.defer=true;
    script.onload=resolve;
    script.onerror=()=>reject(new Error('Unable to load League Comparison presentation module'));
    document.head.appendChild(script);
  });
  return leagueComparisonScriptPromise;
}

function renderProductSurface(route){
  const copy=fsfflProductSurfaceCopy[route];
  if(!copy)return;
  const eyebrow=document.querySelector('#generic-eyebrow');
  const title=document.querySelector('#generic-title');
  const body=document.querySelector('#generic-copy');
  if(eyebrow)eyebrow.textContent=copy[0];
  if(title)title.textContent=copy[1];
  if(body)body.textContent=copy[2];
  if(typeof window.renderFsfflExplorer==='function'&&(route==='players_assets'||route==='analytics'))window.renderFsfflExplorer(route);
  if(route==='league_comparison'){
    ensureLeagueComparisonScript().then(()=>window.renderFsfflLeagueComparison?.()).catch(error=>{
      const panel=document.querySelector('#generic-screen .panel');
      if(panel)panel.innerHTML=`<p class="eyebrow">League Comparison</p><h2>Unable to load League Comparison.</h2><p class="lead">${String(error.message||error)}</p>`;
    });
  }
}

function rebuildProductNavigation(){
  const nav=document.querySelector('#primary-nav');
  if(!nav)return;
  nav.innerHTML='';
  const hasTeam=Boolean(window.state?.context?.team_id||state?.context?.team_id);
  fsfflProductRoutes.forEach(item=>{
    const button=document.createElement('button');
    button.className='nav-item';
    button.dataset.route=item.route;
    if(item.route===(window.state?.route||state?.route))button.classList.add('active');
    if(item.teamScoped&&!hasTeam)button.classList.add('locked');
    button.innerHTML=`<span>${item.label}</span>${item.teamScoped&&!hasTeam?'<small>Select team</small>':''}`;
    button.addEventListener('click',()=>{
      if(button.classList.contains('locked'))return;
      if(typeof setRoute==='function')setRoute(item.route);
    });
    nav.appendChild(button);
  });
}

function productRouteAwareSetRoute(route){
  if(!fsfflProductSurfaceCopy[route])return;
  document.querySelectorAll('.route-screen').forEach(item=>item.hidden=item.id!=='generic-screen');
  document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.route===route));
  renderProductSurface(route);
}

const originalSetRoute=typeof setRoute==='function'?setRoute:null;
if(originalSetRoute){
  window.setRoute=function(route){
    if(fsfflProductSurfaceCopy[route]){
      if(typeof state!=='undefined')state.route=route;
      productRouteAwareSetRoute(route);
      document.querySelector('.sidebar')?.classList.remove('open');
      return;
    }
    return originalSetRoute(route);
  };
  setRoute=window.setRoute;
}

window.addEventListener('load',rebuildProductNavigation);
window.addEventListener('fsffl:product-context-updated',rebuildProductNavigation);
setTimeout(rebuildProductNavigation,0);
