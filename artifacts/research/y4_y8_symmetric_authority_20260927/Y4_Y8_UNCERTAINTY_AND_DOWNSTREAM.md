# Y4-Y8 Symmetric Authority — Uncertainty and Downstream Implications

Date: 2026-09-27  
Authority: **Research only / no production change**

## 1. Statistical/model-selection uncertainty

The symmetric audit uses exact common rolling PIT rows:
- 11,940 unique player-origin rows;
- 47,760 policy prediction rows;
- four policies;
- QB/RB/WR/TE × Y4-Y8;
- source-origin × player clustered uncertainty;
- 2,500 bootstrap repetitions per persisted pairwise comparison.

Across the 20 position×horizon cells:
- **2** cells have a best-supported direct universal policy;
- **9** are practical ties / uncertain;
- **5** are multi-objective tradeoffs;
- **4** are Y8 evidence-limited.

Pairwise uncertainty is pervasive even though central differences exist:
- MAE has at least one statistically supported policy difference in **18/20** cells;
- MSE in **14/20**;
- top-tail MSE in **16/20**;
- absolute-bias differences in only **5/20**;
- 80% coverage-gap differences in only **1/20**;
- **no** 90% coverage-gap pair out of 120 pairwise cell comparisons has a clustered interval excluding zero.

Thus the ambiguity is not “the models are identical.” It is mostly **multi-objective**: policies improve different error dimensions, and most cells do not have one policy that beats every peer without a supported loss elsewhere.

## 2. Central policy spread by horizon

The table below is the median across the four positions of the central max-minus-min policy spread, expressed relative to the best central value in each cell. It is a descriptive model-choice envelope, not a confidence interval.

| Horizon | RMSE spread | MAE spread | top-tail RMSE spread |
| --- | ---: | ---: | ---: |
| Y4 | 7.4% | 12.9% | 27.0% |
| Y5 | 4.3% | 7.1% | 20.2% |
| Y6 | 3.9% | 12.2% | 6.9% |
| Y7 | 7.4% | 18.1% | 9.3% |
| Y8 | 7.6% | 38.2% | 9.3% |

Y8's large MAE spread is not evidence for a precise Y8 router: only two qualifying repeated outer origins remain, below the frozen three-origin minimum for exact-cardinal authority.

## 3. Aggregate policy evidence does not justify a global winner

Across all 11,940 persisted rows:

| Policy | RMSE | MAE | Bias | Spearman | top-tail RMSE | 80% cov. | 90% cov. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 45.64 | **19.96** | -5.70 | 0.4942 | 134.77 | 80.77% | 90.44% |
| hard router | 44.03 | 20.91 | +0.44 | 0.4964 | 113.52 | 79.18% | 89.66% |
| soft stack | **43.20** | 20.73 | +0.23 | **0.5067** | **113.34** | 79.35% | 89.70% |
| blanket 75/25 | 43.48 | 20.71 | **+0.17** | 0.5034 | 114.19 | 79.67% | 89.66% |

Soft stacking has the strongest aggregate RMSE/rank/tail profile, but baseline has the best aggregate MAE and the cell-level symmetric evidence does not support granting soft stacking blanket authority. The fixed 75/25 policy likewise looks competitive in pooled metrics but has a known severe QB-Y8 failure and therefore cannot be treated as a universal architecture.

## 4. Exact cells

### QB Y5 — blanket 75/25

Central evidence:
- RMSE **89.93** vs baseline **103.59**, hard router **93.40**, soft stack **92.23**;
- MAE **59.22**;
- top-tail RMSE **178.71** vs baseline **260.30**;
- absolute bias **3.62** vs baseline **37.58**.

Clustered pairwise evidence:
- MSE gain vs baseline: **+2,643.6**, 95% CI **[+145.2, +5,659.5]**;
- top-tail MSE gain vs baseline: **+35,820.0**, 95% CI **[+25,850.8, +46,175.1]**;
- MSE gain vs hard router: **+636.7**, 95% CI **[+73.1, +1,218.0]**;
- MAE gain vs hard router: **+3.21**, 95% CI **[+0.93, +5.42]**;
- MAE gain vs soft stack: **+3.32**, 95% CI **[+1.41, +5.55]**.

