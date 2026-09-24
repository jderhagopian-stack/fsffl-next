const fsfflProductRoutes=[
  {route:'league',label:'Home'},
  {route:'my_team',label:'Franchise',teamScoped:true},
  {route:'players_assets',label:'Players & Assets',legacy:true},
  {route:'league_comparison',label:'League'},
  {route:'trade_center',label:'Trade Center',teamScoped:true},
  {route:'opportunities',label:'Market',teamScoped:true},
  {route:'behavioral_intelligence',label:'Behavioral Intelligence'},
  {route:'what_if',label:'What-If',teamScoped:true},
  {route:'simulator',label:'Simulator',teamScoped:true},
  {route:'analytics',label:'Analytics Terminal'},
  {route:'reports',label:'Reports'}
];

const fsfflProductSurfaceCopy={
  my_team:['Franchise','What is actually driving your team?','See the competitive profile, optimized lineup, league-relative position edges, fragility, core assets, optionality and draft-capital trajectory without blending them into one score.'],
  players_assets:['Players & Assets','Search the entire league market.','Search, filter and sort canonical league ownership with authoritative FSFFL Cardinal Value and separate market-position evidence, without creating a second valuation path.'],
  league_comparison:['League','How does this league fit together?','See competitive shape, positional control, age, future assets and fragility as distinct governed structures instead of another team leaderboard.'],
  opportunities:['Market','Where is there something worth doing?','Use guided discovery, intent-driven Trade Finder, the independent Player Board, and Free Agents without blending Search, Value or Decision authority.'],
  behavioral_intelligence:['Behavioral Intelligence','See what owners have actually done.','Explore source-backed owner transaction history as descriptive evidence without converting it into universal Value, strategy labels, or acceptance probability.'],
  what_if:['What-If','Stress-test your roster.','Change one roster-availability assumption, rerun authoritative Simulation, and see how your competitive outlook changes without inventing a second forecast or Value path.'],
  simulator:['Simulator','Test multiple roster shocks together.','Choose multiple active-roster players to make unavailable in one hypothetical State, then compare governed NEXT-4 competitive outcomes against baseline. Exact repeated scenarios can reuse authoritative cached results.'],
  analytics:['Analytics Terminal','Explore the full league intelligence stack.','Move between league, player, owner behavior, Value and evidence views using read-only authoritative Analytics/API outputs.'],
  reports:['Reports','Decision intelligence, explained clearly.','Team, league and evidence reports render from the same structured authoritative outputs used throughout the product, with no parallel calculation path.']
};

