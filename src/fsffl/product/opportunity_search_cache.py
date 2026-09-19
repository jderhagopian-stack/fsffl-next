from __future__ import annotations

import logging
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Callable, Mapping

from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeCenterBrowserView


_logger = logging.getLogger("uvicorn.error")
_MAX_ENTRIES = 16

CandidateBuilder = Callable[
    [UserRuntimeContext, TradeCenterBrowserView, Mapping[str, FSFFLCardinalValueScore]],
    list[dict[str, object]],
]


def _evidence_identity(value: object | None) -> tuple[int, str | None]:
    return id(value), getattr(value, "model_version", None) if value is not None else None


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
                return cached
            misses += 1
            result = builder(runtime, browser, cardinal)
            cache[key] = result
            cache.move_to_end(key)
            while len(cache) > _MAX_ENTRIES:
                cache.popitem(last=False)
            _logger.info(
                "FSFFL Market search catalog timing cache_hit=false elapsed=%.3fs hits=%d misses=%d state=%s team=%s candidates=%d",
                monotonic() - started,
                hits,
                misses,
                league_state.state_id,
                runtime.selected_team_id,
                len(result),
            )
            return result

    return cached_builder
