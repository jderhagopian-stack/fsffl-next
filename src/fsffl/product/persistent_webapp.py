from __future__ import annotations

import logging
import os

from fsffl.persistence import persistence_store_from_env, state_snapshot_store_from_env
from fsffl.providers.sleeper_live import SleeperLiveSource

from .behavioral_runtime import BehavioralRuntimeCoordinator
from .forecast_resilience import make_resilient_forecast_loader
from .hosted_connect import install_hosted_connect_routes
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .phase1_latency import install_phase1_latency_routes
from .runtime import default_sleeper_state_loader
from .webapp import create_app


# Hosted private-beta observability only. The coordinator already records exact
# wall-clock phase timings; ensure Render emits those INFO records so latency work
# can target measured bottlenecks without adding technical noise to product UI.
logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)

_persistence_store = persistence_store_from_env()
_state_snapshot_store = state_snapshot_store_from_env()
_runtime_store = PersistentPrivateBetaRuntimeStore(
    _persistence_store,
    state_snapshot_store=_state_snapshot_store,
)
_behavioral_coordinator = BehavioralRuntimeCoordinator(max_workers=2)
_sleeper_probe_source = SleeperLiveSource()
_full_refresh_seconds = max(
    1,
    int(os.getenv("FSFFL_FULL_PROVIDER_REFRESH_SECONDS", "3600")),
)
_forecast_loader = make_resilient_forecast_loader(_persistence_store)

app = create_app(
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
install_phase1_latency_routes(app, persistence_store=_persistence_store)
