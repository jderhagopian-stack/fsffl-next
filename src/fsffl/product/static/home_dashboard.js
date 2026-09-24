/* FSFFL NEXT Home North Star.
 * Presentation only. Home summarizes governed evidence already owned by State,
 * Team Utility, position-strength Analytics and the exact current Simulation.
 * It does not launch Opportunity Search, Decision, Value or new Simulation work.
 */
const fsfflHomeNorthStarState={
  payload:null,
  loading:false,
  error:null,
  requestKey:null,
  positionLens:'rank',
  readinessPollTimer:null,
  readinessPollAttempts:0,
  readinessRequestInFlight:false,
  syncSnapshot:null,
  latestSyncState:null,
};

function homeEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function homeNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function homePercent(value,digits=0){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function homeWords(value){return String(value||'').replaceAll('_',' ')}
function homeStateLabel(value){return value&&value!=='unknown'?homeWords(value):'Not classified'}
function homeRecord(row){if(!row)return'—';return `${row.wins??0}-${row.losses??0}${Number(row.ties||0)>0?'-'+row.ties:''}`}
function homePayload(){return fsfflHomeNorthStarState.payload}
function homeView(){return homePayload()?.team_view||null}
function homeManagedTeamId(){return homePayload()?.managed_team_id||state?.context?.team_id||null}
function homeStandings(){return homePayload()?.standings||[]}
function homeStanding(){const id=homeManagedTeamId();return homeStandings().find(row=>row.team_id===id)||null}
function homeSimulation(){const id=homeManagedTeamId();return (homePayload()?.simulation?.teams||[]).find(row=>row.team_id===id)||null}
function homePositionRows(){
  const rows=homeView()?.position_strengths||[],positions=['QB','RB','WR','TE'];
  return positions.map(position=>rows.find(row=>row.position===position)||null);
}
function homePressurePoint(){
  const order={QB:0,RB:1,WR:2,TE:3};
  const rows=homePositionRows().filter(Boolean);
  if(!rows.length)return null;
  return [...rows].sort((a,b)=>{
    const ar=Number.isFinite(Number(a.league_rank))?Number(a.league_rank):-1,br=Number.isFinite(Number(b.league_rank))?Number(b.league_rank):-1;
    if(ar!==br)return br-ar;
    const ai=Number.isFinite(Number(a.strength_index))?Number(a.strength_index):Infinity,bi=Number.isFinite(Number(b.strength_index))?Number(b.strength_index):Infinity;
    if(ai!==bi)return ai-bi;
    return (order[a.position]??99)-(order[b.position]??99);
  })[0]||null;
}
function homeFragility(){
  const view=homeView(),resilience=view?.utility?.roster_resilience;
  if(!resilience||typeof resilience.largest_single_player_lineup_drop!=='number')return null;
  const ids=resilience.largest_single_player_lineup_drop_player_ids||[];
  const players=ids.map(id=>(view.players||[]).find(player=>player.player_id===id)).filter(Boolean);
  return{
    drop:resilience.largest_single_player_lineup_drop,
    playerIds:ids,
    players,
    label:players.length?players.map(player=>player.full_name).join(' / '):'Driver unavailable',
    position:players[0]?.position||null,
    playerId:players[0]?.player_id||null,
  };
}
function homeAdjacentStandings(){
  const standings=[...homeStandings()].sort((a,b)=>a.rank-b.rank),managed=homeStanding();
  if(!managed)return[];
  const index=standings.findIndex(row=>row.team_id===managed.team_id);
  return standings.slice(Math.max(0,index-1),Math.min(standings.length,index+2));
}
function homeNavigate(intent){
  if(typeof window.fsfflNavigateTo==='function'){window.fsfflNavigateTo(intent);return}
  if(typeof setRoute==='function')setRoute(intent.route);
}
function homeIntentFromButton(button){
  const action=button.dataset.homeAction,teamId=homeManagedTeamId();
  if(action==='franchise')return{route:'my_team',teamId};
  if(action==='pressure')return{route:'opportunities',teamId,position:button.dataset.position||null,source:'home-pressure'};
  if(action==='outlook')return{route:'league_comparison',section:'overview',teamId,metric:button.dataset.metric||null,source:'home-outlook'};
  if(action==='position')return{route:'league_comparison',section:'positions',teamId,position:button.dataset.position||null,source:'home-position'};
  if(action==='exposure')return{route:'league_comparison',section:'positions',teamId,position:button.dataset.position||null,playerId:button.dataset.playerId||null,fragilityDriver:true,source:'home-exposure'};
  if(action==='expected-finish')return{route:'league_comparison',section:'overview',teamId,metric:'expected_finish',source:'home-expected-finish'};
  if(action==='league-context')return{route:'league_comparison',section:'overview',teamId,source:'home-league-context'};
  return null;
}
function homeWireActions(root){
  root.querySelectorAll('[data-home-action]').forEach(button=>button.addEventListener('click',()=>{
    const intent=homeIntentFromButton(button);if(intent)homeNavigate(intent);
  }));
  root.querySelectorAll('[data-home-position-lens]').forEach(button=>button.addEventListener('click',()=>{
    fsfflHomeNorthStarState.positionLens=button.dataset.homePositionLens==='strength'?'strength':'rank';
    renderFsfflHomeNorthStar();
  }));
}
function homeCircle(row){
  if(!row)return'<span class="home-position-pill unavailable"><b>—</b><small>Unavailable</small></span>';
  const mode=fsfflHomeNorthStarState.positionLens;
  const value=mode==='strength'?homeNumber(row.strength_index,0):'#'+(row.league_rank??'—');
  const detail=mode==='strength'?'Strength Index':'Rank';
  const count=row.team_count||homeStandings().length||12;
  const share=(Number(row.league_rank||count)-1)/Math.max(1,count-1);
  const band=share<=.2?'strong':share<=.7?'middle':'weak';
  return `<button type="button" class="home-position-pill ${band}" data-home-action="position" data-position="${homeEscape(row.position)}" aria-label="Open ${homeEscape(row.position)} position detail, ${homeEscape(detail)} ${homeEscape(value)}"><span>${homeEscape(row.position)}</span><b>${homeEscape(value)}</b><small>${homeEscape(detail)}</small></button>`;
}
function homeOutlookMetric(label,value,metric,kind='number'){
  const shown=kind==='percent'?homePercent(value,0):homeNumber(value,1);
  const style=kind==='percent'&&typeof value==='number'&&Number.isFinite(value)?` style="--home-ring:${Math.max(0,Math.min(100,value*100)).toFixed(1)}%"`:'';
  return `<button type="button" class="home-outlook-metric ${kind}" data-home-action="outlook" data-metric="${metric}" aria-label="Open League Race ${homeEscape(label)} detail"><span class="home-ring"${style}><b>${shown}</b></span><small>${homeEscape(label)}</small></button>`;
}
const HOME_READINESS_STEPS=7;
function homeReadinessSnapshot(){
  const context=state?.context||{},job=state?.intelligence?.job||null;
  const phases={
    queued:[1,'Preparing current intelligence…'],
    building_forecasts:[2,'Building projections…'],
    refreshing_state:[3,'Refreshing league state…'],
    running_simulation:[4,'Running season outlook…'],
    building_values:[5,'Building market values…'],
    attaching_results:[6,'Attaching current intelligence…'],
    completed:[7,'Intelligence current'],
  };
  if(job?.status==='failed'||job?.phase==='failed'){
    const prior=Number.isFinite(fsfflHomeNorthStarState.lastReadinessStep)?fsfflHomeNorthStarState.lastReadinessStep:1;
    return{step:Math.max(1,Math.min(HOME_READINESS_STEPS,prior)),total:HOME_READINESS_STEPS,label:'Intelligence refresh needs attention',failed:true,complete:false};
  }
  if(job&&phases[job.phase]){
    const [step,label]=phases[job.phase];
    fsfflHomeNorthStarState.lastReadinessStep=step;
    return{step,total:HOME_READINESS_STEPS,label,failed:false,complete:step===HOME_READINESS_STEPS};
  }
  let step=context?.league_id?1:0;
  if(context?.forecast_ready)step=Math.max(step,2);
  if(context?.simulation_ready)step=Math.max(step,4);
  if(context?.value_ready)step=Math.max(step,5);
  const complete=Boolean(context?.league_id&&context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);
  if(complete)step=HOME_READINESS_STEPS;
  fsfflHomeNorthStarState.lastReadinessStep=step;
  const label=complete?'Intelligence current':!context?.forecast_ready?'Building projections…':!context?.simulation_ready?'Running season outlook…':!context?.value_ready?'Building market values…':'Attaching current intelligence…';
  return{step,total:HOME_READINESS_STEPS,label,failed:false,complete};
}
function homeReadinessMarkup(){
  const status=homeReadinessSnapshot(),pct=status.total?Math.max(0,Math.min(100,(status.step/status.total)*100)):0;
  return `<div class="home-readiness-strip ${status.complete?'complete':''} ${status.failed?'failed':''}" role="status" aria-live="polite" style="--home-readiness:${pct.toFixed(1)}%"><span class="home-readiness-mark" aria-hidden="true">${status.complete?'✓':'●'}</span><strong>${status.step} / ${status.total}</strong><span class="home-readiness-copy">${homeEscape(status.label)}</span></div>`;
}
function homeReadinessHost(){
  let node=document.querySelector('#fsffl-sync-state');
  if(!node){
    const topbar=document.querySelector('.topbar');if(!topbar)return null;
    node=document.createElement('div');
    node.id='fsffl-sync-state';node.className='fsffl-sync-state';
    node.setAttribute('role','status');node.setAttribute('aria-live','polite');
    topbar.insertAdjacentElement('afterend',node);
  }
  if(!node.classList.contains('home-readiness-host')){
    fsfflHomeNorthStarState.syncSnapshot={
      state:node.dataset.state||null,
      html:node.innerHTML,
      hidden:node.hidden,
    };
    node.classList.add('home-readiness-host');
    node.dataset.homeReadiness='true';
  }
  node.innerHTML=homeReadinessMarkup();
  node.hidden=false;
  return node;
}
function homeReleaseReadinessHost(){
  const node=document.querySelector('#fsffl-sync-state.home-readiness-host');if(!node)return;
  node.classList.remove('home-readiness-host');delete node.dataset.homeReadiness;
  const latest=fsfflHomeNorthStarState.latestSyncState;
  if(latest?.state&&window.fsfflSyncState?.set){
    window.fsfflSyncState.set(latest.state,latest.message||null);
  }else{
    const snapshot=fsfflHomeNorthStarState.syncSnapshot;
    if(snapshot){node.innerHTML=snapshot.html||'';node.hidden=Boolean(snapshot.hidden);if(snapshot.state)node.dataset.state=snapshot.state}
  }
}
function homeRefreshReadinessStrip(){
  const host=homeReadinessHost();if(!host)return;
  const node=host.querySelector('.home-readiness-strip');if(!node)return;
  const status=homeReadinessSnapshot(),pct=status.total?Math.max(0,Math.min(100,(status.step/status.total)*100)):0;
  node.style.setProperty('--home-readiness',pct.toFixed(1)+'%');
  node.classList.toggle('complete',status.complete);node.classList.toggle('failed',status.failed);
  const mark=node.querySelector('.home-readiness-mark'),count=node.querySelector('strong'),copy=node.querySelector('.home-readiness-copy');
  if(mark)mark.textContent=status.complete?'✓':'●';
  if(count)count.textContent=`${status.step} / ${status.total}`;
  if(copy)copy.textContent=status.label;
}
function homeStopReadinessPolling(){
  if(fsfflHomeNorthStarState.readinessPollTimer){clearInterval(fsfflHomeNorthStarState.readinessPollTimer);fsfflHomeNorthStarState.readinessPollTimer=null}
  fsfflHomeNorthStarState.readinessPollAttempts=0;
}
async function homePollReadinessOnce(){
  if(fsfflHomeNorthStarState.readinessRequestInFlight)return;
  if(state?.route!=='league'||!state?.context?.league_id){homeStopReadinessPolling();return}
  fsfflHomeNorthStarState.readinessRequestInFlight=true;
  try{
    state.intelligence=await api('/api/intelligence/status');
    homeRefreshReadinessStrip();
    if(homeReadinessSnapshot().complete||homeReadinessSnapshot().failed)homeStopReadinessPolling();
  }catch(_error){
    homeRefreshReadinessStrip();
  }finally{
    fsfflHomeNorthStarState.readinessRequestInFlight=false;
  }
}
function homeStartReadinessPolling(){
  homeRefreshReadinessStrip();
  const status=homeReadinessSnapshot();
  if(status.complete||status.failed||!state?.context?.league_id){homeStopReadinessPolling();return}
  if(fsfflHomeNorthStarState.readinessPollTimer)return;
  fsfflHomeNorthStarState.readinessPollAttempts=0;
  void homePollReadinessOnce();
  fsfflHomeNorthStarState.readinessPollTimer=setInterval(()=>{
    fsfflHomeNorthStarState.readinessPollAttempts+=1;
    if(fsfflHomeNorthStarState.readinessPollAttempts>=36){homeStopReadinessPolling();return}
    void homePollReadinessOnce();
  },2500);
}
function homeLoadingMarkup(){
  return '<section class="home-north-star"><div class="home-loading"><i></i><strong>Building your command center</strong><span>Reading current governed team intelligence.</span></div></section>';
}
function homeUnavailableMarkup(message){
  return `<section class="home-north-star"><div class="home-unavailable"><p class="eyebrow">Home</p><h2>Current team intelligence is unavailable.</h2><p>${homeEscape(message||'Required governed evidence is not attached to this exact league State.')}</p></div></section>`;
}
function renderFsfflHomeNorthStar(){
  const container=document.querySelector('#home-attention');if(!container)return;
  if(!state?.context?.league_id){container.innerHTML='<section class="home-north-star"><div class="home-unavailable"><p class="eyebrow">Home</p><h2>Connect your league.</h2><p>Home becomes your personalized command center after canonical league State is loaded.</p><button type="button" class="primary-button" data-home-connect>Connect Sleeper League</button></div></section>';container.querySelector('[data-home-connect]')?.addEventListener('click',()=>document.querySelector('#connect-button')?.click());return}
  if(!state?.context?.team_id){container.innerHTML='<section class="home-north-star"><div class="home-unavailable"><p class="eyebrow">Home</p><h2>Choose the franchise you manage.</h2><p>Home only prioritizes evidence after a managed team is selected.</p></div></section>';return}
  if(fsfflHomeNorthStarState.loading&&!homePayload()){container.innerHTML=homeLoadingMarkup();return}
  if(fsfflHomeNorthStarState.error&&!homePayload()){container.innerHTML=homeUnavailableMarkup(fsfflHomeNorthStarState.error);return}
  const payload=homePayload(),view=homeView();if(!payload||!view){container.innerHTML=homeLoadingMarkup();return}

  const standing=homeStanding(),simulation=homeSimulation(),pressure=homePressurePoint(),fragility=homeFragility(),adjacent=homeAdjacentStandings(),positions=homePositionRows();
  const competitiveState=homeStateLabel(view.utility?.calculated_competitive_state);
  const simulationReady=payload.simulation?.status==='ready'&&simulation;
  const lens=fsfflHomeNorthStarState.positionLens;
  const pressureTitle=pressure?`${pressure.position} is your clearest roster pressure point`:'Position pressure point unavailable';
  const pressureMeta=pressure?`#${pressure.league_rank??'—'} of ${pressure.team_count||homeStandings().length||'—'} · Strength Index ${homeNumber(pressure.strength_index,0)}`:'Governed position-strength evidence is not available.';
  const expectedFinish=simulationReady?homeNumber(simulation.expected_finish,1):'—';
  const finishContext=simulationReady&&standing?`You’re #${standing.rank} now · projected finish ${expectedFinish}`:'Matching current Simulation unavailable';
  const exposureDetail=fragility?`${homeNumber(fragility.drop,1)} projected-point drop`:'Roster-resilience evidence unavailable';
  const around=adjacent.map(row=>`<span class="${row.team_id===homeManagedTeamId()?'managed':''}"><b>#${row.rank}</b><strong>${homeEscape(row.team_name)}</strong><small>${homeRecord(row)}</small></span>`).join('');

  container.innerHTML=`<section class="home-north-star">
    <button type="button" class="home-identity" data-home-action="franchise" aria-label="Open managed franchise overview">
      <span class="home-team-mark" aria-hidden="true">${homeEscape((view.display_name||'?').slice(0,1).toUpperCase())}</span>
      <span class="home-identity-copy"><strong>${homeEscape(view.display_name)}</strong><span>${homeRecord(standing)} · #${standing?.rank??'—'} of ${homeStandings().length||'—'}</span><small>${homeEscape(competitiveState)}</small></span><b aria-hidden="true">›</b>
    </button>

    <button type="button" class="home-pressure" data-home-action="pressure" data-position="${homeEscape(pressure?.position||'')}" ${pressure?'':'disabled'} aria-label="${pressure?'Explore '+homeEscape(pressure.position)+' options in Market':'Position pressure point unavailable'}">
      <span class="home-card-kicker">What matters right now</span>
      <div class="home-pressure-main"><span class="home-pressure-badge">${homeEscape(pressure?.position||'—')}</span><span><strong>${homeEscape(pressureTitle)}</strong><small>${homeEscape(pressureMeta)}</small></span><b aria-hidden="true">›</b></div>
      <span class="home-pressure-cta">${pressure?'Explore '+homeEscape(pressure.position)+' options →':'Unavailable'}</span>
    </button>

    <section class="home-card home-outlook"><div class="home-card-head"><span class="home-card-kicker">Season outlook · current Simulation</span><small>${simulationReady?Number(payload.simulation.simulation_count||0).toLocaleString()+' runs':'Unavailable'}</small></div><div class="home-outlook-grid">
      ${homeOutlookMetric('Projected final wins',simulationReady?simulation.expected_wins:null,'expected_wins')}
      ${homeOutlookMetric('Playoffs',simulationReady?simulation.playoff_probability:null,'playoff_probability','percent')}
      ${homeOutlookMetric('Championship',simulationReady?simulation.championship_probability:null,'championship_probability','percent')}
    </div></section>

    <section class="home-card home-roster-shape"><div class="home-card-head"><span class="home-card-kicker">Your roster at a glance</span><div class="home-lens-toggle" role="group" aria-label="Roster position lens"><button type="button" data-home-position-lens="rank" class="${lens==='rank'?'active':''}">Rank</button><button type="button" data-home-position-lens="strength" class="${lens==='strength'?'active':''}">Strength Index</button></div></div><div class="home-position-grid">${positions.map(homeCircle).join('')}</div></section>

    <section class="home-card home-secondary"><div class="home-card-head"><span class="home-card-kicker">Also worth knowing</span></div>
      <button type="button" class="home-secondary-row" data-home-action="exposure" data-position="${homeEscape(fragility?.position||'')}" data-player-id="${homeEscape(fragility?.playerId||'')}" ${fragility?'':'disabled'}><span class="home-secondary-icon exposure" aria-hidden="true">!</span><span><small>Largest single-player exposure</small><strong>${homeEscape(fragility?.label||'Unavailable')}</strong><em>${homeEscape(exposureDetail)}</em></span><b aria-hidden="true">›</b></button>
      <button type="button" class="home-secondary-row" data-home-action="expected-finish" ${simulationReady?'':'disabled'}><span class="home-secondary-icon outlook" aria-hidden="true">↗</span><span><small>Current outlook</small><strong>Expected finish: ${expectedFinish}</strong><em>${homeEscape(finishContext)}</em></span><b aria-hidden="true">›</b></button>
    </section>

    <button type="button" class="home-card home-around" data-home-action="league-context" aria-label="Open League Atlas current standings"><span class="home-card-kicker">Around the league</span><div class="home-around-row">${around||'<span><strong>Standings unavailable</strong></span>'}</div><small>Open current league context →</small></button>

  </section>`;
  homeWireActions(container);
  homeRefreshReadinessStrip();
}
async function loadFsfflHomeNorthStar({force=false}={}){
  const leagueId=state?.context?.league_id,teamId=state?.context?.team_id,stateId=state?.context?.state_id;
  if(!leagueId||!teamId){fsfflHomeNorthStarState.payload=null;fsfflHomeNorthStarState.error=null;fsfflHomeNorthStarState.requestKey=null;renderFsfflHomeNorthStar();return}
  const key=`${leagueId}|${teamId}|${stateId||''}`;
  if(!force&&fsfflHomeNorthStarState.payload&&fsfflHomeNorthStarState.requestKey===key){renderFsfflHomeNorthStar();return}
  if(fsfflHomeNorthStarState.loading&&fsfflHomeNorthStarState.requestKey===key)return;
  fsfflHomeNorthStarState.loading=true;fsfflHomeNorthStarState.error=null;fsfflHomeNorthStarState.requestKey=key;renderFsfflHomeNorthStar();
  try{
    const payload=await api('/api/home');
    if(fsfflHomeNorthStarState.requestKey!==key)return;
    if(payload?.league_state_id!==state?.context?.state_id||payload?.managed_team_id!==state?.context?.team_id)throw new Error('Home evidence does not match the current managed-team State.');
    fsfflHomeNorthStarState.payload=payload;
  }catch(error){
    if(fsfflHomeNorthStarState.requestKey===key){fsfflHomeNorthStarState.payload=null;fsfflHomeNorthStarState.error=error?.message||String(error)}
  }finally{
    if(fsfflHomeNorthStarState.requestKey===key){fsfflHomeNorthStarState.loading=false;renderFsfflHomeNorthStar()}
  }
}
function installFsfflHomeExperience(){
  const leagueScreen=document.querySelector('#league-screen');if(!leagueScreen)return;
  leagueScreen.classList.add('fsffl-home-north-star-active');
  const hero=leagueScreen.querySelector('.hero-row');if(hero)hero.hidden=true;
  leagueScreen.querySelector('.metric-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.dashboard-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.roster-panel')?.setAttribute('hidden','');
  document.querySelector('#home-quick-actions')?.remove();
  const runtime=document.querySelector('#runtime-status');if(runtime)runtime.hidden=true;
  let attention=document.querySelector('#home-attention');if(!attention){attention=document.createElement('section');attention.id='home-attention';attention.className='home-attention';if(hero)hero.insertAdjacentElement('afterend',attention);else leagueScreen.prepend(attention)}
  renderFsfflHomeNorthStar();
  void loadFsfflHomeNorthStar();
  homeReadinessHost();
  homeStartReadinessPolling();
  if(!document.querySelector('#fsffl-home-north-star-style')){const style=document.createElement('style');style.id='fsffl-home-north-star-style';style.textContent=`
.home-attention{max-width:720px;margin:0 auto;padding:8px 0 24px}.home-north-star{display:grid;gap:9px;width:100%;max-width:720px;margin:0 auto}.home-north-star button{font:inherit}.home-identity,.home-pressure,.home-card{width:100%;border:1px solid var(--line);border-radius:16px;background:#091522;color:var(--text);box-shadow:0 10px 28px rgba(0,0,0,.15)}.home-identity{display:grid;grid-template-columns:52px minmax(0,1fr) 24px;gap:11px;align-items:center;padding:11px;text-align:left}.home-team-mark{width:50px;height:50px;border-radius:50%;display:grid;place-items:center;border:2px solid #2a789d;background:linear-gradient(145deg,#12304a,#07111d);font-weight:900;font-size:20px;color:#7dd3fc}.home-identity-copy{display:grid;gap:2px}.home-identity-copy strong{font-size:17px}.home-identity-copy span{font-size:12px}.home-identity-copy small{color:var(--muted);font-size:11px;text-transform:capitalize}.home-identity>b,.home-secondary-row>b,.home-pressure-main>b{font-size:28px;font-weight:300;color:#6d94ad}.home-pressure{display:grid;gap:9px;padding:11px;text-align:left;border-color:#7e294b;background:linear-gradient(145deg,rgba(102,23,55,.72),rgba(26,13,31,.96))}.home-card-kicker{font-size:9px;letter-spacing:.14em;text-transform:uppercase;font-weight:900;color:#9bcbe7}.home-pressure .home-card-kicker{color:#ffc0d3}.home-pressure-main{display:grid;grid-template-columns:58px minmax(0,1fr) 22px;gap:10px;align-items:center}.home-pressure-badge{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;border:5px solid #ef476f;background:#24101b;font-size:18px;font-weight:900}.home-pressure-main>span:nth-child(2){display:grid;gap:3px}.home-pressure-main strong{font-size:17px;line-height:1.15}.home-pressure-main small{font-size:11px;color:#d9a8b9}.home-pressure-cta{display:block;padding:8px 10px;border-radius:8px;background:#a72c55;color:white;text-align:center;font-size:11px;font-weight:800}.home-card{padding:11px}.home-card-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.home-card-head>small{font-size:9px;color:var(--muted)}.home-outlook-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}.home-outlook-metric{border:0;background:transparent;color:var(--text);display:grid;justify-items:center;gap:5px;min-height:94px;padding:4px}.home-outlook-metric small{text-align:center;color:#a9bdd0;font-size:9px;line-height:1.2}.home-ring{--home-ring:100%;width:62px;height:62px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#35d399 var(--home-ring),#173247 0);position:relative}.home-ring:after{content:'';position:absolute;inset:5px;border-radius:50%;background:#091522}.home-outlook-metric.number .home-ring{background:#173247;border:5px solid #36b4d7}.home-outlook-metric.number .home-ring:after{inset:0}.home-ring b{position:relative;z-index:1;font-size:16px}.home-lens-toggle{display:grid;grid-template-columns:1fr 1fr;gap:2px;padding:2px;border:1px solid var(--line);border-radius:999px;background:#06111f}.home-lens-toggle button{min-height:28px;border:0;border-radius:999px;background:transparent;color:var(--muted);padding:4px 9px;font-size:8px;font-weight:800}.home-lens-toggle button.active{background:#123957;color:#eaf7ff}.home-position-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-top:9px}.home-position-pill{border:0;background:transparent;color:var(--text);display:grid;justify-items:center;gap:3px;min-height:83px;padding:2px}.home-position-pill>span{font-size:9px;color:#a9bdd0}.home-position-pill>b{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;border:3px solid #e5b84f;background:rgba(229,184,79,.14);font-size:12px}.home-position-pill.strong>b{border-color:#35d399;background:rgba(53,211,153,.16)}.home-position-pill.weak>b{border-color:#ef6478;background:rgba(239,100,120,.15)}.home-position-pill small{font-size:7px;color:var(--muted)}.home-secondary{padding:8px 11px 5px}.home-secondary-row{width:100%;display:grid;grid-template-columns:38px minmax(0,1fr) 20px;gap:9px;align-items:center;border:0;border-top:1px solid var(--line);background:transparent;color:var(--text);padding:9px 0;text-align:left}.home-secondary-row:first-of-type{margin-top:7px}.home-secondary-row>span:nth-child(2){display:grid;gap:2px}.home-secondary-row small,.home-secondary-row em{font-size:9px;color:var(--muted);font-style:normal}.home-secondary-row strong{font-size:13px}.home-secondary-icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#2a1638;color:#d8b4fe;font-weight:900}.home-secondary-icon.outlook{background:#123452;color:#7dd3fc}.home-around{text-align:left;display:grid;gap:8px}.home-around-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.home-around-row>span{display:grid;gap:1px;border:1px solid var(--line);border-radius:9px;padding:7px;background:#08111d}.home-around-row>span.managed{border-color:#38bdf8;background:#0b2031}.home-around-row b{font-size:10px;color:#8fb2c9}.home-around-row strong{font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.home-around-row small,.home-around>small{font-size:8px;color:var(--muted)}.fsffl-sync-state.home-readiness-host{margin:8px 18px 0!important;min-height:32px!important;padding:0 11px!important;border:1px solid var(--line)!important;border-radius:10px!important;background:#0a1120!important;display:block!important}.home-readiness-strip{--home-readiness:0%;position:relative;display:grid;grid-template-columns:14px auto minmax(0,1fr);align-items:center;gap:7px;min-height:31px;padding:6px 0 7px;color:#8fa8bd;font-size:9px;line-height:1.1;overflow:hidden}.home-readiness-strip:after{content:'';position:absolute;left:0;bottom:0;width:var(--home-readiness);height:2px;background:#38bdf8;transition:width .25s ease}.home-readiness-strip.complete:after{background:#35d399}.home-readiness-strip.failed:after{background:#ef6478}.home-readiness-mark{font-size:8px;color:#38bdf8}.home-readiness-strip.complete .home-readiness-mark{color:#35d399}.home-readiness-strip.failed .home-readiness-mark{color:#ef6478}.home-readiness-strip strong{font-size:9px;color:#c7d7e5;white-space:nowrap}.home-readiness-copy{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.home-loading,.home-unavailable{border:1px solid var(--line);border-radius:16px;background:#091522;padding:18px}.home-loading{display:grid;gap:5px}.home-loading i{width:18px;height:18px;border:2px solid #27445c;border-top-color:#38bdf8;border-radius:50%;animation:home-spin .8s linear infinite}.home-unavailable h2{margin:3px 0 6px}.home-unavailable p{color:var(--muted)}.home-north-star button:not(:disabled){cursor:pointer}.home-north-star button:disabled{opacity:.55}@keyframes home-spin{to{transform:rotate(360deg)}}
@media(max-width:760px){.fsffl-sync-state.home-readiness-host{margin:7px 10px 0!important;padding:0 9px!important}.home-attention{padding:4px 10px calc(76px + env(safe-area-inset-bottom,0px));max-width:none}.home-north-star{gap:8px}.home-identity,.home-pressure,.home-card{border-radius:13px}.home-identity{min-height:74px}.home-pressure{min-height:136px}.home-outlook-grid{gap:3px}.home-outlook-metric{min-height:90px}.home-card-head{align-items:flex-start}.home-roster-shape .home-card-head{display:grid;grid-template-columns:1fr auto}.home-around-row{gap:4px}.home-north-star button{touch-action:manipulation}.home-identity,.home-pressure,.home-secondary-row,.home-around,.home-position-pill,.home-outlook-metric{min-height:44px}}
@media(min-width:761px){.home-attention{padding-top:14px}.home-north-star{grid-template-columns:1fr 1fr}.home-identity,.home-pressure,.home-outlook,.home-roster-shape,.home-secondary,.home-around{grid-column:1/-1}.home-outlook-grid{max-width:520px}.home-position-grid{max-width:560px}}
`;document.head.appendChild(style)}
}
window.renderFsfflHomeNorthStar=renderFsfflHomeNorthStar;
window.loadFsfflHomeNorthStar=loadFsfflHomeNorthStar;
window.installFsfflHomeExperience=installFsfflHomeExperience;
window.fsfflHomeReadinessRouteChanged=route=>{
  if(route==='league'){homeReadinessHost();homeRefreshReadinessStrip();homeStartReadinessPolling()}
  else{homeStopReadinessPolling();homeReleaseReadinessHost()}
};
window.addEventListener('fsffl:sync-state',event=>{
  if(event.detail?.state)fsfflHomeNorthStarState.latestSyncState={state:event.detail.state,message:event.detail.message||null};
  if(state?.route==='league')setTimeout(()=>{homeReadinessHost();homeRefreshReadinessStrip()},0);
});
window.addEventListener('fsffl:intelligence-status-updated',event=>{if(event.detail)state.intelligence=event.detail;homeRefreshReadinessStrip();homeStartReadinessPolling()});
window.addEventListener('fsffl:product-context-updated',()=>{fsfflHomeNorthStarState.payload=null;fsfflHomeNorthStarState.error=null;homeStopReadinessPolling();setTimeout(()=>{void loadFsfflHomeNorthStar({force:true});homeStartReadinessPolling()},0)});
