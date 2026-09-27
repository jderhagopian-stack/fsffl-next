from __future__ import annotations

from contextlib import contextmanager
import ctypes
import gc
from dataclasses import dataclass
import logging
import os
import resource
from threading import Condition, RLock, get_ident
from time import monotonic
from typing import Iterator


_logger = logging.getLogger("fsffl.product.performance")
DEFAULT_MEMORY_LIMIT_BYTES = 536_870_900
DEFAULT_MEMORY_HEADROOM_RATIO = 0.20


def current_rss_bytes() -> int:
    """Best-effort current resident-set size for the hosted Linux process."""

    try:
        with open("/proc/self/statm", encoding="utf-8") as handle:
            resident_pages = int(handle.read().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        # ru_maxrss is a peak, not a current measure, but remains useful on
        # platforms where /proc is unavailable.
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value * 1024 if value < 10_000_000 else value


def process_peak_rss_bytes() -> int:
    """Return process peak RSS in bytes on Linux/macOS-compatible Python."""

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes. FSFFL hosted runtime is Linux.
    return value * 1024 if value < 10_000_000 else value


def release_unused_process_memory(*, label: str) -> dict[str, object]:
    """Best-effort reclaim of unreachable Python and glibc heap pages.

    This is execution/resource management only. It never mutates governed model
    results or persistence. Hosted Linux can retain freed allocator arenas in RSS;
    malloc_trim returns those free pages before the next serialized heavy phase so
    a replacement State does not inherit the prior phase's transient high-water set.
    """

    before = current_rss_bytes()
    collected = gc.collect()
    trimmed: bool | None = None
    trim_error: str | None = None
    try:
        libc = ctypes.CDLL(None)
        malloc_trim = getattr(libc, "malloc_trim", None)
        if malloc_trim is not None:
            malloc_trim.argtypes = [ctypes.c_size_t]
            malloc_trim.restype = ctypes.c_int
            trimmed = bool(malloc_trim(0))
    except Exception as exc:  # pragma: no cover - platform-specific fallback
        trim_error = f"{type(exc).__name__}: {exc}"
    after = current_rss_bytes()
    payload = {
        "label": label,
        "before_rss_bytes": before,
        "after_rss_bytes": after,
        "released_rss_bytes": max(0, before - after),
        "gc_collected": collected,
        "malloc_trim": trimmed,
        "trim_error": trim_error,
    }
    _logger.info(
        "FSFFL memory reclaim label=%s before=%s after=%s released=%s gc=%s malloc_trim=%s error=%s",
        label,
        before,
        after,
        payload["released_rss_bytes"],
        collected,
        trimmed,
        trim_error,
    )
    return payload


@dataclass(frozen=True)
class HeavyWorkSnapshot:
    active_kind: str | None
    active_key: str | None
    active_thread_id: int | None
    waiting_count: int
    max_waiting_observed: int
    acquisitions: int
    completions: int
    acquisitions_by_kind: tuple[tuple[str, int], ...]
    completions_by_kind: tuple[tuple[str, int], ...]
    current_rss_bytes: int
    peak_rss_bytes: int
    max_rss_observed_bytes: int
    memory_limit_bytes: int
    memory_budget_bytes: int
    within_memory_budget: bool


class HeavyWorkCoordinator:
    """Process-wide admission gate for memory-heavy private-beta work.

    Existing background coordinators continue to own their domain lifecycle and
    coalescing. This gate owns only process-level overlap: at most one admitted
    Forecast/Simulation/Value, Intrinsic/Shapley, or PI-history build may execute
    at once on the 512 MiB private-beta process.

    The queue is deliberately bounded. Callers are background workers; request
    handlers should enqueue/coalesce domain work and return loading state rather
    than wait on this gate directly.
    """

    def __init__(
        self,
        *,
        max_waiters: int = 8,
        memory_limit_bytes: int | None = None,
        headroom_ratio: float = DEFAULT_MEMORY_HEADROOM_RATIO,
    ) -> None:
        if max_waiters < 1:
            raise ValueError("max_waiters must be positive")
        if not 0 < headroom_ratio < 1:
            raise ValueError("headroom_ratio must be between 0 and 1")
        configured_limit = (
            int(os.getenv("FSFFL_MEMORY_LIMIT_BYTES", str(DEFAULT_MEMORY_LIMIT_BYTES)))
            if memory_limit_bytes is None
            else int(memory_limit_bytes)
        )
        if configured_limit <= 0:
            raise ValueError("memory_limit_bytes must be positive")
        self._max_waiters = int(max_waiters)
        self._memory_limit_bytes = configured_limit
        self._memory_budget_bytes = int(
            configured_limit * (1.0 - float(headroom_ratio))
        )
        self._condition = Condition(RLock())
        self._active_kind: str | None = None
        self._active_key: str | None = None
        self._active_thread_id: int | None = None
        self._waiting_count = 0
        self._max_waiting_observed = 0
        self._acquisitions = 0
        self._completions = 0
        self._acquisitions_by_kind: dict[str, int] = {}
        self._completions_by_kind: dict[str, int] = {}
        self._max_rss_observed_bytes = current_rss_bytes()

    @property
    def memory_budget_bytes(self) -> int:
        return self._memory_budget_bytes

    @contextmanager
    def claim(
        self,
        *,
        kind: str,
        key: str,
        timeout_seconds: float | None = None,
    ) -> Iterator[None]:
        kind = str(kind).strip()
        key = str(key).strip()
        if not kind or not key:
            raise ValueError("heavy-work kind and key cannot be blank")

        deadline = (
            None
            if timeout_seconds is None
            else monotonic() + max(0.01, float(timeout_seconds))
        )
        started_wait = monotonic()
        with self._condition:
            if self._active_thread_id == get_ident():
                raise RuntimeError(
                    "nested heavy-work claims are not allowed; compose heavy phases "
                    "under one domain claim instead"
                )
            if self._active_kind is not None:
                if self._waiting_count >= self._max_waiters:
                    raise RuntimeError(
                        "heavy-work queue is full; retry after the active governed build"
                    )
                self._waiting_count += 1
                self._max_waiting_observed = max(
                    self._max_waiting_observed,
                    self._waiting_count,
                )
                try:
                    while self._active_kind is not None:
                        if deadline is None:
                            self._condition.wait()
                            continue
                        remaining = deadline - monotonic()
                        if remaining <= 0:
                            raise TimeoutError(
                                f"timed out waiting for heavy-work admission: {kind}"
                            )
                        self._condition.wait(timeout=remaining)
                finally:
                    self._waiting_count -= 1

            self._active_kind = kind
            self._active_key = key
            self._active_thread_id = get_ident()
            self._acquisitions += 1
            self._acquisitions_by_kind[kind] = (
                self._acquisitions_by_kind.get(kind, 0) + 1
            )
            before_rss = current_rss_bytes()
            self._max_rss_observed_bytes = max(
                self._max_rss_observed_bytes,
                before_rss,
            )
            _logger.info(
                "FSFFL heavy-work admitted kind=%s key=%s waited=%.3fs rss=%s budget=%s",
                kind,
                key,
                max(0.0, monotonic() - started_wait),
                before_rss,
                self._memory_budget_bytes,
            )

        try:
            yield
        finally:
            after_rss = current_rss_bytes()
            peak_rss = process_peak_rss_bytes()
            with self._condition:
                self._max_rss_observed_bytes = max(
                    self._max_rss_observed_bytes,
                    after_rss,
                    peak_rss,
                )
                _logger.info(
                    "FSFFL heavy-work released kind=%s key=%s rss=%s peak_rss=%s budget=%s",
                    kind,
                    key,
                    after_rss,
                    peak_rss,
                    self._memory_budget_bytes,
                )
                self._active_kind = None
                self._active_key = None
                self._active_thread_id = None
                self._completions += 1
                self._completions_by_kind[kind] = (
                    self._completions_by_kind.get(kind, 0) + 1
                )
                self._condition.notify_all()

    def snapshot(self) -> HeavyWorkSnapshot:
        current = current_rss_bytes()
        peak = process_peak_rss_bytes()
        with self._condition:
            observed = max(self._max_rss_observed_bytes, current, peak)
            self._max_rss_observed_bytes = observed
            return HeavyWorkSnapshot(
                active_kind=self._active_kind,
                active_key=self._active_key,
                active_thread_id=self._active_thread_id,
                waiting_count=self._waiting_count,
                max_waiting_observed=self._max_waiting_observed,
                acquisitions=self._acquisitions,
                completions=self._completions,
                acquisitions_by_kind=tuple(sorted(self._acquisitions_by_kind.items())),
                completions_by_kind=tuple(sorted(self._completions_by_kind.items())),
                current_rss_bytes=current,
                peak_rss_bytes=peak,
                max_rss_observed_bytes=observed,
                memory_limit_bytes=self._memory_limit_bytes,
                memory_budget_bytes=self._memory_budget_bytes,
                within_memory_budget=observed <= self._memory_budget_bytes,
            )