const fsfflStaticVersion='20260924-readiness-truth1';
const leagueAtlasStaticVersion='20260923-league-atlas-home-links1';
const mobileTouchStaticVersion='20260923-mobile-safearea2';
const homeNorthStarStaticVersion='20260924-live-usability-hotfix1';
const franchiseNorthStarStaticVersion='20260924-live-usability-hotfix1';
const opportunityHomeIntentStaticVersion='20260924-live-usability-hotfix1';
let leagueComparisonScriptPromise=null;
let myTeamScriptPromise=null;
let reportsScriptPromise=null;
let homeScriptPromise=null;
let opportunitiesScriptPromise=null;
let behavioralIntelligenceScriptPromise=null;
let analyticsTerminalScriptPromise=null;
let whatIfScriptPromise=null;
let simulatorScriptPromise=null;
function injectMobileTouchFix(){if(document.querySelector('link[data-fsffl-touch-fix]'))return;const link=document.createElement('link');link.rel='stylesheet';link.dataset.fsfflTouchFix='true';link.href=`/static/mobile_touch_fix.css?v=${mobileTouchStaticVersion}`;document.head.appendChild(link)}
function lazyProductScript(existingName,path,errorMessage,promiseGetter,promiseSetter,version=null){if(typeof window[existingName]==='function')return Promise.resolve();const existing=promiseGetter();if(existing)return existing;const promise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=`${path}?v=${fsfflStaticVersion}`;if(version)script.src=`${path}?v=${version}`;script.defer=true;script.onload=resolve;script.onerror=()=>reject(new Error(errorMessage));document.head.appendChild(script)});promiseSetter(promise);return promise}
function ensureLeagueComparisonScript(){if(typeof window.renderFsfflLeagueComparison==='function')return Promise.resolve();if(leagueComparisonScriptPromise)return leagueComparisonScriptPromise;leagueComparisonScriptPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=`/static/league_comparison.js?v=${leagueAtlasStaticVersion}`;script.defer=true;script.onload=resolve;script.onerror=()=>reject(new Error('Unable to load League presentation module'));document.head.appendChild(script)});return leagueComparisonScriptPromise}
function ensureMyTeamScript(){return lazyProductScript('renderFsfflMyTeam','/static/my_team_dashboard.js','Unable to load Franchise presentation module',()=>myTeamScriptPromise,value=>myTeamScriptPromise=value,franchiseNorthStarStaticVersion)}
function ensureReportsScript(){return lazyProductScript('renderFsfflReports','/static/reports.js','Unable to load Reports presentation module',()=>reportsScriptPromise,value=>reportsScriptPromise=value)}
function ensureHomeScript(){if(typeof window.installFsfflHomeExperience==='function')return Promise.resolve();if(homeScriptPromise)return homeScriptPromise;homeScriptPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=`/static/home_dashboard.js?v=${homeNorthStarStaticVersion}`;script.defer=true;script.onload=resolve;script.onerror=()=>reject(new Error('Unable to load Home presentation module'));document.head.appendChild(script)});return homeScriptPromise}
function ensureOpportunitiesScript(){if(typeof window.renderFsfflOpportunities==='function')return Promise.resolve();if(opportunitiesScriptPromise)return opportunitiesScriptPromise;opportunitiesScriptPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=`/static/opportunities.js?v=${opportunityHomeIntentStaticVersion}`;script.defer=true;script.onload=resolve;script.onerror=()=>reject(new Error('Unable to load Opportunity Engine presentation module'));document.head.appendChild(script)});return opportunitiesScriptPromise}
function ensureBehavioralIntelligenceScript(){return lazyProductScript('renderFsfflBehavioralIntelligence','/static/behavioral_intelligence.js','Unable to load Behavioral Intelligence presentation module',()=>behavioralIntelligenceScriptPromise,value=>behavioralIntelligenceScriptPromise=value)}
function ensureAnalyticsTerminalScript(){return lazyProductScript('renderFsfflAnalyticsTerminal','/static/analytics_terminal.js','Unable to load Analytics Terminal presentation module',()=>analyticsTerminalScriptPromise,value=>analyticsTerminalScriptPromise=value)}
function ensureWhatIfScript(){return lazyProductScript('renderFsfflWhatIf','/static/what_if.js','Unable to load What-If scenario module',()=>whatIfScriptPromise,value=>whatIfScriptPromise=value)}
function ensureSimulatorScript(){return lazyProductScript('renderFsfflSimulator','/static/simulator.js','Unable to load Simulator scenario module',()=>simulatorScriptPromise,value=>simulatorScriptPromise=value)}

