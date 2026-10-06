from __future__ import annotations

import asyncio
import gc
import logging
import os
from threading import Event, RLock, Thread
from time import monotonic, sleep

from fastapi import Depends, Request

from fsffl.persistence import (
    ReusableArtifactRecord,
    persistence_store_from_env,
    projection_history_store_from_env,
    state_snapshot_store_from_env,
    utc_now,
)
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability

from . import market_discovery_runtime as _market_discovery_runtime
from . import opportunity_workspace as _opportunity_workspace
from . import webapp as _webapp
from fsffl import journey_telemetry as _journey_telemetry
from .annual_preseason_scheduler_routes import install_annual_preseason_scheduler_route
from .behavioral_runtime import BehavioralRuntimeCoordinator, default_behavioral_store
from .focused_opportunity_routes import install_focused_opportunity_routes
from .acceptance_startup import production_acceptance_startup_enabled
from .foreground_pressure import install_foreground_pressure
from .forecast_resilience import (
    make_preseason_baseline_authority_loader,
    make_resilient_forecast_loader,
)
from .foundation4_career_forward_runtime import (
    CareerIntrinsicLoader,
)
from .foundation4_shadow_routes import install_career_intrinsic_routes
from .hosted_connect import install_hosted_connect_routes
from .in_season_forecast_routes import install_in_season_forecast_routes
from .intrinsic_background import (
    IntrinsicBuildStatus,
    IntrinsicBuildSuperseded,
    ShapleyIntrinsicBackgroundCoordinator,
)
from .intrinsic_market_discovery_routes import install_intrinsic_market_discovery_routes
from .intrinsic_value_routes import install_intrinsic_value_v1_routes
from .league_value_lens_routes import install_league_value_lens_routes
from .latency_observability import install_latency_observability
from .market_economics_cache import make_cached_candidate_economics
from .market_progressive_enrichment import MarketDecisionEnrichmentCoordinator
from .opportunity_search_cache import make_cached_opportunity_search
from .opportunity_workspace_cache import make_cached_opportunity_workspace
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .presentation_continuity import (
    FRANCHISE_SURFACE,
    HOME_SURFACE,
    LEAGUE_ATLAS_SURFACE,
    LEAGUE_TEAM_VIEWS_SURFACE,
    LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
    MARKET_VALUE_LENSES_ALL_SURFACE,
    MARKET_VALUE_LENSES_ROSTERED_SURFACE,
    MARKET_WORKSPACE_SURFACE,
    REQUIRED_PRESENTATION_SURFACES,
    PresentationContinuityStore,
    _manifest_key,
    _surface_key,
)
from .player_intelligence import (
    PlayerFutureForecastCache,
    build_player_intelligence_overview,
)
from .player_intelligence_routes import (
    PlayerHistoryBuildStatus,
    PlayerHistoryCapacityError,
    install_player_intelligence_routes,
)
from .phase1_latency import install_phase1_latency_routes
from .private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from .vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    provide_vnext_future_forecast_contract,
    vnext_future_forecast_input_fingerprint,
)
from .progressive_delivery_routes import install_progressive_delivery_routes
from .provisional_k_dst_routes import install_provisional_k_dst_routes
from .quick_frontier_routes import install_quick_frontier_routes
from .resource_coordinator import (
    HeavyWorkCoordinator,
    ResourceTransition,
    StateResourceBoundary,
    release_unused_process_memory,
)
from .runtime import default_sleeper_state_loader
from .scenario_cache import configure_scenario_cache_persistence
from .shapley_intrinsic_routes import install_shapley_intrinsic_routes
from .state_first_acceptance import (
    run_state_first_production_acceptance,
    resolve_staged_acceptance_user,
    run_state_first_restored_refresh_acceptance,
    stage_restored_refresh_partial_acceptance,
)


# Hosted private-beta observability only. The coordinator already records exact
# wall-clock phase timings; ensure Render emits those INFO records so latency work
# can target measured bottlenecks without adding technical noise to product UI.
logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)
logging.getLogger("fsffl.product.persistence").setLevel(logging.INFO)
_logger = logging.getLogger("fsffl.product.performance")

_persistence_store = persistence_store_from_env()
_projection_history_store = projection_history_store_from_env()
_state_snapshot_store = state_snapshot_store_from_env()
_runtime_store = PersistentPrivateBetaRuntimeStore(
    _persistence_store,
    state_snapshot_store=_state_snapshot_store,
)
_presentation_continuity = PresentationContinuityStore(_persistence_store)
_startup_restore_complete = Event()
_startup_restore_state: dict[str, object] = {"status": "idle"}
_heavy_work_coordinator = HeavyWorkCoordinator(max_waiters=6)


def _load_sleeper_state_under_heavy_claim(league_external_id: str):
    """Serialize large canonical State materialization with every other build."""

    with _heavy_work_coordinator.claim(
        kind="state_sync",
        key=f"sleeper:{league_external_id}",
        timeout_seconds=300.0,
    ):
        release_unused_process_memory(label="before-sleeper-state-sync")
        state = default_sleeper_state_loader(league_external_id)
        logging.getLogger("uvicorn.error").info(
            "FSFFL intelligence memory phase=state_materialization_complete current_rss=%s",
            _heavy_work_coordinator.snapshot().current_rss_bytes,
        )
        release_unused_process_memory(label="after-sleeper-state-sync")
        return state

def _execution_state_scope_owned(context) -> bool:
    """Return whether this context owns the user's current process execution scope."""

    state = context.league_state
    if state is None:
        return False
    if _runtime_store.working_generation_active(context.user_id):
        return _runtime_store.working_target_state_id(context.user_id) == state.state_id
    current = _runtime_store.get(context.user_id)
    return bool(
        current.league_state is not None
        and current.league_state.state_id == state.state_id
    )


def _market_execution_retention_valid(context) -> bool:
    """Market retention additionally requires the current managed-team identity."""

    if not _execution_state_scope_owned(context):
        return False
    current = _runtime_store.get(context.user_id)
    return current.selected_team_id == context.selected_team_id


def _market_enrichment_identity_valid(
    user_id: str,
    league_state_id: str,
    focal_team_id: str,
) -> bool:
    context = _runtime_store.get(user_id)
    return bool(
        context.league_state is not None
        and context.league_state.state_id == league_state_id
        and context.selected_team_id == focal_team_id
        and _market_execution_retention_valid(context)
    )

_market_decision_enrichment = MarketDecisionEnrichmentCoordinator(
    heavy_work_coordinator=_heavy_work_coordinator,
    identity_validator=_market_enrichment_identity_valid,
    max_workers=1,
)
configure_scenario_cache_persistence(_persistence_store)

# Persist-first restoration is a startup concern for the single-user private beta.
# Restore the exact compatible last-good runtime before accepting traffic so the
# first product-context/Home/My Team/Atlas request consumes already-governed
# evidence rather than paying lazy-restore latency. This performs no provider or
# model work; incompatible or absent persistence remains fail-closed.
_beta_auth_enabled = os.getenv("FSFFL_BETA_AUTH", "0").strip().lower() in {"1", "true", "yes", "on"}
_beta_restore_user = (
    os.getenv("FSFFL_BETA_USERNAME", "").strip()
    if _beta_auth_enabled
    else "local-beta-user"
)
# Hosted Behavioral persistence validates its migrated schema when the Postgres
# adapter is first constructed. Build the shared adapter while the Render process is
# starting rather than on the first user status/Market request. Validation is
# read-only: governed migrations own schema/index/RLS creation. Failure remains
# non-fatal here; Behavioral evidence fails closed rather than blocking the product.
# Behavioral storage stays lazy so module import/port binding never waits on a
# database connection. The coordinator owns bounded background initialization.
_behavioral_coordinator = BehavioralRuntimeCoordinator(
    store_factory=default_behavioral_store,
    max_workers=1,
    heavy_work_coordinator=_heavy_work_coordinator,
)
_sleeper_probe_source = SleeperLiveSource()
_full_refresh_seconds = max(
    1,
    int(os.getenv("FSFFL_FULL_PROVIDER_REFRESH_SECONDS", "3600")),
)
_forecast_loader = make_resilient_forecast_loader(_persistence_store)
_preseason_forecast_loader = make_preseason_baseline_authority_loader(_persistence_store)
_shapley_intrinsic_loader = PrivateBetaShapleyContractLoader(
    year_one_loader=_preseason_forecast_loader,
    persistence_store=_persistence_store,
    future_forecast_builder=provide_vnext_future_forecast_contract,
    future_forecast_model_version=VNEXT_FORECAST_VERSION,
    future_missing_fact_family="vnext_future_forecast_coordinate",
    future_forecast_input_fingerprint_resolver=(
        vnext_future_forecast_input_fingerprint
    ),
)
_player_future_forecast_cache = PlayerFutureForecastCache(
    future_forecast_builder=provide_vnext_future_forecast_contract,
    forecast_model_version=VNEXT_FORECAST_VERSION,
    persistence_store=_persistence_store,
    retention_validator=_execution_state_scope_owned,
)
_shapley_intrinsic_coordinator = ShapleyIntrinsicBackgroundCoordinator(
    _shapley_intrinsic_loader,
    max_workers=1,
    intrinsic_input_fingerprint_resolver=(
        _shapley_intrinsic_loader.intrinsic_input_fingerprint
    ),
    heavy_work_coordinator=_heavy_work_coordinator,
    ownership_validator=_execution_state_scope_owned,
)
_career_intrinsic_loader = CareerIntrinsicLoader(
    current_intrinsic_loader=_shapley_intrinsic_loader,
    current_intrinsic_fingerprint_resolver=(
        _shapley_intrinsic_loader.intrinsic_input_fingerprint
    ),
    persistence_store=_persistence_store,
)
_career_intrinsic_coordinator = ShapleyIntrinsicBackgroundCoordinator(
    _career_intrinsic_loader,
    max_workers=1,
    forecast_coordinate_resolver=(
        lambda _context: _career_intrinsic_loader.forecast_model_version
    ),
    intrinsic_input_fingerprint_resolver=(
        _career_intrinsic_loader.intrinsic_input_fingerprint
    ),
    heavy_work_coordinator=_heavy_work_coordinator,
    ownership_validator=_execution_state_scope_owned,
)

