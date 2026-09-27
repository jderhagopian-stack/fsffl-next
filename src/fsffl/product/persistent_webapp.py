from __future__ import annotations

import logging
import os
from threading import Event, RLock, Thread
from time import monotonic, sleep

from fastapi import Depends

from fsffl.persistence import (
    persistence_store_from_env,
    projection_history_store_from_env,
    state_snapshot_store_from_env,
)
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability

from . import market_discovery_runtime as _market_discovery_runtime
from . import opportunity_workspace as _opportunity_workspace
from . import webapp as _webapp
from .annual_preseason_scheduler_routes import install_annual_preseason_scheduler_route
from .behavioral_runtime import BehavioralRuntimeCoordinator, default_behavioral_store
from .focused_opportunity_routes import install_focused_opportunity_routes
from .foreground_pressure import install_foreground_pressure
from .forecast_resilience import (
    make_preseason_baseline_authority_loader,
    make_resilient_forecast_loader,
)
from .hosted_connect import install_hosted_connect_routes
from .in_season_forecast_routes import install_in_season_forecast_routes
from .intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
)
from .intrinsic_market_discovery_routes import install_intrinsic_market_discovery_routes
from .intrinsic_value_routes import install_intrinsic_value_v1_routes
from .league_value_lens_routes import install_league_value_lens_routes
from .latency_observability import install_latency_observability
from .market_economics_cache import make_cached_candidate_economics
from .opportunity_search_cache import make_cached_opportunity_search
from .opportunity_workspace_cache import make_cached_opportunity_workspace
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .presentation_continuity import (
    FRANCHISE_SURFACE,
    HOME_SURFACE,
    LEAGUE_ATLAS_SURFACE,
    LEAGUE_TEAM_VIEWS_SURFACE,
    MARKET_VALUE_LENSES_ALL_SURFACE,
    MARKET_WORKSPACE_SURFACE,
    PresentationContinuityStore,
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
)
from .progressive_delivery_routes import install_progressive_delivery_routes
from .provisional_k_dst_routes import install_provisional_k_dst_routes
from .quick_frontier_routes import install_quick_frontier_routes
from .resource_coordinator import HeavyWorkCoordinator
from .runtime import default_sleeper_state_loader
from .scenario_cache import configure_scenario_cache_persistence
from .shapley_intrinsic_routes import install_shapley_intrinsic_routes
from .state_first_acceptance import run_state_first_production_acceptance


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
)
_player_future_forecast_cache = PlayerFutureForecastCache(
    future_forecast_builder=provide_vnext_future_forecast_contract,
    forecast_model_version=VNEXT_FORECAST_VERSION,
)
_shapley_intrinsic_coordinator = ShapleyIntrinsicBackgroundCoordinator(
    _shapley_intrinsic_loader,
    max_workers=1,
    intrinsic_input_fingerprint_resolver=(
        _shapley_intrinsic_loader.intrinsic_input_fingerprint
    ),
    heavy_work_coordinator=_heavy_work_coordinator,
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
        try:
            record = _shapley_intrinsic_coordinator.restore_compatible(context)
        except Exception as exc:
            _logger.warning(
                "FSFFL Intrinsic readiness compatible-restore failed state=%s error=%s",
                context.league_state.state_id,
                exc,
            )
        if record is None:
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
    payload["overall_status"] = (
        "rebuilding"
        if core_status == "rebuilding"
        else "full"
        if all(status == "full" for status in statuses)
        else "partial"
        if any(status not in {"unavailable", "not_configured"} for status in statuses)
        else "unavailable"
    )
    served = getattr(context, "served_intelligence", None)
    presentation_available = bool(
        served is not None
        and _presentation_continuity.has_snapshot(
            user_id=context.user_id,
            league_id=served.league_id,
            league_state_id=served.league_state_id,
        )
    )
    served_payload = dict(payload.get("served_last_good") or {})
    served_payload["presentation_available"] = presentation_available
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
    record = _shapley_intrinsic_coordinator.wait_for_terminal(context)
    readiness = _intrinsic_readiness_from_record(record)
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
_market_discovery_runtime.evaluate_candidate_economics = make_cached_candidate_economics(
    _market_discovery_runtime.evaluate_candidate_economics
)

# Build the expensive structural candidate catalog once per exact authoritative
# runtime. The normal Market workspace and subsequent Market Focus requests share
# that exact catalog; focus changes Search selection/order without rebuilding the
# same package universe or changing Value/Decision authority.
_cached_opportunity_search = make_cached_opportunity_search(
    _opportunity_workspace.build_roster_aware_trade_candidates
)
_opportunity_workspace.build_roster_aware_trade_candidates = _cached_opportunity_search

# Market navigation can issue the same workspace request repeatedly while the
# authoritative runtime is unchanged. Reuse the exact server-produced workspace
# instead of repeating Search + bounded Decision work. This wrapper is hosted-
# composition infrastructure only; the original builder remains authoritative.
_webapp.build_opportunity_workspace = make_cached_opportunity_workspace(
    _webapp.build_opportunity_workspace
)

def _presentation_payload_loader(user_id: str, context, surface: str):
    return _presentation_continuity.load_for_runtime(
        user_id=user_id,
        runtime=context,
        surface=surface,
    )


app = _webapp.create_app(
    runtime_store=_runtime_store,
    behavioral_coordinator=_behavioral_coordinator,
    forecast_loader=_forecast_loader,
    preseason_forecast_loader=_preseason_forecast_loader,
    state_snapshot_store=_state_snapshot_store,
    persistence_store=_persistence_store,
    capability_readiness_reader=_hosted_capability_readiness,
    product_capability_reconciler=_reconcile_hosted_intrinsic,
    heavy_work_coordinator=_heavy_work_coordinator,
    presentation_payload_loader=_presentation_payload_loader,
)

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


def _acceptance_surface_probe(label: str, context) -> dict[str, object]:
    state = context.league_state
    if state is None:
        raise RuntimeError(f"{label}: canonical State is unavailable")
    if context.selected_team_id is None:
        raise RuntimeError(f"{label}: managed team is unavailable")
    team_state = next(
        (row for row in state.team_states if row.team_id == context.selected_team_id),
        None,
    )
    if team_state is None or not team_state.roster:
        raise RuntimeError(f"{label}: canonical managed roster is blank")

    def call(path: str, **kwargs):
        return _presentation_route_endpoint(path)(user_id=context.user_id, **kwargs)

    home = call("/api/home")
    franchise = call("/api/my-team")
    atlas = call("/api/league/atlas")
    market = call("/api/opportunities/workspace")
    lenses = call("/api/league/value-lenses", universe="all")
    payloads = {
        "home": home,
        "franchise": franchise,
        "league": atlas,
        "market": market,
        "market_value_lenses": lenses,
    }
    for surface, payload in payloads.items():
        if not isinstance(payload, dict) or not payload:
            raise RuntimeError(f"{label}: {surface} presentation is blank")

    freshness = {
        surface: (payload.get("intelligence_freshness") or {}).get("status")
        for surface, payload in payloads.items()
    }
    continuity_modes = {
        surface: (payload.get("presentation_continuity") or {}).get("mode")
        for surface, payload in payloads.items()
    }
    stale_count = sum(
        1 for value in freshness.values() if value == "stale_last_good"
    )
    readiness = _hosted_capability_readiness(context)
    return {
        "league_id": state.league.league_id,
        "state_id": state.state_id,
        "selected_team_id": context.selected_team_id,
        "canonical_roster_count": len(team_state.roster),
        "franchise_team_id": franchise.get("team_id"),
        "league_standings_count": len(atlas.get("standings") or ()),
        "league_simulation_status": (atlas.get("simulation") or {}).get("status"),
        "market_status": market.get("status"),
        "market_player_count": len(lenses.get("players") or ()),
        "readiness_status": readiness.get("overall_status"),
        "readiness_as_of": readiness.get("as_of"),
        "presentation_freshness": freshness,
        "presentation_modes": continuity_modes,
        "stale_surface_count": stale_count,
        "presentation_snapshot_available": (
            (readiness.get("served_last_good") or {}).get(
                "presentation_available", False
            )
        ),
    }


def _acceptance_history_probe(label: str, context) -> dict[str, object]:
    state = context.league_state
    if state is None:
        raise RuntimeError(f"{label}: canonical State is unavailable")
    intrinsic = _reconcile_hosted_intrinsic(context)
    intrinsic_record = _shapley_intrinsic_coordinator.current(context)
    contract = intrinsic_record.contract if intrinsic_record is not None else None
    if intrinsic.get("status") != "full" or contract is None:
        raise RuntimeError(
            f"{label}: governed Intrinsic is not reusable/available: {intrinsic}"
        )

    governed_ids = {item.player_id for item in contract.estimates}
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
            roster_ids = list(selected_state.roster)
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
            }
        if record.status == PlayerHistoryBuildStatus.FAILED:
            raise RuntimeError(
                f"{label}: PI history failed: {record.error or 'unknown error'}"
            )
        sleep(0.25)
    raise RuntimeError(f"{label}: PI history timed out")


