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
