from __future__ import annotations

from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .webapp import create_app


app = create_app(runtime_store=PersistentPrivateBetaRuntimeStore())
