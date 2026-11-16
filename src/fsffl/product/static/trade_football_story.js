/* Explain existing football evidence. No scoring, recommendation or owner-intent inference. */
(function(){
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  const join=items=>items.length>1?items.slice(0,-1).join(', ')+' and '+items.at(-1):items[0]||'';
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
    // Actual slot assignments, not a guessed positional replacement or roster-count surplus.
    if(position)for(const replacement of position.starter_replacements||[]){
      const outgoing=playerName(replacement.outgoing_player_id),incoming=playerName(replacement.replacement_player_id);
      if(outgoing&&incoming)details.push(replacement.replacement_was_already_starting?`${incoming} was already starting; the trade shifts ${incoming} into the ${replacement.slot} spot held by ${outgoing}.`:`In ${possessive} projected lineup, ${incoming} takes over the ${replacement.slot} spot held by ${outgoing}.`);
      else if(outgoing&&replacement.replacement_player_id===null)details.push(`The ${replacement.slot} spot held by ${outgoing} is left unfilled in ${possessive} projected lineup.`);
    }
    if(position)for(const r of rows){
      const promotedIds=(r.after_starter_ids||[]).filter(id=>(r.before_forecasted_bench_ids||[]).includes(id)),promoted=names(promotedIds);
      if(promoted)details.push(`${promoted} ${plural(promotedIds)?'move':'moves'} from the bench into ${possessive} projected ${r.position} lineup.`);
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
    return {headline,summary:summary.join(' '),details,hasRosterEvidence:Boolean(position)};
  };
})();
