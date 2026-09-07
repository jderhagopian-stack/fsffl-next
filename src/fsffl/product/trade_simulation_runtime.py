from __future__ import annotations

from typing import Any, Callable

from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import compare_team_utility_vectors, optimize_team_lineup
from fsffl.trade_decision import (
    apply_bilateral_trade,
    assess_bilateral_materiality,
    assess_negotiation_feasibility,
    assess_package_economics,
    attach_owner_strategy,
    calculate_bilateral_economic_net,
    classify_bilateral_trade_decision,
    decide_trade_disposition,
    evaluate_bilateral_trade_deltas,
    live_bounded_materiality_policy,
    live_bounded_package_premium_prior,
    resolve_mandatory_roster_cuts,
    summarize_bilateral_trade_economics,
    summarize_package_concentration,
)
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.trade_decision.roster_economics import adjust_bilateral_market_net_for_mandatory_cuts

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult
from .trade_value_adapter import cardinal_market_profiles


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-post-trade-simulation-v4"


def _utility_for_team(result: LiveSimulationAnalyticsResult, team_id: str):
    view = next((item for item in result.team_views if item.team_id == team_id), None)
    if view is None or view.utility is None:
        raise ValueError(f"simulation utility is unavailable for {team_id}")
    return view.utility


def _projected_starter_map(league_state, forecasts, team_ids: tuple[str, ...]):
    protected: dict[str, frozenset[str]] = {}
    for team_id in team_ids:
        try:
            lineup = optimize_team_lineup(
                league_state,
                forecasts,
                team_id=team_id,
                as_of=league_state.as_of,
                horizon=ForecastHorizon.SEASON,
                allow_unfilled_slots=True,
                model_version=f"{_PRODUCT_MODEL_VERSION}:cut-protection-lineup",
            )
        except ValueError:
            continue
        protected[team_id] = frozenset(item.player_id for item in lineup.assignments)
    return protected


