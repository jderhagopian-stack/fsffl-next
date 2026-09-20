# FSFFL NEXT — PR #117 Forecast resilience reconciliation

Date: 2026-09-16

Scope: implementation/promotion evidence only. This document does not alter Forecast, I1, Shapley, Value, Decision, Search, Simulation, or presentation authority.

## Management correction

The private-beta Intrinsic live diagnostic had been calling `default_live_forecast_loader` directly. That bypassed the persistence-backed resilience composition established by merged PR #117 and used by the hosted persistent application.

The authoritative hosted behavior remains:

`live >=2-source full-season Forecast -> preserve immutable preseason baseline -> if later live acquisition fails, reuse preserved >=2-source baseline -> reapply current league scoring/uncertainty -> fail closed only if neither valid live evidence nor a valid preserved baseline exists`

The two-independent-source requirement is unchanged.

## Current production persistence verification

A read-only query of the current FSFFL NEXT production persistence store found an active 2026 `preseason_forecast_baseline` record for the currently connected private-beta league-season.

Verified properties:

- artifact kind: `preseason_forecast_baseline`;
- scope kind: `league_season`;
- model version: `next2-preseason-baseline-v1`;
- invalidated: no;
- preserved source count: 2;
- preserved source IDs: `fftoday`, `razzball`;
- raw preserved ensemble observations: 1,675;
- preserved horizon set: `season` only;
- baseline evaluation/capture timestamp: 2026-09-10T21:36:41.346326Z.

A schema-oriented read-only audit over all 1,675 raw observations found zero blank player IDs, zero invalid positions, zero non-season horizons, zero unsupported metrics, zero blank source/model-version fields, zero negative standard deviations, zero invalid forecast periods, and zero provenance-effective timestamps after observation `as_of`.

The same production persistence store also contains later `current_forecast_evidence` records for the current 2026 league state with `evidence_basis=live_full_season`, successful sources `fftoday` + `razzball`, demonstrating that the hosted runtime has been reading/writing the active persistence integration after the baseline was captured.

## Hosted composition verification

The deployed hosted app composes `persistence_store_from_env()` with `make_resilient_forecast_loader(_persistence_store)` and passes that loader into `create_app(...)`. Therefore the hosted Forecast path is not the raw `default_live_forecast_loader` path used by the earlier Intrinsic diagnostic.

The currently deployed Render service remains on main commit `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`; no implementation-branch code has been deployed as part of this reconciliation.

## Diagnostic defect and correction

Concrete defect: `scripts/run_private_beta_intrinsic_diagnostics.py` called `default_live_forecast_loader` directly. A momentary live-provider shortfall therefore caused the management diagnostic to fail even though a valid preserved baseline exists in production persistence.

Correction in this PR:

- `scripts/run_private_beta_intrinsic_resilient_diagnostics.py` wraps the existing coverage/sanity/latency board with the same `make_resilient_forecast_loader` authority used by the hosted app;
- when a production persistence connection and diagnostic league ID are supplied, it retrieves and validates the preserved baseline before running the Intrinsic diagnostic;
- it records the governed Forecast `evidence_basis` separately from raw provider health;
- if the runner does not have production persistence credentials, it emits `PROVIDER_HEALTH_ONLY` rather than declaring Forecast unavailable;
- the workflow now reruns the PR #117 resilience tests, including preserved-baseline fallback and fail-closed-without-baseline behavior.

## Current provider health — operational concern only

The latest raw-provider probe observed only Razzball succeeding at that moment. FFToday returned HTTP 403, CBS did not return a valid full-season projection page, and NFL Fantasy did not return projection content.

That remains an operational provider-reliability concern. It is **not**, by itself, a governed Forecast-availability failure while the valid preserved >=2-source 2026 preseason baseline remains retrievable and usable through PR #117's resilience path.

## Disposition

The prior diagnostic failure is classified as a diagnostic-composition defect, not a reason to redesign Forecast or weaken the >=2-source rule. The implementation should proceed using the persistence-backed resilient Forecast authority for final Intrinsic sanity/coverage/latency validation.
