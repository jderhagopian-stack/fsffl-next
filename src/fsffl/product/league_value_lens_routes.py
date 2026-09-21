from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

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
    def league_value_lenses(user_id: str = Depends(require_user)) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
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
                payload = intrinsic_loading_payload(record)
                payload["message"] = (
                    "League value lenses are loading the shared governed "
                    "FSFFL Intrinsic artifact server-side."
                )
                return JSONResponse(status_code=202, content=payload)
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

        return build_league_value_lenses(
            runtime,
            intrinsic,
            intrinsic_error=intrinsic_error,
        )