def build_post_trade_simulation_comparison(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Compare baseline and legal changed-roster outcomes and produce NEXT-5 disposition.

    Simulation remains authoritative for competitive outcomes. NEXT-5 consumes the
    before/after Team Utility vectors, cardinal market economics, actual mandatory
    cut cost and the bounded package-economics guard. No Presentation calculation
    can create or modify the resulting disposition.
    """

    league_state = runtime.league_state
    forecast_evidence = runtime.forecast_evidence
    baseline = runtime.simulation_analytics
    if league_state is None:
        raise ValueError("post-trade simulation requires a loaded league state")
    if forecast_evidence is None or not forecast_evidence.league_scored_forecasts:
        raise ValueError("post-trade simulation requires current NEXT-2 forecast evidence")
    if baseline is None:
        raise ValueError("post-trade simulation requires a current NEXT-4 baseline simulation")

    scenario = apply_bilateral_trade(league_state, proposal)
    side_a_id = proposal.side_a.team_id
    side_b_id = proposal.side_b.team_id
    if focal_team_id not in {side_a_id, side_b_id}:
        raise ValueError("focal team must be one side of the trade")
    counterparty_team_id = side_b_id if focal_team_id == side_a_id else side_a_id

    forecasts = forecast_evidence.raw_forecasts + forecast_evidence.league_scored_forecasts
    cardinal_profiles = cardinal_market_profiles(runtime.value_evidence)
    market_values = {
        asset_id: profile.market_price.distribution.mean
        for asset_id, profile in cardinal_profiles.items()
        if profile.market_price is not None
    }
    if not cardinal_profiles:
        raise ValueError("post-trade disposition requires authoritative FSFFL cardinal Value")

    protected = _projected_starter_map(scenario.after, forecasts, (side_a_id, side_b_id))
    roster_resolution = resolve_mandatory_roster_cuts(
        scenario.after,
        protected_player_ids_by_team=protected,
        market_values=market_values,
    )
    legal_after = roster_resolution.league_state
    changed = simulation_loader(legal_after, forecast_evidence)

    baseline_a = _utility_for_team(baseline, side_a_id)
    baseline_b = _utility_for_team(baseline, side_b_id)
    changed_a = _utility_for_team(changed, side_a_id)
    changed_b = _utility_for_team(changed, side_b_id)

    evaluation = evaluate_bilateral_trade_deltas(
        proposal,
        before_a=baseline_a,
        after_a=changed_a,
        before_b=baseline_b,
        after_b=changed_b,
        model_version="next5-bilateral-evaluation-v1:simulated-product-view",
    )
    decision = classify_bilateral_trade_decision(
        evaluation,
        model_version="next5-bilateral-decision-v2:simulated-product-view",
    )
    negotiation = assess_negotiation_feasibility(decision, focal_team_id=focal_team_id)
    strategic_context = attach_owner_strategy(decision)

    economics = summarize_bilateral_trade_economics(
        proposal,
        cardinal_profiles,
        model_version="next5-trade-economics-v1:fsffl-cardinal-simulated-product-view",
    )
    economic_net = calculate_bilateral_economic_net(
        economics,
        model_version="next5-economic-net-v1:fsffl-cardinal-simulated-product-view",
    )

    trade_team_resolutions = tuple(
        item
        for item in roster_resolution.resolutions
        if item.team_id in {focal_team_id, counterparty_team_id}
    )
    roster_adjusted_market_net = adjust_bilateral_market_net_for_mandatory_cuts(
        economic_net,
        trade_team_resolutions,
    )

    concentration = summarize_package_concentration(proposal, market_values)
    package_economics = assess_package_economics(
        concentration,
        prior=live_bounded_package_premium_prior(as_of=proposal.as_of),
    )
    materiality_policy = live_bounded_materiality_policy(as_of=proposal.as_of)
    material_assessment = assess_bilateral_materiality(
        evaluation,
        economic_net,
        competitive_policy=materiality_policy.competitive,
        economic_policy=materiality_policy.economic,
        roster_adjusted_market_net=roster_adjusted_market_net,
        model_version="next5-material-assessment-v3:simulated-product-view",
    )
    disposition = decide_trade_disposition(
        material_assessment,
        negotiation,
        strategic_context,
        focal_team_id=focal_team_id,
        package_economics=package_economics,
        model_version="next5-trade-disposition-v3:simulated-product-view",
    )

    comparisons = []
    for team_id in (focal_team_id, counterparty_team_id):
        baseline_utility = _utility_for_team(baseline, team_id)
        changed_utility = _utility_for_team(changed, team_id)
        delta = compare_team_utility_vectors(
            baseline_utility,
            changed_utility,
            model_version=f"{_PRODUCT_MODEL_VERSION}:team-delta",
        )
        comparisons.append(delta.model_dump(mode="json"))

    return {
        "focal_team_id": focal_team_id,
        "counterparty_team_id": counterparty_team_id,
        "state_id_before": scenario.before.state_id,
        "state_id_after_trade": scenario.after.state_id,
        "state_id_after": legal_after.state_id,
        "baseline_simulation_count": baseline.simulation_result.simulation_count,
        "scenario_simulation_count": changed.simulation_result.simulation_count,
        "team_deltas": comparisons,
        "roster_legality": [item.model_dump(mode="json") for item in trade_team_resolutions],
        "evaluation": evaluation.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
        "negotiation": negotiation.model_dump(mode="json"),
        "economics": economics.model_dump(mode="json"),
        "economic_net": economic_net.model_dump(mode="json"),
        "roster_adjusted_market_net": roster_adjusted_market_net.model_dump(mode="json"),
        "package_concentration": concentration.model_dump(mode="json"),
        "package_economics": package_economics.model_dump(mode="json"),
        "materiality_policy": materiality_policy.model_dump(mode="json"),
        "material_assessment": material_assessment.model_dump(mode="json"),
        "disposition": disposition.model_dump(mode="json"),
        "authority": {
            "state_transition": "NEXT-5 Trade Decision",
            "mandatory_roster_cuts": "NEXT-5 Trade Decision",
            "market_value": "NEXT-3 Value",
            "competitive_outcomes": "NEXT-4 Simulation",
            "scenario_delta": "NEXT-4 Team Utility",
            "materiality_and_disposition": "NEXT-5 Trade Decision",
            "package_economic_guard": "NEXT-5 Trade Decision bounded provisional prior",
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
