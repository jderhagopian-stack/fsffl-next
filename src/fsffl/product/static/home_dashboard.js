let fsfflHomeRenderHookInstalled=false;

function homeEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function homeNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function homePercent(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function homeStateLabel(value){return value&&value!=='unknown'?String(value).replaceAll('_',' '):'Not classified'}
function homeStrengthRows(view){return (view?.position_strengths||[]).filter(row=>typeof row?.strength_index==='number'&&Number.isFinite(row.strength_index))}
function homeAttentionCard({eyebrow,title,value,detail,route,action}){return `<article class="home-attention-card"><p class="eyebrow">${homeEscape(eyebrow)}</p><h3>${homeEscape(title)}</h3><strong class="home-attention-value">${homeEscape(value)}</strong><p>${homeEscape(detail)}</p>${route?`<button type="button" class="text-button" data-home-route="${homeEscape(route)}">${homeEscape(action||'Investigate')}</button>`:''}</article>`}
function homeOpportunityAssetLabels(items){return(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean).join(' + ')||'—'}
function homeLoadedOpportunityWorkspace(){return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState.payload:null}
function homeOpportunityCard(){
  const workspace=homeLoadedOpportunityWorkspace();
  const lead=workspace?.trade_discovery?.spotlights?.most_promising_evaluated;
  if(lead){
    const receive=homeOpportunityAssetLabels(lead.receive),send=homeOpportunityAssetLabels(lead.send),other=lead.counterparty_name||lead.counterparty_team_id||'another team';
    const shape=lead.negotiation_feasibility_shape?String(lead.negotiation_feasibility_shape).replaceAll('_',' '):'evaluated lead';
    return homeAttentionCard({eyebrow:'Current opportunity',title:'Most promising evaluated lead',value:receive,detail:`Send ${send} to ${other}. ${shape}. This is the server-selected Decision-evaluated lead, not an acceptance prediction.`,route:'opportunities',action:'Open in Trade Finder'});
  }
  if(workspace?.status&&workspace.status!=='ready')return homeAttentionCard({eyebrow:'Current opportunity',title:'Trade Finder is still preparing',value:'Not ready yet',detail:workspace.message||'A required governed input is still loading.',route:'opportunities',action:'See readiness'});
  if(workspace)return homeAttentionCard({eyebrow:'Current opportunity',title:'No evaluated lead available',value:'No clear lead',detail:'FSFFL will not invent an opportunity when the current governed workspace has not identified one.',route:'opportunities',action:'Explore Trade Finder'});
  return homeAttentionCard({eyebrow:'Current opportunity',title:'Check current acquisition paths',value:'Open Trade Finder',detail:'Home stays fast by reusing Trade Finder results only after its governed workspace has been loaded. It does not launch Search on its own.',route:'opportunities',action:'Load current opportunities'});
}

function renderFsfflHomeAttention(view=state?.teamView){
  const container=document.querySelector('#home-attention');if(!container)return;
  if(!state?.context?.league_id){container.innerHTML='<div class="home-attention-empty"><p class="eyebrow">Start here</p><h2>Connect your league</h2><p>FSFFL NEXT will surface the few things that deserve attention instead of making you scan every dashboard.</p></div>';return}
  if(!state?.context?.team_id){container.innerHTML='<div class="home-attention-empty"><p class="eyebrow">One step left</p><h2>Choose the franchise you manage</h2><p>Home becomes personalized once a managed team is selected.</p></div>';return}
  if(!view){container.innerHTML='<div class="home-attention-empty"><p class="eyebrow">Your attention board</p><h2>Reading the current franchise state…</h2><p>Useful league context can load first while governed team evidence finishes attaching.</p></div>';return}

  const outcome=view.utility?.competitive_outcome;
  const resilience=view.utility?.roster_resilience;
  const strengths=homeStrengthRows(view).sort((a,b)=>a.strength_index-b.strength_index);
  const weakest=strengths[0]||null,strongest=strengths[strengths.length-1]||null;
  const stateLabel=homeStateLabel(view.utility?.calculated_competitive_state);
  const fragility=typeof resilience?.largest_single_player_lineup_drop==='number'?`${homeNumber(resilience.largest_single_player_lineup_drop,1)} pts`:'Evidence unavailable';
  const fragilityDetail=typeof resilience?.largest_single_player_lineup_drop==='number'
    ?`Largest projected lineup loss if one starter becomes unavailable. ${resilience.bench_forecasted_count??'—'} bench players have forecast evidence; ${resilience.missing_forecast_count??'—'} roster forecasts are missing.`
    :'Roster-resilience evidence has not attached to this state yet.';
  const positionValue=weakest?`${weakest.position} · ${Math.round(weakest.strength_index)}`:'Evidence unavailable';
  const positionDetail=weakest
    ?`Weakest current optimized-starter position versus the league. 100 is league average.${strongest&&strongest.position!==weakest.position?` Strongest: ${strongest.position} (${Math.round(strongest.strength_index)}).`:''}`
    :'Position-strength evidence has not attached to this state yet.';
  const outlookValue=outcome?`${homeNumber(outcome.expected_wins,2)} wins · ${homePercent(outcome.playoff_probability,0)} playoffs`:stateLabel;
  const outlookDetail=outcome?`${stateLabel}. This is governed Simulation/Team Utility evidence, not an owner-strategy label.`:'Competitive-outcome evidence is still loading or unavailable.';

  container.innerHTML=`<div class="home-attention-header"><div><p class="eyebrow">What should I care about right now?</p><h2>${homeEscape(view.display_name)}</h2><p>These are separate governed signals, not an opaque combined score. Use them to decide where to investigate next.</p></div><button type="button" class="secondary-button" data-home-route="opportunities">Open Opportunities</button></div><div class="home-attention-grid">${homeOpportunityCard()}${homeAttentionCard({eyebrow:'Competitive outlook',title:'Where you stand now',value:outlookValue,detail:outlookDetail,route:'my_team',action:'See franchise drivers'})}${homeAttentionCard({eyebrow:'Roster vulnerability',title:'How much one absence can hurt',value:fragility,detail:fragilityDetail,route:'what_if',action:'Stress-test the roster'})}${homeAttentionCard({eyebrow:'Position to investigate',title:'Current lineup pressure point',value:positionValue,detail:positionDetail,route:'my_team',action:'Inspect position depth'})}</div><div class="home-investigate"><div><p class="eyebrow">From insight to action</p><h3>Choose the next question</h3></div><div class="home-investigate-actions"><button type="button" data-home-route="opportunities"><strong>Find something worth doing</strong><span>Trade Finder and governed opportunity discovery</span></button><button type="button" data-home-route="league_comparison"><strong>Understand the league structure</strong><span>Compare franchises rather than another team summary</span></button><button type="button" data-home-route="trade_center"><strong>Test a specific trade</strong><span>Build the deal and evaluate both sides</span></button><button type="button" data-home-route="analytics"><strong>Investigate for yourself</strong><span>Open the read-only Analytics Terminal</span></button></div></div><p class="home-roadmap-note"><strong>Not fabricated:</strong> change-since-last-visit, historical inflection points, and owner-behavior alerts will appear here only after their governed history/evidence contracts exist.</p>`;
  container.querySelectorAll('[data-home-route]').forEach(button=>button.addEventListener('click',()=>setRoute(button.dataset.homeRoute)));
}

function installFsfflHomeExperience(){
  const leagueScreen=document.querySelector('#league-screen');if(!leagueScreen)return;
  const hero=leagueScreen.querySelector('.hero-row');
  const eyebrow=hero?.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='Home';
  const heading=hero?.querySelector('h1');if(heading)heading.textContent='Know what deserves your attention.';
  const lead=hero?.querySelector('.lead');if(lead)lead.textContent='Home prioritizes the current signals worth investigating. Full diagnostics, comparisons, trade analysis and exploration live on their own dedicated surfaces.';

  leagueScreen.querySelector('.metric-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.dashboard-grid')?.setAttribute('hidden','');
  leagueScreen.querySelector('.roster-panel')?.setAttribute('hidden','');
  document.querySelector('#home-quick-actions')?.remove();
  let attention=document.querySelector('#home-attention');
  if(!attention){attention=document.createElement('section');attention.id='home-attention';attention.className='home-attention';hero?.insertAdjacentElement('afterend',attention)}

  const runtime=document.querySelector('#runtime-status'),grid=document.querySelector('#runtime-stage-grid');
  if(runtime&&grid&&!runtime.querySelector('#runtime-detail-toggle')){grid.hidden=true;const toggle=document.createElement('button');toggle.id='runtime-detail-toggle';toggle.type='button';toggle.className='text-button';toggle.textContent='Show technical status';toggle.setAttribute('aria-expanded','false');toggle.addEventListener('click',()=>{grid.hidden=!grid.hidden;toggle.textContent=grid.hidden?'Show technical status':'Hide technical status';toggle.setAttribute('aria-expanded',String(!grid.hidden))});runtime.querySelector('.panel-header')?.appendChild(toggle);const runtimeEyebrow=runtime.querySelector('.eyebrow');if(runtimeEyebrow)runtimeEyebrow.textContent='System status'}

  if(!fsfflHomeRenderHookInstalled&&typeof renderMyTeam==='function'){
    const originalRenderMyTeam=renderMyTeam;
    window.renderMyTeam=function(view){const result=originalRenderMyTeam(view);renderFsfflHomeAttention(view);return result};
    renderMyTeam=window.renderMyTeam;fsfflHomeRenderHookInstalled=true;
  }
  renderFsfflHomeAttention(state?.teamView||null);
  if(!document.querySelector('#fsffl-home-attention-style')){const style=document.createElement('style');style.id='fsffl-home-attention-style';style.textContent=`.home-attention{margin:16px 0 20px}.home-attention-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:12px}.home-attention-header h2,.home-attention-header p{margin-top:0}.home-attention-header>div>p:last-child,.home-attention-card p,.home-roadmap-note,.home-attention-empty p{color:var(--muted);line-height:1.45}.home-attention-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.home-attention-card,.home-investigate,.home-attention-empty{border:1px solid var(--line);background:#0a1120;border-radius:16px;padding:16px}.home-attention-card h3{margin:4px 0 10px;font-size:1rem}.home-attention-value{display:block;font-size:1.35rem;line-height:1.2;margin-bottom:8px;text-transform:capitalize}.home-attention-card .text-button{padding-left:0}.home-investigate{margin-top:10px;display:grid;grid-template-columns:minmax(180px,.75fr) minmax(0,2fr);gap:16px;align-items:start}.home-investigate h3{margin:3px 0}.home-investigate-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.home-investigate-actions button{border:1px solid var(--line);background:var(--surface-2);color:var(--text);border-radius:12px;padding:12px;text-align:left;display:grid;gap:4px;cursor:pointer}.home-investigate-actions button:hover{border-color:var(--accent)}.home-investigate-actions span{font-size:11px;color:var(--muted);line-height:1.35}.home-roadmap-note{font-size:12px;margin:10px 2px 0}.home-attention-empty{min-height:120px}.home-attention-empty h2{margin:4px 0}@media(max-width:1100px){.home-attention-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:760px){.home-attention-header{display:grid}.home-attention-header .secondary-button{width:100%}.home-attention-grid{grid-template-columns:1fr}.home-investigate{grid-template-columns:1fr}.home-investigate-actions{grid-template-columns:1fr}.home-attention-card{padding:14px}.home-attention-value{font-size:1.2rem}}`;document.head.appendChild(style)}
}
window.renderFsfflHomeAttention=renderFsfflHomeAttention;
window.installFsfflHomeExperience=installFsfflHomeExperience;
window.addEventListener('fsffl:product-context-updated',()=>setTimeout(()=>renderFsfflHomeAttention(state?.teamView||null),0));
