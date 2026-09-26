"""Research-only entrypoint for the PR #131 benchmark.

The benchmark deliberately reuses the existing standalone career-calibration
script. Python 3.11 dataclasses require dynamically loaded modules to be present
in ``sys.modules`` while their classes are defined. This entrypoint registers
modules created by importlib for this one process, then executes the benchmark
unchanged. It does not alter any production package or model authority.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

_original_module_from_spec = importlib.util.module_from_spec


def _registered_module_from_spec(spec):
    module = _original_module_from_spec(spec)
    if spec.name:
        sys.modules.setdefault(spec.name, module)
    return module


importlib.util.module_from_spec = _registered_module_from_spec
runpy.run_path(
    str(Path(__file__).with_name("run_multiyear_intrinsic_model_a_benchmark.py")),
    run_name="__main__",
)
