from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from functools import wraps
from time import monotonic
from typing import Any, Callable
from uuid import uuid4

_LOGGER = logging.getLogger("uvicorn.error")
_JOURNEY_ID: ContextVar[str | None] = ContextVar("fsffl_journey_id", default=None)
_SAFE_FIELDS = {
    "stage", "outcome", "api_path", "method", "status_code", "elapsed_ms",
    "attempt", "retry_wait_ms", "target_state_id", "served_state_id",
    "publication_generation_id", "artifact_kind", "read_kind", "cache_result",
    "call_count", "row_count", "payload_json_bytes", "first_useful_render_ms",
    "visible", "memory_supported", "memory_heap_bytes", "browser_event_name",
    "request_count", "handoff_from_generation", "handoff_to_generation",
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_JOURNEY_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{36}$")


def new_journey_id() -> str:
    return str(uuid4())


def set_journey_id(value: str | None):
    candidate = value.strip() if isinstance(value, str) else ""
    if not _JOURNEY_ID_PATTERN.fullmatch(candidate):
        candidate = new_journey_id()
    return _JOURNEY_ID.set(candidate), candidate


def reset_journey_id(token) -> None:
    _JOURNEY_ID.reset(token)


def current_journey_id() -> str | None:
    return _JOURNEY_ID.get()


def emit_journey_event(event: str, **fields: Any) -> None:
    journey_id = current_journey_id()
    if journey_id is None:
        return
    record: dict[str, Any] = {"journey_id": journey_id, "event": str(event)[:48]}
    for key, value in fields.items():
        if key not in _SAFE_FIELDS:
            continue
        if isinstance(value, str):
            if key.endswith("_state_id") or key.endswith("_generation") or key == "publication_generation_id":
                if not _SAFE_ID.fullmatch(value):
                    continue
            record[key] = value[:160]
        elif isinstance(value, (bool, int, float)) and not isinstance(value, complex):
            record[key] = value
    _LOGGER.info("FSFFL_CUSTOMER_JOURNEY %s", json.dumps(record, separators=(",", ":"), sort_keys=True))


def record_browser_events(events: Any) -> int:
    if not isinstance(events, list):
        return 0
    accepted = 0
    for item in events[:80]:
        if not isinstance(item, dict):
            continue
        event = item.get("event")
        if not isinstance(event, str):
            continue
        fields = {key: value for key, value in item.items() if key in _SAFE_FIELDS}
        emit_journey_event(event[:48], **fields)
        accepted += 1
    return accepted


def trace_persistence_read(read_kind: str) -> Callable:
    """Measure adapter reads without logging identifiers, SQL, or payload contents."""
    def decorate(method: Callable) -> Callable:
        @wraps(method)
        def wrapped(*args, **kwargs):
            started = monotonic()
            outcome = "error"
            result = None
            try:
                result = method(*args, **kwargs)
                outcome = "hit" if result is not None else "miss"
                return result
            finally:
                payload = getattr(result, "payload", None) if result is not None else None
                payload_bytes = None
                if payload is not None:
                    try:
                        payload_bytes = len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
                    except (TypeError, ValueError):
                        pass
                emit_journey_event(
                    "persistence_read",
                    read_kind=read_kind,
                    outcome=outcome,
                    elapsed_ms=round((monotonic() - started) * 1000, 2),
                    call_count=1,
                    row_count=1 if result is not None else 0,
                    payload_json_bytes=payload_bytes if payload_bytes is not None else 0,
                )
        return wrapped
    return decorate
