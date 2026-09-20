from __future__ import annotations

from typing import Callable

from fastapi import Depends, FastAPI, HTTPException

from fsffl.value.shapley_intrinsic_contract import (
    SHAPLEY_INTRINSIC_ENDPOINT_PATH,
    ShapleyIntrinsicContract,
    build_unavailable_shapley_intrinsic_contract,
)

from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext
from .webapp import require_beta_user


ShapleyIntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract | None]


def install_shapley_intrinsic_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    contract_loader: ShapleyIntrinsicContractLoader | None = None,
) -> None:
    """Expose the versioned Shapley-native Intrinsic contract.

    This route does not reinterpret `/api/value/intrinsic-v1` and does not feed
    Team Utility, Decision, Search, or presentation. Until authoritative
    completed-source I1 facts are attached, it returns an explicit unavailable
    contract instead of inventing provider facts or reusing legacy surplus fields.
    """

    @app.get(SHAPLEY_INTRINSIC_ENDPOINT_PATH)
    def intrinsic_shapley_v1(user_id: str = Depends(require_beta_user)):
        context = runtime_store.get(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Shapley Intrinsic Value")

        if contract_loader is None:
            contract = None
        else:
            try:
                contract = contract_loader(context)
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Governed Shapley Intrinsic contract unavailable: {type(exc).__name__}: {exc}",
                ) from exc

        if contract is None:
            contract = build_unavailable_shapley_intrinsic_contract(
                evaluation_season=state.league.season,
                reason=(
                    "Authoritative completed-source I1 canonical facts are not attached to the product runtime. "
                    "The Shapley-native API contract is active but fail-closed until governed evidence is supplied."
                ),
                missing_required_fact_families=("completed_source_i1_facts",),
            )
        return contract.model_dump(mode="json")