def _intrinsic_readiness_from_record(record) -> dict[str, object]:
    if record is None:
        return {
            "status": "unavailable",
            "reason": "Governed FSFFL Intrinsic has not been prepared for this exact State.",
            "build_status": "idle",
            "forecast_model_version": VNEXT_FORECAST_VERSION,
            "estimate_count": 0,
        }
    if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
        return {
            "status": "building",
            "reason": "Governed FSFFL Intrinsic is being prepared from the vNext Future Forecast contract.",
            "build_status": record.status.value,
            "forecast_model_version": record.forecast_coordinate,
            "estimate_count": 0,
        }
    if record.status == IntrinsicBuildStatus.FAILED:
        return {
            "status": "unavailable",
            "reason": record.error or "Governed FSFFL Intrinsic preparation failed.",
            "build_status": record.status.value,
            "forecast_model_version": record.forecast_coordinate,
            "estimate_count": 0,
        }
    contract = record.contract
    if contract is None:
        return {
            "status": "unavailable",
            "reason": "Intrinsic lifecycle completed without a governed contract.",
            "build_status": record.status.value,
            "forecast_model_version": record.forecast_coordinate,
            "estimate_count": 0,
        }
    if contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE or not contract.estimates:
        return {
            "status": "unavailable",
            "reason": contract.status_reason or "Governed Intrinsic contract is unavailable.",
            "build_status": record.status.value,
            "contract_status": contract.status.value,
            "forecast_model_version": contract.forecast_model_version,
            "estimate_count": len(contract.estimates),
        }
    coverage = contract.coverage
    complete_scope = (
        len(contract.estimates) > 0
        and coverage.player_count == len(contract.estimates)
        and coverage.year_1_forecast_players == coverage.player_count
        and coverage.year_2_i1_players == coverage.player_count
        and coverage.year_3_i1_players == coverage.player_count
        and not coverage.missing_required_fact_families
    )
    status = (
        "full"
        if contract.status == ShapleyIntrinsicAvailability.READY and complete_scope
        else "partial_provisional"
    )
    return {
        "status": status,
        "reason": contract.status_reason or (
            "Governed FSFFL Intrinsic is available from preserved Year-1 evidence "
            "and the Forecast-owned vNext Future Forecast contract. Optional legacy "
            "provenance coverage does not reduce availability."
        ),
        "build_status": record.status.value,
        "contract_status": contract.status.value,
        "forecast_model_version": contract.forecast_model_version,
        "estimate_count": len(contract.estimates),
        "target_years": list(contract.target_years),
    }


def _hosted_capability_readiness(context) -> dict[str, object]:
    payload = dict(_webapp._runtime_capability_readiness(context))
    record = None
    if context.league_state is not None:
        # Foreground readiness is memory-only. Durable Intrinsic reuse is staged by
        # startup/background reconciliation through the process heavy-work lane so
        # first-load reads cannot overlap contract deserialization with fresh core
        # enrichment. A completed in-process record remains immediately visible.
        record = _shapley_intrinsic_coordinator.current(context)
    intrinsic = _intrinsic_readiness_from_record(record)
    payload["intrinsic"] = intrinsic
    required = ("forecast", "simulation", "current_value", "intrinsic")
    statuses = tuple(
        str(payload.get(key, {}).get("status", "unavailable"))
        for key in required
    )
    payload["product_required_capabilities"] = list(required)
    core_status = str(payload.get("overall_status") or "unavailable")
    product_usable = (
        statuses[0] in {"full", "non_material_partial", "partial_nonblocking"}
        and all(status == "full" for status in statuses[1:])
    )
    payload["overall_status"] = (
        "rebuilding"
        if core_status == "rebuilding"
        else "full"
        if product_usable
        else "partial"
        if any(status not in {"unavailable", "not_configured"} for status in statuses)
        else "unavailable"
    )
    served = getattr(context, "served_intelligence", None)
    publication_id = str(
        getattr(context, "publication_generation_id", None) or ""
    ).strip()
    presentation_available = False
    presentation_league_id = None
    presentation_state_id = None
    if publication_id and context.league_state is not None:
        presentation_league_id = context.league_state.league.league_id
        presentation_state_id = context.league_state.state_id
    elif (
        served is not None
        and context.league_state is not None
        and served.league_id == context.league_state.league.league_id
        and served.league_state_id != context.league_state.state_id
        and served.publication_generation_id
    ):
        presentation_league_id = served.league_id
        presentation_state_id = served.league_state_id

    if presentation_league_id is not None and presentation_state_id is not None:
        presentation_available = _presentation_continuity.known_snapshot_available(
            user_id=context.user_id,
            league_id=presentation_league_id,
            league_state_id=presentation_state_id,
            selected_team_id=context.selected_team_id,
        )
        if not presentation_available:
            # Cold/startup validation is strict and warms the process-local hint.
            # Repeated read-only product-context polling then avoids rereading and
            # hashing the full seven-surface persisted snapshot.
            presentation_available = _presentation_continuity.has_snapshot(
                user_id=context.user_id,
                league_id=presentation_league_id,
                league_state_id=presentation_state_id,
                selected_team_id=context.selected_team_id,
            )
    served_payload = dict(payload.get("served_last_good") or {})
    served_payload["presentation_available"] = presentation_available
    if not presentation_available:
        served_payload["publication_generation_id"] = None
    if served_payload.get("available") and not presentation_available:
        served_payload["label"] = (
            "Last-good model identity exists, but a complete persisted presentation "
            "snapshot is unavailable; stale presentation will not be claimed."
        )
    payload["served_last_good"] = served_payload
    payload["presentation_continuity"] = {
        "status": (
            "stale_available"
            if presentation_available
            else "current"
            if payload.get("overall_status") == "full"
            else "unavailable"
        ),
        "contract": "runtime-presentation-continuity-v1",
    }
    return payload


def _reconcile_hosted_intrinsic(context) -> dict[str, object]:
    if context.league_state is None:
        return {
            "status": "unavailable",
            "reason": "Canonical LeagueState is unavailable.",
        }
    try:
        record = _shapley_intrinsic_coordinator.current(context)
        if record is None:
            try:
                record = _shapley_intrinsic_coordinator.restore_compatible_staged(
                    context
                )
            except IntrinsicBuildSuperseded:
                raise
            except Exception as exc:
                # Durable reuse is an optimization. If its staged lookup/gate fails,
                # fall through to the normal background build lifecycle so already
                # completed core Forecast/Simulation/Value work is not discarded.
                _logger.warning(
                    "FSFFL staged Intrinsic restore unavailable state=%s error=%s",
                    context.league_state.state_id,
                    exc,
                )
                record = None
        if record is None or record.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }:
            record = _shapley_intrinsic_coordinator.wait_for_terminal(context)
    except IntrinsicBuildSuperseded as exc:
        raise _webapp.IntelligenceJobInterrupted("lifecycle_switch") from exc
    readiness = _intrinsic_readiness_from_record(record)
    # Career Intrinsic is a production capability downstream of ready Current
    # Intrinsic. Always attach/reuse its exact-State lifecycle here so a startup
    # miss cannot remain stranded after Current Intrinsic later becomes ready.
    if readiness.get("status") == "full":
        try:
            career_record = _career_intrinsic_coordinator.current(context)
            if career_record is not None and career_record.status == IntrinsicBuildStatus.FAILED:
                # A startup attempt can legitimately fail while Current Intrinsic is
                # still restoring. Once Current is ready, discard only that stale
                # execution record and retry the same governed Career coordinate.
                _career_intrinsic_coordinator.clear_user(context.user_id)
                career_record = None
            if career_record is None:
                restored_career = _career_intrinsic_coordinator.restore_compatible_staged(context)
                career_record = restored_career or _career_intrinsic_coordinator.request(context)
            _logger.info(
                "FSFFL Career Intrinsic production lifecycle state=%s status=%s estimates=%s",
                context.league_state.state_id,
                career_record.status.value if career_record is not None else "unavailable",
                len(career_record.contract.estimates)
                if career_record is not None and career_record.contract is not None
                else 0,
            )
        except IntrinsicBuildSuperseded:
            raise
        except Exception as exc:
            # Career Intrinsic is downstream product intelligence; core publication
            # remains usable while this bounded production capability prepares.
            _logger.warning(
                "FSFFL Career Intrinsic production attach unavailable state=%s error=%s",
                context.league_state.state_id,
                exc,
            )
    _logger.info(
        "FSFFL hosted Intrinsic reconciliation state=%s status=%s build=%s forecast=%s estimates=%s",
        context.league_state.state_id,
        readiness.get("status"),
        readiness.get("build_status"),
        readiness.get("forecast_model_version"),
        readiness.get("estimate_count"),
    )
    return readiness


