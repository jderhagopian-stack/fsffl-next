from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    root = Path(__file__).parent
    sanity = load_module(root / "run_intrinsic_explicit_state_sanity.py", "d2_sanity_base")
    original_load = sanity.load

    def patch_d(module):
        cache = {}

        def c2_at_x(x, baseline, marginal):
            return (12.0 * marginal.marginal_at_x(x, baseline) + 0.5 * max(0.0, x)) / 13.0

        def state_contribution(position, state, samples, baseline, marginal):
            if state == "out":
                return 0.0
            key = (id(samples), id(baseline), position, state)
            if key not in cache:
                vals = samples.get((position, state), ())
                cache[key] = 0.0 if not vals else module.mean(c2_at_x(v, baseline[position], marginal) for v in vals)
            return cache[key]

        def d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
            total = c2_at_x(max(0.0, e.means[0]), baseline[e.position], marginal)
            probs = {}
            for h in (1, 2):
                pr = module.state_distribution_for_example(e, boundaries, transitions, qb_probs, h)
                probs[h + 1] = pr
                expected = sum(pr[s] * state_contribution(e.position, s, samples, baseline, marginal) for s in module.STATE_NAMES)
                total += (module.DISCOUNT ** h) * expected
            return total, probs

        def d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
            pr = module.state_distribution_for_example(e, boundaries, transitions, qb_probs, 2)
            expected = sum(pr[s] * state_contribution(e.position, s, samples, baseline, marginal) for s in module.STATE_NAMES)
            return (module.DISCOUNT ** 3) * expected

        def smooth_targets(examples, panel_rows, actual_baselines, marginal):
            by_key = {(r.player_id, r.season): r for r in panel_rows}
            out = {}
            for e in examples:
                total = 0.0
                for offset in range(module.REALIZED_HORIZON):
                    season = e.season + offset
                    row = by_key.get((e.player_id, season))
                    if row is None or row.points <= 0 or season not in actual_baselines:
                        continue
                    total += (module.DISCOUNT ** offset) * c2_at_x(row.points, actual_baselines[season][e.position], marginal)
                out[id(e)] = total
            return out

        module.state_contribution = state_contribution
        module.d_explicit = d_explicit
        module.d_terminal = d_terminal
        module.hard_targets = smooth_targets
        module.MODEL_VERSION = "intrinsic-explicit-career-state-v2-state-conditioned-smooth-contribution"
        module._d2_c2_at_x = c2_at_x
        module._d2_state_contribution = state_contribution
        return module

    def patched_load(path, name):
        module = original_load(path, name)
        if path.name == "run_intrinsic_explicit_state_challenge.py":
            module = patch_d(module)
        return module

    sanity.load = patched_load

    def smooth_state_contribution(d, marginal, position, state, samples, baseline):
        return d._d2_state_contribution(position, state, samples, baseline, marginal)

    sanity.state_mean_contribution = smooth_state_contribution
    sanity.main()


if __name__ == "__main__":
    main()
