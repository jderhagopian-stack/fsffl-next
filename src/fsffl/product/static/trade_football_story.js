/* Explain existing football evidence. No scoring, recommendation or owner-intent inference. */
(function(){
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  const join=items=>items.length>1?items.slice(0,-1).join(', ')+' and '+items.at(-1):items[0]||'';
  window.fsfflOwnerHistoryFacts=function(history,teamId,stateId,focal=false){
    const row=history?.[teamId];
    if(!row||row.source_state_id!==stateId)return [];
    if(row.status==='unavailable')return ['Unavailable for this league snapshot.'];
    if(row.status==='no_completed_trades')return ['No completed trades are recorded for this owner.'];
    if(row.status!=='observed')return [];
    const precedents=(row.contextual_precedents||[]).slice(0,1).map(p=>{
      const d=new Date(p.completed_at);if(Number.isNaN(d.getTime()))return null;
      const when=d.toLocaleDateString(undefined,{month:'long',year:'numeric'});
      const subject=p.attribution_basis==='current_franchise_activity'?(focal?'your franchise':'this franchise'):(focal?'you':'they');let text=`In ${when}, ${subject} traded ${p.sent_summary} for ${p.received_summary}.`;
      const r=p.record_context;
      if(r){const record=`${r.wins}–${r.losses}${r.ties?`–${r.ties}`:''}`;
        if(r.regular_season_complete)text+=` ${focal?'You':'They'} had finished the ${r.season} regular season ${record}.`;
        else if(r.season===p.football_season&&p.trade_phase==='regular_season')text+=` ${focal?'Your':'Their'} record was ${record} at the time.`;
      }
      return text;
    }).filter(Boolean);
    // Package-specific observations come before generic shape. Counts of players
    // must not be described as counts of trades or inferred owner preferences.
    if(row.observations_version==='package-observations-v1'&&Array.isArray(row.observations)){
      const subject=focal?'You':'They',possessive=focal?'your':'their',recipient=focal?'you':'them';
      const positive=n=>Number.isInteger(n)&&n>0;
      const positions={QB:['quarterback','quarterbacks'],RB:['running back','running backs'],WR:['receiver','receivers'],TE:['tight end','tight ends']};
      const facts=row.observations.map(o=>{
        if(!positive(o.count))return null;
        const deals=positive(o.trade_count)&&o.count<=o.trade_count?`${o.count} of ${o.trade_count} completed trades`:null;
        if(o.kind==='acquire_picks'&&deals)return `${subject} have traded for draft picks in ${deals}. This offer brings ${recipient} more picks.`;
        if(o.kind==='send_picks'&&deals)return `${subject} have given up draft picks in ${deals}. This offer uses ${possessive} picks to bring back help.`;
        if(o.kind==='acquire_position'&&positions[o.position])return `${subject} have traded for ${o.count} ${positions[o.position][o.count===1?0:1]}. This offer brings ${recipient} another ${positions[o.position][0]}.`;
        if(o.kind==='counterparty')return `${focal?'You two':'These owners'} have completed ${o.count} ${o.count===1?'trade':'trades'} together.`;
        if(o.kind==='package_shape'&&deals){
          const shape={consolidation:'sending several assets for fewer in return',diversification:'receiving more assets than '+(focal?'you send':'they send'),balanced:'exchanging the same number of assets'}[o.shape];
          return shape?`${subject} have made ${deals} by ${shape}, as ${focal?'you would':'they would'} here.`:null;
        }
        return null;
      }).filter(Boolean);
      if(facts.length||precedents.length)return [...precedents,...facts].slice(0,3);
    }
    const facts=row.facts?.length?row.facts:[`${row.completed_trade_count} completed trades recorded.`];
    return [...precedents,...facts.slice(0,3).map(fact=>focal?fact.replaceAll('They ','You ').replaceAll('their ','your ').replaceAll('they would','you would').replaceAll('them','you'):fact)].slice(0,3);
  };
  window.fsfflTradeFootballStory=function(result,teamId,playerName=()=>null){
    const focal=teamId===result?.focal_team_id,subject=focal?'You':'They',possessive=focal?'your':'their';
    const assessment=[result?.objective_assessment?.side_a,result?.objective_assessment?.side_b].find(s=>s?.context?.team_id===teamId);
    const strategy=assessment?.transaction_strategy||{},context=assessment?.context||{};
    const position=(result?.positional_context||[]).find(p=>p.team_id===teamId&&p.status==='complete'&&p.source_state_id===result.state_id_before&&p.after_state_id===result.state_id_after);
    const rows=position?.positions||[],summary=[],details=[];
    const names=ids=>join((ids||[]).map(id=>playerName(id)).filter(Boolean));
    const plural=ids=>(ids||[]).filter(id=>playerName(id)).length>1;
    const gains=rows.filter(r=>finite(r.expected_points_delta)&&r.expected_points_delta>0),losses=rows.filter(r=>finite(r.expected_points_delta)&&r.expected_points_delta<0);
    const positions=rs=>join(rs.map(r=>r.position));
    let headline='';
    if(gains.length&&losses.length)headline=`Stronger at ${positions(gains)}, weaker at ${positions(losses)}`;
    else if(gains.length)headline=`More help at ${positions(gains)}`;
    else if(position&&strategy.depth_conversion_candidate)headline='Trade depth for the future';
    for(const r of gains){
      const incomingIds=(r.incoming_player_ids||[]).filter(id=>(r.after_starter_ids||[]).includes(id)),incoming=names(incomingIds);
      const strength=r.baseline_league_strength;
      const weakness=strength?.team_id===teamId&&strength.position===r.position&&finite(strength.strength_index)&&strength.strength_index<100;
      summary.push(incoming?`${incoming} ${plural(incomingIds)?'strengthen':'strengthens'} ${possessive} ${r.position} lineup${weakness?', which was below the league average':''}.`:`${subject} get more production at ${r.position}${weakness?', an existing weakness':''}.`);
    }
    for(const r of losses){const outgoing=names(r.outgoing_starter_ids);
      summary.push(outgoing?`Losing ${outgoing} leaves ${possessive} ${r.position} lineup weaker.`:`${subject} give up projected production at ${r.position}.`);
    }
    // Marginal replacement is a change of starting players, not WR1/WR2 slot order.
    if(position){
      const changes=position.lineup_changes;
      const entering=changes?.entering||[],leaving=changes?.leaving||[];
      for(const entry of entering){const name=playerName(entry.player_id);if(!name)continue;
        details.push(entry.origin==='bench'?`${name} comes off ${possessive} bench to start at ${entry.slot}.`:
          `${name} enters ${possessive} starting lineup at ${entry.slot}.`);
      }
      if(entering.length&&leaving.length){const departing=names(leaving.map(p=>p.player_id));
        if(departing)details.push(`${departing} ${leaving.filter(p=>playerName(p.player_id)).length>1?'leave':'leaves'} ${possessive} starting lineup.`);
      }
      for(const mix of changes?.flex_mix||[]){
        const label=counts=>join(Object.entries(counts).map(([p,n])=>n===1?({QB:'a QB',RB:'an RB',WR:'a WR',TE:'a TE'}[p]||p):`${n} ${p}s`))||'an unfilled spot';
        details.push(`${focal?'Your':'Their'} ${mix.slot} mix changes from ${label(mix.before)} to ${label(mix.after)}.`);
      }
      if(!changes){
        // Older results can prove set membership but not exact slot chains.
        const enteringNames=names(position.entering_lineup_ids);
        if(enteringNames)details.push(`${enteringNames} ${plural(position.entering_lineup_ids)?'enter':'enters'} ${possessive} starting lineup.`);
      }
      if(position.after_unfilled_slots>position.before_unfilled_slots)
        details.push(`${focal?'Your':'Their'} projected lineup has ${position.after_unfilled_slots-position.before_unfilled_slots} more unfilled starting spot${position.after_unfilled_slots-position.before_unfilled_slots===1?'':'s'}.`);
    }
    if(position)for(const r of rows){
      const bench=names(r.outgoing_bench_ids);
      if(bench)details.push(`${bench} ${plural(r.outgoing_bench_ids)?'were':'was'} outside ${possessive} projected starting lineup. ${strategy.depth_conversion_candidate?'This lets '+(focal?'you':'them')+' move depth toward the future.':'That is still depth '+(focal?'you':'they')+' would be giving up.'}`);
      const benchIncoming=(r.incoming_player_ids||[]).filter(id=>(r.after_forecasted_bench_ids||[]).includes(id)),incoming=names(benchIncoming);
      if(incoming)details.push(`${incoming} ${plural(benchIncoming)?'add':'adds'} ${r.position} depth rather than stepping into ${possessive} projected starting lineup.`);
    }
    const competitive=(result?.team_deltas||[]).find(t=>t.team_id===teamId)?.competitive||{};
    const confirmed=result?.scenario_computation?.authoritative===true&&result?.availability?.competitive_outcomes===true;
    if(confirmed&&finite(competitive.playoff_probability)){
      const change=competitive.playoff_probability*100,shown=Math.abs(change).toFixed(1);
      if(Number(shown)>0)summary.push(`The trade ${change>0?'raises':'lowers'} ${possessive} playoff chances by ${shown} percentage points.`);
      else details.push(`The change in ${possessive} playoff chances rounds to zero at the precision shown.`);
    }
    const horizon=name=>{const evidence=result?.horizon_asset_economics;if(evidence?.source?.league_state_id!==result.state_id_before)return null;const h=evidence?.[name];const side=[h?.roster_adjusted?.side_a,h?.roster_adjusted?.side_b].find(s=>s?.team_id===teamId);return side?.status==='complete'&&finite(side.roster_adjusted_intrinsic_delta)?side.roster_adjusted_intrinsic_delta:null};
    const three=horizon('three_year'),career=horizon('career');
    if(career!==null&&career<0)summary.push(`The longer-term cost: ${focal?'you’re':'they’re'} giving up more value than ${focal?'you get':'they get'} back over the players’ careers.`);
    else if(career!==null&&career>0)summary.push(three!==null&&three<0?`${subject} gain value further down the road, but give up value over the next three seasons.`:`${subject} come away with more value for the long run.`);
    else if(three!==null&&three<0)summary.push(`${subject} give up value over the next three seasons.`);
    else if(three!==null&&three>0)summary.push(`${subject} gain value over the next three seasons.`);
    const states={contender:`${focal?'You’re':'They’re'} a contender based on the current season outlook.`,competitive:`${focal?'You’re':'They’re'} competitive in the current season outlook.`,developing:`The current season outlook puts ${focal?'your':'their'} team in the developing group.`,rebuilding:`The current season outlook points toward a rebuild for ${focal?'your':'their'} team.`};
    if(states[context.calculated_competitive_state])details.unshift(states[context.calculated_competitive_state]);
    const goals={current_competitiveness:'win this season',three_year_contribution:'build over the next three years',career_contribution:'build for the long term',resilience:'strengthen backup cover',market_capital:'build market value'};
    if(context.explicitly_directed&&context.objectives?.length)details.unshift(`${subject} ${focal?'asked':'chose'} to ${join(context.objectives.map(g=>goals[g]).filter(Boolean))}.`);
    if(position&&strategy.resilience_worsens)details.push(`This leaves ${focal?'you':'them'} more exposed if a starter is lost.`);
    if(position&&position.received_pick_ids?.length)details.push(`${subject} also receive ${position.received_pick_ids.length===1?'a draft pick':position.received_pick_ids.length+' draft picks'} for the future.`);
    const cut=(result?.roster_legality||[]).find(r=>r.team_id===teamId),cuts=names((cut?.cuts||[]).map(c=>c.player_id));
    if(cuts)details.push(`Completing the trade also means cutting ${cuts}.`);
    const history=window.fsfflOwnerHistoryFacts(result?.owner_history,teamId,result?.state_id_before,focal);
    if(history.length)details.push('Trading history: '+history.join(' '));
    return {headline,summary:summary.join(' '),details,hasRosterEvidence:Boolean(position)};
  };
})();
