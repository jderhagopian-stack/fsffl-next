from __future__ import annotations

from typing import Any, Callable

from fsffl.team_utility import compare_team_utility_vectors
from fsffl.trade_decision import apply_bilateral_trade
from fsffl.trade_decision.models import BilateralTradeProposal

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-post-trade-simulation-v1"


def _utility_for_team(result: LiveSimulationAnalyticsResult, team_id: str):
    view = next((item for item in result.team_views if item.team_id == team_id), None)
    if view is None or view.utility is None:
        raise ValueError(f"simulation utility is unavailable for {team_id}")
    return view.utility


def build_post_trade_simulation_comparison(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Compare baseline and changed-roster outcomes through NEXT-4 Simulation.

    The adapter does not estimate wins in Product/Presentation. It applies the
    canonical trade through NEXT-5 state-transition authority, runs the changed
    state through the supplied authoritative NEXT-4 Simulation loader, then uses
    NEXT-4's typed scenario-delta contract to compare the two utility states.
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
    changed = simulation_loader(scenario.after, forecast_evidence)

    side_a_id = proposal.side_a.team_id
    side_b_id = proposal.side_b.team_id
    if focal_team_id not in {side_a_id, side_b_id}:
        raise ValueError("focal team must be one side of the trade")
    counterparty_team_id = side_b_id if focal_team_id == side_a_id else side_a_id

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
        "state_id_after": scenario.after.state_id,
        "baseline_simulation_count": baseline.simulation_result.simulation_count,
        "scenario_simulation_count": changed.simulation_result.simulation_count,
        "team_deltas": comparisons,
        "authority": {
            "state_transition": "NEXT-5 Trade Decision",
            "competitive_outcomes": "NEXT-4 Simulation",
            "scenario_delta": "NEXT-4 Team Utility",
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
