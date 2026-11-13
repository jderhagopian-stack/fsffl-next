"""Opt-in bounded strategic discovery; no page-read or Simulation side effects."""
from __future__ import annotations

from collections import Counter
from itertools import zip_longest
from math import isfinite
import logging
from time import monotonic
from typing import Annotated

from pydantic import Field
from fsffl.forecast import attach_provisional_position_floor_forecasts
from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import optimize_team_lineup

from fsffl.opportunity.strategic_packages import StrategicPackageLane, StrategicSearchBounds, generate_strategic_packages
from fsffl.opportunity.trade_universe import TradeSearchBounds, build_team_trade_inventory
from fsffl.state.models import FrozenModel, PlayerAsset, PickAsset
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
from fsffl.trade_decision.objectives import TradeObjective

from .market_discovery_runtime import evaluate_candidate_path, evaluate_candidate_economics, _proposal_from_row
from .opportunity_search import _latest_season_forecast_means, _position_strengths
from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_center_view import build_trade_center_browser_view, owned_asset_index
from .trade_intrinsic_evidence import bind_trade_intrinsic_values, unavailable_trade_intrinsic, published_horizons_match_runtime
from .trade_objectives import TradeSearchInstructions, objective_context, build_trade_objective_assessment
from .trade_value_adapter import cardinal_market_profiles
from .strategic_discovery_presentation import discovery_display_context
from .discovery_pick_context import discovery_pick_context
from .opportunity_posture import calculated_competitive_state, default_posture_for_state
from dataclasses import replace

_logger = logging.getLogger("fsffl.product.performance")
_MODEL_VERSION = "strategic-discovery-v2:bounded-feedback-retention"

class StrategicDiscoveryRequest(FrozenModel):
    search_instructions: TradeSearchInstructions | None = None
    counterparty_team_id: str | None = None
    target_asset_ref: str | None = None
    target_position: str | None = None
    offered_asset_ref: str | None = None
    continuation_token: Annotated[str | None, Field(max_length=262144)] = None
    max_candidates: Annotated[int, Field(ge=1, le=80)] = 80
    evaluation_budget: Annotated[int, Field(ge=0, le=8)] = 8


def _competitive_context(runtime, team_id):
    calculated = calculated_competitive_state(replace(runtime, selected_team_id=team_id))
    simulation = runtime.simulation_analytics
    outcome = next((row for row in simulation.simulation_result.outcomes if row.team_id == team_id), None) if simulation else None
    return {'team_id': team_id, 'calculated_competitive_state': calculated.value,
        'default_search_posture': default_posture_for_state(calculated).value,
        'playoff_probability': outcome.playoff_probability if outcome else None,
        'championship_probability': outcome.championship_probability if outcome else None,
        'source': 'published_simulation' if simulation else 'unavailable', 'league_state_id': runtime.league_state.state_id,
        'interpretation': 'Calculated competitive state is separate from inferred owner goals; classification is provisional league-relative policy.'}


def _ref(asset):
    return f'player:{asset.player_id}' if isinstance(asset,PlayerAsset) else f'pick:{asset.pick_id}'


def prepare_discovery(runtime, request):
    state, focal = runtime.league_state, runtime.selected_team_id
    if state is None or focal is None:
        raise ValueError('A loaded league and managed team are required')
    context = objective_context(runtime, focal, request.search_instructions)
    browser = build_trade_center_browser_view(state, focal_team_id=focal)
    owned = {a.player_id for a in browser.focal_team.assets if a.player_id}
    if not set(context.protected_player_ids) <= owned:
        raise ValueError('Protected players must belong to the managed team')
    if request.offered_asset_ref is not None:
        offered = next((a for a in browser.focal_team.assets if a.asset_ref == request.offered_asset_ref), None)
        if offered is None:
            raise ValueError('The offered asset must belong to the managed team')
        if offered.player_id in context.protected_player_ids:
            raise ValueError('The offered player is protected')
    teams = browser.counterparties
    if request.counterparty_team_id is not None:
        teams = tuple(t for t in teams if t.team_id == request.counterparty_team_id)
        if not teams:
            raise ValueError('Counterparty must be another team in the current league')
    if request.target_asset_ref is not None:
        teams = tuple(t for t in teams if any(a.asset_ref == request.target_asset_ref for a in t.assets))
        if not teams:
            raise ValueError('The target must be owned by an admitted counterparty')
    if request.target_position is not None:
        if request.target_position not in {p.position.value for p in state.players}:
            raise ValueError('Target position must exist in the current league player population')
        positions = {p.player_id: p.position.value for p in state.players}
        if request.target_asset_ref is not None and not any(
            a.asset_ref == request.target_asset_ref and positions.get(a.player_id) == request.target_position
            for team in teams for a in team.assets
        ):
            raise ValueError('The target asset must match the requested position')
    return context, browser, teams


