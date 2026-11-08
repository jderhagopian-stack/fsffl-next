# Intrinsic magnitude release — November 8, 2026

## Authorized scope

User explicitly directs historical-actuals scale evaluation, implementation and deployment to the existing Render service. No provider/plan migration or raw Forecast/Simulation/Shapley/Career changes. [Decision, original research, exact evidence, supported format and limitations](../../value/intrinsic-magnitude-presentation-v1.md).

Baseline main verified `e0e045a44b4c5b19061922995b1a49d3347c91d2`. Candidate branch `feat/intrinsic-linear-display-20261108`, isolated checkout `/workspace/fsffl-scale-release`. Prior research remains draft PR #464; production integration is a separate narrowly scoped release.

## Implementation

- Central fixed magnitude reference transform with bounded format resolution; independent Market, signed raw preservation, missingness and explicit overflow.
- Supported Career coordinate retains reference completeness validation while its display fingerprint and scores are independent of current raw population distribution.
- Current saved raw lens projection is read-only, versioned and bounded to one existing response; no extra database reads or retained full artifacts. No new connection/persistence owner.
- Roster/Explore/Trade/League displays consume lens fields; Player Intelligence uses the same Career-owned exact-State three-year raw source.
- Percentile-based disagreement replaces subtraction of independently scaled indexes in affected UI. Raw Position & Depth and Decision calculations are unchanged.
- Publication owner stamps matching-state nested Intrinsic generation IDs; stale evidence is not relabelled.

## Validation before promotion

Focused presentation/API/continuity/static selections: **168 passed**, one existing Starlette/httpx deprecation warning, focused rerun. Includes fixed-ratio and population stability, unsupported-format boundary, missing/overflow handling, immutable saved projection, common roster/card formula and generation stamping. JavaScript syntax checks and `git diff --check` pass.

Actual saved **367-player** response replay against candidate projection: **0.0007054 s** conversion, all raw quantities and input payload unchanged, zero overflows, expected version. Process peak **157372 KiB**, including Python/test-fixture imports; this is not a full-refresh or hosted memory measurement. Existing historical production replay: Superflex **63.216 s / 66368 KiB**, 1QB **54.134 s / cumulative 72080 KiB**, exact corrected-archive parity for Superflex.

Required before merge: inspect stable diff, exact-head CI and Stable full suite, and verify no raw/persistence/source rule changes. Required after deployment: exact main/deploy SHA, startup/health, current restored publication/coverage, new asset versions and representative served index consistency. No refresh is required for displaying saved raw values on the new coordinate. Do not claim the full refresh is now fast or extrapolate mapping-only measurements to refresh capacity.

## Release state

Implementation/focused validation complete; review/CI/Stable and hosted deployment verification pending. Exact PR/head/check/deploy receipts will be appended after they exist.

Pre-merge review found and corrected one compatibility edge: an old index-only surface must retain its complete original coordinate, rather than receive new magnitude metadata while one horizon still carries an old rank score. Added a regression; all 166 focused tests pass on the corrected candidate. PR #524 is the deployment candidate. No raw-model, source-policy or transport changes found in the remaining diff.

Final review correction: player-card Career-owned 3-Year overrides require a completed Career record, not just a retained contract; failed records cannot promote stale evidence. Added completed/failed regression. The supported 3-Year lens no longer rebuilds a Market distribution merely to compute its independent linear index. Supersede all earlier candidate-head checks with the ensuing exact stable head.

Final consumer audit: direct league/discovery rows also expose overflow, and the legacy discovery methods panel now describes separate references and percentile comparisons. Added a real discovery-builder overflow regression. Final focused total 168 passes. Local Chromium 390x844 rendering of three saved player rows and both overflow flags passes. Direct hosted Chromium access is blocked by the environment proxy (ERR_TUNNEL_CONNECTION_FAILED); Render Markdown and HTML documentation URLs also return proxy 403, so deployment verification uses connected Render tools and their exact service/deploy/runtime evidence. No platform settings are changed based on unavailable documentation.

