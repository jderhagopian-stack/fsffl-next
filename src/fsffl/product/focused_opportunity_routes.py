from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Mapping

from fastapi import Depends, FastAPI, HTTPException

from fsffl.opportunity import OpportunitySource
from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .focused_opportunity_search import build_focused_trade_candidates
from .market_discovery_runtime import (
    DEFAULT_PRELIMINARY_DECISION_BUDGET,
    build_market_discovery,
)
from .opportunity_posture import posture_payload
from .opportunity_spotlights import build_trade_spotlights
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext
from .trade_center_view import (
    TradeCenterBrowserView,
    build_trade_center_browser_view,
    owned_asset_index,
)


WorkspaceBuilder = Callable[..., dict[str, object]]
CandidateBuilder = Callable[
    [UserRuntimeContext, TradeCenterBrowserView, Mapping[str, FSFFLCardinalValueScore]],
    list[dict[str, object]],
]


def _identity(row: dict[str, object]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        str(row.get("counterparty_team_id") or ""),
        tuple(str(item.get("asset_ref") or "") for item in (row.get("send") or [])),
        tuple(str(item.get("asset_ref") or "") for item in (row.get("receive") or [])),
    )


def _posture(value: str) -> OwnerStrategicPosture:
    try:
        return OwnerStrategicPosture(value)
    except ValueError:
        return OwnerStrategicPosture.DEFAULT_CALCULATED


_logger = logging.getLogger("uvicorn.error")


def _focus_outcome(
    focused: list[dict[str, object]],
    market_discovery: dict[str, object],
) -> dict[str, object]:
    """Explain whether a focused request found paths or where cheap exploration ended."""

    search_diag = dict(getattr(focused, "diagnostics", {}) or {})
    discovery_diag = dict(market_discovery.get("diagnostics") or {})
    path_count = len(market_discovery.get("candidate_paths") or [])
    opportunity_count = len(market_discovery.get("opportunities") or [])
    candidates = len(focused)
    targets_considered = int(search_diag.get("targets_considered", 0) or 0)
    targets_admitted = int(search_diag.get("targets_admitted_pre_package", 0) or 0)
    counterparties_considered = int(search_diag.get("counterparties_considered", 0) or 0)
    counterparties_admitted = int(
        search_diag.get("counterparties_admitted_pre_package", 0) or 0
    )
    packages = int(search_diag.get("raw_packages_generated_pre_dedup", 0) or 0)
    families = int(discovery_diag.get("path_families_created", 0) or 0)
    prelim_runs = int(discovery_diag.get("preliminary_decision_runs", 0) or 0)

    if candidates > 0 and path_count > 0:
        code = "focused_results_ready"
        message = (
            f"Search explored {targets_considered} target assets across "
            f"{counterparties_considered} counterparties, admitted {targets_admitted} "
            f"targets before package generation, and returned {path_count} candidate "
            f"path{'s' if path_count != 1 else ''}."
        )
    elif counterparties_considered and counterparties_admitted == 0:
        code = "no_counterparty_admitted"
        message = (
            f"Search examined {counterparties_considered} counterparties, but none "
            "satisfied the submitted owner/roster/strategic constraints before package generation."
        )
    elif targets_considered and targets_admitted == 0:
        code = "no_target_admitted"
        message = (
            f"Search examined {targets_considered} target assets across "
            f"{counterparties_admitted or counterparties_considered} relevant counterparties, "
            "but none satisfied the submitted intent and strategic lens before package generation."
        )
    elif packages == 0:
        code = "no_package_neighborhood"
        message = (
            "Relevant assets were explored, but no governed package neighborhood could be "
            "constructed from the admitted holdings and current Value coverage."
        )
    elif families == 0:
        code = "no_path_family_after_economic_screen"
        message = (
            f"Search generated {packages} package rows, but none formed a surviving "
            "economically usable candidate-path family."
        )
    else:
        code = "no_final_path_after_screening"
        message = (
            f"Search formed {families} path families and spent {prelim_runs} bounded "
            "preliminary Decision screens, but no path remained for this submitted view."
        )

    return {
        "status": "results" if path_count else "zero",
        "reason_code": code,
        "message": message,
        "candidate_count": candidates,
        "candidate_path_count": path_count,
        "opportunity_count": opportunity_count,
        "counterparties_considered": counterparties_considered,
        "counterparties_admitted_pre_package": counterparties_admitted,
        "targets_considered": targets_considered,
        "targets_admitted_pre_package": targets_admitted,
        "send_assets_considered": int(search_diag.get("send_assets_considered", 0) or 0),
        "send_assets_admitted_for_counterparty_need": int(
            search_diag.get("send_assets_admitted_for_counterparty_need", 0) or 0
        ),
        "package_rows_generated_pre_dedup": packages,
        "packages_removed_exact_duplicate": int(
            search_diag.get("packages_removed_exact_duplicate", 0) or 0
        ),
        "packages_screened_economic": int(
            discovery_diag.get("packages_screened_economic", 0) or 0
        ),
        "packages_economic_incomplete": int(
            discovery_diag.get("packages_economic_incomplete", 0) or 0
        ),
        "cheap_economic_screen_errors": int(
            discovery_diag.get("cheap_economic_screen_errors", 0) or 0
        ),
        "path_families_created": families,
        "packages_collapsed_family_neighborhood": int(
            discovery_diag.get("packages_collapsed_family_neighborhood", 0) or 0
        ),
        "preliminary_decision_runs": prelim_runs,
        "preliminary_decision_budget": int(
            discovery_diag.get("preliminary_decision_budget", 0) or 0
        ),
        "preliminary_decision_errors": int(
            discovery_diag.get("preliminary_decision_errors", 0) or 0
        ),
        "counterparty_dominated_count": int(
            discovery_diag.get("counterparty_dominated_count", 0) or 0
        ),
        "focal_dominated_count": int(
            discovery_diag.get("focal_dominated_count", 0) or 0
        ),
        "opportunities_suppressed": int(
            discovery_diag.get("opportunities_suppressed", 0) or 0
        ),
        "opportunities_market_match_only": int(
            discovery_diag.get("opportunities_market_match_only", 0) or 0
        ),
        "opportunities_attention_ready": int(
            discovery_diag.get("opportunities_attention_ready", 0) or 0
        ),
        "final_for_you_count": int(
            discovery_diag.get("for_you_selected", 0) or 0
        ),
        "changed_state_simulation_calls": int(
            discovery_diag.get("changed_state_simulation_calls_during_discovery", 0) or 0
        ),
        "admission_rejection_reasons": dict(
            search_diag.get("admission_rejection_reasons") or {}
        ),
        "timing_ms": dict(discovery_diag.get("timing_ms") or {}),
    }