function fsfflDisplayedProjectionObservation(player){const observations=player?.forecasts||[];return observations.find(item=>item.metric==='fantasy_points'&&item.horizon==='season')||null}
function fsfflDisplayedProjectionValue(player){const observation=fsfflDisplayedProjectionObservation(player);if(typeof observation?.distribution?.mean==='number'&&Number.isFinite(observation.distribution.mean))return observation.distribution.mean;return typeof player?.season_fantasy_points_projection==='number'&&Number.isFinite(player.season_fantasy_points_projection)?player.season_fantasy_points_projection:null}
window.fsfflDisplayedProjectionObservation=fsfflDisplayedProjectionObservation;
window.fsfflDisplayedProjectionValue=fsfflDisplayedProjectionValue;
function fsfflExplorerMissingForSort(value,key){if(value==null)return true;if(typeof value==='number'){if(!Number.isFinite(value))return true;if(value===0&&['value','market_percentile','projection'].includes(key))return true}return value===''}
function installExplorerSortSemantics(){if(typeof explorerSorted!=='function')return;explorerSorted=function(rows,sort){return[...rows].sort((a,b)=>{const av=a[sort.key],bv=b[sort.key],am=fsfflExplorerMissingForSort(av,sort.key),bm=fsfflExplorerMissingForSort(bv,sort.key);if(am&&bm)return 0;if(am)return 1;if(bm)return-1;const result=explorerCompare(av,bv);return sort.direction==='asc'?result:-result})}}
function installProjectionPresentation(){if(typeof playerProjection==='function')playerProjection=function(player){const value=fsfflDisplayedProjectionValue(player);return value==null?'—':fmtNumber(value,1)};if(typeof explorerPlayerProjection==='function')explorerPlayerProjection=function(player){return fsfflDisplayedProjectionValue(player)};if(typeof myTeamProjection==='function')myTeamProjection=function(player){const value=fsfflDisplayedProjectionValue(player);return value==null?'—':value.toFixed(1)};document.querySelectorAll('th').forEach(th=>{const label=th.textContent.trim();if(label==='Projection'||label==='Reg-season projection')th.textContent='NFL season projection';if(label==='Projected scoring')th.textContent='Reg-season scoring'})}
function presentDownstreamReadiness(){const context=state?.context;const coreReady=Boolean(context?.league_id&&context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);if(!coreReady)return;document.querySelectorAll('.runtime-stage').forEach(node=>{const label=node.querySelector('strong')?.textContent?.trim().toLowerCase();if(label!=='trade decision'&&label!=='opportunity')return;node.classList.remove('waiting_for_input','not_configured','capability-next');node.classList.add('ready');const mark=node.querySelector('.runtime-stage-mark');if(mark)mark.textContent='✓';const detail=node.querySelector('small');if(detail)detail.textContent=label==='trade decision'?'Trade Decision is available for submitted deals using the current authoritative evidence.':'Opportunity discovery is available as a downstream consumer of current Value and Trade Decision evidence.'});const opportunityValue=document.querySelector('#opportunity-value');if(opportunityValue)opportunityValue.textContent='Ready';const opportunityNote=document.querySelector('#opportunity-note');if(opportunityNote)opportunityNote.textContent='Open Opportunities to run the current Search workspace.'}
const fsfflDeepLinkState={intent:null};
function fsfflSetDeepLinkIntent(intent){fsfflDeepLinkState.intent=intent&&intent.route?{...intent}:null;return fsfflDeepLinkState.intent}
function fsfflPeekDeepLinkIntent(route=null){const intent=fsfflDeepLinkState.intent;if(!intent)return null;if(route&&intent.route!==route)return null;return intent}
function fsfflConsumeDeepLinkIntent(route){const intent=fsfflPeekDeepLinkIntent(route);if(!intent)return null;fsfflDeepLinkState.intent=null;return intent}
function fsfflNavigateTo(intent){if(!intent?.route)return;fsfflSetDeepLinkIntent(intent);if(typeof setRoute==='function')setRoute(intent.route)}
window.fsfflSetDeepLinkIntent=fsfflSetDeepLinkIntent;
window.fsfflPeekDeepLinkIntent=fsfflPeekDeepLinkIntent;
window.fsfflConsumeDeepLinkIntent=fsfflConsumeDeepLinkIntent;
window.fsfflNavigateTo=fsfflNavigateTo;
const FSFFL_SHARED_READINESS_STEPS=7;
const fsfflSharedReadinessState={
  pollTimer:null,
  pollAttempts:0,
  requestInFlight:false,
  lastStep:1,
};
const fsfflSharedReadinessPhases={
  queued:[1,'Preparing current intelligence…'],
  building_forecasts:[2,'Building projections…'],
  refreshing_state:[3,'Refreshing league state…'],
  running_simulation:[4,'Running season outlook…'],
  building_values:[5,'Building market values…'],
  attaching_results:[6,'Attaching current intelligence…'],
  completed:[7,'Intelligence current'],
};
function fsfflSharedReadinessEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function fsfflSharedReadinessSnapshot(){
  const context=state?.context||{},job=state?.intelligence?.job||null;
  if(!context?.league_id)return{connected:false,step:0,total:FSFFL_SHARED_READINESS_STEPS,label:'',failed:false,complete:false};
  if(job?.status==='failed'||job?.phase==='failed'||job?.status==='interrupted'||job?.phase==='interrupted'){
    const prior=Number.isFinite(fsfflSharedReadinessState.lastStep)?fsfflSharedReadinessState.lastStep:1;
    return{connected:true,step:Math.max(1,Math.min(FSFFL_SHARED_READINESS_STEPS,prior)),total:FSFFL_SHARED_READINESS_STEPS,label:(job?.status==='interrupted'||job?.phase==='interrupted')?'Refresh interrupted — last-good intelligence retained':'Intelligence refresh needs attention',failed:true,complete:false};
  }
  if(job&&fsfflSharedReadinessPhases[job.phase]){
    const [step,label]=fsfflSharedReadinessPhases[job.phase];
    fsfflSharedReadinessState.lastStep=step;
    return{connected:true,step,total:FSFFL_SHARED_READINESS_STEPS,label,failed:false,complete:step===FSFFL_SHARED_READINESS_STEPS};
  }
  let step=1;
  if(context?.forecast_ready)step=Math.max(step,2);
  if(context?.simulation_ready)step=Math.max(step,4);
  if(context?.value_ready)step=Math.max(step,5);
  const complete=Boolean(context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);
  if(complete)step=FSFFL_SHARED_READINESS_STEPS;
  fsfflSharedReadinessState.lastStep=step;
  const label=complete?'Intelligence current':!context?.forecast_ready?'Building projections…':!context?.simulation_ready?'Running season outlook…':!context?.value_ready?'Building market values…':'Attaching current intelligence…';
  return{connected:true,step,total:FSFFL_SHARED_READINESS_STEPS,label,failed:false,complete};
}
function fsfflSharedReadinessMarkup(status=fsfflSharedReadinessSnapshot()){
  const pct=status.total?Math.max(0,Math.min(100,(status.step/status.total)*100)):0;
  return '<div class="fsffl-shared-readiness-strip '+(status.complete?'complete ':'')+(status.failed?'failed':'')+'" role="status" aria-live="polite" style="--fsffl-readiness:'+pct.toFixed(1)+'%"><span class="fsffl-shared-readiness-mark" aria-hidden="true">'+(status.complete?'✓':'●')+'</span><strong>'+status.step+' / '+status.total+'</strong><span class="fsffl-shared-readiness-copy">'+fsfflSharedReadinessEscape(status.label)+'</span></div>';
}
function fsfflSharedReadinessHost(){
  let node=document.querySelector('#fsffl-sync-state');
  if(!node){
    const topbar=document.querySelector('.topbar');if(!topbar)return null;
    node=document.createElement('div');
    node.id='fsffl-sync-state';node.className='fsffl-sync-state';
    node.setAttribute('role','status');node.setAttribute('aria-live','polite');
    topbar.insertAdjacentElement('afterend',node);
  }
  node.classList.add('fsffl-shared-readiness-host');
  node.dataset.sharedReadiness='true';
  return node;
}
function fsfflRenderSharedReadiness(){
  const node=fsfflSharedReadinessHost();if(!node)return;
  const status=fsfflSharedReadinessSnapshot();
  if(!status.connected){node.hidden=true;node.innerHTML='';return}
  node.innerHTML=fsfflSharedReadinessMarkup(status);
  node.hidden=false;
}
function fsfflStopSharedReadinessPolling(){
  if(fsfflSharedReadinessState.pollTimer){clearInterval(fsfflSharedReadinessState.pollTimer);fsfflSharedReadinessState.pollTimer=null}
  fsfflSharedReadinessState.pollAttempts=0;
}
function fsfflSharedReadinessJobActive(){
  const job=state?.intelligence?.job;
  return job?.status==='queued'||job?.status==='running';
}
async function fsfflPollSharedReadinessOnce(){
  if(fsfflSharedReadinessState.requestInFlight||!state?.context?.league_id)return;
  fsfflSharedReadinessState.requestInFlight=true;
  try{
    // Poll the authoritative lifecycle endpoint directly. /api/intelligence/status
    // is useful for governed evidence stages, but the shared 1/7 -> 7/7 strip is
    // specifically a job-lifecycle view and must not lose the active job when
    // other presentation refreshes replace state.intelligence.
    const payload=await api('/api/intelligence/jobs/current');
    state.context={...state.context,...payload};
    state.intelligence=state.intelligence||{};
    state.intelligence.job={
      job_id:payload.job_id||null,
      status:payload.status||'idle',
      phase:payload.phase||'idle',
      message:payload.message||'',
      error:payload.error||null,
      league_state_id:payload.league_state_id||null,
      created_at:payload.created_at||null,
      updated_at:payload.updated_at||null,
    };
    fsfflRenderSharedReadiness();
    const status=fsfflSharedReadinessSnapshot();
    const terminal=['completed','failed','interrupted'].includes(state.intelligence.job.status);
    if(status.complete||status.failed||terminal)fsfflStopSharedReadinessPolling();
  }catch(_error){
    fsfflRenderSharedReadiness();
  }finally{
    fsfflSharedReadinessState.requestInFlight=false;
  }
}
function fsfflStartSharedReadinessPolling(){
  fsfflRenderSharedReadiness();
  const status=fsfflSharedReadinessSnapshot();
  if(!status.connected||status.complete||status.failed){fsfflStopSharedReadinessPolling();return}
  if(fsfflSharedReadinessState.pollTimer)return;
  fsfflSharedReadinessState.pollAttempts=0;
  void fsfflPollSharedReadinessOnce();
  fsfflSharedReadinessState.pollTimer=setInterval(()=>{
    fsfflSharedReadinessState.pollAttempts+=1;
    if(fsfflSharedReadinessState.pollAttempts>=36&&!fsfflSharedReadinessJobActive()){fsfflStopSharedReadinessPolling();return}
    void fsfflPollSharedReadinessOnce();
  },2500);
}
function installFsfflSharedReadinessStyles(){
  if(document.querySelector('#fsffl-shared-readiness-style'))return;
  const style=document.createElement('style');
  style.id='fsffl-shared-readiness-style';
  style.textContent='.fsffl-sync-state.fsffl-shared-readiness-host{box-sizing:border-box;margin:8px 18px 0!important;max-width:calc(100% - 36px);min-height:32px!important;padding:0 11px!important;border:1px solid var(--line)!important;border-radius:10px!important;background:#0a1120!important;display:block!important;pointer-events:none;overflow:hidden}.fsffl-shared-readiness-strip{--fsffl-readiness:0%;position:relative;display:grid;grid-template-columns:14px auto minmax(0,1fr);align-items:center;gap:7px;min-height:31px;padding:6px 0 7px;color:#8fa8bd;font-size:9px;line-height:1.2;overflow:hidden}.fsffl-shared-readiness-strip:after{content:"";position:absolute;left:0;bottom:0;width:var(--fsffl-readiness);height:2px;background:#38bdf8;transition:width .25s ease}.fsffl-shared-readiness-strip.complete:after{background:#35d399}.fsffl-shared-readiness-strip.failed:after{background:#ef6478}.fsffl-shared-readiness-mark{font-size:8px;color:#38bdf8}.fsffl-shared-readiness-strip.complete .fsffl-shared-readiness-mark{color:#35d399}.fsffl-shared-readiness-strip.failed .fsffl-shared-readiness-mark{color:#ef6478}.fsffl-shared-readiness-strip strong{font-size:9px;color:#c7d7e5;white-space:nowrap}.fsffl-shared-readiness-copy{min-width:0;white-space:normal;overflow-wrap:anywhere}@media(max-width:760px){.fsffl-sync-state.fsffl-shared-readiness-host{margin:7px 10px 0!important;max-width:calc(100% - 20px);padding:0 9px!important}.fsffl-shared-readiness-strip{grid-template-columns:12px auto minmax(0,1fr);gap:6px}}';
  document.head.appendChild(style);
}
window.fsfflSharedReadiness={
  snapshot:fsfflSharedReadinessSnapshot,
  render:fsfflRenderSharedReadiness,
  refresh:fsfflStartSharedReadinessPolling,
};

