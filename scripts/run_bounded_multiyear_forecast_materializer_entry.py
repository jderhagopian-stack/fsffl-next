"""Loader-only entrypoint for the frozen bounded materializer research script.

The research scripts loaded dynamically contain dataclasses. Python 3.11's dataclass
introspection expects a dynamically created module to be registered in sys.modules
before execution. This wrapper fixes only that import plumbing; it does not alter
candidate selection, bounds, state updates, gates, or evaluation logic.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys

_original_module_from_spec = importlib.util.module_from_spec


def _registered_module_from_spec(spec):
    module = _original_module_from_spec(spec)
    if spec.name:
        sys.modules[spec.name] = module
    return module


importlib.util.module_from_spec = _registered_module_from_spec
runpy.run_path("scripts/run_bounded_multiyear_forecast_materializer_research.py", run_name="__main__")
