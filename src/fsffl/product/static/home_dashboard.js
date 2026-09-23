/* FSFFL NEXT Home North Star.
 * Presentation-owned command center. Home summarizes existing governed evidence
 * and never launches Search, Decision, Value, or a new Simulation merely to render.
 */
let fsfflHomeRenderHookInstalled=false;
const fsfflHomeState={
  summary:null,
  loading:false,
  error:null,
  positionLens:'rank',
  contextKey:null,
  loadMs:null,
};

function homeEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function homeNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function homePercent(value){return typeof value==='number'&&Number.isFinite(value)?Math.round(value*100)+'%':'—'}
function homeWords(value){return String(value||'').replaceAll('_',' ')}
function homeStateLabel(value){return value&&value!=='unknown'?homeWords(value):'Unclassified'}
function homeContextKey(){return [state?.context?.league_id||'',state?.context?.team_id||'',state?.context?.state_id||''].join('|')}
function homeRecord(row){if(!row)return'—';return row.ties?row.wins+'-'+row.losses+'-'+row.ties:row.wins+'-'+row.losses}
function homePositions(view){const order={QB:0,RB:1,WR:2,TE:3};return(view?.position_strengths||[]).filter(row=>Object.hasOwn(order,row.position)&&typeof row?.strength_index==='number'&&Number.isFinite(row.strength_index)).sort((a,b)=>order[a.position]-order[b.position])}
function homeWeakestPosition(view){
  const order={QB:0,RB:1,WR:2,TE:3},rows=homePositions(view);
  if(!rows.length)return null;
  return [...rows].sort((a,b)=>{
    const ar=typeof a.league_rank==='number'?a.league_rank:-1,br=typeof b.league_rank==='number'?b.league_rank:-1;
    if(ar!==br)return br-ar;
    const ai=typeof a.strength_index==='number'?a.strength_index:Number.POSITIVE_INFINITY,bi=typeof b.strength_index==='number'?b.strength_index:Number.POSITIVE_INFINITY;
    if(ai!==bi)return ai-bi;
    return order[a.position]-order[b.position];
  })[0];
}
function homeStrengthBand(row){if(!row)return'missing';const count=row.team_count||12,rank=row.league_rank;if(typeof rank!=='number')return'missing';const share=(rank-1)/Math.max(1,count-1);return share<=.2?'elite':share<=.42?'strong':share<=.7?'neutral':'weak'}
function homeDriver(view){
  const resilience=view?.utility?.roster_resilience,ids=resilience?.largest_single_player_lineup_drop_player_ids||[];
  const players=ids.map(id=>(view?.players||[]).find(player=>player.player_id===id)).filter(Boolean);
  return{resilience,players,primary:players[0]||null};
}
function homeSummary(){return fsfflHomeState.summary||{}}
function homeStanding(){return homeSummary().managed_standing||null}
function homeSimulation(){return homeSummary().simulation?.team||null}
function homeSimulationReady(){return homeSummary().simulation?.status==='ready'&&Boolean(homeSimulation())}
function homeNavigate(intent){if(typeof window.fsfflNavigate==='function')window.fsfflNavigate(intent);else if(typeof setRoute==='function')setRoute(intent.route)}
function homeIntentButton(label,intent,body,className=''){
  return '<button type="button" class="'+className+'" data-home-intent="'+homeEscape(JSON.stringify(intent))+'" aria-label="'+homeEscape(label)+'">'+body+'</button>';
}
function homeRing(label,value,display,intent,tone=''){
  const pct=typeof value==='number'&&Number.isFinite(value)?Math.max(0,Math.min(100,Math.round(value*100))):null;
  const style=pct==null?'':(' style="--home-ring-pct:'+pct+'"');
  const body='<span class="home-ring-visual '+tone+'"'+style+'><b>'+homeEscape(display)+'</b></span><span class="home-ring-label">'+homeEscape(label)+'</span>';
  return homeIntentButton(label+' — '+display,intent,body,'home-outlook-metric');
}
function homePositionPill(row,teamId){
  const mode=fsfflHomeState.positionLens,value=mode==='strength'?homeNumber(row?.strength_index,0):(typeof row?.league_rank==='number'?'#'+row.league_rank:'—');
  const intent={route:'league_comparison',section:'positions',teamId,position:row?.position||null};
  const body='<span>'+homeEscape(row?.position||'—')+'</span><b class="'+homeStrengthBand(row)+'">'+homeEscape(value)+'</b>';
  return homeIntentButton((row?.position||'Position')+' detail — '+value,intent,body,'home-position-pill');
}
function homeAroundLeague(){
  const rows=homeSummary().around_the_league||[],managed=homeSummary().managed_team_id;
  if(!rows.length)return'<p class="home-unavailable">Current standings context is unavailable.</p>';
  return '<div class="home-around-list">'+rows.map(row=>'<div class="home-around-row '+(row.team_id===managed?'managed':'')+'"><b>#'+row.rank+'</b><span><strong>'+homeEscape(row.team_name)+'</strong><small>'+homeEscape(homeRecord(row))+'</small></span><em>'+homeNumber(row.points_for,1)+' PF</em></div>').join('')+'</div>';
}
function homeEvidenceDetails(){
  const summary=homeSummary(),count=summary.simulation?.simulation_count;
  return '<details class="home-evidence"><summary>Evidence & definitions</summary><div><p><strong>Current State:</strong> '+homeEscape(String(summary.league_state_id||state?.context?.state_id||'unavailable').slice(0,14))+'…</p><p><strong>Simulation:</strong> '+(count?Number(count).toLocaleString()+' governed runs already attached to this exact State':'unavailable for this exact State')+'. Home does not launch a new Simulation.</p><p><strong>Position strength:</strong> the same League Atlas optimized-starter evidence; Strength Index 100 = league-average optimized starter production.</p><p><strong>Pressure point:</strong> weakest QB/RB/WR/TE within that single comparable position-strength family. Home does not rank unrelated evidence families against one another.</p></div></details>';
}
function homeLoadingMarkup(){
  return '<div class="home-command-loading"><i></i><strong>Reading your current team context…</strong><span>Home is attaching existing State, Team Utility and Simulation evidence without launching downstream Search.</span></div>';
}
function homeUnavailableMarkup(message){
  return '<div class="home-command-unavailable"><p class="eyebrow">Home</p><h2>Current command-center evidence is unavailable.</h2><p>'+homeEscape(message||'The governed runtime has not attached enough evidence yet.')+'</p></div>';
}

