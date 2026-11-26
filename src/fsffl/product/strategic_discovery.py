"""Opt-in bounded strategic discovery; no page-read or Simulation side effects."""
from __future__ import annotations

from collections import Counter
from itertools import zip_longest
from math import isfinite
import logging
from time import monotonic
from typing import Annotated, Literal

from pydantic import Field
from fsffl.forecast import attach_provisional_position_floor_forecasts
from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import optimize_team_lineup

from fsffl.opportunity.strategic_packages import StrategicPackageLane, StrategicSearchBounds
from fsffl.opportunity.guided_strategic_packages import generate_guided_strategic_packages
from fsffl.opportunity.trade_universe import TradeSearchBounds, build_team_trade_inventory
from fsffl.state.models import FrozenModel, PlayerAsset, PickAsset
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
from fsffl.trade_decision.objectives import TradeObjective

from .market_discovery_runtime import evaluate_candidate_path, evaluate_candidate_economics, _proposal_from_row, _economic_band
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
_MODEL_VERSION = "strategic-discovery-v8:goal-branches-and-funded-upgrades"

class StrategicDiscoveryRequest(FrozenModel):
    search_instructions: TradeSearchInstructions | None = None
    counterparty_team_id: str | None = None
    target_asset_ref: str | None = None
    target_position: str | None = None
    target_asset_kinds: tuple[Literal['player','pick'], ...] | None = None
    target_player_max_age: Annotated[int | None, Field(ge=0, le=100, strict=True)] = None
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


def _exploration_goals(context):
    from fsffl.opportunity.strategic_goals import exploration_goals
    return tuple(TradeObjective(g) for g in exploration_goals(context.objectives,
        inferred=not context.explicitly_directed,team_id=context.team_id))


def _ref(asset):
    return f'player:{asset.player_id}' if isinstance(asset,PlayerAsset) else f'pick:{asset.pick_id}'


def _matches_target(option, request):
    if request.target_asset_kinds is not None and option.asset_kind not in request.target_asset_kinds:
        return False
    if option.asset_kind == 'pick':
        # Position-only searches retain their existing player-only semantics.
        return request.target_position is None or request.target_asset_kinds is not None
    if request.target_position is not None and option.detail != request.target_position:
        return False
    age = option.age_years
    return request.target_player_max_age is None or (
        age is not None and isfinite(age) and 0 <= age < request.target_player_max_age + 1)


