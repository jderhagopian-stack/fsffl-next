from __future__ import annotations

import logging
import os

from fsffl.persistence import (
    persistence_store_from_env,
    projection_history_store_from_env,
    state_snapshot_store_from_env,
)
from fsffl.providers.sleeper_live import SleeperLiveSource

from . import webapp as _webapp
from .behavioral_runtime import BehavioralRuntimeCoordinator, default_behavioral_store
from .forecast_resilience import make_resilient_forecast_loader
from .hosted_connect import install_hosted_connect_routes
from .in_season_forecast_routes import install_in_season_forecast_routes
from .latency_observability import install_latency_observability
from .opportunity_workspace_cache import make_cached_opportunity_workspace
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .phase1_latency import install_phase1_latency_routes
from .runtime import default_sleeper_state_loader


# Hosted private-beta observability only. The coordinator already records exact
# wall-clock phase timings; ensure Render emits those INFO records so latency work
# can target measured bottlenecks without adding technical noise to product UI.
logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)
_logger = logging.getLogger("fsffl.product.performance")

_persistence_store = persistence_store_from_env()
_projection_history_store = projection_history_store_from_env()
_state_snapshot_store = state_snapshot_store_from_env()
_runtime_store = PersistentPrivateBetaRuntimeStore(
    _persistence_store,
    state_snapshot_store=_state_snapshot_store,
)

# Hosted Behavioral persistence performs an idempotent deploy-before-migration
# schema safety bootstrap when its Postgres adapter is first constructed. Build the
# shared adapter while the Render process is starting rather than on the first user
# status/Market request. Failure remains non-fatal: the coordinator will retry its
# normal factory later and Behavioral evidence will fail closed rather than blocking
# the rest of the product.
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
    full_refresh_seconds=_full_refresh_seconds,
)
install_in_season_forecast_routes(
    app,
    runtime_store=_runtime_store,
    persistence_store=_persistence_store,
    projection_history_store=_projection_history_store,
)
install_phase1_latency_routes(app, persistence_store=_persistence_store)
install_latency_observability(app)
