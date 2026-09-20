from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Query

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .intrinsic_market_discovery import build_intrinsic_market_discovery
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]


def install_intrinsic_market_discovery_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    contract_loader: IntrinsicContractLoader,
    require_user,
) -> None:
    """Expose a lazy discovery lens without changing Search or Value authority."""

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
        try:
            intrinsic = contract_loader(runtime)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Governed Intrinsic disagreement evidence unavailable: "
                    f"{type(exc).__name__}: {exc}"
                ),
            ) from exc
        return build_intrinsic_market_discovery(
            runtime,
            intrinsic,
            minimum_percentile_gap=minimum_gap,
            limit=limit,
        )
