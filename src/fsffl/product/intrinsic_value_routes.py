from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.value.intrinsic_runtime import build_current_intrinsic_values_v1
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


def install_intrinsic_value_v1_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
) -> None:
    """Expose legacy v1 plus the independent Fundamental Intrinsic successor."""

    def _context_and_paths(user_id: str):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Intrinsic Value")
        if context.forecast_evidence is None or not context.forecast_evidence.league_scored_forecasts:
            raise HTTPException(status_code=409, detail="Refresh authoritative Forecast before requesting Intrinsic Value")
        season_forecasts = context.forecast_evidence.league_scored_forecasts
        qb_career_states = build_qb_career_state_forecasts(
            context.league_state,
            season_forecasts=season_forecasts,
        )
        bounded_paths = build_non_qb_bounded_paths(
            context.league_state,
            season_forecasts=season_forecasts,
        )
        return context, season_forecasts, bounded_paths, qb_career_states

    @app.get("/api/value/intrinsic-v1")
    def intrinsic_value_v1(user_id: str = Depends(require_beta_user)):
        try:
            context, season_forecasts, bounded_paths, qb_career_states = _context_and_paths(user_id)
            result = build_current_intrinsic_values_v1(
                context.league_state,
                season_forecasts=season_forecasts,
                base_forecast_model_version=context.forecast_evidence.runtime_result.model_version,
                bounded_paths=bounded_paths,
                qb_career_states=qb_career_states,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Governed Intrinsic Value v1 unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }

    @app.get("/api/value/intrinsic-v2")
    def intrinsic_value_v2(user_id: str = Depends(require_beta_user)):
        try:
            context, season_forecasts, bounded_paths, qb_career_states = _context_and_paths(user_id)
            result = build_current_intrinsic_values_v2(
                context.league_state,
                season_forecasts=season_forecasts,
                base_forecast_model_version=context.forecast_evidence.runtime_result.model_version,
                bounded_paths=bounded_paths,
                qb_career_states=qb_career_states,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Fundamental Intrinsic Value unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "coordinate": "FSFFL Intrinsic Value",
            "definition": "team-independent fundamental long-term dynasty asset worth from football fundamentals",
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }
