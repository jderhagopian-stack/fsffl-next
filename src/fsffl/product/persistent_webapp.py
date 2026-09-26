from __future__ import annotations

import logging
import os
from threading import Thread

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
from .player_intelligence import (
    PlayerFutureForecastCache,
    build_player_intelligence_overview,
)
from .player_intelligence_routes import install_player_intelligence_routes
from .phase1_latency import install_phase1_latency_routes
from .private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from .vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    provide_vnext_future_forecast_contract,
)
from .progressive_delivery_routes import install_progressive_delivery_routes
from .provisional_k_dst_routes import install_provisional_k_dst_routes
from .quick_frontier_routes import install_quick_frontier_routes
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
if _persistence_store is not None and _beta_restore_user:
    _runtime_store.restore_user(_beta_restore_user)

# Hosted Behavioral persistence validates its migrated schema when the Postgres
# adapter is first constructed. Build the shared adapter while the Render process is
# starting rather than on the first user status/Market request. Validation is
# read-only: governed migrations own schema/index/RLS creation. Failure remains
# non-fatal here; Behavioral evidence fails closed rather than blocking the product.
try:
    _behavioral_store = default_behavioral_store()
except Exception as exc:  # pragma: no cover - hosted infrastructure guard
    _behavioral_store = None
    _logger.warning("FSFFL Behavioral store prewarm unavailable; runtime will retry: %s", exc)

_behavioral_coordinator = BehavioralRuntimeCoordinator(
    store_factory=(
        (lambda: _behavioral_store)
        if _behavioral_store is not None
        else default_behavioral_store
    ),
    max_workers=2,
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
    status = (
        "full"
        if contract.status == ShapleyIntrinsicAvailability.READY
        else "partial_provisional"
    )
    return {
        "status": status,
        "reason": contract.status_reason or (
            "Governed FSFFL Intrinsic is available from preserved Year-1 evidence "
            "and the Forecast-owned vNext Future Forecast contract."
        ),
        "build_status": record.status.value,
        "contract_status": contract.status.value,
        "forecast_model_version": contract.forecast_model_version,
        "estimate_count": len(contract.estimates),
        "target_years": list(contract.target_years),
    }


def _hosted_capability_readiness(context) -> dict[str, object]:
    payload = dict(_webapp._runtime_capability_readiness(context))
    intrinsic = _intrinsic_readiness_from_record(
        _shapley_intrinsic_coordinator.current(context)
        if context.league_state is not None
        else None
    )
    payload["intrinsic"] = intrinsic
    required = ("forecast", "simulation", "current_value", "intrinsic")
    statuses = tuple(str(payload.get(key, {}).get("status", "unavailable")) for key in required)
    payload["product_required_capabilities"] = list(required)
    payload["overall_status"] = (
        "full"
        if all(status == "full" for status in statuses)
        else "partial"
        if any(status not in {"unavailable", "not_configured"} for status in statuses)
        else "unavailable"
    )
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

app = _webapp.create_app(
    runtime_store=_runtime_store,
    behavioral_coordinator=_behavioral_coordinator,
    forecast_loader=_forecast_loader,
    preseason_forecast_loader=_preseason_forecast_loader,
    state_snapshot_store=_state_snapshot_store,
    persistence_store=_persistence_store,
    capability_readiness_reader=_hosted_capability_readiness,
    product_capability_reconciler=_reconcile_hosted_intrinsic,
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
        "FSFFL startup runtime readiness user=%s league=%s state=%s forecast=%s simulation=%s value=%s core_complete=%s product_status=%s as_of=%s",
        _beta_restore_user,
        league_state.league.league_id if league_state is not None else None,
        league_state.state_id if league_state is not None else None,
        context.forecast_evidence is not None,
        context.simulation_analytics is not None,
        context.value_evidence is not None,
        core_complete,
        readiness.get("overall_status"),
        readiness.get("as_of"),
    )

_product_acceptance_state: dict[str, object] = {
    "status": "pending",
    "deploy_contract": "post-pr264-product-acceptance-v1",
}


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
            league_state_id=context.league_state.state_id,
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
            error=f"{type(exc).__name__}: {exc}",
        )
        logging.getLogger("uvicorn.error").exception(
            "FSFFL HOSTED PRODUCT ACCEPTANCE FAILED"
        )


def _prewarm_hosted_product_acceptance() -> None:
    Thread(
        target=_run_hosted_product_acceptance,
        name="fsffl-hosted-product-acceptance",
        daemon=True,
    ).start()


def _maybe_start_state_first_production_acceptance() -> None:
    enabled = os.getenv("FSFFL_RUN_STATE_FIRST_ACCEPTANCE", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        return
    if _persistence_store is None:
        logging.getLogger("uvicorn.error").error(
            "FSFFL STATE-FIRST ACCEPTANCE FAILED production persistence is unavailable"
        )
        return
    acceptance_user = os.getenv(
        "FSFFL_STATE_FIRST_ACCEPTANCE_USER",
        "state-first-production-acceptance",
    ).strip()
    if not acceptance_user:
        logging.getLogger("uvicorn.error").error(
            "FSFFL STATE-FIRST ACCEPTANCE FAILED isolated user id is blank"
        )
        return

    def run() -> None:
        try:
            run_state_first_production_acceptance(
                store=_runtime_store,
                user_id=acceptance_user,
                state_loader=default_sleeper_state_loader,
                start_reconciliation=app.state.start_intelligence_reconciliation,
                start_sync_reconciliation=app.state.start_intelligence_sync_reconciliation,
                jobs=app.state.intelligence_jobs,
                capability_reader=app.state.capability_readiness_reader,
            )
        except Exception:
            logging.getLogger("uvicorn.error").exception(
                "FSFFL STATE-FIRST ACCEPTANCE FAILED"
            )

    Thread(
        target=run,
        name="fsffl-state-first-production-acceptance",
        daemon=True,
    ).start()


app.router.add_event_handler("startup", _log_startup_runtime_readiness)
app.router.add_event_handler("startup", _prewarm_hosted_product_acceptance)
app.router.add_event_handler("startup", _maybe_start_state_first_production_acceptance)


@app.get("/health/product-acceptance")
def hosted_product_acceptance_health() -> dict[str, object]:
    """Non-sensitive production proof for product-path acceptance."""

    return dict(_product_acceptance_state)
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
)
install_player_intelligence_routes(
    app,
    runtime_store=_runtime_store,
    require_user=_webapp.require_beta_user,
    intrinsic_coordinator=_shapley_intrinsic_coordinator,
    future_cache=_player_future_forecast_cache,
    persistence_store=_persistence_store,
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