# Reuse only exact Decision-owned package economics across progressive Market
# requests. Search row metadata is overlaid fresh on every hit, while State/Value
# replacement or a different ordered package identity produces a miss.
_cached_candidate_economics = make_cached_candidate_economics(
    _market_discovery_runtime.evaluate_candidate_economics,
    retention_validator=_market_execution_retention_valid,
)
_market_discovery_runtime.evaluate_candidate_economics = _cached_candidate_economics

# Build the expensive structural candidate catalog once per exact authoritative
# runtime. The normal Market workspace and subsequent Market Focus requests share
# that exact catalog; focus changes Search selection/order without rebuilding the
# same package universe or changing Value/Decision authority.
_cached_opportunity_search = make_cached_opportunity_search(
    _opportunity_workspace.build_roster_aware_trade_candidates,
    retention_validator=_market_execution_retention_valid,
)
_opportunity_workspace.build_roster_aware_trade_candidates = _cached_opportunity_search

# Market navigation can issue the same workspace request repeatedly while the
# authoritative runtime is unchanged. Reuse the exact server-produced workspace
# instead of repeating Search + bounded Decision work. This wrapper is hosted-
# composition infrastructure only; the original builder remains authoritative.
_cached_opportunity_workspace = make_cached_opportunity_workspace(
    _webapp.build_opportunity_workspace,
    retention_validator=_market_execution_retention_valid,
)
_webapp.build_opportunity_workspace = _cached_opportunity_workspace

def _clear_hosted_execution_caches(
    transition: ResourceTransition,
) -> dict[str, int]:
    cleared: dict[str, int] = {}
    for name, wrapper in (
        ("market_economics", _cached_candidate_economics),
        ("opportunity_search", _cached_opportunity_search),
        ("opportunity_workspace", _cached_opportunity_workspace),
    ):
        clear = getattr(wrapper, "clear_user_cache", None)
        if callable(clear):
            cleared[name] = int(clear(transition.user_id))
    return cleared


def _clear_market_enrichment(transition: ResourceTransition) -> int:
    return _market_decision_enrichment.clear_user(transition.user_id)


def _clear_behavioral_execution(transition: ResourceTransition) -> int:
    return _behavioral_coordinator.clear_user(transition.user_id)


def _clear_intrinsic_execution(transition: ResourceTransition) -> dict[str, int]:
    return {
        "coordinator": _shapley_intrinsic_coordinator.clear_user(
            transition.user_id
        ),
        "loader_cache": _shapley_intrinsic_loader.clear_user_cache(
            transition.user_id
        ),
        "career_intrinsic_coordinator": _career_intrinsic_coordinator.clear_user(
            transition.user_id
        ),
        "career_intrinsic_loader_cache": _career_intrinsic_loader.clear_user_cache(
            transition.user_id
        ),
    }


def _clear_player_future_execution(transition: ResourceTransition) -> int:
    return _player_future_forecast_cache.clear_user_cache(transition.user_id)


def _clear_player_history_execution(transition: ResourceTransition) -> int:
    history = getattr(globals().get("app"), "state", None)
    coordinator = (
        getattr(history, "player_history_coordinator", None)
        if history is not None
        else None
    )
    clear = getattr(coordinator, "clear_user", None)
    return int(clear(transition.user_id)) if callable(clear) else 0


def _clear_presentation_validation_hints(transition: ResourceTransition) -> int:
    return _presentation_continuity.clear_user_validation_hints(
        transition.user_id
    )


_state_resource_boundary = StateResourceBoundary(
    clearers=(
        ("market_wrappers", _clear_hosted_execution_caches),
        ("market_enrichment", _clear_market_enrichment),
        ("behavioral", _clear_behavioral_execution),
        ("intrinsic", _clear_intrinsic_execution),
        ("player_future", _clear_player_future_execution),
        ("player_history", _clear_player_history_execution),
        ("presentation_validation", _clear_presentation_validation_hints),
    ),
    max_events=16,
)


def _apply_runtime_resource_boundary(
    transition: ResourceTransition,
) -> dict[str, object]:
    return _state_resource_boundary.apply(transition)


def _reclaim_runtime_phase_memory(label: str) -> dict[str, object]:
    return release_unused_process_memory(label=label)


def _presentation_payload_loader(user_id: str, context, surface: str):
    return _presentation_continuity.load_for_runtime(
        user_id=user_id,
        runtime=context,
        surface=surface,
    )


app = _webapp.create_app(
    runtime_store=_runtime_store,
    behavioral_coordinator=_behavioral_coordinator,
    state_loader=_load_sleeper_state_under_heavy_claim,
    forecast_loader=_forecast_loader,
    preseason_forecast_loader=_preseason_forecast_loader,
    state_snapshot_store=_state_snapshot_store,
    persistence_store=_persistence_store,
    capability_readiness_reader=_hosted_capability_readiness,
    product_capability_reconciler=_reconcile_hosted_intrinsic,
    heavy_work_coordinator=_heavy_work_coordinator,
    presentation_payload_loader=_presentation_payload_loader,
    state_resource_boundary=_apply_runtime_resource_boundary,
    phase_memory_reclaimer=_reclaim_runtime_phase_memory,
)

_RESTORE_GATE_BYPASS_PREFIXES = (
    "/api/connect/sleeper",
    "/health/",
)


@app.middleware("http")
async def _gate_restored_session_reads(request, call_next):
    """Wait for explicit startup restore only when a request depends on that restore.

    Fresh Connect is always allowed through. Once fresh canonical State is in memory,
    all ordinary API reads are also allowed through even if the old restore thread is
    still finishing, so persistence recovery can never sit in front of current State.
    """

    path = request.url.path
    if (
        _startup_restore_complete.is_set()
        or not _beta_restore_user
        or not path.startswith("/api/")
        or any(path.startswith(prefix) for prefix in _RESTORE_GATE_BYPASS_PREFIXES)
        or _runtime_store.get(_beta_restore_user).league_state is not None
        or not _runtime_store.durable_restore_pending(_beta_restore_user)
    ):
        return await call_next(request)

    await asyncio.to_thread(_startup_restore_complete.wait, 180.0)
    return await call_next(request)


