const fsfflLeagueStructureState={views:[],valueLenses:null,atlas:null,managedTeamId:null,valueLensMode:'difference',selectedValueTeamId:null,activeTab:'overview',selectedRoom:null,selectedPickTeamId:null,pickYear:null,positionLens:'current',positionLensMode:'rank',dynastyRooms:null,dynastyRoomStatus:'idle',longTermEvidence:null,longTermStatus:'idle',raceSortKey:'rank',raceSortDirection:'asc',focusMetric:null,focusTeamId:null,focusPlayerId:null,loadMs:null,warmMs:null,valueStatus:'idle',valueError:null};

function leagueComparisonPanel(){return document.querySelector('#generic-screen .panel')}
function laEsc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function laNum(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function laPct(value){return typeof value==='number'&&Number.isFinite(value)?Math.round(value*100):null}
function laValueIndex(value){return typeof value==='number'&&Number.isFinite(value)?Math.round(value).toLocaleString():'—'}
function laState(value){return value&&value!=='unknown'?String(value).replaceAll('_',' '):'Unclassified'}
function laAtlas(){return fsfflLeagueStructureState.atlas||{}}
function laSimulation(teamId){return (laAtlas()?.simulation?.teams||[]).find(row=>row.team_id===teamId)||null}
function laStanding(teamId){return (laAtlas()?.standings||[]).find(row=>row.team_id===teamId)||null}
function laOutcome(view){return view?.utility?.competitive_outcome||laSimulation(view?.team_id)||null}
function laResilience(view){return view?.utility?.roster_resilience||null}
function laFragilityDrivers(view){const resilience=laResilience(view),ids=resilience?.largest_single_player_lineup_drop_player_ids||[];return ids.map(id=>(view?.players||[]).find(player=>player.player_id===id)).filter(Boolean)}
function laFragilityDriverLabel(view){const drivers=laFragilityDrivers(view);return drivers.length?drivers.map(player=>player.full_name).join(' / '):'driver unavailable'}
function laFragilityDriverLinks(view){const drivers=laFragilityDrivers(view);return drivers.length?drivers.map(player=>'<button type="button" data-player-intelligence-id="'+laEsc(player.player_id)+'">'+laEsc(player.full_name)+'</button>').join('<small> / </small>'):'<small>driver unavailable</small>'}
function laStrength(view,position){return (view?.position_strengths||[]).find(row=>row.position===position)||null}
function laDynastyRoom(teamId,position){return (fsfflLeagueStructureState.dynastyRooms?.rooms||[]).find(row=>row.team_id===teamId&&row.position===position)||null}
function laRosterBreadth(teamId,position){return (laAtlas()?.dynasty_position_breadth||[]).find(row=>row.team_id===teamId&&row.position===position)||null}
function laManaged(){return fsfflLeagueStructureState.views.find(view=>view.team_id===fsfflLeagueStructureState.managedTeamId)||null}
function laValuePlayers(teamId){return (fsfflLeagueStructureState.valueLenses?.players||[]).filter(row=>row.owner_team_id===teamId)}
function laValueModeValue(row){if(fsfflLeagueStructureState.valueLensMode==='intrinsic')return row?.intrinsic_percentile;if(fsfflLeagueStructureState.valueLensMode==='difference')return row?.percentile_gap;return row?.broad_market_percentile}
function laValueModeLabel(){if(fsfflLeagueStructureState.valueLensMode==='intrinsic')return'FSFFL Intrinsic';if(fsfflLeagueStructureState.valueLensMode==='difference')return'Difference';return'Broad Market'}
function laValuePosition(value){if(typeof value!=='number'||!Number.isFinite(value))return null;const scaled=fsfflLeagueStructureState.valueLensMode==='difference'?(value+1)*50:value*100;return Math.max(0,Math.min(100,scaled))}
function laStateGroups(){const groups={contender:[],competitive:[],developing:[],rebuilding:[],unknown:[]};fsfflLeagueStructureState.views.forEach(view=>{const key=view?.utility?.calculated_competitive_state||'unknown';(groups[key]||groups.unknown).push(view)});return groups}
function laConsumeDeepLinkIntent(){
  const intent=typeof window.fsfflConsumeDeepLinkIntent==='function'?window.fsfflConsumeDeepLinkIntent('league_comparison'):null;
  if(!intent)return;
  const teamId=intent.teamId||fsfflLeagueStructureState.managedTeamId||null;
  fsfflLeagueStructureState.focusTeamId=teamId;
  fsfflLeagueStructureState.focusMetric=intent.metric||null;
  fsfflLeagueStructureState.focusPlayerId=intent.playerId||null;
  if(intent.section==='positions'||intent.position){
    fsfflLeagueStructureState.activeTab='positions';
    if(teamId&&intent.position)fsfflLeagueStructureState.selectedRoom={teamId,position:intent.position};
  }else{
    fsfflLeagueStructureState.activeTab='overview';
    fsfflLeagueStructureState.selectedRoom=null;
  }
}
function laApplyDeepLinkFocus(){
  const panel=leagueComparisonPanel();if(!panel)return;
  const teamId=fsfflLeagueStructureState.focusTeamId,metric=fsfflLeagueStructureState.focusMetric,playerId=fsfflLeagueStructureState.focusPlayerId;
  panel.querySelectorAll('.atlas-deep-link-focus').forEach(node=>node.classList.remove('atlas-deep-link-focus'));
  if(fsfflLeagueStructureState.activeTab==='overview'&&teamId){
    const row=panel.querySelector('[data-race-team="'+CSS.escape(teamId)+'"]');if(row)row.classList.add('atlas-deep-link-focus');
    if(metric){
      const header=panel.querySelector('[data-race-metric="'+CSS.escape(metric)+'"]');if(header)header.classList.add('atlas-deep-link-focus');
      const cell=panel.querySelector('[data-race-team="'+CSS.escape(teamId)+'"] [data-race-metric="'+CSS.escape(metric)+'"]');
      if(cell){
        cell.classList.add('atlas-deep-link-focus');
        const wrap=panel.querySelector('.atlas-race-table-wrap');
        if(wrap){const fixed=152;wrap.scrollLeft=Math.max(0,cell.offsetLeft-fixed-16);wrap.dispatchEvent(new Event('scroll'))}
      }
    }
    row?.scrollIntoView({block:'center',inline:'nearest'});
  }
  if(fsfflLeagueStructureState.activeTab==='positions'){
    const drawer=panel.querySelector('.atlas-drawer');if(drawer)drawer.scrollIntoView({block:'nearest'});
    if(playerId){const player=panel.querySelector('[data-player-intelligence-id="'+CSS.escape(playerId)+'"]');if(player){player.classList.add('atlas-deep-link-focus');player.scrollIntoView({block:'nearest'})}}
  }
}

function laPrimaryTakeaway(){
  const managed=laManaged(),groups=laStateGroups();
  if(managed){
    const strengths=(managed.position_strengths||[]).filter(row=>['QB','RB','WR','TE'].includes(row.position)&&typeof row.league_rank==='number');
    const strongest=[...strengths].sort((a,b)=>a.league_rank-b.league_rank)[0],weakest=[...strengths].sort((a,b)=>b.league_rank-a.league_rank)[0];
    if(strongest&&weakest)return '<strong>'+laEsc(managed.display_name)+' is '+laEsc(laState(managed?.utility?.calculated_competitive_state).toLowerCase())+', strongest at '+laEsc(strongest.position)+' (#'+strongest.league_rank+') and most exposed at '+laEsc(weakest.position)+' (#'+weakest.league_rank+').</strong><span>'+groups.contender.length+' contender'+(groups.contender.length===1?'':'s')+' · '+groups.rebuilding.length+' rebuilding team'+(groups.rebuilding.length===1?'':'s')+'. Scan the maps below before opening exact evidence.</span>';
  }
  return '<strong>'+groups.contender.length+' contender'+(groups.contender.length===1?'':'s')+' and '+groups.rebuilding.length+' rebuilding team'+(groups.rebuilding.length===1?'':'s')+'.</strong><span>Position, value, age, picks and fragility stay in separate governed lanes instead of one power score.</span>';
}

function laPositionCell(view,position){
  const dynasty=fsfflLeagueStructureState.positionLens==='dynasty',row=dynasty?laDynastyRoom(view.team_id,position):laStrength(view,position);if(!row){if(dynasty){const breadth=laRosterBreadth(view.team_id,position);return '<button type="button" class="league-edge-cell missing" disabled title="Holistic career-forward evidence is '+laEsc(fsfflLeagueStructureState.dynastyRoomStatus)+'">—'+(typeof breadth?.rostered_player_count==='number'?'<small>'+breadth.rostered_player_count+' rostered</small>':'')+'</button>'}return '<button type="button" class="league-edge-cell missing" disabled>—</button>'}
  if(dynasty){
    const breadth=laRosterBreadth(view.team_id,position),count=breadth?.rostered_player_count;
    if(!row.evidence_complete||typeof row.league_rank!=='number')return '<button type="button" class="league-edge-cell missing" disabled title="Holistic career-forward evidence is incomplete for this league position room">—'+(typeof count==='number'?'<small>'+count+' rostered</small>':'')+'</button>';
    const mode=fsfflLeagueStructureState.positionLensMode||'rank',value=mode==='strength'?row.strength_index:row.league_rank,display=mode==='strength'?(typeof value==='number'?laNum(value,0):'—'):'#'+row.league_rank,label=mode==='strength'?(typeof value==='number'?'strength index '+laNum(value,0):'league-average index unavailable'):'rank #'+row.league_rank+' of '+row.team_count;
    const peerRooms=(fsfflLeagueStructureState.dynastyRooms?.rooms||[]).filter(item=>item.position===position),higher=peerRooms.filter(item=>typeof item.room_raw==='number'&&item.room_raw>row.room_raw).length,tied=peerRooms.filter(item=>item.room_raw===row.room_raw).length,meanRank=higher+(tied+1)/2,share=(meanRank-1)/Math.max(1,row.team_count-1),band=share<=.2?'elite':share<=.42?'strong':share<=.7?'neutral':'weak';
    return '<button type="button" class="league-edge-cell '+band+'" data-room-team="'+laEsc(view.team_id)+'" data-room-position="'+laEsc(position)+'" aria-label="'+laEsc(view.display_name)+' '+laEsc(position)+' '+laEsc(label)+'; '+laEsc(String(count??'—'))+' rostered; open team-position detail" title="'+laEsc(label)+'; '+laEsc(String(count??'—'))+' rostered for breadth"><b>'+display+'</b><small>'+laEsc(String(count??'—'))+' rostered</small></button>';
  }
  const rank=typeof row.league_rank==='number'?row.league_rank:null;if(rank===null)return '<button type="button" class="league-edge-cell missing" disabled title="Roster evidence is incomplete">—</button>';
  const count=row.team_count||fsfflLeagueStructureState.views.length,share=(rank-1)/Math.max(1,count-1),band=share<=.2?'elite':share<=.42?'strong':share<=.7?'neutral':'weak';
  const mode=fsfflLeagueStructureState.positionLensMode||'rank',index=row.strength_index,display=mode==='strength'?laNum(index,0):'#'+rank;
  const label=mode==='strength'?'strength index '+laNum(index,0):'rank #'+rank+' of '+count;
  const secondary='strength index '+laNum(index,0);
  return '<button type="button" class="league-edge-cell '+band+'" data-room-team="'+laEsc(view.team_id)+'" data-room-position="'+laEsc(position)+'" aria-label="'+laEsc(view.display_name)+' '+laEsc(position)+' '+laEsc(label)+'; open team-position detail" title="'+laEsc(position)+' rank #'+rank+' of '+count+'; '+laEsc(secondary)+'"><b>'+display+'</b></button>';
}
function laPositionMatrix(){
  const positions=['QB','RB','WR','TE'],mode=fsfflLeagueStructureState.positionLensMode||'rank',dynasty=fsfflLeagueStructureState.positionLens==='dynasty',views=[...fsfflLeagueStructureState.views].sort((a,b)=>{if(a.team_id===fsfflLeagueStructureState.managedTeamId)return-1;if(b.team_id===fsfflLeagueStructureState.managedTeamId)return 1;return a.display_name.localeCompare(b.display_name)});
  const rows=views.map(view=>'<div class="league-edge-row '+(view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><span class="league-edge-team"><strong>'+laEsc(view.display_name)+'</strong>'+(view.team_id===fsfflLeagueStructureState.managedTeamId?'<small>Your team</small>':'')+'</span>'+positions.map(position=>laPositionCell(view,position)).join('')+'</div>').join('');
  const header='<div class="league-edge-row header"><span>Franchise</span>'+positions.map(position=>'<span>'+position+'</span>').join('')+'</div>';


  const displayModes='<button type="button" data-position-lens="rank" class="'+(mode==='rank'?'active':'')+'">Rank</button><button type="button" data-position-lens="strength" class="'+(mode==='strength'?'active':'')+'">Strength Index</button>';
  const roomStatus=dynasty?(fsfflLeagueStructureState.dynastyRoomStatus==='loading'?'Loading Dynasty room values… roster counts are breadth only.':fsfflLeagueStructureState.dynastyRoomStatus==='building'?'Long-Term evidence is building… roster counts are breadth only.':fsfflLeagueStructureState.dynastyRoomStatus==='unavailable'?'Dynasty room ranking is unavailable for this State; roster counts are breadth only.':fsfflLeagueStructureState.dynastyRoomStatus==='stale'?'Dynasty room values are not loaded for this last-good State; roster counts are breadth only.':fsfflLeagueStructureState.dynastyRoomStatus==='last-good'?'Last-good Dynasty room rank while current intelligence rebuilds; roster counts are breadth only.':'Career-forward room rank; roster counts are breadth only.'):mode==='strength'?'Current uses optimized-starter production; 100 = league average.':'Current ranks optimized-starter production for winning now, #1 through #'+views.length+'.';
  const controls='<div class="league-position-lens-wrap"><div class="league-position-lens-row"><div class="league-position-lens" role="group" aria-label="Position outlook"><button type="button" data-position-view="current" class="'+(!dynasty?'active':'')+'">Current</button><button type="button" data-position-view="dynasty" class="'+(dynasty?'active':'')+'">Dynasty</button></div><div class="league-position-lens" role="group" aria-label="Position map display">'+displayModes+'</div></div><small class="league-position-lens-note" role="status" aria-live="polite">'+roomStatus+'</small></div>';
  return '<section class="league-section league-position-section"><div class="league-section-heading league-map-heading"><div><p class="eyebrow">League Map</p><h3>See positional control at a glance</h3></div>'+controls+'</div><div class="league-edge-matrix league-edge-map">'+header+rows+'</div><p class="atlas-foot league-map-foot">Team order does not change between lenses. Dynasty ranks holistic career-forward raw room totals; the roster count shown beneath is secondary breadth evidence. Tap any position to see the players and evidence behind its rank.</p></section>';
}

function laValueDot(row){
  const value=laValueModeValue(row),left=laValuePosition(value);if(left==null)return'';
  const detail=fsfflLeagueStructureState.valueLensMode==='difference'?'Intrinsic − Market '+(value>=0?'+':'')+Math.round(value*100)+' pts':laValueModeLabel()+' '+Math.round(value*100)+'th percentile';
  return '<button type="button" data-player-intelligence-id="'+laEsc(row.player_id)+'" class="league-value-dot pos-'+laEsc(String(row.position||'na').toLowerCase())+'" style="left:'+left.toFixed(1)+'%" title="'+laEsc(row.full_name)+' · '+laEsc(row.position)+' · '+laEsc(detail)+'"></button>';
}
function laValuePlayerDetail(row){
  const market=row.broad_market_value_index,intrinsic=row.intrinsic_value_index,gap=row.value_index_gap;
  const gapLabel=typeof gap==='number'&&Number.isFinite(gap)?(gap>=0?'+':'')+laValueIndex(gap):'—';
  return '<button type="button" class="league-value-player" data-player-intelligence-id="'+laEsc(row.player_id)+'"><div><strong>'+laEsc(row.full_name)+'</strong><small>'+laEsc(row.position)+(typeof row.age_years==='number'?' · age '+laNum(row.age_years,1):'')+'</small></div><span><b>'+laValueIndex(market)+'</b><small>Market</small></span><span><b>'+laValueIndex(intrinsic)+'</b><small>Intrinsic</small></span><span><b>'+gapLabel+'</b><small>Difference</small></span></button>';
}
function laValueDetail(teamId){
  const view=fsfflLeagueStructureState.views.find(item=>item.team_id===teamId);if(!view)return'';
  const rows=laValuePlayers(teamId).sort((a,b)=>String(a.position).localeCompare(String(b.position))||String(a.full_name).localeCompare(String(b.full_name)));
  return '<div class="league-value-detail"><div class="league-value-detail-heading"><strong>'+laEsc(view.display_name)+'</strong><small>Governed 0–10,000 Value Index · player-level only</small></div><div class="league-value-player-grid">'+(rows.map(laValuePlayerDetail).join('')||'<p>No rostered value-lens evidence is available for this team.</p>')+'</div></div>';
}
function laValueLensSection(){
  const payload=fsfflLeagueStructureState.valueLenses,views=fsfflLeagueStructureState.views;
  if(!payload&&fsfflLeagueStructureState.valueStatus==='loading')return '<section class="league-section league-value-section"><div class="league-section-heading"><div><p class="eyebrow">Value lenses</p><h3>Broad Market vs FSFFL Intrinsic</h3></div><small>Governed value lenses are loading independently. League structure remains usable.</small></div><div class="atlas-loading"><i></i><span>Preparing player-level Market / Intrinsic evidence…</span></div></section>';if(!payload)return '<section class="league-section league-value-section"><div class="league-section-heading"><div><p class="eyebrow">Value lenses</p><h3>Broad Market vs FSFFL Intrinsic</h3></div><small>Unavailable from the current runtime. Other Atlas surfaces remain independently usable.</small></div></section>';
  const mode=fsfflLeagueStructureState.valueLensMode,selected=fsfflLeagueStructureState.selectedValueTeamId||fsfflLeagueStructureState.managedTeamId||views[0]?.team_id||null;
  fsfflLeagueStructureState.selectedValueTeamId=selected;
  const axis=mode==='difference'?['Market higher','Even','Intrinsic higher']:['0','50','100'];
  return '<section class="league-section league-value-section"><div class="league-section-heading"><div><p class="eyebrow">Player value map</p><h3>Where do market price and FSFFL football economics disagree?</h3></div><small>Broad Market + FSFFL Intrinsic remain separate player-level lenses. No team Market total, team Intrinsic total, League Market Value, or buy/sell command.</small></div><div class="league-value-toolbar"><div class="league-value-modes" role="group" aria-label="League value lens"><button type="button" data-value-mode="market" class="'+(mode==='market'?'active':'')+'">Broad Market</button><button type="button" data-value-mode="intrinsic" class="'+(mode==='intrinsic'?'active':'')+'">FSFFL Intrinsic</button><button type="button" data-value-mode="difference" class="'+(mode==='difference'?'active':'')+'">Difference</button></div><span>Market '+laEsc(payload?.broad_market?.status||'unavailable')+' · Intrinsic '+laEsc(payload?.fsffl_intrinsic?.status||'unavailable')+'</span></div><div class="league-value-axis"><span>'+axis[0]+'</span><span>'+axis[1]+'</span><span>'+axis[2]+'</span></div><div class="league-value-grid">'+views.map(view=>{const players=laValuePlayers(view.team_id),covered=players.filter(row=>laValueModeValue(row)!=null).length;return '<div class="league-value-row '+(view.team_id===selected?'selected ':'')+(view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><button type="button" class="league-value-team-select" data-value-team="'+laEsc(view.team_id)+'"><span class="league-value-team"><strong>'+laEsc(view.display_name)+'</strong><small>'+covered+'/'+players.length+' covered</small></span></button><span class="league-value-strip">'+players.map(laValueDot).join('')+'</span></div>'}).join('')+'</div>'+laValueDetail(selected)+'</section>';
}
function laPressurePoint(){
  const managed=laManaged();if(!managed)return'';
  const strengths=(managed.position_strengths||[]).filter(row=>['QB','RB','WR','TE'].includes(row.position)&&typeof row.league_rank==='number').sort((a,b)=>b.league_rank-a.league_rank),weak=strengths[0];
  if(!weak)return'';
  const suppliers=fsfflLeagueStructureState.views.map(view=>({view,strength:laStrength(view,weak.position)})).filter(row=>row.view.team_id!==managed.team_id&&row.strength&&typeof row.strength.league_rank==='number').sort((a,b)=>a.strength.league_rank-b.strength.league_rank).slice(0,3);
  return '<section class="league-pressure"><div><p class="eyebrow">Your clearest pressure point</p><h3>'+laEsc(weak.position)+' is '+laEsc(managed.display_name)+"'s weakest league-relative room</h3><p>#"+weak.league_rank+' of '+weak.team_count+' on optimized starter production. The teams at right show where current positional supply sits; they are not trade recommendations. Atlas does not create trade recommendations or partner-fit scores.</p></div><div class="league-supply-list">'+suppliers.map(row=>'<span class="league-supply-team"><b>#'+row.strength.league_rank+' '+laEsc(weak.position)+'</b><strong>'+laEsc(row.view.display_name)+'</strong><small>'+laNum(row.strength.strength_index,0)+' index</small></span>').join('')+'</div><button type="button" class="secondary-button" id="league-open-market">Investigate in Market</button></section>';
}
function laCompetitiveMap(){
  const groups=laStateGroups(),order=[['contender','Contenders'],['competitive','Competitive'],['developing','Developing'],['rebuilding','Rebuilding'],['unknown','Unclassified']];
  return '<section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Competitive shape</p><h3>Who sits in which part of the race?</h3></div><small>Calculated state comes from Team Utility and Simulation; owner strategic posture is separate.</small></div><div class="league-state-lanes">'+order.map(([key,label])=>'<article class="league-state-lane '+key+'"><div><span>'+label+'</span><b>'+groups[key].length+'</b></div><div class="league-team-chips">'+(groups[key].map(view=>{const outcome=laOutcome(view);return '<span class="league-team-chip '+(view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><strong>'+laEsc(view.display_name)+'</strong>'+(typeof outcome?.expected_wins==='number'?'<small>'+laNum(outcome.expected_wins,1)+' wins</small>':'')+'</span>'}).join('')||'<small>None</small>')+'</div></article>').join('')+'</div></section>';
}
function laAgeStructure(){
  const rows=fsfflLeagueStructureState.views.filter(view=>typeof view.roster_average_age==='number').sort((a,b)=>a.roster_average_age-b.roster_average_age);
  if(!rows.length)return'';
  return '<section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Age profile</p><h3>Which rosters are younger or older?</h3></div><small>Canonical point-in-time ages only. Missing ages are counted, not imputed.</small></div><div class="league-age-track">'+rows.map(view=>'<article class="league-age-row '+(view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><div class="league-age-team"><strong>'+laEsc(view.display_name)+'</strong><small>'+String(view.known_age_count||0)+' known ages</small></div><div class="league-age-reading"><b>'+laNum(view.roster_average_age,1)+'</b><span>roster avg</span></div><div class="league-age-reading"><b>'+laNum(view.starter_average_age,1)+'</b><span>starter avg · '+String(view.known_starter_age_count||0)+' known</span></div></article>').join('')+'</div></section>';
}
function laPickStructure(){
  const rows=[...fsfflLeagueStructureState.views].map(view=>({view,picks:view.draft_picks?.length||0})).sort((a,b)=>b.picks-a.picks||a.view.display_name.localeCompare(b.view.display_name)),maxPicks=Math.max(1,...rows.map(row=>row.picks));
  return '<section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Future flexibility</p><h3>Who controls more future pick inventory?</h3></div><small>Canonical owned-pick count only. No player/pick percentiles are summed into a team value.</small></div><div class="league-pick-band">'+rows.map(row=>'<article class="league-pick-row '+(row.view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><div><strong>'+laEsc(row.view.display_name)+'</strong><small>'+row.picks+' owned pick'+(row.picks===1?'':'s')+'</small></div><i><b style="width:'+(100*row.picks/maxPicks).toFixed(1)+'%"></b></i><span>'+row.picks+'</span></article>').join('')+'</div></section>';
}
function laDepthStructure(){
  const rows=fsfflLeagueStructureState.views.filter(view=>laResilience(view)).sort((a,b)=>(laResilience(b)?.bench_forecasted_count||0)-(laResilience(a)?.bench_forecasted_count||0));
  if(!rows.length)return'';
  return '<details class="league-detail" open><summary>Depth & fragility across the league</summary><p>Direct roster-resilience diagnostics from Team Utility. Largest one-player lineup drop is exposure, not a standalone team grade.</p><div class="league-depth-grid">'+rows.map(view=>{const resilience=laResilience(view);return '<article class="league-depth-row '+(view.team_id===fsfflLeagueStructureState.managedTeamId?'managed':'')+'"><strong>'+laEsc(view.display_name)+'</strong><span><b>'+String(resilience.bench_forecasted_count??'—')+'</b><small>forecasted bench</small></span><span class="league-fragility-reading"><b>'+laNum(resilience.largest_single_player_lineup_drop,1)+' pts</b><span class="league-fragility-drivers">'+laFragilityDriverLinks(view)+'</span></span></article>'}).join('')+'</div></details>';
}
function laEvidenceDetail(){
  const latency=typeof fsfflLeagueStructureState.loadMs==='number'&&Number.isFinite(fsfflLeagueStructureState.loadMs)?'<p><strong>Atlas load:</strong> '+Math.round(fsfflLeagueStructureState.loadMs)+' ms for parallel team-view + Atlas requests and browser composition.</p>':'';
  const telemetry='<p><strong>Technical evidence:</strong> State '+laEsc(String(laAtlas()?.league_state_id||'unavailable').slice(0,12))+'… · Simulation '+(laAtlas()?.simulation?.status==='ready'?Number(laAtlas()?.simulation?.simulation_count||0).toLocaleString()+' runs':'unavailable')+' · Value '+laEsc(fsfflLeagueStructureState.valueLenses?.status||fsfflLeagueStructureState.valueStatus)+'.</p>';
  const pre=laAtlas()?.preseason_expectation||{};
  const preseason='<p><strong>Preseason baseline:</strong> '+(pre.status==='ready'?'Frozen pre-opener State + contemporaneous governed Forecast + matching 50,000-run Simulation.':'Unavailable unless a no-hindsight pre-opener State + Forecast + Simulation coordinate can be proven.')+'</p>';
  return '<details class="league-detail league-evidence-detail"><summary>Evidence & definitions</summary><div class="league-evidence-copy"><p><strong>Max PF:</strong> observed season-to-date maximum/potential points from canonical State. For the current Sleeper league this is normalized from provider roster-settings ppts + ppts_decimal at the governed completed-week boundary; Forecast projections are not used.</p>'+preseason+'<p><strong>Position strength:</strong> optimized starter production at QB/RB/WR/TE relative to league average. 100 = league-average optimized starter production.</p><p><strong>Value lenses:</strong> Broad Market and canonical Shapley Intrinsic remain separate authorities. The map uses player-level percentiles for position; the team breakout shows the governed 0–10,000 presentation Value Index for each lens and its allowed display-index difference. Raw Market and raw Intrinsic quantities are never subtracted.</p><p><strong>Pick wealth:</strong> owned-pick inventory only. No team value coordinate is created.</p><p><strong>Trade context:</strong> positional supply is descriptive. Partner fit stays unavailable unless existing Search/Decision authority supplies it.</p>'+telemetry+latency+'<p><strong>Not created here:</strong> team Intrinsic totals/ranks, summed Market percentiles, League Market Value, hidden composite scores, recommendations, owner-adjusted universal Value, or acceptance probability.</p></div></details>';
}

function laTabButton(id,label){return '<button type="button" data-atlas-tab="'+id+'" class="'+(fsfflLeagueStructureState.activeTab===id?'active':'')+'">'+laEsc(label)+'</button>'}
function laAtlasHeader(){
  const asOf=laAtlas()?.as_of;
  return '<section class="league-atlas-header"><div><p class="eyebrow">League intelligence</p><h2>League Atlas</h2><p class="lead">See the whole league. Understand the landscape. Drill into governed evidence.</p></div><span><small>STATE AS OF</small><b>'+(asOf?laEsc(new Date(asOf).toLocaleString()):'Unavailable')+'</b></span></section><nav class="league-atlas-tabs">'+laTabButton('overview','Overview')+laTabButton('positions','Position & Depth')+laTabButton('value','Value Map')+laTabButton('picks','Pick Map')+'</nav>';
}
function laRecord(row){if(!row)return'—';return row.ties?row.wins+'-'+row.losses+'-'+row.ties:row.wins+'-'+row.losses}
function laProb(value){return typeof value==='number'&&Number.isFinite(value)?Math.round(value*100)+'%':'—'}
function laRaceSortValue(row,key){
  const sim=laSimulation(row.team_id);
  if(key==='rank')return row.rank;
  if(key==='points_for')return row.points_for;
  if(key==='points_against')return row.points_against;
  if(key==='max_points_for')return row.max_points_for;
  if(key==='expected_finish')return sim?.expected_finish;
  if(key==='playoff_probability')return sim?.playoff_probability;
  if(key==='championship_probability')return sim?.championship_probability;
  if(key==='expected_wins')return sim?.expected_wins;
  if(key==='first_place_probability')return sim?.first_place_probability;
  return null;
}
function laRaceSorted(standings){
  const key=fsfflLeagueStructureState.raceSortKey||'rank',direction=fsfflLeagueStructureState.raceSortDirection==='desc'?-1:1;
  return [...standings].sort((a,b)=>{
    const av=laRaceSortValue(a,key),bv=laRaceSortValue(b,key),am=typeof av!=='number'||!Number.isFinite(av),bm=typeof bv!=='number'||!Number.isFinite(bv);
    if(am&&bm)return a.rank-b.rank||String(a.team_name).localeCompare(String(b.team_name));
    if(am)return 1;if(bm)return-1;
    const delta=(av-bv)*direction;if(Math.abs(delta)>1e-12)return delta;
    return a.rank-b.rank||String(a.team_name).localeCompare(String(b.team_name));
  });
}
function laRaceSortHeader(key,label){
  const active=fsfflLeagueStructureState.raceSortKey===key,indicator=active?(fsfflLeagueStructureState.raceSortDirection==='asc'?'↑':'↓'):'↕';
  return '<button type="button" class="atlas-race-sort '+(active?'active':'')+'" data-race-sort="'+key+'"><span>'+laEsc(label)+'</span><b aria-hidden="true">'+indicator+'</b></button>';
}
function laRaceHeaderDock(){
  const metrics=[
    '<span class="atlas-race-head-record" data-race-metric="record">Record</span>',
    '<span data-race-metric="points_for">'+laRaceSortHeader('points_for','PF')+'</span>',
    '<span data-race-metric="points_against">'+laRaceSortHeader('points_against','PA')+'</span>',
    '<span data-race-metric="max_points_for">'+laRaceSortHeader('max_points_for','Max PF')+'</span>',
    '<span data-race-metric="expected_finish">'+laRaceSortHeader('expected_finish','Projected Finish')+'</span>',
    '<span data-race-metric="playoff_probability">'+laRaceSortHeader('playoff_probability','Playoffs')+'</span>',
    '<span data-race-metric="championship_probability">'+laRaceSortHeader('championship_probability','Championship')+'</span>',
    '<span data-race-metric="expected_wins">'+laRaceSortHeader('expected_wins','Projected Final Wins')+'</span>',
    '<span data-race-metric="first_place_probability">'+laRaceSortHeader('first_place_probability','1st Place')+'</span>'
  ].join('');
  return '<div class="atlas-race-head-dock" aria-label="League Race column headers">'
    +'<div class="atlas-race-head-fixed"><div class="atlas-race-head-fixed-group"></div><div class="atlas-race-head-fixed-metrics"><span>'+laRaceSortHeader('rank','Rank')+'</span><span class="atlas-race-head-team-label">Team/Owner</span></div></div>'
    +'<div class="atlas-race-head-viewport"><div class="atlas-race-head-track"><div class="atlas-race-head-groups"><span>Current Season</span><span>Outlook from Today</span></div><div class="atlas-race-head-metrics">'+metrics+'</div></div></div>'
    +'</div>';
}
function bindLeagueRaceHeaderScroll(){
  const wrap=document.querySelector('.atlas-race-table-wrap'),track=document.querySelector('.atlas-race-head-track');
  if(!wrap||!track)return;
  const sync=()=>{track.style.transform='translate3d('+(-wrap.scrollLeft)+'px,0,0)'};
  sync();wrap.addEventListener('scroll',sync,{passive:true});
}
function laMove(row){const value=row?.movement_vs_current_rank;if(typeof value!=='number'||!Number.isFinite(value)||Math.abs(value)<.25)return'→';return(value>0?'↑ ':'↓ ')+Math.abs(value).toFixed(1)}
function laRankDelta(pre,current){if(typeof pre!=='number'||typeof current!=='number')return'—';const d=pre-current;if(d===0)return'→';return(d>0?'↑ ':'↓ ')+Math.abs(d)}
function laProbDelta(pre,current){if(typeof pre!=='number'||typeof current!=='number')return'—';const d=Math.round((current-pre)*100);if(d===0)return'→';return(d>0?'+':'')+d+' pts'}

function laOverview(){
  const standings=laAtlas()?.standings||[],sim=laAtlas()?.simulation||{},managed=fsfflLeagueStructureState.managedTeamId,managedStanding=managed?laStanding(managed):null,managedSim=managed?laSimulation(managed):null,lastWeek=laAtlas()?.last_completed_week;
  const raceRows=laRaceSorted(standings).map(row=>{const s=laSimulation(row.team_id),view=fsfflLeagueStructureState.views.find(v=>v.team_id===row.team_id);return '<tr class="'+(row.team_id===managed?'managed':'')+'" data-race-team="'+laEsc(row.team_id)+'"><td class="atlas-race-rank-sticky"><b>#'+row.rank+'</b></td><td class="atlas-race-team-sticky"><span><strong>'+laEsc(row.team_name)+'</strong><small>'+laEsc(laState(view?.utility?.calculated_competitive_state))+'</small></span></td><td data-race-metric="record">'+laRecord(row)+'</td><td data-race-metric="points_for">'+laNum(row.points_for,1)+'</td><td data-race-metric="points_against">'+laNum(row.points_against,1)+'</td><td data-race-metric="max_points_for">'+laNum(row.max_points_for,1)+'</td><td data-race-metric="expected_finish">'+laNum(s?.expected_finish,1)+'</td><td data-race-metric="playoff_probability">'+laProb(s?.playoff_probability)+'</td><td data-race-metric="championship_probability">'+laProb(s?.championship_probability)+'</td><td data-race-metric="expected_wins">'+laNum(s?.expected_wins,1)+'</td><td data-race-metric="first_place_probability">'+laProb(s?.first_place_probability)+'</td></tr>'}).join('');
  const colgroup='<colgroup><col class="atlas-col-rank"><col class="atlas-col-team"><col class="atlas-col-record"><col class="atlas-col-pf"><col class="atlas-col-pa"><col class="atlas-col-maxpf"><col class="atlas-col-finish"><col class="atlas-col-playoffs"><col class="atlas-col-champ"><col class="atlas-col-wins"><col class="atlas-col-first"></colgroup>';
  const race=laRaceHeaderDock()+'<div class="atlas-race-table-wrap"><table class="atlas-race-table">'+colgroup+'<tbody>'+raceRows+'</tbody></table></div>';
  const pre=laAtlas()?.preseason_expectation||{};
  let preHtml='';
  if(pre.status==='ready'){
    const preByTeam=new Map((pre.teams||[]).map(row=>[row.team_id,row]));
    preHtml='<div class="atlas-preseason-compare">'+standings.map(current=>{const before=preByTeam.get(current.team_id),now=laSimulation(current.team_id);if(!before)return'';return '<article class="atlas-preseason-row"><strong>'+laEsc(current.team_name)+'</strong><span><b>#'+before.rank+' → #'+current.rank+'</b><small>rank '+laRankDelta(before.rank,current.rank)+'</small></span><span><b>'+laProb(before.playoff_probability)+' → '+laProb(now?.playoff_probability)+'</b><small>playoffs '+laProbDelta(before.playoff_probability,now?.playoff_probability)+'</small></span><span><b>'+laProb(before.championship_probability)+' → '+laProb(now?.championship_probability)+'</b><small>champ '+laProbDelta(before.championship_probability,now?.championship_probability)+'</small></span></article>'}).join('')+'</div>';
  }else{
    preHtml='<div class="atlas-unavailable atlas-preseason-compact"><strong>2026 preseason baseline unavailable</strong><p>'+laEsc(pre.reason||'A valid pre-first-kickoff State + Forecast + Simulation coordinate could not be proven. Current rosters are not backfilled.')+'</p></div>';
  }
  const groups=laStateGroups();
  const shape=[['contender','Contender'],['competitive','Competitive'],['developing','Developing'],['rebuilding','Rebuilding']].map(item=>'<article class="'+item[0]+'"><b>'+groups[item[0]].length+'</b><span>'+item[1]+'</span><small>'+groups[item[0]].map(v=>laEsc(v.display_name)).join(' · ')+'</small></article>').join('');
  const simulationCopy=sim.status==='ready'
    ?Number(sim.simulation_count||0).toLocaleString()+' governed simulations using current standings, rosters and Forecast evidence.'
    :'Current standings and roster State are shown. Season-outlook Simulation is unavailable under current Forecast authority.';
  const worldDescriptions={expected_like:['Typical league outcome','A representative scoring path across the league.'],plausible_upside:['Higher-scoring league outcome','League-wide scoring is above its typical level.'],plausible_downside:['Lower-scoring league outcome','League-wide scoring is below its typical level.'],extreme_tail:['Unusual team-outcome pattern','The combined distance of teams’ simulated points from expectation is unusually large.'],biggest_blowout:['Largest simulated blowout','The widest margin in one simulated matchup.'],biggest_upset:['Largest simulated upset','The strongest result against pregame expectation.'],strong_team_misses_playoffs:['Strong team misses playoffs','A high-ranked team finishes outside the playoff field.'],low_seed_champion:['Lower-seeded champion','A lower playoff seed wins the title.']};
  const worlds=sim?.multiverse?.worlds||[],managedWorlds=managed?worlds.map(world=>({world,outcome:(world?.team_outcomes||[]).find(outcome=>outcome?.team_id===managed)||null})).filter(item=>item.outcome):[],worldCopy=managedWorlds.length?'<details class="league-section atlas-season-scenarios"><summary><span><b>Season scenarios</b><small>'+managedWorlds.length+' examples from the same '+Number(sim.simulation_count||0).toLocaleString()+'-run Simulation</small></span></summary><p class="atlas-scenario-note">Scenario labels describe the league-wide condition used to select each example. Rarity is how often that condition or event appeared in this same run; a typical example is selected for representativeness. Neither is your team’s odds. Your finish is that world’s simulated result, not a team-specific upside/downside or a separate probability.</p><div class="atlas-world-grid">'+managedWorlds.map(({world,outcome})=>{const copy=worldDescriptions[world.category]||['Simulated league scenario','Example from the governed Simulation.'],rarity=world?.rarity?.label||'example';return '<article><strong>'+laEsc(copy[0])+'</strong><span>'+(typeof outcome.regular_season_rank==='number'?'Your team: #'+outcome.regular_season_rank+' regular-season finish':'Your team result unavailable')+(outcome.champion?' · champion':'')+'</span><small>'+laEsc(copy[1])+' '+laEsc(String(rarity).charAt(0).toUpperCase()+String(rarity).slice(1)+' example')+'</small></article>'}).join('')+'</div></details>':'';
  return '<section class="atlas-glance"><article><small>Teams</small><strong>'+standings.length+'</strong><span>canonical State</span></article><article><small>Last completed</small><strong>'+(lastWeek?'Week '+lastWeek:'Preseason')+'</strong><span>completed matchups only</span></article><article><small>Your rank</small><strong>'+(managedStanding?'#'+managedStanding.rank:'—')+'</strong><span>'+(managedStanding?laRecord(managedStanding):'team not selected')+'</span></article><article><small>Your playoff / champ</small><strong>'+laProb(managedSim?.playoff_probability)+' / '+laProb(managedSim?.championship_probability)+'</strong><span>'+(sim.status==='ready'?Number(sim.simulation_count||0).toLocaleString()+' simulations':'Simulation unavailable')+'</span></article></section><section class="league-section league-race-section"><div class="league-section-heading"><div><p class="eyebrow">Current Season + Outlook from Today</p><h3>League Race</h3></div><small>'+laEsc(simulationCopy)+'</small></div>'+race+'</section>'+worldCopy+'<section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Preseason expectation → now</p><h3>What changed since the frozen baseline?</h3></div><small>'+(pre.status==='ready'?(pre.as_of?laEsc(pre.as_of):'frozen baseline'):'governed unavailable state')+'</small></div>'+preHtml+'</section><section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Competitive shape</p><h3>Governed Team Utility interpretation</h3></div><small>Interpretation layer; factual standings and Simulation remain above.</small></div><div class="atlas-shape-grid">'+shape+'</div></section>'+laPressurePoint()+laAgeStructure();
}
function laPositionsTab(){return laPositionMatrix()+'<section class="league-section league-depth-section"><div class="league-section-heading"><div><p class="eyebrow">Depth / fragility</p><h3>Roster resilience stays in frame</h3></div><small>Team-level governed resilience; not a fabricated position depth score.</small></div>'+laDepthStructure()+'</section>'}
function laValueTab(){return laValueLensSection()}
function laPickTab(){
  const map=laAtlas()?.pick_map||{},years=map.seasons||[],teams=map.teams||[];if(!fsfflLeagueStructureState.pickYear&&years.length)fsfflLeagueStructureState.pickYear=years[0];const year=fsfflLeagueStructureState.pickYear;
  if(!years.length)return'<section class="league-section atlas-unavailable"><h3>Pick Map unavailable</h3><p>No future draft-pick inventory is present in canonical State.</p></section>';
  const max=Math.max(1,...teams.map(team=>(team.by_year||[]).find(row=>Number(row.season)===Number(year))?.total_picks||0));
  const horizon=Math.max(...years);const rows=teams.map(team=>{const yr=(team.by_year||[]).find(row=>Number(row.season)===Number(year))||{total_picks:0,round_counts:{}};return{team,yr}}).sort((a,b)=>b.yr.total_picks-a.yr.total_picks||a.team.team_name.localeCompare(b.team.team_name)).map(item=>'<button type="button" class="atlas-pick-row" data-pick-team="'+laEsc(item.team.team_id)+'"><span class="atlas-pick-team"><strong>'+laEsc(item.team.team_name)+'</strong><small>'+year+' picks: '+item.yr.total_picks+' · '+item.team.total_owned_picks+' total through '+horizon+'</small></span><i><b style="width:'+(100*item.yr.total_picks/max).toFixed(1)+'%"></b></i><span class="atlas-pick-count"><b>'+String(item.yr.round_counts?.['1']||0)+'</b><small>1st</small></span><span class="atlas-pick-count"><b>'+String(item.yr.round_counts?.['2']||0)+'</b><small>2nd</small></span><span class="atlas-pick-count"><b>'+String(item.yr.round_counts?.['3']||0)+'</b><small>3rd</small></span><span class="atlas-pick-count"><b>'+String(item.yr.total_picks||0)+'</b><small>'+year+' total</small></span></button>').join('');
  return '<section class="league-section"><div class="league-section-heading"><div><p class="eyebrow">Pick Map</p><h3>Who controls future draft capital?</h3></div><small>Canonical ownership only · no arbitrary pick-value master score. Selected-year inventory is kept separate from all-horizon inventory.</small></div><div class="atlas-year-tabs">'+years.map(y=>'<button type="button" data-pick-year="'+y+'" class="'+(Number(y)===Number(year)?'active':'')+'">'+y+'</button>').join('')+'</div><div class="atlas-pick-table"><div class="atlas-pick-row header"><span>Team</span><span>Concentration</span><span>1st</span><span>2nd</span><span>3rd</span><span>'+year+' total</span></div>'+rows+'</div></section>';
}

function laRoomDrawer(){
  const room=fsfflLeagueStructureState.selectedRoom;if(!room)return'';const view=fsfflLeagueStructureState.views.find(v=>v.team_id===room.teamId),dynasty=fsfflLeagueStructureState.positionLens==='dynasty',rank=dynasty?laDynastyRoom(room.teamId,room.position):view?laStrength(view,room.position):null;if(!view)return'';
  const players=(view.players||[]).filter(p=>p.position===room.position).slice().sort((a,b)=>(b.projected_starter?1:0)-(a.projected_starter?1:0)||(Number(b.season_fantasy_points_projection)||-1)-(Number(a.season_fantasy_points_projection)||-1));
  const depthBucket=player=>player.roster_slot==='IR'?'IR':player.roster_slot==='TAXI'?'TAXI':player.projected_starter?'STARTER':'BENCH',depthCount=bucket=>players.filter(player=>depthBucket(player)===bucket).length,depthSummary='<div class="atlas-depth-summary"><span><b>'+String(depthCount('STARTER'))+'</b><small>projected starters</small></span><span><b>'+String(depthCount('BENCH'))+'</b><small>bench</small></span><span><b>'+String(depthCount('IR'))+'</b><small>IR</small></span><span><b>'+String(depthCount('TAXI'))+'</b><small>taxi</small></span></div>';
  const resilience=laResilience(view);
  const driverIds=resilience?.largest_single_player_lineup_drop_player_ids||[],driverLabel=laFragilityDriverLabel(view);
  const summary=dynasty
    ?'<span><b>'+(typeof rank?.room_raw==='number'?laNum(rank.room_raw,1):'—')+'</b><small>raw career-forward room</small></span><span><b>'+(typeof rank?.league_rank==='number'?'#'+rank.league_rank+' / '+rank.team_count:'—')+'</b><small>league rank</small></span><span><b>'+(typeof rank?.strength_index==='number'?laNum(rank.strength_index,0):'—')+'</b><small>league-average index</small></span><span><b>'+String(laRosterBreadth(room.teamId,room.position)?.rostered_player_count??'—')+'</b><small>rostered · breadth</small></span>'
    :'<span><b>'+(rank?'#'+rank.league_rank+' / '+rank.team_count:'—')+'</b><small>strength rank</small></span><span><b>'+laNum(rank?.strength_index,0)+'</b><small>strength index</small></span><span><b>'+laNum(rank?.expected_points,1)+'</b><small>starter points</small></span><span><b>'+laNum(resilience?.largest_single_player_lineup_drop,1)+'</b><small>team fragility · '+laEsc(driverLabel)+'</small></span>';
  const longTermStatus=fsfflLeagueStructureState.longTermStatus,longTermCopy=longTermStatus==='loading'?'Loading Foundation 4 player evidence…':longTermStatus==='building'?'Long-Term Intrinsic shadow is building. Reopen this detail after the refresh completes.':longTermStatus==='ready'?'The raw holistic career-forward reference contributes to the Dynasty room total. Y4–Y7 values below are annual Shapley marginal references, not full projected fantasy points.':longTermStatus==='unavailable'?'Long-Term Intrinsic request is temporarily unavailable; reopen this detail to retry. No substitute value is used.':longTermStatus==='stale'?'Long-Term Intrinsic is not loaded for this last-good State.':'Long-Term Intrinsic loads when Dynasty player detail is opened.';
  const playerRows=players.map(player=>{const value=(fsfflLeagueStructureState.valueLenses?.players||[]).find(v=>v.player_id===player.player_id),longTerm=(fsfflLeagueStructureState.longTermEvidence||{})[player.player_id],role=player.projected_starter?(player.projected_lineup_slot||'Projected starter'):(player.roster_slot||'Roster'),driver=driverIds.includes(player.player_id),age=typeof player.age_years==='number'?'age '+laNum(player.age_years,1):'age unavailable',projection=typeof player.season_fantasy_points_projection==='number'?laNum(player.season_fantasy_points_projection,1)+' season pts':'projection unavailable',market=typeof value?.broad_market_value_index==='number'?laValueIndex(value.broad_market_value_index):'—',intrinsic=typeof value?.intrinsic_value_index==='number'?laValueIndex(value.intrinsic_value_index):'—',marketPct=typeof value?.broad_market_percentile==='number'?Math.round(value.broad_market_percentile*100)+'th pct':'pct unavailable',intrinsicPct=typeof value?.intrinsic_percentile==='number'?Math.round(value.intrinsic_percentile*100)+'th pct':'pct unavailable',longTermState=fsfflLeagueStructureState.longTermStatus,longTermAnnual=Array.isArray(longTerm?.uncertainty?.long_horizon_y4_y7)?longTerm.uncertainty.long_horizon_y4_y7.map(row=>'Y'+row.year_index+' '+laNum(row.reference_center,1)).join(' · '):null,career=typeof longTerm?.raw_career_forward_reference==='number'?laNum(longTerm.raw_career_forward_reference,1):(longTermState==='ready'?'not reported':longTermState==='idle'?'not loaded':longTermState==='stale'?'not loaded for this last-good state':longTermState);return '<button type="button" class="'+(player.player_id===fsfflLeagueStructureState.focusPlayerId?'atlas-deep-link-focus':'')+'" data-player-intelligence-id="'+laEsc(player.player_id)+'"><span><strong>'+laEsc(player.full_name)+'</strong><small>'+laEsc(role)+' · '+age+' · '+projection+(driver?' · fragility driver':'')+'</small><small class="atlas-long-term-evidence">Holistic Long-Term Intrinsic shadow · raw career-forward reference: '+career+(longTermAnnual?' · Y4–Y7 marginal Shapley: '+longTermAnnual:'')+'</small></span><span><b>'+market+'</b><small>Market · '+marketPct+'</small></span><span><b>'+intrinsic+'</b><small>Current Intrinsic · '+intrinsicPct+'</small></span></button>'}).join('');
  const dynastyNote=dynasty?'<p class="atlas-scenario-note">Dynasty room raw totals sum each rostered player’s holistic career-forward reference once at actual position, including starters, bench, IR and taxi. The roster count is separate breadth evidence. Market and display indices do not enter the total.</p>':'';
  return '<aside class="atlas-drawer"><button type="button" data-atlas-close class="atlas-drawer-close" aria-label="Close">×</button><header><p class="eyebrow">Team-position detail</p><h3>'+laEsc(view.display_name)+' · '+laEsc(room.position)+'</h3><p>'+(dynasty?'Governed career-forward room allocation and separate player evidence.':'Actual rostered players and governed evidence behind the Current rank.')+'</p></header><div class="atlas-room-summary">'+summary+'</div>'+depthSummary+dynastyNote+(dynasty?'<p class="atlas-scenario-note">'+laEsc(longTermCopy)+'</p>':'')+'<div class="atlas-player-room">'+(playerRows||'<p>No rostered players at this position.</p>')+'</div><p class="atlas-foot">'+(dynasty?'Room rank sums raw holistic career-forward player references. Player-level Market, Current Intrinsic, and Long-Term display indices remain separate evidence; roster count is breadth only.':'Current rank = governed optimized-starter production relative to the league. Team-level resilience is context only; Atlas does not invent a position fragility score.')+'</p></aside>';
}
function laPickDrawer(){
  const id=fsfflLeagueStructureState.selectedPickTeamId;if(!id)return'';const team=(laAtlas()?.pick_map?.teams||[]).find(t=>t.team_id===id);if(!team)return'';
  const sortRows=items=>[...(items||[])].sort((a,b)=>a.season-b.season||a.round-b.round),ownedRows=sortRows(team.owned),tradedRows=sortRows(team.traded_away_original_picks);
  const pickIntel=row=>{const projection=row.projected_slot||null,value=row.fsffl_intrinsic_pick_value||null,estimate=value?.origin_aware_estimate||value?.generic_fallback_estimate||null;const slot=projection&&typeof projection.expected_slot==='number'?'Expected slot '+projection.expected_slot.toFixed(1)+(typeof projection.median_slot==='number'?' · median '+projection.median_slot.toFixed(0):''):null;const bands=projection?'Early '+laProb(projection.early_probability)+' · Mid '+laProb(projection.mid_probability)+' · Late '+laProb(projection.late_probability):null;const intrinsic=estimate&&typeof estimate?.distribution?.mean==='number'?'FSFFL Intrinsic '+laNum(estimate.distribution.mean,1):null;const authority=value?.origin_aware_estimate?'Team-of-origin value':value?.generic_fallback_estimate?'Generic class fallback':null;return [slot,bands,intrinsic,authority].filter(Boolean).join('<br>')};
  const renderPickRows=items=>items.map(row=>{const intel=pickIntel(row),status=row.status==='acquired'?'Acquired':row.status==='traded_away'?'Traded away':'Original pick';return '<article class="'+laEsc(row.status)+'"><span><strong>'+row.season+' · Round '+row.round+'</strong><small>'+laEsc(status)+'</small></span><b>'+laEsc(status)+'</b><p>'+(row.status==='acquired'?'Originally from '+laEsc(row.original_team_name||'another team'):row.status==='traded_away'?'Now owned by '+laEsc(row.owner_team_name||'another team'):'Originally owned by '+laEsc(team.team_name)+' · retained')+'</p>'+(intel?'<small class="atlas-pick-intel">'+intel+'</small>':'')+'</article>'}).join('');
  return '<aside class="atlas-drawer"><button type="button" data-atlas-close class="atlas-drawer-close" aria-label="Close">×</button><header><p class="eyebrow">Pick ownership + outlook</p><h3>'+laEsc(team.team_name)+'</h3><p>'+team.total_owned_picks+' picks currently owned · '+team.first_round_count+' first-round picks. Future slot outlook comes from governed Simulation; FSFFL pick value comes from Value.</p></header><section class="atlas-pick-group"><h4>Currently owned</h4><p>Original picks retained and picks acquired from other teams.</p><div class="atlas-pick-detail">'+(renderPickRows(ownedRows)||'<p>No future picks currently owned.</p>')+'</div></section>'+(tradedRows.length?'<section class="atlas-pick-group atlas-traded-picks"><h4>Traded away</h4><p>Original picks no longer owned by this team.</p><div class="atlas-pick-detail">'+renderPickRows(tradedRows)+'</div></section>':'')+'<p class="atlas-foot">Pick ownership and original team are shown separately. Slot probabilities come from Simulation. Team-of-origin FSFFL Intrinsic uses the pick’s original team outlook; generic class fallback is shown separately.</p></aside>';
}
function laActiveTab(){if(fsfflLeagueStructureState.activeTab==='positions')return laPositionsTab();if(fsfflLeagueStructureState.activeTab==='value')return laValueTab();if(fsfflLeagueStructureState.activeTab==='picks')return laPickTab();return laOverview()}
function laEvidenceStrip(){return '<footer class="atlas-evidence-strip"><span>State '+laEsc(String(laAtlas()?.league_state_id||'unavailable').slice(0,12))+'…</span><span>Simulation '+(laAtlas()?.simulation?.status==='ready'?Number(laAtlas()?.simulation?.simulation_count||0).toLocaleString()+' runs':'unavailable')+'</span><span>Value '+laEsc(fsfflLeagueStructureState.valueLenses?.status||fsfflLeagueStructureState.valueStatus)+'</span><span>Cold '+(typeof fsfflLeagueStructureState.loadMs==='number'?Math.round(fsfflLeagueStructureState.loadMs)+' ms':'—')+'</span></footer>'}
function bindLeagueActions(){
  document.querySelector('#league-open-market')?.addEventListener('click',()=>{if(typeof setRoute==='function')setRoute('opportunities')});
  document.querySelectorAll('[data-race-sort]').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.raceSort||'rank';if(fsfflLeagueStructureState.raceSortKey===key){fsfflLeagueStructureState.raceSortDirection=fsfflLeagueStructureState.raceSortDirection==='asc'?'desc':'asc'}else{fsfflLeagueStructureState.raceSortKey=key;fsfflLeagueStructureState.raceSortDirection=(key==='rank'||key==='expected_finish')?'asc':'desc'}renderLeagueComparison()}));
  document.querySelectorAll('[data-position-lens]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.positionLensMode=button.dataset.positionLens==='strength'?'strength':'rank';renderLeagueComparison()}));
  document.querySelectorAll('[data-position-view]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.positionLens=button.dataset.positionView==='dynasty'?'dynasty':'current';fsfflLeagueStructureState.positionLensMode='rank';renderLeagueComparison();if(fsfflLeagueStructureState.positionLens==='dynasty')void laLoadDynastyRooms();if(fsfflLeagueStructureState.positionLens==='dynasty'&&fsfflLeagueStructureState.selectedRoom)void laLoadLongTermEvidence()}));
  document.querySelectorAll('[data-atlas-tab]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.activeTab=button.dataset.atlasTab||'overview';fsfflLeagueStructureState.selectedRoom=null;fsfflLeagueStructureState.selectedPickTeamId=null;renderLeagueComparison()}));
  document.querySelectorAll('[data-room-team][data-room-position]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.selectedRoom={teamId:button.dataset.roomTeam,position:button.dataset.roomPosition};fsfflLeagueStructureState.selectedPickTeamId=null;renderLeagueComparison();if(fsfflLeagueStructureState.positionLens==='dynasty')void laLoadLongTermEvidence()}));
  document.querySelectorAll('[data-atlas-close]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.selectedRoom=null;fsfflLeagueStructureState.selectedPickTeamId=null;renderLeagueComparison()}));
  document.querySelectorAll('[data-value-mode]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.valueLensMode=button.dataset.valueMode||'difference';renderLeagueComparison()}));
  document.querySelectorAll('[data-value-team]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.selectedValueTeamId=button.dataset.valueTeam||null;renderLeagueComparison()}));
  document.querySelectorAll('[data-pick-year]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.pickYear=Number(button.dataset.pickYear);renderLeagueComparison()}));
  document.querySelectorAll('[data-pick-team]').forEach(button=>button.addEventListener('click',()=>{fsfflLeagueStructureState.selectedPickTeamId=button.dataset.pickTeam||null;fsfflLeagueStructureState.selectedRoom=null;renderLeagueComparison()}));
  bindLeagueRaceHeaderScroll();
}
function renderLeagueComparison(){
  const panel=leagueComparisonPanel();if(!panel)return;const views=fsfflLeagueStructureState.views;
  laConsumeDeepLinkIntent();
  if(!views.length||!fsfflLeagueStructureState.atlas){panel.innerHTML='<p class="eyebrow">League Atlas</p><h2>No governed league structure is available yet.</h2><p class="lead">Load current league evidence from Home, then return here.</p>';return}
  panel.classList.add('league-structure-panel','league-atlas-north-star');
  const freshness=fsfflLeagueStructureState.atlas?.intelligence_freshness||{};
  const staleBanner=freshness.stale?'<aside class="league-last-good-status" role="status"><strong>State current · last-good intelligence</strong><span>Derived fields as of '+laEsc(freshness.served_as_of||'last-good snapshot')+'.</span></aside>':'';
  panel.innerHTML=staleBanner+laAtlasHeader()+'<main class="league-atlas-content">'+laActiveTab()+laEvidenceDetail()+'</main>'+laRoomDrawer()+laPickDrawer();
  bindLeagueActions();setTimeout(laApplyDeepLinkFocus,0);
}
async function loadLeagueValueLenses(){
  const requestId=++fsfflLeagueValueLensRequestId;
  const requestedStateId=fsfflLeagueStructureState.atlas?.league_state_id||null;
  const requestedGeneration=fsfflLeagueStructureState.atlas?.publication_generation_id||null;
  const stillCurrent=(payloadGeneration=requestedGeneration)=>laValueLensResponseMatches(requestId,fsfflLeagueValueLensRequestId,requestedStateId,fsfflLeagueStructureState.atlas?.league_state_id||null,requestedGeneration,fsfflLeagueStructureState.atlas?.publication_generation_id||null,payloadGeneration);
  fsfflLeagueStructureState.valueStatus='loading';renderLeagueComparison();
  for(let attempt=0;attempt<80;attempt+=1){
    try{
      const payload=await api('/api/league/value-lenses');
      if(!stillCurrent(payload?.publication_generation_id||null))return;
      if(payload?.status==='loading'||payload?.build_status==='queued'||payload?.build_status==='running'){
        await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||1500));if(!stillCurrent())return;continue;
      }
      fsfflLeagueStructureState.valueLenses=payload;fsfflLeagueStructureState.valueStatus=payload?.status||'ready';fsfflLeagueStructureState.valueError=null;renderLeagueComparison();return;
    }catch(error){
      if(!stillCurrent())return;
      fsfflLeagueStructureState.valueLenses=null;fsfflLeagueStructureState.valueStatus='unavailable';fsfflLeagueStructureState.valueError=error.message||String(error);renderLeagueComparison();return;
    }
  }
  if(stillCurrent()){fsfflLeagueStructureState.valueStatus='unavailable';fsfflLeagueStructureState.valueError='Governed value-lens preparation did not complete within the bounded polling window.';renderLeagueComparison()}
}
async function laLoadDynastyRooms(){
  const requestedStateId=fsfflLeagueStructureState.atlas?.league_state_id||null;
  const requestedGeneration=fsfflLeagueStructureState.atlas?.publication_generation_id||null;
  if(fsfflLeagueStructureState.dynastyRoomStatus==='loading')return;
  if(fsfflLeagueStructureState.dynastyRoomStatus==='ready'&&fsfflLeagueStructureState.dynastyRooms?.league_state_id===requestedStateId)return;
  const requestId=++fsfflLeagueDynastyRoomsRequestId;
  const stillCurrent=()=>laAtlasEvidenceRequestMatches(requestId,fsfflLeagueDynastyRoomsRequestId,requestedStateId,fsfflLeagueStructureState.atlas?.league_state_id||null,requestedGeneration,fsfflLeagueStructureState.atlas?.publication_generation_id||null);
  fsfflLeagueStructureState.dynastyRoomStatus='loading';renderLeagueComparison();
  for(let attempt=0;attempt<20;attempt+=1){
    try{
      const payload=await api('/api/league/dynasty-position-rooms');
      if(!stillCurrent())return;
      if(payload?.league_state_id&&payload.league_state_id!==requestedStateId)throw new Error('Career-forward room evidence belongs to a different league State');
      if(requestedGeneration&&payload?.publication_generation_id!==requestedGeneration)throw new Error('Career-forward room evidence belongs to a different publication generation');
      if(payload?.status==='building'||payload?.build_status==='queued'||payload?.build_status==='running'){
        fsfflLeagueStructureState.dynastyRoomStatus='building';renderLeagueComparison();
        await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||1500));if(!stillCurrent())return;continue;
      }
      if(payload?.status!=='ready'||!Array.isArray(payload?.rooms))throw new Error(payload?.reason||'Holistic career-forward room evidence is unavailable');
      fsfflLeagueStructureState.dynastyRooms=payload;fsfflLeagueStructureState.dynastyRoomStatus=payload?.intelligence_freshness?.stale?'last-good':'ready';renderLeagueComparison();return;
    }catch(error){
      if(!stillCurrent())return;
      fsfflLeagueStructureState.dynastyRooms=null;fsfflLeagueStructureState.dynastyRoomStatus='unavailable';renderLeagueComparison();return;
    }
  }
  if(!stillCurrent())return;
  fsfflLeagueStructureState.dynastyRoomStatus='building';renderLeagueComparison();
}
async function laLoadLongTermEvidence(){
  if(!['idle','building','unavailable'].includes(fsfflLeagueStructureState.longTermStatus))return;
  const requestedStateId=fsfflLeagueStructureState.atlas?.league_state_id||null;
  const requestedGeneration=fsfflLeagueStructureState.atlas?.publication_generation_id||null;
  if(fsfflLeagueStructureState.atlas?.intelligence_freshness?.stale){fsfflLeagueStructureState.longTermEvidence=null;fsfflLeagueStructureState.longTermStatus='stale';renderLeagueComparison();return}
  const requestId=++fsfflLeagueLongTermRequestId;
  const stillCurrent=()=>laAtlasEvidenceRequestMatches(requestId,fsfflLeagueLongTermRequestId,requestedStateId,fsfflLeagueStructureState.atlas?.league_state_id||null,requestedGeneration,fsfflLeagueStructureState.atlas?.publication_generation_id||null);
  fsfflLeagueStructureState.longTermStatus='loading';renderLeagueComparison();
  try{
    const payload=await api('/api/value/long-term-intrinsic-shadow-v1');
    if(!stillCurrent())return;
    if(fsfflLeagueStructureState.atlas?.intelligence_freshness?.stale){fsfflLeagueStructureState.longTermEvidence=null;fsfflLeagueStructureState.longTermStatus='stale';renderLeagueComparison();return}
    if(payload?.status==='building'||payload?.build_status==='queued'||payload?.build_status==='running'){
      fsfflLeagueStructureState.longTermStatus='building';renderLeagueComparison();return;
    }
    if(payload?.league_state_id!==requestedStateId){fsfflLeagueStructureState.longTermEvidence=null;fsfflLeagueStructureState.longTermStatus='stale';renderLeagueComparison();return}
    if(!Array.isArray(payload?.estimates))throw new Error('Long-Term Intrinsic estimates are unavailable');
    fsfflLeagueStructureState.longTermEvidence=Object.fromEntries(payload.estimates.map(row=>[row.player_id,row]));
    fsfflLeagueStructureState.longTermStatus='ready';renderLeagueComparison();
  }catch(_error){if(!stillCurrent())return;fsfflLeagueStructureState.longTermEvidence=null;fsfflLeagueStructureState.longTermStatus='unavailable';renderLeagueComparison()}
}
function laAtlasPayloadsAligned(atlasPayload,teamViewsPayload,requestedStateId,expectedGeneration=null){
  if(!atlasPayload?.league_state_id||atlasPayload.league_state_id!==teamViewsPayload?.league_state_id)return false;
  if(requestedStateId&&atlasPayload.league_state_id!==requestedStateId)return false;
  const atlasGeneration=atlasPayload.publication_generation_id||null;
  const teamViewsGeneration=teamViewsPayload.publication_generation_id||null;
  if(atlasGeneration!==teamViewsGeneration)return false;
  return !expectedGeneration||(atlasGeneration===expectedGeneration&&teamViewsGeneration===expectedGeneration);
}
function laValueLensResponseMatches(requestId,currentRequestId,requestedStateId,currentStateId,requestedGeneration,currentGeneration,payloadGeneration){
  if(requestId!==currentRequestId||requestedStateId!==currentStateId||requestedGeneration!==currentGeneration)return false;
  return payloadGeneration===requestedGeneration;
}
function laAtlasContextTarget(context,force=false,requestedGeneration=null){
  const readiness=context?.capability_readiness||{},served=readiness.served_last_good||{};
  const usingLastGood=!force&&readiness.overall_status==='rebuilding'&&served.available===true&&served.league_state_id&&served.publication_generation_id;
  return {
    canonicalStateId:context?.state_id||null,
    stateId:usingLastGood?served.league_state_id:(context?.state_id||null),
    generationId:requestedGeneration||(usingLastGood?served.publication_generation_id:(readiness.publication?.generation_id||context?.publication_generation_id||null)),
  };
}
let fsfflLeagueValueLensRequestId=0;
let fsfflLeagueDynastyRoomsRequestId=0;
let fsfflLeagueLongTermRequestId=0;
function laAtlasEvidenceRequestMatches(requestId,currentRequestId,requestedStateId,currentStateId,requestedGeneration,currentGeneration){
  return requestId===currentRequestId&&requestedStateId===currentStateId&&requestedGeneration===currentGeneration;
}
async function loadFsfflLeagueComparison(options={}){
  const force=options?.force===true,target=laAtlasContextTarget(state?.context,force,options?.expectedGeneration||null);
  const expectedGeneration=target.generationId,expectedStateId=target.stateId;
  if(fsfflLeagueComparisonLoadPromise){
    await fsfflLeagueComparisonLoadPromise;
    if(fsfflLeagueStructureState.atlas?.publication_generation_id===expectedGeneration&&fsfflLeagueStructureState.atlas?.league_state_id===expectedStateId)return;
  }
  const request=fetchFsfflLeagueComparison({force,expectedGeneration});
  fsfflLeagueComparisonLoadPromise=request;
  try{return await request}
  finally{if(fsfflLeagueComparisonLoadPromise===request)fsfflLeagueComparisonLoadPromise=null}
}
async function fetchFsfflLeagueComparison({force=false,expectedGeneration=null}={}){
  const panel=leagueComparisonPanel();if(!panel)return;
  if(!state?.context?.league_id){panel.innerHTML='<p class="eyebrow">League Atlas</p><h2>Connect a league first.</h2><p class="lead">Load a league from Home to see its competitive landscape.</p>';return}
  const context=state?.context||{},contextStateId=context.state_id||null;
  const target=laAtlasContextTarget(context,force,expectedGeneration);
  const stateId=target.stateId;
  const started=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();
  expectedGeneration=target.generationId;
  const atlasGeneration=fsfflLeagueStructureState.atlas?.publication_generation_id||null;
  const publicationMatches=expectedGeneration===atlasGeneration;
  if(!force&&publicationMatches&&fsfflLeagueStructureState.atlas&&stateId&&fsfflLeagueStructureState.atlas.league_state_id===stateId&&fsfflLeagueStructureState.views.length){
    const ended=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();fsfflLeagueStructureState.warmMs=Math.max(0,ended-started);renderLeagueComparison();if(!fsfflLeagueStructureState.valueLenses&&fsfflLeagueStructureState.valueStatus!=='loading')void loadLeagueValueLenses();return;
  }
  panel.innerHTML='<div class="atlas-loading"><i></i><strong>League Atlas</strong><span>Loading State, Simulation and league structure independently of Intrinsic.</span></div>';
  try{
    let atlasPayload=null,teamViewsPayload=null;
    for(let attempt=0;attempt<3;attempt+=1){
      const results=await Promise.all([api('/api/league/atlas'),api('/api/league/team-views')]);
      if(laAtlasPayloadsAligned(results[0],results[1],stateId,expectedGeneration)){atlasPayload=results[0];teamViewsPayload=results[1];break}
      if(attempt<2)await new Promise(resolve=>setTimeout(resolve,150));
    }
    const latestContext=state?.context||{},latestTarget=laAtlasContextTarget(latestContext,force,null);
    if(!atlasPayload||!teamViewsPayload||atlasPayload.league_state_id!==stateId||latestContext.state_id!==contextStateId||latestTarget.stateId!==stateId||latestTarget.generationId!==expectedGeneration)throw new Error('League State changed while the Atlas and roster views were loading. Reload to align the evidence.');
    if(expectedGeneration&&atlasPayload.publication_generation_id!==expectedGeneration){
      throw new Error('League Atlas is waiting for the matching published intelligence generation.');
    }
    const retainedViewState=force?{
      activeTab:fsfflLeagueStructureState.activeTab,
      positionLens:fsfflLeagueStructureState.positionLens,
      positionLensMode:fsfflLeagueStructureState.positionLensMode,
      raceSortKey:fsfflLeagueStructureState.raceSortKey,
      raceSortDirection:fsfflLeagueStructureState.raceSortDirection,
      selectedValueTeamId:fsfflLeagueStructureState.selectedValueTeamId,
      selectedRoom:fsfflLeagueStructureState.selectedRoom,
      selectedPickTeamId:fsfflLeagueStructureState.selectedPickTeamId,
      pickYear:fsfflLeagueStructureState.pickYear,
    }:null;
    fsfflLeagueDynastyRoomsRequestId+=1;fsfflLeagueLongTermRequestId+=1;
    fsfflLeagueStructureState.atlas=atlasPayload;fsfflLeagueStructureState.views=teamViewsPayload.team_views||[];
    fsfflLeagueStructureState.valueLenses=null;fsfflLeagueStructureState.valueStatus='idle';fsfflLeagueStructureState.valueError=null;fsfflLeagueStructureState.longTermEvidence=null;fsfflLeagueStructureState.longTermStatus='idle';fsfflLeagueStructureState.dynastyRooms=null;fsfflLeagueStructureState.dynastyRoomStatus='idle';fsfflLeagueStructureState.positionLens=retainedViewState?.positionLens||'current';fsfflLeagueStructureState.positionLensMode=retainedViewState?.positionLensMode||'rank';
    fsfflLeagueStructureState.managedTeamId=state?.context?.team_id||fsfflLeagueStructureState.atlas?.managed_team_id||null;
    fsfflLeagueStructureState.activeTab=retainedViewState?.activeTab||'overview';
    fsfflLeagueStructureState.raceSortKey=retainedViewState?.raceSortKey||'rank';fsfflLeagueStructureState.raceSortDirection=retainedViewState?.raceSortDirection||'asc';
    fsfflLeagueStructureState.selectedValueTeamId=retainedViewState?.selectedValueTeamId||null;
    fsfflLeagueStructureState.selectedRoom=retainedViewState?.selectedRoom||null;fsfflLeagueStructureState.selectedPickTeamId=retainedViewState?.selectedPickTeamId||null;
    fsfflLeagueStructureState.pickYear=retainedViewState?.pickYear||fsfflLeagueStructureState.atlas?.pick_map?.seasons?.[0]||null;
    if(!force){fsfflLeagueStructureState.selectedRoom=null;fsfflLeagueStructureState.selectedPickTeamId=null}
    const ended=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();fsfflLeagueStructureState.loadMs=Math.max(0,ended-started);
    renderLeagueComparison();void loadLeagueValueLenses();
    if(fsfflLeagueStructureState.positionLens==='dynasty')void laLoadDynastyRooms();
    if(fsfflLeagueStructureState.positionLens==='dynasty'&&fsfflLeagueStructureState.selectedRoom)void laLoadLongTermEvidence();
  }catch(error){panel.innerHTML='<p class="eyebrow">League Atlas</p><h2>Unable to load league intelligence.</h2><p class="lead">'+laEsc(error.message||error)+'</p><p class="lead">Missing evidence is never replaced with a decorative score.</p>'}
}
function installLeagueComparisonStyles(){
  if(!document.querySelector('link[data-fsffl-league-atlas-css]')){const link=document.createElement('link');link.rel='stylesheet';link.dataset.fsfflLeagueAtlasCss='true';link.href='/static/league_atlas.css?v=20261004-publication-handoff378';document.head.appendChild(link)}
  if(document.querySelector('#fsffl-league-atlas-v1-style'))return;
  const style=document.createElement('style');style.id='fsffl-league-atlas-v1-style';
  style.textContent='.league-last-good-status{display:flex;align-items:center;gap:7px;min-height:28px;padding:5px 8px;margin:0 0 8px;border:1px solid #765526;border-radius:8px;background:rgba(155,106,42,.07);color:#d7bc8c;font-size:9px;line-height:1.25}.league-last-good-status strong{white-space:nowrap}.league-last-good-status span{color:#bda77f;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.league-structure-panel{padding:0!important;background:transparent!important;border:0!important;box-shadow:none!important}.atlas-deep-link-focus{box-shadow:inset 0 0 0 2px #38bdf8!important;background-color:rgba(56,189,248,.12)!important}.league-structure-hero{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(280px,.85fr);gap:16px;margin-bottom:16px}.league-structure-hero>div:first-child,.league-takeaway,.league-section,.league-pressure,.league-detail{border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,#0b1424,#09101d);box-shadow:0 16px 34px rgba(0,0,0,.16)}.league-structure-hero>div:first-child{padding:22px}.league-takeaway{padding:20px;display:flex;flex-direction:column;justify-content:center;gap:8px}.league-takeaway span,.league-section-heading>small,.league-value-toolbar>span{color:var(--muted);font-size:10px}.league-section{padding:18px;margin:14px 0}.league-section-heading{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:14px}.league-edge-matrix{overflow-x:auto;border:1px solid var(--line);border-radius:14px}.league-edge-row{display:grid;grid-template-columns:minmax(150px,1.4fr) repeat(4,minmax(74px,.7fr));min-width:520px;border-top:1px solid var(--line)}.league-edge-row:first-child{border-top:0}.league-edge-row.header{font-size:10px;color:var(--muted);text-transform:uppercase}.league-edge-row>span{padding:9px 10px}.league-edge-cell{display:flex;align-items:center;justify-content:center;gap:5px;border-left:1px solid var(--line)}.league-edge-cell small{font-size:9px;color:var(--muted)}.league-edge-cell.elite{background:rgba(54,211,153,.13)}.league-edge-cell.strong{background:rgba(78,156,255,.10)}.league-edge-cell.weak{background:rgba(239,103,103,.08)}.league-edge-team{display:grid}.league-edge-team small{color:#63aafc;font-size:9px}.league-edge-row.managed{background:rgba(46,142,255,.05)}.league-value-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}.league-value-modes{display:flex;gap:6px;flex-wrap:wrap}.league-value-modes button{border:1px solid var(--line);border-radius:999px;background:#08101c;color:var(--muted);padding:7px 10px;font-size:10px;font-weight:700}.league-value-modes button.active{color:#fff;border-color:#3d83c9;background:#10243a}.league-value-axis{display:grid;grid-template-columns:1fr 1fr 1fr;padding:0 8px 5px 150px;color:var(--muted);font-size:9px}.league-value-axis span:nth-child(2){text-align:center}.league-value-axis span:last-child{text-align:right}.league-value-grid{border:1px solid var(--line);border-radius:14px;overflow:hidden}.league-value-row{width:100%;display:grid;grid-template-columns:140px minmax(0,1fr);gap:10px;align-items:center;border:0;border-top:1px solid var(--line);background:#09111e;color:inherit;padding:9px 10px;text-align:left}.league-value-row:first-child{border-top:0}.league-value-row.selected{box-shadow:inset 0 0 0 1px #3d83c9}.league-value-team{display:grid;min-width:0}.league-value-team strong{font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.league-value-team small{font-size:9px;color:var(--muted)}.league-value-strip{position:relative;height:22px;border-left:1px solid var(--line);border-right:1px solid var(--line);background:linear-gradient(90deg,transparent 49.7%,rgba(255,255,255,.12) 50%,transparent 50.3%)}.league-value-dot{position:absolute;top:50%;width:7px;height:7px;border-radius:50%;transform:translate(-50%,-50%);background:#7ca8db}.league-value-dot.pos-rb{background:#8ee0bd}.league-value-dot.pos-wr{background:#d6a5ff}.league-value-dot.pos-te{background:#f2cc7e}.league-value-detail{margin-top:10px;border:1px solid var(--line);border-radius:12px;padding:11px}.league-value-detail>div:first-child{display:flex;justify-content:space-between}.league-value-player-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:8px}.league-value-player{display:grid;grid-template-columns:minmax(0,1fr) repeat(3,auto);gap:8px;align-items:center;border:1px solid var(--line);border-radius:9px;padding:8px}.league-value-player>div,.league-value-player>span{display:grid}.league-value-player>span{text-align:right}.league-value-player small{font-size:8px;color:var(--muted)}.league-pressure{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(240px,.9fr) auto;gap:16px;align-items:center;padding:18px;margin:14px 0}.league-pressure p{color:var(--muted);font-size:11px}.league-supply-list{display:grid;gap:6px}.league-supply-team{display:grid;grid-template-columns:auto 1fr auto;gap:8px;font-size:10px}.league-two-column{display:grid;grid-template-columns:1fr 1fr;gap:14px}.league-state-lanes,.league-age-track,.league-pick-band{display:grid;gap:7px}.league-state-lane,.league-age-row,.league-depth-row{border:1px solid var(--line);border-radius:10px;padding:9px}.league-state-lane>div:first-child{display:flex;justify-content:space-between}.league-team-chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.league-team-chip{border:1px solid var(--line);border-radius:999px;padding:4px 7px}.league-team-chip small{font-size:8px;color:var(--muted)}.league-age-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px}.league-age-reading{display:grid;text-align:right}.league-age-reading span{font-size:8px;color:var(--muted)}.league-pick-row{display:grid;grid-template-columns:minmax(120px,1fr) minmax(120px,2fr) auto;gap:10px;align-items:center}.league-pick-row>div{display:grid}.league-pick-row small{font-size:8px;color:var(--muted)}.league-pick-row>i{height:8px;border-radius:999px;background:#08101c;border:1px solid var(--line);overflow:hidden}.league-pick-row>i>b{display:block;height:100%;background:#4e9cff}.league-detail{margin:14px 0}.league-detail summary{padding:15px 18px;font-weight:700}.league-detail>p,.league-evidence-copy{padding:0 18px 16px;color:var(--muted);font-size:11px;line-height:1.5}.league-depth-grid{padding:0 18px 18px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.league-depth-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px}.league-depth-row>span{display:grid;text-align:right}.league-depth-row small{font-size:8px;color:var(--muted)}@media(max-width:900px){.league-structure-hero,.league-two-column{grid-template-columns:1fr}.league-pressure{grid-template-columns:1fr}.league-value-player-grid,.league-depth-grid{grid-template-columns:1fr}.league-section-heading,.league-value-toolbar{align-items:flex-start;flex-direction:column}}@media(max-width:560px){.league-structure-hero>div:first-child,.league-takeaway,.league-section,.league-pressure{border-radius:14px;padding:14px}.league-edge-row{grid-template-columns:minmax(125px,1.25fr) repeat(4,minmax(63px,.7fr));min-width:440px}.league-value-axis{padding-left:105px}.league-value-row{grid-template-columns:95px minmax(0,1fr);gap:7px}.league-value-player{grid-template-columns:minmax(0,1fr) repeat(3,34px)}.league-pick-row{grid-template-columns:minmax(90px,1fr) minmax(90px,1.5fr) auto}}';
  document.head.appendChild(style);
}
let fsfflLeagueComparisonLoadPromise=null;
function renderFsfflLeagueComparison(options={}){installLeagueComparisonStyles();return loadFsfflLeagueComparison(options)}
window.renderFsfflLeagueComparison=renderFsfflLeagueComparison;
window.fsfflLeagueAtlasDiagnostics=()=>({version:'20261004-publication-handoff378',league_state_id:fsfflLeagueStructureState.atlas?.league_state_id||null,publication_generation_id:fsfflLeagueStructureState.atlas?.publication_generation_id||null,cold_load_ms:fsfflLeagueStructureState.loadMs,warm_render_ms:fsfflLeagueStructureState.warmMs,value_status:fsfflLeagueStructureState.valueLenses?.status||fsfflLeagueStructureState.valueStatus,simulation_status:fsfflLeagueStructureState.atlas?.simulation?.status||'unavailable',preseason_status:fsfflLeagueStructureState.atlas?.preseason_expectation?.status||'unavailable'});
