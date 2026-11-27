from __future__ import annotations

from typing import Any
import logging

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.opportunity.frontier import make_frontier_point
from fsffl.opportunity.frontier_search import FrontierSearchPolicy, explore_negotiation_frontier
from fsffl.opportunity.models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)
from fsffl.opportunity.trade_evaluation import candidate_from_trade_evaluation
from fsffl.opportunity.trade_universe import (
    TradePackageSeed,
    TradeSearchBounds,
    build_team_trade_inventory,
    canonical_package_id,
)
from fsffl.trade_decision import (
    BilateralTradeDecision,
    TradeAcceptanceView,
    assess_negotiation_feasibility,
)
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg

from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_objectives import TradeSearchInstructions, validate_search_instructions, build_trade_objective_assessment


_logger=logging.getLogger("uvicorn.error")

_PRODUCT_MODEL_VERSION = "next8-negotiation-frontier-v5:completed-history-lane"


def _package(team_id: str, assets) -> TradePackageSeed:
    items = tuple(assets)
    return TradePackageSeed(
        team_id=team_id,
        assets=items,
        canonical_id=canonical_package_id(team_id, items),
    )


def _proposal(point, *, as_of) -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id=point.point_id,
        as_of=as_of,
        side_a=TradeLeg(team_id=point.focal_package.team_id, sends=point.focal_package.assets),
        side_b=TradeLeg(team_id=point.counterparty_package.team_id, sends=point.counterparty_package.assets),
        model_version=f"{_PRODUCT_MODEL_VERSION}:proposal",
    )


def _incomplete_candidate(point, runtime) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id=point.point_id,
        kind=OpportunityKind.PRICE_DISCOVERY,
        focal_team_id=point.focal_package.team_id,
        league_state_id=runtime.league_state.state_id,
        as_of=runtime.league_state.as_of,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=ActionAuthority.DIAGNOSTIC_ONLY,
        evidence_completeness=EvidenceCompleteness.PARTIAL,
        reasons=(CandidateReason.INCOMPLETE_EVIDENCE,),
        search_model_version=_PRODUCT_MODEL_VERSION,
    )


def _asset_label(league_state, asset) -> str:
    if asset.kind == "player":
        player = next((item for item in league_state.players if item.player_id == asset.player_id), None)
        return player.full_name if player is not None else asset.player_id
    if asset.kind == "pick":
        pick = next((item for item in league_state.draft_picks if item.pick_id == asset.pick_id), None)
        if pick is None:
            return asset.pick_id
        return f"{pick.season} Round {pick.round} pick"
    return f"{asset.amount} FAAB"


