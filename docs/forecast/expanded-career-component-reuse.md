# Expanded Career Y4–Y7 execution reuse

The dynamic Career bridge still acquires current inputs, fits candidate forecasts,
checks coverage, and builds Current and terminal contributions. Only its pure
expanded Y4–Y7 Value calculation can use a saved numerical component. Final Career
capture identity, freshness checks and publication remain unchanged.

## Exact dependency boundary

The existing `long_term_intrinsic_input_fingerprint` owns the numerical identity:
all policy rows (including means and uncertainty), player cohort/positions,
scoring coordinate, season, league rules, authority/model versions, permutations
and seeds. Volatile contract provenance is excluded by that existing function.
Changing a consumed input requires the normal accepted calculation.

The optional adapter is invoked inside the existing admitted Career build, after
candidate Forecast materialization. It creates no acquisition, page-reader,
startup, scheduler or worker lifecycle. Callers without the adapter retain the
original direct calculation. No Value/Forecast/Simulation formulas change.

The execution cache uses the existing bounded persistence store. One mutable
latest slot per season/rules/cohort/model replaces numerical revisions; it does
not append one large artifact per refresh. The slot key is not proof of numerical
identity: restored payloads must validate and match the current semantic
fingerprint, model metadata, seeds, full cohort and positions. Invalidated,
incompatible or malformed entries rebuild. Cache transport errors also fall
back to the owned calculation. Rejected payload references are released before
allocating new calculation workspaces. The existing Shapley execution caches
are cleared and the existing memory guard runs before optional serialization;
guard refusal skips the write without discarding the computed result. No process
cache is retained.

The widest safe sharing scope is the pure football Forecast board and rules.
Equivalent inputs can reuse across leagues; differing boards cannot. This
component contains no user/league/State IDs, owner preferences, roster slots,
source-capture receipts or credentials. Existing private backend access is
unchanged; there is no new endpoint. Final Career output remains bound to its
own canonical State and current source manifest.

## Resource consequences and verification

Each reached expanded-composition phase adds one pooled-store read. A miss adds
one upsert/serialization; a hit adds no write and skips the expensive Value
calculation. Different cohorts/rules can create additional slots; this is not a
globally capped artifact table, and no historical retention/deletion policy is
changed. Cold work and candidate fitting remain; memory headroom is not solved
by the presence of a cache. Read latency and payload bytes require hosted proof.

Focused validation:

```
pytest -q tests/test_long_term_intrinsic_reuse.py tests/test_dynamic_career_allocation.py
```

Tests compare restored and computed typed results, preserve reader-free ownership
and board release, and require rebuilds for numerical/uncertainty, cohort, rules,
model, invalidation and damaged-payload changes. A new adapter instance must hit
without process hints. Existing exact-head numeric parity and hosted bridge tests
remain the final merge gate.

A six-player synthetic fixture with JSON encode/decode transport measured 0.419 s
cold versus 0.0021 s reuse, 32,681 serialized bytes, two reads and one write, with
identical results. This is a small local execution demonstration, not a Render
benchmark, network measurement, memory result or full-refresh speed claim.

Hosted acceptance: on the next normal controlled refresh record the hit/miss,
composition phase time/RSS, artifact read/write bytes, exact State/generation,
and unchanged coverage. Fresh inputs may correctly force a miss. A changed-input
miss and unchanged-input hit must never be confused with skipping source checks.
Do not run repeated expensive refreshes merely to manufacture a hit.
