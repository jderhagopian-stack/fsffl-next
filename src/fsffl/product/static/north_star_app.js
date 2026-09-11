/* North Star app layer.
 * Presentation only. It compresses already-authoritative State/Simulation/Value/Analytics
 * evidence into scan-first graphics and keeps exact measurements available underneath.
 */
(function(){
  let queued=false;
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const pct=value=>finite(value)?Math.max(0,Math.min(100,value*100)):null;
  const num=(value,digits=1)=>finite(value)?value.toFixed(digits):'—';
  const words=value=>String(value||'').replaceAll('_',' ');
  const initials=name=>String(name||'?').split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join('').toUpperCase();

  function installNorthStarMarketAssets(){
    if(!document.querySelector('link[data-ns-market]')){
      const link=document.createElement('link');link.rel='stylesheet';link.href='/static/north_star_market.css?v=20260910-phase3-visual2';link.dataset.nsMarket='true';document.head.appendChild(link);
    }
    if(!document.querySelector('script[data-ns-market]')){
      const script=document.createElement('script');script.src='/static/north_star_market.js?v=20260910-phase3-visual2';script.defer=true;script.dataset.nsMarket='true';document.head.appendChild(script);
    }
  }

  function ring(value,label,sub){
    const percent=pct(value);if(percent==null)return'';
    return `<div class="ns-app-ring" style="--ns-ring:${percent.toFixed(1)}" role="img" aria-label="${esc(label)} ${Math.round(percent)} percent"><div><strong>${Math.round(percent)}%</strong><span>${esc(label)}</span>${sub?`<small>${esc(sub)}</small>`:''}</div></div>`;
  }
  function strengthBand(rank,count){
    if(!finite(rank)||!finite(count)||count<=0)return'unknown';
    const share=(rank-1)/Math.max(1,count-1);
    if(share<=.2)return'elite';if(share<=.42)return'strong';if(share<=.7)return'neutral';return'weak';
  }
  function strength(view,position){return(view?.position_strengths||[]).find(row=>row.position===position)||null}

  function enhanceHome(){
    const priority=document.querySelector('#home-attention .home-priority');
    if(!priority||priority.querySelector('.ns-home-scan'))return;
    const view=typeof state!=='undefined'?state?.teamView:null;if(!view)return;
    const outcome=view.utility?.competitive_outcome;
    const positions=(view.position_strengths||[]).filter(row=>['QB','RB','WR','TE'].includes(row.position)&&finite(row.league_rank));
    const strongest=[...positions].sort((a,b)=>a.league_rank-b.league_rank)[0];
    const weakest=[...positions].sort((a,b)=>b.league_rank-a.league_rank)[0];
    const scan=document.createElement('aside');scan.className='ns-home-scan';
    scan.innerHTML=`${ring(outcome?.playoff_probability,'Playoffs',finite(outcome?.expected_wins)?`${num(outcome.expected_wins,1)} expected wins`:'')}
      <div class="ns-home-scan-copy">
        <div><span>Best room</span><strong>${strongest?`${esc(strongest.position)} #${strongest.league_rank}`:'—'}</strong><small>${strongest&&strongest.league_rank===1?'Strongest in the league':'League-relative lineup strength'}</small></div>
        <div><span>Pressure point</span><strong>${weakest?`${esc(weakest.position)} #${weakest.league_rank}`:'—'}</strong><small>${weakest&&weakest.team_count?`of ${weakest.team_count} teams`:'League-relative lineup strength'}</small></div>
      </div>`;
    priority.appendChild(scan);
  }

  function enhanceFranchise(){
    const hero=document.querySelector('.franchise-hero');if(!hero||hero.querySelector('.ns-franchise-visual'))return;
    const view=typeof fsfflMyTeamState!=='undefined'?fsfflMyTeamState.view:null;if(!view)return;
    const positions=(view.position_strengths||[]).filter(row=>['QB','RB','WR','TE'].includes(row.position)&&finite(row.league_rank));
    const outcome=view.utility?.competitive_outcome;
    const visual=document.createElement('div');visual.className='ns-franchise-visual';
    visual.innerHTML=`${ring(outcome?.playoff_probability,'Playoffs',finite(outcome?.championship_probability)?`${Math.round(outcome.championship_probability*100)}% title`:'')}
      <div class="ns-franchise-mini-bars">${positions.map(row=>{const count=row.team_count||12;const score=Math.max(8,100-((row.league_rank-1)/Math.max(1,count-1))*92);return `<div class="ns-mini-position ${strengthBand(row.league_rank,count)}" title="${esc(row.position)} #${row.league_rank} of ${count}; strength index ${num(row.strength_index,0)}"><span>${esc(row.position)}</span><i><b style="width:${score.toFixed(1)}%"></b></i><strong>#${row.league_rank}</strong></div>`}).join('')}</div>`;
    hero.querySelector('.franchise-hero-main')?.appendChild(visual);

    document.querySelectorAll('.franchise-focus').forEach(card=>{
      if(card.querySelector('.ns-identity-mark'))return;const heading=card.querySelector('h3');if(!heading)return;
      const label=heading.textContent.trim();if(!label||/unavailable|risk|points|nonstarter/i.test(label))return;
      const mark=document.createElement('span');mark.className='ns-identity-mark';mark.textContent=initials(label);mark.setAttribute('aria-hidden','true');heading.before(mark);
    });
  }

  function leagueViews(){try{return typeof fsfflLeagueStructureState!=='undefined'?(fsfflLeagueStructureState.views||[]):[]}catch(_){return[]}}
  function leagueManagedId(){try{return typeof fsfflLeagueStructureState!=='undefined'?fsfflLeagueStructureState.managedTeamId:null}catch(_){return null}}
  function leagueAtlas(){
    const section=document.querySelector('.league-position-section');if(!section||document.querySelector('.ns-league-atlas'))return;
    const views=leagueViews();if(!views.length)return;const positions=['QB','RB','WR','TE'],managed=leagueManagedId();
    const atlas=document.createElement('section');atlas.className='ns-league-atlas';
    const sorted=[...views].sort((a,b)=>a.team_id===managed?-1:b.team_id===managed?1:((a.display_name||'').localeCompare(b.display_name||'')));
    atlas.innerHTML=`<div class="ns-app-section-head"><div><p class="eyebrow">League map</p><h3>See positional control at a glance.</h3></div><div class="ns-atlas-legend"><span><i class="elite"></i>Strength</span><span><i class="neutral"></i>Middle</span><span><i class="weak"></i>Weakness</span></div></div>
      <div class="ns-atlas-grid"><div class="ns-atlas-row header"><span>Team</span>${positions.map(p=>`<b>${p}</b>`).join('')}</div>${sorted.map(view=>`<button type="button" class="ns-atlas-row${view.team_id===managed?' managed':''}" data-ns-team="${esc(view.team_id)}"><span>${esc(view.display_name)}</span>${positions.map(position=>{const row=strength(view,position);if(!row)return'<i class="unknown" title="No current position-strength evidence"></i>';const count=row.team_count||views.length;return `<i class="${strengthBand(row.league_rank,count)}" title="${esc(position)} #${row.league_rank} of ${count}; strength index ${num(row.strength_index,0)}"><em>#${row.league_rank}</em></i>`}).join('')}</button>`).join('')}</div>
      <div class="ns-atlas-detail" aria-live="polite">Tap a franchise to see exact league-relative numbers.</div>`;
    section.before(atlas);
    atlas.querySelectorAll('[data-ns-team]').forEach(button=>button.addEventListener('click',()=>{
      const view=views.find(item=>String(item.team_id)===String(button.dataset.nsTeam));if(!view)return;
      atlas.querySelectorAll('[data-ns-team]').forEach(row=>row.classList.toggle('selected',row===button));
      const outcome=view.utility?.competitive_outcome,resilience=view.utility?.roster_resilience;
      const exact=positions.map(position=>{const row=strength(view,position);return row?`<span><b>${position}</b><strong>#${row.league_rank}</strong><small>${num(row.strength_index,0)} index</small></span>`:''}).join('');
      atlas.querySelector('.ns-atlas-detail').innerHTML=`<div><strong>${esc(view.display_name)}</strong><small>${esc(words(view.utility?.calculated_competitive_state||'unclassified'))}${finite(outcome?.playoff_probability)?` · ${Math.round(outcome.playoff_probability*100)}% playoffs`:''}</small></div><div class="ns-atlas-exact">${exact}</div>${resilience&&finite(resilience.largest_single_player_lineup_drop)?`<span class="ns-atlas-risk">${num(resilience.largest_single_player_lineup_drop,1)} pts largest one-player lineup drop</span>`:''}`;
    }));
  }

  function compressLeagueLists(){
    const panel=document.querySelector('.league-structure-panel');if(!panel||panel.classList.contains('ns-app-compressed'))return;panel.classList.add('ns-app-compressed');
    panel.querySelectorAll('.league-section-heading>small').forEach(note=>{note.classList.add('ns-supporting-detail')});
    const age=panel.querySelector('.league-age-track');if(age)age.classList.add('ns-horizontal-band');
    const assets=panel.querySelector('.league-asset-grid');if(assets)assets.classList.add('ns-horizontal-band');
    const depth=panel.querySelector('.league-depth-grid');if(depth)depth.classList.add('ns-horizontal-band');
  }

  function simplifyPrimaryLanguage(){
    const league=document.querySelector('.league-structure-panel');
    if(league){const lead=league.querySelector('.league-structure-hero .lead'),copy='Spot the league’s strongest rooms, weakest links, competitive tiers and future flexibility at a glance.';if(lead&&lead.textContent!==copy)lead.textContent=copy}
    const franchise=document.querySelector('.franchise-header>div>p:last-child');if(franchise&&franchise.textContent.length>170&&!franchise.classList.contains('ns-supporting-detail'))franchise.classList.add('ns-supporting-detail');
  }

  function enhance(){queued=false;installNorthStarMarketAssets();enhanceHome();enhanceFranchise();leagueAtlas();compressLeagueLists();simplifyPrimaryLanguage()}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  const observer=new MutationObserver(schedule);
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',()=>{observer.observe(document.body,{childList:true,subtree:true});schedule()},{once:true});else{observer.observe(document.body,{childList:true,subtree:true});schedule()}
  window.addEventListener('fsffl:product-context-updated',schedule);
  window.addEventListener('load',schedule,{once:true});
})();
