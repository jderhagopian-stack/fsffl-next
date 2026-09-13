from __future__ import annotations

import logging
from time import monotonic
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException

from fsffl.trade_decision import (
    apply_bilateral_trade,
    assess_package_economics,
    calculate_bilateral_economic_net,
    live_bounded_package_premium_prior,
    summarize_bilateral_trade_economics,
    summarize_package_concentration,
)

from .runtime import PrivateBetaRuntimeStore
from .trade_value_adapter import cardinal_market_profiles
from .webapp import AnalyzeTradeRequest, _proposal_from_request


_logger = logging.getLogger("uvicorn.error")
WorkspaceBuilder = Callable[..., dict[str, object]]


def _dump(value):
    return value.model_dump(mode="json") if value is not None else None


def _quick_trade_view(runtime, proposal, *, focal_team_id: str) -> dict[str, object]:
    """Return only cheap, already-authoritative package evidence.

    This is deliberately not a second Trade Decision. It validates the canonical
    changed State and exposes current Value/package economics while roster/lineup
    consequences and Simulation remain explicitly unavailable.
    """

    started = monotonic()
    scenario = apply_bilateral_trade(runtime.league_state, proposal)
    validated = monotonic()
    side_a_id = proposal.side_a.team_id
    side_b_id = proposal.side_b.team_id
    counterparty_team_id = side_b_id if focal_team_id == side_a_id else side_a_id

    profiles = cardinal_market_profiles(runtime.value_evidence)
    market_values = {
        asset_id: profile.market_price.distribution.mean
        for asset_id, profile in profiles.items()
        if profile.market_price is not None
    }
    concentration = summarize_package_concentration(proposal, market_values) if market_values else None
    package_economics = (
        assess_package_economics(
            concentration,
            prior=live_bounded_package_premium_prior(as_of=proposal.as_of),
        )
        if concentration is not None
        else None
    )
    economics = (
        summarize_bilateral_trade_economics(
            proposal,
            profiles,
            model_version="next5-trade-economics-v1:progressive-quick-view",
        )
        if profiles
        else None
    )
    economic_net = (
        calculate_bilateral_economic_net(
            economics,
            model_version="next5-economic-net-v1:progressive-quick-view",
        )
        if economics is not None
        else None
    )
    completed = monotonic()
    _logger.info(
        "FSFFL progressive Trade quick timing state_validation=%.3fs package_economics=%.3fs total=%.3fs state=%s",
        validated - started,
        completed - validated,
        completed - started,
        scenario.before.state_id,
    )
    warnings = [
        "Quick view is package-level evidence only. Full roster and lineup consequences are still calculating.",
        "Competitive win, playoff and first-place impact remains unavailable until the unchanged 50,000-run Simulation completes.",
    ]
    if not profiles:
        warnings.append("FSFFL Cardinal Value is still loading; no substitute package value is fabricated.")
    return {
        "proposal": proposal.model_dump(mode="json"),
        "focal_team_id": focal_team_id,
        "counterparty_team_id": counterparty_team_id,
        "state_id_before": scenario.before.state_id,
        "state_id_after_trade": scenario.after.state_id,
        "delivery": {
            "status": "quick_view_ready",
            "completeness": "partial_package_economics",
            "full_roster_analysis_pending": True,
            "full_simulation_pending": True,
        },
        "decision_completeness": {
            "status": "partial_package_economics",
            "simulation_backed": False,
            "final_disposition_available": False,
            "decision_scope": "canonical_state_and_package_economics_only",
            "missing_authorities": ["roster_consequences", "simulation", "final_disposition"],
        },
        "economics": _dump(economics),
        "economic_net": _dump(economic_net),
        "package_concentration": _dump(concentration),
        "package_economics": _dump(package_economics),
        "warnings": warnings,
    }


def install_progressive_delivery_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    workspace_builder: WorkspaceBuilder,
    require_user,
) -> None:
    """Install Phase 3 fast-first, full-fidelity-follow-up endpoints."""

    @app.get("/api/opportunities/workspace/quick")
    def opportunity_workspace_quick(user_id: str = Depends(require_user)) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        started = monotonic()
        result = workspace_builder(runtime, bilateral_evaluation_limit=0)
        completed = monotonic()
        _logger.info(
            "FSFFL progressive Market quick timing total=%.3fs state=%s status=%s candidates=%s",
            completed - started,
            getattr(runtime.league_state, "state_id", None),
            result.get("status"),
            (result.get("trade_discovery") or {}).get("candidate_count"),
        )
        return {
            **result,
            "delivery": {
                "status": "quick_view_ready" if result.get("status") == "ready" else "not_ready",
                "completeness": "search_only",
                "decision_enrichment_pending": result.get("status") == "ready",
                "full_simulation_pending": False,
            },
        }

    @app.post("/api/trade-center/quick")
    def trade_center_quick(
        request: AnalyzeTradeRequest,
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        try:
            proposal = _proposal_from_request(runtime, request, draft_prefix="product-trade-quick")
            return _quick_trade_view(runtime, proposal, focal_team_id=runtime.selected_team_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
