# PR #311 production adoption decision — 2026-10-01

Status: **AUTHORIZED FOR PRODUCTION / PRIVATE-BETA PROMOTION WITH MONITORED RESIDUAL RISK**

Management explicitly authorized promotion of PR #311 after reviewing the complete available evidence.

## Decision

Promote PR #311 to `main` and the FSFFL NEXT private beta with:

- canonical Simulation count unchanged at 50,000 trials;
- `numpy-pcg64-batched-gauss-v1`;
- NumPy batch size 500;
- versioned RNG/replay identity and the legacy Python replay compatibility path preserved;
- the PIT-history streaming corrective preserved;
- publication/restart identity safeguards preserved.

No additional generic code/model review cycle is required before this promotion.

## Evidence supporting adoption

The original hosted experiment completed Forecast, Simulation, Current Value, Intrinsic and atomic publication, but failed the then-current resource gate at process high-water RSS 576,552,960 bytes versus the 536,870,900-byte hard limit.

Subsequent hosted attribution materially changed the interpretation of that failure. The dominant transient allocation was localized to `forecast.raw_replay_history_discovery`: persisted PIT history materialized as many as 32 complete JSONB league-State payloads/validated object graphs at once. That phase increased process high-water by 231,202,816 bytes. It was not owned by the NumPy Simulation kernel.

The corrective changes PIT-history replay discovery to materialize/validate candidates one at a time while preserving ordering, PIT validation, candidate limit, compatibility/fingerprint selection, fallback behavior and governed Forecast/Simulation/Value semantics. A deterministic regression protects the lazy materialization contract.

A clean hosted 50,000-trial build during attribution completed publication at process high-water RSS 361,902,080 bytes. Simulation attachment, lineup compilation, weekly scoring and kernel/result aggregation did not increase that high-water; sampled Simulation stages were at most 349,007,872 bytes.

Final code validation includes a 1,903-test local suite, successful exact-head CI/focused workflows, multiple clean whole-PR reviews, fixed 50k replay digests for supported Python 3.11/3.12, publication-boundary Simulation artifact identity protection, and deterministic changed-State downstream validation.

The original statistical study remains unchanged: probability ±0.002 and rank-distribution TV ±0.005 passed; expected-wins ±0.001 remains **inconclusive**, with worst observed point difference +0.002395, simultaneous intervals including zero, and zero expected-wins ordering inversions. Adoption does not relabel that evidence as an expected-wins equivalence pass.

## Explicit residual risk accepted by Management

The corrected exact PR head was **not** rerun through the planned final hosted journey with genuine concurrent external Home / My Team / Product Context HTTP requests and subsequent exact-branch restart restore. The Work browser environment blocked access to the private-beta product host under URL policy. This missing test is recorded as residual deployment evidence, not silently treated as passed.

Management accepts that residual risk because the blocking condition is the acceptance-tool environment, while the observed defect that caused the prior memory failure has been specifically attributed, narrowly corrected, regression-protected and supported by a later clean 50k hosted memory profile.

## Promotion monitoring / rollback rule

The first genuine private-beta refresh after promotion is the final observational hosted validation.

Capture and preserve:
- process high-water RSS and headroom against 536,870,900 bytes;
- Forecast / Simulation / Current Value / Intrinsic readiness and atomic publication;
- foreground Home / My Team / Product Context behavior when naturally exercised during heavy work;
- restart/restore continuity at the next applicable restart.

If process high-water reaches or exceeds 536,870,900 bytes, or promotion exposes a publication/restore continuity defect, treat it as an immediate Management incident and roll back rather than beginning another unbounded micro-optimization cycle.

If the promoted private beta behaves consistently with the corrected evidence, close #311 and resume capability development. Heavyweight lifecycle acceptance is not to become the default gate for ordinary capability work.
