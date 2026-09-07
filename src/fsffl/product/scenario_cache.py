from __future__ import annotations

import hashlib
from collections import OrderedDict
from threading import RLock
from typing import Callable

from fsffl.state.models import LeagueState

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_CACHE_MODEL_VERSION = "next8-scenario-cache-v1:exact-state-forecast-loader"
_MAX_ENTRIES = 64
_lock = RLock()
_cache: OrderedDict[str, LiveSimulationAnalyticsResult] = OrderedDict()
_hits = 0
_misses = 0


def _forecast_fingerprint(evidence: LiveForecastEvidence) -> str:
    """Hash the exact Simulation-facing forecast evidence, not merely its version."""

    digest = hashlib.sha256()
    digest.update(evidence.model_version.encode("utf-8"))
    digest.update(b"\0")
    for source_id in sorted(evidence.successful_source_ids):
        digest.update(source_id.encode("utf-8"))
        digest.update(b"\0")
    observations = sorted(
        evidence.league_scored_forecasts,
        key=lambda item: (
            item.player_id,
            item.horizon.value,
            item.metric.value,
            item.as_of.isoformat(),
            item.source,
            item.model_version,
        ),
    )
    for observation in observations:
        digest.update(observation.model_dump_json().encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _loader_identity(loader: SimulationLoader) -> str:
    module = getattr(loader, "__module__", type(loader).__module__)
    qualname = getattr(loader, "__qualname__", type(loader).__qualname__)
    return f"{module}:{qualname}:{id(loader)}"


def scenario_cache_key(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    simulation_loader: SimulationLoader,
) -> str:
    digest = hashlib.sha256()
    digest.update(_CACHE_MODEL_VERSION.encode("utf-8"))
    digest.update(b"\0")
    digest.update(league_state.state_id.encode("utf-8"))
    digest.update(b"\0")
    digest.update(_forecast_fingerprint(evidence).encode("utf-8"))
    digest.update(b"\0")
    digest.update(_loader_identity(simulation_loader).encode("utf-8"))
    return digest.hexdigest()


def run_cached_scenario_simulation(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    *,
    simulation_loader: SimulationLoader,
) -> tuple[LiveSimulationAnalyticsResult, bool]:
    """Reuse only an exact changed-State + forecast + loader Simulation result.

    The cache is a Product runtime performance layer only. It cannot create,
    modify, approximate, or interpolate Simulation output. A miss invokes the
    authoritative Simulation loader normally; a hit returns that exact prior
    result. The bounded process-local cache is intentionally disposable.
    """

    global _hits, _misses
    key = scenario_cache_key(league_state, evidence, simulation_loader)
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            _hits += 1
            return cached, True
        _misses += 1

    result = simulation_loader(league_state, evidence)
    if result.league_view.context.league_state_id != league_state.state_id:
        raise ValueError("scenario Simulation result must match the exact changed LeagueState")

    with _lock:
        existing = _cache.get(key)
        if existing is not None:
            _cache.move_to_end(key)
            return existing, True
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > _MAX_ENTRIES:
            _cache.popitem(last=False)
    return result, False


def scenario_cache_status() -> dict[str, object]:
    with _lock:
        return {
            "entries": len(_cache),
            "max_entries": _MAX_ENTRIES,
            "hits": _hits,
            "misses": _misses,
            "model_version": _CACHE_MODEL_VERSION,
            "authority": "performance-only exact-result reuse",
        }


def clear_scenario_cache() -> None:
    """Test/runtime maintenance hook; never changes authoritative stored evidence."""

    global _hits, _misses
    with _lock:
        _cache.clear()
        _hits = 0
        _misses = 0
