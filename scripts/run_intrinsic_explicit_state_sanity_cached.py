from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_base():
    path=Path(__file__).with_name('run_intrinsic_explicit_state_sanity.py')
    spec=importlib.util.spec_from_file_location('explicit_state_sanity_base',path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module


def main():
    base=load_base();cache={}
    def bounded_state_contribution(d,marginal,position,state,samples,baseline):
        if state=='out': return 0.0
        key=(id(samples),id(baseline),position,state)
        if key in cache:return cache[key]
        vals=samples.get((position,state),())
        result=0.0 if not vals else d.mean(marginal.marginal_at_x(v,baseline[position]) for v in vals)
        cache[key]=result
        return result
    base.state_mean_contribution=bounded_state_contribution
    base.main()

if __name__=='__main__':main()
