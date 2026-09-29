from __future__ import annotations

import gc
import logging
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Callable, Mapping

from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeCenterBrowserView


_logger = logging.getLogger("uvicorn.error")
_MAX_ENTRIES_PER_USER = 1

CandidateBuilder = Callable[
    [UserRuntimeContext, TradeCenterBrowserView, Mapping[str, FSFFLCardinalValueScore]],
    list[dict[str, object]],
]


def _evidence_identity(value: object | None) -> tuple[int, str | None]:
    return id(value), getattr(value, "model_version", None) if value is not None else None


def _annotate_cache(result: list[dict[str, object]], *, cache_hit: bool, elapsed_ms: float):
    diagnostics = getattr(result, "diagnostics", None)
    if not isinstance(diagnostics, dict):
        return result
    try:
        return type(result)(
            list(result),
            diagnostics={
                **diagnostics,
                "search_cache_hit": cache_hit,
                "search_cache_elapsed_ms": round(elapsed_ms, 3),
            },
        )
    except TypeError:
        return result


def make_cached_opportunity_search(builder: CandidateBuilder) -> CandidateBuilder:
    """Reuse the exact full structural candidate catalog for one authoritative runtime.

    The cache changes only execution. Search still owns candidate generation and ordering;
    callers may apply a narrower server-side search focus to this exact catalog without
    rebuilding the same expensive package universe for every Market interaction.
    """

    cache: OrderedDict[tuple[object, ...], list[dict[str, object]]] = OrderedDict()
    lock = RLock()
    hits = 0
    misses = 0

    def cached_builder(
        runtime: UserRuntimeContext,
        browser: TradeCenterBrowserView,
        cardinal: Mapping[str, FSFFLCardinalValueScore],
    ) -> list[dict[str, object]]:
        nonlocal hits, misses
        league_state = runtime.league_state
        if league_state is None:
            return builder(runtime, browser, cardinal)
        key = (
            runtime.user_id,
            league_state.state_id,
            id(league_state),
            runtime.selected_team_id,
            _evidence_identity(runtime.simulation_analytics),
            _evidence_identity(runtime.value_evidence),
        )
        started = monotonic()
        with lock:
            cached = cache.get(key)
            if cached is not None:
                cache.move_to_end(key)
                hits += 1
                _logger.info(
                    "FSFFL Market search catalog timing cache_hit=true elapsed=%.3fs hits=%d misses=%d state=%s team=%s",
                    monotonic() - started,
                    hits,
                    misses,
                    league_state.state_id,
                    runtime.selected_team_id,
                )
                return _annotate_cache(
                    cached,
                    cache_hit=True,
                    elapsed_ms=(monotonic() - started) * 1000.0,
                )
            misses += 1
            # Candidate catalogs are exact-State execution caches. Evict only
            # this user's prior scope before allocating the new catalog; another
            # user's live Market workspace is outside this transition boundary.
            stale_keys = [
                item
                for item in cache
                if item[0] == runtime.user_id and item != key
            ]
            for stale_key in stale_keys:
                cache.pop(stale_key, None)
            if stale_keys:
                gc.collect()
                _logger.info(
                    "FSFFL Market search cache evicted_prior_scope entries=%d state=%s team=%s",
                    len(stale_keys),
                    league_state.state_id,
                    runtime.selected_team_id,
                )
            result = builder(runtime, browser, cardinal)
            cache[key] = result
            cache.move_to_end(key)
            user_keys = [
                item for item in cache if item[0] == runtime.user_id
            ]
            while len(user_keys) > _MAX_ENTRIES_PER_USER:
                stale_key = user_keys.pop(0)
                cache.pop(stale_key, None)
            _logger.info(
                "FSFFL Market search catalog timing cache_hit=false elapsed=%.3fs hits=%d misses=%d state=%s team=%s candidates=%d",
                monotonic() - started,
                hits,
                misses,
                league_state.state_id,
                runtime.selected_team_id,
                len(result),
            )
            return _annotate_cache(
                result,
                cache_hit=False,
                elapsed_ms=(monotonic() - started) * 1000.0,
            )

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
