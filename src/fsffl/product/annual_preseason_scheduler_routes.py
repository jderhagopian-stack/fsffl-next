from __future__ import annotations

import hmac
import logging
import os

from fastapi import FastAPI, Header, HTTPException, status

from fsffl.forecast.annual_preseason_scheduler import (
    AnnualPreseasonSchedulerResult,
    run_annual_preseason_scheduler_tick,
)
from fsffl.persistence.contracts import PersistenceStore


_logger = logging.getLogger("fsffl.product.annual_preseason_scheduler")


def _scheduler_token() -> str:
    return os.getenv("FSFFL_SCHEDULER_TOKEN", "").strip()


def _as_payload(result: AnnualPreseasonSchedulerResult) -> dict[str, object]:
    return {
        "season": result.season,
        "attempted": result.attempted,
        "outcome": result.outcome,
        "detail": result.detail,
    }


def install_annual_preseason_scheduler_route(
    app: FastAPI,
    *,
    persistence_store: PersistenceStore | None,
) -> None:
    """Install the token-protected operational entry point for annual capture."""

    @app.post("/internal/annual-preseason-snapshot/capture")
    def annual_preseason_snapshot_capture(
        scheduler_token: str | None = Header(
            default=None,
            alias="X-FSFFL-Scheduler-Token",
        ),
    ) -> dict[str, object]:
        expected = _scheduler_token()
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="annual preseason scheduler token is not configured",
            )
        if not scheduler_token or not hmac.compare_digest(scheduler_token, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid annual preseason scheduler token",
            )

        _logger.info("annual preseason snapshot scheduler attempted")
        result = run_annual_preseason_scheduler_tick(persistence_store)
        _logger.info(
            "annual preseason snapshot scheduler outcome=%s season=%s detail=%s",
            result.outcome,
            result.season,
            result.detail,
        )
        if result.outcome == "failed-with-reason":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_as_payload(result),
            )
        return _as_payload(result)