@app.middleware("http")
async def _trace_customer_journey(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    token, journey_id = _journey_telemetry.set_journey_id(
        request.headers.get("x-fsffl-journey-id")
    )
    request.state.journey_id = journey_id
    started = monotonic()
    _journey_telemetry.emit_journey_event(
        "request_start",
        api_path=request.url.path,
        method=request.method,
    )
    try:
        response = await call_next(request)
        response.headers["X-FSFFL-Journey-ID"] = journey_id
        _journey_telemetry.emit_journey_event(
            "request_complete",
            api_path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            elapsed_ms=round((monotonic() - started) * 1000, 2),
        )
        return response
    except Exception:
        _journey_telemetry.emit_journey_event(
            "request_complete",
            api_path=request.url.path,
            method=request.method,
            outcome="error",
            elapsed_ms=round((monotonic() - started) * 1000, 2),
        )
        raise
    finally:
        _journey_telemetry.reset_journey_id(token)


@app.post("/api/diagnostics/customer-journey")
async def _collect_customer_journey(
    request: Request,
    _beta_user: str = Depends(_webapp.require_beta_user),
):
    body = await request.body()
    if len(body) > 65536:
        return {"accepted": 0, "reason": "payload_too_large"}
    try:
        payload = __import__("json").loads(body)
    except (TypeError, ValueError):
        return {"accepted": 0, "reason": "invalid_payload"}
    accepted = _journey_telemetry.record_browser_events(
        payload.get("events") if isinstance(payload, dict) else None
    )
    return {"accepted": accepted}


def _log_startup_runtime_readiness() -> None:
    if not _beta_restore_user:
        return
    context = _runtime_store.get(_beta_restore_user)
    league_state = context.league_state
    core_complete = bool(
        league_state is not None
        and context.forecast_evidence is not None
        and context.simulation_analytics is not None
        and context.value_evidence is not None
    )
    readiness = _hosted_capability_readiness(context)
    logging.getLogger("uvicorn.error").info(
        "FSFFL startup runtime readiness user=%s league=%s state=%s forecast=%s simulation=%s value=%s complete=%s",
        _beta_restore_user,
        league_state.league.league_id if league_state is not None else None,
        league_state.state_id if league_state is not None else None,
        context.forecast_evidence is not None,
        context.simulation_analytics is not None,
        context.value_evidence is not None,
        core_complete,
    )
    logging.getLogger("uvicorn.error").info(
        "FSFFL startup product readiness status=%s as_of=%s intrinsic=%s",
        readiness.get("overall_status"),
        readiness.get("as_of"),
        readiness.get("intrinsic", {}).get("status"),
    )
    resource_state = _heavy_work_coordinator.snapshot()
    logging.getLogger("uvicorn.error").info(
        "FSFFL startup resource readiness rss=%s peak_rss=%s budget=%s active=%s waiting=%s",
        resource_state.current_rss_bytes,
        resource_state.peak_rss_bytes,
        resource_state.memory_budget_bytes,
        resource_state.active_kind,
        resource_state.waiting_count,
    )

_product_acceptance_state: dict[str, object] = {
    "status": "idle",
    "deploy_contract": "runtime-architecture-acceptance-v1",
    "reason": "Acceptance is explicit; startup performs restore-only work.",
}
_product_acceptance_lock = RLock()


def _run_hosted_product_acceptance() -> None:
    if not _beta_restore_user:
        _product_acceptance_state.update(
            status="unavailable",
            reason="No hosted beta user is configured.",
        )
        return
    context = _runtime_store.get(_beta_restore_user)
    if context.league_state is None:
        _product_acceptance_state.update(
            status="unavailable",
            reason="No canonical hosted league State is restored.",
        )
        return
    try:
        intrinsic = _reconcile_hosted_intrinsic(context)
        record = _shapley_intrinsic_coordinator.current(context)
        contract = record.contract if record is not None else None
        if intrinsic.get("status") != "full" or contract is None:
            raise RuntimeError(
                "Governed FSFFL Intrinsic is not fully available: "
                + str(intrinsic.get("reason") or intrinsic.get("status"))
            )

        governed_ids = {
            item.player_id for item in contract.estimates
        }
        candidate = next(
            (
                player.player_id
                for player in context.league_state.players
                if player.player_id in governed_ids
            ),
            None,
        )
        if candidate is None:
            raise RuntimeError("No governed Intrinsic player is present in hosted State")
        overview = build_player_intelligence_overview(
            context,
            candidate,
            intrinsic=contract,
            future_cache=_player_future_forecast_cache,
        )
        years = sorted(
            int(item["year_index"])
            for item in overview.get("forecast", {}).get("rows", [])
            if item.get("year_index") is not None
        )
        if 2 not in years or 3 not in years:
            raise RuntimeError(
                f"Hosted Player Intelligence missing vNext Y2/Y3 rows: {years}"
            )

        atlas = _webapp.build_league_atlas_payload(
            context,
            preseason_reason="Hosted acceptance probe does not reconstruct preseason evidence.",
        )
        if not atlas.get("standings"):
            raise RuntimeError("Hosted League Atlas composition returned no standings")

        readiness = _hosted_capability_readiness(context)
        if readiness.get("overall_status") != "full":
            raise RuntimeError(
                "Hosted product readiness is not full after Intrinsic reconciliation: "
                + str(readiness)
            )
        _product_acceptance_state.clear()
        _product_acceptance_state.update(
            status="pass",
            deploy_contract="post-pr264-product-acceptance-v1",
            readiness_status=readiness.get("overall_status"),
            readiness_as_of=readiness.get("as_of"),
            intrinsic_status=intrinsic.get("status"),
            intrinsic_contract_status=intrinsic.get("contract_status"),
            intrinsic_estimate_count=intrinsic.get("estimate_count"),
            future_forecast_model_version=intrinsic.get("forecast_model_version"),
            player_intelligence_y2_y3=(2 in years and 3 in years),
            league_atlas_composed=True,
            league_static_module_present=(
                _webapp._STATIC_DIR / "league_comparison.js"
            ).is_file(),
        )
        _logger.info(
            "FSFFL HOSTED PRODUCT ACCEPTANCE PASS data=%s",
            _product_acceptance_state,
        )
    except Exception as exc:
        _product_acceptance_state.clear()
        _product_acceptance_state.update(
            status="fail",
            deploy_contract="post-pr264-product-acceptance-v1",
            error_type=type(exc).__name__,
            reason="Hosted product acceptance failed; detailed diagnostics are available in server logs.",
        )
        logging.getLogger("uvicorn.error").exception(
            "FSFFL HOSTED PRODUCT ACCEPTANCE FAILED"
        )


def _start_hosted_product_acceptance() -> bool:
    """Start hosted acceptance only after an explicit authenticated request."""

    with _product_acceptance_lock:
        if _product_acceptance_state.get("status") == "running":
            return False
        _product_acceptance_state.clear()
        _product_acceptance_state.update(
            status="running",
            deploy_contract="runtime-architecture-acceptance-v1",
        )
        Thread(
            target=_run_hosted_product_acceptance,
            name="fsffl-hosted-product-acceptance",
            daemon=True,
        ).start()
        return True

_runtime_availability_acceptance_state: dict[str, object] = {
    "status": "idle",
    "contract": "runtime-availability-acceptance-v1",
    "reason": "Acceptance mode is disabled; normal startup remains restore-only.",
}


_foundation4_acceptance_state: dict[str, object] = {
    "status": "idle",
    "contract": "foundation4-shadow-acceptance-v1",
    "reason": "Foundation 4 acceptance is disabled; normal startup remains restore-only.",
}
_foundation4_acceptance_lock = RLock()


def _run_foundation4_shadow_acceptance() -> None:
    mode = os.getenv("FSFFL_FOUNDATION4_ACCEPTANCE_MODE", "build").strip().lower()
    if mode not in {"build", "restore"}:
        _foundation4_acceptance_state.update(
            status="fail",
            mode=mode,
            reason="FSFFL_FOUNDATION4_ACCEPTANCE_MODE must be build or restore.",
        )
        return
    if not _startup_restore_complete.wait(timeout=180.0):
        _foundation4_acceptance_state.update(
            status="fail",
            mode=mode,
            reason="Startup restore did not complete before Foundation 4 acceptance.",
        )
        return
    if not _beta_restore_user:
        _foundation4_acceptance_state.update(
            status="fail",
            mode=mode,
            reason="No hosted beta user is configured.",
        )
        return

    try:
        context = _runtime_store.get(_beta_restore_user)
        if context.league_state is None:
            raise RuntimeError("Foundation 4 acceptance requires restored canonical State")
        if context.league_state.league.season != 2026:
            raise RuntimeError("Foundation 4 frozen authority is 2026-only")

        before = _heavy_work_coordinator.snapshot()
        current_record = _shapley_intrinsic_coordinator.wait_for_terminal(
            context,
            timeout_seconds=240.0,
        )
        if (
            current_record.status != IntrinsicBuildStatus.COMPLETED
            or current_record.contract is None
        ):
            raise RuntimeError(
                "Governed Current Intrinsic was not ready for Foundation 4 acceptance"
            )

        if mode == "restore":
            foundation4_record = (
                _career_intrinsic_coordinator.restore_compatible_staged(context)
            )
            if foundation4_record is None:
                raise RuntimeError(
                    "No compatible persisted Foundation 4 shadow was restored"
                )
        else:
            foundation4_record = _career_intrinsic_coordinator.wait_for_terminal(
                context,
                timeout_seconds=240.0,
            )

        if (
            foundation4_record.status != IntrinsicBuildStatus.COMPLETED
            or foundation4_record.contract is None
        ):
            raise RuntimeError("Foundation 4 shadow did not reach completed state")
        contract = foundation4_record.contract
        component = _career_intrinsic_loader.current_component(context)
        if contract.player_count != 335 or len(contract.estimates) != 335:
            raise RuntimeError("Foundation 4 holistic cohort is not the governed 335 players")
        if component is None or len(component.estimates) != 335:
            raise RuntimeError("Foundation 4 Y4-Y7 component is not the governed 335 players")
        if (
            contract.current_intrinsic_replaced
            or contract.authoritative_for_current_intrinsic
            or contract.display_scaling_applied
            or contract.market_inputs_used
        ):
            raise RuntimeError("Foundation 4 violated the governed shadow/economic boundary")
        if contract.aggregation != (
            "phi_Y1 + phi_Y2 + phi_Y3 + phi_Y4 + phi_Y5 + phi_Y6 + phi_Y7 + "
            "TAIL_Y8_PLUS"
        ):
            raise RuntimeError("Foundation 4 aggregation semantics drifted")

        current_by_id = {
            row.player_id: row for row in current_record.contract.estimates
        }
        for estimate in contract.estimates:
            current = current_by_id.get(estimate.player_id)
            if current is None:
                raise RuntimeError("Foundation 4 current-cohort identity mismatch")
            raw_y1_y3 = sum(
                float(row.raw_shapley_contribution) for row in current.contributions
            )
            if abs(raw_y1_y3 - estimate.current_intrinsic_raw_y1_y3) > 1e-9:
                raise RuntimeError("Foundation 4 Y1-Y3 raw Shapley semantics drifted")
            reconstructed = (
                estimate.current_intrinsic_raw_y1_y3
                + estimate.long_horizon_raw_y4_y7_reference
                + estimate.terminal_raw_y8_plus_reference
            )
            if abs(reconstructed - estimate.raw_career_forward_reference) > 1e-9:
                raise RuntimeError("Foundation 4 career-forward economics do not reconcile")

        after = _heavy_work_coordinator.snapshot()
        if after.peak_rss_bytes > after.memory_budget_bytes:
            raise RuntimeError(
                "Foundation 4 acceptance exceeded the engineering memory budget: "
                f"{after.peak_rss_bytes} > {after.memory_budget_bytes}"
            )
        _foundation4_acceptance_state.clear()
        _foundation4_acceptance_state.update(
            status="pass",
            contract="foundation4-shadow-acceptance-v1",
            mode=mode,
            league_state_id=context.league_state.state_id,
            dependency_fingerprint=foundation4_record.intrinsic_input_fingerprint,
            semantic_input_fingerprint=contract.input_fingerprint,
            player_count=contract.player_count,
            current_intrinsic_player_count=len(current_record.contract.estimates),
            long_horizon_player_count=len(component.estimates),
            aggregation=contract.aggregation,
            current_intrinsic_replaced=False,
            display_scaling_applied=False,
            market_inputs_used=False,
            rss_before_bytes=before.current_rss_bytes,
            rss_after_bytes=after.current_rss_bytes,
            peak_rss_bytes=after.peak_rss_bytes,
            memory_budget_bytes=after.memory_budget_bytes,
        )
        logging.getLogger("uvicorn.error").info(
            "FSFFL FOUNDATION4 SHADOW ACCEPTANCE PASS data=%s",
            _foundation4_acceptance_state,
        )
    except Exception as exc:
        _foundation4_acceptance_state.clear()
        _foundation4_acceptance_state.update(
            status="fail",
            contract="foundation4-shadow-acceptance-v1",
            mode=mode,
            error_type=type(exc).__name__,
            reason=str(exc),
        )
        logging.getLogger("uvicorn.error").exception(
            "FSFFL FOUNDATION4 SHADOW ACCEPTANCE FAILED"
        )


def _maybe_start_foundation4_shadow_acceptance() -> None:
    enabled = os.getenv("FSFFL_RUN_FOUNDATION4_ACCEPTANCE", "0").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    with _foundation4_acceptance_lock:
        if _foundation4_acceptance_state.get("status") == "running":
            return
        _foundation4_acceptance_state.clear()
        _foundation4_acceptance_state.update(
            status="running",
            contract="foundation4-shadow-acceptance-v1",
            mode=os.getenv("FSFFL_FOUNDATION4_ACCEPTANCE_MODE", "build").strip().lower(),
        )
    Thread(
        target=_run_foundation4_shadow_acceptance,
        name="fsffl-foundation4-shadow-acceptance",
        daemon=True,
    ).start()


def _acceptance_surface_probe(label: str, context) -> dict[str, object]:
    state = context.league_state
    if state is None:
        raise RuntimeError(f"{label}: canonical State is unavailable")
    state_only = context.selected_team_id is None
    team_state = None
    if not state_only:
        team_state = next(
            (row for row in state.team_states if row.team_id == context.selected_team_id),
            None,
        )
        if team_state is None or not team_state.roster:
            raise RuntimeError(f"{label}: canonical managed roster is blank")

    def call(path: str, **kwargs):
        return _presentation_route_endpoint(path)(user_id=context.user_id, **kwargs)

    # The browser journey hydrates primary surfaces sequentially. The acceptance
    # harness must not manufacture a larger resident set by retaining every full
    # response payload in one Python frame until the final assertion.
    freshness: dict[str, object] = {}
    continuity_modes: dict[str, object] = {}
    publication_generations: dict[str, object] = {}
    metrics: dict[str, object] = {}

    def inspect(surface: str, payload: object) -> None:
        if not isinstance(payload, dict) or not payload:
            raise RuntimeError(f"{label}: {surface} presentation is blank")
        freshness[surface] = (
            payload.get("intelligence_freshness") or {}
        ).get("status")
        continuity_modes[surface] = (
            payload.get("presentation_continuity") or {}
        ).get("mode")
        publication_generations[surface] = payload.get(
            "publication_generation_id"
        )
        if surface == "franchise":
            metrics["franchise_team_id"] = payload.get("team_id")
        elif surface == "league":
            metrics["league_standings_count"] = len(payload.get("standings") or ())
            metrics["league_simulation_status"] = (
                payload.get("simulation") or {}
            ).get("status")
        elif surface == "market":
            metrics["market_status"] = payload.get("status")
        elif surface == "market_value_lenses":
            metrics["market_player_count"] = len(payload.get("players") or ())

    surface_requests = (
        (
            ("context", "/api/product-context", {}),
            ("league", "/api/league/atlas", {}),
        )
        if state_only
        else (
            ("context", "/api/product-context", {}),
            ("home", "/api/home", {}),
            ("franchise", "/api/my-team", {}),
            ("league", "/api/league/atlas", {}),
            ("market", "/api/opportunities/workspace", {}),
            ("market_value_lenses", "/api/league/value-lenses", {"universe": "all"}),
            (
                "market_value_lenses_rostered",
                "/api/league/value-lenses",
                {"universe": "rostered"},
            ),
        )
    )
    surface_latency_seconds: dict[str, float] = {}
    for surface, path, kwargs in surface_requests:
        started = monotonic()
        payload = call(path, **kwargs)
        surface_latency_seconds[surface] = round(monotonic() - started, 3)
        inspect(surface, payload)
        del payload
        # This mirrors independent request lifetimes in the hosted browser path and
        # prevents acceptance instrumentation from retaining transient payload graphs.
        gc.collect()

    stale_count = sum(
        1 for value in freshness.values() if value == "stale_last_good"
    )
    generation_ids = {
        str(value)
        for value in publication_generations.values()
        if value is not None and str(value).strip()
    }
    if len(generation_ids) > 1:
        raise RuntimeError(
            f"{label}: cross-surface publication generations diverged: "
            f"{publication_generations}"
        )
    readiness = app.state.capability_readiness_reader(context)
    publication = dict(readiness.get("publication") or {})
    reconciliation = dict(readiness.get("reconciliation") or {})
    runtime_generation_id = readiness.get("publication_generation_id")
    if generation_ids and runtime_generation_id not in generation_ids:
        raise RuntimeError(
            f"{label}: surfaces do not match published runtime generation: "
            f"runtime={runtime_generation_id} surfaces={publication_generations}"
        )
    return {
        "league_id": state.league.league_id,
        "state_id": state.state_id,
        "selected_team_id": context.selected_team_id,
        "state_only": state_only,
        "canonical_roster_count": (
            len(team_state.roster) if team_state is not None else None
        ),
        **metrics,
        "readiness_status": readiness.get("overall_status"),
        "readiness_as_of": readiness.get("as_of"),
        "working_generation_active": publication.get("working_generation_active"),
        "publication_status": publication.get("status"),
        "publication_target_state_id": publication.get("target_state_id"),
        "reconciliation_status": reconciliation.get("status"),
        "reconciliation_target_state_id": reconciliation.get("target_state_id"),
        "reconciliation_published_state_id": reconciliation.get("published_state_id"),
        "presentation_freshness": freshness,
        "presentation_modes": continuity_modes,
        "publication_generations": publication_generations,
        "publication_generation_id": runtime_generation_id,
        "stale_surface_count": stale_count,
        "presentation_snapshot_available": (
            (readiness.get("served_last_good") or {}).get(
                "presentation_available", False
            )
        ),
        "surface_latency_seconds": surface_latency_seconds,
        "max_surface_latency_seconds": (
            max(surface_latency_seconds.values())
            if surface_latency_seconds
            else 0.0
        ),
        "total_surface_latency_seconds": round(
            sum(surface_latency_seconds.values()),
            3,
        ),
    }


def _acceptance_history_probe(label: str, context) -> dict[str, object]:
    state = context.league_state
    if state is None:
        raise RuntimeError(f"{label}: canonical State is unavailable")

    cold_state_only = label == "cold_pi_history_during_initial_reconciliation"
    roster_ids: list[str] = []
    if context.selected_team_id is not None:
        selected_state = next(
            (
                row
                for row in state.team_states
                if row.team_id == context.selected_team_id
            ),
            None,
        )
        if selected_state is not None:
            roster_ids = [
                entry.player_id for entry in selected_state.roster
            ]

    intrinsic: dict[str, object] = {
        "status": "building",
        "build_status": "not_required_for_state_only_history",
    }
    contract = None
    years: list[int] = []

    if cold_state_only:
        canonical_player_ids = {item.player_id for item in state.players}
        canonical_roster_ids = [
            item for item in roster_ids if item in canonical_player_ids
        ]
        preferred = "sleeper:player:4881"
        player_id = (
            preferred
            if preferred in canonical_roster_ids
            else (canonical_roster_ids[0] if canonical_roster_ids else None)
        )
        if player_id is None:
            raise RuntimeError(
                f"{label}: no rostered player is present in canonical player State"
            )
    else:
        intrinsic = _reconcile_hosted_intrinsic(context)
        intrinsic_record = _shapley_intrinsic_coordinator.current(context)
        contract = intrinsic_record.contract if intrinsic_record is not None else None
        if intrinsic.get("status") != "full" or contract is None:
            raise RuntimeError(
                f"{label}: governed Intrinsic is not reusable/available: {intrinsic}"
            )

        governed_ids = {item.player_id for item in contract.estimates}
        preferred = "sleeper:player:4881"
        player_id = (
            preferred
            if preferred in governed_ids
            else next((item for item in roster_ids if item in governed_ids), None)
            or next(iter(governed_ids), None)
        )
        if player_id is None:
            raise RuntimeError(f"{label}: no governed player is available")

        overview = build_player_intelligence_overview(
            context,
            player_id,
            intrinsic=contract,
            future_cache=_player_future_forecast_cache,
        )
        years = sorted(
            int(item["year_index"])
            for item in overview.get("forecast", {}).get("rows", [])
            if item.get("year_index") is not None
        )
        if 2 not in years or 3 not in years:
            raise RuntimeError(f"{label}: Player Intelligence lacks Y2/Y3: {years}")

    history = getattr(app.state, "player_history_coordinator", None)
    if history is None:
        raise RuntimeError(f"{label}: shared PI history coordinator is unavailable")
    deadline = monotonic() + 180.0
    started = monotonic()
    capacity_waits = 0
    while monotonic() < deadline:
        try:
            record = history.request(context, player_id)
        except PlayerHistoryCapacityError:
            capacity_waits += 1
            sleep(0.25)
            continue
        if record.status == PlayerHistoryBuildStatus.COMPLETED:
            return {
                "league_id": state.league.league_id,
                "state_id": state.state_id,
                "player_id": player_id,
                "history_status": record.status.value,
                "history_seasons": len(record.seasons),
                "capacity_waits": capacity_waits,
                "elapsed_seconds": round(monotonic() - started, 3),
                "intrinsic_status": intrinsic.get("status"),
                "intrinsic_build_status": intrinsic.get("build_status"),
                "forecast_years": years,
                "state_only_during_enrichment": cold_state_only,
            }
        if record.status == PlayerHistoryBuildStatus.FAILED:
            raise RuntimeError(
                f"{label}: PI history failed: {record.error or 'unknown error'}"
            )
        sleep(0.25)
    raise RuntimeError(f"{label}: PI history timed out")


def _runtime_acceptance_resource_reader() -> dict[str, object]:
    return {
        **dict(_heavy_work_coordinator.snapshot().__dict__),
        "recent_resource_boundaries": _state_resource_boundary.snapshot(),
    }


def _runtime_acceptance_process_identity() -> str:
    return f"pid:{os.getpid()}"


def _clone_acceptance_presentation_snapshot(
    source_user_id: str,
    acceptance_user_id: str,
    source_context: object,
) -> str:
    """Copy one validated governed presentation into the isolated acceptance scope."""

    if _persistence_store is None:
        raise RuntimeError("Acceptance presentation cloning requires persistence")
    state = getattr(source_context, "league_state", None)
    selected_team_id = getattr(source_context, "selected_team_id", None)
    if state is None:
        raise RuntimeError("Acceptance presentation source State is unavailable")

    source_manifest = _persistence_store.get_reusable_artifact(
        _manifest_key(
            user_id=source_user_id,
            league_id=state.league.league_id,
            league_state_id=state.state_id,
        )
    )
    if source_manifest is None:
        raise RuntimeError("Acceptance presentation source manifest is unavailable")
    manifest_payload = dict(source_manifest.payload)
    promotion_id = str(manifest_payload.get("promotion_id") or "").strip()
    if (
        not promotion_id
        or manifest_payload.get("selected_team_id") != selected_team_id
    ):
        raise RuntimeError("Acceptance presentation source identity is inconsistent")

    available = set(manifest_payload.get("surfaces") or ())
    if not set(REQUIRED_PRESENTATION_SURFACES).issubset(available):
        raise RuntimeError("Acceptance presentation source is incomplete")

    now = utc_now()
    for surface in REQUIRED_PRESENTATION_SURFACES:
        source_surface = _persistence_store.get_reusable_artifact(
            _surface_key(
                user_id=source_user_id,
                league_id=state.league.league_id,
                promotion_id=promotion_id,
                surface=surface,
            )
        )
        if source_surface is None:
            raise RuntimeError(
                f"Acceptance presentation source surface is unavailable: {surface}"
            )
        _persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=_surface_key(
                    user_id=acceptance_user_id,
                    league_id=state.league.league_id,
                    promotion_id=promotion_id,
                    surface=surface,
                ),
                payload=dict(source_surface.payload),
                computed_at=now,
            )
        )

    _persistence_store.put_artifact(
        ReusableArtifactRecord(
            key=_manifest_key(
                user_id=acceptance_user_id,
                league_id=state.league.league_id,
                league_state_id=state.state_id,
            ),
            payload=manifest_payload,
            computed_at=now,
        )
    )
    return promotion_id


