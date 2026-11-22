"""Football explanations consume evidence, never invent motives or a new Decision."""
import shutil,subprocess
from pathlib import Path
import pytest


def test_football_story_named_replacements_timelines_sources_and_both_perspectives():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');const c={window:{}};
vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const explain=c.window.fsfflTradeFootballStory,names=id=>({flowers:'Zay Flowers',bucky:'Bucky Irving',replacement:'Josh Downs',bench:'Young WR'}[id]||null);
const r={state_id_before:'before',state_id_after:'after',focal_team_id:'a',counterparty_team_id:'b',
 scenario_computation:{authoritative:true},availability:{competitive_outcomes:true},
 team_deltas:[{team_id:'a',competitive:{playoff_probability:.03}},{team_id:'b',competitive:{playoff_probability:0}}],
 positional_context:[{team_id:'a',status:'complete',source_state_id:'before',after_state_id:'after',positions:[
 {position:'RB',expected_points_delta:123.5,incoming_player_ids:['bucky'],after_starter_ids:['bucky'],baseline_league_strength:{team_id:'a',position:'RB',strength_index:80}},
 {position:'WR',expected_points_delta:-105.5,outgoing_starter_ids:['flowers']}],lineup_changes:{entering:[{player_id:'replacement',slot:'FLEX',origin:'bench'}],leaving:[{player_id:'flowers'}]},starter_replacements:[{slot:'WR',outgoing_player_id:'flowers',replacement_player_id:'replacement'}]},
 {team_id:'b',status:'complete',source_state_id:'before',after_state_id:'after',positions:[{position:'RB',expected_points_delta:-123.5,outgoing_starter_ids:['bucky']}]}],
 objective_assessment:{side_a:{context:{team_id:'a',calculated_competitive_state:'contender',explicitly_directed:true,objectives:['career_contribution']},transaction_strategy:{resilience_worsens:true}},side_b:{context:{team_id:'b'},transaction_strategy:{}}},
 horizon_asset_economics:{source:{league_state_id:'before'},career:{roster_adjusted:{side_a:{team_id:'a',status:'complete',roster_adjusted_intrinsic_delta:-80.7},side_b:{team_id:'b',status:'complete',roster_adjusted_intrinsic_delta:80.7}}},three_year:{roster_adjusted:{side_a:{team_id:'a',status:'complete',roster_adjusted_intrinsic_delta:1.5},side_b:{team_id:'b',status:'complete',roster_adjusted_intrinsic_delta:-1.5}}}}};
const before=JSON.stringify(r),a=explain(r,'a',names),b=explain(r,'b',names);
assert.match(a.headline,/Stronger at RB, weaker at WR/);
assert.match(a.summary,/Bucky Irving strengthens your RB lineup/);
assert.match(a.summary,/Losing Zay Flowers/);assert.match(a.summary,/3.0 percentage points/);
assert.match(a.details.join(' '),/Josh Downs comes off your bench to start at FLEX/);
assert.match(a.summary,/below the league average/);
assert.match(a.details.join(' '),/You asked to build for the long term/);
assert.match(a.details.join(' '),/a contender/);
assert.match(b.summary,/their RB lineup weaker/);
assert(!/\byou\b|\byour\b/i.test(b.summary+' '+b.details.join(' ')));
assert.match(b.summary,/gain value further down the road/);
assert.equal(JSON.stringify(r),before);
let h=JSON.parse(before);h.owner_history={b:{status:'observed',source_state_id:'before',facts:['They acquired picks in 4 of their 10 recorded trades.']}};
assert.match(explain(h,'b',names).details.join(' '),/acquired picks in 4/);
h.owner_history.b.source_state_id='stale';assert(!explain(h,'b',names).details.join(' ').includes('acquired picks in 4'));
h.owner_history.b={status:'unavailable',source_state_id:'before'};assert.match(explain(h,'b',names).details.join(' '),/Trading history: Unavailable/);
h.owner_history.b={status:'observed',source_state_id:'before',completed_trade_count:4,facts:[]};assert.match(explain(h,'b',names).details.join(' '),/4 completed trades recorded/);