def _runtime_acceptance_resource_reader() -> dict[str, object]:
    return dict(_heavy_work_coordinator.snapshot().__dict__)


def _runtime_acceptance_process_identity() -> str:
    return f"pid:{os.getpid()}"


def _maybe_start_state_first_production_acceptance() -> None:
    enabled = any(
        os.getenv(name, "0").strip().lower() in {"1", "true", "yes", "on"}
        for name in (
            "FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE",
            "FSFFL_RUN_STATE_FIRST_ACCEPTANCE",
        )
    )
    if not enabled:
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
    _runtime_availability_acceptance_state.clear()
    _runtime_availability_acceptance_state.update(
        status="scheduled",
        contract="runtime-availability-acceptance-v1",
        user_id=acceptance_user,
        delay_seconds=delay_seconds,
    )

    def run() -> None:
        try:
            sleep(delay_seconds)
            if not _startup_restore_complete.wait(timeout=180.0):
                raise RuntimeError("Hosted lightweight startup restore did not complete")
            _runtime_availability_acceptance_state["status"] = "running"
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
            )
            _runtime_availability_acceptance_state.clear()
            _runtime_availability_acceptance_state.update(
                status="pass",
                contract="runtime-availability-acceptance-v1",
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


@app.get("/health/runtime-resources")
def hosted_runtime_resources() -> dict[str, object]:
    """Non-sensitive process resource/admission telemetry for beta acceptance."""

    snapshot = _heavy_work_coordinator.snapshot()
    return {
        "status": "ok",
        "contract": "runtime-resource-telemetry-v1",
        **snapshot.__dict__,
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
    state_loader=default_sleeper_state_loader,
    behavioral_coordinator=_behavioral_coordinator,
    persistence_store=_persistence_store,
    sync_probe_loader=lambda league_id: _sleeper_probe_source.fetch_sync_probe(
        league_external_id=league_id
    ),
    intelligence_reconciler=app.state.start_intelligence_reconciliation,
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


def _promote_presentation_for_user(user_id: str, context) -> object | None:
    if not _presentation_continuity.enabled or context.league_state is None:
        return None
    # Snapshot exactly the existing governed presentation contracts. Builders run
    # sequentially and each payload is persisted before the next is composed.
    specs = (
        (HOME_SURFACE, "/api/home", {}),
        (FRANCHISE_SURFACE, "/api/my-team", {}),
        (LEAGUE_ATLAS_SURFACE, "/api/league/atlas", {}),
        (LEAGUE_TEAM_VIEWS_SURFACE, "/api/league/team-views", {}),
        (MARKET_WORKSPACE_SURFACE, "/api/opportunities/workspace", {}),
        (
            MARKET_VALUE_LENSES_ALL_SURFACE,
            "/api/league/value-lenses",
            {"universe": "all"},
        ),
    )
    builders = []
    for surface, path, kwargs in specs:
        endpoint = _presentation_route_endpoint(path)
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


app.state.presentation_promoter = _promote_presentation_for_user


def _run_lightweight_startup_restore() -> None:
    _startup_restore_state.clear()
    _startup_restore_state["status"] = "running"
    try:
        if _beta_restore_user:
            context = _runtime_store.restore_user(_beta_restore_user)
            if context.league_state is not None:
                try:
                    _shapley_intrinsic_coordinator.restore_compatible(context)
                except Exception as exc:
                    _logger.warning(
                        "FSFFL startup Intrinsic compatible-restore unavailable user=%s error=%s",
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
                        _promote_presentation_for_user(_beta_restore_user, context)
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