def _descending(assets, values):
    return tuple(sorted(assets,key=lambda a:(a not in values,-values.get(a,0.0),_ref(a))))


def _ranks(values):
    ordered = sorted(values, key=lambda a:(-values[a],_ref(a)))
    result, previous, rank = {}, None, 0
    for index,asset in enumerate(ordered,1):
        if previous is None or values[asset] != previous:
            rank = index
        result[asset], previous = rank, values[asset]
    return result


def _interleave_kinds(assets):
    groups = [tuple(a for a in assets if isinstance(a,kind)) for kind in (PlayerAsset,PickAsset)]
    return tuple(a for row in zip_longest(*groups) for a in row if a is not None)


def build_discovery_lanes(runtime, request, read):
    context, browser, teams = prepare_discovery(runtime,request)
    state = runtime.league_state
    bounds = TradeSearchBounds(max_assets_per_side=2)
    inventories = {t.team_id:build_team_trade_inventory(state,team_id=t.team_id,bounds=bounds)
                   for t in (browser.focal_team,*teams)}
    focal = inventories[runtime.selected_team_id]
    focal = focal.model_copy(update={'assets':tuple(a for a in focal.assets
        if not isinstance(a,PlayerAsset) or a.player_id not in context.protected_player_ids)})
    required_send = next((a for a in focal.assets if _ref(a) == request.offered_asset_ref), None)
    forecasts = _latest_season_forecast_means(runtime)
    profiles = cardinal_market_profiles(runtime.value_evidence)
    metric_values = {goal:{} for goal in TradeObjective}
    # Native values stay keyed by typed assets; a pick cannot borrow a player's ID.
    all_assets = {a for inventory in inventories.values() for a in inventory.assets}
    for asset in all_assets:
        asset_id = asset.player_id if isinstance(asset,PlayerAsset) else asset.pick_id
        profile = profiles.get(asset_id)
        if profile is not None and profile.asset_kind == asset.kind and profile.market_price is not None:
            value = profile.market_price.distribution.mean
            if isfinite(value): metric_values[TradeObjective.MARKET][asset] = value
        if isinstance(asset,PlayerAsset):
            if asset_id in forecasts and isfinite(forecasts[asset_id]):
                metric_values[TradeObjective.CURRENT][asset] = forecasts[asset_id]
            for goal,name in ((TradeObjective.THREE_YEAR,'three_year'),(TradeObjective.CAREER,'career')):
                if read is not None and asset_id in read.values[name]:
                    metric_values[goal][asset] = read.values[name][asset_id]
    strengths = _position_strengths(runtime)
    positions = {p.player_id:p.position for p in state.players}
    def roster_fit(assets,recipient):
        def key(asset):
            position = positions.get(asset.player_id) if isinstance(asset,PlayerAsset) else None
            row = strengths.get(recipient,{}).get(position)
            index = row.strength_index if row is not None else None
            return (index is None, index if index is not None else 0,
                    asset not in metric_values[TradeObjective.CURRENT],
                    -metric_values[TradeObjective.CURRENT].get(asset,0),_ref(asset))
        return tuple(sorted(assets,key=key))
    rank_signals = {}
    for goal in (TradeObjective.THREE_YEAR,TradeObjective.CAREER):
        covered = set(metric_values[goal]) & set(metric_values[TradeObjective.MARKET])
        native_ranks = _ranks({a:metric_values[goal][a] for a in covered})
        market_ranks = _ranks({a:metric_values[TradeObjective.MARKET][a] for a in covered})
        rank_signals[goal] = {a:market_ranks[a]-native_ranks[a] for a in covered}
    lanes=[]
    for team in teams:
        other = inventories[team.team_id]
        if request.target_position is not None:
            other = other.model_copy(update={'assets': tuple(a for a in other.assets
                if isinstance(a, PlayerAsset) and positions.get(a.player_id) == request.target_position)})
        other_context = objective_context(runtime,team.team_id)
        other_goal = next((g for g in other_context.objectives if metric_values[g]),TradeObjective.MARKET)
        required = next((a for a in other.assets if _ref(a)==request.target_asset_ref),None)
        def add(name,sends,receives):
            if sends and receives:
                lanes.append(StrategicPackageLane(name,focal.model_copy(update={'assets':sends}),
                    other.model_copy(update={'assets':receives}),required_receive=required,required_send=required_send))
        # Request order changes which horizon hypotheses receive early exploration.
        goals = tuple(dict.fromkeys((*context.objectives,TradeObjective.THREE_YEAR,TradeObjective.CAREER)))
        for goal in goals:
            if goal == TradeObjective.CURRENT:
                add('roster_fit',roster_fit(focal.assets,team.team_id),roster_fit(other.assets,focal.team_id))
                continue
            if goal not in (TradeObjective.THREE_YEAR,TradeObjective.CAREER) or not metric_values[goal]:
                continue
            sends = _descending(focal.assets,metric_values[other_goal])
            receives = _descending(other.assets,metric_values[goal])
            add(goal.value,sends,receives)
        if TradeObjective.CURRENT not in goals:
            add('roster_fit',roster_fit(focal.assets,team.team_id),roster_fit(other.assets,focal.team_id))
        for goal, signals in rank_signals.items():
            receives = tuple(a for a in _descending(other.assets,signals) if signals.get(a,0)>0)
            sends = _descending(focal.assets,{a:-v for a,v in signals.items()})
            add('rank_disagreement_'+goal.value,sends,receives)
        add('package_structure',_interleave_kinds(_descending(focal.assets,metric_values[TradeObjective.MARKET])),
            _interleave_kinds(_descending(other.assets,metric_values[TradeObjective.MARKET])))
    # Across the first traversal, rotate teams as well as hypothesis lanes.
    names = tuple(dict.fromkeys(l.name for l in lanes))
    lanes = tuple(l for name in names for l in lanes if l.name==name)
    return lanes,context,browser,teams,rank_signals,profiles


