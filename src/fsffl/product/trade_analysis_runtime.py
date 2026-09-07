from __future__ import annotations

from typing import Any

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import (
    TeamUtilityVector,
    assemble_team_utility_vector,
    compare_position_strengths,
    optimize_team_lineup,
)
from fsffl.trade_decision import (
    apply_bilateral_trade,
    assess_package_economics,
    bind_owner_behavior_evidence,
    calculate_bilateral_economic_net,
    classify_bilateral_trade_decision,
    evaluate_bilateral_trade_deltas,
    live_bounded_package_premium_prior,
    resolve_mandatory_roster_cuts,
    summarize_bilateral_trade_economics,
    summarize_package_concentration,
)
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.trade_decision.roster_economics import adjust_bilateral_market_net_for_mandatory_cuts

from .trade_value_adapter import cardinal_market_profiles


_PRODUCT_MODEL_VERSION = "next8-trade-analysis-v8"


def _fallback_vector(team_id: str, *, as_of, reason: str) -> TeamUtilityVector:
    return TeamUtilityVector(team_id=team_id, as_of=as_of, model_version=f"{_PRODUCT_MODEL_VERSION}:{reason}")


def _assemble_resilience_vector(league_state, forecasts, *, team_id: str):
    try:
        return assemble_team_utility_vector(
            league_state,
            forecasts,
            team_id=team_id,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
            model_version=f"{_PRODUCT_MODEL_VERSION}:roster-consequences",
        ), None
    except ValueError as exc:
        return _fallback_vector(team_id, as_of=league_state.as_of, reason="roster-consequences-unavailable"), str(exc)


def _optimized_lineup(league_state, forecasts, *, team_id: str, purpose: str):
    return optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=league_state.as_of,
        horizon=ForecastHorizon.SEASON,
        allow_unfilled_slots=True,
        model_version=f"{_PRODUCT_MODEL_VERSION}:{purpose}",
    )


def _projected_starter_map(league_state, forecasts, team_ids: tuple[str, ...]):
    protected: dict[str, frozenset[str]] = {}
    if not forecasts:
        return protected
    for team_id in team_ids:
        try:
            lineup = _optimized_lineup(league_state, forecasts, team_id=team_id, purpose="cut-protection-lineup")
        except ValueError:
            continue
        protected[team_id] = frozenset(item.player_id for item in lineup.assignments)
    return protected


def _position_strength_comparison(before_state, after_state, forecasts, *, team_id: str):
    if not forecasts:
        return None
    try:
        before = _optimized_lineup(before_state, forecasts, team_id=team_id, purpose="position-strength-before")
        after = _optimized_lineup(after_state, forecasts, team_id=team_id, purpose="position-strength-after")
    except ValueError:
        return None
    return compare_position_strengths(before, after)


