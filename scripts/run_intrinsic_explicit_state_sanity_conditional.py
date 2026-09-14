from __future__ import annotations

import importlib.util
import math
import os
import statistics
import sys
from pathlib import Path

VARIANT=os.environ.get("FSFFL_CONDITIONAL_D2_VARIANT","conditional").strip().lower()
if VARIANT not in {"conditional","shrunk"}: raise RuntimeError(VARIANT)
NORMAL=statistics.NormalDist(); JEFFREYS_REFERENCE_MASS=.5


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m


def main():
    root=Path(__file__).parent
    sanity=load_module(root/"run_intrinsic_explicit_state_sanity.py","conditional_sanity_base")
    original_load=sanity.load

    def patch_d(module):
        cache={}
        def c2_at_x(x,baseline,marginal):
            n=float(marginal.TEAM_COUNT); return (n*marginal.marginal_at_x(x,baseline)+.5*max(0.,x))/(n+1.)
        def reference(position,state,samples,baseline,marginal):
            if state=="out": return 0.
            key=(id(samples),id(baseline),position,state)
            if key not in cache:
                vals=samples.get((position,state),()); cache[key]=0. if not vals else module.mean(c2_at_x(v,baseline[position],marginal) for v in vals)
            return cache[key]
        def interval(state,bounds):
            _c,t=bounds
            if state=="out": return -math.inf,0.
            i=module.STATE_NAMES.index(state)-1
            return (0. if i==0 else float(t[i-1]), math.inf if i==len(module.POSITIVE_STATES)-1 else float(t[i]))
        def phi(z): return 0. if not math.isfinite(z) else NORMAL.pdf(z)
        def conditional_c2(mu,sd,lo,hi,neutral,marginal):
            if sd<=1e-9:
                x=max(0.,mu); return c2_at_x(x,neutral,marginal),1. if lo<=x<hi else 0.
            zl=(lo-mu)/sd if math.isfinite(lo) else -math.inf; zu=(hi-mu)/sd if math.isfinite(hi) else math.inf
            pl=0. if zl==-math.inf else NORMAL.cdf(zl); pu=1. if zu==math.inf else NORMAL.cdf(zu); mass=max(0.,min(1.,pu-pl))
            if mass<=1e-12: return 0.,mass
            ex=mu+sd*(phi(zl)-phi(zu))/mass; em=0.
            for b,p in neutral:
                lower=max(lo,float(b))
                if lower>=hi: continue
                za=(lower-mu)/sd if math.isfinite(lower) else -math.inf; zb=(hi-mu)/sd if math.isfinite(hi) else math.inf
                pa=0. if za==-math.inf else NORMAL.cdf(za); pb=1. if zb==math.inf else NORMAL.cdf(zb)
                m=max(0.,pb-pa); num=(mu-float(b))*m+sd*(phi(za)-phi(zb)); em+=float(p)*max(0.,num/mass)
            n=float(marginal.TEAM_COUNT); return (n*em+.5*max(0.,ex))/(n+1.),mass
        def quality(e,h,state,bounds,samples,baseline,marginal):
            ref=reference(e.position,state,samples,baseline,marginal)
            if state=="out": return 0.
            lo,hi=interval(state,bounds[e.position]); player,mass=conditional_c2(max(0.,float(e.means[h])),max(0.,float(e.sds[h])),lo,hi,baseline[e.position],marginal)
            if mass<=1e-10: return ref
            if VARIANT=="conditional": return player
            w=mass/(mass+JEFFREYS_REFERENCE_MASS); return w*player+(1.-w)*ref
        def expected(e,h,pr,bounds,samples,baseline,marginal): return sum(pr[s]*quality(e,h,s,bounds,samples,baseline,marginal) for s in module.STATE_NAMES)
        def d_explicit(e,bounds,transitions,samples,baseline,qb_probs,marginal):
            total=c2_at_x(max(0.,e.means[0]),baseline[e.position],marginal); probs={}
            for h in (1,2):
                pr=module.state_distribution_for_example(e,bounds,transitions,qb_probs,h); probs[h+1]=pr; total+=(module.DISCOUNT**h)*expected(e,h,pr,bounds,samples,baseline,marginal)
            return total,probs
        def d_terminal(e,bounds,transitions,samples,baseline,qb_probs,marginal):
            pr=module.state_distribution_for_example(e,bounds,transitions,qb_probs,2); return (module.DISCOUNT**3)*expected(e,2,pr,bounds,samples,baseline,marginal)
        def targets(examples,panel_rows,actual_baselines,marginal):
            by={(r.player_id,r.season):r for r in panel_rows}; out={}
            for e in examples:
                total=0.
                for off in range(module.REALIZED_HORIZON):
                    season=e.season+off; row=by.get((e.player_id,season))
                    if row is None or row.points<=0 or season not in actual_baselines: continue
                    total+=(module.DISCOUNT**off)*c2_at_x(row.points,actual_baselines[season][e.position],marginal)
                out[id(e)]=total
            return out
        module.state_contribution=reference; module.d_explicit=d_explicit; module.d_terminal=d_terminal; module.hard_targets=targets
        module.MODEL_VERSION=f"intrinsic-explicit-career-state-v2-{VARIANT}-conditional-player-quality"
        module._reference=reference
        return module

    def patched_load(path,name):
        m=original_load(path,name)
        if path.name=="run_intrinsic_explicit_state_challenge.py": m=patch_d(m)
        return m
    sanity.load=patched_load
    sanity.state_mean_contribution=lambda d,marginal,position,state,samples,baseline:d._reference(position,state,samples,baseline,marginal)
    sanity.main()


if __name__=="__main__": main()
