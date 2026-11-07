from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
    intrinsic_failure_payload,
    intrinsic_loading_payload,
)
from .intrinsic_market_discovery import build_intrinsic_market_discovery
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]


def install_intrinsic_market_discovery_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    contract_loader: IntrinsicContractLoader,
    require_user,
    background_coordinator: ShapleyIntrinsicBackgroundCoordinator | None = None,
) -> None:
    """Read prepared Intrinsic for discovery without starting a model build."""

    @app.get("/api/opportunities/value-disagreements")
    def value_disagreements(
        minimum_gap: float = Query(default=0.10, ge=0.0, le=1.0),
        limit: int = Query(default=24, ge=1, le=100),
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting value disagreement discovery",
            )
        if background_coordinator is not None:
            record = background_coordinator.current(runtime)
            if record is None:
                return JSONResponse(status_code=503, content={
                    "status": "refresh_required",
                    "capability": "current_intrinsic",
                    "league_state_id": runtime.league_state.state_id,
                    "reason": "Refresh league intelligence to prepare value disagreement evidence.",
                })
            if record.status in {
                IntrinsicBuildStatus.QUEUED,
                IntrinsicBuildStatus.RUNNING,
            }:
                payload = intrinsic_loading_payload(record)
                payload["message"] = (
                    "Governed Value Disagreement evidence is being prepared "
                    "server-side from the shared FSFFL Intrinsic artifact."
                )
                return JSONResponse(status_code=202, content=payload)
            if record.status == IntrinsicBuildStatus.FAILED:
                return JSONResponse(
                    status_code=503,
                    content=intrinsic_failure_payload(record),
                )
            intrinsic = record.contract
            if intrinsic is None:
                if record.contract_ref is not None:
                    return JSONResponse(status_code=202, content=intrinsic_loading_payload(record))
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "message": "Governed FSFFL Intrinsic completed without a usable contract.",
                    },
                )
        else:
            return JSONResponse(status_code=503, content={
                "status": "refresh_required",
                "capability": "current_intrinsic",
                "reason": "Value disagreement evidence must be prepared by the intelligence lifecycle.",
            })
        return build_intrinsic_market_discovery(
            runtime,
            intrinsic,
            minimum_percentile_gap=minimum_gap,
            limit=limit,
        )
