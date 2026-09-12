from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .frontier_runtime import build_negotiation_frontier
from .runtime import PrivateBetaRuntimeStore
from .webapp import AnalyzeTradeRequest, _proposal_from_request


_QUICK_FRONTIER_EVALUATIONS = 4


def install_quick_frontier_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    require_user,
) -> None:
    """Install the first interactive counter-search slice.

    The quick route uses the same NEXT-6 frontier and NEXT-5 bilateral evaluation as
    the full frontier, but returns after a small adjacent slice so an interactive
    request does not synchronously evaluate the entire 24-point frontier. The full
    endpoint remains available for explicit deeper expansion.
    """

    @app.post("/api/trade-center/frontier/quick")
    def explore_trade_frontier_quick(
        request: AnalyzeTradeRequest,
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        try:
            proposal = _proposal_from_request(
                runtime,
                request,
                draft_prefix="product-frontier-quick",
            )
            result = build_negotiation_frontier(
                runtime,
                proposal,
                focal_team_id=runtime.selected_team_id,
                max_depth=1,
                max_evaluations=_QUICK_FRONTIER_EVALUATIONS,
            )
            return {
                **result,
                "interactive_slice": "quick",
                "deeper_search_available": not bool(result.get("exhausted")),
                "full_frontier_max_evaluations": 24,
            }
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
