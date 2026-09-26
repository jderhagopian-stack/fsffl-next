# FSFFL NEXT — Comprehensive Y4-Y8 Intrinsic Research Management Handoff

Date: 2026-09-26  
State: **MANAGEMENT GATE — COMPREHENSIVE LONG-HORIZON ARCHITECTURE**  
Authority: Research only. No production implementation is authorized.

## Bottom line

The comprehensive study gave richer point-in-time football evidence, alternative target decompositions, flexible model families, shared/continuous architectures, specialist position × horizon routes, and hierarchical blending a fair nested-chronological test.

The best development candidate was **not** the old simple model. It was a 75% cell-specialist / 25% shared continuous-horizon blend using richer football information.

That richer architecture **failed the untouched final holdout under the rules frozen before the holdout was opened**.

Therefore the final supported Research architecture is the simpler contract:

**position × horizon specialist fits using `forecast10 + two_part_ridge` for every QB/RB/WR/TE cell at Y4-Y8.**

There is:
- no promoted model-family breakpoint;
- no promoted position/horizon model router;
- no evidence that H5 is a statistical regime boundary;
- no pooled/shared model promoted over the cell specialist;
- no exact terminal/career architecture promoted;
- no production H3 change.

## Why the richer candidate was rejected

Across 8,579 untouched holdout rows, the richer candidate:
- improved RMSE from **44.185 to 43.603**;
- improved Spearman from **0.4906 to 0.4942**;
- improved top-decile tail RMSE from **130.48 to 113.40**;
- but worsened MAE from **18.756 to 19.797**.

The predeclared gate also prohibited a catastrophic position × horizon cell. The richer candidate failed at **QB Y8**:
- rich RMSE **100.44**;
- fallback RMSE **77.84**;
- ratio **1.290×**;
- frozen limit **1.15×**.

Research did not retune, remove, or reroute that cell after seeing the final outcomes. The fallback was automatically preserved.

## What the richer feature search taught us

The historical inventory found defensible PIT evidence far beyond the inherited 10 features:
- draft/pedigree and rookie timing;
- height/weight;
- games/availability proxies;
- passing/rushing/receiving usage and efficiency;
- target/air-yard shares, EPA/CPOE and related role measures;
- team continuity;
- residual, trajectory, innovation and volatility states.

Development evidence showed real localized signal, especially in QB cells. The selected development route used richer football features in 6/20 cells and full-rich features in 5/20.

But no standalone richer feature family established broad stable superiority, and the final routed/blended architecture failed confirmation. This is a negative selection result, not evidence that the features are irrelevant.

## Final position × horizon conclusion

For **all 20** cells (QB/RB/WR/TE × Y4/Y5/Y6/Y7/Y8), the effective Research candidate is:

`specialist | forecast10 | two_part_ridge`

The same feature/model contract is used, but each position × horizon cell is fit separately. This is not one pooled universal regression.

Machine-readable cell evidence:
`FINAL_POSITION_HORIZON_MATRIX.csv`.

## Uncertainty

Uncertainty is derived only from development OOF residuals, before the final holdout:
- absolute-residual conformal bands;
- position × horizon calibration;
- monotone horizon floor.

Untouched final-holdout coverage:
- nominal 80% band: **87.66%** actual;
- nominal 90% band: **94.32%** actual.

The bands are conservative overall. Cross-horizon error covariance is **not** validated, so Research does not authorize a precise cumulative H4-H8 variance by mechanically summing annual uncertainty.

Long-run annual precision remains weak relative to expected production, particularly for RB/TE and for QB magnitude at deep horizons.

## Current 335-player shadows

Current named-player shadows were generated only after the historical architecture was frozen.

- 335/335 players matched the persisted production H3 reference.
- Research H3 vs production H3 rank Spearman: **0.99654**.
- 293/335 players had exact 2025 prior-production rows; 42 use the frozen model's ordinary missing-value treatment.
- No named-player tuning occurred.

Rank movement from H3:
- H4 median **4**, p90 **12**;
- H5 median **7**, p90 **19**;
- H6 median **10**, p90 **24**;
- H7 median **11**, p90 **27**;
- H8 median **12**, p90 **29**.

H3 vs H8 rank Spearman remains **0.96788**. The divergence is gradual rather than a breakpoint.

Top-50 composition changes from H3 **52% QB / 32% RB / 16% WR / 0% TE** to H8 **50% / 20% / 30% / 0%**.

Age effects are also gradual rather than manually imposed. For example:
- young QBs average +22.5 ranks by H5 and +35.2 by H8;
- aging RBs average -12.6 / -20.8;
- aging WRs average -9.4 / -16.9;
- aging TEs average -7.0 / -13.3.

## Data gaps

Research did not invent evidence for:
- historical contract guarantees/years remaining;
- historical injury-event/designation detail;
- governed point-in-time depth-chart/starter labels;
- complete combine/athletic testing.

Those remain explicit future data opportunities, not assumed-zero predictors.

## Recommended Management interpretation

1. Preserve production H3 unchanged.
2. Treat `forecast10 + two_part_ridge` as the best-supported **Research** annual architecture for Y4-Y8 today.
3. Do not promote the richer development router/hierarchical blend.
4. Do not describe H5 as an empirically discovered breakpoint. H5 may still be a useful product-selected decision lens.
5. If Management wants Y4+ production next, require a separate promotion/implementation gate with current-data availability, uncertainty presentation, cumulative covariance/scenario semantics, H3 non-regression and downstream containment.
6. Treat the richer features/models as a retained challenger set for future evidence, not as discarded work.
7. A terminal/career-state product remains a separate research problem; this study did not validate an exact terminal coordinate.

## Management decisions required

- whether to accept the simpler post-H3 Research architecture as the basis for a future production challenger;
- which horizon(s), if any, should be product-facing decision lenses;
- whether to authorize a separate terminal/career-state study;
- whether additional PIT data acquisition is justified for the explicit gaps above;
- whether to authorize a Y4+ production-promotion workstream with cumulative uncertainty/scenario validation.

**MANAGEMENT GATE — COMPREHENSIVE LONG-HORIZON ARCHITECTURE**
