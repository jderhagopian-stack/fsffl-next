from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fsffl.state.models import Position


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    here = Path(__file__).parent
    validator = _load(here / "validate_i1_production_parity.py", "i1_production_parity_v1")
    original_load = validator.load

    def load_with_position(path: Path, name: str):
        module = original_load(path, name)
        if path.name == "run_integrated_multivariate_forecast.py":
            # Research harness uses string positions and does not itself expose the
            # canonical Position enum. The production validator needs only this
            # type binding; no research behavior or result is changed.
            module.Position = Position
        return module

    validator.load = load_with_position
    validator.main()
