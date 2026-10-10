# Universal sparse-player Forecast prior — implementation checkpoint

Date: 2026-10-10  
Base: current main `37fd2cd06f25eb99716191dcead6a309e268901c`  
Branch: `feature/universal-forecast-sparse-prior-20261010`

## Implemented in this tranche

- Added an in-memory, reusable historical position × age × experience empirical prior with broad position-only backoff. It does not fit per candidate or per league.
- Enforced canonical subject IDs, supported position, the standard/non-PPR training coordinate, completed target seasons, exact `as_of` cutoffs, minimum sample support and duplicate-history rejection. Missing seasons are not synthesized as zero by the production prior.
- Added rolling-origin split-conformal calibration of central 50% and 80% forecast intervals. Calibration is limited to earlier target seasons and available observations, with position/evidence-tier pooling and a position fallback.
- Added an adapter to the canonical Forecast observation only after compatible rolling calibration passes and source timestamps do not exceed the candidate `as_of`.
- Added focused tests and a reproducible rolling validation script. Validation labels were derived from the preserved accepted historical panel and explicit rookie-season evidence; the source hashes are in `ROLLING_CALIBRATION_RESULT.json`.

## Validation

The 15-season rolling run contains 18,905 accepted outcomes, 36,232 prior-fold calibration cases and 34,930 calibrated holdout forecasts. Across QB/RB/WR/TE and both known age/experience and sparse position-only evidence tiers, the calibrated central 80% empirical interval coverage was approximately 0.90. The central 50% intervals remain conservative for discrete fantasy scores; this tranche does not claim point-quantile calibration. Repeated player-seasons mean Wilson intervals are descriptive, not independent-sample guarantees.

Focused regression command:

```text
.venv/bin/python -m pytest -q tests/test_sparse_player_prior.py tests/test_p0_forecast_runtime.py tests/test_private_beta_shapley_runtime.py tests/test_future_state_primitive.py
49 passed in 2.26s
```

Bounded synthetic resource measurement (one process, 20,000 historical outcomes, 1,000 candidate lookups): 30.2 ms to initialize shared prior, 24.9 ms for the batch (0.0249 ms/candidate), 41,596 KiB peak RSS. All 1,000 candidates had a supported position-pool estimate in this fixture. This measures prior generation only, not full Forecast publication or P0/Career runtime.

## Explicit scope boundary

This tranche is a governed Forecast fallback primitive and validation artifact. It does **not** yet create production candidate evidence from current State/provider identity, translate to arbitrary league scoring, feed dynamic subjects into P0, or materialize Career Y4–Y7. The frozen P0 source table remains 335 and its outputs are untouched. The next implementation slice must add the canonical identity/evidence adapter, derive or validate league-scoring-compatible Year-1 inputs under existing scoring authority, supply the accepted P0 model's required dynamic features without fabricating them, then connect results to Career. It must retain explicit player-level failures, exact-State accounting, #370 fail-closed completeness and #445 job bounds. No deployment or merge was performed.