def _maybe_start_state_first_production_acceptance() -> None:
    if not production_acceptance_startup_enabled(os.environ):
        return
    if _persistence_store is None:
        _runtime_availability_acceptance_state.update(
            status="fail",
            reason="Production persistence is unavailable.",
        )
        logging.getLogger("uvicorn.error").error(
            "FSFFL RUNTIME AVAILABILITY ACCEPTANCE FAILED production persistence is unavailable"
        )
        return
    acceptance_user = os.getenv(
        "FSFFL_RUNTIME_AVAILABILITY_ACCEPTANCE_USER",
        "runtime-availability-production-acceptance",
    ).strip()
    if not acceptance_user:
        _runtime_availability_acceptance_state.update(
            status="fail",
            reason="Isolated acceptance user id is blank.",
        )
        return
    delay_seconds = max(
        0.0,
        float(os.getenv("FSFFL_RUNTIME_ACCEPTANCE_DELAY_SECONDS", "5")),
    )
    acceptance_mode = os.getenv(
        "FSFFL_RUNTIME_AVAILABILITY_ACCEPTANCE_MODE",
        "full",
    ).strip().lower()
    if acceptance_mode not in {"full", "journey", "restore", "restored_refresh"}:
        _runtime_availability_acceptance_state.update(
            status="fail",
            reason=f"Unsupported runtime acceptance mode: {acceptance_mode}",
        )
        return
    stage_partial_restore = (
        os.getenv(
            "FSFFL_RUNTIME_AVAILABILITY_ACCEPTANCE_STAGE_PARTIAL",
            "0",
        ).strip().lower()
        in {"1", "true", "yes", "on"}
    )
    acceptance_source_user = os.getenv(
        "FSFFL_RUNTIME_AVAILABILITY_ACCEPTANCE_SOURCE_USER",
        _beta_restore_user,
    ).strip()
    if stage_partial_restore:
        acceptance_user = resolve_staged_acceptance_user(
            source_user_id=acceptance_source_user,
            configured_acceptance_user_id=acceptance_user,
        )
    if stage_partial_restore and acceptance_mode != "restored_refresh":
        _runtime_availability_acceptance_state.update(
            status="fail",
            reason="Partial acceptance staging is valid only for restored_refresh mode.",
        )
        return
    _runtime_availability_acceptance_state.clear()
    _runtime_availability_acceptance_state.update(
        status="scheduled",
        contract="runtime-availability-acceptance-v1",
        user_id=acceptance_user,
        mode=acceptance_mode,
        delay_seconds=delay_seconds,
        stage_partial_restore=stage_partial_restore,
        source_user_id=(acceptance_source_user if stage_partial_restore else None),
    )

    def run() -> None:
        try:
            sleep(delay_seconds)
            if not _startup_restore_complete.wait(timeout=180.0):
                raise RuntimeError("Hosted lightweight startup restore did not complete")
            _runtime_availability_acceptance_state["status"] = "running"
            if acceptance_mode == "restored_refresh":
                if stage_partial_restore:
                    staged = stage_restored_refresh_partial_acceptance(
                        store=_runtime_store,
                        source_user_id=acceptance_source_user,
                        acceptance_user_id=acceptance_user,
                        clone_presentation_snapshot=(
                            _clone_acceptance_presentation_snapshot
                        ),
                    )
                    _logger.info(
                        "FSFFL RUNTIME AVAILABILITY ACCEPTANCE staged partial data=%s",
                        staged,
                    )
                    release_unused_process_memory(
                        label="after-runtime-acceptance-partial-staging"
                    )
                report = run_state_first_restored_refresh_acceptance(
                    store=_runtime_store,
                    user_id=acceptance_user,
                    start_sync_reconciliation=app.state.start_intelligence_sync_reconciliation,
                    jobs=app.state.intelligence_jobs,
                    capability_reader=app.state.capability_readiness_reader,
                    surface_probe=_acceptance_surface_probe,
                    resource_reader=_runtime_acceptance_resource_reader,
                )
            else:
                report = run_state_first_production_acceptance(
                    store=_runtime_store,
                    user_id=acceptance_user,
                    state_loader=default_sleeper_state_loader,
                    start_reconciliation=app.state.start_intelligence_reconciliation,
                    start_sync_reconciliation=app.state.start_intelligence_sync_reconciliation,
                    jobs=app.state.intelligence_jobs,
                    capability_reader=app.state.capability_readiness_reader,
                    surface_probe=_acceptance_surface_probe,
                    history_probe=_acceptance_history_probe,
                    resource_reader=_runtime_acceptance_resource_reader,
                    process_identity_reader=_runtime_acceptance_process_identity,
                    state_activator=app.state.activate_state_with_resource_boundary,
                    restore_only=acceptance_mode == "restore",
                    journey_only=acceptance_mode == "journey",
                )
            _runtime_availability_acceptance_state.clear()
            _runtime_availability_acceptance_state.update(
                status="pass",
                contract="runtime-availability-acceptance-v1",
                mode=acceptance_mode,
                report=report,
            )
            logging.getLogger("uvicorn.error").info(
                "FSFFL RUNTIME AVAILABILITY ACCEPTANCE PASS peak_rss=%s budget=%s",
                report.get("peak_rss_bytes"),
                report.get("memory_budget_bytes"),
            )
        except Exception as exc:
            _runtime_availability_acceptance_state.clear()
            _runtime_availability_acceptance_state.update(
                status="fail",
                contract="runtime-availability-acceptance-v1",
                mode=acceptance_mode,
                error_type=type(exc).__name__,
                reason=str(exc),
            )
            logging.getLogger("uvicorn.error").exception(
                "FSFFL RUNTIME AVAILABILITY ACCEPTANCE FAILED"
            )

    Thread(
        target=run,
        name="fsffl-runtime-availability-acceptance",
        daemon=True,
    ).start()


