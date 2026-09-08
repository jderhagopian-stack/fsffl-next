function myTeamDiagnosticAverageAge(players){let total=0,count=0;for(const player of players||[]){if(typeof player?.age_years==='number'&&Number.isFinite(player.age_years)){total+=player.age_years;count+=1}}return count?total/count:null}
function myTeamDiagnosticStrengths(view){return (view?.position_strengths||[]).filter(row=>typeof row?.strength_index==='number'&&Number.isFinite(row.strength_index)).sort((a,b)=>a.strength_index-b.strength_index)}
function myTeamDiagnosticPicksBySeason(view){const seasons=new Map();for(const row of view?.draft_picks||[]){const season=row?.pick?.season;if(season==null)continue;const bucket=seasons.get(season)||{count:0,rounds:new Map()};bucket.count+=1;const round=row?.pick?.round;if(round!=null)bucket.rounds.set(round,(bucket.rounds.get(round)||0)+1);seasons.set(season,bucket)}return [...seasons.entries()].sort((a,b)=>a[0]-b[0])}
function myTeamDiagnosticRoundLabel(round,count){const label=round===1?'1st':round===2?'2nd':round===3?'3rd':`${round}th`;return `${count} ${label}`}
function myTeamDiagnosticPickText(view){const seasons=myTeamDiagnosticPicksBySeason(view);if(!seasons.length)return'No owned picks exposed';return seasons.map(([season,bucket])=>{const rounds=[...bucket.rounds.entries()].sort((a,b)=>a[0]-b[0]).map(([round,count])=>myTeamDiagnosticRoundLabel(round,count)).join(', ');return `${season}: ${bucket.count} pick${bucket.count===1?'':'s'}${rounds?` · ${rounds}`:''}`}).join(' | ')}
function myTeamDiagnosticCard(eyebrow,title,value,detail){return `<article class="my-team-driver-card"><p class="eyebrow">${myTeamEsc(eyebrow)}</p><h4>${myTeamEsc(title)}</h4><strong>${myTeamEsc(value)}</strong><p>${myTeamEsc(detail)}</p></article>`}

function renderFsfflMyTeamDiagnostics(){
  const panel=document.querySelector('#generic-screen .panel'),view=fsfflMyTeamState?.view;if(!panel||!view)return;
  panel.querySelector('#my-team-franchise-drivers')?.remove();
  const metrics=panel.querySelector('.my-team-metrics');if(!metrics)return;
  const roster=view.players||[],starters=roster.filter(player=>player.projected_starter),strengths=myTeamDiagnosticStrengths(view),weakest=strengths[0]||null,strongest=strengths[strengths.length-1]||null,resilience=view.utility?.roster_resilience;
  const starterAge=myTeamDiagnosticAverageAge(starters),rosterAge=myTeamDiagnosticAverageAge(roster);
  const fragility=typeof resilience?.largest_single_player_lineup_drop==='number'?`${myTeamNum(resilience.largest_single_player_lineup_drop,1)} pts`:'Unavailable';
  const fragilityDetail=typeof resilience?.largest_single_player_lineup_drop==='number'?`Largest projected lineup drop from one unavailable starter. ${resilience.bench_forecasted_count??'—'} bench players have forecast evidence; ${resilience.missing_forecast_count??'—'} roster forecasts are missing.`:'Roster-resilience evidence has not attached.';
  const pressure=weakest?`${weakest.position} · ${Math.round(weakest.strength_index)}`:'Unavailable';
  const pressureDetail=weakest?`Lowest current optimized-starter position strength. 100 is league average.${strongest&&strongest.position!==weakest.position?` Highest: ${strongest.position} (${Math.round(strongest.strength_index)}).`:''}`:'Position-strength evidence has not attached.';
  const ageValue=starterAge!=null||rosterAge!=null?`Starters ${starterAge==null?'—':starterAge.toFixed(1)} · roster ${rosterAge==null?'—':rosterAge.toFixed(1)}`:'Unavailable';
  const ageDetail='Descriptive average ages only. No youth/veteran label or age-curve value adjustment is created in Presentation.';
  const pickText=myTeamDiagnosticPickText(view);
  const section=document.createElement('section');section.id='my-team-franchise-drivers';section.className='my-team-section my-team-franchise-drivers';section.innerHTML=`<div class="my-team-driver-heading"><div><p class="eyebrow">Franchise drivers</p><h3>What is actually shaping this team?</h3><p class="my-team-section-note">Start with the structural facts before scanning the full roster. These are separate descriptive signals from governed team evidence—not a franchise-health score.</p></div><button type="button" class="text-button" data-my-team-route="analytics">Investigate deeper</button></div><div class="my-team-driver-grid">${myTeamDiagnosticCard('Lineup pressure','Position to investigate',pressure,pressureDetail)}${myTeamDiagnosticCard('Roster fragility','One-player exposure',fragility,fragilityDetail)}${myTeamDiagnosticCard('Age profile','Current roster age shape',ageValue,ageDetail)}${myTeamDiagnosticCard('Draft capital','Owned-pick trajectory',pickText,'Inventory grouped by season and round only; no new pick-value score is calculated here.')}</div>`;
  metrics.insertAdjacentElement('afterend',section);
  section.querySelectorAll('[data-my-team-route]').forEach(button=>button.addEventListener('click',()=>setRoute(button.dataset.myTeamRoute)));
}

(function installFsfflMyTeamDiagnostics(){
  if(typeof renderMyTeamCommandCenter!=='function')return;
  const originalRenderMyTeamCommandCenter=renderMyTeamCommandCenter;
  renderMyTeamCommandCenter=function(){const result=originalRenderMyTeamCommandCenter();renderFsfflMyTeamDiagnostics();return result};
  const style=document.createElement('style');style.id='fsffl-my-team-diagnostics-style';style.textContent=`.my-team-driver-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.my-team-driver-heading h3{margin:3px 0}.my-team-driver-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.my-team-driver-card{border:1px solid var(--line);border-radius:14px;padding:14px;background:#0a1120;min-width:0}.my-team-driver-card h4{margin:3px 0 8px}.my-team-driver-card>strong{display:block;font-size:1.15rem;line-height:1.25;margin-bottom:7px;overflow-wrap:anywhere}.my-team-driver-card>p:last-child{color:var(--muted);font-size:12px;line-height:1.45;margin-bottom:0}@media(max-width:760px){.my-team-driver-heading{display:grid}.my-team-driver-grid{grid-template-columns:1fr}.my-team-driver-card{padding:13px}}`;document.head.appendChild(style);
})();
window.renderFsfflMyTeamDiagnostics=renderFsfflMyTeamDiagnostics;
