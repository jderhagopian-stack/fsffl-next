const fsfflMyTeamState={view:null,valueLenses:null,leagueViews:[],leagueSource:'',valueLensLoading:false,valueLensGeneration:0};

function myTeamEsc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function myTeamNum(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function myTeamPct(value,digits=0){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function myTeamAge(value){return typeof value==='number'&&Number.isFinite(value)?(Number.isInteger(value)?String(value):value.toFixed(1)):'—'}
function myTeamPanel(){return document.querySelector('#generic-screen .panel')}
function myTeamLensMap(){return new Map((fsfflMyTeamState.valueLenses?.players||[]).map(item=>[item.player_id,item]))}
function myTeamIntrinsicNumber(id){const row=myTeamLensMap().get(id);return typeof row?.intrinsic_percentile==='number'&&Number.isFinite(row.intrinsic_percentile)?row.intrinsic_percentile:null}
function myTeamIntrinsicIndex(id){const row=myTeamLensMap().get(id);return typeof row?.intrinsic_value_index==='number'&&Number.isFinite(row.intrinsic_value_index)?row.intrinsic_value_index:null}
function myTeamIntrinsic(id){const index=myTeamIntrinsicIndex(id),pct=myTeamIntrinsicNumber(id);if(index!=null)return `${Math.round(index).toLocaleString()}<small>${pct==null?'':`${Math.round(pct*100)}th pct`}</small>`;if(fsfflMyTeamState.valueLensLoading)return'Loading…';const reason=fsfflMyTeamState.valueLenses?.fsffl_intrinsic?.reason||fsfflMyTeamState.valueLenses?.message||'Governed FSFFL Intrinsic is unavailable for the current league state.';return `<span class="franchise-intrinsic-unavailable">Unavailable<small>${myTeamEsc(reason)}</small></span>`}
function myTeamMarketNumber(player){const estimate=player?.value_profile?.market_price;return estimate?.scale?.scale_id==='dynasty-market-percentile'&&typeof estimate?.distribution?.mean==='number'&&Number.isFinite(estimate.distribution.mean)?estimate.distribution.mean:null}
function myTeamMarketIndex(player){const row=myTeamLensMap().get(player?.player_id);return typeof row?.broad_market_value_index==='number'&&Number.isFinite(row.broad_market_value_index)?row.broad_market_value_index:null}
function myTeamProjectionObservation(player){if(typeof window.fsfflDisplayedProjectionObservation==='function')return window.fsfflDisplayedProjectionObservation(player);const observations=player?.forecasts||[];return observations.find(item=>item.metric==='fantasy_points'&&item.horizon==='season')||null}
function myTeamProjectionNumber(player){const obs=myTeamProjectionObservation(player);return typeof obs?.distribution?.mean==='number'&&Number.isFinite(obs.distribution.mean)?obs.distribution.mean:null}
function myTeamProjection(player){const value=myTeamProjectionNumber(player);return value==null?'—':value.toFixed(1)}
function myTeamMarket(player){const index=myTeamMarketIndex(player),pct=myTeamMarketNumber(player);return index==null?(pct==null?'—':`${Math.round(pct*100)}th pct`):`${Math.round(index).toLocaleString()}<small>${pct==null?'':`${Math.round(pct*100)}th pct`}</small>`}
function myTeamAllLeaguePlayers(){return fsfflMyTeamState.leagueViews.flatMap(team=>team.players||[])}
function myTeamPositionRank(player,kind){const candidates=myTeamAllLeaguePlayers().filter(row=>row.position===player.position).map(row=>({id:row.player_id,value:kind==='projection'?myTeamProjectionNumber(row):kind==='intrinsic'?myTeamIntrinsicNumber(row.player_id):myTeamMarketNumber(row)})).filter(row=>typeof row.value==='number').sort((a,b)=>b.value-a.value);const index=candidates.findIndex(row=>row.id===player.player_id);return index<0?null:{rank:index+1,count:candidates.length}}
function myTeamRankText(rank){return rank?`#${rank.rank} of ${rank.count}`:'—'}
function myTeamLeagueOutcomeRank(metric){const rows=fsfflMyTeamState.leagueViews.map(view=>({team_id:view.team_id,value:view.utility?.competitive_outcome?.[metric]})).filter(row=>typeof row.value==='number').sort((a,b)=>b.value-a.value);const index=rows.findIndex(row=>row.team_id===state?.context?.team_id);return index<0?null:{rank:index+1,count:rows.length}}
function myTeamTeamName(teamId){if(!teamId)return'';if(teamId===state?.context?.team_id)return'own';return(state?.context?.teams||[]).find(team=>team.team_id===teamId)?.display_name||'original team'}
function myTeamOrdinalRound(round){const n=Number(round);if(n===1)return'1st';if(n===2)return'2nd';if(n===3)return'3rd';return`${n}th`}
function myTeamPickLabel(row){const pick=row.pick||{};const season=pick.season??'Future';const round=pick.round!=null?myTeamOrdinalRound(pick.round):'pick';const owner=myTeamTeamName(pick.original_team_id);return `${season} ${round}${owner?` (${owner})`:''}`}
function myTeamStateLabel(value){return value&&value!=='unknown'?String(value).replaceAll('_',' '):'Not classified'}
function myTeamStrengths(view){return(view?.position_strengths||[]).filter(row=>typeof row?.strength_index==='number'&&Number.isFinite(row.strength_index)).sort((a,b)=>b.strength_index-a.strength_index)}
function myTeamAverageAge(players){const ages=(players||[]).map(row=>row.age_years).filter(value=>typeof value==='number'&&Number.isFinite(value));return ages.length?ages.reduce((sum,value)=>sum+value,0)/ages.length:null}
function myTeamRankedAssets(players){const useIntrinsic=(fsfflMyTeamState.valueLenses?.fsffl_intrinsic?.status||'')!=='unavailable';return(players||[]).map(player=>({player,value:useIntrinsic?myTeamIntrinsicNumber(player.player_id):myTeamMarketNumber(player),lens:useIntrinsic?'FSFFL Intrinsic':'Broad Market'})).filter(row=>row.value!=null).sort((a,b)=>b.value-a.value)}
function myTeamPickSeasons(view){const map=new Map();for(const row of view?.draft_picks||[]){const season=row?.pick?.season;if(season==null)continue;const bucket=map.get(season)||[];bucket.push(row);map.set(season,bucket)}return[...map.entries()].sort((a,b)=>a[0]-b[0])}
function myTeamStrengthDirection(value){if(typeof value!=='number')return'No current evidence';const delta=value-100;if(Math.abs(delta)<1)return'At league average';return`${Math.abs(delta).toFixed(0)}% ${delta>0?'above':'below'} league average`}
function myTeamStrengthBar(row){const value=Math.max(0,Math.min(160,row.strength_index));const pct=Math.min(100,value/1.6);return `<article class="franchise-position-row"><div class="franchise-position-label"><strong>${myTeamEsc(row.position)}</strong><span>${row.league_rank&&row.team_count?`#${row.league_rank} of ${row.team_count}`:'League rank unavailable'}</span></div><div class="franchise-position-track" aria-label="${myTeamEsc(row.position)} strength ${Math.round(row.strength_index)}, league average 100"><span style="width:${pct.toFixed(1)}%"></span><i style="left:62.5%" aria-hidden="true"></i></div><div class="franchise-position-value"><strong>${Math.round(row.strength_index)}</strong><span>${myTeamEsc(myTeamStrengthDirection(row.strength_index))}</span></div></article>`}
function myTeamAssetChip(row,index){return `<button type="button" class="franchise-asset" data-player-intelligence-id="${myTeamEsc(row.player.player_id)}"><span class="franchise-asset-rank">${index+1}</span><span><strong>${myTeamEsc(row.player.full_name)}</strong><small>${myTeamEsc(row.player.position)} · age ${myTeamAge(row.player.age_years)} · ${myTeamEsc(row.lens)}</small></span><b>${row.lens==='FSFFL Intrinsic'?(myTeamIntrinsicIndex(row.player.player_id)==null?`${Math.round(row.value*100)}th pct`:Math.round(myTeamIntrinsicIndex(row.player.player_id)).toLocaleString()):(myTeamMarketIndex(row.player)==null?`${Math.round(row.value*100)}th pct`:Math.round(myTeamMarketIndex(row.player)).toLocaleString())}</b></button>`}
function myTeamPickTrajectory(view){const seasons=myTeamPickSeasons(view);if(!seasons.length)return'<p class="franchise-empty">No owned draft picks are exposed in the current team view.</p>';return seasons.map(([season,rows])=>{const rounds=new Map();rows.forEach(row=>{const round=row.pick?.round;if(round!=null)rounds.set(round,(rounds.get(round)||0)+1)});const labels=[...rounds.entries()].sort((a,b)=>a[0]-b[0]).map(([round,count])=>`${count}× ${myTeamOrdinalRound(round)}`).join(' · ');return `<div class="franchise-pick-year"><strong>${season}</strong><span>${rows.length} pick${rows.length===1?'':'s'}</span><small>${myTeamEsc(labels||'Round detail unavailable')}</small></div>`}).join('')}
function myTeamStarterOrder(player){const order={QB:0,RB:10,WR:20,TE:30,FLEX:40,SUPERFLEX:50,K:60,DST:70};return order[player.projected_lineup_slot]??90}
function myTeamRosterRows(players){return[...(players||[])].sort((a,b)=>{if(Boolean(a.projected_starter)!==Boolean(b.projected_starter))return a.projected_starter?-1:1;if(a.projected_starter&&b.projected_starter){const d=myTeamStarterOrder(a)-myTeamStarterOrder(b);if(d)return d;return(myTeamProjectionNumber(b)??-Infinity)-(myTeamProjectionNumber(a)??-Infinity)}const slots={BENCH:0,TAXI:10,IR:20};const d=(slots[a.roster_slot]??30)-(slots[b.roster_slot]??30);if(d)return d;return(myTeamMarketNumber(b)??-Infinity)-(myTeamMarketNumber(a)??-Infinity)})}
function myTeamPlayerTable(rows,emptyText){const body=rows.map(player=>`<tr><td>${myTeamEsc(player.projected_starter?(player.projected_lineup_slot||'Starter'):player.roster_slot)}</td><td><button type="button" class="pi-player-link" data-player-intelligence-id="${myTeamEsc(player.player_id)}"><strong>${myTeamEsc(player.full_name)}</strong></button><small>${myTeamEsc(player.position)} · age ${myTeamAge(player.age_years)}</small></td><td>${myTeamProjection(player)}<small>${myTeamRankText(myTeamPositionRank(player,'projection'))} at ${myTeamEsc(player.position)}</small></td><td><strong>${myTeamMarket(player)}</strong><small>${myTeamRankText(myTeamPositionRank(player,'market'))} at ${myTeamEsc(player.position)}</small></td><td><strong>${myTeamIntrinsic(player.player_id)}</strong><small>${myTeamRankText(myTeamPositionRank(player,'intrinsic'))} at ${myTeamEsc(player.position)}</small></td></tr>`).join('');return `<div class="table-wrap franchise-table-wrap"><table><thead><tr><th>Role</th><th>Player</th><th>Season projection</th><th>Broad Market Value Index</th><th>FSFFL Intrinsic Value Index</th></tr></thead><tbody>${body||`<tr><td colspan="5">${myTeamEsc(emptyText)}</td></tr>`}</tbody></table></div>`}
function myTeamTabButton(id,label,active){return `<button type="button" role="tab" data-franchise-tab="${id}" aria-selected="${active?'true':'false'}">${label}</button>`}
function myTeamDiagnosisSentence(view,strongest,weakest){if(!view?.forecast_authority?.evidence_basis)return`Canonical roster State is current for ${view.display_name}. Forecast, Simulation-derived classification and position strength are not currently authoritative.`;const stateLabel=myTeamStateLabel(view.utility?.calculated_competitive_state);if(strongest&&weakest&&strongest.position!==weakest.position)return`${view.display_name} profiles as ${stateLabel}. ${strongest.position} is the clearest current lineup advantage; ${weakest.position} is the first position to investigate.`;if(strongest)return`${view.display_name} profiles as ${stateLabel}, with ${strongest.position} providing the clearest current lineup edge.`;return`${view.display_name} profiles as ${stateLabel}. Position-strength evidence is not currently available.`}

function renderMyTeamCommandCenter(){
  const panel=myTeamPanel();if(!panel)return;const view=fsfflMyTeamState.view;
  if(!view){panel.innerHTML='<p class="eyebrow">Franchise</p><h2>Unable to load your franchise.</h2>';return}
  const roster=myTeamRosterRows(view.players||[]),starters=roster.filter(player=>player.projected_starter),bench=roster.filter(player=>!player.projected_starter),outcome=view.utility?.competitive_outcome,resilience=view.utility?.roster_resilience;
  const stateOnly=!view.forecast_authority?.evidence_basis;
  const strengths=myTeamStrengths(view),strongest=strengths[0]||null,weakest=strengths[strengths.length-1]||null;
  const assets=myTeamRankedAssets(roster),core=assets.slice(0,3),benchAsset=assets.find(row=>!row.player.projected_starter)||null;
  const starterAge=myTeamAverageAge(starters),rosterAge=myTeamAverageAge(roster),stateLabel=myTeamStateLabel(view.utility?.calculated_competitive_state);
  const winRank=myTeamLeagueOutcomeRank('expected_wins'),playoffRank=myTeamLeagueOutcomeRank('playoff_probability');
  const fragility=typeof resilience?.largest_single_player_lineup_drop==='number'?resilience.largest_single_player_lineup_drop:null;
  const benchForecasted=resilience?.bench_forecasted_count,missingForecast=resilience?.missing_forecast_count;
  const picks=[...(view.draft_picks||[])].sort((a,b)=>(a.pick?.season??9999)-(b.pick?.season??9999)||(a.pick?.round??99)-(b.pick?.round??99));
  const pickRows=picks.length?picks.map(row=>`<tr><td><strong>${myTeamEsc(myTeamPickLabel(row))}</strong></td><td>${myTeamMarket({value_profile:row.value_profile})}</td></tr>`).join(''):'<tr><td colspan="2">No owned picks exposed.</td></tr>';

  panel.innerHTML=`<div class="franchise-shell">
    <header class="franchise-header"><div><p class="eyebrow">Franchise</p><h2>${myTeamEsc(view.display_name)}</h2><p>${myTeamEsc(myTeamDiagnosisSentence(view,strongest,weakest))}</p></div><span class="franchise-state">${myTeamEsc(stateLabel)}</span></header>
    <nav class="franchise-tabs" role="tablist" aria-label="Franchise views">${myTeamTabButton('diagnosis','Diagnosis',true)}${myTeamTabButton('roster','Roster',false)}${myTeamTabButton('assets','Assets & picks',false)}</nav>
    ${stateOnly?`<aside class="franchise-forecast-authority state-only"><strong>Roster State current · ${roster.length} players</strong><span>Canonical roster and picks are usable. Forecast, Simulation, position strength and competitive classification remain unavailable until their governed upstream evidence is authoritative. See the readiness strip for the exact blocker.</span></aside>`:(view.forecast_authority?.fallback_active?`<aside class="franchise-forecast-authority fallback"><strong>Preseason Forecast fallback active</strong><span>Season projections use the immutable preserved baseline from ${myTeamEsc(view.forecast_authority.evaluation_as_of||'the preseason snapshot')}. Live provider refresh did not satisfy the current source-health gate. Sources: ${myTeamEsc((view.forecast_authority.successful_source_ids||[]).join(', ')||'preserved baseline')}.</span></aside>`:`<aside class="franchise-forecast-authority"><strong>Current governed Forecast</strong><span>Evidence basis: ${myTeamEsc(view.forecast_authority?.evidence_basis||'unavailable')} · Sources: ${myTeamEsc((view.forecast_authority?.successful_source_ids||[]).join(', ')||'unavailable')} · As of ${myTeamEsc(view.forecast_authority?.evaluation_as_of||'—')}.</span></aside>`))}

    <section class="franchise-view" data-franchise-view="diagnosis">
      <section class="franchise-hero">
        <div class="franchise-hero-main"><span class="franchise-kicker">What is driving this team?</span><h3>${strongest?`${myTeamEsc(strongest.position)} carries the clearest edge.`:'Your competitive profile is the starting point.'}</h3><p>${strongest?`${myTeamEsc(strongest.position)} ranks ${strongest.league_rank?`#${strongest.league_rank} of ${strongest.team_count}`:'above the league baseline'} at ${Math.round(strongest.strength_index)} on the governed position-strength index. ${weakest&&weakest.position!==strongest.position?`${myTeamEsc(weakest.position)} is the pressure point at ${Math.round(weakest.strength_index)}.`:''}`:'Current position-strength evidence is unavailable; no substitute score is being invented.'}</p><div class="franchise-hero-actions"><button type="button" class="primary-button" data-franchise-route="opportunities">Find an upgrade</button><button type="button" class="secondary-button" data-franchise-route="trade_center">Build a trade</button></div></div>
        <div class="franchise-outlook"><span>Competitive outlook</span><strong>${myTeamNum(outcome?.expected_wins,2)} wins</strong><small>${winRank?`#${winRank.rank} of ${winRank.count} in expected wins`:'League rank unavailable'}</small><div><b>${myTeamPct(outcome?.playoff_probability,0)}</b><span>playoffs${playoffRank?` · #${playoffRank.rank}`:''}</span></div><div><b>${myTeamPct(outcome?.championship_probability,0)}</b><span>title</span></div></div>
      </section>

      <section class="franchise-section"><div class="franchise-section-head"><div><p class="eyebrow">Position profile</p><h3>Where the lineup wins — and where it bends</h3></div><span>100 = league average</span></div><div class="franchise-position-map">${strengths.length?strengths.map(myTeamStrengthBar).join(''):'<p class="franchise-empty">Position-strength evidence is unavailable.</p>'}</div></section>

      <section class="franchise-diagnosis-grid">
        <article class="franchise-focus"><span class="franchise-kicker">Vulnerability</span><h3>${fragility==null?'Resilience evidence unavailable':`${myTeamNum(fragility,1)} projected points at risk`}</h3><p>${fragility==null?'The current team view does not expose roster-resilience evidence.':`Largest projected lineup drop if one starter becomes unavailable. ${benchForecasted??'—'} bench players have forecast evidence${missingForecast!=null?`; ${missingForecast} roster forecasts are missing.`:'.'}`}</p><button type="button" data-franchise-route="what_if">Stress-test the roster →</button></article>
        <article class="franchise-focus"><span class="franchise-kicker">Core assets</span><h3>${core[0]?myTeamEsc(core[0].player.full_name):'Value evidence unavailable'}</h3><p>${core.length?`Your three highest current ${core[0]?.lens||'governed value'} percentiles are ${core.map(row=>row.player.full_name).join(', ')}.`:'No player Value evidence is attached.'}</p><button type="button" data-franchise-tab-open="assets">See asset base →</button></article>
        <article class="franchise-focus"><span class="franchise-kicker">Optionality</span><h3>${benchAsset?myTeamEsc(benchAsset.player.full_name):'No valued nonstarter exposed'}</h3><p>${benchAsset?`${myTeamEsc(benchAsset.player.position)} · ${myTeamEsc(benchAsset.lens)} ${Math.round(benchAsset.value*100)}th percentile. Highest-ranked nonstarter on that explicit lens.`:'No nonstarter with governed Market / Intrinsic evidence is available.'}</p><button type="button" data-franchise-tab-open="roster">See lineup & depth →</button></article>
      </section>

      <section class="franchise-section franchise-balance"><div><p class="eyebrow">Short term ↔ long term</p><h3>Roster age and draft-capital trajectory</h3><p>Descriptive evidence only: no presentation-layer dynasty score or age multiplier.</p></div><div class="franchise-age"><span>Projected starters</span><strong>${starterAge==null?'—':starterAge.toFixed(1)}</strong><small>average age</small></div><div class="franchise-age"><span>Full roster</span><strong>${rosterAge==null?'—':rosterAge.toFixed(1)}</strong><small>average age</small></div><div class="franchise-pick-strip">${myTeamPickTrajectory(view)}</div></section>
    </section>

    <section class="franchise-view" data-franchise-view="roster" hidden><div class="franchise-section-head"><div><p class="eyebrow">Optimized lineup</p><h3>Who is actually carrying the weekly roster?</h3><p>Forecast, Broad Market and FSFFL Intrinsic stay separate; no blended value score is created.</p></div></div>${myTeamPlayerTable(starters,'No projected starters available.')}<div class="franchise-section-head franchise-depth-head"><div><p class="eyebrow">Depth</p><h3>What sits behind the lineup?</h3></div></div>${myTeamPlayerTable(bench,'No nonstarters available.')}</section>

    <section class="franchise-view" data-franchise-view="assets" hidden><div class="franchise-assets-layout"><section><div class="franchise-section-head"><div><p class="eyebrow">Franchise core</p><h3>Highest-value roster assets</h3><p>Player assets use an explicit governed FSFFL Intrinsic percentile when ready, otherwise Broad Market. The two lenses are never blended.</p></div></div><div class="franchise-asset-list">${assets.slice(0,8).map(myTeamAssetChip).join('')||'<p class="franchise-empty">Player Value evidence is unavailable.</p>'}</div></section><section><div class="franchise-section-head"><div><p class="eyebrow">Draft capital</p><h3>Owned picks by season</h3></div></div><div class="franchise-pick-strip franchise-pick-strip-full">${myTeamPickTrajectory(view)}</div><div class="table-wrap franchise-pick-table"><table><thead><tr><th>Pick</th><th>Broad Market</th></tr></thead><tbody>${pickRows}</tbody></table></div></section></div></section>

    <details class="technical-evidence franchise-evidence"><summary>Evidence & model details</summary><div class="my-team-evidence"><p><strong>Team view:</strong> ${myTeamEsc(view.view_model_version||'—')}</p><p><strong>League comparison source:</strong> ${myTeamEsc(fsfflMyTeamState.leagueSource||'—')}</p><p><strong>Position strength:</strong> ${myTeamEsc(strengths[0]?.model_version||'—')}</p><p><strong>Utility:</strong> ${myTeamEsc(view.utility?.model_version||'—')}</p><p><strong>Simulation:</strong> ${myTeamEsc(outcome?.simulation_model_version||'—')}</p><p><strong>Value lenses:</strong> ${myTeamEsc(fsfflMyTeamState.valueLenses?.contract_version||'loading / unavailable')}</p><p><strong>State:</strong> ${myTeamEsc(view.context?.league_state_id||'—')}</p></div></details>
  </div>`;

  function activateTab(tab){panel.querySelectorAll('[data-franchise-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.franchiseTab===tab)));panel.querySelectorAll('[data-franchise-view]').forEach(section=>section.hidden=section.dataset.franchiseView!==tab)}
  panel.querySelectorAll('[data-franchise-tab]').forEach(button=>button.addEventListener('click',()=>activateTab(button.dataset.franchiseTab)));
  panel.querySelectorAll('[data-franchise-tab-open]').forEach(button=>button.addEventListener('click',()=>activateTab(button.dataset.franchiseTabOpen)));
  panel.querySelectorAll('[data-franchise-route]').forEach(button=>button.addEventListener('click',()=>setRoute(button.dataset.franchiseRoute)));
  if(stateOnly)activateTab('roster');
}

async function loadMyTeamValueLenses(expectedStateId){const generation=++fsfflMyTeamState.valueLensGeneration;fsfflMyTeamState.valueLensLoading=true;renderMyTeamCommandCenter();try{let payload=null;for(let attempt=0;attempt<80;attempt+=1){payload=await api('/api/league/value-lenses');if(generation!==fsfflMyTeamState.valueLensGeneration||state?.context?.state_id!==expectedStateId)return;if(payload?.status!=='loading')break;await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||1500))}if(payload?.status==='loading')payload={status:'unavailable',players:[],message:'FSFFL Intrinsic is still preparing; retry the Franchise view shortly.'};fsfflMyTeamState.valueLenses=payload}catch(error){if(generation!==fsfflMyTeamState.valueLensGeneration)return;fsfflMyTeamState.valueLenses={status:'unavailable',players:[],message:error?.message||String(error)}}finally{if(generation===fsfflMyTeamState.valueLensGeneration){fsfflMyTeamState.valueLensLoading=false;renderMyTeamCommandCenter()}}}

async function loadMyTeamCommandCenter(){
  const panel=myTeamPanel();
  if(!state?.context?.team_id){if(panel)panel.innerHTML='<p class="eyebrow">Franchise</p><h2>Select the franchise you manage.</h2><p class="lead">Choose a team from the product context to unlock the diagnosis.</p>';return}
  if(panel)panel.innerHTML='<p class="eyebrow">Franchise</p><h2>Reading the franchise…</h2><p class="lead">Loading optimized lineup, league-relative position strength, resilience, Value and draft capital.</p>';
  try{const[view,league]=await Promise.all([api('/api/my-team'),api('/api/league/team-views').catch(()=>({team_views:[],source_level:'unavailable'}))]);fsfflMyTeamState.view=view;fsfflMyTeamState.valueLenses=null;fsfflMyTeamState.leagueViews=league.team_views||[];fsfflMyTeamState.leagueSource=league.source_level||'';renderMyTeamCommandCenter();void loadMyTeamValueLenses(state.context?.state_id||null)}catch(error){if(panel)panel.innerHTML=`<p class="eyebrow">Franchise</p><h2>Unable to load your franchise.</h2><p class="lead">${myTeamEsc(error.message)}</p>`}
}
window.renderFsfflMyTeam=loadMyTeamCommandCenter;

(function installMyTeamStyles(){if(document.querySelector('#fsffl-franchise-diagnosis-style'))return;const style=document.createElement('style');style.id='fsffl-franchise-diagnosis-style';style.textContent=`
.franchise-shell{max-width:1180px;margin:0 auto}.franchise-forecast-authority{display:flex;gap:10px;justify-content:space-between;align-items:center;border:1px solid var(--line);border-radius:11px;padding:9px 12px;margin:-2px 0 12px;background:#09111e}.franchise-forecast-authority strong{font-size:11px}.franchise-forecast-authority span{font-size:10px;color:var(--muted);text-align:right}.franchise-forecast-authority.fallback{border-color:#a56b2e;background:rgba(165,107,46,.08)}.franchise-forecast-authority.state-only{border-color:#31536a;background:rgba(49,83,106,.12)}.franchise-header{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin-bottom:15px}.franchise-header h2{font-size:clamp(1.8rem,4vw,2.7rem);letter-spacing:-.04em;margin:2px 0 7px}.franchise-header>div>p:last-child{color:#cbd5e1;max-width:760px;line-height:1.5;margin:0}.franchise-state{border:1px solid var(--line);border-radius:999px;padding:8px 11px;color:var(--muted);font-size:11px;text-transform:capitalize;white-space:nowrap}.franchise-tabs{display:flex;gap:5px;border:1px solid var(--line);background:#080e1a;border-radius:13px;padding:4px;margin-bottom:13px;width:max-content;max-width:100%}.franchise-tabs button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:12px;font-weight:750;padding:8px 13px;border-radius:9px}.franchise-tabs button[aria-selected=true]{color:var(--text);background:#17233a;box-shadow:inset 0 0 0 1px #304562}.franchise-hero{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(250px,.65fr);gap:12px}.franchise-hero-main,.franchise-outlook,.franchise-section,.franchise-focus{border:1px solid var(--line);border-radius:17px;background:#0a1120}.franchise-hero-main{padding:22px;background:linear-gradient(135deg,rgba(16,43,62,.84),rgba(10,17,32,.97) 68%);border-color:#31536a}.franchise-kicker{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:850}.franchise-hero-main h3{font-size:clamp(1.5rem,3.5vw,2.35rem);letter-spacing:-.04em;line-height:1.08;margin:7px 0 10px}.franchise-hero-main p{color:#cbd5e1;line-height:1.5;max-width:720px}.franchise-hero-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}.franchise-outlook{padding:19px;display:grid;align-content:start;gap:8px}.franchise-outlook>span{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.franchise-outlook>strong{font-size:1.9rem}.franchise-outlook>small{color:var(--muted)}.franchise-outlook>div{display:flex;justify-content:space-between;gap:10px;border-top:1px solid var(--line);padding-top:10px;margin-top:2px}.franchise-outlook>div b{font-size:1.1rem}.franchise-outlook>div span{color:var(--muted);font-size:11px}.franchise-section{padding:17px;margin-top:12px}.franchise-section-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-bottom:12px}.franchise-section-head h3{margin:2px 0;font-size:1.1rem}.franchise-section-head p:not(.eyebrow){margin:5px 0 0;color:var(--muted);font-size:11px}.franchise-section-head>span{font-size:10px;color:var(--muted);white-space:nowrap}.franchise-position-map{display:grid;gap:5px}.franchise-position-row{display:grid;grid-template-columns:120px minmax(160px,1fr) 180px;gap:13px;align-items:center;padding:9px 0;border-top:1px solid rgba(51,65,85,.48)}.franchise-position-row:first-child{border-top:0}.franchise-position-label,.franchise-position-value{display:grid;gap:2px}.franchise-position-label strong{font-size:13px}.franchise-position-label span,.franchise-position-value span{font-size:10px;color:var(--muted)}.franchise-position-track{height:9px;border-radius:99px;background:#151f31;position:relative;overflow:hidden}.franchise-position-track>span{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#3b82f6,#22c55e)}.franchise-position-track>i{position:absolute;top:-2px;bottom:-2px;width:1px;background:#f8fafc;opacity:.75}.franchise-position-value{justify-items:end}.franchise-position-value strong{font-size:15px}.franchise-diagnosis-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:12px}.franchise-focus{padding:15px}.franchise-focus h3{margin:6px 0 7px;font-size:1.08rem}.franchise-focus p{color:var(--muted);font-size:11px;line-height:1.45;min-height:48px}.franchise-focus button{border:0;background:transparent;color:var(--accent);font:inherit;font-size:11px;padding:4px 0}.franchise-balance{display:grid;grid-template-columns:minmax(220px,1.2fr) 120px 120px minmax(280px,1.4fr);gap:16px;align-items:center}.franchise-balance h3{margin:3px 0}.franchise-balance>div:first-child>p:last-child{color:var(--muted);font-size:10px}.franchise-age{display:grid;gap:2px}.franchise-age span,.franchise-age small{color:var(--muted);font-size:10px}.franchise-age strong{font-size:1.45rem}.franchise-pick-strip{display:flex;gap:7px;overflow:auto;padding-bottom:2px}.franchise-pick-year{min-width:92px;border-left:2px solid #31536a;padding:4px 8px;display:grid;gap:2px}.franchise-pick-year strong{font-size:13px}.franchise-pick-year span,.franchise-pick-year small{font-size:9px;color:var(--muted)}.franchise-depth-head{margin-top:22px}.franchise-table-wrap table td:nth-child(2){min-width:170px}.franchise-table-wrap td small{display:block;color:var(--muted);font-size:9px;margin-top:2px}.franchise-assets-layout{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr);gap:14px}.franchise-assets-layout>section{border:1px solid var(--line);border-radius:17px;background:#0a1120;padding:17px}.franchise-asset-list{display:grid;gap:6px}.franchise-asset{border:1px solid var(--line);border-radius:12px;background:#0d1627;color:var(--text);padding:10px;display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:9px;align-items:center;text-align:left;font:inherit}.franchise-asset-rank{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:#17233a;color:var(--muted);font-size:10px}.franchise-asset>span:nth-child(2){display:grid;gap:2px}.franchise-asset small{color:var(--muted);font-size:10px}.franchise-asset>b{font-size:12px;color:#dbeafe}.franchise-pick-strip-full{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));overflow:visible}.franchise-pick-table{margin-top:14px}.franchise-evidence{margin-top:16px}.franchise-empty{color:var(--muted);font-size:11px}.my-team-evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.my-team-evidence p{margin:0;font-size:10px;color:var(--muted)}
@media(max-width:820px){.franchise-hero{grid-template-columns:1fr}.franchise-diagnosis-grid{grid-template-columns:1fr}.franchise-balance{grid-template-columns:repeat(2,minmax(0,1fr))}.franchise-balance>div:first-child,.franchise-pick-strip{grid-column:1/-1}.franchise-assets-layout{grid-template-columns:1fr}.franchise-position-row{grid-template-columns:80px minmax(110px,1fr) 96px}.franchise-position-value span{display:none}}
@media(max-width:560px){.franchise-header{align-items:flex-start}.franchise-header .franchise-state{margin-top:4px}.franchise-tabs{width:100%}.franchise-tabs button{flex:1;padding:8px 6px}.franchise-hero-main,.franchise-outlook,.franchise-section{padding:14px}.franchise-hero-actions{display:grid}.franchise-position-row{grid-template-columns:58px minmax(80px,1fr) 58px;gap:8px}.franchise-position-label span{display:none}.franchise-position-value strong{font-size:13px}.franchise-balance{grid-template-columns:1fr 1fr}.franchise-pick-strip-full{grid-template-columns:1fr}.franchise-table-wrap{margin-left:-14px;margin-right:-14px;border-radius:0}.my-team-evidence{grid-template-columns:1fr}}
`;document.head.appendChild(style)})();


/* Franchise North Star 2026-09-24.
 * Presentation-only recomposition of existing governed Franchise evidence.
 * Uses /api/my-team, /api/league/team-views, /api/home and the existing
 * /api/league/value-lenses read path. It does not launch Forecast,
 * Simulation, Value reconstruction, Decision, Search, or Optimization work.
 */
Object.assign(fsfflMyTeamState,{
  franchiseTab:'overview',
  franchisePositionLens:'rank',
  franchiseExpandedPosition:null,
  franchiseRosterFilter:'starters',
  franchiseAssetLens:'market',
  franchisePickLens:'count',
  franchiseExpandedPickSeason:null,
  franchiseHome:null,
});
const FSFFL_FRANCHISE_GAME_BASIS=17;
const FSFFL_FRANCHISE_POSITIONS=['QB','RB','WR','TE'];

function franchiseNSStateId(){
  return fsfflMyTeamState.view?.context?.league_state_id||null;
}
function franchiseNSHome(){
  const home=fsfflMyTeamState.franchiseHome;
  return home&&home.league_state_id===franchiseNSStateId()?home:null;
}
function franchiseNSStandings(){
  return franchiseNSHome()?.standings||[];
}
function franchiseNSStanding(){
  const id=state?.context?.team_id;
  return franchiseNSStandings().find(row=>row.team_id===id)||null;
}
function franchiseNSSimulation(){
  const home=franchiseNSHome(),id=state?.context?.team_id;
  if(!home||home.simulation?.status!=='ready')return null;
  return (home.simulation.teams||[]).find(row=>row.team_id===id)||null;
}
function franchiseNSPositionRows(){
  const view=fsfflMyTeamState.view;
  return FSFFL_FRANCHISE_POSITIONS.map(position=>(view?.position_strengths||[]).find(row=>row.position===position)||null);
}
function franchiseNSPositionBand(row){
  if(!row)return'unknown';
  const count=Number(row.team_count||fsfflMyTeamState.leagueViews.length||12);
  const rank=Number(row.league_rank);
  if(!Number.isFinite(rank)||!Number.isFinite(count)||count<=1)return'unknown';
  const share=(rank-1)/(count-1);
  if(share<=.2)return'strong';
  if(share<=.7)return'middle';
  return'weak';
}
function franchiseNSPositionPlayers(position){
  const rows=myTeamRosterRows(fsfflMyTeamState.view?.players||[]).filter(player=>player.position===position);
  return rows;
}
function franchiseNSFragility(){
  const view=fsfflMyTeamState.view,resilience=view?.utility?.roster_resilience;
  if(!resilience||typeof resilience.largest_single_player_lineup_drop!=='number')return null;
  const ids=resilience.largest_single_player_lineup_drop_player_ids||[];
  const player=ids.length?(view.players||[]).find(row=>row.player_id===ids[0]):null;
  return{
    drop:resilience.largest_single_player_lineup_drop,
    playerId:player?.player_id||ids[0]||null,
    playerName:player?.full_name||null,
    position:player?.position||null,
    benchForecasted:resilience.bench_forecasted_count,
    missingForecast:resilience.missing_forecast_count,
  };
}
function franchiseNSSeasonProjection(player){
  const value=myTeamProjectionNumber(player);
  return typeof value==='number'&&Number.isFinite(value)?value:null;
}
function franchiseNSPpg(player){
  const season=franchiseNSSeasonProjection(player);
  return season==null?null:season/FSFFL_FRANCHISE_GAME_BASIS;
}
function franchiseNSMarketPercentile(player){return myTeamMarketNumber(player)}
function franchiseNSIntrinsicPercentile(player){return myTeamIntrinsicNumber(player?.player_id)}
function franchiseNSLensPercentile(player,lens){
  return lens==='intrinsic'?franchiseNSIntrinsicPercentile(player):franchiseNSMarketPercentile(player);
}
function franchiseNSMarketDisplay(player){
  const index=myTeamMarketIndex(player),pct=franchiseNSMarketPercentile(player);
  if(index!=null)return '<strong>'+Math.round(index).toLocaleString()+'</strong><small>'+(pct==null?'Broad Market':Math.round(pct*100)+'th pct')+'</small>';
  if(pct!=null)return '<strong>'+Math.round(pct*100)+'th</strong><small>Broad Market pct</small>';
  return '<strong>—</strong><small>Market unavailable</small>';
}
function franchiseNSIntrinsicReason(){
  return fsfflMyTeamState.valueLenses?.fsffl_intrinsic?.reason||
    fsfflMyTeamState.valueLenses?.message||
    'Governed FSFFL Intrinsic is unavailable for the current league state.';
}
function franchiseNSIntrinsicDisplay(player){
  const index=myTeamIntrinsicIndex(player?.player_id),pct=franchiseNSIntrinsicPercentile(player);
  if(index!=null)return '<strong>'+Math.round(index).toLocaleString()+'</strong><small>'+(pct==null?'FSFFL Intrinsic':Math.round(pct*100)+'th pct')+'</small>';
  if(fsfflMyTeamState.valueLensLoading)return '<strong>…</strong><small>Intrinsic preparing</small>';
  if(pct!=null)return '<strong>'+Math.round(pct*100)+'th</strong><small>Intrinsic pct</small>';
  return '<strong>—</strong><small title="'+myTeamEsc(franchiseNSIntrinsicReason())+'">Intrinsic unavailable</small>';
}
function franchiseNSProjectedStarter(player){
  return player?.projected_starter===true;
}
function franchiseNSPlayerRole(player){
  if(franchiseNSProjectedStarter(player))return player.projected_lineup_slot||'Starter';
  if(player?.roster_slot==='TAXI')return'Taxi';
  if(player?.roster_slot==='IR')return'IR';
  return'Bench';
}
function franchiseNSPlayerRow(player){
  const ppg=franchiseNSPpg(player),season=franchiseNSSeasonProjection(player);
  return '<button type="button" class="franchise-ns-player-row" data-player-intelligence-id="'+myTeamEsc(player.player_id)+'">'+
    '<span class="franchise-ns-player-id"><i>'+myTeamEsc(player.position||'—')+'</i><span><strong>'+myTeamEsc(player.full_name)+'</strong><small>'+myTeamEsc(franchiseNSPlayerRole(player))+' · Age '+myTeamAge(player.age_years)+'</small></span></span>'+
    '<span class="franchise-ns-player-stat"><small>PPG</small><strong>'+(ppg==null?'—':ppg.toFixed(1))+'</strong></span>'+
    '<span class="franchise-ns-player-stat"><small>Proj · 17g</small><strong>'+(season==null?'—':season.toFixed(1))+'</strong></span>'+
    '<span class="franchise-ns-player-value market"><small>Broad Market</small>'+franchiseNSMarketDisplay(player)+'</span>'+
    '<span class="franchise-ns-player-value intrinsic"><small>FSFFL Intrinsic</small>'+franchiseNSIntrinsicDisplay(player)+'</span>'+
    '<b class="franchise-ns-chevron" aria-hidden="true">›</b>'+
  '</button>';
}
function franchiseNSRankedAssets(lens,onlyNonstarters){
  const roster=fsfflMyTeamState.view?.players||[];
  return roster
    .filter(player=>!onlyNonstarters||!franchiseNSProjectedStarter(player))
    .map(player=>({player,value:franchiseNSLensPercentile(player,lens)}))
    .filter(row=>typeof row.value==='number'&&Number.isFinite(row.value))
    .sort((a,b)=>b.value-a.value||a.player.full_name.localeCompare(b.player.full_name));
}
function franchiseNSAssetValue(player,lens){
  return lens==='intrinsic'?franchiseNSIntrinsicDisplay(player):franchiseNSMarketDisplay(player);
}
function franchiseNSAssetCard(row,index,lens){
  return '<button type="button" class="franchise-ns-asset-card" data-player-intelligence-id="'+myTeamEsc(row.player.player_id)+'">'+
    '<span class="franchise-ns-asset-rank">'+(index+1)+'</span>'+
    '<span class="franchise-ns-asset-main"><i>'+myTeamEsc(row.player.position||'—')+'</i><strong>'+myTeamEsc(row.player.full_name)+'</strong><small>Age '+myTeamAge(row.player.age_years)+'</small></span>'+
    '<span class="franchise-ns-asset-value">'+franchiseNSAssetValue(row.player,lens)+'</span>'+
    '<b aria-hidden="true">›</b>'+
  '</button>';
}
function franchiseNSPickPercentile(row){
  const estimate=row?.value_profile?.market_price;
  if(estimate?.scale?.scale_id!=='dynasty-market-percentile')return null;
  const value=estimate?.distribution?.mean;
  return typeof value==='number'&&Number.isFinite(value)?value:null;
}
function franchiseNSPickValueLabel(row){
  const pct=franchiseNSPickPercentile(row);
  return pct==null?'Value unavailable':Math.round(pct*100)+'th pct';
}
function franchiseNSPickSeasons(){
  return myTeamPickSeasons(fsfflMyTeamState.view);
}
function franchiseNSPickSeasonMarkup(compact){
  const seasons=franchiseNSPickSeasons();
  if(!seasons.length)return '<p class="franchise-ns-empty">No owned draft picks are exposed in the current State.</p>';
  const mode=fsfflMyTeamState.franchisePickLens;
  const expanded=fsfflMyTeamState.franchiseExpandedPickSeason;
  return seasons.map(([season,rows])=>{
    const valueText=rows.map(row=>{
      const round=row.pick?.round!=null?myTeamOrdinalRound(row.pick.round):'Pick';
      return round+' '+franchiseNSPickValueLabel(row);
    }).join(' · ');
    const summary=mode==='value'?(valueText||'No pick Value evidence'):rows.length+' pick'+(rows.length===1?'':'s');
    const detail=rows.map(row=>'<span><strong>'+myTeamEsc(myTeamPickLabel(row))+'</strong><small>Broad Market · '+myTeamEsc(franchiseNSPickValueLabel(row))+'</small></span>').join('');
    return '<article class="franchise-ns-pick-year'+(String(expanded)===String(season)?' expanded':'')+'">'+
      '<button type="button" data-franchise-pick-season="'+myTeamEsc(season)+'"><span><strong>'+myTeamEsc(season)+'</strong><small>'+myTeamEsc(summary)+'</small></span><b aria-hidden="true">'+(String(expanded)===String(season)?'−':'+')+'</b></button>'+
      (String(expanded)===String(season)?'<div class="franchise-ns-pick-detail">'+detail+'</div>':'')+
    '</article>';
  }).join('');
}
function franchiseNSPickValueAvailable(){
  return (fsfflMyTeamState.view?.draft_picks||[]).some(row=>franchiseNSPickPercentile(row)!=null);
}
function franchiseNSCurrentRank(){
  const standing=franchiseNSStanding();
  return standing?.rank||null;
}
function franchiseNSStrongWeak(){
  const rows=franchiseNSPositionRows().filter(Boolean).filter(row=>typeof row.strength_index==='number');
  if(!rows.length)return{strongest:null,weakest:null};
  const sorted=[...rows].sort((a,b)=>b.strength_index-a.strength_index);
  return{strongest:sorted[0]||null,weakest:sorted[sorted.length-1]||null};
}
function franchiseNSFoundationPlayers(position){
  if(!position)return[];
  return franchiseNSPositionPlayers(position).slice(0,3);
}
function franchiseNSPositionRing(row){
  if(!row)return '<div class="franchise-ns-position-ring unavailable"><span>—</span><small>No evidence</small></div>';
  const mode=fsfflMyTeamState.franchisePositionLens;
  const count=row.team_count||fsfflMyTeamState.leagueViews.length||12;
  const value=mode==='index'?Math.round(row.strength_index):'#'+(row.league_rank||'—');
  const sub=mode==='index'?'Index · 100 avg':'of '+count;
  return '<button type="button" class="franchise-ns-position-ring '+franchiseNSPositionBand(row)+(fsfflMyTeamState.franchiseExpandedPosition===row.position?' selected':'')+'" data-franchise-position="'+myTeamEsc(row.position)+'">'+
    '<span>'+myTeamEsc(row.position)+'</span><i><strong>'+myTeamEsc(value)+'</strong></i><small>'+myTeamEsc(sub)+'</small>'+
  '</button>';
}
function franchiseNSPositionDetail(){
  const position=fsfflMyTeamState.franchiseExpandedPosition;
  if(!position)return'';
  const row=franchiseNSPositionRows().find(item=>item?.position===position),players=franchiseNSPositionPlayers(position),fragility=franchiseNSFragility();
  if(!row)return'';
  return '<div class="franchise-ns-position-detail">'+
    '<div class="franchise-ns-position-detail-head"><span><strong>'+myTeamEsc(position)+' room</strong><small>#'+myTeamEsc(row.league_rank||'—')+' of '+myTeamEsc(row.team_count||fsfflMyTeamState.leagueViews.length||'—')+' · Strength Index '+myTeamNum(row.strength_index,0)+'</small></span><button type="button" data-franchise-position-close aria-label="Close '+myTeamEsc(position)+' detail">×</button></div>'+
    '<div class="franchise-ns-position-players">'+players.map(player=>{
      const exposed=fragility?.playerId===player.player_id;
      return '<button type="button" data-player-intelligence-id="'+myTeamEsc(player.player_id)+'"><span><strong>'+myTeamEsc(player.full_name)+'</strong><small>'+myTeamEsc(franchiseNSPlayerRole(player))+' · Age '+myTeamAge(player.age_years)+'</small></span>'+(exposed?'<em>Largest exposure</em>':'')+'<b>›</b></button>';
    }).join('')+'</div>'+
    (fragility&&fragility.position===position?'<p>Largest one-player lineup drop: <strong>'+myTeamNum(fragility.drop,1)+' projected points</strong>'+(fragility.playerName?' · '+myTeamEsc(fragility.playerName):'')+'.</p>':'')+
  '</div>';
}
function franchiseNSOverview(){
  const view=fsfflMyTeamState.view,simulation=franchiseNSSimulation(),standing=franchiseNSStanding(),rank=franchiseNSCurrentRank();
  const {strongest,weakest}=franchiseNSStrongWeak(),foundation=franchiseNSFoundationPlayers(strongest?.position),fragility=franchiseNSFragility();
  const starterAge=view?.starter_average_age??myTeamAverageAge((view?.players||[]).filter(player=>player.projected_starter));
  const rosterAge=view?.roster_average_age??myTeamAverageAge(view?.players||[]);
  const pressureAction=weakest?'<button type="button" class="franchise-ns-context-action" data-franchise-market-position="'+myTeamEsc(weakest.position)+'">Explore '+myTeamEsc(weakest.position)+' upgrades <b>→</b></button>':'';
  const foundationNames=foundation.length?foundation.map(player=>player.full_name).join(' · '):'Player detail unavailable';
  const positionRows=franchiseNSPositionRows();
  return '<section class="franchise-ns-view" data-franchise-view="overview">'+
    '<section class="franchise-ns-outlook" aria-label="Competitive outlook">'+
      '<div><small>Expected wins</small><strong>'+myTeamNum(simulation?.expected_wins,1)+'</strong></div>'+
      '<div><small>Playoffs</small><strong>'+myTeamPct(simulation?.playoff_probability,0)+'</strong></div>'+
      '<div><small>Championship</small><strong>'+myTeamPct(simulation?.championship_probability,0)+'</strong></div>'+
      '<div><small>League rank</small><strong>'+(rank?'#'+rank:'—')+'</strong><span>'+(standing?myTeamEsc(String(standing.wins??0)+'-'+String(standing.losses??0)+(Number(standing.ties||0)>0?'-'+String(standing.ties):'')):'Current standings unavailable')+'</span></div>'+
    '</section>'+
    '<section class="franchise-ns-section franchise-ns-position-section">'+
      '<div class="franchise-ns-section-head"><div><p class="eyebrow">Position strength</p><h3>How the starting lineup stacks up</h3></div><div class="franchise-ns-segment" role="group" aria-label="Position strength lens"><button type="button" data-franchise-position-lens="rank" aria-pressed="'+(fsfflMyTeamState.franchisePositionLens==='rank')+'">Rank</button><button type="button" data-franchise-position-lens="index" aria-pressed="'+(fsfflMyTeamState.franchisePositionLens==='index')+'">Index</button></div></div>'+
      '<div class="franchise-ns-position-grid">'+positionRows.map(franchiseNSPositionRing).join('')+'</div>'+
      franchiseNSPositionDetail()+
    '</section>'+
    '<section class="franchise-ns-section"><div class="franchise-ns-section-head"><div><p class="eyebrow">What defines this franchise</p><h3>Three structural facts</h3></div></div>'+
      '<div class="franchise-ns-diagnosis">'+
        '<article class="foundation"><span>Foundation</span><h4>'+(strongest?myTeamEsc(strongest.position)+' is the clearest strength':'Strength unavailable')+'</h4><p>'+(strongest?'#'+myTeamEsc(strongest.league_rank||'—')+' of '+myTeamEsc(strongest.team_count||'—')+' · Index '+myTeamNum(strongest.strength_index,0)+' · '+myTeamEsc(foundationNames):'Position-strength evidence has not attached.')+'</p></article>'+
        '<article class="pressure"><span>Pressure point</span><h4>'+(weakest?myTeamEsc(weakest.position)+' is the first position to investigate':'Pressure point unavailable')+'</h4><p>'+(weakest?'#'+myTeamEsc(weakest.league_rank||'—')+' of '+myTeamEsc(weakest.team_count||'—')+' · Index '+myTeamNum(weakest.strength_index,0)+'. Descriptive diagnosis only.':'Position-strength evidence has not attached.')+'</p></article>'+
        '<article class="exposure"><span>Largest single-player exposure</span><h4>'+(fragility?(fragility.playerName?myTeamEsc(fragility.playerName):myTeamNum(fragility.drop,1)+' projected points'):'Exposure unavailable')+'</h4><p>'+(fragility?(fragility.playerName?myTeamNum(fragility.drop,1)+' projected-point lineup drop if unavailable.':'Largest projected lineup drop: '+myTeamNum(fragility.drop,1)+' points.'):'Roster-resilience evidence has not attached.')+'</p></article>'+
      '</div>'+
    '</section>'+
    '<section class="franchise-ns-age-row"><div><small>Projected starter age</small><strong>'+(starterAge==null?'—':starterAge.toFixed(1))+'</strong></div><div><small>Full-roster age</small><strong>'+(rosterAge==null?'—':rosterAge.toFixed(1))+'</strong></div><p>Descriptive age profile only.</p></section>'+
    '<section class="franchise-ns-section franchise-ns-draft">'+
      '<div class="franchise-ns-section-head"><div><p class="eyebrow">Draft capital</p><h3>Future runway</h3></div><div class="franchise-ns-segment" role="group" aria-label="Draft capital lens"><button type="button" data-franchise-pick-lens="count" aria-pressed="'+(fsfflMyTeamState.franchisePickLens==='count')+'">Count</button><button type="button" data-franchise-pick-lens="value" aria-pressed="'+(fsfflMyTeamState.franchisePickLens==='value')+'" '+(franchiseNSPickValueAvailable()?'':'disabled')+'>Value</button></div></div>'+
      '<div class="franchise-ns-pick-years">'+franchiseNSPickSeasonMarkup(true)+'</div>'+
      (!franchiseNSPickValueAvailable()?'<p class="franchise-ns-note">Broad Market pick Value evidence is unavailable; literal owned-pick inventory remains visible.</p>':'')+
    '</section>'+
    pressureAction+
  '</section>';
}
function franchiseNSRoster(){
  const roster=myTeamRosterRows(fsfflMyTeamState.view?.players||[]);
  const filter=fsfflMyTeamState.franchiseRosterFilter;
  const rows=filter==='starters'?roster.filter(franchiseNSProjectedStarter):filter==='bench'?roster.filter(player=>!franchiseNSProjectedStarter(player)):roster;
  return '<section class="franchise-ns-view" data-franchise-view="roster">'+
    '<div class="franchise-ns-roster-head"><div><p class="eyebrow">Roster</p><h3>Lineup and depth</h3><p>PPG and projected season points use the same governed full-season Forecast on a 17-game display basis.</p></div>'+
    '<div class="franchise-ns-segment franchise-ns-roster-filter" role="group" aria-label="Roster filter"><button type="button" data-franchise-roster-filter="starters" aria-pressed="'+(filter==='starters')+'">Starters</button><button type="button" data-franchise-roster-filter="bench" aria-pressed="'+(filter==='bench')+'">Bench</button><button type="button" data-franchise-roster-filter="all" aria-pressed="'+(filter==='all')+'">All Players</button></div></div>'+
    '<div class="franchise-ns-player-list">'+(rows.length?rows.map(franchiseNSPlayerRow).join(''):'<p class="franchise-ns-empty">No players in this roster view.</p>')+'</div>'+
  '</section>';
}
function franchiseNSAssets(){
  const lens=fsfflMyTeamState.franchiseAssetLens,all=franchiseNSRankedAssets(lens,false),flex=franchiseNSRankedAssets(lens,true);
  const intrinsicReady=!fsfflMyTeamState.valueLensLoading&&(fsfflMyTeamState.valueLenses?.fsffl_intrinsic?.status||'')!=='unavailable';
  const taxi=(fsfflMyTeamState.view?.players||[]).filter(player=>player.roster_slot==='TAXI');
  const ir=(fsfflMyTeamState.view?.players||[]).filter(player=>player.roster_slot==='IR');
  const extra=[];
  if(taxi.length)extra.push('<span><strong>'+taxi.length+' taxi</strong><small>'+myTeamEsc(taxi.map(player=>player.full_name).join(' · '))+'</small></span>');
  if(ir.length)extra.push('<span><strong>'+ir.length+' reserve / IR</strong><small>'+myTeamEsc(ir.map(player=>player.full_name).join(' · '))+'</small></span>');
  return '<section class="franchise-ns-view" data-franchise-view="assets">'+
    '<div class="franchise-ns-assets-top"><div><p class="eyebrow">Value lens</p><h3>What is this franchise built around?</h3></div><div class="franchise-ns-segment" role="group" aria-label="Franchise asset value lens"><button type="button" data-franchise-asset-lens="market" aria-pressed="'+(lens==='market')+'">Broad Market</button><button type="button" data-franchise-asset-lens="intrinsic" aria-pressed="'+(lens==='intrinsic')+'" '+(intrinsicReady?'':'disabled')+'>FSFFL Intrinsic</button></div></div>'+
    (lens==='intrinsic'&&!intrinsicReady?'<p class="franchise-ns-warning">FSFFL Intrinsic is '+(fsfflMyTeamState.valueLensLoading?'preparing.':myTeamEsc(franchiseNSIntrinsicReason()))+'</p>':'')+
    '<section class="franchise-ns-section"><div class="franchise-ns-section-head"><div><p class="eyebrow">Franchise core</p><h3>Highest-value roster assets</h3><p>Descriptive ranking under the explicitly selected lens.</p></div></div><div class="franchise-ns-asset-grid">'+(all.length?all.slice(0,4).map((row,index)=>franchiseNSAssetCard(row,index,lens)).join(''):'<p class="franchise-ns-empty">Selected-lens player Value evidence is unavailable.</p>')+'</div></section>'+
    '<section class="franchise-ns-section"><div class="franchise-ns-section-head"><div><p class="eyebrow">Flexible assets</p><h3>Valuable nonstarters and depth</h3><p>Highest-value players not currently projected to start. This describes optionality; it is not a trade recommendation.</p></div></div><div class="franchise-ns-asset-grid">'+(flex.length?flex.slice(0,4).map((row,index)=>franchiseNSAssetCard(row,index,lens)).join(''):'<p class="franchise-ns-empty">No valued nonstarters are available under the selected lens.</p>')+'</div></section>'+
    '<section class="franchise-ns-section franchise-ns-draft"><div class="franchise-ns-section-head"><div><p class="eyebrow">Draft capital</p><h3>Owned picks by season</h3><p>Player lens selection never changes universal pick evidence.</p></div><div class="franchise-ns-segment" role="group" aria-label="Draft pick display"><button type="button" data-franchise-pick-lens="count" aria-pressed="'+(fsfflMyTeamState.franchisePickLens==='count')+'">Picks</button><button type="button" data-franchise-pick-lens="value" aria-pressed="'+(fsfflMyTeamState.franchisePickLens==='value')+'" '+(franchiseNSPickValueAvailable()?'':'disabled')+'>Value</button></div></div><div class="franchise-ns-pick-years">'+franchiseNSPickSeasonMarkup(false)+'</div></section>'+
    '<section class="franchise-ns-additional"><p class="eyebrow">Additional assets</p><div>'+(extra.length?extra.join(''):'<span><strong>No separate future-asset buckets exposed</strong><small>Current State does not expose additional taxi / reserve groupings beyond the roster above.</small></span>')+'</div></section>'+
  '</section>';
}
function renderFranchiseNorthStar(){
  const panel=myTeamPanel(),view=fsfflMyTeamState.view;
  if(!panel)return;
  if(!view){panel.innerHTML='<div class="franchise-ns-shell"><p class="eyebrow">Franchise</p><h2>Unable to load your franchise.</h2></div>';return}
  const stateLabel=myTeamStateLabel(view.utility?.calculated_competitive_state),rank=franchiseNSCurrentRank();
  const fallback=view.forecast_authority?.fallback_active;
  panel.innerHTML='<div class="franchise-ns-shell">'+
    '<header class="franchise-ns-header"><div class="franchise-ns-mark" aria-hidden="true">'+myTeamEsc((view.display_name||'?').slice(0,1).toUpperCase())+'</div><div><p class="eyebrow">Franchise</p><h2>'+myTeamEsc(view.display_name)+'</h2><p><strong>'+myTeamEsc(stateLabel)+'</strong>'+(rank?' · #'+rank+' of '+franchiseNSStandings().length:' · League rank unavailable')+'</p></div></header>'+
    '<nav class="franchise-ns-tabs" role="tablist" aria-label="Franchise views">'+
      myTeamTabButton('overview','Overview',fsfflMyTeamState.franchiseTab==='overview')+
      myTeamTabButton('roster','Roster',fsfflMyTeamState.franchiseTab==='roster')+
      myTeamTabButton('assets','Assets & Picks',fsfflMyTeamState.franchiseTab==='assets')+
    '</nav>'+
    (fallback?'<aside class="franchise-ns-forecast-strip" role="status"><strong>Forecast fallback active</strong><span>Preserved preseason projections in use · live source-health degraded.</span></aside>':'')+
    (fsfflMyTeamState.franchiseTab==='overview'?franchiseNSOverview():fsfflMyTeamState.franchiseTab==='roster'?franchiseNSRoster():franchiseNSAssets())+
  '</div>';
  panel.querySelectorAll('[data-franchise-tab]').forEach(button=>button.addEventListener('click',()=>{fsfflMyTeamState.franchiseTab=button.dataset.franchiseTab;renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-position-lens]').forEach(button=>button.addEventListener('click',()=>{fsfflMyTeamState.franchisePositionLens=button.dataset.franchisePositionLens==='index'?'index':'rank';renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-position]').forEach(button=>button.addEventListener('click',()=>{const pos=button.dataset.franchisePosition;fsfflMyTeamState.franchiseExpandedPosition=fsfflMyTeamState.franchiseExpandedPosition===pos?null:pos;renderFranchiseNorthStar()}));
  panel.querySelector('[data-franchise-position-close]')?.addEventListener('click',()=>{fsfflMyTeamState.franchiseExpandedPosition=null;renderFranchiseNorthStar()});
  panel.querySelectorAll('[data-franchise-roster-filter]').forEach(button=>button.addEventListener('click',()=>{fsfflMyTeamState.franchiseRosterFilter=button.dataset.franchiseRosterFilter;renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-asset-lens]').forEach(button=>button.addEventListener('click',()=>{if(button.disabled)return;fsfflMyTeamState.franchiseAssetLens=button.dataset.franchiseAssetLens;renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-pick-lens]').forEach(button=>button.addEventListener('click',()=>{if(button.disabled)return;fsfflMyTeamState.franchisePickLens=button.dataset.franchisePickLens;renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-pick-season]').forEach(button=>button.addEventListener('click',()=>{const season=button.dataset.franchisePickSeason;fsfflMyTeamState.franchiseExpandedPickSeason=String(fsfflMyTeamState.franchiseExpandedPickSeason)===String(season)?null:season;renderFranchiseNorthStar()}));
  panel.querySelectorAll('[data-franchise-market-position]').forEach(button=>button.addEventListener('click',()=>{
    const intent={route:'opportunities',teamId:state?.context?.team_id||null,position:button.dataset.franchiseMarketPosition||null,source:'franchise-pressure'};
    if(typeof window.fsfflNavigateTo==='function')window.fsfflNavigateTo(intent);else if(typeof setRoute==='function')setRoute('opportunities');
  }));
}
async function loadFranchiseNorthStarValueLenses(expectedStateId){
  const generation=++fsfflMyTeamState.valueLensGeneration;
  fsfflMyTeamState.valueLensLoading=true;renderFranchiseNorthStar();
  try{
    let payload=null;
    for(let attempt=0;attempt<80;attempt+=1){
      payload=await api('/api/league/value-lenses');
      if(generation!==fsfflMyTeamState.valueLensGeneration||state?.context?.state_id!==expectedStateId)return;
      if(payload?.status!=='loading')break;
      await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||1500));
    }
    if(payload?.status==='loading')payload={status:'unavailable',players:[],message:'FSFFL Intrinsic is still preparing; retry the Franchise view shortly.'};
    fsfflMyTeamState.valueLenses=payload;
  }catch(error){
    if(generation!==fsfflMyTeamState.valueLensGeneration)return;
    fsfflMyTeamState.valueLenses={status:'unavailable',players:[],message:error?.message||String(error)};
  }finally{
    if(generation===fsfflMyTeamState.valueLensGeneration){fsfflMyTeamState.valueLensLoading=false;renderFranchiseNorthStar()}
  }
}
async function loadFranchiseNorthStar(){
  const panel=myTeamPanel();
  if(!state?.context?.team_id){
    if(panel)panel.innerHTML='<div class="franchise-ns-shell"><p class="eyebrow">Franchise</p><h2>Select the franchise you manage.</h2><p class="lead">Choose a team from the product context to open Franchise.</p></div>';
    return;
  }
  const expectedStateId=state.context?.state_id||null;
  fsfflMyTeamState.valueLensGeneration+=1;
  fsfflMyTeamState.valueLensLoading=false;
  // Keep the accepted last-good Franchise visible while fresh reads are in flight.
  // This prevents a prior Market body from occupying Franchise during refresh and
  // avoids replacing usable governed evidence with a generic loading takeover.
  const hasLastGood=Boolean(fsfflMyTeamState.view);
  if(hasLastGood){
    renderFranchiseNorthStar();
  }else if(panel){
    panel.innerHTML='<div class="franchise-ns-shell franchise-ns-loading"><p class="eyebrow">Franchise</p><h2>Restoring your franchise…</h2><p>Using the last compatible league context while current evidence is checked.</p></div>';
  }
  try{
    const results=await Promise.all([
      api('/api/my-team'),
      api('/api/league/team-views').catch(()=>({team_views:[],source_level:'unavailable'})),
      api('/api/home').catch(()=>null),
    ]);
    if(state?.context?.state_id!==expectedStateId)return;
    fsfflMyTeamState.view=results[0];
    fsfflMyTeamState.leagueViews=results[1]?.team_views||[];
    fsfflMyTeamState.leagueSource=results[1]?.source_level||'';
    fsfflMyTeamState.franchiseHome=results[2]&&results[2].league_state_id===results[0]?.context?.league_state_id?results[2]:null;
    renderFranchiseNorthStar();
    void loadFranchiseNorthStarValueLenses(expectedStateId);
  }catch(error){
    if(panel)panel.innerHTML='<div class="franchise-ns-shell"><p class="eyebrow">Franchise</p><h2>Unable to load your franchise.</h2><p class="lead">'+myTeamEsc(error?.message||String(error))+'</p></div>';
  }
}
window.renderFsfflMyTeam=loadFranchiseNorthStar;

(function installFranchiseNorthStarStyles(){
  if(document.querySelector('#fsffl-franchise-north-star-style'))return;
  const style=document.createElement('style');
  style.id='fsffl-franchise-north-star-style';
  style.textContent=[
    '.franchise-ns-shell{max-width:1080px;margin:0 auto;color:var(--text);min-width:0}',
    '.franchise-ns-header{display:flex;align-items:center;gap:12px;margin:0 0 12px}.franchise-ns-header h2{margin:1px 0 3px;font-size:clamp(1.65rem,5vw,2.35rem);letter-spacing:-.035em}.franchise-ns-header p{margin:0;color:var(--muted);font-size:11px;text-transform:capitalize}.franchise-ns-header p strong{color:#5ee6a8}.franchise-ns-mark{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;border:1px solid #2b7898;background:#10243a;color:#7dd3fc;font-weight:850}',
    '.franchise-ns-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:4px;border:1px solid var(--line);border-radius:12px;background:#08101c;margin-bottom:12px}.franchise-ns-tabs button{min-height:44px;border:0;border-radius:9px;background:transparent;color:var(--muted);font:inherit;font-size:11px;font-weight:800}.franchise-ns-tabs button[aria-selected=true]{background:#0b4d82;color:#f8fafc;box-shadow:inset 0 0 0 1px #1874ad}',
    '.franchise-ns-forecast-strip{display:flex;align-items:center;gap:6px;min-height:30px;border:1px solid #765526;border-radius:8px;background:rgba(155,106,42,.07);padding:5px 8px;margin:-4px 0 10px;color:#d7bc8c;line-height:1.25}.franchise-ns-forecast-strip strong{font-size:9px;white-space:nowrap}.franchise-ns-forecast-strip span{font-size:9px;color:#bda77f}.franchise-ns-warning{border:1px solid #9b6a2a;border-radius:10px;background:rgba(155,106,42,.10);padding:8px 10px;color:#d6b57d;font-size:10px}',
    '.franchise-ns-view{display:grid;gap:11px}.franchise-ns-outlook{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;border:1px solid var(--line);border-radius:15px;background:#091321;overflow:hidden}.franchise-ns-outlook>div{padding:11px 8px;display:grid;gap:2px;text-align:center;border-left:1px solid var(--line)}.franchise-ns-outlook>div:first-child{border-left:0}.franchise-ns-outlook small{font-size:8px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.franchise-ns-outlook strong{font-size:1.18rem}.franchise-ns-outlook span{font-size:8px;color:var(--muted)}',
    '.franchise-ns-section{border:1px solid var(--line);border-radius:16px;background:#0a1120;padding:14px;min-width:0}.franchise-ns-section-head{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:10px}.franchise-ns-section-head h3,.franchise-ns-roster-head h3,.franchise-ns-assets-top h3{margin:2px 0;font-size:1.08rem}.franchise-ns-section-head p:not(.eyebrow),.franchise-ns-roster-head p:not(.eyebrow),.franchise-ns-assets-top p:not(.eyebrow){margin:4px 0 0;font-size:10px;line-height:1.4;color:var(--muted)}',
    '.franchise-ns-segment{display:flex;gap:3px;border:1px solid #223149;border-radius:999px;padding:3px;background:#07101d;flex:0 0 auto}.franchise-ns-segment button{min-height:36px;border:0;border-radius:999px;padding:6px 12px;background:transparent;color:#8091aa;font:inherit;font-size:10px;font-weight:800}.franchise-ns-segment button[aria-pressed=true]{color:#f8fafc;background:#153a54;box-shadow:inset 0 0 0 1px #2b7796}.franchise-ns-segment button:disabled{opacity:.38}',
    '.franchise-ns-position-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.franchise-ns-position-ring{min-height:100px;border:0;background:transparent;color:var(--text);display:grid;justify-items:center;align-content:center;gap:5px;font:inherit;border-radius:12px;touch-action:manipulation}.franchise-ns-position-ring>span{font-size:10px;font-weight:850}.franchise-ns-position-ring>i{--ring:#718096;width:52px;height:52px;border:4px solid var(--ring);border-radius:50%;display:grid;place-items:center;font-style:normal;background:#0a1625}.franchise-ns-position-ring>i strong{font-size:13px}.franchise-ns-position-ring>small{font-size:8px;color:var(--muted)}.franchise-ns-position-ring.strong>i{--ring:#35d399}.franchise-ns-position-ring.middle>i{--ring:#efc65d}.franchise-ns-position-ring.weak>i{--ring:#ef6478}.franchise-ns-position-ring.selected{background:#0c1c2d;box-shadow:inset 0 0 0 1px #2d5f7c}',
    '.franchise-ns-position-detail{border-top:1px solid var(--line);margin-top:10px;padding-top:10px}.franchise-ns-position-detail-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.franchise-ns-position-detail-head span{display:grid;gap:2px}.franchise-ns-position-detail-head small{font-size:9px;color:var(--muted)}.franchise-ns-position-detail-head button{width:36px;height:36px;border:0;border-radius:50%;background:#101b2c;color:var(--muted);font-size:18px}.franchise-ns-position-players{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:8px}.franchise-ns-position-players button{min-height:48px;border:1px solid var(--line);border-radius:10px;background:#0c1728;color:var(--text);display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:center;text-align:left;padding:8px 10px;font:inherit}.franchise-ns-position-players button span{display:grid}.franchise-ns-position-players button small{font-size:9px;color:var(--muted)}.franchise-ns-position-players button em{font-style:normal;font-size:8px;color:#f5b8c0}.franchise-ns-position-detail>p{font-size:10px;color:var(--muted);margin:8px 0 0}',
    '.franchise-ns-diagnosis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.franchise-ns-diagnosis article{border:1px solid var(--line);border-radius:12px;padding:11px;background:#0b1626;min-width:0}.franchise-ns-diagnosis article>span{font-size:8px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:800}.franchise-ns-diagnosis h4{margin:5px 0 5px;font-size:12px}.franchise-ns-diagnosis p{margin:0;color:var(--muted);font-size:9px;line-height:1.4}.franchise-ns-diagnosis .foundation{border-top-color:#35d399}.franchise-ns-diagnosis .pressure{border-top-color:#ef6478}.franchise-ns-diagnosis .exposure{border-top-color:#efc65d}',
    '.franchise-ns-age-row{display:grid;grid-template-columns:1fr 1fr minmax(110px,1.2fr);gap:1px;border:1px solid var(--line);border-radius:13px;background:#091321;overflow:hidden}.franchise-ns-age-row>div{padding:10px 12px;display:grid;gap:1px}.franchise-ns-age-row>div+div{border-left:1px solid var(--line)}.franchise-ns-age-row small{font-size:8px;text-transform:uppercase;color:var(--muted)}.franchise-ns-age-row strong{font-size:1.2rem}.franchise-ns-age-row p{margin:0;padding:10px 12px;color:var(--muted);font-size:9px;display:grid;place-items:center;text-align:center;border-left:1px solid var(--line)}',
    '.franchise-ns-pick-years{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.franchise-ns-pick-year{border:1px solid var(--line);border-radius:11px;background:#0b1626;min-width:0;overflow:hidden}.franchise-ns-pick-year>button{width:100%;min-height:52px;border:0;background:transparent;color:var(--text);display:flex;justify-content:space-between;gap:8px;align-items:center;text-align:left;padding:9px 10px;font:inherit}.franchise-ns-pick-year>button span{display:grid;gap:2px}.franchise-ns-pick-year>button small{font-size:9px;color:var(--muted);overflow:hidden;text-overflow:ellipsis}.franchise-ns-pick-detail{display:grid;gap:5px;border-top:1px solid var(--line);padding:8px}.franchise-ns-pick-detail span{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px}.franchise-ns-pick-detail strong{font-size:10px}.franchise-ns-pick-detail small{font-size:9px;color:var(--muted)}.franchise-ns-note{margin:8px 0 0;font-size:9px;color:var(--muted)}',
    '.franchise-ns-context-action{min-height:46px;border:1px solid #245c78;border-radius:12px;background:#0d2940;color:#8fe1ff;font:inherit;font-size:12px;font-weight:800;display:flex;justify-content:space-between;align-items:center;padding:10px 13px}.franchise-ns-context-action b{font-size:16px}',
    '.franchise-ns-roster-head,.franchise-ns-assets-top{display:flex;justify-content:space-between;align-items:end;gap:12px}.franchise-ns-player-list{display:grid;gap:5px}.franchise-ns-player-row{width:100%;min-height:58px;border:1px solid var(--line);border-radius:12px;background:#091321;color:var(--text);display:grid;grid-template-columns:minmax(180px,1.5fr) 64px 78px 110px 110px 14px;gap:8px;align-items:center;text-align:left;padding:7px 9px;font:inherit;touch-action:manipulation}.franchise-ns-player-id{display:grid;grid-template-columns:34px minmax(0,1fr);gap:8px;align-items:center;min-width:0}.franchise-ns-player-id>i{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#10233a;border:1px solid #2b5b7b;color:#8ddfff;font-style:normal;font-size:9px;font-weight:850}.franchise-ns-player-id>span{display:grid;min-width:0}.franchise-ns-player-id strong{white-space:normal;overflow:visible;text-overflow:clip;overflow-wrap:anywhere;line-height:1.15}.franchise-ns-player-id small{font-size:9px;color:var(--muted)}.franchise-ns-player-stat,.franchise-ns-player-value{display:grid;gap:1px}.franchise-ns-player-stat small,.franchise-ns-player-value>small:first-child,.franchise-ns-player-value span small{font-size:8px;color:var(--muted)}.franchise-ns-player-stat strong,.franchise-ns-player-value strong{font-size:11px}.franchise-ns-player-value>strong+small{display:block}.franchise-ns-chevron{color:#61738c;font-size:16px}',
    '.franchise-ns-asset-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.franchise-ns-asset-card{min-height:68px;border:1px solid var(--line);border-radius:12px;background:#0b1626;color:var(--text);display:grid;grid-template-columns:24px minmax(0,1fr) auto 10px;gap:8px;align-items:center;text-align:left;padding:9px;font:inherit}.franchise-ns-asset-rank{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:#142139;color:#94a3b8;font-size:9px}.franchise-ns-asset-main{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:6px;align-items:center}.franchise-ns-asset-main i{grid-row:1/3;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:#10233a;color:#8ddfff;font-style:normal;font-size:8px;font-weight:850}.franchise-ns-asset-main strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.franchise-ns-asset-main small{font-size:9px;color:var(--muted)}.franchise-ns-asset-value{display:grid;text-align:right}.franchise-ns-asset-value>span,.franchise-ns-asset-value>small{font-size:8px;color:var(--muted)}.franchise-ns-asset-value strong{font-size:11px}',
    '.franchise-ns-additional{border-top:1px solid var(--line);padding:11px 2px 0}.franchise-ns-additional>div{display:flex;gap:8px;flex-wrap:wrap}.franchise-ns-additional>div>span{border:1px solid var(--line);border-radius:10px;padding:8px 10px;display:grid;gap:2px;background:#091321}.franchise-ns-additional small{font-size:9px;color:var(--muted)}',
    '.franchise-ns-empty{color:var(--muted);font-size:10px}.franchise-ns-loading p{color:var(--muted)}',
    '@media(max-width:760px){.franchise-ns-shell{padding:0 0 calc(74px + env(safe-area-inset-bottom,0px));width:100%;max-width:none}.franchise-ns-header{padding:0 2px}.franchise-ns-outlook>div{padding:9px 4px}.franchise-ns-outlook strong{font-size:1.02rem}.franchise-ns-section{padding:12px}.franchise-ns-section-head,.franchise-ns-roster-head,.franchise-ns-assets-top{align-items:flex-start}.franchise-ns-position-ring{min-height:94px}.franchise-ns-position-ring>i{width:48px;height:48px}.franchise-ns-position-players{grid-template-columns:1fr}.franchise-ns-diagnosis{grid-template-columns:1fr}.franchise-ns-pick-years{grid-template-columns:1fr}.franchise-ns-player-row{grid-template-columns:minmax(0,1fr) 52px 64px;grid-template-areas:"id ppg proj" "market market intrinsic"}.franchise-ns-player-id{grid-area:id}.franchise-ns-player-stat:nth-of-type(2){grid-area:ppg}.franchise-ns-player-stat:nth-of-type(3){grid-area:proj}.franchise-ns-player-value.market{grid-area:market;border-top:1px solid rgba(51,65,85,.45);padding-top:5px}.franchise-ns-player-value.intrinsic{grid-area:intrinsic;border-top:1px solid rgba(51,65,85,.45);padding-top:5px}.franchise-ns-chevron{display:none}.franchise-ns-asset-grid{grid-template-columns:1fr}}',
    '@media(max-width:420px){.franchise-ns-tabs button{font-size:10px;padding:6px 4px}.franchise-ns-section-head,.franchise-ns-roster-head,.franchise-ns-assets-top{display:grid}.franchise-ns-segment{width:max-content;max-width:100%}.franchise-ns-position-grid{gap:2px}.franchise-ns-position-ring{min-height:88px;padding:4px 1px}.franchise-ns-position-ring>i{width:45px;height:45px}.franchise-ns-position-ring>small{font-size:7px}.franchise-ns-age-row{grid-template-columns:1fr 1fr}.franchise-ns-age-row p{grid-column:1/-1;border-left:0;border-top:1px solid var(--line)}.franchise-ns-player-row{padding:7px}.franchise-ns-player-id{grid-template-columns:30px minmax(0,1fr)}.franchise-ns-player-id>i{width:30px;height:30px}}'
  ].join('');
  document.head.appendChild(style);
})();
