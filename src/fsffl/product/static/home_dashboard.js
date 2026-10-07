/* FSFFL NEXT Home North Star.
 * Presentation only. Home summarizes governed evidence already owned by State,
 * Team Utility and the exact current Simulation. Legacy position-strength rows are
 * intentionally not presented as Current authority while Home consolidation is pending.
 * It does not launch Opportunity Search, Decision, Value or new Simulation work.
 */
const fsfflHomeNorthStarState={
  payload:null,
  loading:false,
  error:null,
  requestKey:null,
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
  if(action==='outlook')return{route:'league_comparison',section:'overview',teamId,metric:button.dataset.metric||null,source:'home-outlook'};
  if(action==='exposure')return{route:'league_comparison',section:'positions',teamId,position:button.dataset.position||null,playerId:button.dataset.playerId||null,fragilityDriver:true,source:'home-exposure'};
  if(action==='expected-finish')return{route:'league_comparison',section:'overview',teamId,metric:'expected_finish',source:'home-expected-finish'};
  if(action==='league-context')return{route:'league_comparison',section:'overview',teamId,source:'home-league-context'};
  return null;
}
function homeWireActions(root){
  root.querySelectorAll('[data-home-action]').forEach(button=>button.addEventListener('click',()=>{
    const intent=homeIntentFromButton(button);if(intent)homeNavigate(intent);
  }));
}
function homeOutlookMetric(label,value,metric,kind='number'){
  const shown=kind==='percent'?homePercent(value,0):homeNumber(value,1);
  const style=kind==='percent'&&typeof value==='number'&&Number.isFinite(value)?` style="--home-ring:${Math.max(0,Math.min(100,value*100)).toFixed(1)}%"`:'';
  return `<button type="button" class="home-outlook-metric ${kind}" data-home-action="outlook" data-metric="${metric}" aria-label="Open League Race ${homeEscape(label)} detail"><span class="home-ring"${style}><b>${shown}</b></span><small>${homeEscape(label)}</small></button>`;
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

  const standing=homeStanding(),simulation=homeSimulation(),fragility=homeFragility(),adjacent=homeAdjacentStandings();
  const freshness=payload.intelligence_freshness||{};
  const staleBanner=freshness.stale?'<aside class="home-last-good-status" role="status"><strong>State current · last-good intelligence</strong><span>Derived fields as of '+homeEscape(freshness.served_as_of||'the last-good snapshot')+'.</span></aside>':'';
  const competitiveState=homeStateLabel(view.utility?.calculated_competitive_state);
  const simulationReady=payload.simulation?.status==='ready'&&simulation;
  // Home does not derive or display Current position ranks here. League Atlas owns
  // the accepted lineup-slot Current contract; Home consolidation is a separate decision.
  const expectedFinish=simulationReady?homeNumber(simulation.expected_finish,1):'—';
  const finishContext=simulationReady&&standing?`You’re #${standing.rank} now · projected finish ${expectedFinish}`:'Matching current Simulation unavailable';
  const exposureDetail=fragility?`${homeNumber(fragility.drop,1)} projected-point drop`:'Roster-resilience evidence unavailable';
  const around=adjacent.map(row=>`<span class="${row.team_id===homeManagedTeamId()?'managed':''}"><b>#${row.rank}</b><strong>${homeEscape(row.team_name)}</strong><small>${homeRecord(row)}</small></span>`).join('');

  container.innerHTML=`<section class="home-north-star">
    ${staleBanner}
    <button type="button" class="home-identity" data-home-action="franchise" aria-label="Open managed franchise overview">
      <span class="home-team-mark" aria-hidden="true">${homeEscape((view.display_name||'?').slice(0,1).toUpperCase())}</span>
      <span class="home-identity-copy"><strong>${homeEscape(view.display_name)}</strong><span>${homeRecord(standing)} · #${standing?.rank??'—'} of ${homeStandings().length||'—'}</span><small>${homeEscape(competitiveState)}</small></span><b aria-hidden="true">›</b>
    </button>

    <section class="home-card home-outlook"><div class="home-card-head"><span class="home-card-kicker">Season outlook · current Simulation</span><small>${simulationReady?Number(payload.simulation.simulation_count||0).toLocaleString()+' runs':'Unavailable'}</small></div><div class="home-outlook-grid">
      ${homeOutlookMetric('Projected final wins',simulationReady?simulation.expected_wins:null,'expected_wins')}
      ${homeOutlookMetric('Playoffs',simulationReady?simulation.playoff_probability:null,'playoff_probability','percent')}
      ${homeOutlookMetric('Championship',simulationReady?simulation.championship_probability:null,'championship_probability','percent')}
    </div></section>

    <section class="home-card home-secondary"><div class="home-card-head"><span class="home-card-kicker">Also worth knowing</span></div>
      <button type="button" class="home-secondary-row" data-home-action="exposure" data-position="${homeEscape(fragility?.position||'')}" data-player-id="${homeEscape(fragility?.playerId||'')}" ${fragility?'':'disabled'}><span class="home-secondary-icon exposure" aria-hidden="true">!</span><span><small>Largest single-player exposure</small><strong>${homeEscape(fragility?.label||'Unavailable')}</strong><em>${homeEscape(exposureDetail)}</em></span><b aria-hidden="true">›</b></button>
      <button type="button" class="home-secondary-row" data-home-action="expected-finish" ${simulationReady?'':'disabled'}><span class="home-secondary-icon outlook" aria-hidden="true">↗</span><span><small>Current outlook</small><strong>Expected finish: ${expectedFinish}</strong><em>${homeEscape(finishContext)}</em></span><b aria-hidden="true">›</b></button>
    </section>

    <button type="button" class="home-card home-around" data-home-action="league-context" aria-label="Open League Atlas current standings"><span class="home-card-kicker">Around the league</span><div class="home-around-row">${around||'<span><strong>Standings unavailable</strong></span>'}</div><small>Open current league context →</small></button>

  </section>`;
  homeWireActions(container);
}
function homePayloadMatchesContext(payload,context){
  const leagueId=context?.leagueId,teamId=context?.teamId,stateId=context?.stateId;
  if(!payload||!leagueId||!teamId||!stateId)return false;
  if(payload.league_id!==leagueId||payload.managed_team_id!==teamId||payload.team_view?.team_id!==teamId)return false;
  const freshness=payload.intelligence_freshness||{},continuity=payload.presentation_continuity||{};
  if(payload.league_state_id===stateId){
    if(freshness.target_state_id&&freshness.target_state_id!==stateId)return false;
    if(freshness.served_state_id&&freshness.served_state_id!==stateId)return false;
    if(freshness.target_league_id&&freshness.target_league_id!==leagueId)return false;
    if(freshness.served_league_id&&freshness.served_league_id!==leagueId)return false;
    if(continuity.mode&&continuity.mode!=='published')return false;
    if(continuity.target_league_id&&continuity.target_league_id!==leagueId)return false;
    if(continuity.served_league_id&&continuity.served_league_id!==leagueId)return false;
    if(continuity.target_league_state_id&&continuity.target_league_state_id!==stateId)return false;
    if(continuity.served_league_state_id&&continuity.served_league_state_id!==stateId)return false;
    const generation=payload.publication_generation_id;
    if(generation&&freshness.publication_generation_id&&generation!==freshness.publication_generation_id)return false;
    if(generation&&continuity.publication_generation_id&&generation!==continuity.publication_generation_id)return false;
    if(generation&&continuity.promotion_id&&generation!==continuity.promotion_id)return false;
    return true;
  }
  const generation=payload.publication_generation_id;
  return freshness.status==='stale_last_good'
    &&freshness.stale===true
    &&freshness.target_state_id===stateId
    &&freshness.target_league_id===leagueId
    &&freshness.served_state_id===payload.league_state_id
    &&freshness.served_league_id===leagueId
    &&continuity.mode==='stale_last_good'
    &&continuity.target_league_id===leagueId
    &&continuity.served_league_id===leagueId
    &&continuity.target_league_state_id===stateId
    &&continuity.served_league_state_id===payload.league_state_id
    &&typeof generation==='string'&&generation.length>0
    &&generation===freshness.publication_generation_id
    &&generation===continuity.publication_generation_id
    &&generation===continuity.promotion_id;
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
    if(!homePayloadMatchesContext(payload,{leagueId,teamId,stateId}))throw new Error('Home evidence does not match the current managed-team State.');
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
  if(!document.querySelector('#fsffl-home-north-star-style')){const style=document.createElement('style');style.id='fsffl-home-north-star-style';style.textContent=`
.home-attention{max-width:720px;margin:0 auto;padding:8px 0 24px}.home-north-star{display:grid;gap:9px;width:100%;max-width:720px;margin:0 auto}.home-last-good-status{display:flex;align-items:center;gap:7px;min-height:28px;padding:5px 8px;border:1px solid #765526;border-radius:8px;background:rgba(155,106,42,.07);color:#d7bc8c;font-size:9px;line-height:1.25}.home-last-good-status strong{white-space:nowrap}.home-last-good-status span{color:#bda77f;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.home-north-star button{font:inherit}.home-identity,.home-card{width:100%;border:1px solid var(--line);border-radius:16px;background:#091522;color:var(--text);box-shadow:0 10px 28px rgba(0,0,0,.15)}.home-identity{display:grid;grid-template-columns:52px minmax(0,1fr) 24px;gap:11px;align-items:center;padding:11px;text-align:left}.home-team-mark{width:50px;height:50px;border-radius:50%;display:grid;place-items:center;border:2px solid #2a789d;background:linear-gradient(145deg,#12304a,#07111d);font-weight:900;font-size:20px;color:#7dd3fc}.home-identity-copy{display:grid;gap:2px}.home-identity-copy strong{font-size:17px}.home-identity-copy span{font-size:12px}.home-identity-copy small{color:var(--muted);font-size:11px;text-transform:capitalize}.home-identity>b,.home-secondary-row>b{font-size:28px;font-weight:300;color:#6d94ad}.home-card-kicker{font-size:9px;letter-spacing:.14em;text-transform:uppercase;font-weight:900;color:#9bcbe7}.home-card{padding:11px}.home-card-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.home-card-head>small{font-size:9px;color:var(--muted)}.home-outlook-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}.home-outlook-metric{border:0;background:transparent;color:var(--text);display:grid;justify-items:center;gap:5px;min-height:94px;padding:4px}.home-outlook-metric small{text-align:center;color:#a9bdd0;font-size:9px;line-height:1.2}.home-ring{--home-ring:100%;width:62px;height:62px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#35d399 var(--home-ring),#173247 0);position:relative}.home-ring:after{content:'';position:absolute;inset:5px;border-radius:50%;background:#091522}.home-outlook-metric.number .home-ring{background:#173247;border:5px solid #36b4d7}.home-outlook-metric.number .home-ring:after{inset:0}.home-ring b{position:relative;z-index:1;font-size:16px}.home-secondary{padding:8px 11px 5px}.home-secondary-row{width:100%;display:grid;grid-template-columns:38px minmax(0,1fr) 20px;gap:9px;align-items:center;border:0;border-top:1px solid var(--line);background:transparent;color:var(--text);padding:9px 0;text-align:left}.home-secondary-row:first-of-type{margin-top:7px}.home-secondary-row>span:nth-child(2){display:grid;gap:2px}.home-secondary-row small,.home-secondary-row em{font-size:9px;color:var(--muted);font-style:normal}.home-secondary-row strong{font-size:13px}.home-secondary-icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#2a1638;color:#d8b4fe;font-weight:900}.home-secondary-icon.outlook{background:#123452;color:#7dd3fc}.home-around{text-align:left;display:grid;gap:8px}.home-around-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.home-around-row>span{display:grid;gap:1px;border:1px solid var(--line);border-radius:9px;padding:7px;background:#08111d}.home-around-row>span.managed{border-color:#38bdf8;background:#0b2031}.home-around-row b{font-size:10px;color:#8fb2c9}.home-around-row strong{font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.home-around-row small,.home-around>small{font-size:8px;color:var(--muted)}.home-loading,.home-unavailable{border:1px solid var(--line);border-radius:16px;background:#091522;padding:18px}.home-loading{display:grid;gap:5px}.home-loading i{width:18px;height:18px;border:2px solid #27445c;border-top-color:#38bdf8;border-radius:50%;animation:home-spin .8s linear infinite}.home-unavailable h2{margin:3px 0 6px}.home-unavailable p{color:var(--muted)}.home-north-star button:not(:disabled){cursor:pointer}.home-north-star button:disabled{opacity:.55}@keyframes home-spin{to{transform:rotate(360deg)}}
@media(max-width:760px){.home-attention{padding:4px 10px calc(76px + env(safe-area-inset-bottom,0px));max-width:none}.home-north-star{gap:8px}.home-identity,.home-card{border-radius:13px}.home-identity{min-height:74px}.home-outlook-grid{gap:3px}.home-outlook-metric{min-height:90px}.home-card-head{align-items:flex-start}.home-around-row{gap:4px}.home-north-star button{touch-action:manipulation}.home-identity,.home-secondary-row,.home-around,.home-outlook-metric{min-height:44px}}
@media(min-width:761px){.home-attention{padding-top:14px}.home-north-star{grid-template-columns:1fr 1fr}.home-identity,.home-outlook,.home-secondary,.home-around{grid-column:1/-1}.home-outlook-grid{max-width:520px}}
`;document.head.appendChild(style)}
}
window.renderFsfflHomeNorthStar=renderFsfflHomeNorthStar;
window.loadFsfflHomeNorthStar=loadFsfflHomeNorthStar;
window.installFsfflHomeExperience=installFsfflHomeExperience;
window.addEventListener('fsffl:product-context-updated',()=>{fsfflHomeNorthStarState.payload=null;fsfflHomeNorthStarState.error=null;setTimeout(()=>{void loadFsfflHomeNorthStar({force:true})},0)});
