from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable, Mapping
from threading import RLock
from time import monotonic
from typing import Any

from .runtime import UserRuntimeContext


_logger = logging.getLogger("uvicorn.error")
_MAX_ENTRIES = 2048
_ECONOMIC_EVIDENCE_KEYS = (
    "economics",
    "economic_net",
    "package_concentration",
    "package_economics",
    "cheap_economic_screen_complete",
    "cheap_economic_screen_authority",
    "preliminary_economic_band",
)

EconomicEvaluator = Callable[..., dict[str, object]]


def _evidence_identity(value: object | None) -> tuple[int, str | None]:
    return id(value), getattr(value, "model_version", None) if value is not None else None


def _ordered_refs(row: Mapping[str, object], side: str) -> tuple[str, ...]:
    return tuple(
        str(item.get("asset_ref") or "")
        for item in (row.get(side) or ())
        if isinstance(item, dict)
    )


def market_economics_cache_key(
    runtime: UserRuntimeContext,
    row: Mapping[str, object],
) -> tuple[object, ...] | None:
    league_state = runtime.league_state
    if league_state is None or runtime.selected_team_id is None:
        return None
    counterparty = str(row.get("counterparty_team_id") or "")
    send = _ordered_refs(row, "send")
    receive = _ordered_refs(row, "receive")
    if not counterparty or not send or not receive:
        return None
    return (
        league_state.state_id,
        id(league_state),
        runtime.selected_team_id,
        _evidence_identity(runtime.value_evidence),
        counterparty,
        send,
        receive,
    )


def make_cached_candidate_economics(evaluator: EconomicEvaluator) -> EconomicEvaluator:
    """Reuse exact Decision economic evidence for an identical package.

    Search-owned row metadata is never cached. A hit overlays only the governed
    economic fields produced by the wrapped evaluator onto the caller's current
    row, preserving focus/posture/search coordinates exactly. The cache is
    process-local and invalidates naturally on any State or Value object change.
    """

    cache: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()
    lock = RLock()
    hits = 0
    misses = 0

    def cached_evaluator(
        runtime: UserRuntimeContext,
        row: dict[str, object],
        **kwargs: Any,
    ) -> dict[str, object]:
        nonlocal hits, misses
        key = market_economics_cache_key(runtime, row)
        if key is None:
            return evaluator(runtime, row, **kwargs)

        started = monotonic()
        with lock:
            evidence = cache.get(key)
            if evidence is None:
                misses += 1
                evaluated = evaluator(runtime, row, **kwargs)
                evidence = {
                    name: evaluated[name]
                    for name in _ECONOMIC_EVIDENCE_KEYS
                    if name in evaluated
                }
                cache[key] = evidence
                cache.move_to_end(key)
                while len(cache) > _MAX_ENTRIES:
                    cache.popitem(last=False)
                cache_hit = False
            else:
                hits += 1
                cache.move_to_end(key)
                cache_hit = True

        if cache_hit:
            elapsed = (monotonic() - started) * 1000.0
            _logger.info(
                "FSFFL Market package economics cache_hit=true elapsed_ms=%.3f hits=%d misses=%d",
                elapsed,
                hits,
                misses,
            )
        return {**row, **evidence}

    cached_evaluator.__name__ = getattr(evaluator, "__name__", "cached_candidate_economics")
    cached_evaluator.__doc__ = getattr(evaluator, "__doc__", None)
    return cached_evaluator
