# Simulation production performance corrective — 2026-10-02

## Status
ACTIVE — Tier A module-internal Simulation performance corrective.

## Authority boundaries
Simulation 2.0 remains accepted and closed. This work does not reopen #324-#333.

Production authority remains:
- 50,000 canonical trials;
- `numpy-pcg64-batched-gauss-v1`;
- batch size 500.

Do not lower the count, alter RNG, weaken playoff/tiebreak semantics, remove outputs, change replay identity, or trigger unrelated platform retesting.

## Required sequence
1. Replace sampled/extrapolated hot-loop profiling with direct measurement sufficient to account for essentially the full exact kernel wall time.
2. Directly measure at least cooperative yield, trial/static setup, RNG generation, vectorized matchup/scoring, full per-trial schedule/H2H scan, standings, postseason, team-of-origin future-pick ordering, Multiverse/common-world work, aggregation/observer work, and explicit loop/scheduler residual.
3. Run one representative governed hosted FSFFL 50k execution and reconcile measured phases to the exact outer kernel wall time with only a small explicit residual.
4. Let that corrected measurement determine the first optimization target.
5. Implement only the highest-value bounded optimization that preserves exact outputs, replay identity, authority, and semantics.
6. Validate exact-output/replay equivalence, focused tests, full CI, and one hosted 50k before/after benchmark.
7. Record actual seconds saved and new total Simulation wall time in canonical ops state.

## Promotion classification
Tier A while the published Simulation contract, model/replay identity, persistence behavior, and authority remain unchanged. Escalate only if direct evidence shows a broader contract/runtime impact.

## Acceptance
- profiler reconciliation explains essentially all kernel wall time;
- optimization target is selected from corrected measurement rather than the prior incomplete hotspot ranking;
- exact 50k governed output digest/replay identity is unchanged;
- focused tests and full CI pass;
- hosted benchmark proves before/after runtime on the governed FSFFL path;
- canonical operations docs contain exact PR/SHA/deploy/test/runtime evidence and any remaining limitations.
