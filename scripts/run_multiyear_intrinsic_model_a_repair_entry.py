from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path


_original_module_from_spec = importlib.util.module_from_spec


def _registered_module_from_spec(spec):
    module = _original_module_from_spec(spec)
    if spec.name:
        sys.modules[spec.name] = module
    return module


# The research harness dynamically loads dataclass-bearing scripts. Python 3.11
# dataclasses expect the defining module to be present in sys.modules while the
# class is created. Register dynamic modules before executing them without
# changing any benchmark method, threshold, or model behavior.
importlib.util.module_from_spec = _registered_module_from_spec

runpy.run_path(
    str(Path(__file__).with_name("run_multiyear_intrinsic_model_a_repair.py")),
    run_name="__main__",
)
