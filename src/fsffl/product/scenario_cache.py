from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from threading import RLock
from typing import Callable

from fsffl.persistence.contracts import ArtifactKey, PersistenceStore, canonical_fingerprint
from fsffl.persistence.runtime_cache import (
    LEAGUE_SCOPE_KIND,
    SIMULATION_ARTIFACT_KIND,
    SIMULATION_MODEL_VERSION,
    decode_simulation,
    simulation_artifact,
)
from fsffl.state.models import LeagueState

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_CACHE_MODEL_VERSION = "next8-scenario-cache-v2:durable-exact-state-forecast"
_MAX_ENTRIES = 64
_lock = RLock()
_cache: OrderedDict[str, LiveSimulationAnalyticsResult] = OrderedDict()
_hits = 0
_misses = 0
_durable_hits = 0
_persistence: PersistenceStore | None = None
_logger = logging.getLogger("uvicorn.error")


def configure_scenario_cache_persistence(store: PersistenceStore | None) -> None:
    """Attach optional fail-open persistence to exact scenario reuse.

    Persistence never becomes Simulation authority. Only an artifact whose exact
    changed State, exact forecast fingerprint and Simulation model version match is
    reusable. Any storage error falls through to the authoritative Simulation loader.
    """

    global _persistence
    with _lock:
        _persistence = store


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


def _durable_key(league_state: LeagueState, evidence: LiveForecastEvidence) -> ArtifactKey:
    forecast_fingerprint = _forecast_fingerprint(evidence)
    return ArtifactKey(
        artifact_kind=SIMULATION_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        input_fingerprint=canonical_fingerprint(league_state.state_id, forecast_fingerprint),
        model_version=SIMULATION_MODEL_VERSION,
    )


def _load_durable(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
) -> LiveSimulationAnalyticsResult | None:
    store = _persistence
    if store is None:
        return None
    try:
        record = store.get_reusable_artifact(_durable_key(league_state, evidence))
        if record is None:
            return None
        result = decode_simulation(dict(record.payload))
        if result.league_view.context.league_state_id != league_state.state_id:
            return None
        return result
    except Exception as exc:  # cache persistence must fail open
        _logger.warning(
            "FSFFL durable scenario cache read failed state=%s error=%s",
            league_state.state_id,
            exc,
        )
        return None


def _persist_durable(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    result: LiveSimulationAnalyticsResult,
) -> None:
    store = _persistence
    if store is None:
        return
    try:
        store.put_artifact(
            simulation_artifact(
                league_state_id=league_state.state_id,
                forecast_fingerprint=_forecast_fingerprint(evidence),
                result=result,
            )
        )
    except Exception as exc:  # authoritative output is already complete
        _logger.warning(
            "FSFFL durable scenario cache write failed state=%s error=%s",
            league_state.state_id,
            exc,
        )


def run_cached_scenario_simulation(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    *,
    simulation_loader: SimulationLoader,
) -> tuple[LiveSimulationAnalyticsResult, bool]:
    """Reuse only an exact changed-State + forecast + Simulation result.

    A process-local hit is cheapest. On a process miss, the runtime may reuse the
    same exact authoritative artifact from durable persistence, including after a
    Render restart. If neither exists, the authoritative 50,000-run Simulation runs
    normally and its exact output is retained for later reuse. No approximation,
    interpolation or reduced Simulation count is permitted here.
    """

    global _hits, _misses, _durable_hits
    key = scenario_cache_key(league_state, evidence, simulation_loader)
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            _hits += 1
            return cached, True
        _misses += 1

    durable = _load_durable(league_state, evidence)
    if durable is not None:
        with _lock:
            _cache[key] = durable
            _cache.move_to_end(key)
            while len(_cache) > _MAX_ENTRIES:
                _cache.popitem(last=False)
            _hits += 1
            _durable_hits += 1
        _logger.info(
            "FSFFL scenario simulation cache_hit=true tier=durable state=%s",
            league_state.state_id,
        )
        return durable, True

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
    _persist_durable(league_state, evidence, result)
    return result, False


def scenario_cache_status() -> dict[str, object]:
    with _lock:
        return {
            "entries": len(_cache),
            "max_entries": _MAX_ENTRIES,
            "hits": _hits,
            "misses": _misses,
            "durable_hits": _durable_hits,
            "persistence_enabled": _persistence is not None,
            "model_version": _CACHE_MODEL_VERSION,
            "authority": "performance-only exact-result reuse",
        }


def clear_scenario_cache() -> None:
    """Clear disposable process memory only; durable exact artifacts remain reusable."""

    global _hits, _misses, _durable_hits
    with _lock:
        _cache.clear()
        _hits = 0
        _misses = 0
        _durable_hits = 0