function productSurfaceError(label,error){const panel=document.querySelector('#generic-screen .panel');if(panel)panel.innerHTML=`<p class="eyebrow">${label}</p><h2>Unable to load this view.</h2><p class="lead">${String(error.message||error)}</p>`}
function renderProductSurface(route){const copy=fsfflProductSurfaceCopy[route];if(!copy)return;if(route==='players_assets'){window.fsfflSetDeepLinkIntent?.({route:'opportunities',marketTab:'player_board'});if(typeof setRoute==='function')setTimeout(()=>setRoute('opportunities'),0);return}const panel=document.querySelector('#generic-screen .panel');if(route!=='league_comparison')panel?.classList.remove('league-structure-panel');const eyebrow=document.querySelector('#generic-eyebrow'),title=document.querySelector('#generic-title'),body=document.querySelector('#generic-copy');if(eyebrow)eyebrow.textContent=copy[0];if(title)title.textContent=copy[1];if(body)body.textContent=copy[2];if(route==='my_team')ensureMyTeamScript().then(()=>{installProjectionPresentation();window.renderFsfflMyTeam?.();setTimeout(installProjectionPresentation,0)}).catch(error=>productSurfaceError('Franchise',error));if(route==='players_assets'&&typeof window.renderFsfflExplorer==='function'){installExplorerSortSemantics();installProjectionPresentation();window.renderFsfflExplorer(route);setTimeout(()=>{installProjectionPresentation();installExplorerSortSemantics()},0)}if(route==='league_comparison')ensureLeagueComparisonScript().then(()=>window.renderFsfflLeagueComparison?.()).catch(error=>productSurfaceError('League',error));if(route==='opportunities')ensureOpportunitiesScript().then(()=>window.renderFsfflOpportunities?.()).catch(error=>productSurfaceError('Opportunity Engine',error));if(route==='behavioral_intelligence')ensureBehavioralIntelligenceScript().then(()=>window.renderFsfflBehavioralIntelligence?.()).catch(error=>productSurfaceError('Behavioral Intelligence',error));if(route==='what_if')ensureWhatIfScript().then(()=>window.renderFsfflWhatIf?.()).catch(error=>productSurfaceError('What-If',error));if(route==='simulator')ensureSimulatorScript().then(()=>window.renderFsfflSimulator?.()).catch(error=>productSurfaceError('Simulator',error));if(route==='analytics')ensureAnalyticsTerminalScript().then(()=>window.renderFsfflAnalyticsTerminal?.()).catch(error=>productSurfaceError('Analytics Terminal',error));if(route==='reports')ensureReportsScript().then(()=>window.renderFsfflReports?.()).catch(error=>productSurfaceError('Reports',error))}
function rebuildProductNavigation(){const nav=document.querySelector('#primary-nav');if(!nav)return;nav.innerHTML='';const hasTeam=Boolean(state?.context?.team_id);fsfflProductRoutes.filter(item=>!item.legacy).forEach(item=>{const button=document.createElement('button');button.type='button';button.className='nav-item';button.dataset.route=item.route;if(item.route===state?.route)button.classList.add('active');if(item.teamScoped&&!hasTeam)button.classList.add('locked');button.innerHTML=`<span>${item.label}</span>${item.teamScoped&&!hasTeam?'<small>Select team</small>':''}`;button.addEventListener('click',event=>{event.preventDefault();if(button.classList.contains('locked'))return;if(typeof setRoute==='function')setRoute(item.route)});nav.appendChild(button)})}
function productRouteAwareSetRoute(route){if(!fsfflProductSurfaceCopy[route])return;document.querySelectorAll('.route-screen').forEach(item=>item.hidden=item.id!=='generic-screen');document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.route===route));renderProductSurface(route)}
function renderMobileRecoveryControls(){const topbar=document.querySelector('.topbar');const leagueScreen=document.querySelector('#league-screen');if(!topbar||!leagueScreen)return;let nav=document.querySelector('#mobile-direct-nav');if(!nav){nav=document.createElement('nav');nav.id='mobile-direct-nav';nav.className='mobile-direct-nav';nav.setAttribute('aria-label','Quick section navigation');topbar.insertAdjacentElement('afterend',nav)}nav.innerHTML='';fsfflProductRoutes.filter(item=>['league','my_team','league_comparison','trade_center','opportunities','what_if','simulator','analytics','reports','behavioral_intelligence'].includes(item.route)).forEach(item=>{const button=document.createElement('button');button.type='button';button.textContent=item.label;button.dataset.directRoute=item.route;const locked=item.teamScoped&&!state?.context?.team_id;button.disabled=locked;button.addEventListener('click',()=>{if(!button.disabled)setRoute(item.route)});nav.appendChild(button)});let chooser=document.querySelector('#mobile-team-chooser');if(!state?.context?.league_id||state?.context?.team_id){chooser?.remove();return}if(!chooser){chooser=document.createElement('section');chooser.id='mobile-team-chooser';chooser.className='panel mobile-team-chooser';const hero=leagueScreen.querySelector('.hero-row');hero?.insertAdjacentElement('afterend',chooser)}chooser.innerHTML='<p class="eyebrow">Choose your team</p><h2>Select the franchise you manage</h2><p class="lead">Use these buttons if the Managing dropdown is unreliable on your phone.</p><div class="mobile-team-grid"></div>';const grid=chooser.querySelector('.mobile-team-grid');(state.context.teams||[]).forEach(team=>{const button=document.createElement('button');button.type='button';button.className='secondary-button';button.textContent=team.display_name;button.addEventListener('click',async()=>{button.disabled=true;try{await selectTeam(team.team_id)}finally{button.disabled=false;renderMobileRecoveryControls();rebuildProductNavigation()}});grid.appendChild(button)})}
const originalRenderRuntimeStatus=typeof renderRuntimeStatus==='function'?renderRuntimeStatus:null;if(originalRenderRuntimeStatus){renderRuntimeStatus=function(){const result=originalRenderRuntimeStatus();presentDownstreamReadiness();return result}}
const originalSetRoute=typeof setRoute==='function'?setRoute:null;if(originalSetRoute){window.setRoute=function(route){if(fsfflProductSurfaceCopy[route]){state.route=route;fsfflRenderSharedReadiness();productRouteAwareSetRoute(route);document.querySelector('.sidebar')?.classList.remove('open');renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness();return}const result=originalSetRoute(route);fsfflRenderSharedReadiness();if(route==='league')ensureHomeScript().then(()=>{window.installFsfflHomeExperience?.();fsfflRenderSharedReadiness()}).catch(()=>{});if(route==='trade_center'&&typeof loadTradeCenter==='function')setTimeout(loadTradeCenter,0);renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness();return result};setRoute=window.setRoute}
const originalApplyContext=typeof applyContext==='function'?applyContext:null;if(originalApplyContext){applyContext=function(){const result=originalApplyContext();window.dispatchEvent(new CustomEvent('fsffl:product-context-updated',{detail:state.context}));renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness();return result}}
installFsfflSharedReadinessStyles();
window.addEventListener('fsffl:intelligence-status-updated',event=>{
  if(event.detail)state.intelligence=event.detail;
  fsfflRenderSharedReadiness();
  fsfflStartSharedReadinessPolling();
});
window.addEventListener('fsffl:product-context-updated',()=>{
  fsfflStopSharedReadinessPolling();
  setTimeout(()=>fsfflStartSharedReadinessPolling(),0);
});
window.addEventListener('fsffl:sync-state',()=>setTimeout(()=>fsfflRenderSharedReadiness(),0));
injectMobileTouchFix();window.addEventListener('load',()=>{injectMobileTouchFix();rebuildProductNavigation();renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness();fsfflStartSharedReadinessPolling();ensureHomeScript().then(()=>window.installFsfflHomeExperience?.()).catch(()=>{})});window.addEventListener('fsffl:product-context-updated',()=>{rebuildProductNavigation();renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness()});setTimeout(()=>{rebuildProductNavigation();renderMobileRecoveryControls();installExplorerSortSemantics();installProjectionPresentation();presentDownstreamReadiness()},0);