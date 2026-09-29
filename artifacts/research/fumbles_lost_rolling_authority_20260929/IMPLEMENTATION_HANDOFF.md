# Bounded Implementation Handoff — Rolling FUMBLES_LOST + Lifecycle

Date: 2026-09-29  
Research status: **DIRECTIVE COMPLETE — RESEARCH**  
Production status: **NOT CHANGED BY RESEARCH**

## Objective

Implement only the frozen FUMBLES_LOST authority lifecycle:

- completed Week 0: explicit omission + corrected materiality fallback only;
- completed Week 1: explicit omission + corrected materiality fallback only;
- completed Weeks 2-17: the already-accepted rolling first-party point model;
- Week 18: no fabricated remaining-season point estimate;
- 2027+: target-season table produced by the minimal governed annual refresh/freeze.

Then resume the full hosted lifecycle acceptance on the existing #296 runtime lineage.

Do not reopen #294/#295/#296 architecture.

## Authoritative tables/docs

Use:
- `ROLLING_PRODUCTION_TABLE.json`;
- `MATERIALITY_RULE.md`;
- `SEASON_START_LIFECYCLE.md`;
- `ANNUAL_ROLLOVER_CONTRACT.md`.

The old primary-population-only materiality bounds are retained only as legacy audit fields. They are **not** the production fallback bounds.

## Week 0 / Week 1 behavior

Do **not** invoke the rolling mean model.

Required behavior:
1. leave `fum_lost` explicitly omitted;
2. do not synthesize a zero FUMBLES_LOST observation;
3. retain PARTIAL/degraded scoring diagnostics;
4. use the target-season Week-0/Week-1 materiality bound only if population eligibility and the runtime inequality both pass;
5. otherwise keep the downstream blocker.

Week 1 current opportunities do not create point authority.

## Weeks 2-17 rolling point model

Update the first-party supplement only.

Required behavior:

1. Accept canonical `completed_through_week` from 2 through 17.
2. Require provider NFL-state cutoff to equal canonical State exactly.
3. Fetch and hash **exactly Weeks 1..c**.
4. Never request/use week > c.
5. Preserve exact lost-fumble semantics.
6. Preserve the frozen target-season position lost-fumble rates.
7. Preserve `ROLE_PRIOR_GAMES = 4`.
8. Resolve the exact cutoff scalar from `ROLLING_PRODUCTION_TABLE.json`.
9. Resolve the exact cutoff/position uncertainty floor from the same table.
10. Preserve cold-start/identity-light non-zero uncertainty.
11. Include completed week, scalar, annual table/version, current-input hashes and uncertainty contract in authority fingerprint/provenance.
12. State advance must invalidate/rebuild through the existing selective current Forecast/Simulation path.
13. Do not mutate retained preseason raw Forecast evidence.
14. Week 18 must not call this rolling model.

Suggested model version remains:
`next2-fumbles-lost-first-party-v2:rolling-completed-week`.

The accepted Week-2→17 scalar/rate/floor point-model table is not reopened by the materiality correction.

## Corrected materiality fallback

When the FUMBLES_LOST point estimate is unavailable:

1. keep `fum_lost` in omitted stats;
2. determine evidence tier / fallback population;
3. read that position/cutoff population eligibility from the frozen table/contract;
4. if ineligible, fail closed;
5. read the corrected all-population event bound;
6. multiply by the league's actual `fum_lost` scoring coefficient;
7. require non-zero governed supported-fantasy-point stddev;
8. classify `NON_MATERIAL_PARTIAL` only if:

`impact_bound_90 <= 0.10 * 1.645 * supported_fp_stddev`;

9. Simulation may omit the partial-coordinate blocker only when **every** Simulation-relevant subject passes;
10. preserve partial/degraded status and numeric omission diagnostics.

### Population rules

Eligible observed evidence tiers, subject to the inequality:
- history + current;
- history only;
- current only;
- cold start, except the restriction below.

Identity-light:
- canonical offensive position must be known/non-conflicting;
- eligibility mirrors the matching cold-start position/cutoff;
- otherwise fail closed.

Hard restriction:
- **QB cold-start and QB identity-light are fallback-ineligible at completed Weeks 13-17.**

Unknown/conflicting position is always fallback-ineligible.

### Corrected current Week-3 bounds