function renderFsfflHomeAttention(view=state?.teamView){
  const container=document.querySelector('#home-attention');if(!container)return;
  if(!state?.context?.league_id){
    container.innerHTML='<div class="home-onboarding"><p class="eyebrow">FSFFL NEXT</p><h2>Connect a league to activate Home.</h2><p>Home will summarize the governed signals that matter to the franchise you manage and route you directly to the authoritative detail.</p><button type="button" class="primary-button" data-home-connect>Connect Sleeper League</button></div>';
    container.querySelector('[data-home-connect]')?.addEventListener('click',()=>document.querySelector('#connect-button')?.click());return;
  }
  if(!state?.context?.team_id){
    container.innerHTML='<div class="home-onboarding"><p class="eyebrow">FSFFL NEXT</p><h2>Choose the franchise you manage.</h2><p>Select a team above to personalize the command center.</p></div>';return;
  }
  if(!view||fsfflHomeState.loading&&!fsfflHomeState.summary){container.innerHTML=homeLoadingMarkup();return}
  const summary=homeSummary();
  if(fsfflHomeState.error&&!summary.managed_standing){
    container.innerHTML=homeUnavailableMarkup(fsfflHomeState.error);return;
  }

  const standing=homeStanding(),simulation=homeSimulation(),teamId=state.context.team_id;
  const stateLabel=homeStateLabel(view?.utility?.calculated_competitive_state||simulation?.competitive_state);
  const teamCount=(standing?.team_count||state?.context?.teams?.length||12);
  const weakest=homeWeakestPosition(view),positions=homePositions(view);
  const driver=homeDriver(view),drop=driver.resilience?.largest_single_player_lineup_drop;
  const driverNames=driver.players.length?driver.players.map(player=>player.full_name).join(' / '):'Driver unavailable';
  const expectedFinish=homeSimulationReady()?homeNumber(simulation.expected_finish,1):'—';
  const pressureBody=weakest
    ?'<div class="home-pressure-main"><span class="home-pressure-circle '+homeStrengthBand(weakest)+'">'+homeEscape(weakest.position)+'</span><div><p class="eyebrow">What matters right now</p><h2>'+homeEscape(weakest.position)+' is your clearest roster pressure point</h2><p>#'+homeEscape(weakest.league_rank)+' of '+homeEscape(weakest.team_count||teamCount)+' · Strength Index '+homeNumber(weakest.strength_index,0)+'</p></div></div><span class="home-pressure-cta">Explore '+homeEscape(weakest.position)+' options <b>→</b></span>'
    :'<div class="home-pressure-main"><span class="home-pressure-circle missing">—</span><div><p class="eyebrow">What matters right now</p><h2>Position-strength evidence unavailable</h2><p>Home will not derive a substitute from Market Value or raw projections.</p></div></div>';

  const identity=homeIntentButton(
    'Open '+view.display_name+' Franchise',
    {route:'my_team',teamId},
    '<span class="home-team-mark">'+homeEscape((view.display_name||'?').slice(0,2).toUpperCase())+'</span><span class="home-identity-copy"><strong>'+homeEscape(view.display_name)+'</strong><small>'+homeEscape(homeRecord(standing))+(standing?' · #'+standing.rank+' of '+teamCount:'')+'</small><em>'+homeEscape(stateLabel)+'</em></span><b aria-hidden="true">›</b>',
    'home-identity'
  );
  const pressure=homeIntentButton(
    weakest?'Explore '+weakest.position+' options in Market':'Position-strength evidence unavailable',
    weakest?{route:'opportunities',teamId,position:weakest.position,source:'home-pressure'}:{route:'league_comparison',section:'positions',teamId},
    pressureBody,
    'home-pressure '+(weakest?'':'unavailable')
  );

  const simCount=summary.simulation?.simulation_count;
  const outlook=homeSimulationReady()
    ?'<div class="home-outlook-grid">'
      +homeRing('Projected final wins',null,homeNumber(simulation.expected_wins,1),{route:'league_comparison',section:'overview',teamId,metric:'expected_wins'},'wins')
      +homeRing('Playoffs',simulation.playoff_probability,homePercent(simulation.playoff_probability),{route:'league_comparison',section:'overview',teamId,metric:'playoff_probability'},'playoffs')
      +homeRing('Championship',simulation.championship_probability,homePercent(simulation.championship_probability),{route:'league_comparison',section:'overview',teamId,metric:'championship_probability'},'championship')
      +'</div><small class="home-section-note">'+(simCount?Number(simCount).toLocaleString()+' current-State simulations':'Current governed Simulation')+'</small>'
    :'<p class="home-unavailable">Current Simulation is unavailable for this exact State. Home will not reuse stale probabilities.</p>';

  const roster=positions.length===4
    ?'<div class="home-position-grid">'+positions.map(row=>homePositionPill(row,teamId)).join('')+'</div>'
    :'<p class="home-unavailable">Complete QB/RB/WR/TE position-strength evidence is unavailable.</p>';

  const exposureIntent=driver.primary?{route:'league_comparison',section:'positions',teamId,position:driver.primary.position,playerId:driver.primary.player_id,source:'home-fragility'}:{route:'league_comparison',section:'positions',teamId};
  const exposureValue=typeof drop==='number'?homeNumber(drop,1)+' projected-point drop':'Unavailable';
  const exposure=homeIntentButton(
    'Open largest single-player exposure detail',
    exposureIntent,
    '<span class="home-secondary-icon">◉</span><span><small>Largest single-player exposure</small><strong>'+homeEscape(driverNames)+'</strong><em>'+homeEscape(exposureValue)+'</em></span><b aria-hidden="true">›</b>',
    'home-secondary-row'
  );
  const finish=homeIntentButton(
    'Open current expected finish in League Atlas',
    {route:'league_comparison',section:'overview',teamId,metric:'expected_finish',source:'home-finish'},
    '<span class="home-secondary-icon">↗</span><span><small>Current outlook</small><strong>Expected finish: '+homeEscape(expectedFinish)+'</strong><em>'+(standing?'You’re #'+standing.rank+' of '+teamCount:'Current rank unavailable')+'</em></span><b aria-hidden="true">›</b>',
    'home-secondary-row'
  );
  const around=homeIntentButton(
    'Open current standings in League Atlas',
    {route:'league_comparison',section:'overview',teamId,source:'home-around-league'},
    '<div><p class="eyebrow">Around the league</p>'+homeAroundLeague()+'</div><b aria-hidden="true">›</b>',
    'home-around'
  );

  container.innerHTML='<div class="home-command">'
    +'<header class="home-brand-row"><span>FSFFL <b>NEXT</b></span></header>'
    +identity
    +pressure
    +'<section class="home-section"><div class="home-section-heading"><div><p class="eyebrow">Season outlook</p><h3>Current Simulation</h3></div></div>'+outlook+'</section>'
    +'<section class="home-section"><div class="home-section-heading home-roster-heading"><div><p class="eyebrow">Your roster at a glance</p><h3>League-relative shape</h3></div><div class="home-position-toggle" role="group" aria-label="Roster position lens"><button type="button" data-home-position-mode="rank" class="'+(fsfflHomeState.positionLens==='rank'?'active':'')+'">Rank</button><button type="button" data-home-position-mode="strength" class="'+(fsfflHomeState.positionLens==='strength'?'active':'')+'">Strength Index</button></div></div>'+roster+'</section>'
    +'<section class="home-section"><div class="home-section-heading"><div><p class="eyebrow">Also worth knowing</p><h3>Two supporting facts</h3></div></div><div class="home-secondary-list">'+exposure+finish+'</div></section>'
    +around
    +homeEvidenceDetails()
    +'</div>';

  container.querySelectorAll('[data-home-intent]').forEach(button=>button.addEventListener('click',()=>{
    try{homeNavigate(JSON.parse(button.dataset.homeIntent))}catch(_){}
  }));
  container.querySelectorAll('[data-home-position-mode]').forEach(button=>button.addEventListener('click',event=>{
    fsfflHomeState.positionLens=event.currentTarget.dataset.homePositionMode==='strength'?'strength':'rank';
    renderFsfflHomeAttention(state?.teamView||view);
  }));
}

