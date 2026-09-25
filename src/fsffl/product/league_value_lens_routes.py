from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
    intrinsic_failure_payload,
    intrinsic_loading_payload,
)
from .league_value_lenses import build_league_value_lenses
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]


def install_league_value_lens_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    contract_loader: IntrinsicContractLoader,
    require_user,
    background_coordinator: ShapleyIntrinsicBackgroundCoordinator | None = None,
) -> None:
    """Expose Atlas-ready player lenses without creating team value authority."""

    @app.get("/api/league/value-lenses")
    def league_value_lenses(
        universe: str = "rostered",
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        if universe not in {"rostered", "all"}:
            raise HTTPException(
                status_code=422,
                detail="universe must be rostered or all",
            )
        if runtime.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting League value lenses",
            )

        intrinsic = None
        intrinsic_error = None
        if background_coordinator is not None:
            record = background_coordinator.request(runtime)
            if record.status in {
                IntrinsicBuildStatus.QUEUED,
                IntrinsicBuildStatus.RUNNING,
            }:
                loading = intrinsic_loading_payload(record)
                payload = build_league_value_lenses(
                    runtime,
                    None,
                    intrinsic_error=(
                        "Governed FSFFL Intrinsic is preparing server-side. "
                        "Broad Market remains independently usable."
                    ),
                    include_unrostered=universe == "all",
                )
                payload["status"] = (
                    "degraded"
                    if payload.get("broad_market", {}).get("status") == "ready"
                    else "building"
                )
                payload["fsffl_intrinsic"] = {
                    **dict(payload.get("fsffl_intrinsic") or {}),
                    "status": "building",
                    "reason": loading["message"],
                    "retry_after_ms": loading.get("retry_after_ms"),
                    "build_status": loading.get("build_status"),
                }
                payload["surface_readiness"] = {
                    "surface": "player_board",
                    "status": "building_optional",
                    "required_dependencies": ["canonical_state", "broad_market_value"],
                    "optional_dependencies": ["fsffl_intrinsic_all_player"],
                    "blockers": [],
                    "missing_optional": ["fsffl_intrinsic_all_player"],
                    "league_state_id": runtime.league_state.state_id,
                    "retry_after_ms": loading.get("retry_after_ms"),
                }
                return payload
            if record.status == IntrinsicBuildStatus.FAILED:
                intrinsic_error = str(intrinsic_failure_payload(record)["message"])
            else:
                intrinsic = record.contract
        else:
            try:
                intrinsic = contract_loader(runtime)
            except Exception as exc:
                # Broad Market remains independently usable. A failure in the Intrinsic
                # coordinate must not silently replace it or suppress the Market lens.
                intrinsic_error = (
                    "Governed FSFFL Intrinsic unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )

        payload = build_league_value_lenses(
            runtime,
            intrinsic,
            intrinsic_error=intrinsic_error,
            include_unrostered=universe == "all",
        )
        payload["surface_readiness"] = {
            "surface": "player_board",
            "status": (
                "ready"
                if payload.get("broad_market", {}).get("status") == "ready"
                and payload.get("fsffl_intrinsic", {}).get("status") != "unavailable"
                else (
                    "degraded"
                    if payload.get("broad_market", {}).get("status") == "ready"
                    else "blocked"
                )
            ),
            "required_dependencies": ["canonical_state", "broad_market_value"],
            "optional_dependencies": ["fsffl_intrinsic_all_player"],
            "blockers": (
                []
                if payload.get("broad_market", {}).get("status") == "ready"
                else ["broad_market_value"]
            ),
            "missing_optional": (
                []
                if payload.get("fsffl_intrinsic", {}).get("status") != "unavailable"
                else ["fsffl_intrinsic_all_player"]
            ),
            "league_state_id": runtime.league_state.state_id,
            "retry_after_ms": None,
        }
        return payload
