from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from fsffl.persistence import (
    PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND,
    PROVISIONAL_K_DST_SCOPE_KIND,
    PersistenceStore,
    decode_provisional_k_dst_forecast,
    provisional_k_dst_scope_id,
)
from fsffl.forecast.k_dst_provisional import PROVISIONAL_K_DST_MODEL_VERSION

from .provisional_k_dst_presentation import build_provisional_k_dst_presentation
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


class ProvisionalKDstLookupError(ValueError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def load_provisional_k_dst_presentation(
    runtime: UserRuntimeContext,
    *,
    persistence_store: PersistenceStore | None,
    subject_key: str,
) -> dict[str, object]:
    """Load only an exact-state provisional artifact for Presentation/API exposure."""

    subject_key = subject_key.strip()
    if not subject_key:
        raise ProvisionalKDstLookupError("subject_key cannot be blank", status_code=422)
    state = runtime.league_state
    if state is None:
        raise ProvisionalKDstLookupError(
            "Connect a league before requesting provisional K/DST Forecast",
            status_code=409,
        )
    if state.league.season != 2026:
        raise ProvisionalKDstLookupError(
            "Provisional K/DST Forecast is authorized only for season 2026",
            status_code=404,
        )
    if persistence_store is None:
        raise ProvisionalKDstLookupError(
            "Provisional K/DST persistence is unavailable",
            status_code=503,
        )

    record = persistence_store.get_latest_reusable_artifact(
        artifact_kind=PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND,
        scope_kind=PROVISIONAL_K_DST_SCOPE_KIND,
        scope_id=provisional_k_dst_scope_id(
            league_state_id=state.state_id,
            subject_key=subject_key,
        ),
        model_version=PROVISIONAL_K_DST_MODEL_VERSION,
    )
    if record is None:
        raise ProvisionalKDstLookupError(
            "No provisional K/DST Forecast exists for this exact league state and subject",
            status_code=404,
        )

    try:
        forecast = decode_provisional_k_dst_forecast(dict(record.payload))
    except (TypeError, ValueError) as exc:
        raise ProvisionalKDstLookupError(
            "Stored provisional K/DST Forecast failed contract validation",
            status_code=409,
        ) from exc

    if (
        forecast.league_id != state.league.league_id
        or forecast.league_state_id != state.state_id
        or forecast.season != state.league.season
        or forecast.subject_key != subject_key
    ):
        raise ProvisionalKDstLookupError(
            "Stored provisional K/DST Forecast does not match the active league state",
            status_code=409,
        )
    return build_provisional_k_dst_presentation(forecast)


def install_provisional_k_dst_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    persistence_store: PersistenceStore | None,
    require_user,
) -> None:
    @app.get("/api/forecast/provisional-k-dst")
    def provisional_k_dst_forecast(
        subject_key: str = Query(..., min_length=1),
        user_id: str = Depends(require_user),
    ):
        runtime = runtime_store.get(user_id)
        try:
            return load_provisional_k_dst_presentation(
                runtime,
                persistence_store=persistence_store,
                subject_key=subject_key,
            )
        except ProvisionalKDstLookupError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