def _representative_indices(rows,budget):
    """Categorical coverage, not a composite opportunity score."""
    remaining=list(range(len(rows))); chosen=[]; teams=set(); hypotheses=set(); sent=set()
    while remaining and len(chosen)<budget:
        diverse = [i for i in remaining if not ({a['asset_ref'] for a in rows[i]['send']} & sent)]
        eligible = [i for i in diverse if rows[i]['counterparty_team_id'] not in teams
                    and set(rows[i]['hypotheses'])-hypotheses]
        if not eligible: eligible=[i for i in diverse if rows[i]['counterparty_team_id'] not in teams]
        if not eligible: eligible=[i for i in diverse if set(rows[i]['hypotheses'])-hypotheses]
        if not eligible: eligible=diverse
        if not eligible: eligible=[i for i in remaining if rows[i]['counterparty_team_id'] not in teams]
        if not eligible: eligible=[i for i in remaining if set(rows[i]['hypotheses'])-hypotheses]
        if not eligible: eligible=remaining
        # A conditional raw horizon complement may guide investigation; actual cuts
        # and team consequences are evaluated only in the subsequent Decision pass.
        index=next((i for i in eligible if rows[i]['pre_cut_horizon_complement_hypothesis']),None)
        if index is None:
            index=next((i for i in eligible if rows[i].get('counterparty_horizon_gain_current_pending')),None)
        if index is None:
            index=next((i for i in eligible if rows[i].get('preliminary_economic_band')
                in ('robust_or_ordinary','bounded_uncertainty')),eligible[0])
        chosen.append(index);remaining.remove(index)
        teams.add(rows[index]['counterparty_team_id']);hypotheses.update(rows[index]['hypotheses'])
        sent.update(a['asset_ref'] for a in rows[index]['send'])
    return chosen