async function loadFsfflHomeCommandCenter({force=false}={}){
  if(!state?.context?.league_id||!state?.context?.team_id)return;
  const key=homeContextKey();
  if(!force&&fsfflHomeState.summary&&fsfflHomeState.contextKey===key){renderFsfflHomeAttention(state?.teamView);return}
  if(fsfflHomeState.loading)return;
  fsfflHomeState.loading=true;fsfflHomeState.error=null;fsfflHomeState.contextKey=key;
  const started=typeof performance!=='undefined'&&performance.now?performance.now():Date.now();
  renderFsfflHomeAttention(state?.teamView);
  try{
    const payload=await api('/api/home/command-center');
    if(homeContextKey()!==key)return;
    fsfflHomeState.summary=payload;
    const ended=typeof performance!=='undefined'&&performance.now?performance.now():Date.now();
    fsfflHomeState.loadMs=Math.max(0,ended-started);
  }catch(error){
    if(homeContextKey()===key){fsfflHomeState.summary=null;fsfflHomeState.error=error.message||String(error)}
  }finally{
    if(homeContextKey()===key){fsfflHomeState.loading=false;renderFsfflHomeAttention(state?.teamView)}
  }
}

function installFsfflHomeExperience(){
  const leagueScreen=document.querySelector('#league-screen');if(!leagueScreen)return;
  const hero=leagueScreen.querySelector('.hero-row');if(hero)hero.hidden=true;
  leagueScreen.querySelector('.metric-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.dashboard-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.roster-panel')?.setAttribute('hidden','');
  const runtime=document.querySelector('#runtime-status');if(runtime)runtime.hidden=true;
  document.querySelector('#home-quick-actions')?.remove();
  let attention=document.querySelector('#home-attention');
  if(!attention){attention=document.createElement('section');attention.id='home-attention';attention.className='home-attention';leagueScreen.prepend(attention)}

  if(!fsfflHomeRenderHookInstalled&&typeof renderMyTeam==='function'){
    const originalRenderMyTeam=renderMyTeam;
    window.renderMyTeam=function(view){const result=originalRenderMyTeam(view);renderFsfflHomeAttention(view);return result};
    renderMyTeam=window.renderMyTeam;fsfflHomeRenderHookInstalled=true;
  }
  renderFsfflHomeAttention(state?.teamView||null);
  void loadFsfflHomeCommandCenter();

  if(!document.querySelector('#fsffl-home-north-star-style')){
    const style=document.createElement('style');style.id='fsffl-home-north-star-style';style.textContent=`
.home-attention{width:min(100%,720px);margin:0 auto;padding:10px 0 calc(88px + env(safe-area-inset-bottom,0px));overflow-x:hidden}.home-command{display:grid;gap:10px}.home-brand-row{padding:2px 4px 0;font-size:21px;font-weight:900;letter-spacing:.04em}.home-brand-row span{color:#50d3ff}.home-brand-row b{color:#fff}.home-identity,.home-pressure,.home-outlook-metric,.home-position-pill,.home-secondary-row,.home-around{appearance:none;width:100%;border:1px solid #1b3850;background:linear-gradient(145deg,#0a1b2d,#071421);color:#f3f7fb;text-align:left;font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}.home-identity{min-height:72px;border-radius:13px;padding:9px 12px;display:grid;grid-template-columns:52px minmax(0,1fr) 22px;gap:10px;align-items:center}.home-team-mark{display:grid;place-items:center;width:48px;height:48px;border-radius:50%;background:#173a56;border:1px solid #3baedc;font-weight:900}.home-identity-copy{display:grid;gap:1px;min-width:0}.home-identity-copy strong{font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.home-identity-copy small,.home-identity-copy em{color:#9bb0c4;font-size:11px;font-style:normal}.home-identity>b,.home-secondary-row>b,.home-around>b{color:#86b6d4;font-size:26px;font-weight:300}.home-pressure{border-color:#7d294e;background:radial-gradient(circle at 15% 25%,rgba(215,47,101,.18),transparent 35%),linear-gradient(145deg,#2a0e22,#170d1c);border-radius:14px;padding:12px;display:grid;gap:9px}.home-pressure-main{display:grid;grid-template-columns:68px minmax(0,1fr);gap:12px;align-items:center}.home-pressure-circle{display:grid;place-items:center;width:62px;height:62px;border-radius:50%;border:5px solid #e33e71;font-size:19px;font-weight:900;background:#250e1d}.home-pressure-circle.strong,.home-pressure-circle.elite{border-color:#42d49d}.home-pressure-circle.neutral{border-color:#e6bb57}.home-pressure-circle.missing{border-color:#506174;color:#8fa2b4}.home-pressure h2{font-size:18px;line-height:1.14;margin:2px 0 4px}.home-pressure p:not(.eyebrow){margin:0;color:#b8a4af;font-size:11px}.home-pressure-cta{display:flex;justify-content:center;align-items:center;min-height:38px;border-radius:8px;background:#a52955;font-weight:800;font-size:12px}.home-pressure.unavailable{border-color:#263b4e;background:#0b1724}.home-section{border:1px solid #16334a;border-radius:14px;background:linear-gradient(145deg,#071725,#07131f);padding:11px}.home-section-heading{display:flex;justify-content:space-between;align-items:end;gap:8px;margin-bottom:9px}.home-section-heading h3{font-size:15px;margin:1px 0}.home-section .eyebrow,.home-pressure .eyebrow,.home-around .eyebrow{margin:0;color:#83bfe1;font-size:9px;font-weight:850;letter-spacing:.13em;text-transform:uppercase}.home-outlook-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.home-outlook-metric{border:0;background:transparent;display:grid;justify-items:center;gap:6px;padding:2px;min-height:98px;text-align:center}.home-ring-visual{--home-ring-pct:0;position:relative;display:grid;place-items:center;width:66px;height:66px;border-radius:50%;background:conic-gradient(#42d49d calc(var(--home-ring-pct)*1%),#183146 0)}.home-ring-visual:after{content:'';position:absolute;inset:6px;border-radius:50%;background:#081625}.home-ring-visual.wins{background:#173e58}.home-ring-visual b{position:relative;z-index:1;font-size:16px}.home-ring-visual.championship{background:conic-gradient(#e05f77 calc(var(--home-ring-pct)*1%),#183146 0)}.home-ring-label{font-size:9px;color:#a7b9c9;line-height:1.15}.home-section-note{display:block;text-align:center;color:#738da3;font-size:8px}.home-roster-heading{align-items:center}.home-position-toggle{display:grid;grid-template-columns:1fr 1fr;border:1px solid #21415a;border-radius:999px;padding:2px;min-width:180px}.home-position-toggle button{border:0;border-radius:999px;background:transparent;color:#91a8bb;min-height:30px;padding:4px 8px;font-size:8px;font-weight:800}.home-position-toggle button.active{background:#15527a;color:#fff}.home-position-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.home-position-pill{border:0;background:transparent;display:grid;justify-items:center;gap:4px;padding:3px;min-height:64px}.home-position-pill>span{color:#8fa7ba;font-size:9px;font-weight:800}.home-position-pill>b{display:grid;place-items:center;width:46px;height:46px;border-radius:50%;background:#163f58;border:2px solid #3183a9;font-size:12px}.home-position-pill>b.elite{background:#0e4b40;border-color:#35c99a}.home-position-pill>b.strong{background:#11445d;border-color:#3598c8}.home-position-pill>b.neutral{background:#4a4125;border-color:#d9ad48}.home-position-pill>b.weak{background:#542536;border-color:#dc5d79}.home-secondary-list{display:grid;border-top:1px solid #18344a}.home-secondary-row{border:0;border-bottom:1px solid #18344a;background:transparent;border-radius:0;min-height:64px;padding:8px 2px;display:grid;grid-template-columns:42px minmax(0,1fr) 18px;gap:8px;align-items:center}.home-secondary-icon{display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:#173a56;color:#58c9f3;font-size:18px}.home-secondary-row>span:nth-child(2){display:grid;gap:1px}.home-secondary-row small,.home-secondary-row em{color:#8ea5b8;font-size:9px;font-style:normal}.home-secondary-row strong{font-size:13px}.home-around{border-radius:14px;padding:11px 12px;display:grid;grid-template-columns:minmax(0,1fr) 20px;gap:8px;align-items:center}.home-around-list{display:grid;margin-top:5px}.home-around-row{display:grid;grid-template-columns:32px minmax(0,1fr) auto;gap:7px;align-items:center;padding:5px 0;border-top:1px solid #173146}.home-around-row:first-child{border-top:0}.home-around-row.managed{color:#75d8ff}.home-around-row>span{display:grid}.home-around-row small,.home-around-row em{color:#88a0b4;font-size:8px;font-style:normal}.home-evidence{border:1px solid #173146;border-radius:11px;background:#07131f}.home-evidence summary{padding:10px 12px;color:#8ea4b6;font-size:9px;font-weight:800}.home-evidence>div{padding:0 12px 10px;color:#8499aa;font-size:9px;line-height:1.4}.home-evidence p{margin:6px 0}.home-unavailable{color:#879cad;font-size:10px;line-height:1.4;margin:5px 0}.home-command-loading,.home-command-unavailable,.home-onboarding{border:1px solid #1b3850;border-radius:14px;background:#081625;padding:18px}.home-command-loading{display:grid;gap:5px}.home-command-loading i{width:26px;height:26px;border-radius:50%;border:3px solid #21445f;border-top-color:#50cfff;animation:home-spin .8s linear infinite}.home-command-loading span,.home-command-unavailable p,.home-onboarding p{color:#91a5b7;line-height:1.45}.home-onboarding .primary-button{margin-top:8px}@keyframes home-spin{to{transform:rotate(360deg)}}@media(max-width:760px){#league-screen>.hero-row,#runtime-status,.metric-grid,.dashboard-grid,.roster-panel{display:none!important}.home-attention{padding-left:8px;padding-right:8px}.home-brand-row{font-size:19px}.home-position-toggle{min-width:164px}.home-pressure-main{grid-template-columns:62px minmax(0,1fr)}.home-pressure-circle{width:56px;height:56px}.home-ring-visual{width:62px;height:62px}.home-outlook-metric{min-height:90px}}@media(max-width:390px){.home-roster-heading{display:grid;align-items:start}.home-position-toggle{width:100%}.home-identity{grid-template-columns:46px minmax(0,1fr) 18px}.home-team-mark{width:42px;height:42px}.home-position-pill>b{width:42px;height:42px}.home-outlook-grid{gap:3px}}
`;document.head.appendChild(style)}
}
window.renderFsfflHomeAttention=renderFsfflHomeAttention;
window.loadFsfflHomeCommandCenter=loadFsfflHomeCommandCenter;
window.installFsfflHomeExperience=installFsfflHomeExperience;
window.fsfflHomeDiagnostics=()=>({version:'20260923-home-north-star1',context_key:fsfflHomeState.contextKey,load_ms:fsfflHomeState.loadMs,summary_status:fsfflHomeState.summary?.status||'unavailable',simulation_status:fsfflHomeState.summary?.simulation?.status||'unavailable',position_lens:fsfflHomeState.positionLens});
window.addEventListener('fsffl:product-context-updated',()=>{fsfflHomeState.summary=null;fsfflHomeState.error=null;fsfflHomeState.contextKey=null;setTimeout(()=>{renderFsfflHomeAttention(state?.teamView||null);void loadFsfflHomeCommandCenter({force:true})},0)});