def install_focused_opportunity_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    workspace_builder: WorkspaceBuilder,
    candidate_builder: CandidateBuilder,
    require_user: Any,
) -> None:
    """Expose a server-owned Market Focus endpoint without changing model authority."""

    @app.get("/api/opportunities/focused-workspace")
    def focused_workspace(
        posture: str = OwnerStrategicPosture.DEFAULT_CALCULATED.value,
        intent: str = "",
        value: str = "",
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        # Focus only needs the workspace shell/readiness/available-player context.
        # Building the generic 80-row Market discovery here duplicates economics
        # and family work before the submitted focused neighborhood is evaluated.
        base = workspace_builder(
            runtime,
            candidate_limit=0,
            bilateral_evaluation_limit=0,
        )
        if base.get("status") != "ready":
            return base
        league_state = runtime.league_state
        focal_team_id = runtime.selected_team_id
        if league_state is None or focal_team_id is None:
            raise HTTPException(status_code=409, detail="Market Focus requires a loaded league and managed team")
        values = runtime.value_evidence
        cardinal = {
            row.asset_id: row
            for row in (values.fsffl_cardinal_values if values is not None else ())
        }
        if not cardinal:
            raise HTTPException(status_code=409, detail="Market Focus requires current authoritative FSFFL Cardinal Market Value")

        browser = build_trade_center_browser_view(league_state, focal_team_id=focal_team_id)
        # Focused discovery now always constructs the submitted strategic neighborhood
        # directly; do not touch the generic structural catalog merely to submit a lens.
        canonical = None
        requested = _posture(posture)
        focused = build_focused_trade_candidates(
            runtime,
            browser,
            cardinal,
            canonical_candidates=canonical,
            requested_posture=requested,
            intent=intent,
            intent_value=value,
        )

        discovery = dict(base.get("trade_discovery") or {})
        limit = int(discovery.get("returned_count") or 80)
        if limit <= 0:
            limit = 80
        returned = list(focused[:limit])

        # Use the canonical evaluator directly so build_market_discovery can share
        # exact Value profiles, ownership resolution, Forecast floor evidence and
        # baseline lineups across the unchanged bounded preliminary-screen budget.
        focused_market_discovery = build_market_discovery(
            runtime,
            returned,
            evaluation_limit=DEFAULT_PRELIMINARY_DECISION_BUDGET,
            source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
            exact_target_constraint=(value if intent == "target" and value else None),
            intent=intent,
            intent_value=value,
            search_generation_diagnostics=dict(
                getattr(focused, "diagnostics", {}) or {}
            ),
            asset_index=owned_asset_index(browser),
        )
        focus_outcome = _focus_outcome(focused, focused_market_discovery)
        posture_meta = posture_payload(runtime, requested)
        _logger.info(
            "FSFFL Market focused outcome posture=%s effective=%s intent=%s value=%s "
            "status=%s reason=%s candidates=%d paths=%d prelim_runs=%d simulation_calls=%d",
            requested.value,
            posture_meta.get("effective_posture"),
            intent,
            value,
            focus_outcome["status"],
            focus_outcome["reason_code"],
            focus_outcome["candidate_count"],
            focus_outcome["candidate_path_count"],
            focus_outcome["preliminary_decision_runs"],
            focus_outcome["changed_state_simulation_calls"],
        )

        enriched = {
            _identity(path.get("representative_package") or {}):
                path.get("representative_package") or {}
            for path in focused_market_discovery.get("candidate_paths") or []
            if (path.get("representative_package") or {}).get(
                "bilateral_decision_evaluated"
            )
        }
        returned = [
            enriched.get(_identity(row), row)
            for row in returned
        ]
        discovery.update(
            {
                "candidate_count": len(focused),
                "returned_count": len(returned),
                "truncated": len(focused) > len(returned),
                "candidates": returned,
                "spotlights": build_trade_spotlights(returned),
                "posture_views": {},
                "active_posture": requested.value,
                "focus": {
                    "posture": requested.value,
                    "effective_posture": posture_meta.get("effective_posture"),
                    "intent": intent,
                    "value": value,
                    "server_owned": True,
                    "applied_before_candidate_limit": True,
                },
                "focus_outcome": focus_outcome,
            }
        )
        payload = dict(base)
        payload["search_posture"] = posture_meta
        payload["trade_discovery"] = discovery
        payload["market_discovery"] = focused_market_discovery
        payload["message"] = "Market Focus applied to the server-owned governed opportunity search."
        return payload