@app.get("/health/product-acceptance")
def hosted_product_acceptance_health() -> dict[str, object]:
    """Non-sensitive production proof for product-path acceptance."""

    return dict(_product_acceptance_state)


@app.get("/health/runtime-availability-acceptance")
def hosted_runtime_availability_acceptance_health() -> dict[str, object]:
    """Non-sensitive proof for the explicit hosted combined acceptance journey."""

    return dict(_runtime_availability_acceptance_state)


@app.get("/health/foundation4-shadow-acceptance")
def hosted_foundation4_shadow_acceptance_health() -> dict[str, object]:
    """Non-sensitive Foundation 4 materialization/restore/resource acceptance proof."""

    return dict(_foundation4_acceptance_state)


@app.get("/health/runtime-resources")
def hosted_runtime_resources() -> dict[str, object]:
    """Non-sensitive process resource/admission telemetry for beta acceptance."""

    snapshot = _heavy_work_coordinator.snapshot()
    return {
        "status": "ok",
        "contract": "runtime-resource-telemetry-v2:bounded-redacted-boundaries",
        **snapshot.__dict__,
        "recent_resource_boundaries": _state_resource_boundary.snapshot(),
    }


@app.post("/api/runtime/product-acceptance")
def trigger_hosted_product_acceptance(
    _user_id: str = Depends(_webapp.require_beta_user),
) -> dict[str, object]:
    started = _start_hosted_product_acceptance()
    return {
        "started": started,
        **dict(_product_acceptance_state),
    }
