from __future__ import annotations

import logging

from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .webapp import create_app


# Hosted private-beta observability only. The coordinator already records exact
# wall-clock phase timings; ensure Render emits those INFO records so latency work
# can target measured bottlenecks without adding technical noise to product UI.
logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)

app = create_app(runtime_store=PersistentPrivateBetaRuntimeStore())
