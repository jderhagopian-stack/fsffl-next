# Unified Intrinsic magnitude calibration — shadow gate (2026-10-17)

Status: **RESEARCH / NO PRODUCTION PROMOTION**. This branch adds an isolated deterministic experiment only.

## Management direction

3-Year and Career Intrinsic must use a coherent **raw-magnitude-first** display philosophy. Percentile ranks are supplementary descriptive metadata, not the intrinsic 0–10,000 index. Do not change accepted 3-Year or Career Shapley contributions, Forecast, projection acquisition, leagues, lineups, market, position/depth, or roster display.

## Current discrepancy

- 3-Year user-facing display: percentile rank mapped via market-derived nonlinear quantile coordinate (`value_lens_evidence.py`, `value_presentation.py`, `league_value_lenses.py`).
- Career user-facing display: empirical midrank directly scaled to 0–10,000 (`career_presentation.py`).
- Both destroy important information about raw contribution gaps and depend on reference population membership.
- Preserve production scores unchanged until approval.

## Verified single-league observational evidence (not a frozen historical training set)

Retained Supabase `fsffl.derived_artifact`: reference Career ID 12005 and 3-Year contract ID 11748, matched 335/335 player IDs. Data are saved at **different timestamps**, so do not misrepresent as identical current-State output.

| Raw | 3-Year | Career |
|--|--:|--:|
| Median | 110.8 | 212.7 |
| P90 | 400.7 | 731.1 |
| P95 | 479.1 | 1138.6 |
| P99 | 568.4 | 1743.6 |
| Maximum | 724.1 | 2062.3 |

Current Career midrank produces ~67 of 335 scores >=8,000 by construction. Diagnostics (NOT proposed anchors): fixed 750 raw 3-Year units and 2000 raw Career units yield square-root median scores 3,843 and 3,261; 17 and 13 scores >=8,000. Linear yields median 1,477 and 1,064; 2 and 6 scores >=8,000. Neither provisional anchor is validated for production.

The square-root Career diagnostic gave 13 QBs and **zero** RB/WR/TE above 8,000. Audit raw superflex/terminal valuation economics; do not artificially equalize positional distributions.

## Shadow code

`src/fsffl/product/intrinsic_magnitude_shadow.py`: immutable `MagnitudeRuler`, explicitly supplied anchor and reference-version, horizon identification, formula, fingerprint, missing handling. `shadow_compare` only returns diagnostic scores. Import graph intentionally has no production wiring. Test module: `tests/test_intrinsic_magnitude_shadow.py`.

## Further required validation

1. Obtain same-State raw 3-Year and Career values with matching cutoff and full player coverage, including unsupported players.
2. Obtain commercially eligible historical multi-season reference values, pre-register anchors and curvature on development years, reserve later seasons as untouched confirmation.
3. Head-to-head compare raw-gap preservation and stable magnitudes against existing 3-Year nonlinear market-shaped rank, Career percentile, fixed linear, concave power, and bounded piecewise alternatives. Expose percentile separately.
4. Audit cases by QB/RB/WR/TE, age and role, candidate entrants, rookies, injury, and tail (especially QB Y8+).
5. Test reference population expansion stability, multi-year score revision sensitivity, 8k/9k concentrations, cross-league scaling, score saturation and economically meaningful gap behavior.
6. Distinguish `raw 3-Year` discounted Shapley from `raw Career` undiscounted cumulative Shapley and keep display index out of arithmetic.
7. Ensure missing values stay missing; never fabricate zero estimates.
8. Production adoption of **both** horizon displays as one release decision only after frozen reference, historical holdout, full CI, and explicit Management approval.

The work here does **not** assert that any tested mapping is economically calibrated or ready for users.