install_annual_preseason_scheduler_route(
    app,
    persistence_store=_persistence_store,
)
install_hosted_connect_routes(
    app,
    runtime_store=_runtime_store,
    state_loader=_load_sleeper_state_under_heavy_claim,
    behavioral_coordinator=_behavioral_coordinator,
    persistence_store=_persistence_store,
    sync_probe_loader=lambda league_id: _sleeper_probe_source.fetch_sync_probe(
        league_external_id=league_id
    ),
    intelligence_reconciler=app.state.start_intelligence_reconciliation,
    state_activator=app.state.activate_state_with_resource_boundary,
    full_refresh_seconds=_full_refresh_seconds,
)
install_in_season_forecast_routes(
    app,
    runtime_store=_runtime_store,
    persistence_store=_persistence_store,
    projection_history_store=_projection_history_store,
)
install_intrinsic_value_v1_routes(app, runtime_store=_runtime_store)
install_shapley_intrinsic_routes(
    app,
    runtime_store=_runtime_store,
    contract_loader=_shapley_intrinsic_loader,
    background_coordinator=_shapley_intrinsic_coordinator,
)
install_career_intrinsic_routes(
    app,
    runtime_store=_runtime_store,
    loader=_career_intrinsic_loader,
    coordinator=_career_intrinsic_coordinator,
    presentation_payload_loader=_presentation_payload_loader,
)
install_intrinsic_market_discovery_routes(
    app,
    runtime_store=_runtime_store,
    contract_loader=_shapley_intrinsic_loader,
    require_user=_webapp.require_beta_user,
    background_coordinator=_shapley_intrinsic_coordinator,
)
install_league_value_lens_routes(
    app,
    runtime_store=_runtime_store,
    contract_loader=_shapley_intrinsic_loader,
    require_user=_webapp.require_beta_user,
    background_coordinator=_shapley_intrinsic_coordinator,
    presentation_payload_loader=_presentation_payload_loader,
)
install_player_intelligence_routes(
    app,
    runtime_store=_runtime_store,
    require_user=_webapp.require_beta_user,
    intrinsic_coordinator=_shapley_intrinsic_coordinator,
    future_cache=_player_future_forecast_cache,
    persistence_store=_persistence_store,
    heavy_work_coordinator=_heavy_work_coordinator,
)
install_provisional_k_dst_routes(
    app,
    runtime_store=_runtime_store,
    persistence_store=_persistence_store,
    require_user=_webapp.require_beta_user,
)
install_focused_opportunity_routes(
    app,
    runtime_store=_runtime_store,
    workspace_builder=_webapp.build_opportunity_workspace,
    candidate_builder=_cached_opportunity_search,
    require_user=_webapp.require_beta_user,
    enrichment_coordinator=_market_decision_enrichment,
)
install_progressive_delivery_routes(
    app,
    runtime_store=_runtime_store,
    workspace_builder=_webapp.build_opportunity_workspace,
    require_user=_webapp.require_beta_user,
)
install_quick_frontier_routes(
    app,
    runtime_store=_runtime_store,
    require_user=_webapp.require_beta_user,
)
install_phase1_latency_routes(app, persistence_store=_persistence_store)
install_latency_observability(app)
install_foreground_pressure(app)


