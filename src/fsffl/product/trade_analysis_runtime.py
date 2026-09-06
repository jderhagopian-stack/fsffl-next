from __future__ import annotations

from typing import Any

from fsffl.forecast.models import ForecastHorizon
from fsffl.team_utility import TeamUtilityVector, assemble_team_utility_vector
from fsffl.trade_decision import (
    apply_bilateral_trade,
    classify_bilateral_trade_decision,
    evaluate_bilateral_trade_deltas,
    summarize_bilateral_trade_economics,
)
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.value.models import AssetValueProfile


_PRODUCT_MODEL_VERSION = "next8-trade-analysis-v1"


def _fallback_vector(team_id: str, *, as_of, reason: str) -> TeamUtilityVector:
    return TeamUtilityVector(
        team_id=team_id,
        as_of=as_of,
        model_version=f"{_PRODUCT_MODEL_VERSION}:{reason}",
    )


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
        return (
            _fallback_vector(
                team_id,
                as_of=league_state.as_of,
                reason="roster-consequences-unavailable",
            ),
            str(exc),
        )


def build_private_beta_trade_analysis(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
) -> dict[str, object]:
    """Build a read-only NEXT-8 view from authoritative upstream contracts.

    This adapter is intentionally conservative. It applies the proposal through
    NEXT-5 transaction-state authority, compares NEXT-4 roster-resilience
    consequences when forecast evidence exists, and binds governed NEXT-3 market
    evidence through the existing trade-economics contract. It does not use the
    provisional cardinal FSFFL Value challenger, invent a trade grade, estimate
    acceptance, or approximate competitive win impact outside Simulation.
    """

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
    if forecast_evidence is not None:
        forecasts = forecast_evidence.raw_forecasts + forecast_evidence.league_scored_forecasts
        if forecasts:
            before_a, error_before_a = _assemble_resilience_vector(
                scenario.before, forecasts, team_id=side_a_id
            )
            after_a, error_after_a = _assemble_resilience_vector(
                scenario.after, forecasts, team_id=side_a_id
            )
            before_b, error_before_b = _assemble_resilience_vector(
                scenario.before, forecasts, team_id=side_b_id
            )
            after_b, error_after_b = _assemble_resilience_vector(
                scenario.after, forecasts, team_id=side_b_id
            )
            for label, error in (
                ("side A baseline", error_before_a),
                ("side A scenario", error_after_a),
                ("side B baseline", error_before_b),
                ("side B scenario", error_after_b),
            ):
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
            decision = classify_bilateral_trade_decision(
                evaluation,
                model_version="next5-bilateral-decision-v1:product-view",
            )
            roster_consequences_ready = any(
                side.delta.resilience is not None
                for side in (evaluation.side_a, evaluation.side_b)
            )
    if evaluation is None:
        warnings.append(
            "Roster consequence analysis is waiting for current NEXT-2 forecast evidence."
        )

    economics = None
    value_evidence = runtime.value_evidence
    if value_evidence is not None and value_evidence.estimates:
        profiles = {
            estimate.asset_id: AssetValueProfile(
                asset_id=estimate.asset_id,
                asset_kind=estimate.asset_kind,
                market_price=estimate,
            )
            for estimate in value_evidence.estimates
        }
        economics = summarize_bilateral_trade_economics(
            proposal,
            profiles,
            model_version="next5-trade-economics-v1:product-view",
        )
    else:
        warnings.append(
            "Governed market-economic context is waiting for current NEXT-3 market evidence."
        )

    # Current live simulation describes the baseline league. A changed roster must
    # be re-simulated through NEXT-4 before we may claim post-trade win/playoff deltas.
    warnings.append(
        "Competitive win/playoff impact is intentionally unavailable in this fast analysis until the post-trade state is run through Simulation authority."
    )
    warnings.append(
        "Acceptance probability is not estimated; no calibrated acceptance model is attached to this product runtime yet."
    )

    return {
        "proposal": proposal.model_dump(mode="json"),
        "focal_team_id": focal_team_id,
        "counterparty_team_id": counterparty_team_id,
        "state_id_before": scenario.before.state_id,
        "state_id_after": scenario.after.state_id,
        "evaluation": evaluation.model_dump(mode="json") if evaluation is not None else None,
        "decision": decision.model_dump(mode="json") if decision is not None else None,
        "economics": economics.model_dump(mode="json") if economics is not None else None,
        "availability": {
            "roster_consequences": roster_consequences_ready,
            "market_economics": economics is not None,
            "competitive_outcomes": False,
            "acceptance_probability": False,
            "provisional_fsffl_value_used_for_decision": False,
        },
        "warnings": warnings,
        "model_version": _PRODUCT_MODEL_VERSION,
    }
