from __future__ import annotations

import logging
from time import monotonic

from fastapi import FastAPI, Request


_logger = logging.getLogger("fsffl.product.performance")
_TARGET_PATHS = frozenset(
    {
        "/api/product-context",
        "/api/my-team",
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center/browser",
        "/api/trade-center/analyze",
        "/api/trade-center/simulate",
        "/api/trade-center/frontier",
    }
)


def install_latency_observability(app: FastAPI) -> None:
    """Measure hosted request wall-clock without changing analytical execution.

    This instrumentation is deliberately outside model layers. It records only
    request path, method, response status and elapsed wall-clock. It does not alter
    inputs, cache policy, Simulation count, Search ordering, or authority.
    """

    @app.middleware("http")
    async def _fsffl_latency_observer(request: Request, call_next):
        path = request.url.path
        if path not in _TARGET_PATHS:
            return await call_next(request)
        started = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            _logger.exception(
                "FSFFL hosted request timing method=%s path=%s elapsed=%.3fs status=exception",
                request.method,
                path,
                monotonic() - started,
            )
            raise
        elapsed = monotonic() - started
        _logger.info(
            "FSFFL hosted request timing method=%s path=%s elapsed=%.3fs status=%s",
            request.method,
            path,
            elapsed,
            response.status_code,
        )
        response.headers["Server-Timing"] = f"fsffl;dur={elapsed * 1000:.1f}"
        return response
