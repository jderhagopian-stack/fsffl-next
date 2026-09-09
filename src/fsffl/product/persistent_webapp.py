from __future__ import annotations

import logging

from .behavioral_runtime import BehavioralRuntimeCoordinator
from .hosted_connect import install_hosted_connect_routes
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .runtime import default_sleeper_state_loader
from .webapp import create_app


# Hosted private-beta observability only. The coordinator already records exact
# wall-clock phase timings; ensure Render emits those INFO records so latency work
# can target measured bottlenecks without adding technical noise to product UI.
logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)

_runtime_store = PersistentPrivateBetaRuntimeStore()
_behavioral_coordinator = BehavioralRuntimeCoordinator(max_workers=2)
app = create_app(
    runtime_store=_runtime_store,
    behavioral_coordinator=_behavioral_coordinator,
)
install_hosted_connect_routes(
    app,
    runtime_store=_runtime_store,
    state_loader=default_sleeper_state_loader,
    behavioral_coordinator=_behavioral_coordinator,
)
