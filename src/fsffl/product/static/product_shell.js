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
  my_team:['My Team','Your franchise command center.','See competitive outlook, optimized lineup, roster depth, draft picks, authoritative FSFFL Value and supporting evidence in one place.'],
  players_assets:['Players & Assets','Search the entire league market.','Search, filter and sort canonical league ownership with authoritative FSFFL Value and separate market-position evidence, without creating a second valuation path.'],
  league_comparison:['League Comparison','Compare every franchise live.','Interactive rankings, tiles and charts expose projected scoring, expected wins, playoff odds, market portfolio and pick inventory from authoritative Analytics outputs.'],
  what_if:['Alternate History / What-If','Change one thing. Re-run the consequences.','Counterfactual scenarios will create a changed point-in-time State and then reuse Forecast, Value, Decision and Simulation authority to show what would have changed.'],
  simulator:['Simulator','Test the future before acting.','Scenario controls will expose governed NEXT-4 competitive outcomes for lineup, roster, injury and transaction scenarios. Expensive simulation work will remain server-owned, reusable and cacheable.'],
  analytics:['Analytics Explorer','Compare the whole league without hunting for answers.','Search and sort authoritative team-level outputs from State, Forecast, Value and Simulation.'],
  reports:['Reports','Decision intelligence, explained clearly.','Team, league and evidence reports render from the same structured authoritative outputs used throughout the product, with no parallel calculation path.']
};

const fsfflStaticVersion='20260906-touch4';
let leagueComparisonScriptPromise=null;
let myTeamScriptPromise=null;
let reportsScriptPromise=null;
let homeScriptPromise=null;
function injectMobileTouchFix(){if(document.querySelector('link[data-fsffl-touch-fix]'))return;const link=document.createElement('link');link.rel='stylesheet';link.dataset.fsfflTouchFix='true';link.href=`/static/mobile_touch_fix.css?v=${fsfflStaticVersion}`;document.head.appendChild(link)}
function lazyProductScript(existingName,path,errorMessage,promiseGetter,promiseSetter){if(typeof window[existingName]==='function')return Promise.resolve();const existing=promiseGetter();if(existing)return existing;const promise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=`${path}?v=${fsfflStaticVersion}`;script.defer=true;script.onload=resolve;script.onerror=()=>reject(new Error(errorMessage));document.head.appendChild(script)});promiseSetter(promise);return promise}
function ensureLeagueComparisonScript(){return lazyProductScript('renderFsfflLeagueComparison','/static/league_comparison.js','Unable to load League Comparison presentation module',()=>leagueComparisonScriptPromise,value=>leagueComparisonScriptPromise=value)}
function ensureMyTeamScript(){return lazyProductScript('renderFsfflMyTeam','/static/my_team_dashboard.js','Unable to load My Team presentation module',()=>myTeamScriptPromise,value=>myTeamScriptPromise=value)}
function ensureReportsScript(){return lazyProductScript('renderFsfflReports','/static/reports.js','Unable to load Reports presentation module',()=>reportsScriptPromise,value=>reportsScriptPromise=value)}
function ensureHomeScript(){return lazyProductScript('installFsfflHomeExperience','/static/home_dashboard.js','Unable to load Home presentation module',()=>homeScriptPromise,value=>homeScriptPromise=value)}

function productSurfaceError(label,error){const panel=document.querySelector('#generic-screen .panel');if(panel)panel.innerHTML=`<p class="eyebrow">${label}</p><h2>Unable to load this view.</h2><p class="lead">${String(error.message||error)}</p>`}
function renderProductSurface(route){const copy=fsfflProductSurfaceCopy[route];if(!copy)return;const eyebrow=document.querySelector('#generic-eyebrow'),title=document.querySelector('#generic-title'),body=document.querySelector('#generic-copy');if(eyebrow)eyebrow.textContent=copy[0];if(title)title.textContent=copy[1];if(body)body.textContent=copy[2];if(route==='my_team')ensureMyTeamScript().then(()=>window.renderFsfflMyTeam?.()).catch(error=>productSurfaceError('My Team',error));if(typeof window.renderFsfflExplorer==='function'&&(route==='players_assets'||route==='analytics'))window.renderFsfflExplorer(route);if(route==='league_comparison')ensureLeagueComparisonScript().then(()=>window.renderFsfflLeagueComparison?.()).catch(error=>productSurfaceError('League Comparison',error));if(route==='reports')ensureReportsScript().then(()=>window.renderFsfflReports?.()).catch(error=>productSurfaceError('Reports',error))}
function rebuildProductNavigation(){const nav=document.querySelector('#primary-nav');if(!nav)return;nav.innerHTML='';const hasTeam=Boolean(state?.context?.team_id);fsfflProductRoutes.forEach(item=>{const button=document.createElement('button');button.type='button';button.className='nav-item';button.dataset.route=item.route;if(item.route===state?.route)button.classList.add('active');if(item.teamScoped&&!hasTeam)button.classList.add('locked');button.innerHTML=`<span>${item.label}</span>${item.teamScoped&&!hasTeam?'<small>Select team</small>':''}`;button.addEventListener('click',event=>{event.preventDefault();if(button.classList.contains('locked'))return;if(typeof setRoute==='function')setRoute(item.route)});nav.appendChild(button)})}
function productRouteAwareSetRoute(route){if(!fsfflProductSurfaceCopy[route])return;document.querySelectorAll('.route-screen').forEach(item=>item.hidden=item.id!=='generic-screen');document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.route===route));renderProductSurface(route)}