def prepare_discovery(runtime, request):
    state, focal = runtime.league_state, runtime.selected_team_id
    if state is None or focal is None:
        raise ValueError('A loaded league and managed team are required')
    context = objective_context(runtime, focal, request.search_instructions)
    if request.target_asset_kinds is not None and (not request.target_asset_kinds or len(set(request.target_asset_kinds)) != len(request.target_asset_kinds)):
        raise ValueError('Choose one or both target asset types without duplicates')
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
    if request.target_asset_ref is not None and not any(
        a.asset_ref == request.target_asset_ref and _matches_target(a, request)
        for team in teams for a in team.assets
    ):
        raise ValueError('The target asset must match the requested asset type, age and position')
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
    bounds = TradeSearchBounds(max_assets_per_side=8)
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
        elif isinstance(asset,PickAsset) and read is not None:
            for goal,name in ((TradeObjective.THREE_YEAR,'three_year'),(TradeObjective.CAREER,'career')):
                if asset_id in read.pick_values.get(name, {}):
                    metric_values[goal][asset] = read.pick_values[name][asset_id]
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
    benches={v.team_id:set(v.optimized_lineup.bench_player_ids) for v in (runtime.simulation_analytics.team_views if runtime.simulation_analytics is not None else ()) if v.optimized_lineup is not None}
    rank_signals = {}
    for goal in (TradeObjective.THREE_YEAR,TradeObjective.CAREER):
        covered = set(metric_values[goal]) & set(metric_values[TradeObjective.MARKET])
        native_ranks = _ranks({a:metric_values[goal][a] for a in covered})
        market_ranks = _ranks({a:metric_values[TradeObjective.MARKET][a] for a in covered})
        rank_signals[goal] = {a:market_ranks[a]-native_ranks[a] for a in covered}
    from .discovery_purposes import matching_published_lineups,pair_purpose_lanes
    from .behavioral_runtime import cached_behavior_profile_for_team
    from fsffl.behavioral.discovery_interests import observed_acquisition_interests
    lineups=matching_published_lineups(runtime)
    # Do not use position-strength snapshots from a different canonical State.
    if not lineups:purpose_strengths={}
    else:purpose_strengths=strengths
    ages={p.player_id:p.age_years for p in state.player_states
        if p.as_of<=state.as_of and p.age_years is not None and isfinite(p.age_years)}
    interests={t.team_id:observed_acquisition_interests(cached_behavior_profile_for_team(state,t.team_id),as_of=state.as_of)
        for t in (browser.focal_team,*teams)}
    lanes=[]
    for team in teams:
        other = inventories[team.team_id]
        if request.target_position is not None or request.target_asset_kinds is not None or request.target_player_max_age is not None:
            eligible = {a.asset_ref for a in team.assets if _matches_target(a, request)}
            other = other.model_copy(update={'assets': tuple(a for a in other.assets if _ref(a) in eligible)})
        other_context = objective_context(runtime,team.team_id)
        other_goal = next((g for g in _exploration_goals(other_context) if metric_values[g]),TradeObjective.MARKET)
        required = next((a for a in other.assets if _ref(a)==request.target_asset_ref),None)
        def add(name,sends,receives):
            if sends and receives:
                lanes.append(StrategicPackageLane(name,focal.model_copy(update={'assets':sends}),
                    other.model_copy(update={'assets':receives}),required_receive=required,required_send=required_send))
        add('roster_surplus', tuple(sorted(roster_fit(focal.assets,team.team_id), key=lambda a: not (isinstance(a,PlayerAsset) and a.player_id in benches.get(focal.team_id,set())))), roster_fit(other.assets,focal.team_id))
        # Explore inferred goal sets without a universal Current-first prefix.
        goals = tuple(dict.fromkeys((*_exploration_goals(context),TradeObjective.THREE_YEAR,TradeObjective.CAREER)))
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
        lanes.extend(pair_purpose_lanes(state_id=state.state_id,focal=focal,other=other,context=context,
            other_context=other_context,strengths=purpose_strengths,lineups=lineups,metrics=metric_values,
            positions=positions,ages=ages,roster_fit=roster_fit,required_send=required_send,
            required_receive=required,interests=interests))
        # Draft-capital packages need room for several picks, including shapes
        # that cannot arise from an alternating player/pick ingredient prefix.
        focal_picks = tuple(a for a in _descending(focal.assets,metric_values[other_goal]) if isinstance(a,PickAsset))
        other_picks = tuple(a for a in _descending(other.assets,metric_values[TradeObjective.CAREER]) if isinstance(a,PickAsset))
        add('spend_draft_capital', focal_picks,
            tuple(a for a in roster_fit(other.assets, focal.team_id) if isinstance(a,PlayerAsset)))
        add('acquire_draft_capital',
            tuple(a for a in roster_fit(focal.assets, team.team_id) if isinstance(a,PlayerAsset)), other_picks)
    # Across the first traversal, rotate teams as well as hypothesis lanes.
    names = tuple(dict.fromkeys(l.name for l in lanes))
    lanes = tuple(l for name in names for l in lanes if l.name==name)
    return lanes,context,browser,teams,rank_signals,profiles