For FSFFL's -1 lost-fumble rule:
- QB event/score bound **10.9286**, minimum supported FP stddev **66.44**;
- RB **4.8571 / 29.53**;
- WR **3.6429 / 22.15**;
- TE **2.4286 / 14.76**.

These supersede the original primary-population-only Week-3 materiality thresholds.

## Week 18

No remaining-season rolling estimate.

Do not create:
- a Week-18 calibration scalar;
- a zero FUMBLES_LOST coordinate;
- an artificial full-coverage state.

## Annual rollover — 2027+

Implementation should make target season/table identity explicit rather than retaining a hard-coded 2026 authority forever.

The annual refresh is deterministic but requires a small governed freeze before target-season point authority:

1. ingest finalized exact weekly data through `Y-1`;
2. verify exact lost-fumble semantics/source hashes;
3. recompute cumulative position rates and opportunity/game priors;
4. recompute player prior sufficient statistics;
5. recompute the same global cutoff scalars for Weeks 2-17;
6. carry prior uncertainty floors forward and, for each cutoff `c`, widen with the **prefix maximum** of the newly completed held-out season's residual RMSE over every cutoff `k <= c`;
7. carry prior materiality bounds forward and widen with the new all-population historical maximum when necessary;
8. revalidate the population eligibility matrix;
9. persist/fingerprint the target-season table.

No new Forecast-family search is part of annual rollover.

If the annual freeze is missing or fails its bounded gates, no point authority is granted for that target season. Preserve explicit omission/materiality if valid; otherwise fail closed.

## Required tests

### Season start
- completed Week 0 emits no first-party FUMBLES_LOST point row;
- completed Week 1 emits no first-party FUMBLES_LOST point row;
- both preserve `fum_lost` omission;
- both can proceed only through corrected materiality authority;
- no zero substitution;
- Week 2 transitions into the accepted rolling point model.

### Rolling Forecast
- Week 2 reproduces v1 mean/scalar/uncertainty numerically;
- Week 3 scalar remains `0.6183406074632098`;
- all cutoff scalars and uncertainty floors Week 2-17 match the frozen table;
- fetch set is exactly Weeks 1..c;
- provider cutoff mismatch fails closed;
- no future week enters hash/opportunity total;
- target-season position rates and 4-game role prior are unchanged;
- cold/identity-light point-model uncertainty remains non-zero;
- cutoff included in authority fingerprint;
- c→c+1 changes supplement fingerprint and selectively invalidates current consumers;
- Week 18 cannot invoke point authority.

### Materiality
- corrected all-population bound is used, never the legacy primary bound;
- missing `fum_lost` remains omitted;
- no zero FUMBLES_LOST observation is synthesized;
- scoring coefficient comes from league rules;
- non-zero supported FP uncertainty is required;
- bound passes exactly at the inequality and fails immediately below it;
- QB cold-start/identity-light Week 13-17 fail closed regardless of numeric inequality;
- unknown/conflicting position fails closed;
- one failing/ineligible Simulation-relevant subject preserves the blocker;
- all passing relevant subjects permit Simulation only with explicit `NON_MATERIAL_PARTIAL`;
- taxi/IR/non-consumed scope remains unchanged;
- Intrinsic continuation retains degraded provenance and does not change Shapley math.

### Annual rollover
- target-season table cannot be reused under the wrong season;
- source hashes/semantics are part of annual freeze identity;
- no current/future target-season outcomes enter rates/calibration/floors;
- new annual floor at cutoff `c` equals or exceeds both the prior frozen floor at `c` and every newly completed held-out residual RMSE at cutoffs `k <= c`;
- new materiality bound cannot be lower than prior frozen bound;
- annual adequacy/population failures prevent automatic point promotion.

### Regression boundaries
- Y2/Y3 unchanged;
- Y4-Y7 unchanged;
- K/DST unchanged;
- Current Intrinsic mathematics unchanged;
- #294/#295/#296 persistence/restore/team/publication architecture unchanged.

## Acceptance sequence

After implementation:
1. focused tests;
2. full suite;
3. bounded P1/P2 review;
4. deploy on current #296 lineage;
5. prove current canonical cutoff builds the rolling FUMBLES_LOST supplement;
6. prove fallback uses the corrected population-bound contract;
7. prove no Week-0/1 fake point estimate can be created;
8. resume the previously blocked hosted clean-first-run / switch / same-State / restart acceptance journey.

No additional Research decision is required before this bounded implementation.