def build_negotiation_frontier(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    counterparty_behavior_profile: OwnerBehaviorProfile | None = None,
    max_depth: int = 1,
    max_evaluations: int = 24,
    search_instructions: TradeSearchInstructions | None = None,
    horizon_provider=None,
    price_side=None,
) -> dict[str, object]:
    """Explore a responsive first slice of the governed negotiation frontier.

    The interactive product evaluates a bounded adjacent set synchronously so the
    user receives a useful frontier instead of waiting on a deep 100-point search.
    Every returned point remains a canonical owned package evaluated through the
    same NEXT-5 Decision adapter. Deeper frontier expansion can be requested later
    without changing Value, Decision authority, or acceptance semantics.
    """

    league_state = runtime.league_state
    if league_state is None:
        raise ValueError("negotiation frontier requires a loaded league state")
    if focal_team_id not in {proposal.side_a.team_id, proposal.side_b.team_id}:
        raise ValueError("focal team must be one side of the frontier seed")

    validate_search_instructions(runtime, proposal, search_instructions)
    focal_leg = proposal.side_a if proposal.side_a.team_id == focal_team_id else proposal.side_b
    counter_leg = proposal.side_b if proposal.side_a.team_id == focal_team_id else proposal.side_a
    max_seed_size = max(len(focal_leg.sends), len(counter_leg.sends))
    bounds = TradeSearchBounds(
        max_assets_per_side=min(6, max(max_seed_size + 1, 2)),
        include_players=True,
        include_picks=True,
        include_faab=False,
    )
    focal_inventory = build_team_trade_inventory(league_state, team_id=focal_leg.team_id, bounds=bounds)
    if search_instructions is not None:
        protected = set(search_instructions.protected_player_ids)
        focal_inventory = focal_inventory.model_copy(update={'assets': tuple(a for a in focal_inventory.assets
            if a.kind != 'player' or a.player_id not in protected)})
    counter_inventory = build_team_trade_inventory(league_state, team_id=counter_leg.team_id, bounds=bounds)
    seed = make_frontier_point(
        _package(focal_leg.team_id, focal_leg.sends),
        _package(counter_leg.team_id, counter_leg.sends),
    )

    # Reuse the existing published source once, bounded to these two rosters.
    read=None
    if horizon_provider is not None:
        try:
            ids=frozenset(r.player_id for t in league_state.team_states
                if t.team_id in (focal_leg.team_id,counter_leg.team_id) for r in t.roster)
            read=horizon_provider(runtime,ids)
            from .trade_intrinsic_evidence import published_horizons_match_runtime
            if read is not None and not published_horizons_match_runtime(runtime,read):
                read=None
        except Exception as exc:
            _logger.warning("Counter raw horizons unavailable error_type=%s",type(exc).__name__)
            read=None
    if price_side and (read is None or runtime.forecast_evidence is None):
        return {"state_id_before": league_state.state_id,
                "publication_generation_id": runtime.publication_generation_id,
                "focal_team_id": focal_team_id, "counterparty_team_id": counter_leg.team_id,
                "points": [], "evaluated_count": 0,
                "negotiating_terms": {"opening": None, "fallback": None, "eligible_count": 0,
                                      "reason": "missing_publication"}}
    screen_inputs={}
    if read is not None and runtime.forecast_evidence is not None:
        from .simulation_forecasts import current_forecast_coordinates
        from fsffl.forecast.models import ForecastHorizon
        from fsffl.forecast import attach_provisional_position_floor_forecasts
        from fsffl.team_utility import optimize_team_lineup
        from .trade_value_adapter import cardinal_market_profiles
        forecasts,horizon,cutoff=current_forecast_coordinates(league_state,runtime.forecast_evidence)
        effective=(forecasts if horizon==ForecastHorizon.REST_OF_SEASON else
            attach_provisional_position_floor_forecasts(league_state,forecasts,as_of=cutoff,horizon=horizon))
        simulation=runtime.simulation_analytics
        baselines={v.team_id:v.optimized_lineup for v in (simulation.team_views if simulation is not None else ()) if v.optimized_lineup is not None}
        for team in (focal_leg.team_id,counter_leg.team_id):
            if team not in baselines:
                baselines[team]=optimize_team_lineup(league_state,effective,team_id=team,as_of=cutoff,
                    horizon=horizon,allow_unfilled_slots=True,model_version='market-preliminary-screen-lineup-v1')
        profiles=cardinal_market_profiles(runtime.value_evidence)
        screen_inputs={'effective_forecasts':effective,'baseline_by_team':baselines,'profiles':profiles,
            'market_values':{pid:p.market_price.distribution.mean for pid,p in profiles.items() if p.market_price is not None}}
    from .owner_history_runtime import cached_trade_profiles, build_trade_owner_history, prepare_trade_owner_history
    history_profiles=cached_trade_profiles(runtime,proposal)
    history_positions={p.player_id:p.position.value for p in league_state.players}
    history_context=prepare_trade_owner_history(runtime,profiles=history_profiles,player_positions=history_positions)
    partner_strength = {}
    analytics = runtime.simulation_analytics if price_side else None
    if analytics is not None and analytics.league_view.context.league_state_id == league_state.state_id:
        partner_strength = {room.position.value: room.strength_index for team in analytics.team_views
                            if team.team_id == counter_leg.team_id for room in team.position_strengths
                            if room.strength_index is not None}
    seed_effects=None

    detail_by_point: dict[str, dict[str, object]] = {}

    def evaluator(point) -> OpportunityCandidate:
        point_proposal = _proposal(point, as_of=league_state.as_of)
        nonlocal seed_effects
        if read is not None and runtime.forecast_evidence is not None and focal_team_id==runtime.selected_team_id and all(a.kind in ('player','pick') for a in (*point.focal_package.assets,*point.counterparty_package.assets)):
            from .market_discovery_runtime import evaluate_candidate_path
            from .trade_intrinsic_evidence import bind_trade_intrinsic_values
            from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
            from .strategic_discovery_presentation import discovery_display_context
            from .counter_review import counter_effects,review_counter
            def ref(a):
                return f'player:{a.player_id}' if a.kind=='player' else f'pick:{a.pick_id}'
            row={'point_id':point.point_id,'counterparty_team_id':counter_leg.team_id,
                'send':[{'asset_ref':ref(a)} for a in point.focal_package.assets],
                'receive':[{'asset_ref':ref(a)} for a in point.counterparty_package.assets]}
            result=evaluate_candidate_path(runtime,row,owner_history_context=history_context,**screen_inputs)
            cuts=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality'])
            result['horizon_asset_economics']=bind_trade_intrinsic_values(runtime,point_proposal,read,roster_resolutions=cuts)
            assessment=build_trade_objective_assessment(runtime,point_proposal,result,search_instructions)
            context=discovery_display_context({'evidence_status':'pre_simulation_screened',
                'objective_assessment':assessment,'preliminary_decision_screen':result.get('preliminary_bilateral_screen')})
            effects=counter_effects(result,focal_team_id,counter_leg.team_id)
            price_check = {}
            if price_side:
                from .market_discovery_runtime import _economic_band
                band = _economic_band(runtime, {**result, "counterparty_team_id": counter_leg.team_id})
                price_context = discovery_display_context({
                    "evidence_status": "pre_simulation_screened", "objective_assessment": assessment,
                    "preliminary_decision_screen": result.get("preliminary_bilateral_screen"),
                    "preliminary_economic_band": band.value,
                })
                markets = result["roster_adjusted_market_net"]
                rooms = next((team["positions"] for team in result.get("positional_context", ())
                              if team["team_id"] == counter_leg.team_id), ())
                needs_filled = [room["position"] for room in rooms
                                if set(room["incoming_player_ids"]).intersection(room["after_starter_ids"])
                                and room.get("expected_points_delta", 0) > 0
                                and partner_strength.get(room["position"], 100) < 100]
                price_check = {"price_check": {
                    "needs_filled": needs_filled, "band": band.value,
                    "group": price_context["group"], "gate": price_context["limiting_gate"],
                    "market": {markets[s]["team_id"]: markets[s]["roster_adjusted_market_delta"]
                               for s in ("side_a", "side_b")},
                    "cuts": {r["team_id"]: r["required_cut_count"] for r in result["roster_legality"]},
                    "basis": effects["basis"],
                }}
            if point.point_id==seed.point_id:seed_effects=effects
            review=review_counter(seed_effects,effects,display_group=context['group'])
            detail_by_point[point.point_id]={**price_check,'owner_history':result.get('owner_history') or build_trade_owner_history(runtime,point_proposal,context=history_context), 'objective_assessment':assessment,'counter_review':review,
                'decision_shape':result['decision_shape'],
                'feasibility_shape':'mutual_gain_candidate' if review['status'] in ('improves_terms','alternative') else 'mixed',
                'action_authority':'diagnostic_only','reasons':['materiality_not_evaluated','unknown_acceptance']}
            return OpportunityCandidate(candidate_id=point.point_id,kind=OpportunityKind.PRICE_DISCOVERY,
                focal_team_id=focal_team_id,league_state_id=league_state.state_id,as_of=league_state.as_of,
                discovery_status=DiscoveryStatus.EVALUATED,action_authority=ActionAuthority.DIAGNOSTIC_ONLY,
                evidence_completeness=EvidenceCompleteness.PARTIAL,
                reasons=(CandidateReason.MATERIALITY_NOT_EVALUATED,CandidateReason.UNKNOWN_ACCEPTANCE),
                search_model_version=_PRODUCT_MODEL_VERSION)
        analysis = build_private_beta_trade_analysis(
            runtime,
            point_proposal,
            focal_team_id=focal_team_id,
            counterparty_behavior_profile=counterparty_behavior_profile,
        )
        if search_instructions is not None:
            assessment = build_trade_objective_assessment(runtime, point_proposal, analysis, search_instructions)
            detail_by_point[point.point_id] = {'objective_assessment': assessment}
            if any(assessment[s]['protected_players_lost'] for s in ('side_a', 'side_b')):
                candidate = _incomplete_candidate(point, runtime)
                detail_by_point[point.point_id].update({'decision_shape': None,
                    'feasibility_shape': 'constraints_violated', 'action_authority': 'diagnostic_only',
                    'reasons': ['protected_player_would_be_lost']})
                return candidate
        decision_payload = analysis.get("decision")
        if decision_payload is None:
            candidate = _incomplete_candidate(point, runtime)
            detail_by_point[point.point_id] = {
                **detail_by_point.get(point.point_id, {}),
                "decision_shape": None,
                "feasibility_shape": "incomplete",
                "behavioral_evidence": analysis.get("behavioral_context") is not None,
                "action_authority": candidate.action_authority.value,
                "reasons": [reason.value for reason in candidate.reasons],
            }
            return candidate

        decision = BilateralTradeDecision.model_validate(decision_payload)
        acceptance_payload = analysis.get("behavioral_context")
        acceptance = (
            TradeAcceptanceView.model_validate(acceptance_payload)
            if acceptance_payload is not None
            else None
        )
        feasibility = assess_negotiation_feasibility(
            decision,
            focal_team_id=focal_team_id,
            acceptance=acceptance,
            model_version=f"{_PRODUCT_MODEL_VERSION}:feasibility",
        )
        complete = bool(analysis.get("availability", {}).get("roster_consequences"))
        candidate = candidate_from_trade_evaluation(
            candidate_id=point.point_id,
            focal_team_id=focal_team_id,
            league_state_id=league_state.state_id,
            as_of=league_state.as_of,
            feasibility=feasibility,
            evidence_completeness=(
                EvidenceCompleteness.COMPLETE if complete else EvidenceCompleteness.PARTIAL
            ),
            acceptance=acceptance,
            disposition=None,
            search_model_version=_PRODUCT_MODEL_VERSION,
        )
        detail_by_point[point.point_id] = {
            **detail_by_point.get(point.point_id, {}),
            "decision_shape": decision.shape.value,
            "feasibility_shape": feasibility.shape.value,
            "behavioral_evidence": acceptance is not None,
            "action_authority": candidate.action_authority.value,
            "reasons": [reason.value for reason in candidate.reasons],
        }
        return candidate

    targeted = bool(read is not None and screen_inputs and focal_team_id == runtime.selected_team_id
        and all(a.kind in ('player', 'pick') for a in (*focal_leg.sends, *counter_leg.sends)))
    def order_neighbors(point, neighbors):
        # Only the original offer has established cost evidence at this stage.
        # Subsequent breadth-first layers preserve ordinary geometry/order.
        if point.point_id != seed.point_id:
            return neighbors
        from .counter_search import order_counter_hypotheses
        starters = {team: frozenset(a.player_id for a in lineup.assignments if a.player_id is not None)
            for team, lineup in screen_inputs['baseline_by_team'].items()}
        return order_counter_hypotheses(seed, neighbors, seed_effects=seed_effects,
            published=read, starters=starters,
            history_matches={p.point_id:build_trade_owner_history(runtime,_proposal(p,as_of=league_state.as_of),
                context=history_context)[counter_leg.team_id]['matching_features'] for p in neighbors})

    policy = FrontierSearchPolicy(
        max_depth=max_depth,
        max_evaluations=max_evaluations,
        expand_focal_side=price_side != "sell",
        expand_counterparty_side=price_side != "buy",
        include_substitutions=targeted,
    )
    result = explore_negotiation_frontier(
        seed,
        focal_inventory=focal_inventory,
        counterparty_inventory=counter_inventory,
        bounds=bounds,
        evaluator=evaluator,
        policy=policy,
        search_model_version=_PRODUCT_MODEL_VERSION,
        order_neighbors=order_neighbors if targeted else None,
        # A counter should retain at least one asset the user is trying to get.
        # Replacing the sole target is a different search, not better terms.
        allow_neighbor=(lambda p: bool(set(p.counterparty_package.assets) & set(seed.counterparty_package.assets))) if targeted and not price_side else None,
    )

    points = []
    for evaluated in result.evaluated:
        point = evaluated.point
        points.append(
            {
                "point_id": point.point_id,
                "depth": evaluated.depth,
                "is_seed": point.point_id == result.seed_point_id,
                "focal_assets": [
                    {
                        "kind": asset.kind,
                        "label": _asset_label(league_state, asset),
                        "asset": asset.model_dump(mode="json"),
                    }
                    for asset in point.focal_package.assets
                ],
                "counterparty_assets": [
                    {
                        "kind": asset.kind,
                        "label": _asset_label(league_state, asset),
                        "asset": asset.model_dump(mode="json"),
                    }
                    for asset in point.counterparty_package.assets
                ],
                'owner_history':build_trade_owner_history(runtime,_proposal(point,as_of=league_state.as_of),context=history_context),
                'counter_review': {'status':'incomplete','missing':['published_horizons'],'decision_effect':'no_disposition_change'},
                **detail_by_point.get(point.point_id, {}),
            }
        )

    plan = {}
    if price_side:
        from fsffl.opportunity.negotiating_terms import negotiating_terms
        plan = {"negotiating_terms": negotiating_terms(points, focal_team=focal_team_id,
                                                        other_team=counter_leg.team_id, buying=price_side == "buy"),
                "publication_generation_id": runtime.publication_generation_id}
    return {
        **plan,
        "seed_point_id": result.seed_point_id,
        "state_id_before": league_state.state_id,
        "focal_team_id": focal_team_id,
        "counterparty_team_id": counter_leg.team_id,
        "evaluated_count": len(result.evaluated),
        "max_depth_reached": result.max_depth_reached,
        "exhausted": result.exhausted,
        "policy": policy.model_dump(mode="json"),
        "bounds": bounds.model_dump(mode="json"),
        "points": points,
        "authority": {
            "search_geometry": "NEXT-6 Opportunity frontier",
            "bilateral_consequences": "NEXT-5 Trade Decision",
            "behavioral_evidence": counterparty_behavior_profile is not None,
            "acceptance_probability": False,
            "materiality_evaluated": False,
            "market_value_rewritten": False,
            "interactive_compute_bounded": True,
            "published_native_context":read is not None,
            "targeted_substitutions":targeted,
            "search_hints_are_transaction_effects":False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
