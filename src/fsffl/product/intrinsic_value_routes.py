from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.state.models import Position
from fsffl.value.intrinsic_display import (
    INTRINSIC_DYNASTY_DISPLAY_SCALE,
    intrinsic_dynasty_display_value,
    intrinsic_population_percentiles,
)
from fsffl.value.intrinsic_runtime import build_current_intrinsic_values_v1

from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


def _roster_player_ids(context) -> tuple[str, ...]:
    state = context.league_state
    if state is None:
        return ()
    player_by_id = {player.player_id: player for player in state.players}
    supported = {Position.QB, Position.RB, Position.WR, Position.TE}
    return tuple(
        sorted(
            {
                entry.player_id
                for team_state in state.team_states
                for entry in team_state.roster
                if entry.player_id in player_by_id
                and player_by_id[entry.player_id].position in supported
            }
        )
    )


def _forecast_player_ids(context) -> set[str]:
    evidence = context.forecast_evidence
    if evidence is None:
        return set()
    return {
        observation.player_id
        for observation in evidence.league_scored_forecasts
        if observation.horizon == ForecastHorizon.SEASON
        and observation.metric == ForecastMetric.FANTASY_POINTS
    }


def install_intrinsic_value_v1_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
) -> None:
    """Expose raw Intrinsic v1 plus a market-independent dynasty display coordinate."""

    @app.get("/api/value/intrinsic-v1")
    def intrinsic_value_v1(user_id: str = Depends(require_beta_user)):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Intrinsic Value")
        if context.forecast_evidence is None or not context.forecast_evidence.league_scored_forecasts:
            raise HTTPException(status_code=409, detail="Refresh authoritative Forecast before requesting Intrinsic Value")
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
                detail=f"Governed Intrinsic Value v1 unavailable: {type(exc).__name__}: {exc}",
            ) from exc

        estimate_by_id = {estimate.player_id: estimate for estimate in result.estimates}
        percentiles = intrinsic_population_percentiles(result.estimates)
        forecast_player_ids = _forecast_player_ids(context)
        player_rows: list[dict[str, object]] = []
        for player_id in _roster_player_ids(context):
            estimate = estimate_by_id.get(player_id)
            if estimate is None:
                has_forecast = player_id in forecast_player_ids
                player_rows.append(
                    {
                        "player_id": player_id,
                        "availability": "unavailable",
                        "evidence_state": "unavailable",
                        "reason": (
                            "Intrinsic estimate unavailable because governed replacement context could not be constructed."
                            if has_forecast
                            else "Authoritative season Forecast evidence is incomplete for this player."
                        ),
                        "raw_intrinsic_value": None,
                        "intrinsic_dynasty_value": None,
                        "percentile": None,
                        "confidence": None,
                        "estimate": None,
                    }
                )
                continue

            valid_zero = estimate.value == 0
            player_rows.append(
                {
                    "player_id": player_id,
                    "availability": "available",
                    "evidence_state": (
                        "low_evidence" if estimate.confidence.value == "low" else "available"
                    ),
                    "reason": (
                        "Valid zero surplus: projected production does not exceed modeled replacement across the weighted horizons."
                        if valid_zero
                        else None
                    ),
                    "raw_intrinsic_value": estimate.value,
                    "intrinsic_dynasty_value": intrinsic_dynasty_display_value(estimate.value),
                    "percentile": percentiles.get(player_id),
                    "confidence": estimate.confidence.value,
                    "estimate": estimate.model_dump(mode="json"),
                }
            )

        return {
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "raw_scale": {
                "scale_id": "fsffl_intrinsic_surplus",
                "version": "1",
                "unit_label": "weighted expected fantasy-point surplus above replacement",
            },
            "display_scale": INTRINSIC_DYNASTY_DISPLAY_SCALE.model_dump(mode="json"),
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "players": player_rows,
            # Backward-compatible raw estimates remain available for governed
            # internal/downstream consumers. Presentation should prefer `players`.
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }
