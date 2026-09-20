# FSFFL NEXT — PR #147 Merge and Development Continuation Checkpoint

Date: 2026-09-20

## Live pre-merge recovery

- PR #147 head: `34470dce369df2c9d5454ebbd481317c5ab76d12`
- Pre-merge main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR state before merge: open, mergeable, not draft, unmerged
- Compare state: head ahead by 162 commits, behind by 0
- Final required workflow runs on PR head:
  - CI — success
  - Private-beta Intrinsic live diagnostics — success
  - Build private-beta I1 activation artifacts — success
- PR diff contained implementation code, tests, workflows, and implementation/provenance/evidence artifacts. No `artifacts/research` experimental research branch content was present.

## Merge result

- Merge method: normal GitHub merge
- Final PR head: `34470dce369df2c9d5454ebbd481317c5ab76d12`
- Merge commit: `32d24eadcd90de60db5f68ff24d8bfa6dc3c7f0d`
- Post-merge main: `32d24eadcd90de60db5f68ff24d8bfa6dc3c7f0d`
- PR #147 is now merged/closed.
- No manual production deployment was performed.

## Current Forecast authority after merge

The merged P0/D0-D1 Forecast is now repository authority for the current production version. Its exact version/provenance remains preserved. The final route authority contains exactly the already-validated route changes:
- developmental QB Y3: D0 -> D1
- established RB Y3: D0 -> D1

This authority is versioned, not treated as immutable architecture.

## Known localized Forecast limitation

The separate baseline-attribution diagnostic found a material conditional-production pooling limitation localized to developmental RB Y3. Implementation must not repair this with a mean boost, percentile rule, elite adjustment, collapse haircut, or ad hoc uncertainty patch. Foundational Forecast architecture research remains owned by the separate research chat.

## Research / implementation separation

Implementation proceeds around the current merged Forecast authority. Intermediate research results must not be cherry-picked. A future Forecast architecture change requires a durable management-approved research conclusion, a separately validated Forecast version, and a controlled migration.

## Stable model-agnostic Forecast boundary requirements

Downstream consumers must receive governed forecast outputs through a versioned interface that can carry:
- player and horizon identity;
- central expectation;
- the uncertainty/distribution representation available in that Forecast version;
- scoring coordinate;
- provenance/source coordinate;
- model/version identity.

New downstream architecture must not permanently assume that every Forecast version is P0/D1 or that uncertainty is always six discrete states with one point mean per state.

## Recovered roadmap state

Repository evidence shows Phase 3 is active rather than a return to Phase 1/2 implementation:
- runtime persistence and single-owner restore orchestration are already implemented;
- Phase 3 reconciliation explicitly records Home, Franchise, League, Market/Opportunities, Trade Center, and Behavioral surfaces as mostly complete, with latency/product-learning/evidence gaps remaining;
- progressive Market/Trade delivery and exact Simulation reuse/coalescing are already merged before PR #147.

Underlying derived-artifact persistence is already model-versioned: artifact identity includes `model_version`, and PostgreSQL coexistence keys include `(artifact_kind, scope_kind, scope_id, input_fingerprint, model_version)`. The persistence database therefore does not silently overwrite prior Forecast-version semantics.

The remaining migration-readiness gap is at the product/value boundary: `PrivateBetaShapleyContractLoader` still imports P0/D1 implementation functions and materialization types directly. That creates an avoidable coupling between downstream Value product code and the current Forecast internals.

## Exact next implementation item selected

**Implement a model-agnostic future Forecast contract and make the P0/D0-D1 producer adapt into it before downstream Shapley/Intrinsic consumption, with exact parity to the merged behavior.**

Scope:
1. Add a versioned Forecast-owned contract for future player/horizon outputs.
2. Contract must represent central expectation, scoring coordinate, model identity, provenance, and optional uncertainty/scenario support without naming D0/D1.
3. Add a P0 adapter that materializes the current authority into that contract.
4. Refactor the product Shapley loader to consume the contract boundary rather than importing P0 materialization internals directly.
5. Preserve exact current P0 probabilities/means, scoring translation, Shapley legality, and 0.85 discount.
6. Add parity/fail-closed tests.
7. Do not alter Forecast coefficients/routes or research architecture.

Implementation branch: `implementation/forecast-contract-migration-readiness`.
