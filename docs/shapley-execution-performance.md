# Shapley scenario execution

This optimization changes execution cost, not the governed game or estimator.
Scenario weights are converted to floats and clamped once per calculation. The
permutation loop accumulates the same marginal formula without allocating a
temporary result tuple for every scenario. Player order, shuffle calls, seeds,
2,048 permutations, lineup feasibility, replacement tie-breaking, epsilon,
floating-point addition order, standard errors and efficiency checks are retained.

Prepared weights are local to one calculation, bounded by its player/scenario
inputs, and released on return. They are not a retained forecast cache. The basis,
integer feasibility cache and existing clearing/ownership boundaries are unchanged.
No provider acquisition, persistence write, worker, plan or model version is added.

The accepted legacy loop remains a test oracle. Regressions compare every result
field across 2/8/12/16-team Superflex and 1-QB games, negative/zero weights, ties,
epsilon boundaries, different scenario-row lengths, no eligible slots, empty
cohorts and one-permutation statistics. The existing frozen Career/Shapley parity
gate remains required.

Run the isolated synthetic benchmark with:

```sh
PYTHONPATH=src python scripts/benchmark_shapley_scenarios.py --format superflex
PYTHONPATH=src python scripts/benchmark_shapley_scenarios.py --format 1qb
```

Use the same benchmark script, interpreter and machine with each checkout's
`src` on `PYTHONPATH`. Compare the full result digest before comparing timings;
use fresh processes and multiple runs. Process peak RSS includes imports and
the execution workspace. This is not an estimate of hosted refresh peak memory.

An isolated 366-player, seven-scenario, 2,048-permutation three-run comparison
measured median wall time 3.585 → 2.657 seconds (about 26% less), CPU time
3.584 → 2.656 seconds, and maximum process peak RSS 54,936 → 54,620 KiB.
Every output field was identical. These measurements apply to the synthetic
kernel; model fitting, acquisition, publication and other refresh work remain.

The accepted 335-player long-horizon reference fixture, composed through the
production long-term contract builder, measured 52.057 → 36.692 seconds wall and
52.049 → 36.687 seconds CPU (about 30% less). Its complete serialized contract
was identical before/after, including metadata and uncertainty; maximum process
RSS was 201,748 → 201,572 KiB. This is a single isolated pair, not a hosted
full-refresh measurement or a new historical forecast evaluation.

The existing Career instrumentation now separately measures expanded Current
Shapley and expanded long-horizon composition. Verify their wall/CPU/peak memory
and exact-State output coverage on a normal hosted refresh after deployment.
Do not infer an equal percentage improvement for the entire refresh, or claim
that this change resolves all retained-memory pressure.
