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
NORMAL = statistics.NormalDist()
JEFFREYS_REFERENCE_MASS = 0.5


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
        if state == "out": return 0.0
        key = (id(samples), id(baseline), position, state)
        if key not in reference_cache:
            vals = samples.get((position, state), ())
            reference_cache[key] = 0.0 if not vals else base.mean(c2_at_x(v, baseline[position], marginal) for v in vals)
        return reference_cache[key]

    def state_interval(state, position_boundaries):
        _centers, thresholds = position_boundaries
        idx = base.STATE_NAMES.index(state)
        if state == "out": return -math.inf, 0.0
        i = idx - 1
        return (0.0 if i == 0 else float(thresholds[i-1]), math.inf if i == len(base.POSITIVE_STATES)-1 else float(thresholds[i]))

    def phi(z):
        return 0.0 if not math.isfinite(z) else NORMAL.pdf(z)

    def conditional_c2(mu, sd, lo, hi, neutral_baseline, marginal):
        if sd <= 1e-9:
            x=max(0.0,mu)
            return c2_at_x(x,neutral_baseline,marginal), 1.0 if lo <= x < hi else 0.0
        zlo=(lo-mu)/sd if math.isfinite(lo) else -math.inf
        zhi=(hi-mu)/sd if math.isfinite(hi) else math.inf
        plo=0.0 if zlo == -math.inf else NORMAL.cdf(zlo)
        phi_cdf=1.0 if zhi == math.inf else NORMAL.cdf(zhi)
        mass=max(0.0,min(1.0,phi_cdf-plo))
        if mass <= 1e-12: return 0.0,mass
        ex=mu+sd*(phi(zlo)-phi(zhi))/mass
        expected_marginal=0.0
        for b,p in neutral_baseline:
            lower=max(lo,float(b))
            if lower >= hi: continue
            zl=(lower-mu)/sd if math.isfinite(lower) else -math.inf
            zu=(hi-mu)/sd if math.isfinite(hi) else math.inf
            pl=0.0 if zl == -math.inf else NORMAL.cdf(zl)
            pu=1.0 if zu == math.inf else NORMAL.cdf(zu)
            interval_mass=max(0.0,pu-pl)
            numerator=(mu-float(b))*interval_mass+sd*(phi(zl)-phi(zu))
            expected_marginal += float(p)*max(0.0,numerator/mass)
        n=float(marginal.TEAM_COUNT)
        return (n*expected_marginal+0.5*max(0.0,ex))/(n+1.0),mass

    def conditional_player_contribution(e,h,state,boundaries,samples,baseline,marginal):
        reference=reference_state_contribution(e.position,state,samples,baseline,marginal)
        if state == "out": return 0.0,1.0
        mu=max(0.0,float(e.means[h])); sd=max(0.0,float(e.sds[h])); lo,hi=state_interval(state,boundaries[e.position])
        player,mass=conditional_c2(mu,sd,lo,hi,baseline[e.position],marginal)
        if mass <= 1e-10: return reference,mass
        if VARIANT == "conditional": return player,mass
        # Bounded empirical-Bayes support: player evidence is the governed Forecast
        # probability mass actually occupying this state. A Jeffreys half-observation
        # supplies the position/state reference prior. Quadrature resolution is not
        # treated as sample size or confidence.
        w=mass/(mass+JEFFREYS_REFERENCE_MASS)
        return w*player+(1.0-w)*reference,mass

    def expected_future(e,h,pr,boundaries,samples,baseline,marginal):
        return sum(pr[s]*conditional_player_contribution(e,h,s,boundaries,samples,baseline,marginal)[0] for s in base.STATE_NAMES)

    def d_explicit(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
        total=c2_at_x(max(0.0,e.means[0]),baseline[e.position],marginal); probs={}
        for h in (1,2):
            pr=base.state_distribution_for_example(e,boundaries,transitions,qb_probs,h); probs[h+1]=pr
            total+=(base.DISCOUNT**h)*expected_future(e,h,pr,boundaries,samples,baseline,marginal)
        return total,probs

    def d_terminal(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
        pr=base.state_distribution_for_example(e,boundaries,transitions,qb_probs,2)
        return (base.DISCOUNT**3)*expected_future(e,2,pr,boundaries,samples,baseline,marginal)

    def smooth_targets(examples,panel_rows,actual_baselines,marginal):
        by_key={(r.player_id,r.season):r for r in panel_rows}; out={}
        for e in examples:
            total=0.0
            for offset in range(base.REALIZED_HORIZON):
                season=e.season+offset; row=by_key.get((e.player_id,season))
                if row is None or row.points <= 0 or season not in actual_baselines: continue
                total+=(base.DISCOUNT**offset)*c2_at_x(row.points,actual_baselines[season][e.position],marginal)
            out[id(e)]=total
        return out

    base.state_contribution=reference_state_contribution
    base.d_explicit=d_explicit
    base.d_terminal=d_terminal
    base.hard_targets=smooth_targets
    base.MODEL_VERSION=("intrinsic-explicit-career-state-v2-conditional-player-quality" if VARIANT == "conditional" else "intrinsic-explicit-career-state-v2-shrunk-conditional-player-quality")
    base.main()


if __name__ == "__main__": main()
