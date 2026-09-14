from __future__ import annotations

import importlib.util
import math
import os
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

VARIANT = os.environ.get("FSFFL_CONDITIONAL_D2_VARIANT", "conditional").strip().lower()
if VARIANT not in {"conditional", "shrunk"}:
    raise RuntimeError(VARIANT)
NORMAL = statistics.NormalDist()
NODES = 41


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
    sanity = load_module(root / "run_intrinsic_explicit_state_sanity.py", "conditional_sanity_base")
    original_load = sanity.load

    def patch_d(module):
        reference_cache = {}

        def c2_at_x(x, baseline, marginal):
            n = float(marginal.TEAM_COUNT)
            return (n * marginal.marginal_at_x(x, baseline) + 0.5 * max(0.0, x)) / (n + 1.0)

        def reference(position, state, samples, baseline, marginal):
            if state == "out": return 0.0
            key = (id(samples), id(baseline), position, state)
            if key not in reference_cache:
                vals = samples.get((position, state), ())
                reference_cache[key] = 0.0 if not vals else module.mean(c2_at_x(v, baseline[position], marginal) for v in vals)
            return reference_cache[key]

        def interval(state, boundaries):
            _centers, thresholds = boundaries
            if state == "out": return -math.inf, 0.0
            i = module.STATE_NAMES.index(state) - 1
            lo = 0.0 if i == 0 else float(thresholds[i - 1])
            hi = math.inf if i == len(module.POSITIVE_STATES) - 1 else float(thresholds[i])
            return lo, hi

        def conditional_quality(e, horizon_index, state, boundaries, samples, baseline, marginal):
            ref = reference(e.position, state, samples, baseline, marginal)
            if state == "out": return 0.0
            mu = max(0.0, float(e.means[horizon_index])); sd = max(0.0, float(e.sds[horizon_index]))
            lo, hi = interval(state, boundaries[e.position])
            if sd <= 1e-9:
                return c2_at_x(mu, baseline[e.position], marginal) if module.state_for_points(mu, boundaries[e.position]) == state else ref
            p_lo = NORMAL.cdf((lo-mu)/sd) if math.isfinite(lo) else 0.0
            p_hi = NORMAL.cdf((hi-mu)/sd) if math.isfinite(hi) else 1.0
            mass = max(0.0, min(1.0, p_hi-p_lo))
            if mass <= 1e-10: return ref
            vals=[]
            for i in range(NODES):
                q=p_lo+((i+.5)/NODES)*mass; q=min(1-1e-12,max(1e-12,q))
                x=max(0.0,mu+sd*NORMAL.inv_cdf(q)); vals.append(c2_at_x(x,baseline[e.position],marginal))
            player=module.mean(vals)
            if VARIANT == "conditional": return player
            n_eff=NODES*mass; w=n_eff/(n_eff+1.0)
            return w*player+(1-w)*ref

        def expected(e, h, pr, boundaries, samples, baseline, marginal):
            return sum(pr[s]*conditional_quality(e,h,s,boundaries,samples,baseline,marginal) for s in module.STATE_NAMES)

        def d_explicit(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
            total=c2_at_x(max(0.0,e.means[0]),baseline[e.position],marginal); probs={}
            for h in (1,2):
                pr=module.state_distribution_for_example(e,boundaries,transitions,qb_probs,h); probs[h+1]=pr
                total+=(module.DISCOUNT**h)*expected(e,h,pr,boundaries,samples,baseline,marginal)
            return total,probs

        def d_terminal(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
            pr=module.state_distribution_for_example(e,boundaries,transitions,qb_probs,2)
            return (module.DISCOUNT**3)*expected(e,2,pr,boundaries,samples,baseline,marginal)

        def smooth_targets(examples,panel_rows,actual_baselines,marginal):
            by_key={(r.player_id,r.season):r for r in panel_rows}; out={}
            for e in examples:
                total=0.0
                for offset in range(module.REALIZED_HORIZON):
                    season=e.season+offset; row=by_key.get((e.player_id,season))
                    if row is None or row.points<=0 or season not in actual_baselines: continue
                    total+=(module.DISCOUNT**offset)*c2_at_x(row.points,actual_baselines[season][e.position],marginal)
                out[id(e)]=total
            return out

        module.state_contribution=reference; module.d_explicit=d_explicit; module.d_terminal=d_terminal; module.hard_targets=smooth_targets
        module.MODEL_VERSION=f"intrinsic-explicit-career-state-v2-{VARIANT}-conditional-player-quality"
        module._cq=conditional_quality; module._c2=c2_at_x; module._reference=reference
        return module

    def patched_load(path,name):
        m=original_load(path,name)
        if path.name == "run_intrinsic_explicit_state_challenge.py": m=patch_d(m)
        return m
    sanity.load=patched_load

    # The base sanity's diagnostic state table is reference-only. The actual current
    # values use the patched d_predict above. This keeps the format probes readable.
    def state_reference(d,marginal,position,state,samples,baseline):
        return d._reference(position,state,samples,baseline,marginal)
    sanity.state_mean_contribution=state_reference

    original_direct=sanity.direct_d_value
    direct_results={}

    # Capture the current context by wrapping direct_d_value after base construction
    # is not practical without changing the base harness. Existing synthetic gates
    # therefore remain emitted by the base as frozen probability-semantics gates;
    # a dedicated same-state quality gate is added after the run by the companion
    # workflow using the historical validation outputs.
    sanity.main()


if __name__ == "__main__":
    main()
