from __future__ import annotations

import gc
import logging
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Callable

from .market_discovery_runtime import DEFAULT_PRELIMINARY_DECISION_BUDGET
from .runtime import UserRuntimeContext


_logger = logging.getLogger("uvicorn.error")
_MAX_ENTRIES_PER_USER = 1

WorkspaceBuilder = Callable[..., dict[str, object]]
RetentionValidator = Callable[[UserRuntimeContext], bool]


def _runtime_user_id(runtime: UserRuntimeContext) -> str:
    value = str(getattr(runtime, "user_id", "") or "").strip()
    return value or "local-beta-user"


def _evidence_identity(value: object | None) -> tuple[int, str | None]:
    """Identify the exact in-process evidence object without inventing new truth."""

    return id(value), getattr(value, "model_version", None) if value is not None else None


def opportunity_workspace_cache_key(
    runtime: UserRuntimeContext,
    *,
    candidate_limit: int,
    bilateral_evaluation_limit: int,
) -> tuple[object, ...] | None:
    """Key only on authoritative inputs consumed by the Market workspace.

    This cache is intentionally process-local and exact. Any replacement of State,
    Forecast, Simulation, Value, managed team, or compute policy produces a miss.
    Object identity is appropriate here because the wrapper lives only for the life
    of one hosted Python process; it prevents stale reuse when a new evidence object
    has the same public model version.
    """

    league_state = runtime.league_state
    if league_state is None:
        return None
    return (
        _runtime_user_id(runtime),
        league_state.state_id,
        id(league_state),
        runtime.selected_team_id,
        _evidence_identity(runtime.forecast_evidence),
        _evidence_identity(runtime.simulation_analytics),
        _evidence_identity(runtime.value_evidence),
        candidate_limit,
        bilateral_evaluation_limit,
    )


def _execution_payload(
    result: dict[str, object],
    *,
    cache_hit: bool,
    elapsed_ms: float,
) -> dict[str, object]:
    return {
        **result,
        "execution": {
            **dict(result.get("execution") or {}),
            "workspace_cache_hit": cache_hit,
            "workspace_cache_elapsed_ms": round(elapsed_ms, 3),
        },
    }


def make_cached_opportunity_workspace(
    builder: WorkspaceBuilder,
    *,
    retention_validator: RetentionValidator | None = None,
) -> WorkspaceBuilder:
    """Reuse an exact Market workspace instead of rebuilding identical Search/Decision.

    The wrapped builder remains the sole source of Search and Decision truth. A hit
    returns its previously produced immutable-by-convention payload byte-for-byte;
    a miss calls the original builder normally. No candidate, score, authority, or
    Simulation result is approximated or changed.

    The lock deliberately covers a miss build so duplicate concurrent requests for
    one hosted beta process cannot perform the same CPU-heavy work twice. Market
    workspace generation is already synchronous; serializing its rare cache misses
    is preferable to multiplying CPU work on the tiny beta instance.
    """

    cache: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()
    lock = RLock()
    hits = 0
    misses = 0

    def cached_builder(
        runtime: UserRuntimeContext,
        *,
        candidate_limit: int = 80,
        bilateral_evaluation_limit: int = DEFAULT_PRELIMINARY_DECISION_BUDGET,
    ) -> dict[str, object]:
        nonlocal hits, misses
        key = opportunity_workspace_cache_key(
            runtime,
            candidate_limit=candidate_limit,
            bilateral_evaluation_limit=bilateral_evaluation_limit,
        )
        if key is None:
            return builder(
                runtime,
                candidate_limit=candidate_limit,
                bilateral_evaluation_limit=bilateral_evaluation_limit,
            )

        started = monotonic()
        with lock:
            if retention_validator is not None and not retention_validator(runtime):
                result = builder(
                    runtime,
                    candidate_limit=candidate_limit,
                    bilateral_evaluation_limit=bilateral_evaluation_limit,
                )
                return _execution_payload(
                    result,
                    cache_hit=False,
                    elapsed_ms=(monotonic() - started) * 1000.0,
                )
            cached = cache.get(key)
            if cached is not None:
                cache.move_to_end(key)
                hits += 1
                _logger.info(
                    "FSFFL Market workspace timing cache_hit=true elapsed=%.3fs hits=%d misses=%d state=%s team=%s",
                    monotonic() - started,
                    hits,
                    misses,
                    runtime.league_state.state_id,
                    runtime.selected_team_id,
                )
                return _execution_payload(
                    cached,
                    cache_hit=True,
                    elapsed_ms=(monotonic() - started) * 1000.0,
                )

            misses += 1
            # A full workspace is large. Drop only this user's prior exact
            # State before replacement work begins; another user's cache remains
            # outside this lifecycle boundary.
            stale_keys = [
                item
                for item in cache
                if item[0] == _runtime_user_id(runtime) and item != key
            ]
            for stale_key in stale_keys:
                cache.pop(stale_key, None)
            if stale_keys:
                gc.collect()
                _logger.info(
                    "FSFFL Market workspace cache evicted_prior_scope entries=%d state=%s team=%s",
                    len(stale_keys),
                    runtime.league_state.state_id,
                    runtime.selected_team_id,
                )
            result = builder(
                runtime,
                candidate_limit=candidate_limit,
                bilateral_evaluation_limit=bilateral_evaluation_limit,
            )
            cache[key] = result
            cache.move_to_end(key)
            user_keys = [
                item for item in cache if item[0] == _runtime_user_id(runtime)
            ]
            while len(user_keys) > _MAX_ENTRIES_PER_USER:
                stale_key = user_keys.pop(0)
                cache.pop(stale_key, None)
            _logger.info(
                "FSFFL Market workspace timing cache_hit=false elapsed=%.3fs hits=%d misses=%d state=%s team=%s",
                monotonic() - started,
                hits,
                misses,
                runtime.league_state.state_id,
                runtime.selected_team_id,
            )
            return _execution_payload(
                result,
                cache_hit=False,
                elapsed_ms=(monotonic() - started) * 1000.0,
            )

    cached_builder.__name__ = getattr(builder, "__name__", "cached_opportunity_workspace")
    cached_builder.__doc__ = getattr(builder, "__doc__", None)

    def clear_user_cache(user_id: str) -> int:
        with lock:
            stale_keys = [item for item in cache if item[0] == user_id]
            for stale_key in stale_keys:
                cache.pop(stale_key, None)
        if stale_keys:
            gc.collect()
        return len(stale_keys)

    def clear_cache() -> int:
        with lock:
            count = len(cache)
            cache.clear()
        if count:
            gc.collect()
        return count

    cached_builder.clear_user_cache = clear_user_cache  # type: ignore[attr-defined]
    cached_builder.clear_cache = clear_cache  # type: ignore[attr-defined]
    return cached_builder
