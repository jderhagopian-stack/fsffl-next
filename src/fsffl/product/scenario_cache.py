from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from concurrent.futures import Future
from threading import RLock
from time import monotonic
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
_CACHE_MODEL_VERSION = "next8-scenario-cache-v4:durable-exact-state-forecast-loader-inflight"
_MAX_ENTRIES = 64
_lock = RLock()
_cache: OrderedDict[str, LiveSimulationAnalyticsResult] = OrderedDict()
_inflight: dict[str, Future[LiveSimulationAnalyticsResult]] = {}
_hits = 0
_misses = 0
_durable_hits = 0
_coalesced_hits = 0
_persistence: PersistenceStore | None = None
_logger = logging.getLogger("uvicorn.error")


def configure_scenario_cache_persistence(store: PersistenceStore | None) -> None:
    """Attach optional fail-open persistence to exact scenario reuse.

    Persistence never becomes Simulation authority. Only an artifact whose exact
    changed State, exact forecast fingerprint, loader/configuration identity and
    Simulation model version match is reusable. Any storage error falls through to
    the authoritative Simulation loader.
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
    """Process-local loader identity for the cheapest in-memory reuse boundary."""

    module = getattr(loader, "__module__", type(loader).__module__)
    qualname = getattr(loader, "__qualname__", type(loader).__qualname__)
    return f"{module}:{qualname}:{id(loader)}"


def _durable_loader_identity(loader: SimulationLoader) -> str:
    """Stable implementation/configuration identity for cross-process reuse."""

    explicit = getattr(loader, "__fsffl_cache_identity__", None)
    if explicit is not None:
        return canonical_fingerprint("explicit", str(explicit))

    module = getattr(loader, "__module__", type(loader).__module__)
    qualname = getattr(loader, "__qualname__", type(loader).__qualname__)
    code = getattr(loader, "__code__", None)
    if code is None:
        return canonical_fingerprint("callable", module, qualname)
    return canonical_fingerprint(
        "function",
        module,
        qualname,
        code.co_code.hex(),
        code.co_consts,
        getattr(loader, "__defaults__", None),
        getattr(loader, "__kwdefaults__", None),
    )


def _durable_forecast_fingerprint(
    evidence: LiveForecastEvidence,
    simulation_loader: SimulationLoader,
) -> str:
    return canonical_fingerprint(
        _forecast_fingerprint(evidence),
        _durable_loader_identity(simulation_loader),
    )


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


def _durable_key(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    simulation_loader: SimulationLoader,
) -> ArtifactKey:
    durable_fingerprint = _durable_forecast_fingerprint(evidence, simulation_loader)
    return ArtifactKey(
        artifact_kind=SIMULATION_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        input_fingerprint=canonical_fingerprint(league_state.state_id, durable_fingerprint),
        model_version=SIMULATION_MODEL_VERSION,
    )


def _load_durable(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    simulation_loader: SimulationLoader,
) -> LiveSimulationAnalyticsResult | None:
    store = _persistence
    if store is None:
        return None
    try:
        record = store.get_reusable_artifact(
            _durable_key(league_state, evidence, simulation_loader)
        )
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
    simulation_loader: SimulationLoader,
    result: LiveSimulationAnalyticsResult,
) -> None:
    store = _persistence
    if store is None:
        return
    try:
        store.put_artifact(
            simulation_artifact(
                league_state_id=league_state.state_id,
                forecast_fingerprint=_durable_forecast_fingerprint(
                    evidence, simulation_loader
                ),
                result=result,
            )
        )
    except Exception as exc:  # authoritative output is already complete
        _logger.warning(
            "FSFFL durable scenario cache write failed state=%s error=%s",
            league_state.state_id,
            exc,
        )


def _remember(key: str, result: LiveSimulationAnalyticsResult) -> None:
    _cache[key] = result
    _cache.move_to_end(key)
    while len(_cache) > _MAX_ENTRIES:
        _cache.popitem(last=False)


def run_cached_scenario_simulation(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    *,
    simulation_loader: SimulationLoader,
) -> tuple[LiveSimulationAnalyticsResult, bool]:
    """Reuse or coalesce only an exact changed-State + forecast + loader result.

    Exactly matching concurrent cold requests share one authoritative 50,000-run
    Simulation. Followers wait for that exact run; no approximation or reduced run
    count is introduced. Near-repeats with a different State, forecast fingerprint,
    loader/configuration identity, or Simulation model remain cache misses.
    """

    global _hits, _misses, _durable_hits, _coalesced_hits
    total_started = monotonic()
    key = scenario_cache_key(league_state, evidence, simulation_loader)
    lookup_finished = monotonic()
    leader = False
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            _hits += 1
            _logger.info(
                "FSFFL scenario phases cache=memory key=%.3fs total=%.3fs state=%s",
                lookup_finished - total_started,
                monotonic() - total_started,
                league_state.state_id,
            )
            return cached, True
        pending = _inflight.get(key)
        if pending is None:
            pending = Future()
            _inflight[key] = pending
            _misses += 1
            leader = True
        else:
            _coalesced_hits += 1
            _hits += 1

    if not leader:
        wait_started = monotonic()
        result = pending.result()
        _logger.info(
            "FSFFL scenario phases cache=coalesced key=%.3fs wait=%.3fs total=%.3fs state=%s",
            lookup_finished - total_started,
            monotonic() - wait_started,
            monotonic() - total_started,
            league_state.state_id,
        )
        return result, True

    try:
        durable_started = monotonic()
        durable = _load_durable(league_state, evidence, simulation_loader)
        durable_finished = monotonic()
        if durable is not None:
            with _lock:
                _remember(key, durable)
                _hits += 1
                _durable_hits += 1
            pending.set_result(durable)
            _logger.info(
                "FSFFL scenario phases cache=durable key=%.3fs durable=%.3fs total=%.3fs state=%s",
                lookup_finished - total_started,
                durable_finished - durable_started,
                monotonic() - total_started,
                league_state.state_id,
            )
            return durable, True

        simulation_started = monotonic()
        result = simulation_loader(league_state, evidence)
        simulation_finished = monotonic()
        if result.league_view.context.league_state_id != league_state.state_id:
            raise ValueError("scenario Simulation result must match the exact changed LeagueState")

        with _lock:
            _remember(key, result)
        persistence_started = monotonic()
        _persist_durable(league_state, evidence, simulation_loader, result)
        persistence_finished = monotonic()
        pending.set_result(result)
        _logger.info(
            "FSFFL scenario phases cache=miss key=%.3fs durable=%.3fs simulation_50k=%.3fs persistence=%.3fs total=%.3fs state=%s",
            lookup_finished - total_started,
            durable_finished - durable_started,
            simulation_finished - simulation_started,
            persistence_finished - persistence_started,
            monotonic() - total_started,
            league_state.state_id,
        )
        return result, False
    except BaseException as exc:
        pending.set_exception(exc)
        raise
    finally:
        with _lock:
            if _inflight.get(key) is pending:
                _inflight.pop(key, None)


def scenario_cache_status() -> dict[str, object]:
    with _lock:
        return {
            "entries": len(_cache),
            "max_entries": _MAX_ENTRIES,
            "hits": _hits,
            "misses": _misses,
            "durable_hits": _durable_hits,
            "coalesced_hits": _coalesced_hits,
            "inflight": len(_inflight),
            "persistence_enabled": _persistence is not None,
            "model_version": _CACHE_MODEL_VERSION,
            "authority": "performance-only exact-result reuse",
        }


def clear_scenario_cache() -> None:
    """Clear disposable completed process memory; running exact work is not cancelled."""

    global _hits, _misses, _durable_hits, _coalesced_hits
    with _lock:
        _cache.clear()
        _hits = 0
        _misses = 0
        _durable_hits = 0
        _coalesced_hits = 0
