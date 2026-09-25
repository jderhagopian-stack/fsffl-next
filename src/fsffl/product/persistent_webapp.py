from __future__ import annotations

import logging
import os

from fsffl.persistence import (
    persistence_store_from_env,
    projection_history_store_from_env,
    state_snapshot_store_from_env,
)
from fsffl.providers.sleeper_live import SleeperLiveSource

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
from .intrinsic_background import ShapleyIntrinsicBackgroundCoordinator
from .intrinsic_market_discovery_routes import install_intrinsic_market_discovery_routes
from .intrinsic_value_routes import install_intrinsic_value_v1_routes
from .league_value_lens_routes import install_league_value_lens_routes
from .latency_observability import install_latency_observability
from .opportunity_search_cache import make_cached_opportunity_search
from .opportunity_workspace_cache import make_cached_opportunity_workspace
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .player_intelligence import PlayerFutureForecastCache
from .player_intelligence_routes import install_player_intelligence_routes
from .phase1_latency import install_phase1_latency_routes
from .private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from .vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    build_vnext_future_forecast_contract,
)
from .progressive_delivery_routes import install_progressive_delivery_routes
from .provisional_k_dst_routes import install_provisional_k_dst_routes
from .quick_frontier_routes import install_quick_frontier_routes
from .runtime import default_sleeper_state_loader
from .scenario_cache import configure_scenario_cache_persistence
from .shapley_intrinsic_routes import install_shapley_intrinsic_routes


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
    future_forecast_builder=build_vnext_future_forecast_contract,
    future_forecast_model_version=VNEXT_FORECAST_VERSION,
    future_missing_fact_family="vnext_future_forecast_coordinate",
)
_player_future_forecast_cache = PlayerFutureForecastCache(
    future_forecast_builder=build_vnext_future_forecast_contract,
    forecast_model_version=VNEXT_FORECAST_VERSION,
)
_shapley_intrinsic_coordinator = ShapleyIntrinsicBackgroundCoordinator(
    _shapley_intrinsic_loader,
    max_workers=1,
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
)

def _log_startup_runtime_readiness() -> None:
    if not _beta_restore_user:
        return
    context = _runtime_store.get(_beta_restore_user)
    league_state = context.league_state
    complete = bool(
        league_state is not None
        and context.forecast_evidence is not None
        and context.simulation_analytics is not None
        and context.value_evidence is not None
    )
    logging.getLogger("uvicorn.error").info(
        "FSFFL startup runtime readiness user=%s league=%s state=%s forecast=%s simulation=%s value=%s complete=%s",
        _beta_restore_user,
        league_state.league.league_id if league_state is not None else None,
        league_state.state_id if league_state is not None else None,
        context.forecast_evidence is not None,
        context.simulation_analytics is not None,
        context.value_evidence is not None,
        complete,
    )

app.router.add_event_handler("startup", _log_startup_runtime_readiness)
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
