/* Phase 3 Home Command Center.
 * Presentation only. Home reuses already-loaded governed team/opportunity evidence
 * and deliberately does not initiate Search, Decision, Value or Simulation work.
 */
let fsfflHomeRenderHookInstalled=false;

function homeEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function homeNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function homePercent(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function homeWords(value){return String(value||'').replaceAll('_',' ')}
function homeStateLabel(value){return value&&value!=='unknown'?homeWords(value):'Not classified'}
function homeStrengthRows(view){return(view?.position_strengths||[]).filter(row=>typeof row?.strength_index==='number'&&Number.isFinite(row.strength_index))}
function homeOpportunityAssetLabels(items){return(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean).join(' + ')||'—'}
function homeLoadedOpportunityWorkspace(){return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState.payload:null}

function homePrimaryAction(){
  const workspace=homeLoadedOpportunityWorkspace();
  const lead=workspace?.trade_discovery?.spotlights?.most_promising_evaluated;
  if(lead){
    const receive=homeOpportunityAssetLabels(lead.receive),send=homeOpportunityAssetLabels(lead.send),other=lead.counterparty_name||lead.counterparty_team_id||'another team';
    const shape=lead.negotiation_feasibility_shape?homeWords(lead.negotiation_feasibility_shape):'Decision evaluated';
    return{tone:'opportunity',kicker:'Best current action path',title:`Explore ${receive}`,detail:`Send ${send} to ${other}. ${shape}. This is the server-selected Decision-evaluated lead, not an acceptance prediction.`,route:'opportunities',action:'Work this opportunity',meta:'Strongest evaluated path already loaded by Market'};
  }
  if(workspace?.status&&workspace.status!=='ready')return{tone:'waiting',kicker:'Market intelligence',title:'Opportunity search is still preparing',detail:workspace.message||'A governed input is still attaching.',route:'opportunities',action:'See market readiness',meta:'FSFFL will not substitute an unevaluated guess'};
  if(workspace)return{tone:'quiet',kicker:'Market intelligence',title:'No evaluated lead stands out yet',detail:'The current governed workspace has not identified a Decision-evaluated lead. FSFFL will not invent an opportunity to fill this space.',route:'opportunities',action:'Explore the full market',meta:'No fabricated recommendation'};
  return{tone:'opportunity',kicker:'Best next action',title:'Scan the personalized market',detail:'Market has not been opened in this session yet. Home stays fast by reusing governed results after Market loads instead of launching deep Search itself.',route:'opportunities',action:'Find my best moves',meta:'Opens Market without duplicating Search work'};
}

function homePulse(view){
  const outcome=view?.utility?.competitive_outcome,resilience=view?.utility?.roster_resilience;
  const strengths=homeStrengthRows(view).sort((a,b)=>a.strength_index-b.strength_index),weakest=strengths[0]||null,strongest=strengths[strengths.length-1]||null;
  const stateLabel=homeStateLabel(view?.utility?.calculated_competitive_state);
  const outlook=outcome?`${homeNumber(outcome.expected_wins,2)} wins · ${homePercent(outcome.playoff_probability,0)} playoffs`:stateLabel;
  const outlookDetail=outcome?`${stateLabel} current competitive profile.`:'Competitive Simulation evidence is still attaching.';
  const risk=typeof resilience?.largest_single_player_lineup_drop==='number'?`${homeNumber(resilience.largest_single_player_lineup_drop,1)} projected points`:'Not available';
  const riskDetail=typeof resilience?.largest_single_player_lineup_drop==='number'?`Largest lineup loss from one starter becoming unavailable. ${resilience.bench_forecasted_count??'—'} bench players have forecast evidence.`:'Roster-resilience evidence is not available on this state.';
  const pressure=weakest?`${weakest.position} · #${weakest.league_rank||'—'} of ${weakest.team_count||'—'}`:'Not available';
  const pressureDetail=weakest?`${Math.round(weakest.strength_index)} strength index versus 100 league average.${strongest&&strongest.position!==weakest.position?` Strongest unit: ${strongest.position}.`:''}`:'League-relative position evidence is not available.';
  return[
    {label:'Competitive outlook',value:outlook,detail:outlookDetail,route:'my_team',action:'Open Franchise'},
    {label:'Biggest roster risk',value:risk,detail:riskDetail,route:'what_if',action:'Stress-test it'},
    {label:'Position to watch',value:pressure,detail:pressureDetail,route:'my_team',action:'See the diagnosis'},
  ];
}
function homePulseRow(item){return`<article class="home-pulse-row"><div><span>${homeEscape(item.label)}</span><strong>${homeEscape(item.value)}</strong><small>${homeEscape(item.detail)}</small></div><button type="button" data-home-route="${homeEscape(item.route)}">${homeEscape(item.action)}<b aria-hidden="true">›</b></button></article>`}
function homeWorkflow(route,title,detail){return`<button type="button" class="home-workflow" data-home-route="${homeEscape(route)}"><span><strong>${homeEscape(title)}</strong><small>${homeEscape(detail)}</small></span><b aria-hidden="true">›</b></button>`}

function renderFsfflHomeAttention(view=state?.teamView){
  const container=document.querySelector('#home-attention');if(!container)return;
  if(!state?.context?.league_id){container.innerHTML='<div class="home-onboarding"><p class="eyebrow">Your league, understood</p><h2>Connect a league to turn FSFFL on.</h2><p>FSFFL will prioritize what deserves attention, explain why it matters, and connect each insight to the next decision.</p><button type="button" class="primary-button" data-home-connect>Connect Sleeper League</button></div>';container.querySelector('[data-home-connect]')?.addEventListener('click',()=>document.querySelector('#connect-button')?.click());return}
  if(!state?.context?.team_id){container.innerHTML='<div class="home-onboarding"><p class="eyebrow">Personalize the command center</p><h2>Choose the franchise you manage.</h2><p>FSFFL already knows the league. Select your team so Home can prioritize the signals that matter to you.</p></div>';return}
  if(!view){container.innerHTML='<div class="home-onboarding"><p class="eyebrow">Command Center</p><h2>Reading the current franchise state…</h2><p>The product remains usable while governed Franchise evidence attaches.</p></div>';return}

  const primary=homePrimaryAction(),pulse=homePulse(view);
  container.innerHTML=`
    <section class="home-command-head"><div><p class="eyebrow">Command Center</p><h2>${homeEscape(view.display_name)}</h2><p>What deserves your attention right now.</p></div><span class="home-state-pill">${homeEscape(homeStateLabel(view.utility?.calculated_competitive_state))}</span></section>
    <section class="home-priority ${homeEscape(primary.tone)}">
      <div class="home-priority-copy"><span class="home-priority-kicker">${homeEscape(primary.kicker)}</span><h3>${homeEscape(primary.title)}</h3><p>${homeEscape(primary.detail)}</p><small>${homeEscape(primary.meta)}</small></div>
      <button type="button" class="primary-button" data-home-route="${homeEscape(primary.route)}">${homeEscape(primary.action)} <b aria-hidden="true">→</b></button>
    </section>
    <section class="home-current"><div class="home-section-title"><div><p class="eyebrow">Franchise pulse</p><h3>Three things worth knowing</h3></div><button type="button" class="text-button" data-home-route="my_team">Full diagnosis</button></div><div class="home-pulse-list">${pulse.map(homePulseRow).join('')}</div></section>
    <section class="home-next"><div class="home-section-title"><div><p class="eyebrow">Go deeper</p><h3>Choose the decision, not the dashboard</h3></div></div><div class="home-workflows">${homeWorkflow('opportunities','Find my best moves','Open the personalized Market and set an objective.')}${homeWorkflow('trade_center','Test a specific trade','See both franchises, Simulation impact and realistic counters.')}${homeWorkflow('league_comparison','Read the league','Find positional edges, structural imbalances and complementary needs.')}</div></section>
    <p class="home-evidence-note">Home prioritizes already-loaded governed evidence; it does not calculate a combined score or launch deep Search. Change-since-last-visit and activity alerts will join this command center only after their governed history/evidence contracts exist.</p>`;
  container.querySelectorAll('[data-home-route]').forEach(button=>button.addEventListener('click',()=>setRoute(button.dataset.homeRoute)));
}

function installFsfflHomeExperience(){
  const leagueScreen=document.querySelector('#league-screen');if(!leagueScreen)return;
  const hero=leagueScreen.querySelector('.hero-row');
  const eyebrow=hero?.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='Home';
  const heading=hero?.querySelector('h1');if(heading)heading.textContent='Know what matters. Then act.';
  const lead=hero?.querySelector('.lead');if(lead)lead.textContent='Your command center prioritizes the current action, risk and context worth your attention. Detailed diagnosis and evidence live where they belong.';
  hero?.querySelector('.hero-actions')?.setAttribute('hidden','');
  leagueScreen.querySelector('.metric-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.dashboard-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.roster-panel')?.setAttribute('hidden','');
  document.querySelector('#home-quick-actions')?.remove();
  let attention=document.querySelector('#home-attention');if(!attention){attention=document.createElement('section');attention.id='home-attention';attention.className='home-attention';hero?.insertAdjacentElement('afterend',attention)}

  const runtime=document.querySelector('#runtime-status'),grid=document.querySelector('#runtime-stage-grid');
  if(runtime){runtime.classList.add('home-system-status');if(grid&&!runtime.querySelector('#runtime-detail-toggle')){grid.hidden=true;const toggle=document.createElement('button');toggle.id='runtime-detail-toggle';toggle.type='button';toggle.className='text-button';toggle.textContent='Show technical status';toggle.setAttribute('aria-expanded','false');toggle.addEventListener('click',()=>{grid.hidden=!grid.hidden;toggle.textContent=grid.hidden?'Show technical status':'Hide technical status';toggle.setAttribute('aria-expanded',String(!grid.hidden))});runtime.querySelector('.panel-header')?.appendChild(toggle);const runtimeEyebrow=runtime.querySelector('.eyebrow');if(runtimeEyebrow)runtimeEyebrow.textContent='System status'}}

  if(!fsfflHomeRenderHookInstalled&&typeof renderMyTeam==='function'){
    const originalRenderMyTeam=renderMyTeam;window.renderMyTeam=function(view){const result=originalRenderMyTeam(view);renderFsfflHomeAttention(view);return result};renderMyTeam=window.renderMyTeam;fsfflHomeRenderHookInstalled=true;
  }
  renderFsfflHomeAttention(state?.teamView||null);
  if(!document.querySelector('#fsffl-home-command-style')){const style=document.createElement('style');style.id='fsffl-home-command-style';style.textContent=`
.home-attention{margin:4px 0 24px;max-width:1080px}.home-command-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-end;margin-bottom:13px}.home-command-head h2{margin:2px 0 4px;font-size:clamp(1.45rem,3vw,2rem)}.home-command-head>div>p:last-child{margin:0;color:var(--muted)}.home-state-pill{border:1px solid var(--line);border-radius:999px;padding:7px 10px;color:var(--muted);font-size:11px;text-transform:capitalize}.home-priority{border:1px solid #31536a;border-radius:18px;padding:22px;background:linear-gradient(135deg,rgba(19,48,67,.82),rgba(10,17,32,.96) 64%);display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:center;box-shadow:var(--shadow)}.home-priority.quiet,.home-priority.waiting{border-color:var(--line);background:linear-gradient(135deg,rgba(17,25,43,.95),rgba(10,17,32,.96))}.home-priority-kicker{font-size:10px;letter-spacing:.14em;text-transform:uppercase;font-weight:850;color:var(--accent)}.home-priority h3{font-size:clamp(1.5rem,4vw,2.25rem);line-height:1.08;margin:7px 0 9px;letter-spacing:-.035em}.home-priority p{color:#cbd5e1;line-height:1.5;margin:0 0 8px;max-width:720px}.home-priority small{display:block;color:var(--muted);font-size:11px}.home-priority>.primary-button{min-width:178px}.home-current,.home-next{margin-top:22px}.home-section-title{display:flex;justify-content:space-between;gap:12px;align-items:flex-end;margin-bottom:9px}.home-section-title h3{margin:2px 0;font-size:1.05rem}.home-pulse-list{border-top:1px solid var(--line)}.home-pulse-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;padding:13px 2px;border-bottom:1px solid var(--line)}.home-pulse-row>div{display:grid;grid-template-columns:minmax(130px,.65fr) minmax(160px,.8fr) minmax(220px,1.4fr);gap:14px;align-items:center}.home-pulse-row span{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}.home-pulse-row strong{font-size:14px}.home-pulse-row small{color:var(--muted);font-size:11px;line-height:1.35}.home-pulse-row>button{border:0;background:transparent;color:var(--accent);font:inherit;font-size:12px;white-space:nowrap}.home-pulse-row>button b,.home-workflow>b{font-size:17px;font-weight:400;margin-left:3px}.home-workflows{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.home-workflow{border:1px solid var(--line);border-radius:13px;background:#0a1120;color:var(--text);padding:13px;text-align:left;display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;font:inherit}.home-workflow:hover{border-color:#37516f}.home-workflow span{display:grid;gap:3px}.home-workflow strong{font-size:13px}.home-workflow small{color:var(--muted);font-size:10px;line-height:1.35}.home-workflow>b{color:var(--muted)}.home-evidence-note{color:var(--muted);font-size:10px;line-height:1.45;margin:14px 2px 0}.home-onboarding{border:1px solid var(--line);border-radius:18px;background:#0a1120;padding:24px;max-width:760px}.home-onboarding h2{font-size:1.7rem;margin:4px 0 8px}.home-onboarding p:not(.eyebrow){color:var(--muted);line-height:1.5}.home-onboarding .primary-button{margin-top:8px}.home-system-status{margin-top:18px;opacity:.82}
@media(max-width:760px){.home-attention{margin-top:0}.home-command-head{align-items:flex-start}.home-priority{grid-template-columns:1fr;padding:17px;gap:16px}.home-priority>.primary-button{width:100%}.home-pulse-row{grid-template-columns:1fr}.home-pulse-row>div{grid-template-columns:1fr;gap:4px}.home-pulse-row>button{text-align:left;padding:3px 0}.home-workflows{grid-template-columns:1fr}.home-section-title{align-items:flex-start}.home-system-status{margin-top:12px}}
`;document.head.appendChild(style)}
}
window.renderFsfflHomeAttention=renderFsfflHomeAttention;
window.installFsfflHomeExperience=installFsfflHomeExperience;
window.addEventListener('fsffl:product-context-updated',()=>setTimeout(()=>renderFsfflHomeAttention(state?.teamView||null),0));
