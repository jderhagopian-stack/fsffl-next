from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


challenger = load_registered(
    HERE / "run_forecast_trajectory_challengers.py",
    "pr131_forecast_trajectory_challengers_main",
)
# The repair runner's legacy loader does not register its dynamic dataclass module
# under Python 3.11. Reuse the already safely registered benchmark module instead.
challenger.repair.load_base = lambda: challenger.base

if __name__ == "__main__":
    challenger.main()
