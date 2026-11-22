# Exact Foundation 4 training-fit reuse

This is an execution optimization of the accepted Foundation 4 materializer, not
new forecasting methodology or a new model release. The original accepted
training selectors, feature transforms, targets, estimator constructors, seeds,
parameters, policy weights, calibration, fresh evaluation and output calculations
still execute. No source-freshness or final Career readiness shortcut is added.

The existing owned materializer installs wrappers on its dynamically loaded
accepted module's estimator constructors only. It does not patch sklearn globals
or reader/startup paths. The wrapper receives the exact training arrays that the
unchanged accepted code supplies to `.fit`. Its returned object is the original
native fitted estimator; prediction still runs on current evaluation features.
Nonstandard fit signatures, unsupported layouts/types or unseeded stochastic
learners use the original fit path. Original fitting errors still propagate.

## Reuse identity and scope

The key includes estimator class and complete constructor parameters, training
matrix and target dtype/shape/ordered bytes, accepted development/route program
hashes, cache format, Python and NumPy/sklearn versions. No rounding, casting,
row sorting, feature inference, sample changes or approximate matching occurs.
Current player evaluation rows do not belong to the training key: predictions
must be freshly calculated for those rows. League, user and capture timestamp
are not training dependencies. Identical accepted training fits can therefore
be reused across leagues and changing evaluation cohorts without reusing any
owner-specific predictions or source receipts.

Each native model is streamed to a private process-created temporary directory.
Only an in-memory index of this process's own files and SHA256 digests permits
restoration; there is no external pickle, uploaded path or artifact loader.
Content is verified before deserialization and native type/parameters rechecked.
Corruption, missing files and optional cache-write failures take the original fit
path. Temporary storage initialization failure leaves constructors unchanged.

The cache holds no fitted model graphs, training matrices or evaluation rows in
RAM. Its metadata and disk entries are bounded to 64 entries/32 MiB, least
recently used eviction. One write in progress can temporarily add up to 32 MiB;
partial writes are removed. The existing reclaim/hard-cap guard runs before
optional serialization; refusal skips the write and returns the valid fitted
estimator. This does not certify peak RSS or cgroup/page-cache headroom. Restart/deploy discards this execution cache, which
is not historical evidence or authoritative storage. No Supabase writes, schema,
connection path, workers, schedule, service, new secrets or infrastructure costs.

## Evidence and acceptance

The controlled hosted baseline spent 195.740 s in candidate materialization;
roughly 17.9 s preceded the end of historical horizon expansion, with 177.9 s
remaining for policy calculation and output work. This identifies a meaningful
execution target; it does not attribute every remaining second to estimator fit.
A separate synthetic 335-player Future Forecast retention check found only
3.24 MB of traced retained objects; that useful cache was left intact.

Reproduce focused checks:

```
pytest -q tests/test_foundation4_fit_reuse.py tests/test_foundation4_matrix.py
PYTHONPATH=src python scripts/benchmarks/foundation4_fit_reuse.py
```

Tests use verbatim accepted `fit_predict` and `state_labels` oracles from
`be2541a496227b33c12c755f576843dc4ab5a0bb`, with synthetic feature data and the
existing frozen matrix oracle. Ridge, two-part ridge, histogram boosting,
two-part boosting and state boosting match exactly; parallel ExtraTrees
summation uses a 1e-12 absolute tolerance for native scheduling variation.
Carry-forward remains unchanged. Warm calls must make no additional native fits,
while fresh evaluation produces the matching fresh predictions. Training bytes,
target, row order, dtype, parameters and source-scope changes require a refit.
Bounds, weak-reference release, digest rejection before unpickling, write/setup
failure, concurrency and unseeded passthrough are covered.

A synthetic 5,000×32 seeded histogram regressor measured 0.307 s cold vs 0.0030 s
reuse, with identical predictions and 242,433 cached bytes. This is a local unit
cost, not full hosted timing, peak-RAM certification or historical validation.
First fits remain cold, and feature staging still runs. Existing exact-head
numeric parity and full-suite checks remain the promotion gate.

Fit hit/miss timing and the existing expanded-component reuse log use the
hosted Uvicorn handler, matching existing RSS attribution. A logger level alone
does not attach a handler to the root logger. No product-screen text is added.

Hosted acceptance requires one normal owned run: collect native fit hit/miss
counts and elapsed times, total materialization time/RSS, source receipts, full
coverage and coherent publication. The first run after deploy can reuse models
across cells, but starts with an empty process cache. No repeated expensive
refreshes solely to manufacture hits; no claim that the 512-MiB reliability or
full product acceptance gates are complete before measurement.

## Full-suite test isolation

The first stable run passed 3,241 tests but four sequencing/concurrency tests
read the full pytest process's accumulated ~541 MB RSS, so their work never
entered the lane whose ordering they tested. Injecting that ambient RSS reproduced
all four failures in isolation. Those four tests now explicitly provide the
intended admissible 300-MiB initial state. Production limits/admission code are
unchanged; dedicated over-cap refusal and isolated resource acceptance remain
separate checks. This resolves test-order dependence, not the live ~502-MiB
peak or outstanding hosted memory-margin gate.
