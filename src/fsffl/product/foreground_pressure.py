from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import RLock
from time import monotonic, sleep


_logger = logging.getLogger("fsffl.product.performance")


@dataclass(frozen=True)
class ForegroundPressureSnapshot:
    active_requests: int
    recent_slow_until: float
    last_latency_seconds: float | None


class ForegroundPressure:
    """Cheap process-local signal for foreground-first background pacing.

    The policy is capacity-agnostic: background work yields only while interactive
    demand is active or immediately after a slow interactive request. On stronger
    infrastructure with no foreground pressure, background work runs without a
    permanent throttle.
    """

    def __init__(
        self,
        *,
        slow_request_seconds: float = 0.75,
        recovery_seconds: float = 0.75,
        yield_seconds: float = 0.005,
        yield_budget_seconds: float = 0.05,
        yield_window_seconds: float = 1.0,
    ) -> None:
        self._lock = RLock()
        self._active_requests = 0
        self._recent_slow_until = 0.0
        self._last_latency_seconds: float | None = None
        self._slow_request_seconds = max(0.0, slow_request_seconds)
        self._recovery_seconds = max(0.0, recovery_seconds)
        self._yield_seconds = max(0.0, yield_seconds)
        self._yield_budget_seconds = max(0.0, yield_budget_seconds)
        self._yield_window_seconds = max(0.001, yield_window_seconds)
        self._yield_window_started = monotonic()
        self._yielded_in_window = 0.0

    def begin_request(self) -> None:
        with self._lock:
            self._active_requests += 1

    def end_request(self, *, elapsed_seconds: float, interactive: bool = True) -> None:
        now = monotonic()
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            if interactive:
                self._last_latency_seconds = max(0.0, elapsed_seconds)
                if elapsed_seconds >= self._slow_request_seconds:
                    self._recent_slow_until = max(
                        self._recent_slow_until,
                        now + self._recovery_seconds,
                    )

    def snapshot(self) -> ForegroundPressureSnapshot:
        with self._lock:
            return ForegroundPressureSnapshot(
                active_requests=self._active_requests,
                recent_slow_until=self._recent_slow_until,
                last_latency_seconds=self._last_latency_seconds,
            )

    def should_yield(self) -> bool:
        snapshot = self.snapshot()
        return snapshot.active_requests > 0 or monotonic() < snapshot.recent_slow_until

    def cooperative_yield(self) -> bool:
        """Yield briefly under load, with a strict wall-time budget per window.

        Interactive requests retain priority, but no sustained request/polling load
        can consume more than the configured background-yield budget in each window.
        """
        if not self.should_yield():
            return False
        now = monotonic()
        with self._lock:
            if now - self._yield_window_started >= self._yield_window_seconds:
                self._yield_window_started = now
                self._yielded_in_window = 0.0
            remaining = self._yield_budget_seconds - self._yielded_in_window
            if remaining <= 0.0:
                return False
            requested = min(self._yield_seconds, remaining)
            if requested <= 0.0:
                return False
            self._yielded_in_window += requested
            window_started = self._yield_window_started
        sleep_started = monotonic()
        sleep(requested)
        actual = max(requested, monotonic() - sleep_started)
        with self._lock:
            if self._yield_window_started == window_started:
                self._yielded_in_window += actual - requested
        return True


foreground_pressure = ForegroundPressure()


def install_foreground_pressure(app) -> None:
    """Install hosted request accounting without changing route/model authority."""

    @app.middleware("http")
    async def _track_foreground_pressure(request, call_next):
        path = request.url.path
        # Starting/polling jobs and reading lightweight readiness are orchestration,
        # not interactive product demand. Exclude them so status polling cannot pace
        # Simulation; a bounded yield budget also protects progress under real reads.
        interactive = not (
            path.startswith("/api/intelligence/jobs")
            or path == "/api/intelligence/status"
        )
        started = monotonic()
        if interactive:
            foreground_pressure.begin_request()
        try:
            return await call_next(request)
        finally:
            if interactive:
                elapsed = max(0.0, monotonic() - started)
                foreground_pressure.end_request(
                    elapsed_seconds=elapsed,
                    interactive=True,
                )
                if elapsed >= 1.0:
                    _logger.info(
                        "FSFFL foreground pressure path=%s elapsed=%.3fs active_after=%s",
                        path,
                        elapsed,
                        foreground_pressure.snapshot().active_requests,
                    )
