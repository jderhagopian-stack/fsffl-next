# Workstream — Performance

## State
**ACTIVE — PRODUCTION ACCEPTANCE / LAST-GOOD RESTORATION**

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

### PR #226 — merged and currently live
Title: **Performance: log restored runtime readiness after startup**

Merge SHA / current Render production SHA:
`50614b1deeeccfe61c7b4fe3acc46111f7ad23cc`

Render deployment:
`dep-dar7oi0473hc73a5hs4g` — **LIVE**

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

## Persisted production truth
Latest durable user context still records the fresher failed-refresh State `3014bb7625...`, which is expected state-history/runtime-context evidence and is not the serving complete-bundle identity.

Latest promoted `runtime_last_good_bundle` is:
`203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed`

That state has current reusable:
- `current_forecast_evidence`;
- `live_simulation_analytics`;
- `current_market_value`.

The latest lifecycle row remains terminal failed for a newer enrichment attempt. Production startup nevertheless restores the promoted complete bundle, as intended.

## Mobile Refresh Intelligence state
Live `product_shell.js` on production SHA #226 uses:
- cache generation `20260925-lastgood-repair1`;
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

Post-restart physical-device timing on the live #226 build now proves Home/Franchise are responsive but exposes a Market cold-path defect:
- `/api/home`: approximately 0.3–0.7s;
- `/api/my-team`: approximately 0.1–0.5s;
- first `/api/opportunities/workspace/quick`: **36.705s**;
- first `/api/opportunities/workspace`: **48.396s**;
- subsequent cached full workspace: **0.172s**.

Therefore the foreground-responsiveness gate remains red specifically on cold Market discovery. Performance must repair/bound that cold path without changing Search/Decision/Simulation authority.

Restart/failure preservation itself is now production-validated by the two #226 startup records above.

## Boundary
Do not weaken Forecast/Simulation/Value authority, fabricate missing evidence, change canonical 50,000 Simulation fidelity, or force a fresh refresh merely to make readiness green.

The separate K/DST Forecast authority work remains a Forecast/Product concern. It is not the current Performance stop state for this existing-league restoration directive.
