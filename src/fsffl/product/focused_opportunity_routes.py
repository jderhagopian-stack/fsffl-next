from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping

from fastapi import Depends, FastAPI, HTTPException

from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .focused_opportunity_search import build_focused_trade_candidates
from .opportunity_posture import posture_payload
from .opportunity_spotlights import build_trade_spotlights
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext
from .trade_center_view import TradeCenterBrowserView, build_trade_center_browser_view


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
        base = workspace_builder(runtime)
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
            raise HTTPException(status_code=409, detail="Market Focus requires current authoritative FSFFL Value")

        browser = build_trade_center_browser_view(league_state, focal_team_id=focal_team_id)
        canonical = candidate_builder(runtime, browser, cardinal)
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
        base_rows = {
            _identity(row): row
            for row in (discovery.get("candidates") or [])
            if isinstance(row, dict)
        }
        returned = [base_rows.get(_identity(row), row) for row in focused[:limit]]
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
                    "intent": intent,
                    "value": value,
                    "server_owned": True,
                    "applied_before_candidate_limit": True,
                },
            }
        )
        payload = dict(base)
        payload["search_posture"] = posture_payload(runtime, requested)
        payload["trade_discovery"] = discovery
        payload["message"] = "Market Focus applied to the server-owned trade search."
        return payload
