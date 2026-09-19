# Forecast Hybrid / Ensemble — Final Resolution Checkpoint

## Result
No H candidate advances. No current-board run authorized.

## Stage 0
PASS. Persisted recombination prediction evidence was verified directly.
- recombination_prediction_rows.csv: 41,344 rows
- SHA-256: dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b
- prior R1/R2/B summary metrics reproduce from prediction rows to floating-point precision.
- prior run performed fold-specific model fitting and newly generated CSV/PDF outputs.
- prior wall-clock runtime was not durably recoverable.

## Anchors
- Candidate B: conservative anchor.
- R2: richer persisted anchor (R1 + already-approved two-prior evidence); not selected using 2021-2022.

## Candidates
H1 = B + w(R2-B), global convex w by horizon.
H2 = B + bounded continuous restoration weight * (R2-B), with restoration weight using only ordered-state concentration and normalized B/R2 disagreement. Ridge alpha=100; shrinkage/no intercept; fit chronologically.
H3 not separately manufactured because bounded residual restoration with the same continuous confidence evidence is mathematically the H2 family.

## Chronological discipline
Persisted anchor outputs do not provide a leakage-free hybrid-training block before the early fold. Therefore:
- mid is evaluated after fitting hybrid parameters on early outcomes;
- validation is evaluated after fitting on early+mid outcomes;
- 2021-2022 was not used for selection because no candidate froze.
No current-player outputs were inspected.

## Key results
H1 chooses w=1.0 in every evaluable horizon/fold, reducing exactly to R2.

H2:
- mid Y2 overall MAE 42.70 vs B 43.91; top10 55.24 vs 58.90; role-loss 46.65 vs 32.66
- mid Y3 overall 45.80 vs 46.32; top10 59.09 vs 59.25; role-loss 57.44 vs 40.76
- validation Y2 overall 39.42 vs 39.53; top10 54.70 vs 58.95; role-loss 46.81 vs 32.78
- validation Y3 overall 42.01 vs 40.68; top10 60.19 vs 62.86; role-loss 47.06 vs 30.47

Confidence bands are partially informative: the highest-restoration quartile is consistently where R2 beats B on average, but lower/middle bands are not monotonically reliable.

## Advance rule
FAIL. H2 preserves upper-tail gains but does not preserve most of Candidate B's role-loss safety and worsens validation Y3 overall stability. H1 is R2 and inherits R2's role-loss failure.

## Stop
No H4/new feature family/external-data/coefficient search. No implementation/promotion/merge/deploy/main/PR147/Shapley/Intrinsic change. Management must choose the governed next product path.
