from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from enum import StrEnum
from concurrent.futures import Future
from threading import RLock
from time import monotonic
from typing import Callable, Literal

from fsffl.persistence.contracts import (
    ArtifactKey,
    PersistenceStore,
    ReusableArtifactRecord,
    canonical_fingerprint,
    utc_now,
)
from fsffl.persistence.runtime_cache import (
    LEAGUE_SCOPE_KIND,
    SIMULATION_ARTIFACT_KIND,
    SIMULATION_MODEL_VERSION,
    decode_simulation,
    encode_simulation,
)
from fsffl.state.models import FrozenModel, LeagueState

from .runtime import LiveForecastEvidence
from .simulation_runtime import (
    LiveSimulationAnalyticsResult,
    simulation_forecast_dependency_fingerprint,
    simulation_structure_dependency_fingerprint,
)


SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]


class ScenarioComputationStage(StrEnum):
    SCREENING = "screening"
    PROVISIONAL = "provisional"
    CONFIRMATION = "confirmation"


_SCENARIO_STAGE_COUNTS = {
    ScenarioComputationStage.SCREENING: 1_000,
    ScenarioComputationStage.PROVISIONAL: 5_000,
    ScenarioComputationStage.CONFIRMATION: 50_000,
}


class ScenarioDependencyPlan(FrozenModel):
    affected_team_ids: tuple[str, ...] = ()
    reusable_team_ids: tuple[str, ...] = ()
    planned_mode: Literal[
        "full_recompute", "selective_inputs", "reuse_competitive_simulation"
    ]
    structure_compatible: bool
    forecast_compatible: bool
    baseline_preparation_available: bool
    reasons: tuple[str, ...] = ()


class ScenarioComputationMetadata(FrozenModel):
    requested_stage: ScenarioComputationStage
    requested_simulation_count: int
    effective_simulation_count: int
    authoritative: bool
    execution_mode: Literal[
        "cache_reuse",
        "full_recompute",
        "selective_inputs",
        "reuse_competitive_simulation",
    ]
    dependency_plan: ScenarioDependencyPlan
    cache_hit: bool
    deeper_stage_available: ScenarioComputationStage | None = None
    authority_label: str


_CACHE_MODEL_VERSION = "next8-scenario-cache-v5:progressive-selective-dependency-plan"
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
    """Process-local loader identity for exact reuse and in-flight coalescing.

    Progressive stage factories create a fresh callable for each request. When a
    loader supplies an explicit governed cache identity, that identity plus model
    version is the contract and must remain stable across equivalent callable
    instances. Call-object identity is retained only for ad-hoc loaders that do not
    declare an explicit cache identity.
    """

    module = getattr(loader, "__module__", type(loader).__module__)
    qualname = getattr(loader, "__qualname__", type(loader).__qualname__)
    explicit = getattr(loader, "__fsffl_cache_identity__", None)
    model_version = getattr(loader, "__fsffl_simulation_model_version__", "")
    if explicit is not None:
        return f"{module}:{qualname}:{explicit}:{model_version}"
    return f"{module}:{qualname}::{model_version}:{id(loader)}"


def _durable_loader_identity(loader: SimulationLoader) -> str:
    """Stable implementation/configuration identity for cross-process reuse."""

    explicit = getattr(loader, "__fsffl_cache_identity__", None)
    if explicit is not None:
        return canonical_fingerprint(
            "explicit",
            str(explicit),
            str(getattr(loader, "__fsffl_simulation_model_version__", "")),
        )

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


def scenario_stage_simulation_count(stage: ScenarioComputationStage) -> int:
    return _SCENARIO_STAGE_COUNTS[stage]


def _roster_fingerprint_by_team(league_state: LeagueState) -> dict[str, str]:
    return {
        team_state.team_id: canonical_fingerprint(
            tuple(
                sorted(
                    (
                        entry.player_id,
                        entry.slot.value,
                    )
                    for entry in team_state.roster
                )
            )
        )
        for team_state in league_state.team_states
    }


def build_scenario_dependency_plan(
    baseline_state: LeagueState,
    changed_state: LeagueState,
    evidence: LiveForecastEvidence,
    baseline_result: LiveSimulationAnalyticsResult,
    *,
    stage: ScenarioComputationStage,
) -> ScenarioDependencyPlan:
    if baseline_state.league.league_id != changed_state.league.league_id:
        raise ValueError("scenario dependency planning requires the same league")

    if (
        baseline_result.league_view.context.league_state_id
        != baseline_state.state_id
    ):
        raise ValueError("baseline Simulation result does not match baseline State")
    preparation = baseline_result.scenario_preparation
    if preparation is not None and preparation.source_state_id != baseline_state.state_id:
        raise ValueError("scenario preparation does not match baseline State")

    changed_structure = simulation_structure_dependency_fingerprint(changed_state)
    changed_forecast = simulation_forecast_dependency_fingerprint(
        evidence.league_scored_forecasts,
        forecast_model_version=evidence.model_version,
    )
    baseline_rosters = _roster_fingerprint_by_team(baseline_state)
    changed_rosters = _roster_fingerprint_by_team(changed_state)
    all_team_ids = tuple(sorted(set(baseline_rosters) | set(changed_rosters)))
    affected = tuple(
        team_id
        for team_id in all_team_ids
        if baseline_rosters.get(team_id) != changed_rosters.get(team_id)
    )

    reasons: list[str] = []
    if preparation is None:
        reasons.append("baseline_scenario_preparation_unavailable")
        return ScenarioDependencyPlan(
            affected_team_ids=affected,
            reusable_team_ids=(),
            planned_mode="full_recompute",
            structure_compatible=False,
            forecast_compatible=False,
            baseline_preparation_available=False,
            reasons=tuple(reasons),
        )

    structure_compatible = preparation.structure_fingerprint == changed_structure
    forecast_compatible = preparation.forecast_fingerprint == changed_forecast
    if not structure_compatible:
        reasons.append("global_simulation_dependency_changed")
    if not forecast_compatible:
        reasons.append("forecast_dependency_changed")
    if not structure_compatible or not forecast_compatible:
        return ScenarioDependencyPlan(
            affected_team_ids=affected,
            reusable_team_ids=(),
            planned_mode="full_recompute",
            structure_compatible=structure_compatible,
            forecast_compatible=forecast_compatible,
            baseline_preparation_available=True,
            reasons=tuple(reasons),
        )

    reusable = tuple(team_id for team_id in all_team_ids if team_id not in affected)
    if not affected:
        # No competitive roster dependency changed. Reuse the canonical baseline
        # result at every requested stage rather than rerunning a weaker preview.
        mode = "reuse_competitive_simulation"
    else:
        mode = "selective_inputs"
    return ScenarioDependencyPlan(
        affected_team_ids=affected,
        reusable_team_ids=reusable,
        planned_mode=mode,
        structure_compatible=True,
        forecast_compatible=True,
        baseline_preparation_available=True,
        reasons=(),
    )