def build_strategic_discovery(runtime, request, *, read=None, previously_screened=(), feedback_already_attempted=False):
    start=monotonic()
    if read is not None and not published_horizons_match_runtime(runtime,read):
        read=None
    lanes,context,browser,teams,rank_signals,profiles=build_discovery_lanes(runtime,request,read)
    pool_budget=min(640,request.max_candidates*8)
    screen_cap=min(request.evaluation_budget,request.max_candidates)
    from .strategic_feedback import FeedbackVisits, repair_path, needs_second_step
    can_feedback=(request.offered_asset_ref is None and read is not None and screen_cap>=3 and TradeObjective.CURRENT in context.objectives
        and runtime.forecast_evidence is not None
        and runtime.forecast_evidence.simulation_forward_forecasts is not None
        and runtime.simulation_analytics is not None)
    reserve=min(8,pool_budget//4) if can_feedback else 0
    visits=FeedbackVisits(reserve)
    generation_limit=pool_budget-reserve
    seeds,diagnostics=generate_strategic_packages(lanes,as_of=runtime.league_state.as_of,
        bounds=StrategicSearchBounds(max_candidates=generation_limit,max_pair_visits=generation_limit))
    options={a.asset_ref:a for team in (browser.focal_team,*teams) for a in team.assets}
    asset_index=owned_asset_index(browser)
    market_values={asset_id:p.market_price.distribution.mean for asset_id,p in profiles.items() if p.market_price is not None}
    contexts={team.team_id:objective_context(runtime,team.team_id) for team in teams}
    def make_row(proposal, point_id, hypotheses):
        row={'point_id':point_id,'counterparty_team_id':proposal.side_b.team_id,
            'hypotheses':list(hypotheses),'send':[{'asset_ref':_ref(a),'label':options[_ref(a)].label} for a in proposal.side_a.sends],
            'receive':[{'asset_ref':_ref(a),'label':options[_ref(a)].label} for a in proposal.side_b.sends],
            'action_authority':'diagnostic_only','evidence_status':'not_roster_screened'}
        evidence=bind_trade_intrinsic_values(runtime,proposal,read) if read is not None else unavailable_trade_intrinsic('Published native horizon evidence unavailable')
        def raw_priority_gain(team_context,label):
            supported={TradeObjective.THREE_YEAR:'three_year',TradeObjective.CAREER:'career'}
            if any(g not in supported for g in team_context.objectives): return False
            deltas=[((evidence.get(supported[g]) or {}).get(label) or {}).get('mean_delta') for g in team_context.objectives]
            return bool(deltas) and all(d is not None and d>=0 for d in deltas) and any(d>0 for d in deltas)
        row['pre_cut_horizon_complement_hypothesis']=raw_priority_gain(context,'side_a') and raw_priority_gain(contexts[proposal.side_b.team_id],'side_b')
        row['counterparty_horizon_gain_current_pending']=(TradeObjective.CURRENT in context.objectives
            and raw_priority_gain(contexts[proposal.side_b.team_id],'side_b'))
        row['raw_horizon_trade_deltas']={name:{side:((evidence.get(name) or {}).get(side) or {}).get('mean_delta') for side in ('side_a','side_b')} for name in ('three_year','career')}
        try:
            cheap=evaluate_candidate_economics(runtime,row,profiles=profiles,market_values=market_values,
                asset_index=asset_index,proposal=proposal)
            row['preliminary_economic_band']=cheap['preliminary_economic_band']
            row['package_economics']=cheap.get('package_economics')
        except ValueError:
            row['preliminary_economic_band']='incomplete'
        # Trade Center receives the same temporary directions with the exact assets.
        row['trade_center_request']={'counterparty_team_id':proposal.side_b.team_id,
            'focal_asset_refs':[_ref(a) for a in proposal.side_a.sends],
            'counterparty_asset_refs':[_ref(a) for a in proposal.side_b.sends]}
        if request.search_instructions is not None:
            row['trade_center_request']['search_instructions']=request.search_instructions.model_dump(mode='json')
        return row
    rows=[make_row(item.seed.proposal,item.seed.point_id,item.hypotheses) for item in seeds]
    pool_count=len(rows)
    by_point={row['point_id']:row for row in rows}
    excluded = frozenset(previously_screened)
    roots = [row for row in rows if row['point_id'] not in excluded]
    root_order=[roots[i] for i in _representative_indices(roots,min(len(roots),screen_cap+2))]
    generated=monotonic()
    screened=[];seen={};root_attempts=repair_attempts=errors=duplicates=existing_repairs=0
    sequence_used=feedback_already_attempted

    effective_forecasts=None
    baseline_by_team={}
    shared_error=None
    if screen_cap and runtime.forecast_evidence is not None:
        try:
            from .simulation_forecasts import current_forecast_coordinates
            forecasts,horizon,cutoff=current_forecast_coordinates(runtime.league_state,runtime.forecast_evidence)
            effective_forecasts=(forecasts if horizon==ForecastHorizon.REST_OF_SEASON else
                attach_provisional_position_floor_forecasts(runtime.league_state,forecasts,as_of=cutoff,horizon=horizon))
            simulation=runtime.simulation_analytics
            baseline_by_team={v.team_id:v.optimized_lineup for v in (simulation.team_views if simulation is not None else ()) if v.optimized_lineup is not None}
            needed={runtime.selected_team_id,*(row['counterparty_team_id'] for row in root_order)}
            for team_id in sorted(needed-set(baseline_by_team)):
                baseline_by_team[team_id]=optimize_team_lineup(runtime.league_state,effective_forecasts,
                    team_id=team_id,as_of=cutoff,horizon=horizon,
                    allow_unfilled_slots=True,model_version='market-preliminary-screen-lineup-v1')
        except ValueError as exc:
            shared_error=exc
    def screen(row,kind):
        nonlocal errors,root_attempts,repair_attempts
        if row['point_id'] in excluded:
            return None
        if row['point_id'] in seen:
            return seen[row['point_id']]
        if len(screened)>=screen_cap:
            return None
        seen[row['point_id']]=row;screened.append(row)
        row['evaluation_kind']=kind
        if kind=='root':root_attempts+=1
        else:repair_attempts+=1
        try:
            if shared_error is not None:
                raise shared_error
            proposal=_proposal_from_row(runtime,row,prefix='market-prelim',asset_index=asset_index)
            if runtime.forecast_evidence is not None:
                result=evaluate_candidate_path(runtime,row,profiles=profiles,market_values=market_values,
                    effective_forecasts=effective_forecasts,baseline_by_team=baseline_by_team,asset_index=asset_index)
            else:
                result=build_private_beta_trade_analysis(runtime,proposal,focal_team_id=runtime.selected_team_id)
            cuts=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality'])
            evidence=bind_trade_intrinsic_values(runtime,proposal,read,roster_resolutions=cuts) if read is not None else unavailable_trade_intrinsic('Published native horizon evidence unavailable')
            result={**result,'horizon_asset_economics':evidence}
            row.update({'current_roster_points':result.get('current_roster_points'),'forecast_input':result.get('forecast_input'),'evidence_status':'pre_simulation_screened','preliminary_decision_screen':result.get('preliminary_bilateral_screen'),
                'roster_legality':result['roster_legality'],'position_strength_comparisons':result.get('position_strength_comparisons'),
                'horizon_asset_economics':evidence,'roster_adjusted_market_net':result.get('roster_adjusted_market_net'),
                'objective_assessment':build_trade_objective_assessment(runtime,proposal,result,request.search_instructions),
                'behavioral_context':result.get('behavioral_context'), 'decision_completeness':result.get('decision_completeness')})
        except Exception as exc:
            errors+=1
            row['evidence_status']='screen_unavailable'
            row['screen_error_type']=type(exc).__name__
            _logger.warning('Strategic discovery screen unavailable error_type=%s',type(exc).__name__)
        return row

    for root in root_order:
        if len(screened)>=screen_cap: break
        if root['point_id'] in seen: continue
        screen(root,'root')
        if not can_feedback or sequence_used or screen_cap-len(screened)<2: continue
        path=repair_path(runtime,root,read,protected_player_ids=context.protected_player_ids,visits=visits)
        for point,lineage in path:
            sequence_used=True
            if len(screened)>=screen_cap: break
            if point.point_id in excluded:
                root.setdefault('linked_prior_point_ids',[]).append(point.point_id)
                visits.skipped['previously_evaluated_repair_not_repeated'] += 1
                break
            row=by_point.get(point.point_id)
            if row is not None: existing_repairs+=1
            if row is None:
                from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
                proposal=BilateralTradeProposal(proposal_id=point.point_id,as_of=runtime.league_state.as_of,
                    side_a=TradeLeg(team_id=point.focal_package.team_id,sends=point.focal_package.assets),
                    side_b=TradeLeg(team_id=point.counterparty_package.team_id,sends=point.counterparty_package.assets))
                row=make_row(proposal,point.point_id,('feedback_repair',))
                rows.append(row);by_point[point.point_id]=row
            row.setdefault('repair_lineages',[]).append(lineage)
            if point.point_id in seen: duplicates+=1
            result=screen(row,'repair')
            if result is None or (lineage['depth']==1 and not needs_second_step(result)): break
    # Keep every evaluated point and failed parent; only then fill unscreened
    # exploration slots. The old 540->80 pruning cannot erase this evidence.
    fillers=[row for row in rows if row['point_id'] not in seen and row['point_id'] not in excluded]
    rows=screened+[fillers[i] for i in _representative_indices(fillers,
        max(0,request.max_candidates-len(screened)))]
    unexamined_pool_count = len([point for point in by_point if point not in seen and point not in excluded])
    _attach_comparable_frontiers(rows,runtime)
    for row in rows:
        row['display_context'] = discovery_display_context(row)
    team_contexts = {team.team_id: _competitive_context(runtime, team.team_id) for team in (browser.focal_team, *teams)}
    completed=monotonic()
    return {'league_state_id':runtime.league_state.state_id,'publication_generation_id':runtime.publication_generation_id,
        'focal_team_id':runtime.selected_team_id,'priority_context':context.model_dump(mode='json'),
        'competitive_context':team_contexts[runtime.selected_team_id], 'team_competitive_contexts':team_contexts,
        'pick_evidence':discovery_pick_context(runtime, rows),
        'candidate_packages':rows,'diagnostics':{**diagnostics,'candidate_pool_unique_count':len(by_point),'generated_candidate_pool_unique_count':pool_count,
            'candidate_pool_limit':pool_budget,'max_candidates':request.max_candidates,
            'pool_shapes':diagnostics['shapes'],'pool_hypotheses':diagnostics['hypotheses'],
            'candidate_count':len(rows),'returned_candidate_limit':request.max_candidates,
            'pick_package_count':sum(any(a['asset_ref'].startswith('pick:') for a in (*r['send'],*r['receive'])) for r in rows),
            'native_pick_intrinsic_coverage':'unavailable',
            'shapes':dict(Counter(f"{len(r['send'])}_for_{len(r['receive'])}" for r in rows)),
            'hypotheses':dict(Counter(h for r in rows for h in r['hypotheses'])),
            'returned_counterparties':len({r['counterparty_team_id'] for r in rows}),
            'preliminary_decision_attempts':len(screened),
            'preliminary_decision_errors':errors,'preliminary_decision_budget':request.evaluation_budget,
            'effective_preliminary_decision_budget':screen_cap,
            'changed_state_simulation_calls':0,'forecast_or_intrinsic_recomputations':0,
            'timing_ms':{'generation_and_raw_binding':round((generated-start)*1000,3),'decision_screens':round((completed-generated)*1000,3),'total':round((completed-start)*1000,3)},
            'screened_counterparties':len({row['counterparty_team_id'] for row in screened}),
            'screened_hypotheses':dict(Counter(h for row in screened for h in row['hypotheses'])),
            'pair_visits':diagnostics['pair_visits']+visits.used,'max_pair_visits':pool_budget,
            'generation_pair_visits':diagnostics['pair_visits'],'generation_visit_budget':generation_limit,
            'repair_pair_visits':visits.used,'repair_visit_budget':reserve,
            'repair_visit_exhausted':visits.exhausted,'repair_skipped':dict(visits.skipped),
            'root_screen_attempts':root_attempts,'repair_screen_attempts':repair_attempts,
            'duplicate_repair_points':duplicates,'repair_existing_pool_points':existing_repairs,
            'repair_sequence_attempted':sequence_used,
            'evaluated_points_retained':len(screened),
            'previously_evaluated_skipped':len(excluded),
            'unexamined_pool_count':unexamined_pool_count,
            'rank_signal_covered_players':{goal.value:len(values) for goal,values in rank_signals.items()},
            'native_player_coverage':{name:len(values) for name,values in read.values.items()} if read is not None else {},
            'raw_source':dict(read.source) if read is not None else None},
        'interpretation':'Bounded hypotheses and preliminary consequences; no final recommendations, acceptance probabilities or confirmed mutual benefit',
        'model_version':_MODEL_VERSION}


def _attach_comparable_frontiers(rows,runtime):
    """Reuse NEXT6 Pareto comparisons only where BOTH goal vectors are complete.

    Different goal sets/native coordinates are separate groups. Missing cases
    remain visible, not dominated. Non-domination never grants action authority.
    """
    from fsffl.opportunity.ordering import OrderedOpportunityPoint, OpportunityObjective, ObjectiveDirection, pareto_front
    from fsffl.opportunity.models import OpportunityCandidate
    groups={}
    for row in rows:
        row['non_dominated_within_comparable_evaluated_group']=None
        assessment=row.get('objective_assessment')
        if not assessment or any(assessment[side]['status'] in ('incomplete','constraints_violated') for side in ('side_a','side_b')):
            continue
        metrics=[];coordinates=[]
        for side in ('side_a','side_b'):
            goals=assessment[side]['context']['objectives']
            for metric in assessment[side]['metrics']:
                if metric['objective'] not in goals:
                    continue
                if not metric['authoritative'] or metric['delta'] is None:
                    metrics=[];break
                name=f"{side}:{metric['objective']}:{metric['metric']}"
                metrics.append(OpportunityObjective(name=name,value=metric['delta'],
                    direction=ObjectiveDirection.MAXIMIZE if metric['higher_is_better'] else ObjectiveDirection.MINIMIZE))
                coordinates.append((name,metric['unit'],metric['source_identity']))
            if not metrics: break
        if not metrics: continue
        candidate=OpportunityCandidate(candidate_id=row['point_id'],kind='trade',focal_team_id=runtime.selected_team_id,
            league_state_id=runtime.league_state.state_id,as_of=runtime.league_state.as_of,
            discovery_status='evaluated',action_authority='diagnostic_only',evidence_completeness='partial',
            reasons=('unknown_acceptance','materiality_not_evaluated'),search_model_version=_MODEL_VERSION)
        groups.setdefault(tuple(coordinates),[]).append(OrderedOpportunityPoint(candidate=candidate,objectives=tuple(metrics)))
    survivors=set();eligible=set()
    for points in groups.values():
        eligible.update(p.candidate.candidate_id for p in points)
        survivors.update(p.candidate.candidate_id for p in pareto_front(tuple(points)))
    for row in rows:
        if row['point_id'] in eligible:
            row['non_dominated_within_comparable_evaluated_group']=row['point_id'] in survivors
