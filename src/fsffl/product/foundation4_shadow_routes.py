from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .foundation4_career_forward_runtime import Foundation4CareerForwardShadowLoader
from .intrinsic_background import IntrinsicBuildStatus, ShapleyIntrinsicBackgroundCoordinator
from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


FOUNDATION4_CAREER_FORWARD_ENDPOINT = "/api/value/long-term-intrinsic-shadow-v1"
FOUNDATION4_Y4_Y7_ENDPOINT = "/api/value/long-horizon-y4-y7-shadow-v1"


def _building_payload(record) -> dict[str, object]:
    return {
        "status": "building",
        "shadow": True,
        "build_status": record.status.value,
        "league_state_id": record.league_state_id,
        "input_fingerprint": record.intrinsic_input_fingerprint,
        "current_intrinsic_replaced": False,
    }


def install_foundation4_shadow_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    loader: Foundation4CareerForwardShadowLoader,
    coordinator: ShapleyIntrinsicBackgroundCoordinator,
) -> None:
    def _record(user_id: str):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting Long-Term Intrinsic shadow",
            )
        return context, coordinator.request(context)

    @app.get(FOUNDATION4_CAREER_FORWARD_ENDPOINT)
    def career_forward_shadow(user_id: str = Depends(require_beta_user)):
        _context, record = _record(user_id)
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            return JSONResponse(status_code=202, content=_building_payload(record))
        if record.status == IntrinsicBuildStatus.FAILED:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "shadow": True,
                    "reason": record.error or "Foundation 4 shadow build failed",
                    "current_intrinsic_replaced": False,
                },
            )
        if record.contract is None:
            raise HTTPException(
                status_code=503,
                detail="Foundation 4 lifecycle completed without a holistic contract",
            )
        return record.contract.model_dump(mode="json")

    @app.get(FOUNDATION4_Y4_Y7_ENDPOINT)
    def y4_y7_shadow(user_id: str = Depends(require_beta_user)):
        context, record = _record(user_id)
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            return JSONResponse(status_code=202, content=_building_payload(record))
        if record.status == IntrinsicBuildStatus.FAILED:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "shadow": True,
                    "reason": record.error or "Foundation 4 shadow build failed",
                    "current_intrinsic_replaced": False,
                },
            )
        component = loader.current_component(context)
        if component is None:
            raise HTTPException(
                status_code=503,
                detail="Foundation 4 Y4-Y7 shadow component is not available",
            )
        return component.model_dump(mode="json")
