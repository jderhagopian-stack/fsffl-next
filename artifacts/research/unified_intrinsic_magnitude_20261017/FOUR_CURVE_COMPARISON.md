# Four-way magnitude calibration comparison — 2026-10-17

**Status:** numerical research, no production ruler approved. The 335 raw 3-Year and Career values derive concurrently from Career checkpoint `12063`: raw 3-Year = Y1 + 0.85*Y2 + 0.7225*Y3; raw Career is the preserved full horizon. Historical anchors **not yet calibrated**; use 750 and 2000 solely as diagnostic constants.

|Candidate|Median 3-Year|Median Career|3-Year >=8000|Career >=8000|
|---|---:|---:|---:|---:|
|linear|1477|1064|2|6|
|power 0.75|2382|1862|6|7|
|sqrt (power 0.50)|3843|3261|17|13|
|piecewise hypothesis (0,0),(.1,.06),(.4,.32),(1,1)|1013|655|1|6|

This refutes the assumption that any concave/piecewise ruler will automatically improve readability. The tested piecewise curve suppresses the middle more than linear. The power 0.75 family is a plausible diagnostic compromise but **not validated** as best.

## Evaluation requirements beyond matching distributions

1. Explicit objective: within each time horizon display score should be a stable, monotone, interpretable function of marginal fantasy-point contribution. Ratios are preserved only by linear; nonlinear coordinates need a published inverse to expose raw magnitude.
2. Use actual 35 player cases and full reference, not simply distribution fit; evaluate pairwise separation for high-value vs marginal players and characterize saturation.
3. Account for 3-Year and Career meaning separately; projections present-season, 3-Year nearer-term, Career remaining career. Never require a higher Career index than 3-Year.
4. Make separate percentile supplemental; do not normalize by rank or by position.
5. Choose anchor and curve using legally usable historical calibration evidence and untouched future holdout, validate across league configurations and roster expansion.
6. Compare against current published presentation using matching-State evidence; same published window alone does not independently prove State identity for saved reference checkpoint.
7. Preserve unsupported/unavailable rows, source provenance, existing raw Shapley models, and no production wiring until joint release approval.

Source: governed read-only `fsffl.derived_artifact` Career checkpoint ID 12063; formulas added in `src/fsffl/product/intrinsic_magnitude_shadow.py`; candidate regression tests in `tests/test_intrinsic_magnitude_curve_comparison.py`.