def _stage_loader(
    simulation_loader: SimulationLoader,
    stage: ScenarioComputationStage,
) -> SimulationLoader:
    if stage == ScenarioComputationStage.CONFIRMATION:
        return simulation_loader
    factory = getattr(simulation_loader, "__fsffl_progressive_loader_factory__", None)
    if factory is None:
        raise ValueError(
            "scenario Simulation loader does not support non-authoritative progressive stages"
        )
    loader = factory(scenario_stage_simulation_count(stage), stage.value)
    return loader


def _next_stage(stage: ScenarioComputationStage) -> ScenarioComputationStage | None:
    if stage == ScenarioComputationStage.SCREENING:
        return ScenarioComputationStage.PROVISIONAL
    if stage == ScenarioComputationStage.PROVISIONAL:
        return ScenarioComputationStage.CONFIRMATION
    return None


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
    model_version = getattr(simulation_loader, "__fsffl_simulation_model_version__", None)
    if model_version is None:
        model_version = SIMULATION_MODEL_VERSION
    return ArtifactKey(
        artifact_kind=SIMULATION_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        input_fingerprint=canonical_fingerprint(league_state.state_id, durable_fingerprint),
        model_version=str(model_version),
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
            ReusableArtifactRecord(
                key=_durable_key(league_state, evidence, simulation_loader),
                payload=encode_simulation(result),
                computed_at=utc_now(),
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
    executor: Callable[[], LiveSimulationAnalyticsResult] | None = None,
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
        result = (
            executor()
            if executor is not None
            else simulation_loader(league_state, evidence)
        )
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


def run_progressive_scenario_simulation(
    baseline_state: LeagueState,
    changed_state: LeagueState,
    evidence: LiveForecastEvidence,
    baseline_result: LiveSimulationAnalyticsResult,
    *,
    simulation_loader: SimulationLoader,
    stage: ScenarioComputationStage = ScenarioComputationStage.CONFIRMATION,
) -> tuple[
    LiveSimulationAnalyticsResult,
    bool,
    ScenarioComputationMetadata,
]:
    """Run one explicitly staged alternate-State Simulation with proven reuse."""

    plan = build_scenario_dependency_plan(
        baseline_state,
        changed_state,
        evidence,
        baseline_result,
        stage=stage,
    )
    requested_count = scenario_stage_simulation_count(stage)

    # If competitive inputs did not change at all, an authoritative canonical
    # baseline is stronger than rerunning a smaller provisional sample.
    reuse_canonical = (
        plan.planned_mode == "reuse_competitive_simulation"
        and baseline_result.simulation_result.simulation_count == 50_000
    )
    selected_stage = (
        ScenarioComputationStage.CONFIRMATION if reuse_canonical else stage
    )
    selected_loader = _stage_loader(simulation_loader, selected_stage)
    selective_runner = getattr(selected_loader, "__fsffl_selective_runner__", None)

    actual_mode = plan.planned_mode
    executor: Callable[[], LiveSimulationAnalyticsResult] | None = None
    if (
        plan.planned_mode in {"selective_inputs", "reuse_competitive_simulation"}
        and selective_runner is not None
    ):
        executor = lambda: selective_runner(
            changed_state,
            evidence,
            baseline_result,
            plan,
            reuse_canonical,
        )
    elif plan.planned_mode != "full_recompute":
        actual_mode = "full_recompute"

    result, cache_hit = run_cached_scenario_simulation(
        changed_state,
        evidence,
        simulation_loader=selected_loader,
        executor=executor,
    )
    authoritative = (
        reuse_canonical
        or (
            stage == ScenarioComputationStage.CONFIRMATION
            and result.simulation_result.simulation_count == 50_000
        )
    )
    effective_count = result.simulation_result.simulation_count
    execution_mode: Literal[
        "cache_reuse",
        "full_recompute",
        "selective_inputs",
        "reuse_competitive_simulation",
    ] = "cache_reuse" if cache_hit else actual_mode
    return (
        result,
        cache_hit,
        ScenarioComputationMetadata(
            requested_stage=stage,
            requested_simulation_count=requested_count,
            effective_simulation_count=effective_count,
            authoritative=authoritative,
            execution_mode=execution_mode,
            dependency_plan=plan,
            cache_hit=cache_hit,
            deeper_stage_available=(None if authoritative else _next_stage(stage)),
            authority_label=(
                "authoritative_confirmation"
                if authoritative
                else "non_authoritative_scenario_preview"
            ),
        ),
    )


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