CI on superseded head e7cac488 passed numeric frozen 335 parity, RSS/browser resource and source/cohort checks, but failed four isolated lifecycle cases: new dependencies absent from AST-extracted function namespaces and a minimal context without league rules. Corrected the synthetic harness to supply real presentation imports and made the Career endpoint preserve the existing unsupported-format fallback for absent rules. Expanded local selection to the entire CI lifecycle group plus display/API regressions: **229 passed**, one existing warning, **6.92 s**. Require fresh exact-head CI/Stable on the correction; superseded runs do not count.

Related authority-migration static check updated to expect independent versioned references instead of the obsolete shared-ruler sentence. This is the intended display-policy change, not a weakened raw-authority assertion; the raw Market/Shapley separation assertions remain.

Automated pre-merge reviews identified two genuine consumer regressions: the Intrinsic overflow marker had also been added to the Broad Market roster renderer, and Analytics still filtered on the removed index-gap value. Removed Market contamination; migrated Analytics and the remaining League detail gap to percentile differences. A Node regression executes the actual roster and Analytics scripts, verifies Market 6000 versus Intrinsic 10000+, retains comparable rows with null index gaps, excludes missing ranks and sorts/displays rank disagreement correctly. No browser consumer of value_index_gap/index_gap remains. Updated lazy asset hashes and relevant contract assertions. **261 focused/lifecycle/consumer tests passed**, one existing warning, **7.29 s**. The new consumer tests are included in CI. Require fresh exact-head CI/Stable and review before merge; prior heads are superseded.


## Verified release receipt

PR [#524](https://github.com/jderhagopian-stack/fsffl-next/pull/524) merged as **53712984d4a346f587f094877056110138aef02a** from exact tested head **5319d87ba94087b1fe4467188e970b9ce2802e44**. Tested and merged Git trees both **9616c67af286b5c4f0310e57599a1d0acf596dba**; zero diff. Final automated code review completed clean at **2026-11-08 18:27:53.609110 UTC**, no findings/unresolved findings for that exact head; both prior genuine findings were corrected and resolved. CI [42509863528](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42509863528) succeeds. Stable [42509925259](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42509925259), job **128820549241**, passes **2699 / 5 skipped / one existing pandas warning, 638.91 s**; before/after PR-head verification succeeds. Final expanded local selection **261 passed / one existing warning / 7.29 s**. Superseded-head runs are not acceptance evidence. Branch-policy enforcement was not independently inspected; exact-head checks were enforced procedurally.

Render deploy **dep-dboc345g1s2s73ep3f3g**, service `srv-dae6k7vqj5pc73af7bt0`, workspace `tea-dae6if9t0dsc73918us0`, verified exact merge commit **53712984d4a346f587f094877056110138aef02a**. Created **18:38:09.018141 UTC**, live **18:39:56.050484 UTC**, November 8. Service remains one **0.5 CPU / 512 MiB** Python web instance, auto-deploy off, no infrastructure/source/provider/migration changes. Prior live deploy `dep-dbo7u1psrm7s73b74et0` is the rollback identity; no rollback was needed.

At **18:40:13.616 UTC**, startup restores State **f0aebd5971731782c6c56257d3d42b18d072bd4bdab9282e349577a137cfb28c**, with Forecast/Simulation/Value complete and product/Intrinsic **full**. Canonical Career artifact read hits (**3416013 JSON bytes**); no refitting or new intelligence refresh was started. Resource readiness: RSS **350273536 B (334.05 MiB)**, process high-water **381513728 B (363.84 MiB)**, active **None**, waiting **0**. This is startup evidence only; it does not close the existing slow-refresh/page-use memory gate. Render's root GET 401 is expected private-beta Basic auth; its HEAD root 405 is not a 503 or resource failure.

Exact deploy, process startup and restored readiness are verified through connected Render tools. Direct hosted HTTP/Chromium access is denied by this environment's proxy, and no beta credentials are configured here, so authenticated rendered-screen acceptance is not claimed. Local production-JavaScript/mobile-browser and current 367-player raw replay checks cover the changed display behavior. User should reload the beta page; no intelligence refresh is needed to consume the new projection of saved raw values. Physical page confirmation remains distinct from successful deployment.

**DEPLOYMENT COMPLETE — Intrinsic magnitude display v1.** Refresh performance, larger league-format reference coverage and broader rollout acceptance remain separate work. This post-deploy documentation-only receipt does not require another full suite under AGENTS.md; no executable behavior or acceptance gate is changed.
