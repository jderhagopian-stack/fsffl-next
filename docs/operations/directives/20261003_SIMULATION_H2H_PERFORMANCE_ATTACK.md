# Simulation H2H performance attack — 2026-10-03

## Status
ACTIVE — Tier A internal Simulation performance optimization.

## Accepted prerequisite
Postseason optimization PR #351 is accepted and closed. Its governed hosted 50,000-run benchmark reduced:
- postseason: **55.888s -> 8.836s**;
- kernel: **104.901s -> 61.007s**;
- full Simulation baseline after that tranche: approximately **84s** (use exact hosted evidence when reporting the H2H closeout).

Do not reopen the accepted postseason tranche absent contradictory evidence.

## Current target
The new largest measured kernel bottleneck is the NumPy-path matchup/H2H reconstruction pass at approximately **20.4s**. Team-origin ordering at approximately **12.5s** is next only after H2H reaches diminishing returns.

## Frozen authority
Preserve exactly:
- 50,000 canonical trials;
- `numpy-pcg64-batched-gauss-v1`;
- batch size 500;
- regular-season standings/tiebreak semantics;
- playoff/championship outputs and accepted #351 execution plan;
- finish distributions;
- team-origin future-pick distributions and governed H2H tiebreak logic;
- Multiverse/common-world behavior and representative-world identity;
- RNG draw count/order;
- deterministic replay identity and all published Simulation contracts.

Simulation 2.0 semantics remain accepted and closed. Do not reopen #324-#333.

## Authorized structural optimization
Eliminate the second per-trial Python schedule scan in the NumPy production path by deriving schedule-dependent products in the existing bounded batch pass when exact semantics permit. In particular:
- compute simulated H2H outcome matrices batch-wise;
- precompile H2H game-count topology because scheduled games are invariant across worlds;
- derive Multiverse biggest-blowout and biggest-upset candidates batch-wise with the scalar path's exact first-on-tie selection behavior;
- keep the legacy Python RNG path unchanged;
- do not alter score generation or RNG sequencing.

## Required proof
- exact complete-result equivalence against a literal scalar reference across multiple seeds;
- standing 2/4/6/8 postseason, exact-provider, future-pick, Multiverse, common-world, and fixed 50k replay regressions remain green;
- focused tests + full CI;
- one governed hosted 50k benchmark on the exact optimization head using the existing exact profiler;
- report H2H/matchup cost, kernel wall time, full Simulation wall time, seconds saved, and percentage recovered against the accepted #351 baseline.

If the H2H tranche is clean and reaches diminishing returns, advance directly to team-origin ordering. No unrelated platform acceptance is authorized.
