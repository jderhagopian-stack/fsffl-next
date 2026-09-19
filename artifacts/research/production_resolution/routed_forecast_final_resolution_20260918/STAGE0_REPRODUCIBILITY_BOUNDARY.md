# Routed Forecast Final Resolution - Stage 0 reproducibility boundary

Date: 2026-09-18
Status: FINAL - OUTCOME C
Authority: research only

## Recovery
The live research branch was recovered exactly at Stage C Outcome B commit `11399fb1fbfb89d99e38250d31b72dc2dbbc78fa`. No Routed Forecast Final Resolution work existed after that commit. The recovery note was then persisted at `da88ba09f92eb9cd35db201e88a88be61286ee1c`.

Protected refs re-fetched before this Stage 0 work:
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

## What Stage 0 recovered
Durable repository checkpoints establish the governed candidate history:
- B2a definition and aggregate pre-holdout behavior are documented in `B2_BOUNDED_REFINEMENT_CHECKPOINT_2026-09-18.md`.
- The later rejection audit reopened B2a/B2b, B3, R1/R2 and H2 under the corrected role-loss policy and ultimately identified B2a as the provisional fallback.
- The hybrid provenance audit records an aligned `recombination_prediction_rows.csv` with 41,344 rows and SHA-256 `dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b`, containing Candidate B, FrozenForecast, R1 and R2 on identical rows.
- The hybrid final checkpoint records H2's documented family and aggregate mid/validation results.

## Exact failure
The required Stage 0 parity coordinate cannot be reconstructed from the durable branch without a new refit/reconstruction choice.

1. The 41,344-row `recombination_prediction_rows.csv` referenced by the hybrid audit is not tracked on the live research branch. Comparing B3 result commit `86043a6610bc4dce79a159502f24cb70a762fabc` to hybrid result commit `8839cfad99ec4850782d5bc720784d0672012472` shows exactly two commits and only two added files: `STAGE0_PROVENANCE_AUDIT.md` and `FINAL_CHECKPOINT.md`. No row-level CSV or machine-readable candidate prediction artifact was committed.

2. B2a has a durable formula/summary checkpoint but no durable aligned row-level prediction checkpoint or fitted fold parameters on the identical R1/R2/H2 evaluation rows.

3. H2 has a durable family description and aggregate results but no durable aligned row-level predictions or complete fitted fold-specific restoration parameters sufficient to recreate its exact row outputs without refitting.

4. The Routed Forecast directive requires candidate-by-position/career-state scorecards, chronological cell stability, and a position-only versus position x career-state complexity challenger on identical rows. Those calculations cannot be legally produced from aggregate summaries alone.

## Why no workaround is allowed
Refitting B2a/H2, substituting another historical coordinate, inferring row values from aggregate metrics, or manufacturing new career-state buckets would violate the directive's Stage 0 parity rule and no-new-methodological-choice restriction. The current Python runtime also cannot fetch the public GitHub repository directly; repository access is through the connected GitHub tools, which expose the committed checkpoints but not the missing prior local row files.

## Outcome
**C - UNRESOLVED REPRODUCIBILITY BOUNDARY.**

Smallest missing dependency:
> A durable, exact, aligned pre-holdout row-level candidate coordinate for B2a, R1, R2 and H2 (or the exact frozen fitted artifacts/parameters and source rows sufficient to reproduce that coordinate without refitting/model-selection choices).

Without it, routing selection cannot begin. No career-state definitions, routing cells, routing analysis, complexity challenger, holdout routing evaluation, or current-board run was performed.

## Protections honored
- no main modification;
- no PR #147 modification;
- no merge/deploy/promotion;
- no current-player or named-player tuning;
- no holdout used for route discovery;
- no Intrinsic/Shapley, Constitution, C=0.25, or production-authority change;
- no new model family or H4;
- zero model refits/reruns in this continuation.

STOP for management review.
