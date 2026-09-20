# FSFFL NEXT - Selected Forecast / League-Scoring Reconciliation

Date: 2026-09-19  
Outcome: **STOP AT DURABILITY GATE**

## Executive result

PR #147 still uses its embedded legacy I1 artifacts to produce Years 2-3. The preserved preseason Year-1 architecture is correctly league-specific and separately reproduces the frozen standard/non-PPR coordinate from the same immutable raw-stat observations.

The selected routed Forecast cannot be wired safely from durable governed evidence. The exact 670-row routed + M1a + two-prior board was recovered and hash-verified, but it was materialized from the September 18 live Year-1 universe, not the September 10 preserved preseason raw-stat coordinate. The fitted routed estimator/vectorizer state needed to reproduce Years 2-3 from the preseason standard coordinate is not durable. Reusing the old board would mix source coordinates; rebuilding it would require a prohibited refit.

No runtime correction was made.

## Live repository state at execution start

- Authoritative research-evidence branch: `research/future-state-resolution-phase34-resume` at `3bbdf8ce75eff05e26c154b2c38c70d425a4a5d2`.
- PR #147 implementation branch: `implementation/forecast-intrinsic-i1-shapley` at `1fd76ac589b3d801e85a7f8963b27018f75916e6`.
- Protected `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.

These refs were fetched live before inspection. They are recorded as starting evidence and must be re-fetched before any later exact-SHA claim.

## Authority recovered

The management-selected Forecast authority is:

- Year 1: preserved immutable preseason raw-stat ensemble.
- Years 2-3: selected frozen position-routed Forecast plus frozen M1a plus frozen two-prior-season consistency.
- Routing: QB = A2+C+D; RB/WR/TE = A2+D.
- The older PR #147 embedded I1 future-year path is not the selected authority.

## PR #147 trace

`src/fsffl/product/private_beta_shapley_runtime.py` loads `frozen_i1_h12.json` and `frozen_i1_h3.json` from the private-beta activation bundle. It wraps them with `LeagueScoringNormalizedI1Predictor` and passes them to `compose_live_intrinsic_calendar` as the Year-2 and Year-3 producers.

Therefore the current PR implementation still assigns Years 2-3 to legacy I1. The selected routed Forecast is not wired.

## Year-1 scoring architecture

This part passes.

- Production baseline record: 145.
- Frozen raw observations: 1,675.
- Raw-array SHA-256: `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`.
- League-specific 0.5-PPR board: 335 players, SHA-256 `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`.
- Standard/non-PPR board: 335 players, SHA-256 `dfe817909dc42782ef4f1249692a9ad9139b5fa25311549ae741970c4ef9efe9`.
- Identity/population parity between the two Year-1 coordinates: PASS.

`build_runtime_from_preseason_baseline` derives league-facing fantasy points directly from `baseline.raw_ensemble` under the connected league rules. `build_future_i1_position_scoring_multipliers` independently derives the standard/non-PPR Year-1 coordinate from those same raw observations. Year 1 is not estimated from a scoring multiplier.

## Selected-candidate evidence recovered

- Replacement identity/materialization coordinate: 335 rows; coordinate SHA-256 `95fd6565a908b044ca234898cc801749abb2b6aa62a84c2d3c917445d369cda1`; row-material SHA-256 `1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`.
- September 18 live Year-1 universe: 335 rows; canonical SHA-256 `5dee244f794cd504a84d1575ed1d5fca5b467e604f682018a850363f7fbd5c0f`.
- Selected routed + M1a + two-prior Y2/Y3 board: 670 rows / 335 players; canonical row SHA-256 `723f14076f5d0b8801cfff731c8a533494a9d8bbf98531bf25e2d45a16ce1fe8`.
- Eight-sentinel parity against the replacement-coordinate authority: maximum absolute difference 0.0.

This proves the prior board itself is authentic. It does not prove that the selected Forecast can be recalculated from the preserved preseason coordinate.

## Why the old 670-row board cannot be reused

The old board was generated from a different Year-1 source coordinate and a slightly different player population.

After normalizing the two ID prefixes, 334 players overlap. The one-player difference is:

| Coordinate | Player | Position |
|---|---|---|
| Preserved preseason | Malik Davis | RB |
| September 18 live | Roman Wilson | WR |

The position counts also differ:

| Coordinate | QB | RB | WR | TE |
|---|---:|---:|---:|---:|
| Preserved preseason | 61 | 89 | 121 | 64 |
| September 18 live | 61 | 88 | 122 | 64 |

The selected candidate uses the Year-1 standard coordinate as model input for current production/state magnitude. Consequently, substituting the old board would not be a scoring-only translation; it would silently preserve forecasts produced from different source observations and omit the preseason-only player.

## Exact missing reproducibility dependency

Proceeding requires all of the following, without fitting or making a new methodological choice:

1. The fitted current-cutoff routed probability estimators for QB A2+C+D and RB/WR/TE A2+D, including the exact `DictVectorizer` feature state and all persistence/ordered-state logistic coefficients and intercepts.
2. A deployment-grade serialization of the frozen M1a and two-prior conditional-production transforms and coefficients attached to that routed estimator.
3. A governed replacement identity/history coordinate aligned to the preserved preseason population, including Malik Davis rather than Roman Wilson.
4. Either a row-complete selected-candidate Y2/Y3 board produced from the preserved preseason standard/non-PPR coordinate, or sufficient frozen estimator state to reproduce it without `.fit()`.

The branch retains historical prediction checkpoints, M1a/two-prior summaries, the replacement coordinate, the old current board, and parity evidence. It does not retain the fitted current-cutoff routed estimator package needed for a new source-coordinate materialization.

## Regression evidence

Focused command:

`uv run pytest -q tests/test_preseason_forecast_baseline.py tests/test_private_beta_shapley_runtime.py tests/test_pr147_sanity_regressions.py`

Result: **27 passed**.

This confirms the current PR's preserved Year-1 behavior and legacy I1 wiring; it does not authorize legacy I1 as the selected Years 2-3 authority.

## Stop boundary

STOP for management review.

No model fit/refit, tuning, source substitution, runtime source change, merge, deploy, or production-authority change occurred. Do not use the September 18 live-coordinate board as a preseason-coordinate board, reconstruct missing coefficients, or fall back to legacy I1.
