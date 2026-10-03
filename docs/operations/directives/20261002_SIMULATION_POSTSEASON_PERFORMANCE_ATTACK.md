# Simulation postseason performance attack — 2026-10-02

## Status
ACTIVE — Tier A internal Simulation performance corrective.

## Controlling baseline
The corrected exact production profile on the representative governed FSFFL 50k run is authoritative:
- full Simulation: ~127.5s;
- exact kernel: **104.900603s**;
- postseason/playoff phase: **55.887840s**;
- H2H schedule scan: **17.668497s**;
- team-origin ordering: **11.978498s**.

Postseason is therefore the first optimization target.

## Frozen authority
Do not reopen Simulation 2.0 or #324-#333. Preserve exactly:
- 50,000 trials;
- `numpy-pcg64-batched-gauss-v1`;
- batch 500;
- governed 2/4/6/8-team and exact-provider bracket semantics;
- bracket/tiebreak rules;
- playoff/championship probabilities;
- finish distributions;
- team-origin pick outputs;
- Multiverse/common-world behavior;
- deterministic replay identity and RNG consumption/order.

## Required execution
1. Add profiler-only exact attribution inside the current postseason phase for repeated validation/bracket compilation/canonicalization, seed setup, participant resolution, score/RNG game execution, winner/elimination bookkeeping, and residual.
2. Run one governed hosted FSFFL 50k profile before optimization.
3. Let the exact split choose the structural change.
4. Prefer hoisting invariant bracket work outside the trial loop, precompiled compact execution plans, and removal of repeated Python/Pydantic/dict/list/sort work. Batch/vectorize only where exact RNG order and semantics remain unchanged.
5. Prove exact serialized/result and replay equivalence across governed standard 2/4/6/8-team brackets, exact-provider structures, deterministic fixtures and multiple seeds, including downstream future-pick and Multiverse dependencies.
6. Run focused tests + full CI only; no unrelated platform acceptance.
7. Deploy the exact optimization head and run one governed hosted FSFFL 50k benchmark with the same exact profiler.
8. Report seconds and percentage recovered versus 55.887840s postseason, 104.900603s kernel and ~127.5s full Simulation.
9. If another bounded postseason optimization is obvious and exact after the first benchmark, continue. Move next to H2H and team-origin ordering only after postseason reaches diminishing returns.
