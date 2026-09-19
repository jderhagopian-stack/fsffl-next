from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Query

from fsffl.forecast.in_season_orchestration import (
    build_governed_in_season_outlook,
    canonical_week_window,
)
from fsffl.forecast.in_season_runtime import build_in_season_forecasts
from fsffl.forecast.models import ForecastHorizon
from fsffl.forecast.preseason_baseline import (
    PRESEASON_BASELINE_MODEL_VERSION,
    build_runtime_from_preseason_baseline,
    preseason_scope_id,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.persistence.projection_history import PostgresProjectionHistoryStore
from fsffl.persistence.runtime_cache import (
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_preseason_forecast_baseline,
)

from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


def _baseline_season_forecasts(persistence_store: PersistenceStore, league_state):
    record = persistence_store.get_latest_reusable_artifact(
        artifact_kind=PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
        scope_kind=LEAGUE_SEASON_SCOPE_KIND,
        scope_id=preseason_scope_id(league_state),
        model_version=PRESEASON_BASELINE_MODEL_VERSION,
    )
    if record is None:
        return ()
    baseline = decode_preseason_forecast_baseline(dict(record.payload))
    runtime = build_runtime_from_preseason_baseline(league_state, baseline)
    return runtime.fantasy_point_forecasts


def _obs_payload(item) -> dict[str, object]:
    return {
        "player_id": item.player_id,
        "position": item.position.value,
        "horizon": item.horizon.value,
        "metric": item.metric.value,
        "mean": item.distribution.mean,
        "stddev": item.distribution.stddev,
        "period_start": item.period_start.isoformat(),
        "period_end": item.period_end.isoformat(),
        "as_of": item.as_of.isoformat(),
        "source": item.source,
        "model_version": item.model_version,
    }


def install_in_season_forecast_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    persistence_store: PersistenceStore | None,
    projection_history_store: PostgresProjectionHistoryStore | None,
) -> None:
    """Install authenticated diagnostic/API access to governed horizon-specific Forecasts."""

    @app.get("/api/forecast/in-season/outlook")
    def in_season_outlook(user_id: str = Depends(require_beta_user)):
        context = runtime_store.get(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Forecast")
        baseline = (
            _baseline_season_forecasts(persistence_store, state)
            if persistence_store is not None
            else ()
        )
        try:
            result = build_governed_in_season_outlook(
                state,
                preseason_season_forecasts=baseline,
                history_writer=projection_history_store,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Governed in-season Forecast unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "season": state.league.season,
            "completed_through_week": result.completed_through_week,
            "evidence_basis": result.evidence_basis,
            "current_ros_failure": result.current_failure,
            "forward_count": len(result.forward_forecasts),
            "season_outlook_count": len(result.season_outlook),
            "season_outlook": [_obs_payload(item) for item in result.season_outlook],
        }

    @app.get("/api/forecast/in-season/week/{week}")
    def in_season_week(week: int, user_id: str = Depends(require_beta_user)):
        context = runtime_store.get(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Forecast")
        try:
            period_start, period_end = canonical_week_window(state.league.season, week)
            result = build_in_season_forecasts(
                state,
                horizon=ForecastHorizon.WEEK,
                week=week,
                period_start=period_start,
                period_end=period_end,
                history_writer=projection_history_store,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Governed weekly Forecast unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "season": state.league.season,
            "week": week,
            "horizon": result.horizon.value,
            "successful_sources": list(result.successful_source_ids),
            "failed_sources": list(result.failed_sources),
            "forecast_count": len(result.fantasy_point_forecasts),
            "forecasts": [_obs_payload(item) for item in result.fantasy_point_forecasts],
        }

    @app.get("/api/forecast/history/{horizon}")
    def projection_history(
        horizon: ForecastHorizon,
        week: int | None = Query(default=None, ge=1, le=18),
        as_of: datetime | None = None,
        user_id: str = Depends(require_beta_user),
    ):
        context = runtime_store.get(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Forecast")
        if projection_history_store is None:
            raise HTTPException(status_code=503, detail="Projection history storage is not configured")
        if as_of is not None and as_of.tzinfo is None:
            raise HTTPException(status_code=422, detail="as_of must include a timezone")
        from fsffl.forecast.projection_history import ProjectionSelector

        try:
            selector = ProjectionSelector(
                season=state.league.season,
                horizon=horizon,
                week=week,
                as_of=as_of.astimezone(UTC) if as_of is not None else None,
            )
            revisions = projection_history_store.latest_revisions(selector)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "season": state.league.season,
            "horizon": horizon.value,
            "week": week,
            "as_of": as_of.isoformat() if as_of is not None else None,
            "revisions": [
                {
                    "provider": revision.snapshot.provider,
                    "effective_at": revision.snapshot.effective_at.isoformat(),
                    "retrieved_at": revision.snapshot.retrieved_at.isoformat(),
                    "content_fingerprint": revision.snapshot.content_fingerprint,
                    "observation_count": len(revision.observations),
                }
                for revision in revisions
            ],
        }