h.owner_history.b={status:'observed',source_state_id:'before',completed_trade_count:10,observations_version:'package-observations-v1',observations:[
 {kind:'acquire_picks',count:4,trade_count:10},{kind:'acquire_position',position:'WR',count:7},{kind:'package_shape',shape:'consolidation',count:3,trade_count:10}]};
let facts=c.window.fsfflOwnerHistoryFacts(h.owner_history,'b','before');
assert.match(facts[0],/They have traded for draft picks in 4 of 10 completed trades/);
assert.match(facts[1],/7 receivers/);assert(!facts[1].includes('7 trades'));
assert.match(facts[2],/sending several assets for fewer/);
let focalFacts=c.window.fsfflOwnerHistoryFacts(h.owner_history,'b','before',true);
assert.match(focalFacts[0],/You have traded/);assert.match(focalFacts[0],/brings you/);
assert(!/their|them|They/.test(focalFacts.join(' ')));
h.owner_history.b.observations=[{kind:'send_picks',count:2,trade_count:10},{kind:'counterparty',count:1}];
facts=c.window.fsfflOwnerHistoryFacts(h.owner_history,'b','before',true);
assert.match(facts[0],/your picks/);assert.match(facts[1],/You two have completed 1 trade together/);
h.owner_history.b.source_state_id='stale';assert.equal(c.window.fsfflOwnerHistoryFacts(h.owner_history,'b','before').length,0);
h.owner_history.b.source_state_id='before';h.owner_history.b.observations=[{kind:'acquire_picks',count:11,trade_count:10},{kind:'acquire_position',position:'WR',count:-1}];
assert.deepEqual(Array.from(c.window.fsfflOwnerHistoryFacts(h.owner_history,'b','before')),['10 completed trades recorded.']);

let x=JSON.parse(before);x.positional_context[0].source_state_id='stale';x.horizon_asset_economics.source.league_state_id='stale';
let story=explain(x,'a',names);assert(!story.summary.includes('Bucky'));assert(!story.summary.includes('career'));assert(!story.details.join(' ').includes('Josh Downs'));
x=JSON.parse(before);x.scenario_computation.authoritative=false;assert(!explain(x,'a',names).summary.includes('playoff'));
x=JSON.parse(before);x.team_deltas[0].competitive.playoff_probability=.00001;
assert(!explain(x,'a',names).summary.includes('raises'));assert.match(explain(x,'a',names).details.join(' '),/rounds to zero/);
x=JSON.parse(before);x.horizon_asset_economics.career.roster_adjusted.side_a.status='incomplete';assert(!explain(x,'a',names).summary.includes('careers'));
x=JSON.parse(before);x.positional_context[0].positions[0].baseline_league_strength.strength_index=100;assert(!explain(x,'a',names).summary.includes('below the league average'));
x=JSON.parse(before);x.positional_context[0].positions=[{position:'WR',expected_points_delta:0,outgoing_bench_ids:['bench']}];x.objective_assessment.side_a.transaction_strategy={};
story=explain(x,'a',names);assert.match(story.details.join(' '),/still depth/);assert(!story.headline.includes('Trade depth'));
x.objective_assessment.side_a.transaction_strategy.depth_conversion_candidate=true;x.positional_context[0].received_pick_ids=['p'];
story=explain(x,'a',names);assert.equal(story.headline,'Trade depth for the future');assert.match(story.details.join(' '),/also receive a draft pick/);
x=JSON.parse(before);x.positional_context[0].starter_replacements[0].replacement_was_already_starting=true;x.positional_context[0].starter_replacements[0].replacement_player_id='bucky';assert(!explain(x,'a',names).details.join(' ').includes('Bucky Irving'));assert.match(explain(x,'a',names).details.join(' '),/Josh Downs comes off your bench/);
x=JSON.parse(before);x.positional_context[0].positions[0].incoming_player_ids=['bucky','bench'];x.positional_context[0].positions[0].after_starter_ids=['bucky','bench'];assert.match(explain(x,'a',names).summary,/Bucky Irving and Young WR strengthen/);
assert(!/acceptance|will accept|wants to|surplus|significant|negligible/.test(JSON.stringify(a)+JSON.stringify(b)));
"""
    result=subprocess.run([node,'-e',script,'src/fsffl/product/static/trade_football_story.js'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
