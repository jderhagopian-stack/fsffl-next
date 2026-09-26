from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
# The benchmark helper dynamically loads this exact module name without first
# registering it. Pre-register it so dataclass type resolution is safe while
# leaving the audit methodology and benchmark helper unchanged.
_load_registered(HERE / "run_career_calibration.py", "pr131_career_calibration")
audit = _load_registered(
    HERE / "run_forecast_update_reliability_audit.py",
    "pr131_forecast_update_reliability_audit",
)

if __name__ == "__main__":
    audit.main()
