from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException

from fsffl.persistence import PersistenceStore, UserPerceivedLatencyRecord, utc_now
from fsffl.state.models import FrozenModel

from .webapp import require_beta_user


_logger = logging.getLogger("fsffl.product.performance")
_ALLOWED_OPERATIONS = {
    "first_connect_ready",
    "restore_ready",
    "opportunities_ready",
    "explicit_deep_analysis",
}
_ALLOWED_OUTCOMES = {"success", "failed"}


class UserPerceivedLatencyEvent(FrozenModel):
    operation: str
    elapsed_ms: float
    outcome: str = "success"
    detail: str | None = None


def install_phase1_latency_routes(
    application: FastAPI,
    *,
    persistence_store: PersistenceStore | None = None,
) -> None:
    """Record Phase 1/2 exit-gate timings without affecting model truth or runtime work."""

    @application.post("/api/performance/latency")
    def record_phase1_latency(
        event: UserPerceivedLatencyEvent,
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        if event.operation not in _ALLOWED_OPERATIONS:
            raise HTTPException(status_code=422, detail="Unsupported latency operation")
        if event.outcome not in _ALLOWED_OUTCOMES:
            raise HTTPException(status_code=422, detail="Unsupported latency outcome")
        if event.elapsed_ms < 0 or event.elapsed_ms > 300_000:
            raise HTTPException(status_code=422, detail="Latency measurement is outside the supported range")
        detail = (event.detail or "")[:160]
        _logger.info(
            "FSFFL user-perceived latency operation=%s elapsed_ms=%.1f outcome=%s detail=%s user=%s",
            event.operation,
            event.elapsed_ms,
            event.outcome,
            detail,
            user_id,
        )
        if persistence_store is not None:
            try:
                persistence_store.append_user_perceived_latency(
                    UserPerceivedLatencyRecord(
                        user_id=user_id,
                        operation=event.operation,
                        elapsed_ms=event.elapsed_ms,
                        outcome=event.outcome,
                        detail=detail or None,
                        observed_at=utc_now(),
                    )
                )
            except Exception as exc:
                # Observability storage must never break the user request or become
                # a runtime/model dependency.
                _logger.warning(
                    "FSFFL latency persistence failed operation=%s user=%s error=%s",
                    event.operation,
                    user_id,
                    exc,
                )
        return {"status": "recorded", "operation": event.operation}
