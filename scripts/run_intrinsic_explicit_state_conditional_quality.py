from __future__ import annotations

import importlib.util
import math
import os
import statistics
import sys
from pathlib import Path


VARIANT = os.environ.get("FSFFL_CONDITIONAL_D2_VARIANT", "conditional").strip().lower()
if VARIANT not in {"conditional", "shrunk"}:
    raise RuntimeError(f"unsupported FSFFL_CONDITIONAL_D2_VARIANT={VARIANT!r}")

CONDITIONAL_NODES = 41
NORMAL = statistics.NormalDist()


def load_base():
    path = Path(__file__).with_name("run_intrinsic_explicit_state_challenge.py")
    spec = importlib.util.spec_from_file_location("conditional_d2_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    base = load_base()
    reference_cache = {}

    def c2_at_x(x, baseline, marginal):
        n = float(marginal.TEAM_COUNT)
        return (n * marginal.marginal_at_x(x, baseline) + 0.5 * max(0.0, x)) / (n + 1.0)

    def reference_state_contribution(position, state, samples, baseline, marginal):
        if state == "out":
            return 0.0
        key = (id(samples), id(baseline), position, state)
        if key not in reference_cache:
            vals = samples.get((position, state), ())
            reference_cache[key] = 0.0 if not vals else base.mean(
                c2_at_x(v, baseline[position], marginal) for v in vals
            )
        return reference_cache[key]

    def state_interval(state, position_boundaries):
        _centers, thresholds = position_boundaries
        idx = base.STATE_NAMES.index(state)
        if state == "out":
            return -math.inf, 0.0
        positive_idx = idx - 1
        lo = 0.0 if positive_idx == 0 else float(thresholds[positive_idx - 1])
        hi = math.inf if positive_idx == len(base.POSITIVE_STATES) - 1 else float(thresholds[positive_idx])
        return lo, hi

    def conditional_player_contribution(e, horizon_index, state, boundaries, samples, baseline, marginal):
        reference = reference_state_contribution(e.position, state, samples, baseline, marginal)
        if state == "out":
            return 0.0, 1.0

        mu = max(0.0, float(e.means[horizon_index]))
        sd = max(0.0, float(e.sds[horizon_index]))
        lo, hi = state_interval(state, boundaries[e.position])

        if sd <= 1e-9:
            if base.state_for_points(mu, boundaries[e.position]) == state:
                return c2_at_x(mu, baseline[e.position], marginal), 1.0
            return reference, 0.0

        p_lo = NORMAL.cdf((lo - mu) / sd) if math.isfinite(lo) else 0.0
        p_hi = NORMAL.cdf((hi - mu) / sd) if math.isfinite(hi) else 1.0
        mass = max(0.0, min(1.0, p_hi - p_lo))
        if mass <= 1e-10:
            return reference, mass

        vals = []
        for i in range(CONDITIONAL_NODES):
            q = p_lo + ((i + 0.5) / CONDITIONAL_NODES) * mass
            q = min(1.0 - 1e-12, max(1e-12, q))
            x = max(0.0, mu + sd * NORMAL.inv_cdf(q))
            vals.append(c2_at_x(x, baseline[e.position], marginal))
        player = base.mean(vals)

        if VARIANT == "conditional":
            return player, mass

        # One reference-equivalent observation provides hierarchical support.
        # Effective player evidence is the fixed quadrature sample multiplied by
        # the Forecast mass inside this state. This changes within-state quality
        # only; career-state entry probabilities remain entirely frozen.
        n_eff = CONDITIONAL_NODES * mass
        weight = n_eff / (n_eff + 1.0)
        return weight * player + (1.0 - weight) * reference, mass

    def expected_future(e, horizon_index, pr, boundaries, samples, baseline, marginal):
        return sum(
            pr[state]
            * conditional_player_contribution(
                e, horizon_index, state, boundaries, samples, baseline, marginal
            )[0]
            for state in base.STATE_NAMES
        )

    def d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
        total = c2_at_x(max(0.0, e.means[0]), baseline[e.position], marginal)
        probs = {}
        for h in (1, 2):
            pr = base.state_distribution_for_example(e, boundaries, transitions, qb_probs, h)
            probs[h + 1] = pr
            total += (base.DISCOUNT ** h) * expected_future(
                e, h, pr, boundaries, samples, baseline, marginal
            )
        return total, probs

    def d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
        pr = base.state_distribution_for_example(e, boundaries, transitions, qb_probs, 2)
        expected = expected_future(e, 2, pr, boundaries, samples, baseline, marginal)
        return (base.DISCOUNT ** 3) * expected

    def smooth_targets(examples, panel_rows, actual_baselines, marginal):
        by_key = {(r.player_id, r.season): r for r in panel_rows}
        out = {}
        for e in examples:
            total = 0.0
            for offset in range(base.REALIZED_HORIZON):
                season = e.season + offset
                row = by_key.get((e.player_id, season))
                if row is None or row.points <= 0 or season not in actual_baselines:
                    continue
                total += (base.DISCOUNT ** offset) * c2_at_x(
                    row.points, actual_baselines[season][e.position], marginal
                )
            out[id(e)] = total
        return out

    base.state_contribution = reference_state_contribution
    base.d_explicit = d_explicit
    base.d_terminal = d_terminal
    base.hard_targets = smooth_targets
    base.MODEL_VERSION = (
        "intrinsic-explicit-career-state-v2-conditional-player-quality"
        if VARIANT == "conditional"
        else "intrinsic-explicit-career-state-v2-shrunk-conditional-player-quality"
    )
    base.main()


if __name__ == "__main__":
    main()
