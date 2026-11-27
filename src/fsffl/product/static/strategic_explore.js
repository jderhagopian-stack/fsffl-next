/* Explore composes published Search/Decision evidence. No valuation or outcome model. */
(function(){
  'use strict';
  const GOALS={current_competitiveness:'Win now',three_year_contribution:'Build over 3 years',career_contribution:'Build for the long term'};
  const ALL=Object.keys(GOALS);
  const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const signed=(v,d=1)=>{if(!finite(v))return 'Unavailable';const rounded=Number(v.toFixed(d));return(rounded>0?'+':'')+(rounded===0?0:v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});};
  const ctx=()=>typeof state!=='undefined'?state.context||{}:{};
  const contextKey=()=>JSON.stringify([ctx().user_id,ctx().league_id,ctx().team_id,ctx().state_id,ctx().capability_readiness?.publication?.generation_id||ctx().publication_generation_id]);
  const fresh=()=>({key:contextKey(),prices:new Map(),priceBusy:false,sequence:0,result:null,browser:null,busy:false,inFlight:false,pauseRequested:false,pendingBatch:null,started:false,error:'',browserError:'',browserLoading:false,mode:'automatic',goals:[ALL[0]],young:false,picks:false,partner:'',position:'',target:'',offer:'',protected:[],directed:false,expanded:false,dirty:false});
  let view=fresh(),host=null;
  function reconcile(){if(view.key!==contextKey())view=fresh();}
  function visibleHost(){return host?.isConnected&&typeof state!=='undefined'&&state.route==='opportunities'&&host.id==='market-ns-body'&&['for_you','trade_finder'].includes(window.fsfflMarketNorthStar?.activeTab?.());}
  const asset=ref=>[view.browser?.focal_team,...(view.browser?.counterparties||[])].filter(Boolean).flatMap(t=>t.assets||[]).find(a=>a.asset_ref===ref);
  const teamName=id=>(view.browser?.counterparties||[]).find(t=>t.team_id===id)?.display_name||'Other franchise';
  const option=(v,label,selected)=>`<option value="${esc(v)}"${selected===v?' selected':''}>${esc(label)}</option>`;
  function instructions(){
    if(view.mode==='automatic')return view.protected.length?{protected_player_ids:[...view.protected]}:null;
    if(!view.goals.length)throw new Error('Choose at least one priority.');
    return{objectives:[...view.goals],protected_player_ids:[...view.protected]};
  }
  function requestBody(){const body={max_candidates:80,evaluation_budget:8};const goals=instructions();if(goals)body.search_instructions=goals;if(view.partner)body.counterparty_team_id=view.partner;if(view.position)body.target_position=view.position;if(view.target)body.target_asset_ref=view.target;if(view.offer)body.offered_asset_ref=view.offer;if(view.young||view.picks){body.target_asset_kinds=[...(view.young?['player']:[]),...(view.picks?['pick']:[])];if(view.young)body.target_player_max_age=26;}return body;}
  function priorities(context){return(context?.objectives||[]).map(g=>GOALS[g]||g.replaceAll('_',' ')).join(' / ')||'Direction unavailable';}
  const stateNames={contender:'Contender',competitive:'Competitive',developing:'Developing',rebuilding:'Rebuilding',unknown:'Unavailable'};
  const postureNames={win_now:'Win now',balanced:'Balanced',retool:'Build over 3 years',rebuild:'Build for the long term'};
  const pct=value=>finite(value)?(value*100).toFixed(1)+'%':'Unavailable';
  function direction(){
    const competitive=view.result?.competitive_context;
    const priority=view.result?.priority_context;
    const calculated=competitive?.calculated_competitive_state||(!priority?.explicitly_directed?priority?.calculated_competitive_state:null)||'unknown';
    const posture=competitive?.default_search_posture||(!priority?.explicitly_directed?priority?.inferred_posture:null);
    const inferred=priority?.explicitly_directed?null:priority;
    const lens=calculated==='unknown'?'Compare all horizons · state unavailable':postureNames[posture]||'Direction preparing';
    return `<section class="se-direction"><div class="se-row"><p class="eyebrow">Your Direction</p></div><div class="se-competitive"><span>Calculated competitive state</span><strong>${esc(stateNames[calculated]||calculated)}</strong>${competitive?`<p>Playoff chance <b>${pct(competitive.playoff_probability)}</b> · Championship chance <b>${pct(competitive.championship_probability)}</b></p>`:''}</div><div class="se-modes" role="group" aria-label="Search direction">${[['automatic','Automatic'],['custom','Set priorities']].map(([key,label])=>`<button type="button" data-se-mode="${key}" aria-pressed="${view.mode===key}">${label}</button>`).join('')}</div>${view.mode==='custom'?`<fieldset class="se-protect"><legend>Your priorities · choose any combination</legend>${Object.entries(GOALS).map(([g,label])=>`<label><input type="checkbox" data-se-priority="${g}"${view.goals.includes(g)?' checked':''}><span>${label}</span></label>`).join('')}</fieldset>`:`<span class="se-direction-label">Automatic lens: ${esc(lens)}</span><p>${esc(inferred?priorities(inferred):'Server priorities will be shown after discovery.')}</p>`}<details class="se-evidence"><summary>How this direction is determined</summary><p>Current policy uses league-relative playoff and regular-season first-place odds. Contender maps to Win now; Competitive to Balanced; Developing to 3-Year; Rebuilding to Career. The classification is provisional. Championship odds are shown separately.</p><p>Balanced compares Current, 3-Year and Career without blending them into a score. Known losses remain visible. You can select a different direction; owner preferences and willingness are not confirmed.</p></details><button type="button" class="text-button se-different" data-se-different>Explore different options</button></section>`;
  }
  function refinements(){
    const others=(view.browser?.counterparties||[]).filter(t=>!view.partner||t.team_id===view.partner);
    const assets=others.flatMap(t=>(t.assets||[]).filter(a=>a.asset_kind==='pick'?view.picks||!view.young&&!view.position:(!view.picks||view.young)&&(!view.position||a.detail===view.position)&&(!view.young||finite(a.age_years)&&a.age_years>=0&&a.age_years<27)).map(a=>({...a,team:t.display_name})));
    const positions=[...new Set((view.browser?.counterparties||[]).flatMap(t=>(t.assets||[]).filter(a=>a.asset_kind==='player').map(a=>a.detail)).filter(Boolean))].sort();
    return `<details class="se-refine"${view.expanded?' open':''}><summary><span><b>Refine your search</b><small>Target or offer an asset, protect players, or choose a partner.</small></span><span aria-hidden="true">＋</span></summary><div class="se-refine-fields"><fieldset class="se-protect"><legend>Look for · combine with any priorities</legend><label><input type="checkbox" data-se-young${view.young?' checked':''}><span>Players age 26 &amp; under</span></label><label><input type="checkbox" data-se-picks${view.picks?' checked':''}><span>Draft picks</span></label></fieldset>${view.browserError?`<p role="alert">${esc(view.browserError)}</p>`:''}<label class="se-field"><span>Player position</span><select data-se-position${!view.browser?' disabled':''}>${option('','Any position',view.position)}${positions.map(p=>option(p,p,view.position)).join('')}</select></label><label class="se-field"><span>Trade partner</span><select data-se-partner${!view.browser?' disabled':''}>${option('','Across the league',view.partner)}${(view.browser?.counterparties||[]).map(t=>option(t.team_id,t.display_name,view.partner)).join('')}</select></label><label class="se-field"><span>Target an asset</span><select data-se-target${!view.browser?' disabled':''}>${option('','No specific target',view.target)}${assets.map(a=>option(a.asset_ref,a.label+' · '+a.team,view.target)).join('')}</select></label><label class="se-field"><span>Offer / shop an asset</span><select data-se-offer${!view.browser?' disabled':''}>${option('','No required outgoing asset',view.offer)}${(view.browser?.focal_team?.assets||[]).map(a=>option(a.asset_ref,a.label,view.offer)).join('')}</select></label><fieldset class="se-protect"><legend>Keep these players</legend><p>Protected players cannot be sent or included in required cuts.</p>${(view.browser?.focal_team?.assets||[]).filter(a=>a.player_id).map(a=>`<label><input type="checkbox" data-se-protect="${esc(a.player_id)}"${view.protected.includes(a.player_id)?' checked':''}><span>${esc(a.label)}</span></label>`).join('')}</fieldset></div></details>`;
  }
  function metric(value){return `<td class="${finite(value)?(value>0?'se-gain':value<0?'se-loss':''):''}">${finite(value)?esc(signed(value)):'<span title="Evidence unavailable">—</span>'}</td>`;}
  function sideData(row,label){
    const assessment=row.objective_assessment?.[label],current=row.preliminary_decision_screen;
    const screened=row.evidence_status==='pre_simulation_screened';
    const points=screened?current?.[label==='side_a'?'focal':'counterparty']?.starter_points_delta:null;
    const native=h=>{const a=row.horizon_asset_economics?.[h]?.roster_adjusted?.[label];return a?.status==='complete'?a.roster_adjusted_intrinsic_delta:null;};
    const market=row.roster_adjusted_market_net?.[label];
    const marketDelta=screened&&market?.status==='complete'?market.roster_adjusted_market_delta:null;
    const team=assessment?.context?.team_id||(label==='side_a'?view.result?.focal_team_id:row.counterparty_team_id);
    const positions=screened?(row.position_strength_comparisons?.[team]?.positions||[]):[];
    const gains=positions.filter(p=>finite(p.expected_points_delta)&&p.expected_points_delta>0).map(p=>p.position);
    const losses=positions.filter(p=>finite(p.expected_points_delta)&&p.expected_points_delta<0).map(p=>p.position);
    const facts=[];
    if(gains.length)facts.push('Stronger '+gains.join(' / ')+' lineup');
    if(losses.length)facts.push('less '+losses.join(' / ')+' lineup production');
    if(!facts.length&&finite(points)&&points!==0)facts.push(points>0?'More projected lineup points':'Fewer projected lineup points');
    for(const [h,name] of [['three_year','3-Year'],['career','Career']]){
      const value=native(h);if(finite(value)&&value!==0)facts.push((value>0?'adds ':'gives up ')+name+' contribution');
    }
    const rationale=facts.length?facts.join('; ')+'.':'';
    const competitive=view.result?.team_competitive_contexts?.[team];
    const calculated=competitive?.calculated_competitive_state||assessment?.context?.calculated_competitive_state||'unknown';
    return {teamId:team,assessment,points,three:native('three_year'),career:native('career'),market,marketDelta,rationale,calculated};
  }
  function weeklyAccounting(row,team){const p=row.current_roster_points;if(p?.basis!=='remaining_regular_season_weekly_mean')return '';const before=p.before_weekly_means?.[team],after=p.after_weekly_means?.[team],total=p.remaining_totals?.[team],weeks=p.weeks_by_team?.[team]||[],details=p.weekly_details?.[team]||[];if(!finite(before)||!finite(after)||!weeks.length)return '';return `<p>Current lineup: <b>${before.toFixed(1)} → ${after.toFixed(1)}</b> pts / week across ${weeks.length} remaining regular-season week${weeks.length===1?'':'s'}${finite(total)?` · ${esc(signed(total))} total points`:''}.</p>${details.length?`<details><summary>Week-by-week lineup points</summary><ul>${details.map(w=>`<li>Week ${esc(w.week)}: ${w.before.toFixed(1)} → ${w.after.toFixed(1)} (${esc(signed(w.delta))})</li>`).join('')}</ul></details>`:''}`}
  function irPlacement(row,team){const ids=(row.roster_legality||[]).find(r=>r.team_id===team)?.ir_placements||[];const assets=[...(row.send||[]),...(row.receive||[])];return ids.length?`<p>Move ${ids.map(id=>esc(assets.find(a=>a.asset_ref==='player:'+id)?.label||id)).join(', ')} to the available IR ${ids.length===1?'spot':'spots'}.</p>`:'';}
  function impact(row,name){
    const sides=[['side_a','You'],['side_b',name]].map(([key,title])=>({...sideData(row,key),title}));
    const weekly=row.preliminary_decision_screen?.current_points_basis==='remaining_regular_season_weekly_mean';
    return `<div class="se-impact"><table><caption>Change after trade</caption><thead><tr><th scope="col">Franchise</th><th scope="col">Current<small>${weekly?'pts / week':'lineup pts'}</small></th><th scope="col">3-Year<small>contribution</small></th><th scope="col">Career<small>contribution</small></th></tr></thead><tbody>${sides.map(d=>`<tr><th scope="row">${esc(d.title)}</th>${metric(d.points)}${metric(d.three)}${metric(d.career)}</tr>`).join('')}</tbody></table></div>${sides.filter(d=>d.market?.required_cut_count||d.assessment?.protected_players_lost?.length).map(d=>`<p class="${d.assessment?.protected_players_lost?.length?'se-caution':'se-cut'}">${esc(d.title)}: ${d.assessment?.protected_players_lost?.length?'a protected player would be lost.':esc(d.market.required_cut_count)+' required roster cut(s).'}</p>`).join('')}<details class="se-evidence se-accounting"><summary>Team context & accounting</summary>${sides.map(d=>`<section><b>${esc(d.title)}</b><p>${esc(stateNames[d.calculated]||d.calculated)} · ${esc(priorities(d.assessment?.context))}</p>${irPlacement(row,d.teamId)}${weeklyAccounting(row,d.teamId)}${d.teamId===row.counterparty_team_id?(window.fsfflOwnerHistoryFacts?.(row.owner_history,d.teamId,view.result?.league_state_id)||[]).map((fact,index)=>`<p>${index===0?'<b>Trading history</b><br>':''}${esc(fact)}</p>`).join(''):''}${d.rationale?`<p>${esc(d.rationale[0].toUpperCase()+d.rationale.slice(1))}</p>`:''}<p>Net Market change after cuts: <b>${esc(signed(d.marketDelta,0))}</b></p></section>`).join('')}<p>3-Year and Career show raw Shapley contribution, with required cuts included. They overlap and must not be added. Current averages use each team’s own replacements, byes and required cuts. Simulation supplies competitive outcomes. A dash means evidence is unavailable.</p></details>`;
  }
  function pickSlotRange(pick){
    const ranges=pick.intrinsic_slot_ranges||{};
    if(!ranges.career||!finite(ranges.career.low)||!finite(ranges.career.high))return '';
    const value=v=>finite(v)?v.toLocaleString(undefined,{maximumFractionDigits:0}):'Unavailable';
    const line=(name,label,mean)=>ranges[name]&&finite(ranges[name].low)&&finite(ranges[name].high)?`<small>${label}: <b>${value(mean)}</b> · ${value(ranges[name].low)}–${value(ranges[name].high)} by slot</small>`:'';
    return `<details class="se-evidence"><summary>Value by draft slot</summary>${pick.outside_three_year_window?'<small>3-Year: 0 · outside the current window</small>':line('three_year','3-Year',pick.three_year_intrinsic)}${line('career','Career',pick.career_intrinsic)}<small>Raw Intrinsic contribution. Slot scenarios, not guaranteed player outcomes.</small></details>`;
  }
  function packageAssets(items){return(items||[]).map(a=>{const info=asset(a.asset_ref),pick=view.result?.pick_evidence?.[a.asset_ref];return `<div class="se-asset"><div><b>${info?.player_id?`<button type="button" class="pi-player-link" data-player-intelligence-id="${esc(info.player_id)}">${esc(a.label||info.label)}</button>`:esc(a.label||a.asset_ref)}</b><small>${esc(info?.detail||info?.asset_kind||'Asset')}</small>${pick?`<small>${pick.slot_uncertain_prior?'Slot uncertain':finite(pick.expected_slot)?'Projected slot '+pick.expected_slot.toFixed(1):'Draft slot unavailable'} · ${pick.three_year_intrinsic_status==='bounded_provisional'?'Preliminary pick estimate':'Pick Intrinsic unavailable'}</small>${pickSlotRange(pick)}`:''}</div></div>`;}).join('');}
  const hypotheses={roster_fit:'Roster construction',three_year_contribution:'3-Year contribution',career_contribution:'Career contribution',rank_disagreement_three_year_contribution:'Intrinsic / Market rank disagreement',rank_disagreement_career_contribution:'Intrinsic / Market rank disagreement',package_structure:'Package structure',feedback_repair:'Alternative package'};
  function purposeMarkup(row){
    const ps=(row.discovery_purposes||[]).filter(p=>p.source_state_id===view.result?.league_state_id);
    if(!ps.length)return '';
    const supported=ps.filter(p=>p.kind!=='observed_acquisition');
    const p=supported.find(p=>['lineup_gain','current_lineup_preserved','asset_contribution_gain'].includes(p.result))||supported[0];
    if(!p)return ''; 
    let title='Explore a different way to improve';
    if(p.kind==='improve_lineup')title=p.result==='lineup_gain'?`More ${p.position} points now`:`Looking for ${p.position} help`;
    if(p.kind==='test_depth_conversion')title='Explore trading depth for draft picks';
    if(p.kind==='acquire_future_assets')title=p.asset_focus==='picks'?'Build draft capital':'Explore younger talent';
    return `<div class="se-purpose"><b>${esc(title)}</b></div>`;
  }
  function pointAssets(point, side){
    return point[side].map(({asset:term,label})=>{
      const ref=term.kind==='player'?'player:'+term.player_id:'pick:'+term.pick_id;
      const detail=term.kind==='pick'?asset(ref)?.detail?.split(' · ')[0]:'';
      return {asset_ref:ref,label:detail?label+' ('+detail+')':label};
    });
  }
  function priceMarkup(row,index){
    if(!row.evaluation_kind||view.dirty)return '';
    const entry=view.prices.get(row.point_id);
    const choices=[['buy','Buying: compare offers',!view.offer],['sell','Selling: compare returns',!(view.target||view.position||view.young||view.picks)]];
    const buttons=choices.filter(item=>item[2]).map(([side,label])=>
      `<button type="button" class="text-button" data-se-price="${index}" data-side="${side}" ${view.priceBusy||view.busy?'disabled':''}>${label}</button>`).join(' ');
    if(!buttons)return '';
    let body='';
    if(entry?.message)body=`<p role="status">${esc(entry.message)}</p>`;
    if(entry?.result){
      const result=entry.result, plan=result.negotiating_terms;
      const describe=(id,title)=>{
        const point=result.points.find(p=>p.point_id===id);
        if(!point)return '';
        const give=pointAssets(point,'focal_assets').map(a=>a.label).join(' + ');
        const get=pointAssets(point,'counterparty_assets').map(a=>a.label).join(' + ');
        const lines=[['You',result.focal_team_id],[teamName(result.counterparty_team_id),result.counterparty_team_id]].map(([label,id])=>{
          const effect=point.counter_review.effects.teams[id],cuts=point.price_check.cuts[id];
          const unit=point.price_check.basis==='remaining_regular_season_weekly_mean'?'pts/week':'projected lineup pts';
          return `<p>${esc(label)}: ${signed(effect.current)} ${unit} · ${signed(effect.three_year)} over three years · ${signed(effect.career)} career${cuts?' · '+cuts+' required cut'+(cuts===1?'':'s'):''}.</p>`;
        }).join('');
        return `<div><strong>${title}</strong><p>Give ${esc(give)} for ${esc(get)}.</p>${lines}<button type="button" class="text-button" data-se-term="${index}" data-point="${esc(id)}">Check this offer in Trade Center →</button></div>`;
      };
      if(plan.opening){
        body=describe(plan.opening,plan.conditional_opening?'Ask if they’d consider this':entry.side==='buy'?'Open with this offer':'Start by asking for this return');
        if(plan.conditional_opening){
          const check=result.points.find(p=>p.point_id===plan.opening).price_check;
          body+=`<p>This helps ${esc(teamName(result.counterparty_team_id))} at ${esc(check.needs_filled.join(' and '))}. They would give up market value, so they have a reason to ask for more.</p>`;
        }
        if(plan.fallback){
          const opened=result.points.find(p=>p.point_id===plan.opening);
          const next=result.points.find(p=>p.point_id===plan.fallback);
          const team=result.counterparty_team_id, before=opened.counter_review.effects.teams[team], after=next.counter_review.effects.teams[team];
          const reason=after.career>before.career?'a better long-term return':after.three_year>before.three_year?'more over the next three years':after.current>before.current?'more lineup production now':'better market value';
          body+=`<p>If talks stall, the next package gives ${esc(teamName(team))} ${reason}.</p>`;
        }
        body+=plan.fallback?describe(plan.fallback,entry.side==='buy'?'If they ask for more':'If they offer less'):'<p>Keep these terms. The other checked prices give you no clear reason to concede.</p>';
        if(plan.outside){
          const outside=result.points.find(p=>p.point_id===plan.outside);
          const terms=pointAssets(outside,'counterparty_assets').map(a=>a.label).join(' + ');
          body+=`<p><b>Where to stop:</b> At ${esc(terms)}, you would give up more in market value than the price check supports. Consider keeping what you have.</p>`;
        }
        body+=plan.fallback&&!plan.outside?'<p>Beyond these terms, compare keeping what you have. Check the season impact before agreeing.</p>':'<small>Check the season impact before agreeing.</small>';
      }else if(plan.reason==='missing_publication')body='<p>A matching forecast and long-term values are needed to compare prices.</p>';
      else body='<p>No opening price established. The checked packages need better terms or stronger evidence for both teams.</p>';
    }
    return `<div class="se-negotiation">${buttons}${body}</div>`;
  }
  async function comparePrices(index,side){
    const owner=view, row=view.result?.candidate_packages[index], key=contextKey(), seq=view.sequence;
    if(!row||view.priceBusy||view.busy||view.dirty)return;
    const active=()=>view===owner&&contextKey()===key&&owner.sequence===seq&&!owner.dirty;
    const openPanels=[...host.querySelectorAll('details.se-more')].map(el=>el.open);
    const redraw=()=>{paint();host?.querySelectorAll('details.se-more').forEach((el,i)=>{el.open=Boolean(openPanels[i]);});};
    owner.priceBusy=true;owner.prices.set(row.point_id,{message:'Checking nearby prices…'});redraw();
    try{
      const result=await api('/api/trade-center/frontier',{method:'POST',body:JSON.stringify({...row.trade_center_request,price_side:side})});
      if(!active())return;
      if(result.state_id_before!==view.result.league_state_id||result.publication_generation_id!==view.result.publication_generation_id||result.focal_team_id!==view.result.focal_team_id||result.counterparty_team_id!==row.counterparty_team_id)throw Error('The league changed. Run the search again.');
      owner.prices.set(row.point_id,{side,result});
    }catch(error){if(active())owner.prices.set(row.point_id,{message:error.message||'Please retry the price check.'});}
    finally{owner.priceBusy=false;if(view===owner&&visibleHost())redraw();}
  }
  function card(row,rows){
    const index=rows.indexOf(row);
    const name=teamName(row.counterparty_team_id);
    const lineages=row.repair_lineages||[];
    const related=rows.filter(other=>other.point_id!==row.point_id&&((row.shortlist_quality?.alternative_point_ids||[]).includes(other.point_id)||(row.linked_prior_point_ids||[]).includes(other.point_id)||lineages.some(l=>l.root_point_id===other.point_id||l.parent_point_id===other.point_id)||(other.repair_lineages||[]).some(l=>l.root_point_id===row.point_id||l.parent_point_id===row.point_id)));
    const blocked=['side_a','side_b'].some(s=>row.objective_assessment?.[s]?.protected_players_lost?.length);
    return `<article class="se-card" data-se-group="${esc(row.display_context?.group||'needs_evidence')}"><header><div class="se-row"><span class="eyebrow">${row.display_context?.group==='priority_tradeoff'?'Tradeoff':'Preliminary'}</span><small>${esc(name)}</small></div><h2>${row.receive?.length===1?'Explore '+esc(row.receive[0].label||row.receive[0].asset_ref):esc(row.send?.length||0)+' for '+esc(row.receive?.length||0)+' package'}</h2></header><div class="se-card-body"><div class="se-package-grid"><section><p class="eyebrow">You receive · ${esc(row.receive?.length||0)}</p>${packageAssets(row.receive)}</section><section><p class="eyebrow">You send · ${esc(row.send?.length||0)}</p>${packageAssets(row.send)}</section></div>${choiceSummary(row,name)}${purposeMarkup(row)}${priceMarkup(row,index)}${impact(row,name)}${related.length?`<details class="se-alternatives"><summary>Compare linked package alternatives</summary>${related.map(other=>`<div><b>You give:</b> ${esc((other.send||[]).map(a=>a.label).join(' + '))}<br><b>You get:</b> ${esc((other.receive||[]).map(a=>a.label).join(' + '))}<p>${esc(other.evidence_status==='pre_simulation_screened'?'Preliminary effects are shown in its own card.':'Effects are incomplete; no benefit is assumed.')}</p><button type="button" class="text-button" data-se-compare="${rows.indexOf(other)}">View this alternative</button></div>`).join('')}</details>`:''}<button type="button" class="primary-button se-evaluate" data-se-evaluate="${index}"${blocked?' disabled':''}>Evaluate in Trade Center →</button></div></article>`;
  }
  function choiceSummary(row,name){
    if(row.evidence_status!=='pre_simulation_screened')return '';
    const proof=row.screen_confirmation;
    if(proof?.status==='not_worthwhile'){
      const names=(proof.limiting_team_ids||[]).map(id=>id===row.focal_team_id?'your team':teamName(id));
      return `<p class="se-choice-summary">The season check found no clear competitive gain for ${esc(names.join(' or ')||'both teams')}.</p>`;
    }
    const sentence=(side,label)=>{
      const current=row.preliminary_decision_screen?.[side==='side_a'?'focal':'counterparty']?.starter_points_delta;
      const future=['three_year','career'].map(h=>row.horizon_asset_economics?.[h]?.roster_adjusted?.[side]?.roster_adjusted_intrinsic_delta);
      const weekly=row.preliminary_decision_screen?.current_points_basis==='remaining_regular_season_weekly_mean';
      let now=!Number.isFinite(current)?'Current lineup estimate unavailable':Math.abs(current)<.05?'Little change to the lineup':`${current>0?'Adds':'Gives up'} about ${Math.abs(current).toFixed(1)} ${weekly?'points a week':'total points over the projection period'}`;
      const checked=proof?.material?.[side],change=checked&&proof?.competitive?.[checked.team_id];
      if(change){
        for(const [metric,title] of [['championship_probability','title chances'],['playoff_probability','playoff chances'],['expected_wins','expected wins']]){
          if(!Number.isFinite(change[metric])||(metric!=='championship_probability'&&!['material_gain','material_loss'].includes(checked[metric])))continue;
          const delta=change[metric],amount=metric==='expected_wins'?Math.abs(delta).toFixed(2):Math.abs(delta*100).toFixed(1);
          now=`${title[0].toUpperCase()+title.slice(1)} ${delta>0?'rise':'fall'} by ${amount}${metric==='expected_wins'?'':' percentage points'}`;break;
        }
      }
      if(!Number.isFinite(change?.championship_probability)&&proof?.roster_supported_future_team_ids?.includes(checked?.team_id))now='Trades bench depth while keeping the current outlook steady';
      const later=!future.every(Number.isFinite)?future.map((v,i)=>Number.isFinite(v)?`${i===0?'Three-year':'Career'} contribution ${v>=0?'rises':'falls'}.`:`${i===0?'Three-year':'Career'} estimate unavailable.`).join(' '):future.every(v=>v>=-1e-9)&&future.some(v=>v>1e-9)?'More long-term upside.':future.every(v=>v<=1e-9)&&future.some(v=>v < -1e-9)?'The price is less future upside.':future.every(v=>Math.abs(v)<=1e-9)?'No projected change to future production.':future[0]>0?'More help over the next few seasons, with a longer-term cost.':'More long-term upside, less help over the next few seasons.';
      const risk=checked?.largest_single_player_lineup_drop==='material_loss'?' Less cover if a starter is lost.':'';
      return `<p><b>${esc(label)}:</b> ${esc(now)}. ${esc(later)}${esc(risk)}</p>`;
    };
    const comparison=row.shortlist_quality?.reason==='better_focal_alternative'&&row.shortlist_quality?.comparison_basis==='confirmed'?'<p>Another evaluated offer gives you comparable or better results with less sacrifice.</p>':'';
    return `<div class="se-choice-summary">${sentence('side_a','You')}${sentence('side_b',name)}${comparison}</div>`;
  }
  function emptyResult(){
    const pending=view.result?.search_progress?.pending_confirmation_count;
    return `<div class="se-empty"><b>${pending?'Promising offers still need checking.':'No worthwhile matches found yet.'}</b><p>${pending?'Continue the search, or open an offer below in Trade Center.':'Find more, or choose the priority you want to pursue.'}</p></div>`;
  }
  function results(){
    if(view.dirty)return '<div class="se-empty" role="status"><b>Your search has changed.</b><p>Run discovery to see opportunities for these settings.</p></div>';
    if(view.busy&&!view.result)return '<div class="se-empty" role="status"><b>Looking for complementary interests…</b><p>Comparing bounded packages and both teams’ tradeoffs.</p></div>';
    if(view.error&&!view.result)return `<div class="se-empty" role="alert"><b>Discovery couldn’t complete.</b><p>${esc(view.error)}</p><p>Your settings are preserved. Try again when intelligence work is available.</p></div>`;
    if(!view.result)return '';
    const rows=view.result.candidate_packages||[];
    const fits=rows.filter(r=>['shortlist','strategic_tradeoff'].includes(r.shortlist_quality?.status)||(!r.shortlist_quality&&r.display_context?.group==='preliminary_fit')).sort((a,b)=>(a.shortlist_quality?.rank??999)-(b.shortlist_quality?.rank??999)); 
    const tradeoffs=rows.filter(r=>r.display_context?.group==='priority_tradeoff'&&r.shortlist_quality?.status!=='strategic_tradeoff'&&r.shortlist_quality?.status!=='alternative');
    const concerns=rows.filter(r=>r.display_context?.group==='priority_concern');
    const others=rows.filter(r=>r.shortlist_quality?.status==='alternative'||(r.shortlist_quality?.status==='review'&&!['priority_tradeoff','priority_concern'].includes(r.display_context?.group))||!['preliminary_fit','priority_tradeoff','priority_concern','depth_conversion_hypothesis'].includes(r.display_context?.group));
    return `${progressMarkup()}<section class="se-results"><p class="eyebrow">Opportunities to investigate</p><h2>See the upside. Know the cost.</h2>${fits.length?fits.slice(0,4).map(r=>card(r,rows)).join(''):emptyResult()}${fits.length>4?`<details class="se-more"><summary>${fits.length-4} more directions to explore</summary>${fits.slice(4).map(r=>card(r,rows)).join('')}</details>`:''}${tradeoffs.length?`<details class="se-more" data-se-tradeoffs><summary>${tradeoffs.length} ${tradeoffs.length===1?'tradeoff':'tradeoffs'} needing a closer look</summary>${tradeoffs.map(r=>card(r,rows)).join('')}</details>`:''}${concerns.length?`<details class="se-more" data-se-concerns><summary>${concerns.length} packages needing better terms</summary>${concerns.map(r=>card(r,rows)).join('')}</details>`:''}${others.length?`<details class="se-more"><summary>${others.length} additional candidates to review</summary>${others.map(r=>card(r,rows)).join('')}</details>`:''}<details class="se-evidence"><summary>Search coverage</summary><p>Up to 80 packages per search, checked in batches. Find More continues the same search. Player and pick packages are included, with up to 10 assets combined. Package adjustments can include players and draft picks.</p><p>Fits follow the selected priorities; tradeoffs show the costs. The strongest Current cases get a season check. Trade Center shows the full analysis.</p></details></section>`;
  }

  function paint(){
    if(!visibleHost())return;
    host.innerHTML=`<div class="strategic-explore">${direction()}${refinements()}<button type="button" class="primary-button se-search" data-se-run${view.busy?' disabled':''}>${view.busy?'Discovering…':'Find opportunities'}</button>${results()}</div>`;
    wire();
  }
  function changed(){view.prices.clear();view.expanded=host?.querySelector('.se-refine')?.open??view.expanded;view.sequence+=1;view.dirty=true;paint();}
  function wire(){
    host.querySelectorAll('[data-se-price]').forEach(b=>b.onclick=()=>comparePrices(Number(b.dataset.sePrice),b.dataset.side));
    host.querySelectorAll('[data-se-term]').forEach(b=>b.onclick=()=>{
      if(view.dirty||view.key!==contextKey())return;
      const row=view.result.candidate_packages[Number(b.dataset.seTerm)];
      const point=view.prices.get(row.point_id)?.result?.points.find(p=>p.point_id===b.dataset.point);
      if(point)window.fsfflOpenOpportunityInTradeCenter?.({send:pointAssets(point,'focal_assets'),receive:pointAssets(point,'counterparty_assets'),
        counterparty_team_id:row.counterparty_team_id,counterparty_name:teamName(row.counterparty_team_id),
        league_state_id:view.result.league_state_id,publication_generation_id:view.result.publication_generation_id,
        negotiation_note:point.point_id===view.prices.get(row.point_id).result.negotiating_terms.opening
          ?(view.prices.get(row.point_id).result.negotiating_terms.conditional_opening?'Possible opener. Your partner would be giving up market value.':'Opening terms from Explore.')
          :'Fallback terms from Explore.',
        trade_center_request:{search_instructions:row.trade_center_request.search_instructions}});
    });
    host.querySelectorAll('[data-se-mode]').forEach(b=>b.addEventListener('click',()=>{if(view.mode===b.dataset.seMode)return;view.mode=b.dataset.seMode;changed();}));
    host.querySelectorAll('[data-se-priority]').forEach(b=>b.addEventListener('change',()=>{const set=new Set(view.goals);b.checked?set.add(b.dataset.sePriority):set.delete(b.dataset.sePriority);view.goals=ALL.filter(g=>set.has(g));changed();}));
    for(const name of ['young','picks'])host.querySelector('[data-se-'+name+']')?.addEventListener('change',e=>{view[name]=e.target.checked;view.target='';changed();});
    host.querySelector('.se-refine')?.addEventListener('toggle',e=>{if(e.target.isConnected)view.expanded=e.target.open;});
    for(const name of ['position','partner','target','offer'])host.querySelector('[data-se-'+name+']')?.addEventListener('change',e=>{view[name]=e.target.value;if(['position','partner'].includes(name))view.target='';changed();});
    host.querySelectorAll('[data-se-protect]').forEach(b=>b.addEventListener('change',()=>{const set=new Set(view.protected);b.checked?set.add(b.dataset.seProtect):set.delete(b.dataset.seProtect);view.protected=[...set];changed();}));
    host.querySelector('[data-se-run]')?.addEventListener('click',()=>run());
    host.querySelector('[data-se-more]')?.addEventListener('click',()=>run({continueSearch:true}));
    host.querySelector('[data-se-different]')?.addEventListener('click',()=>{view.expanded=true;paint();host.querySelector('.se-direction')?.scrollIntoView?.({behavior:'smooth',block:'start'});});
    host.querySelector('[data-se-pause]')?.addEventListener('click',()=>{view.pauseRequested=true;paint();});
    host.querySelectorAll('[data-se-evaluate]').forEach(b=>b.addEventListener('click',async()=>{
      if(view.dirty||view.key!==contextKey())return;
      const row=view.result?.candidate_packages?.[Number(b.dataset.seEvaluate)];
      const captured=view;view.pauseRequested=true;
      if(view.pendingBatch){try{await view.pendingBatch}catch(_){}}
      if(view!==captured||view.dirty||view.key!==contextKey())return;
      if(row)window.fsfflOpenOpportunityInTradeCenter?.({...row,league_state_id:view.result.league_state_id,publication_generation_id:view.result.publication_generation_id,counterparty_name:teamName(row.counterparty_team_id)});
    }));
    host.querySelectorAll('[data-se-compare]').forEach(b=>b.addEventListener('click',()=>{
      const i=b.dataset.seCompare,target=host.querySelector('[data-se-evaluate="'+i+'"]')?.closest('.se-card');
      if(target){let parent=target.parentElement;while(parent&&parent!==host){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}target.scrollIntoView({behavior:'smooth',block:'start'});}
    }));
  }
  function progressMarkup(){
    const p=view.result?.search_progress;
    if(!p)return '';
    const stop={confirmations_pending:'Checking the remaining promising offers.',confirmation_incomplete:'Some promising offers still need a full check. Open them in Trade Center.',shortlist_ready:'',screening_limit:'Search limit reached. Change direction to explore other packages.',pool_exhausted:'No more packages for this search.',screening_disabled:''};
    return `<div class="se-progress" role="status"><b>${p.total_screened} packages screened · ${p.shortlisted_choice_count??p.preliminary_fit_count} ${(p.shortlisted_choice_count??p.preliminary_fit_count)===1?'option':'options'}${Number.isInteger(p.priority_tradeoff_count)?` · ${p.priority_tradeoff_count} ${p.priority_tradeoff_count===1?'tradeoff':'tradeoffs'}`:''}</b>${view.busy?`<p>${view.pauseRequested?'Finishing this batch…':'Finding opportunities…'}</p>`:stop[p.stop_reason]?`<p>${esc(stop[p.stop_reason])}</p>`:''}${view.error?`<p role="alert">${esc(view.error)} Completed results are preserved.</p>`:''}<div class="se-search-actions">${view.busy?'<button type="button" class="text-button" data-se-pause>Pause</button>':p.next_token?`<button type="button" class="secondary-button" data-se-more>${p.stop_reason==='confirmations_pending'?'Finish checking':'Find More'}</button>`:''}</div></div>`;
  }
  function mergeBatch(previous,result){
    if(!previous)return result;
    const merged=new Map((previous.candidate_packages||[]).map(r=>[r.point_id,r]));
    for(const row of result.candidate_packages||[]){
      const old=merged.get(row.point_id);
      if(!old||!old.evaluation_kind||row.evaluation_kind)merged.set(row.point_id,row);
    }
    for(const [id,proof] of Object.entries(result.confirmation_updates||{})){const row=merged.get(id);if(row)merged.set(id,{...row,screen_confirmation:proof});}
    for(const [id,quality] of Object.entries(result.shortlist_updates||{})){const row=merged.get(id);if(row)merged.set(id,{...row,shortlist_quality:quality});}
    const all=[...merged.values()],evaluated=all.filter(r=>r.evaluation_kind);
    return {...previous,...result,pick_evidence:{...(previous.pick_evidence||{}),...(result.pick_evidence||{})},candidate_packages:[...evaluated,...all.filter(r=>!r.evaluation_kind)].slice(0,80)};
  }
  async function run({continueSearch=false}={}){
    reconcile();if(view.inFlight||!ctx().team_id||!ctx().state_id)return;
    if(continueSearch&&view.dirty)return;
    if(!view.browser)void loadBrowser();
    let body;try{body=requestBody();}catch(error){view.error=error.message;view.result=null;view.dirty=false;paint();return;}
    const current=view,key=view.key,id=++view.sequence;
    const active=()=>view===current&&contextKey()===key&&id===view.sequence&&state.route==='opportunities'&&['for_you','trade_finder'].includes(window.fsfflMarketNorthStar?.activeTab?.());
    let token=continueSearch?view.result?.search_progress?.next_token:null;
    if(continueSearch&&!token)return;
    if(!continueSearch){view.result=null;view.prices.clear();}
    view.started=true;view.busy=true;view.inFlight=true;view.pauseRequested=false;view.error='';view.dirty=false;paint();
    // Sequential bounded batches; finalist checks share the existing Trade Center evaluator.
    try{
      for(let batch=0;batch<4;batch++){
        view.pendingBatch=api('/api/opportunities/strategic-discover',{method:'POST',body:JSON.stringify({...body,...(token?{continuation_token:token}:{})})});
        const result=await view.pendingBatch;view.pendingBatch=null;
        if(!active())return;
        const generation=ctx().capability_readiness?.publication?.generation_id||ctx().publication_generation_id;
        if(result.league_state_id!==ctx().state_id||result.focal_team_id!==ctx().team_id||(generation&&result.publication_generation_id!==generation))throw new Error('League intelligence changed. Reload Explore for current evidence.');
        view.result=mergeBatch(view.result,result);paint();
        const progress=result.search_progress;
        token=progress?.next_token;
        if(view.pauseRequested||!token||!['continue','confirmations_pending'].includes(progress.stop_reason))break;
      }
    }catch(error){if(active())view.error=error?.message||'Please retry discovery.';}
    finally{if(view===current&&contextKey()===key){view.inFlight=false;view.pendingBatch=null;view.busy=false;paint();}}
  }
  async function loadBrowser(){
    if(view.browser||view.browserLoading)return;
    view.browserLoading=true;
    const current=view,key=view.key;
    try{const browser=await api('/api/trade-center/browser');if(view!==current||key!==contextKey())return;if(browser.state_id!==ctx().state_id||browser.focal_team?.team_id!==ctx().team_id)throw new Error('League ownership changed. Reload Explore.');view.browser=browser;}
    catch(error){if(view===current&&key===contextKey())view.browserError=error?.message||'Search controls are unavailable.';}
    if(view===current){view.browserLoading=false;paint();}
  }
  function applyIntent(intent,value){
    reconcile();
    view.offer='';view.target='';view.position='';view.partner='';view.young=false;view.picks=false;
    if(intent==='shop')view.offer=value||'';
    if(intent==='target')view.target=value||'';
    if(intent==='position')view.position=value||'';
    if(intent==='owner')view.partner=value||'';
    view.sequence+=1;view.dirty=true;view.expanded=true;
  }
  function render(body,payload,{directed=false}={}){
    reconcile();host=body;
    if(directed&&!view.directed)view.expanded=true;
    view.directed=directed;
    if(!ctx().league_id||!ctx().team_id||!ctx().state_id){host.innerHTML='<div class="se-empty"><b>Connect a league and choose your franchise to discover trades.</b></div>';return;}
    paint();if(!view.started){void loadBrowser();if(!directed&&!view.dirty)void run();}
  }
  window.fsfflStrategicExplore={render,run,priorities,applyIntent};
  window.addEventListener('fsffl:product-context-updated',()=>{reconcile();});
})();