def _representative_indices(rows,budget,*,visited_families=()):
    """Categorical coverage, not a composite opportunity score."""
    remaining=list(range(len(rows))); chosen=[]; teams=set(); hypotheses=set(); sent=set(); shapes=set(); paths=set(); families=set(visited_families); goal_turn=0; axis_turns=Counter()
    while remaining and len(chosen)<budget:
        # Existing Decision economics precede diversity. Unknowns and strained
        # structures remain available for explicit review, never gain priority
        # just because they involve a new team, size or outgoing asset.
        plausible=[i for i in remaining if rows[i].get('preliminary_economic_band') in ('robust_or_ordinary','bounded_uncertainty')]
        eligible=plausible or remaining
        complement=[i for i in eligible if rows[i].get('joint_priority_gain_hypothesis') or rows[i].get('pre_cut_horizon_complement_hypothesis')]
        eligible=complement or eligible
        # Explore each requested direction before demanding a gain in every
        # inferred horizon. A balanced inferred posture is not a veto on a
        # useful current/future exchange. These remain unconfirmed hypotheses.
        goals=next((r.get('search_objectives') for r in rows if r.get('search_objectives')),())
        axis=None
        if goals:
            for offset in range(len(goals)):
                goal=goals[(goal_turn+offset)%len(goals)]
                directed=[i for i in eligible if (rows[i].get('priority_gain_hints') or {}).get(goal,0)>1e-9]
                if directed:
                    if goal=='current_competitiveness':
                        targeted=[i for i in directed if any(p.get('kind')=='improve_lineup'
                            and p.get('team_id')==rows[i].get('focal_team_id') for p in rows[i].get('discovery_purposes',()))]
                        directed=targeted or directed
                    eligible=directed;axis=goal;goal_turn=(goal_turn+offset+1)%len(goals);break
        else:
            native_compatible=[i for i in eligible if rows[i].get('requested_native_compatibility') is True]
            eligible=native_compatible or eligible
        varied=[i for i in eligible if rows[i].get('focal_package_family',i) not in families]
        eligible=varied or eligible
        if axis is not None:
            # Allocate bounded small-package coverage rather than exhausting all
            # singleton swaps before testing a funded positional improvement.
            desired=(2,3,4)[axis_turns[axis]%3]
            structured=[i for i in eligible if len(rows[i]['send'])+len(rows[i]['receive'])==desired]
            eligible=structured or eligible
            axis_turns[axis]+=1
        smallest=min(len(rows[i]['send'])+len(rows[i]['receive']) for i in eligible)
        eligible=[i for i in eligible if len(rows[i]['send'])+len(rows[i]['receive'])==smallest]
        different_path=[i for i in eligible if set(rows[i].get('discovery_paths',('ordinary',)))-paths]
        eligible=different_path or eligible
        diverse=[i for i in eligible if rows[i]['counterparty_team_id'] not in teams]
        eligible=diverse or eligible
        diverse=[i for i in eligible if not ({a['asset_ref'] for a in rows[i]['send']} & sent)]
        eligible=diverse or eligible
        if axis is not None:
            # Magnitudes compare within ONE native coordinate, never a sum or
            # a conversion between Current, future contribution and Market.
            best=max(rows[i]['priority_gain_hints'][axis] for i in eligible)
            eligible=[i for i in eligible if rows[i]['priority_gain_hints'][axis]>=best-1e-9]
        # Positive completed-trade precedents break otherwise equivalent ties.
        # Absence is never a rejection, preference estimate or economic veto.
        from fsffl.trade_decision.contextual_precedents import precedent_category
        best=min(precedent_category(rows[i].get('owner_history',{}).get(rows[i]['counterparty_team_id'],{}).get('matching_features',()))for i in eligible)
        if best<2:
            eligible=[i for i in eligible if precedent_category(rows[i].get('owner_history',{}).get(rows[i]['counterparty_team_id'],{}).get('matching_features',()))==best]
        observed=[i for i in eligible if (rows[i].get('owner_history',{}).get(rows[i]['counterparty_team_id'],{}).get('matching_features'))]
        eligible=observed or eligible
        index=eligible[0]
        chosen.append(index);remaining.remove(index)
        paths.update(rows[index].get('discovery_paths',('ordinary',)))
        families.add(rows[index].get('focal_package_family',index))
        teams.add(rows[index]['counterparty_team_id']);hypotheses.update(rows[index]['hypotheses'])
        sent.update(a['asset_ref'] for a in rows[index]['send'])
        shapes.add((len(rows[index]['send']),len(rows[index]['receive'])))
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
    can_compensate=read is not None and screen_cap>=3
    reserve=min(8,pool_budget//4) if can_feedback or can_compensate else 0
    visits=FeedbackVisits(reserve)
    generation_limit=pool_budget-reserve
    from fsffl.trade_decision import live_bounded_materiality_policy
    try:
        tolerance=live_bounded_materiality_policy(as_of=runtime.league_state.as_of).economic.mean_value_abs
    except ValueError:
        tolerance=None
    typed_market={a:profiles[(a.player_id if isinstance(a,PlayerAsset) else a.pick_id)].market_price.distribution.mean
        for lane in lanes for a in (*lane.focal.assets,*lane.counterparty.assets)
        if isinstance(a,(PlayerAsset,PickAsset)) and (a.player_id if isinstance(a,PlayerAsset) else a.pick_id) in profiles
        and profiles[(a.player_id if isinstance(a,PlayerAsset) else a.pick_id)].market_price is not None}
    seeds,diagnostics=generate_guided_strategic_packages(lanes,as_of=runtime.league_state.as_of,
        market_values=typed_market,economic_tolerance=tolerance,
        bounds=StrategicSearchBounds(max_candidates=generation_limit,max_pair_visits=generation_limit))
    options={a.asset_ref:a for team in (browser.focal_team,*teams) for a in team.assets}
    asset_index=owned_asset_index(browser)
    market_values={asset_id:p.market_price.distribution.mean for asset_id,p in profiles.items() if p.market_price is not None}
    contexts={team.team_id:objective_context(runtime,team.team_id) for team in teams}
    forecast_means=_latest_season_forecast_means(runtime)
    positions={p.player_id:p.position for p in runtime.league_state.players}
    same_state_simulation=(runtime.simulation_analytics is not None and runtime.simulation_analytics.league_view.context.league_state_id==runtime.league_state.state_id)
    published_lineups={v.team_id:v.optimized_lineup for v in (runtime.simulation_analytics.team_views if same_state_simulation else ()) if v.optimized_lineup is not None}
    def current_gain_hint(team_id,sent,received):
        lineup=published_lineups.get(team_id)
        from .simulation_forecasts import current_forecast_coordinates
        try:
            _,hint_horizon,hint_cutoff=current_forecast_coordinates(runtime.league_state,runtime.forecast_evidence)
        except (ValueError,AttributeError): return None
        if lineup is None or lineup.horizon!=hint_horizon or lineup.as_of>hint_cutoff: return None
        floors={position:min(a.expected_points for a in lineup.assignments if a.position==position)
                for position in {a.position for a in lineup.assignments}}
        assigned={a.player_id:a.expected_points for a in lineup.assignments}
        bench={position:max((forecast_means.get(pid,0.) for pid in lineup.bench_player_ids if positions.get(pid)==position),default=0.) for position in floors}
        outgoing=sum(max(0.,assigned.get(a.player_id,0.)-bench.get(positions.get(a.player_id),0.)) for a in sent if isinstance(a,PlayerAsset))
        incoming=sum(max(0.,forecast_means.get(a.player_id,0.)-floors.get(positions.get(a.player_id),0.)) for a in received if isinstance(a,PlayerAsset))
        return incoming-outgoing
    from .owner_history_runtime import build_trade_owner_history, prepare_trade_owner_history
    from .behavioral_runtime import cached_behavior_profile_for_team
    history_profiles={team.team_id:cached_behavior_profile_for_team(runtime.league_state,team.team_id)
        for team in (browser.focal_team,*teams)}
    history_positions={p.player_id:p.position.value for p in runtime.league_state.players}
    history_context=prepare_trade_owner_history(runtime,profiles=history_profiles,player_positions=history_positions)
    from .discovery_purposes import purpose_catalog,package_purposes,review_purposes
    purposes=purpose_catalog(lanes)
    ordinary_names={l.name for l in lanes if l.purpose is None}
    repair_inventories={}
    for lane in lanes:
        for inventory in (lane.focal,lane.counterparty):
            prior=repair_inventories.get(inventory.team_id)
            assets=tuple(dict.fromkeys((*(prior.assets if prior else ()),*inventory.assets)))
            repair_inventories[inventory.team_id]=inventory.model_copy(update={'assets':assets})
    from .discovery_families import focal_package_family
    picks_by_id={p.pick_id:p for p in runtime.league_state.draft_picks}
    hint_checks=0
    hint_limit=min(64,pool_budget//8)
    def make_row(proposal, point_id, hypotheses):
        nonlocal hint_checks

        row={'point_id':point_id,'focal_team_id':proposal.side_a.team_id,'counterparty_team_id':proposal.side_b.team_id,
            'hypotheses':list(hypotheses),'send':[{'asset_ref':_ref(a),'label':options[_ref(a)].label} for a in proposal.side_a.sends],
            'receive':[{'asset_ref':_ref(a),'label':options[_ref(a)].label} for a in proposal.side_b.sends],
            'action_authority':'diagnostic_only','evidence_status':'not_roster_screened'}
        row['discovery_purposes']=package_purposes(purposes,team_id=proposal.side_b.team_id,hypotheses=hypotheses)
        paths={'ordinary'} if any(h in ordinary_names for h in hypotheses) or not row['discovery_purposes'] else set()
        paths.update('owner_history' if p['kind']=='observed_acquisition' else 'team_purpose' for p in row['discovery_purposes'])
        row['discovery_paths']=sorted(paths)
        row['focal_package_family']=focal_package_family(row,picks=picks_by_id,read=read)
        row['owner_history']=build_trade_owner_history(runtime,proposal,context=history_context)
        evidence=bind_trade_intrinsic_values(runtime,proposal,read) if read is not None else unavailable_trade_intrinsic('Published native horizon evidence unavailable')
        def raw_priority_gain(team_context,label):
            supported={TradeObjective.THREE_YEAR:'three_year',TradeObjective.CAREER:'career'}
            if any(g not in supported for g in team_context.objectives): return False
            deltas=[((evidence.get(supported[g]) or {}).get(label) or {}).get('mean_delta') for g in team_context.objectives]
            return bool(deltas) and all(d is not None and d>=0 for d in deltas) and any(d>0 for d in deltas)
        row['pre_cut_horizon_complement_hypothesis']=raw_priority_gain(context,'side_a') and raw_priority_gain(contexts[proposal.side_b.team_id],'side_b')
        def possible_priority_gain(team_context,label,sent,received):
            supported={TradeObjective.THREE_YEAR:'three_year',TradeObjective.CAREER:'career'}
            for goal in team_context.objectives:
                if goal==TradeObjective.CURRENT and (current_gain_hint(team_context.team_id,sent,received) or 0)>1e-9: return True
                if goal in supported:
                    value=((evidence.get(supported[goal]) or {}).get(label) or {}).get('mean_delta')
                    if value is not None and value>1e-9: return True
            return False
        row['joint_priority_gain_hypothesis']=(possible_priority_gain(context,'side_a',proposal.side_a.sends,proposal.side_b.sends)
            and possible_priority_gain(contexts[proposal.side_b.team_id],'side_b',proposal.side_b.sends,proposal.side_a.sends))
        # FLEX and replacement chains defeat the cheap independent-position
        # subtraction. For bounded small targeted packages, reuse Team Utility's
        # optimizer to order hypotheses. No weekly/cut or Simulation conclusion
        # is granted by this deliberately pre-cut hint.
        targeted=any(p.get('kind')=='improve_lineup' and p.get('team_id')==context.team_id
            for p in row['discovery_purposes'])
        optimized_hint=None
        if targeted and TradeObjective.CURRENT in context.objectives and hint_checks<hint_limit and len(proposal.side_a.sends)+len(proposal.side_b.sends)<=4:
            hint_checks+=1
            try:
                from fsffl.trade_decision import apply_bilateral_trade
                from .simulation_forecasts import current_forecast_coordinates
                hint_forecasts,hint_horizon,hint_cutoff=current_forecast_coordinates(runtime.league_state,runtime.forecast_evidence)
                before=published_lineups[context.team_id]
                if before.horizon!=hint_horizon or before.as_of>hint_cutoff:
                    raise ValueError('Published lineup coordinates do not match Current Forecast')
                after=optimize_team_lineup(apply_bilateral_trade(runtime.league_state,proposal).after,hint_forecasts,
                    team_id=context.team_id,as_of=hint_cutoff,horizon=hint_horizon,
                    allow_unfilled_slots=True,model_version='discovery-pre-cut-lineup-hint-v1')
                optimized_hint=sum(a.expected_points for a in after.assignments)-sum(a.expected_points for a in before.assignments)
            except (ValueError,KeyError,AttributeError):pass
        row['search_objectives']=[g.value for g in _exploration_goals(context)]
        row['priority_gain_hints']={g.value:((optimized_hint if optimized_hint is not None else current_gain_hint(context.team_id,proposal.side_a.sends,proposal.side_b.sends))
            if g==TradeObjective.CURRENT else ((evidence.get('three_year' if g==TradeObjective.THREE_YEAR else 'career') or {}).get('side_a') or {}).get('mean_delta'))
            for g in context.objectives if g in (TradeObjective.CURRENT,TradeObjective.THREE_YEAR,TradeObjective.CAREER)}
        row['priority_gain_hints']={g:v for g,v in row['priority_gain_hints'].items() if v is not None}
        if optimized_hint is not None and optimized_hint>1e-9 and raw_priority_gain(contexts[proposal.side_b.team_id],'side_b'):
            row['joint_priority_gain_hypothesis']=True
        row['counterparty_horizon_gain_current_pending']=(TradeObjective.CURRENT in context.objectives
            and raw_priority_gain(contexts[proposal.side_b.team_id],'side_b'))
        future_goals=[g for g in context.objectives if g in (TradeObjective.THREE_YEAR,TradeObjective.CAREER)]
        native_deltas=[((evidence.get('three_year' if g==TradeObjective.THREE_YEAR else 'career') or {}).get('side_a') or {}).get('mean_delta') for g in future_goals]
        row['requested_native_compatibility']=(all(d>=-1e-9 for d in native_deltas) if all(d is not None for d in native_deltas) else None)
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
    root_order=[roots[i] for i in _representative_indices(roots,min(len(roots),screen_cap+2),
        visited_families={r['focal_package_family'] for r in rows if r['point_id'] in excluded})]
    generated=monotonic()
    screened=[];seen={};root_attempts=repair_attempts=errors=duplicates=existing_repairs=0
    # One bounded sequence per batch; a previous batch must not disable all
    # future repairs. Exact screened IDs still prevent duplicate evaluations.
    sequence_used=False

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
                    effective_forecasts=effective_forecasts,baseline_by_team=baseline_by_team,asset_index=asset_index,owner_history_context=history_context)
            else:
                result=build_private_beta_trade_analysis(runtime,proposal,focal_team_id=runtime.selected_team_id)
            cuts=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality'])
            evidence=bind_trade_intrinsic_values(runtime,proposal,read,roster_resolutions=cuts) if read is not None else unavailable_trade_intrinsic('Published native horizon evidence unavailable')
            result={**result,'horizon_asset_economics':evidence}
            row.update({'current_roster_points':result.get('current_roster_points'),'forecast_input':result.get('forecast_input'),'evidence_status':'pre_simulation_screened','preliminary_decision_screen':result.get('preliminary_bilateral_screen'),
                'roster_legality':result['roster_legality'],'position_strength_comparisons':result.get('position_strength_comparisons'),
                'horizon_asset_economics':evidence,'roster_adjusted_market_net':result.get('roster_adjusted_market_net'),
                'objective_assessment':build_trade_objective_assessment(runtime,proposal,result,request.search_instructions),
                'owner_history':result.get('owner_history',row.get('owner_history')), 'behavioral_context':result.get('behavioral_context'), 'decision_completeness':result.get('decision_completeness')})
            # The raw negotiating envelope is superseded by the SAME existing
            # economic policy applied to the actually resolved mandatory cuts.
            row['pre_cut_economic_band']=row['preliminary_economic_band']
            row['preliminary_economic_band']=_economic_band(runtime,row).value
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
        if not (can_feedback or can_compensate) or sequence_used or screen_cap-len(screened)<2: continue
        from .strategic_compensation import compensation_path
        from itertools import chain
        path=chain(compensation_path(runtime,root,read,inventories=repair_inventories,visits=visits,feedback=lambda point_id:seen.get(point_id),market_values=market_values,economic_tolerance=tolerance) if can_compensate else (),
                   repair_path(runtime,root,read,protected_player_ids=context.protected_player_ids,visits=visits) if can_feedback else ())
        for point,lineage in path:
            if any(not _matches_target(options[_ref(a)],request) for a in point.counterparty_package.assets):
                visits.skipped['repair_outside_requested_targets'] += 1
                break
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
            if result is None or result.get('evidence_status')!='pre_simulation_screened': break
            if lineage['move']=='add_native_compensation':
                if discovery_display_context(result)['group']=='preliminary_fit': break
                if lineage['depth']>=2: break
            elif lineage['depth']==1 and not needs_second_step(result): break
    # Keep every evaluated point and failed parent; only then fill unscreened
    # exploration slots. The old 540->80 pruning cannot erase this evidence.
    fillers=[row for row in rows if row['point_id'] not in seen and row['point_id'] not in excluded]
    rows=screened+[fillers[i] for i in _representative_indices(fillers,
        max(0,request.max_candidates-len(screened)))]
    unexamined_pool_count = len([point for point in by_point if point not in seen and point not in excluded])
    _attach_comparable_frontiers(rows,runtime)
    for row in rows:
        review_purposes(row)
        row['display_context'] = discovery_display_context(row)
    from fsffl.opportunity.shortlist_quality import curate_shortlist
    curate_shortlist(rows)
    team_contexts = {team.team_id: _competitive_context(runtime, team.team_id) for team in (browser.focal_team, *teams)}
    returned_picks = {a['asset_ref'][5:] for row in rows for a in (*row['send'],*row['receive'])
                      if a['asset_ref'].startswith('pick:')}
    covered_picks = returned_picks & set(read.pick_sources) if read is not None else set()
    completed=monotonic()
    return {'league_state_id':runtime.league_state.state_id,'publication_generation_id':runtime.publication_generation_id,
        'focal_team_id':runtime.selected_team_id,'priority_context':context.model_dump(mode='json'),
        'competitive_context':team_contexts[runtime.selected_team_id], 'team_competitive_contexts':team_contexts,
        'pick_evidence':discovery_pick_context(runtime, rows, read=read),
        'candidate_packages':rows,'diagnostics':{**diagnostics,'candidate_pool_unique_count':len(by_point),'generated_candidate_pool_unique_count':pool_count,
            'candidate_pool_limit':pool_budget,'max_candidates':request.max_candidates,
            'pool_shapes':diagnostics['shapes'],'pool_hypotheses':diagnostics['hypotheses'],
            'candidate_count':len(rows),'returned_candidate_limit':request.max_candidates,
            'pick_package_count':sum(any(a['asset_ref'].startswith('pick:') for a in (*r['send'],*r['receive'])) for r in rows),
            'native_pick_intrinsic_coverage':('unavailable' if not covered_picks else
                'complete' if covered_picks==returned_picks else 'partial'),
            'native_pick_intrinsic_covered_count':len(covered_picks),
            'shapes':dict(Counter(f"{len(r['send'])}_for_{len(r['receive'])}" for r in rows)),
            'hypotheses':dict(Counter(h for r in rows for h in r['hypotheses'])),
            'returned_counterparties':len({r['counterparty_team_id'] for r in rows}),
            'preliminary_decision_attempts':len(screened),
            'preliminary_decision_errors':errors,'preliminary_decision_budget':request.evaluation_budget,
            'effective_preliminary_decision_budget':screen_cap,
            'changed_state_simulation_calls':0,'forecast_or_intrinsic_recomputations':0,
            'timing_ms':{'generation_and_raw_binding':round((generated-start)*1000,3),'decision_screens':round((completed-generated)*1000,3),'total':round((completed-start)*1000,3)},
            'purpose_lane_count':sum(l.purpose is not None for l in lanes),
            'pre_cut_lineup_hint_checks':hint_checks,'pre_cut_lineup_hint_limit':hint_limit,
            'owner_expansion_lane_count':sum(l.purpose is not None and l.purpose.kind=='observed_acquisition' for l in lanes),
            'screened_discovery_paths':dict(Counter(path for r in screened for path in r.get('discovery_paths',()))),
            'screened_counterparties':len({row['counterparty_team_id'] for row in screened}),
            'screened_shapes':dict(Counter(f"{len(row['send'])}_for_{len(row['receive'])}" for row in screened)),
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