function renderMobileRecoveryControls(){
  const topbar=document.querySelector('.topbar');
  const leagueScreen=document.querySelector('#league-screen');
  if(!topbar||!leagueScreen)return;
  let nav=document.querySelector('#mobile-direct-nav');
  if(!nav){nav=document.createElement('nav');nav.id='mobile-direct-nav';nav.className='mobile-direct-nav';nav.setAttribute('aria-label','Quick section navigation');topbar.insertAdjacentElement('afterend',nav)}
  nav.innerHTML='';
  fsfflProductRoutes.filter(item=>['league','my_team','players_assets','league_comparison','trade_center','analytics','reports'].includes(item.route)).forEach(item=>{
    const button=document.createElement('button');button.type='button';button.textContent=item.label;button.dataset.directRoute=item.route;const locked=item.teamScoped&&!state?.context?.team_id;button.disabled=locked;button.addEventListener('click',()=>{if(!button.disabled)setRoute(item.route)});nav.appendChild(button)
  });

  let chooser=document.querySelector('#mobile-team-chooser');
  if(!state?.context?.league_id||state?.context?.team_id){chooser?.remove();return}
  if(!chooser){chooser=document.createElement('section');chooser.id='mobile-team-chooser';chooser.className='panel mobile-team-chooser';const hero=leagueScreen.querySelector('.hero-row');hero?.insertAdjacentElement('afterend',chooser)}
  chooser.innerHTML='<p class="eyebrow">Choose your team</p><h2>Select the franchise you manage</h2><p class="lead">Use these buttons if the Managing dropdown is unreliable on your phone.</p><div class="mobile-team-grid"></div>';
  const grid=chooser.querySelector('.mobile-team-grid');
  (state.context.teams||[]).forEach(team=>{const button=document.createElement('button');button.type='button';button.className='secondary-button';button.textContent=team.display_name;button.addEventListener('click',async()=>{button.disabled=true;try{await selectTeam(team.team_id)}finally{button.disabled=false;renderMobileRecoveryControls();rebuildProductNavigation()}});grid.appendChild(button)})
}

const originalSetRoute=typeof setRoute==='function'?setRoute:null;
if(originalSetRoute){window.setRoute=function(route){if(fsfflProductSurfaceCopy[route]){state.route=route;productRouteAwareSetRoute(route);document.querySelector('.sidebar')?.classList.remove('open');renderMobileRecoveryControls();return}const result=originalSetRoute(route);if(route==='league')ensureHomeScript().then(()=>window.installFsfflHomeExperience?.()).catch(()=>{});renderMobileRecoveryControls();return result};setRoute=window.setRoute}

const originalApplyContext=typeof applyContext==='function'?applyContext:null;
if(originalApplyContext){applyContext=function(){const result=originalApplyContext();window.dispatchEvent(new CustomEvent('fsffl:product-context-updated',{detail:state.context}));renderMobileRecoveryControls();return result}}

injectMobileTouchFix();
window.addEventListener('load',()=>{injectMobileTouchFix();rebuildProductNavigation();renderMobileRecoveryControls();ensureHomeScript().then(()=>window.installFsfflHomeExperience?.()).catch(()=>{})});
window.addEventListener('fsffl:product-context-updated',()=>{rebuildProductNavigation();renderMobileRecoveryControls()});
setTimeout(()=>{rebuildProductNavigation();renderMobileRecoveryControls()},0);
