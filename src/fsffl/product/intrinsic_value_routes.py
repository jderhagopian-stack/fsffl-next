from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.value.intrinsic_runtime import build_current_intrinsic_values_v1

from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


def install_intrinsic_value_v1_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
) -> None:
    """Expose legacy replacement-surplus as a deprecated compatibility coordinate.

    Canonical FSFFL Intrinsic is the Shapley contract at
    /api/value/intrinsic-shapley-v1. This endpoint remains temporarily available
    for compatibility/research inspection and is not a current product authority.
    """

    @app.get("/api/value/intrinsic-v1", deprecated=True)
    def legacy_replacement_surplus_v1(user_id: str = Depends(require_beta_user)):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting legacy replacement-surplus compatibility evidence")
        if context.forecast_evidence is None or not context.forecast_evidence.league_scored_forecasts:
            raise HTTPException(status_code=409, detail="Refresh authoritative Forecast before requesting legacy replacement-surplus compatibility evidence")
        try:
            qb_career_states = build_qb_career_state_forecasts(
                context.league_state,
                season_forecasts=context.forecast_evidence.league_scored_forecasts,
            )
            result = build_current_intrinsic_values_v1(
                context.league_state,
                season_forecasts=context.forecast_evidence.league_scored_forecasts,
                base_forecast_model_version=context.forecast_evidence.runtime_result.model_version,
                qb_career_states=qb_career_states,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Legacy replacement-surplus compatibility coordinate unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "authority_status": "legacy_replacement_surplus_compatibility_only",
            "canonical_intrinsic_endpoint": "/api/value/intrinsic-shapley-v1",
            "coordinate_semantics": "weighted_expected_fantasy_point_surplus_above_replacement",
            "product_consumer_status": "no_current_product_consumer",
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }
