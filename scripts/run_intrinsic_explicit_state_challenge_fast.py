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

    def state_contribution(position, state, samples, baseline, marginal):
        values = samples.get((position, state), ())
        if not values or state == "out":
            return 0.0
        # D is a state-probability primitive. Use the empirical conditional mean
        # production of the explicit state; do not re-integrate a generic tail or
        # repeatedly average thousands of equivalent sample contributions.
        conditional_mean = base.mean(values)
        return marginal.marginal_at_x(conditional_mean, baseline[position])

    base.state_contribution = state_contribution
    base.MODEL_VERSION = "intrinsic-explicit-career-state-v1-fast-state-mean"
    base.main()


if __name__ == "__main__":
    main()