def build_private_beta_trade_analysis(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    counterparty_behavior_profile: OwnerBehaviorProfile | None = None,
) -> dict[str, object]:
    league_state = runtime.league_state
    if league_state is None:
        raise ValueError("trade analysis requires a loaded league state")

    scenario = apply_bilateral_trade(league_state, proposal)
    side_a_id = proposal.side_a.team_id
    side_b_id = proposal.side_b.team_id
    counterparty_team_id = side_b_id if focal_team_id == side_a_id else side_a_id
    warnings: list[str] = []
    evaluation = None
    decision = None
    roster_consequences_ready = False

    forecast_evidence = runtime.forecast_evidence
    forecasts = ()
    if forecast_evidence is not None:
        forecasts = forecast_evidence.raw_forecasts + forecast_evidence.league_scored_forecasts
    value_evidence = runtime.value_evidence
    cardinal_profiles = cardinal_market_profiles(value_evidence)
    market_values = {
        asset_id: profile.market_price.distribution.mean
        for asset_id, profile in cardinal_profiles.items()
        if profile.market_price is not None
    }
    package_concentration = summarize_package_concentration(proposal, market_values) if market_values else None
    package_economics = None
    if package_concentration is not None:
        package_economics = assess_package_economics(
            package_concentration,
            prior=live_bounded_package_premium_prior(as_of=proposal.as_of),
        )

    protected = _projected_starter_map(scenario.after, forecasts, (side_a_id, side_b_id))
    roster_resolution = resolve_mandatory_roster_cuts(
        scenario.after,
        protected_player_ids_by_team=protected,
        market_values=market_values,
    )
    legal_after = roster_resolution.league_state
    trade_team_resolutions = tuple(item for item in roster_resolution.resolutions if item.team_id in {side_a_id, side_b_id})
    position_strength = _position_strength_comparison(scenario.before, legal_after, forecasts, team_id=focal_team_id)

    if forecasts:
        before_a, error_before_a = _assemble_resilience_vector(scenario.before, forecasts, team_id=side_a_id)
        after_a, error_after_a = _assemble_resilience_vector(legal_after, forecasts, team_id=side_a_id)
        before_b, error_before_b = _assemble_resilience_vector(scenario.before, forecasts, team_id=side_b_id)
        after_b, error_after_b = _assemble_resilience_vector(legal_after, forecasts, team_id=side_b_id)
        for label, error in (("side A baseline", error_before_a), ("side A scenario", error_after_a), ("side B baseline", error_before_b), ("side B scenario", error_after_b)):
            if error:
                warnings.append(f"Roster consequence evidence unavailable for {label}: {error}")
        evaluation = evaluate_bilateral_trade_deltas(
            proposal,
            before_a=before_a,
            after_a=after_a,
            before_b=before_b,
            after_b=after_b,
            model_version="next5-bilateral-evaluation-v1:product-view",
        )
        decision = classify_bilateral_trade_decision(evaluation, model_version="next5-bilateral-decision-v2:product-view")
        roster_consequences_ready = any(side.delta.resilience is not None for side in (evaluation.side_a, evaluation.side_b))
    else:
        warnings.append("Roster consequence analysis is waiting for current NEXT-2 forecast evidence.")

    economics = None
    economic_net = None
    roster_adjusted_market_net = None
    if cardinal_profiles:
        economics = summarize_bilateral_trade_economics(
            proposal,
            cardinal_profiles,
            model_version="next5-trade-economics-v1:fsffl-cardinal-product-view",
        )
        economic_net = calculate_bilateral_economic_net(
            economics,
            model_version="next5-economic-net-v1:fsffl-cardinal-product-view",
        )
        roster_adjusted_market_net = adjust_bilateral_market_net_for_mandatory_cuts(
            economic_net,
            trade_team_resolutions,
        )
    else:
        warnings.append("FSFFL cardinal market Value is still loading for this trade.")

    behavioral_view = None
    if counterparty_behavior_profile is not None:
        behavioral_view = bind_owner_behavior_evidence(proposal, accepting_team_id=counterparty_team_id, profile=counterparty_behavior_profile)
    else:
        warnings.append("Owner Behavioral Intelligence is still building or no current owner profile is mapped for this counterparty.")

    incomplete_cut_cost = any(item.required_cut_count and item.cut_market_value_total is None for item in trade_team_resolutions)
    if incomplete_cut_cost:
        warnings.append("The post-trade state is roster-legal, but at least one mandatory cut lacks authoritative FSFFL Value; cut opportunity cost remains incomplete.")
    warnings.append("Competitive win/playoff/championship impact is intentionally unavailable in this fast analysis until the post-trade state is run through Simulation authority.")
    warnings.append("Acceptance probability is not estimated; Behavioral Intelligence is descriptive evidence until a calibrated acceptance model is promoted.")
    warnings.append("Package concentration is measured separately from cuts, lineup impact and Simulation. The current 0%-15% residual premium interval is only a provisional Decision robustness guard and is not added to FSFFL Value.")

    return {
        "proposal": proposal.model_dump(mode="json"),
        "focal_team_id": focal_team_id,
        "counterparty_team_id": counterparty_team_id,
        "state_id_before": scenario.before.state_id,
        "state_id_after_trade": scenario.after.state_id,
        "state_id_after": legal_after.state_id,
        "evaluation": evaluation.model_dump(mode="json") if evaluation is not None else None,
        "decision": decision.model_dump(mode="json") if decision is not None else None,
        "economics": economics.model_dump(mode="json") if economics is not None else None,
        "economic_net": economic_net.model_dump(mode="json") if economic_net is not None else None,
        "roster_adjusted_market_net": roster_adjusted_market_net.model_dump(mode="json") if roster_adjusted_market_net is not None else None,
        "package_concentration": package_concentration.model_dump(mode="json") if package_concentration is not None else None,
        "package_economics": package_economics.model_dump(mode="json") if package_economics is not None else None,
        "roster_legality": [item.model_dump(mode="json") for item in trade_team_resolutions],
        "position_strength": position_strength.model_dump(mode="json") if position_strength is not None else None,
        "behavioral_context": behavioral_view.model_dump(mode="json") if behavioral_view is not None else None,
        "availability": {
            "roster_consequences": roster_consequences_ready,
            "position_strength": position_strength is not None,
            "market_economics": economics is not None,
            "economic_net": economic_net is not None,
            "competitive_outcomes": False,
            "championship_probability": False,
            "mandatory_cut_cost": roster_adjusted_market_net is not None and not incomplete_cut_cost,
            "package_concentration_evidence": package_concentration is not None,
            "bounded_package_economic_guard": package_economics is not None,
            "package_concentration_premium": False,
            "behavioral_evidence": behavioral_view is not None,
            "acceptance_probability": False,
            "provisional_fsffl_value_used_for_decision": False,
        },
        "warnings": warnings,
        "model_version": _PRODUCT_MODEL_VERSION,
    }
