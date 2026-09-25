# Workstream — Performance

## State
**ACTIVE — PRODUCTION ACCEPTANCE / MARKET COLD-PATH VALIDATION**

The prior PR #211 K/DST-only Management Gate is obsolete for this active directive. Performance is currently executing the production repair caused by the FSFFL Dynasty league regressing from valid 7/7 intelligence to visible 3/7 after the Market deployment.

## Incident
Physical-iPhone acceptance after Market PR #220 / production SHA `ff3e0fbe8ff0827d123e6d465b42116512e6d820` showed the existing FSFFL Dynasty league (`jimmygoodjob`, Sleeper league `1312071960615731200`) at 3/7 with governed Simulation / position-strength evidence unavailable even though a valid promoted complete bundle already existed.

The newest provider/state checkpoint and a failed enrichment were being treated as restart authority. `restore_runtime_snapshot()` used `runtime_last_good_bundle` only for queued/running jobs, not terminal failed/interrupted refreshes. This allowed a failed newer state refresh to displace a previously promoted complete bundle on restoration. Readiness Presentation also allowed a terminal failed job to override a complete restored context.

The mobile Refresh Intelligence control separately rendered abnormally narrow because its readiness grid defined three columns while rendering four elements.

## Repair sequence
### PR #222 — merged
Title: **Hotfix: preserve promoted 7/7 intelligence across failed refreshes**

Merge SHA: `514b27e9ee55d6b1984bd72e004a8eb826b174d4`

Repair:
- same-league provider revalidation cannot demote an already complete Forecast/Simulation/Value runtime merely because a fresher State exists;
- fresher State history is retained while the promoted bundle remains serving authority;
- failed/interrupted enrichment may restore the same-league promoted last-good bundle;
- cross-league last-good restoration remains forbidden;
- terminal failed/interrupted lifecycle status no longer makes a genuinely complete restored context render below 7/7;
- Refresh Intelligence now owns an explicit fourth readiness-grid column and uses no-wrap/min-content sizing on mobile;
- static assets cache-busted to `20260925-lastgood-repair1`.

All six applicable PR validation workflows were green on head `a56d1991145717a39296f7d83a6f82426b7bac5d`.

### PR #226 — merged; startup-restoration evidence retained
Title: **Performance: log restored runtime readiness after startup**

Merge SHA:
`50614b1deeeccfe61c7b4fe3acc46111f7ad23cc`

Historical validation deployment:
`dep-dar7oi0473hc73a5hs4g`

Adds explicit startup evidence for restored league/state and Forecast/Simulation/Value completeness.

Production evidence:
- 2026-09-25 13:52:35Z startup:
  `league=sleeper:1312071960615731200 state=203227df... forecast=True simulation=True value=True complete=True`
- 2026-09-25 14:39:09Z subsequent restart:
  same league/state and `forecast=True simulation=True value=True complete=True`;
- no automatic `POST /api/intelligence/jobs` after those restarts;
- no startup errors observed.

This is direct production evidence that the promoted last-good bundle survives restart after the terminal failed refresh.

### PR #227 — merged, test-only
Title: **Test: lock interrupted-refresh last-good restoration**

Merge SHA:
`ee221b29969c5fd83c75e7ea45903deca25c6410`

PR #227 adds the missing interrupted-refresh restoration regression. Its workflows were green. It contains no production runtime code and therefore does not require a distinct production deploy to make the #222 behavior active.

### PR #235 — merged and live
Title: **Performance: reuse exact Market evaluation inputs on cold discovery**

Merge SHA / current Render production SHA:
`3c252aedb5974f40fabe2c16cce01e8e106a2b74`

Render deployment:
`dep-dar9kg142hec73dglcq0` — **LIVE**

Production startup at 2026-09-25T16:00:24.900936Z restored:
`league=sleeper:1312071960615731200 state=203227df... forecast=True simulation=True value=True complete=True`.

