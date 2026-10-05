from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fsffl.analytics.dynasty_position_room import build_dynasty_position_rooms
from .foundation4_career_forward_runtime import Foundation4CareerForwardShadowLoader
from .intrinsic_background import IntrinsicBuildStatus, ShapleyIntrinsicBackgroundCoordinator
from .presentation_continuity import LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE
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
    presentation_payload_loader=None,
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
        payload = record.contract.model_dump(mode="json")
        payload["league_state_id"] = record.league_state_id
        return payload

    @app.get("/api/league/dynasty-position-rooms")
    def dynasty_position_rooms(user_id: str = Depends(require_beta_user)):
        """Return governed positional rooms, preferring the matching published surface."""

        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if presentation_payload_loader is not None:
            persisted = presentation_payload_loader(
                user_id,
                context,
                LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
            )
            if persisted is not None:
                return persisted

        # Only compose from live Foundation 4 evidence when no verified publication
        # surface can serve this runtime. A last-good read never starts a new build.
        context, record = _record(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            return _building_payload(record)
        if record.status == IntrinsicBuildStatus.FAILED or record.contract is None:
            return {
                "status": "unavailable",
                "shadow": True,
                "league_state_id": state.state_id,
                "reason": record.error or "Holistic career-forward evidence is unavailable",
            }
        if record.league_state_id != state.state_id:
            return {
                "status": "unavailable",
                "league_state_id": state.state_id,
                "reason": "Career-forward evidence does not match the current league State",
            }
        rooms = build_dynasty_position_rooms(
            state,
            career_forward=record.contract,
            evidence_state_id=record.league_state_id,
        )
        return {
            "status": "ready",
            "league_state_id": state.state_id,
            "input_fingerprint": record.intrinsic_input_fingerprint,
            "model_version": rooms[0].model_version if rooms else None,
            "rooms": [row.model_dump(mode="json") for row in rooms],
        }

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
