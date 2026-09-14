from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_base():
    path = Path(__file__).with_name("run_intrinsic_explicit_state_challenge.py")
    spec = importlib.util.spec_from_file_location("explicit_state_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    base = load_base()
    cache = {}

    def state_contribution(position, state, samples, baseline, marginal):
        if state == "out":
            return 0.0
        key = (id(samples), id(baseline), position, state)
        if key in cache:
            return cache[key]
        values = samples.get((position, state), ())
        if not values:
            result = 0.0
        else:
            # Preserve bounded within-state production dispersion, but compute it
            # once per state/context. Generic player Forecast SD cannot move mass
            # across states; uncertainty only exists inside the explicit state.
            result = base.mean(marginal.marginal_at_x(v, baseline[position]) for v in values)
        cache[key] = result
        return result

    base.state_contribution = state_contribution
    base.MODEL_VERSION = "intrinsic-explicit-career-state-v1-cached-within-state"
    base.main()


if __name__ == "__main__":
    main()