No automatic `POST /api/intelligence/jobs` occurred after that restart and no startup errors were observed.

PR #235 is a Performance-only exact-input reuse optimization layered on the merged PR #232 discovery contract. It:
- reuses the already built canonical Trade Center ownership index instead of rebuilding team ownership for every candidate asset resolution;
- reuses one exact Cardinal profile / market-value map across candidate economics and the eight-path preliminary Decision screen;
- reuses one exact provisional forecast-floor input set and baseline-lineup map across those same eight Decision paths;
- retains resolver fallback on any ownership-index miss;
- changes no candidate admission/order, strategic hypothesis, cheap economic-screen semantics, family pruning, dominance/diversity rule, eight-path budget, For You eligibility, or zero-broad-Simulation boundary.

PR #235 head `1674039186fbe06cfd81e20254dc0bd5d8cbb73c` passed repository-wide `pytest -q`, PR164 focused corrective regression, and Live Forecast corrective trace. Therefore the PR #232 discovery/admission/dominance/diversity/intent/zero-Simulation regressions all remained green with the optimization.

The prior physical-device baseline remains the comparison point: search catalog cold generation was 2.698s, quick workspace 36.705s, full workspace 48.396s, then exact in-process workspace reuse fell to 0.172s. No authenticated Market request has yet reached the fresh #235 process, so a truthful post-optimization cold production timing is not yet available. This is a validation gap, not evidence that the optimization succeeded or failed.

## Persisted production truth
Latest durable user context now points directly to the restored/promoted FSFFL Dynasty State:
`203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed`.

Latest promoted `runtime_last_good_bundle` is the same State:
`203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed`

That state has current reusable:
- `current_forecast_evidence`;
- `live_simulation_analytics`;
- `current_market_value`.

The latest lifecycle row remains terminal failed for a newer enrichment attempt. Production startup nevertheless restores the promoted complete bundle, as intended.

## Mobile Refresh Intelligence state
Current canonical/live `product_shell.js` retains the repaired control under Market static generation `20260925-market-corrective1` and uses:
- four explicit readiness columns: mark / step / copy / action;
- `white-space: nowrap`;
- `min-width: max-content`;
- mobile-specific compact padding/font sizing.

Code/CI validation is complete. Physical-iPhone confirmation of the corrected width remains required before Presentation acceptance is claimed.

## Remaining acceptance work
Continue without asking Management to repeatedly refresh.

Remaining gates:
1. authenticated physical-iPhone request after the live #226 build must show the existing FSFFL Dynasty league as truthful 7/7 from restored last-good;
2. Home, Franchise, and Market must remain populated from the correct league after restore;
3. mobile Refresh Intelligence must render as a normal single-line actionable control;
4. foreground surfaces must remain responsive;
5. no stale-job or cross-league contamination may appear.

The pre-#235 physical-device timing proves Home/Franchise were responsive but established the Market cold-path baseline:
- `/api/home`: approximately 0.3–0.7s;
- `/api/my-team`: approximately 0.1–0.5s;
- first `/api/opportunities/workspace/quick`: **36.705s**;
- first `/api/opportunities/workspace`: **48.396s**;
- subsequent cached full workspace: **0.172s**.

PR #235 is the bounded repair for that cold path and is now live. The foreground-responsiveness gate remains open until the first authenticated post-#235 cold Market request provides direct production timing. Do not infer success from CI or cache-hit behavior.

Restart/failure preservation is production-validated again on #235, including correct league/state identity, complete Forecast/Simulation/Value restoration, no startup errors, and no automatic heavy intelligence launch.

## Boundary
Do not weaken Forecast/Simulation/Value authority, fabricate missing evidence, change canonical 50,000 Simulation fidelity, or force a fresh refresh merely to make readiness green.

The separate K/DST Forecast authority work remains a Forecast/Product concern. It is not the current Performance stop state for this existing-league restoration directive.