No peer shows a supported primary-dimension loss that reverses this result. This is an exact Research authority cell.

### WR Y5 — hard router

Central evidence:
- RMSE **31.14**;
- MAE **17.42**;
- top-tail RMSE **82.63**;
- Spearman **0.5209**.

Clustered pairwise MAE gains:
- vs baseline: **+1.34**, 95% CI **[+0.59, +2.23]**;
- vs soft stack: **+0.31**, 95% CI **[+0.03, +0.72]**;
- vs blanket 75/25: **+0.77**, 95% CI **[+0.04, +1.58]**.

Again, no peer shows a supported primary-dimension loss sufficient to create a tradeoff. This is the second exact Research authority cell.

## 5. Y8 uncertainty ceiling

All Y8 cells have only **two** qualifying repeated outer origins.

The persisted central evidence still contains useful warnings:
- QB Y8 baseline RMSE **78.00**;
- soft stack **78.35**;
- hard router **83.12**;
- blanket 75/25 **102.23**.

That rejects any claim that the 75/25 blend is universally safe. It does **not** grant exact Y8 authority to baseline or soft stack because independent outer support remains structurally insufficient.

RB-Y8 and WR-Y8 have a directional hard-router result in the symmetric map, but the two-origin ceiling prevents exact-cardinal promotion.

## 6. Downstream current-player implications

The only already-persisted governed current-player shadow is the 335-player long-horizon baseline/comprehensive shadow. It is useful for **impact magnitude**, not for selecting among the symmetric policies.

Relative to governed H3, its rank behavior is:

| Horizon | H3-vs-H rank Spearman | Median abs rank move | P90 move | Share moving >=20 |
| --- | ---: | ---: | ---: | ---: |
| H4 | 0.9940 | 4 | 12 | 3.6% |
| H5 | 0.9860 | 7 | 19 | 9.6% |
| H6 | 0.9767 | 10 | 24 | 17.0% |
| H7 | 0.9712 | 11 | 27 | 22.4% |
| H8 | 0.9679 | 12 | 29 | 26.0% |

So long-horizon information is not merely cosmetic: rank effects become material for a growing minority of players. But because 18/20 symmetric cells lack exact single-policy authority, these movements must carry **model-authority uncertainty**, not just point-estimate uncertainty.

Descriptive current-shadow age patterns also become larger with horizon:
- young QB mean H3→H5 rank improvement: **22.5** places; H3→H8: **35.2**;
- aging RB mean H3→H5 movement: **-12.6**; H3→H8: **-20.8**;
- aging WR: **-9.4 / -16.9**;
- aging TE: **-7.0 / -13.3**.

These are descriptive shadows from one historical architecture. The symmetric age/exposure audit specifically rejects turning them into a universal youth premium, age cliff, or workload penalty.

## 7. Intrinsic / product consequence

Current production Intrinsic consumes governed H1-H3, not Y4-Y8. Therefore this Research result causes **zero current production Intrinsic/value/rank change**.

If a long-horizon product lens is later authorized:
- H5 is the most useful candidate display horizon because it has five outer origins and two cells with exact policy authority;
- QB-Y5 may use the frozen 75/25 Research policy;
- WR-Y5 may use the frozen hard-router Research policy;
- RB-Y5 and TE-Y5 must remain model-set / uncertainty-forward;
- all Y4/Y6/Y7 non-exact cells must expose policy/model uncertainty rather than manufacture one precise cardinal score;
- Y8 must remain coarse/uncertain.

A future production implementation should carry at least two uncertainty layers:
1. within-model forecast/residual uncertainty;
2. between-model / policy-authority uncertainty for cells without exact authority.

Cross-horizon covariance is still unvalidated, so these long-horizon estimates must not be summed into a falsely precise lifetime Intrinsic quantity.
