"""Bounded, privacy-safe EVENT / REQUEST / BODY-BYTES provider telemetry.

This is observational only: it never initiates a request, stores a response, or
changes the provider's normalization, refresh policy, or persistence contract.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from hashlib import sha256
import json
import logging
import os
from threading import Lock
from time import perf_counter
from typing import Any, Callable
from urllib.parse import urlsplit
from uuid import uuid4

_log = logging.getLogger("fsffl.provider_acquisition")
_active: ContextVar["_Event | None"] = ContextVar("fsffl_acquisition_event", default=None)
_attempt: ContextVar[dict[str, Any] | None] = ContextVar("fsffl_request_attempt", default=None)
_cause: ContextVar[str | None] = ContextVar("fsffl_acquisition_cause", default=None)
_CAUSES = frozenset({
    "explicit_refresh", "saved_session_probe", "connection",
    "governed_recovery", "independent_current", "scheduled_authority", "unknown",
})


def _enabled() -> bool:
    return os.getenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1") == "1"


@contextmanager
def acquisition_cause(cause: str):
    """Explicit lifecycle signal; never infer intent from an HTTP URL."""
    token = _cause.set(cause if cause in _CAUSES else "unknown")
    try:
        yield
    finally:
        _cause.reset(token)


def _family(provider: str, url: str) -> str:
    """Fixed, low-cardinality families; never return a raw URL or identifier."""
    path = urlsplit(url).path
    if provider == "sleeper":
        if path.endswith("/players/nfl"):
            return "player_catalog"
        if path.endswith("/state/nfl"):
            return "nfl_state"
        if "/schedule/nfl/regular/" in path:
            return "nfl_schedule"
        if "/stats/nfl/regular/" in path:
            after = path.split("/stats/nfl/regular/", 1)[1]
            return "weekly_actuals" if "/" in after else "season_actuals"
        for suffix, family in (
            ("/rosters", "rosters"), ("/users", "users"),
            ("/traded_picks", "traded_picks"),
        ):
            if path.endswith(suffix):
                return family
        if "/matchups/" in path:
            return "matchups"
        if "/league/" in path:
            return "league_metadata"
        return "other"
    if provider in {"cbs", "razzball", "fftoday", "nfl_fantasy"}:
        return "projection_page"
    return "other"


@dataclass
class _Event:
    provider: str
    horizon: str
    season: int | None
    week: int | None
    cause: str
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])
    started: float = field(default_factory=perf_counter)
    lock: Lock = field(default_factory=Lock)
    requests: int = 0
    succeeded: int = 0
    failed: int = 0
    retries: int = 0
    body_bytes: int = 0
    unknown_bytes: int = 0
    elapsed_ms: list[float] = field(default_factory=list)
    families: dict[str, int] = field(default_factory=dict)
    family_bytes: dict[str, int] = field(default_factory=dict)
    family_unknown: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)
    targets: set[str] = field(default_factory=set)

    def record(
        self, *, url: str, elapsed_ms: float, body_bytes: int | None,
        failed: bool, status_class: str,
    ) -> None:
        family = _family(self.provider, url)
        # Identifiers exist only as non-logged in-memory digests during this event.
        digest = sha256(url.encode("utf-8")).hexdigest()
        with self.lock:
            self.requests += 1
            self.failed += int(failed)
            self.statuses[status_class] = self.statuses.get(status_class, 0) + 1
            self.succeeded += int(not failed)
            self.body_bytes += body_bytes or 0
            self.unknown_bytes += int(body_bytes is None)
            self.family_bytes[family] = self.family_bytes.get(family, 0) + (body_bytes or 0)
            self.family_unknown[family] = self.family_unknown.get(family, 0) + int(body_bytes is None)
            self.retries += int(digest in self.targets)
            if len(self.targets) < 128:
                self.targets.add(digest)
            if len(self.elapsed_ms) < 128:
                self.elapsed_ms.append(round(elapsed_ms, 2))
            if family in self.families or len(self.families) < 12:
                self.families[family] = self.families.get(family, 0) + 1
            else:
                self.families["other"] = self.families.get("other", 0) + 1


def response_body_read(response: Any) -> bytes:
    """Exactly the original one read; measure actual body bytes before decoding."""
    data = response.read()
    sample = _attempt.get()
    if sample is not None:
        if isinstance(data, bytes):
            sample["body_bytes"] = len(data)
        status = getattr(response, "status", None)
        if isinstance(status, int):
            sample["status_class"] = str(status // 100) + "xx"
    return data


def observed_getter(getter: Callable[[str], Any], provider: str) -> Callable[[str], Any]:
    """Wrap the existing injectable getter; no extra network operation."""
    @wraps(getter)
    def get(url: str) -> Any:
        event = _active.get()
        if event is None or event.provider != provider:
            return getter(url)
        sample: dict[str, Any] = {"body_bytes": None, "status_class": "unknown"}
        token = _attempt.set(sample)
        began = perf_counter()
        failed = False
        try:
            return getter(url)
        except BaseException as exc:
            failed = True
            code = getattr(exc, "code", None)
            if isinstance(code, int):
                sample["status_class"] = str(code // 100) + "xx"
            raise
        finally:
            duration = (perf_counter() - began) * 1000
            _attempt.reset(token)
            try:
                event.record(
                    url=url, elapsed_ms=duration,
                    body_bytes=sample["body_bytes"], failed=failed,
                    status_class=sample["status_class"],
                )
            except Exception:
                # Observability must never become a provider failure.
                pass
    return get


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else None


def _fingerprint(result: Any) -> str | None:
    explicit = getattr(result, "fingerprint", None)
    if isinstance(explicit, str) and len(explicit) >= 32:
        return explicit[:64]
    rows = getattr(result, "rows", None)
    if rows is None:
        return None
    digest = sha256()
    for row in rows:
        digest.update(repr(row).encode("utf-8", errors="replace"))
        digest.update(b"\n")
    return digest.hexdigest()


def _nearest(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    from math import ceil
    return ordered[max(0, ceil(pct * len(ordered)) - 1)]


def _emit(event: _Event, result: Any, failure: str | None) -> None:
    try:
        rows = getattr(result, "rows", None)
        summary: dict[str, Any] = {
            "event": "provider_acquisition_v1", "trace": event.event_id,
            "provider": event.provider, "horizon": event.horizon,
            "season": event.season, "week": event.week, "cause": event.cause,
            "requests": event.requests, "success": event.succeeded,
            "failures": event.failed, "retries": event.retries,
            "response_body_bytes": event.body_bytes,
            "unknown_body_count": event.unknown_bytes,
            "latency_ms": round((perf_counter() - event.started) * 1000, 2),
            "request_p50_ms": _nearest(event.elapsed_ms, 0.50),
            "request_p95_ms": _nearest(event.elapsed_ms, 0.95),
            "families": dict(sorted(event.families.items())),
            "family_response_body_bytes": dict(sorted(event.family_bytes.items())),
            "family_unknown_body_count": dict(sorted(event.family_unknown.items())),
            "status_classes": dict(sorted(event.statuses.items())),
            "cohort": sha256(f"{event.provider}|{event.horizon}|{event.season}|{event.week}".encode()).hexdigest()[:16],
            "cache": "miss" if event.requests else "not_observed",
            "result": "failed" if failure is not None else "ok",
            "error_class": failure, "source_version":
                getattr(result, "source_version", None),
            "captured_at": _iso(getattr(result, "captured_at", None)),
            "effective_at": _iso(getattr(result, "effective_at", None)),
            "content_fingerprint": _fingerprint(result),
            "normalized_rows": len(rows) if rows is not None else None,
        }
        _log.info("FSFFL_PROVIDER_ACQUISITION %s", json.dumps(summary, separators=(",", ":")))
    except Exception:
        # Avoid changing domain behavior for logging/serialization failures.
        pass


def observe_acquisition(provider: str, horizon: str, *, cause: str = "independent_current"):
    """One aggregate per existing provider entrypoint; thread-safe when context copied."""
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if not _enabled():
                return fn(*args, **kwargs)
            value = _cause.get() or cause
            event = _Event(
                provider=provider, horizon=horizon,
                season=kwargs.get("season"), week=kwargs.get("week"),
                cause=value if value in _CAUSES else "unknown",
            )
            token = _active.set(event)
            result = None
            failure: str | None = None
            try:
                result = fn(*args, **kwargs)
                return result
            except BaseException as exc:
                failure = type(exc).__name__[:48]
                raise
            finally:
                _active.reset(token)
                _emit(event, result, failure)
        return wrapped
    return decorate


def log_reuse(*, provider: str, cause: str, reuse: str) -> None:
    """Log a proven zero-request lifecycle reuse (never infer a cache hit)."""
    if not _enabled():
        return
    if provider not in {"sleeper"} or cause not in _CAUSES or reuse not in {"state_current", "active_connection"}:
        return
    event = {
        "event": "provider_acquisition_reuse_v1", "provider": provider,
        "cause": cause, "reuse": reuse, "requests": 0,
        "response_body_bytes": 0, "cache": "hit",
    }
    _log.info("FSFFL_PROVIDER_ACQUISITION %s", json.dumps(event, separators=(",", ":")))
