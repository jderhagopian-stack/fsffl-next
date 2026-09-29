# Bounded Implementation Handoff — Rolling FUMBLES_LOST

Date: 2026-09-29  
Research status: **SUPPORTED**  
Production status: **NOT CHANGED BY RESEARCH**

## Objective

Replace the hard Week-2-only first-party supplement guard with the frozen Week-2..17 rolling contract, then resume the full hosted lifecycle acceptance on the existing #296 runtime lineage.

Do not reopen #294/#295/#296 architecture.

## Forecast implementation

Update the first-party FUMBLES_LOST supplement only.

Required behavior:

1. Accept canonical `completed_through_week` from 2 through 17.
2. Require Sleeper current-input NFL state cutoff to exactly equal canonical State.
3. Fetch and hash weekly opportunity rows for **every completed week 1..c**.
4. Never request/use week > c.
5. Keep exact lost-fumble target semantics and current opportunity schema.
6. Keep the frozen 2021-2025 position lost-fumble rates.
7. Keep `ROLE_PRIOR_GAMES = 4`.
8. Replace one Week-2 scalar with the exact cutoff scalar in `ROLLING_PRODUCTION_TABLE.json`.
9. Replace static position uncertainty floors with the exact cutoff/position rolling floors in the same table.
10. Preserve cold-start/identity-light floor behavior.
11. Include completed week, cutoff scalar, rolling-floor contract version and all current-input row hashes in authority fingerprint/provenance.
12. State advance must invalidate/rebuild the current supplement and current Forecast/Simulation consumers through the existing selective invalidation path.
13. Do not mutate retained preseason raw Forecast evidence.
14. Week 18 must not fabricate a new rolling projection.

Suggested version:
`next2-fumbles-lost-first-party-v2:rolling-completed-week`.

## Materiality fallback

Add a typed Forecast/consumer authority assessment; do not make this a Presentation-only exception.

When the first-party FUMBLES_LOST estimate is unavailable:

1. keep the scored fantasy-point row partial with `fum_lost` explicitly omitted;
2. obtain the position/cutoff event bound from the frozen rolling table;
3. multiply by the league's actual `fum_lost` scoring coefficient;
4. compare against the subject's already-governed supported fantasy-point stddev using:

`impact_bound_90 <= 0.10 * 1.645 * supported_fp_stddev`;

5. classify the subject `NON_MATERIAL_PARTIAL` only if the inequality passes;
6. Simulation may omit the existing partial-coordinate blocker only when every simulation-relevant subject passes;
7. otherwise preserve the blocker;
8. do not create a zero event Forecast;
9. do not claim COMPLETE/FULL scoring coverage;
10. expose the omission, bound and reason in authority diagnostics.

Current Intrinsic may continue only through an explicitly degraded/non-material-partial current-season input state; its Shapley math and Y2/Y3 future inputs remain unchanged.

## Required tests

### Rolling Forecast
- Week 2 reproduces v1 mean/scalar/uncertainty numerically.
- Week 3 uses scalar `0.6183406074632098`.
- Each cutoff 2..17 resolves exactly one frozen scalar.
- Fetch set is exactly weeks 1..c.
- Provider cutoff mismatch fails closed.
- No future week enters hash or opportunity total.
- Position rates and 4-game role prior remain unchanged.
- Cutoff/position uncertainty floor is applied.
- cold/identity-light remains non-zero.
- exact lost-fumble semantics only.
- total fumbles rejected.
- cutoff included in authority fingerprint.
- state advance c→c+1 produces a distinct supplement fingerprint and selective current-consumer invalidation.
- Week 18 cannot call this rolling model.

### Materiality
- missing `fum_lost` remains in omitted stats.
- no zero `FUMBLES_LOST` observation is synthesized.
- scoring weight is read from league rules, not hardcoded.
- bound passes exactly at the frozen inequality and fails immediately below it.
- missing/zero supported FP stddev fails closed.
- one failing simulation-relevant subject preserves the Simulation blocker.
- all passing relevant subjects permit Simulation with explicit `NON_MATERIAL_PARTIAL` status.
- taxi/IR/non-consumed scoping remains unchanged.
- Intrinsic continuation retains degraded provenance and does not alter Shapley formula.
- K/DST family authority remains untouched.

### Regression boundaries
- Y2/Y3 future Forecast unchanged.
- Y4-Y7 unchanged.
- Current Intrinsic math unchanged.
- no changes to #294/#295/#296 persistence/restore/team/publication identity code.

## Acceptance sequence

After implementation:
1. focused unit tests;
2. full suite;
3. deploy on current #296 lineage;
4. prove current canonical cutoff builds a first-party rolling FUMBLES_LOST supplement;
5. prove current Forecast no longer fails solely on the Week-2 guard;
6. prove unavailable FUMBLES_LOST follows the materiality rule rather than unconditional league-wide blockage;
7. immediately resume the previously blocked hosted clean-first-run / switch / same-State / restart acceptance journey.

Research does not require another model-family study before this implementation.
