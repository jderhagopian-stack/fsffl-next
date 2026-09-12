from __future__ import annotations

import logging
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Callable

from .runtime import UserRuntimeContext


_logger = logging.getLogger("uvicorn.error")
_MAX_ENTRIES = 16

WorkspaceBuilder = Callable[..., dict[str, object]]


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
        league_state.state_id,
        id(league_state),
        runtime.selected_team_id,
        _evidence_identity(runtime.forecast_evidence),
        _evidence_identity(runtime.simulation_analytics),
        _evidence_identity(runtime.value_evidence),
        candidate_limit,
        bilateral_evaluation_limit,
    )


def make_cached_opportunity_workspace(builder: WorkspaceBuilder) -> WorkspaceBuilder:
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
        bilateral_evaluation_limit: int = 1,
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
                return cached

            misses += 1
            result = builder(
                runtime,
                candidate_limit=candidate_limit,
                bilateral_evaluation_limit=bilateral_evaluation_limit,
            )
            cache[key] = result
            cache.move_to_end(key)
            while len(cache) > _MAX_ENTRIES:
                cache.popitem(last=False)
            _logger.info(
                "FSFFL Market workspace timing cache_hit=false elapsed=%.3fs hits=%d misses=%d state=%s team=%s",
                monotonic() - started,
                hits,
                misses,
                runtime.league_state.state_id,
                runtime.selected_team_id,
            )
            return result

    cached_builder.__name__ = getattr(builder, "__name__", "cached_opportunity_workspace")
    cached_builder.__doc__ = getattr(builder, "__doc__", None)
    return cached_builder
