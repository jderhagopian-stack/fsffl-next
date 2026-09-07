from __future__ import annotations

from typing import Any, Callable

from fsffl.opportunity import EvidenceCompleteness, candidate_from_trade_evaluation
from fsffl.trade_decision import TradeDecisionDisposition, TradeNegotiationFeasibility
from fsffl.trade_decision.models import BilateralTradeProposal

from .behavioral_fit_runtime import build_trade_behavioral_fit
from .behavioral_runtime import cached_behavior_profile_for_team
from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult
from .trade_simulation_runtime import build_post_trade_simulation_comparison


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-trade-opportunity-action-v2:behavioral-fit"


def build_trade_opportunity_evaluation(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Promote a discovered trade only as far as governed evidence permits.

    The existing post-trade runtime owns changed-state Simulation and NEXT-5
    disposition. NEXT-6 maps those outputs into opportunity lifecycle authority.
    Behavioral Intelligence may add a directional plausibility estimate, but it
    does not rewrite Value, disposition, or action authority. Until a separate
    calibrated acceptance model exists, even a complete focal SUPPORT result is
    MARKET_TEST_ONLY rather than ACTIONABLE.
    """

    comparison = build_post_trade_simulation_comparison(
        runtime,
        proposal,
        focal_team_id=focal_team_id,
        simulation_loader=simulation_loader,
    )
    feasibility = TradeNegotiationFeasibility.model_validate(comparison["negotiation"])
    disposition = TradeDecisionDisposition.model_validate(comparison["disposition"])
    candidate = candidate_from_trade_evaluation(
        candidate_id=f"trade:{runtime.league_state.state_id}:{proposal.proposal_id}",
        focal_team_id=focal_team_id,
        league_state_id=runtime.league_state.state_id,
        as_of=proposal.as_of,
        feasibility=feasibility,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        acceptance=None,
        disposition=disposition,
        search_model_version=f"{_PRODUCT_MODEL_VERSION}:candidate",
    )

    counterparty_team_id = (
        proposal.side_b.team_id if proposal.side_a.team_id == focal_team_id else proposal.side_a.team_id
    )
    counterparty_profile = cached_behavior_profile_for_team(
        runtime.league_state,
        counterparty_team_id,
    )
    focal_profile = cached_behavior_profile_for_team(
        runtime.league_state,
        focal_team_id,
    )
    behavioral_fit = build_trade_behavioral_fit(
        runtime,
        proposal,
        focal_team_id=focal_team_id,
        counterparty_profile=counterparty_profile,
        focal_owner_id=focal_profile.owner_id if focal_profile is not None else None,
    )

    return {
        **comparison,
        "candidate": candidate.model_dump(mode="json"),
        "action_authority": candidate.action_authority.value,
        "behavioral_fit": behavioral_fit.model_dump(mode="json") if behavioral_fit is not None else None,
        "opportunity_explanation": (
            "Complete changed-state trade evidence is attached. Behavioral fit may "
            "describe whether the structure appears more or less plausible for the "
            "other owner, but acceptance remains uncalibrated. A supported offer may "
            "therefore be promoted only to market-test authority, not an acceptance "
            "prediction or automatic action."
        ),
        "authority": {
            **comparison["authority"],
            "opportunity_lifecycle": "NEXT-6 Opportunity",
            "behavioral_fit": "Behavioral Intelligence directional inference only",
            "acceptance": "not calibrated or numerically estimated",
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
