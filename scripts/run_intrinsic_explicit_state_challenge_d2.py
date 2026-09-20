from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_base():
    path=Path(__file__).with_name('run_intrinsic_explicit_state_challenge.py')
    spec=importlib.util.spec_from_file_location('explicit_state_d2_base',path)
    if spec is None or spec.loader is None:raise RuntimeError(path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module


def main():
    base=load_base();cache={}

    def c2_at_x(x,baseline,marginal):
        n=float(marginal.TEAM_COUNT)
        return (n*marginal.marginal_at_x(x,baseline)+0.5*max(0.0,x))/(n+1.0)

    def state_contribution(position,state,samples,baseline,marginal):
        if state=='out':return 0.0
        key=(id(samples),id(baseline),position,state)
        if key in cache:return cache[key]
        vals=samples.get((position,state),())
        result=0.0 if not vals else base.mean(c2_at_x(v,baseline[position],marginal) for v in vals)
        cache[key]=result
        return result

    def d_explicit(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
        total=c2_at_x(max(0.0,e.means[0]),baseline[e.position],marginal)
        probs={}
        for h in (1,2):
            pr=base.state_distribution_for_example(e,boundaries,transitions,qb_probs,h);probs[h+1]=pr
            expected=sum(pr[s]*state_contribution(e.position,s,samples,baseline,marginal) for s in base.STATE_NAMES)
            total+=(base.DISCOUNT**h)*expected
        return total,probs

    def d_terminal(e,boundaries,transitions,samples,baseline,qb_probs,marginal):
        pr=base.state_distribution_for_example(e,boundaries,transitions,qb_probs,2)
        expected=sum(pr[s]*state_contribution(e.position,s,samples,baseline,marginal) for s in base.STATE_NAMES)
        return (base.DISCOUNT**3)*expected

    def smooth_targets(examples,panel_rows,actual_baselines,marginal):
        by_key={(r.player_id,r.season):r for r in panel_rows};out={}
        for e in examples:
            total=0.0
            for offset in range(base.REALIZED_HORIZON):
                season=e.season+offset;row=by_key.get((e.player_id,season))
                if row is None or row.points<=0 or season not in actual_baselines:continue
                total+=(base.DISCOUNT**offset)*c2_at_x(row.points,actual_baselines[season][e.position],marginal)
            out[id(e)]=total
        return out

    base.state_contribution=state_contribution
    base.d_explicit=d_explicit
    base.d_terminal=d_terminal
    base.hard_targets=smooth_targets
    base.MODEL_VERSION='intrinsic-explicit-career-state-v2-state-conditioned-smooth-contribution'
    base.main()

if __name__=='__main__':main()