def _presentation_route_endpoint(path: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and "GET" in getattr(route, "methods", set()):
            return route.endpoint
    raise RuntimeError(f"presentation continuity route is unavailable: {path}")


_dynasty_followup_lock = RLock()
_dynasty_followups: set[tuple[str, str, str]] = set()


def _prepare_presentation_for_user(user_id: str, context) -> None:
    """Kick Dynasty preparation without putting it on the core publication path."""
    if context.league_state is None:
        return
    record = _career_intrinsic_coordinator.request(context)
    if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
        key = (
            user_id,
            context.league_state.state_id,
            record.intrinsic_input_fingerprint,
        )
        with _dynasty_followup_lock:
            if key in _dynasty_followups:
                return
            _dynasty_followups.add(key)

        def completed(terminal_record) -> None:
            try:
                if (
                    terminal_record.status == IntrinsicBuildStatus.COMPLETED
                    and terminal_record.contract is not None
                ):
                    Thread(
                        target=_publish_dynasty_presentation_followup,
                        args=(user_id, context.league_state.state_id, key),
                        daemon=True,
                        name="fsffl-dynasty-presentation-followup",
                    ).start()
                else:
                    with _dynasty_followup_lock:
                        _dynasty_followups.discard(key)
            except Exception:
                with _dynasty_followup_lock:
                    _dynasty_followups.discard(key)
                _logger.exception(
                    "FSFFL Dynasty completion callback failed user=%s state=%s",
                    user_id,
                    context.league_state.state_id,
                )

        _career_intrinsic_coordinator.add_terminal_callback(context, completed)

def _promote_presentation_for_user(user_id: str, context) -> object | None:
    if not _presentation_continuity.enabled or context.league_state is None:
        return None
    # Prime the bounded Future Forecast cache while the exact authoritative
    # Forecast is attached. A later same-league State reconciliation may then keep
    # Y2/Y3 visible as explicitly stale-last-good without rebuilding Forecast on a
    # foreground PI request.
    if context.forecast_evidence is not None:
        try:
            contract, freshness = _player_future_forecast_cache.resolve(context)
            _logger.info(
                "FSFFL PI future continuity prime state=%s status=%s rows=%s",
                context.league_state.state_id,
                freshness,
                len(contract.forecasts) if contract is not None else 0,
            )
        except Exception as exc:
            _logger.warning(
                "FSFFL PI future continuity prime unavailable state=%s error=%s",
                context.league_state.state_id,
                exc,
            )
    # Snapshot exactly the existing governed presentation contracts. Builders run
    # sequentially and each payload is persisted before the next is composed.
    dynasty_last_good = None
    dynasty_record = _career_intrinsic_coordinator.current(context)
    if (
        dynasty_record is None
        or dynasty_record.status != IntrinsicBuildStatus.COMPLETED
        or dynasty_record.contract is None
        or dynasty_record.league_state_id != context.league_state.state_id
    ):
        # Capture verified last-good Dynasty before promote() enters its recursive
        # read fence. The payload is copied into the new atomic generation rather
        # than referencing/mixing an older generation in place.
        candidate = _presentation_continuity.load_for_runtime(
            user_id=user_id,
            runtime=context,
            surface=LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
        )
        if candidate is not None and candidate.get("status") == "ready":
            dynasty_last_good = dict(candidate)
            dynasty_last_good["dynasty_evidence_status"] = "last_good"
            dynasty_last_good["dynasty_evidence_state_id"] = candidate.get(
                "league_state_id"
            )
            dynasty_last_good["dynasty_evidence_publication_generation_id"] = (
                candidate.get("publication_generation_id")
            )
            # The copied evidence is now a governed value inside the new State's
            # atomic presentation publication. Keep its source coordinates above
            # instead of making the surface look like it belongs to the old State.
            dynasty_last_good["league_state_id"] = context.league_state.state_id
            dynasty_last_good.pop("publication_generation_id", None)
            dynasty_last_good.pop("intelligence_freshness", None)
            dynasty_last_good.pop("presentation_continuity", None)

    specs = (
        (HOME_SURFACE, "/api/home", {}),
        (FRANCHISE_SURFACE, "/api/my-team", {}),
        (LEAGUE_ATLAS_SURFACE, "/api/league/atlas", {}),
        (LEAGUE_TEAM_VIEWS_SURFACE, "/api/league/team-views", {}),
        (LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE, "/api/league/dynasty-position-rooms", {}),
        (
            MARKET_WORKSPACE_SURFACE,
            None,
            {
                "presentation_shell": True,
            },
        ),
        (
            MARKET_VALUE_LENSES_ROSTERED_SURFACE,
            "/api/league/value-lenses",
            {"universe": "rostered"},
        ),
        (
            MARKET_VALUE_LENSES_ALL_SURFACE,
            "/api/league/value-lenses",
            {"universe": "all"},
        ),
    )
    builders = []
    for surface, path, kwargs in specs:
        if surface == MARKET_WORKSPACE_SURFACE and kwargs.get("presentation_shell"):
            builders.append(
                (
                    surface,
                    lambda: _webapp.build_opportunity_workspace(
                        context,
                        candidate_limit=0,
                        bilateral_evaluation_limit=0,
                    ),
                )
            )
            continue
        endpoint = _presentation_route_endpoint(path)
        if surface == LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE:
            def build_dynasty_rooms(endpoint=endpoint, kwargs=kwargs):
                record = _career_intrinsic_coordinator.current(context)
                if (
                    record is None
                    or record.status != IntrinsicBuildStatus.COMPLETED
                    or record.contract is None
                    or record.league_state_id != context.league_state.state_id
                ):
                    if dynasty_last_good is not None:
                        return dict(dynasty_last_good)
                    preparing = bool(
                        record is not None
                        and record.status in {
                            IntrinsicBuildStatus.QUEUED,
                            IntrinsicBuildStatus.RUNNING,
                        }
                    )
                    return {
                        "status": "preparing" if preparing else "unavailable",
                        "league_state_id": context.league_state.state_id,
                        "reason": (
                            "Dynasty position-room evidence is preparing in the background"
                            if preparing
                            else "Dynasty position-room evidence is unsupported or unavailable for this State"
                        ),
                    }
                payload = endpoint(user_id=user_id, **kwargs)
                if payload.get("status") != "ready":
                    return {
                        "status": "unavailable",
                        "league_state_id": context.league_state.state_id,
                        "reason": payload.get("reason") or "Dynasty position-room evidence is unavailable",
                    }
                return payload
            builders.append((surface, build_dynasty_rooms))
            continue
        builders.append(
            (
                surface,
                lambda endpoint=endpoint, kwargs=kwargs: endpoint(
                    user_id=user_id,
                    **kwargs,
                ),
            )
        )
    return _presentation_continuity.promote(
        user_id=user_id,
        runtime=context,
        builders=tuple(builders),
    )


def _publish_dynasty_presentation_followup(
    user_id: str,
    expected_state_id: str,
    key: tuple[str, str, str],
) -> None:
    """Atomically republish presentation only after late Dynasty completion."""
    try:
        with _runtime_store.publication_sequence(user_id):
            context = _runtime_store.get(user_id)
            if (
                context.league_state is None
                or context.league_state.state_id != expected_state_id
            ):
                return
            record = _career_intrinsic_coordinator.current(context)
            if (
                record is None
                or record.status != IntrinsicBuildStatus.COMPLETED
                or record.contract is None
                or record.league_state_id != expected_state_id
            ):
                return
            promotion = _promote_presentation_for_user(user_id, context)
            if promotion is None:
                return
            _runtime_store.bind_publication_generation_id(
                user_id,
                promotion.publication_generation_id,
            )
            _logger.info(
                "FSFFL Dynasty presentation-only follow-up promoted user=%s state=%s generation=%s",
                user_id,
                expected_state_id,
                promotion.publication_generation_id,
            )
    except Exception:
        _logger.exception(
            "FSFFL Dynasty presentation-only follow-up failed user=%s state=%s",
            user_id,
            expected_state_id,
        )
    finally:
        with _dynasty_followup_lock:
            _dynasty_followups.discard(key)


app.state.presentation_preparer = _prepare_presentation_for_user
app.state.presentation_promoter = _promote_presentation_for_user


def _run_lightweight_startup_restore() -> None:
    _startup_restore_state.clear()
    _startup_restore_state["status"] = "running"
    try:
        if _beta_restore_user:
            context = _runtime_store.restore_user(_beta_restore_user)
            if context.league_state is not None:
                try:
                    _shapley_intrinsic_coordinator.restore_compatible_staged(context)
                except Exception as exc:
                    _logger.warning(
                        "FSFFL startup Intrinsic compatible-restore unavailable user=%s error=%s",
                        _beta_restore_user,
                        exc,
                    )
                try:
                    restored_f4 = _career_intrinsic_coordinator.restore_compatible_staged(
                        context
                    )
                    if restored_f4 is not None:
                        _logger.info(
                            "FSFFL Career Intrinsic restored compatible production artifact user=%s state=%s estimates=%s",
                            _beta_restore_user,
                            context.league_state.state_id,
                            len(restored_f4.contract.estimates)
                            if restored_f4.contract is not None
                            else 0,
                        )
                except Exception as exc:
                    _logger.warning(
                        "FSFFL Career Intrinsic compatible-restore unavailable user=%s error=%s",
                        _beta_restore_user,
                        exc,
                    )
                context = _runtime_store.get(_beta_restore_user)
                terminal = bool(
                    context.forecast_evidence is not None
                    and context.value_evidence is not None
                    and (
                        context.simulation_analytics is not None
                        or not context.forecast_evidence.uncertainty_ready
                    )
                )
                if terminal:
                    try:
                        # A pre-#382 v1 snapshot remains valid evidence for migration,
                        # but it is never served as a v2 snapshot. Prepare Dynasty
                        # opportunistically, then republish the already-restored core
                        # runtime into the new manifest version without provider work.
                        legacy_migration = _presentation_continuity.legacy_snapshot_available(
                            user_id=_beta_restore_user,
                            league_id=context.league_state.league.league_id,
                            league_state_id=context.league_state.state_id,
                            selected_team_id=context.selected_team_id,
                        )
                        # Startup never waits for Dynasty. Reuse/restore exact
                        # evidence when available; otherwise start it in the background
                        # and publish core/presentation continuity immediately.
                        _prepare_presentation_for_user(_beta_restore_user, context)
                        promotion = _promote_presentation_for_user(
                            _beta_restore_user,
                            context,
                        )
                        if promotion is not None:
                            _runtime_store.bind_publication_generation_id(
                                _beta_restore_user,
                                promotion.publication_generation_id,
                            )
                    except Exception as exc:
                        _logger.warning(
                            "FSFFL startup presentation backfill unavailable user=%s error=%s",
                            _beta_restore_user,
                            exc,
                        )
        _startup_restore_state["status"] = "complete"
        _log_startup_runtime_readiness()
    except Exception as exc:
        _startup_restore_state.update(
            status="failed",
            error_type=type(exc).__name__,
            reason=str(exc),
        )
        logging.getLogger("uvicorn.error").exception(
            "FSFFL lightweight startup restore failed"
        )
    finally:
        _startup_restore_complete.set()


def _start_lightweight_startup_restore() -> None:
    Thread(
        target=_run_lightweight_startup_restore,
        name="fsffl-startup-restore",
        daemon=True,
    ).start()


app.router.add_event_handler("startup", _start_lightweight_startup_restore)
app.router.add_event_handler("startup", _maybe_start_state_first_production_acceptance)
app.router.add_event_handler("startup", _maybe_start_foundation4_shadow_acceptance)
