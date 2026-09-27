# Y4-Y8 Age / Experience / Exposure — Symmetric Interpretation

Date: 2026-09-27  
Authority: **Research only / production H3 unchanged**

## Purpose

The prior age/exposure audit used a multi-objective composite and correctly warned against causal wear-and-tear claims. This symmetric re-read goes one step further: each frozen variant is treated as a peer and the survival, total-production and conditional-production dimensions are read separately with paired source-origin × player uncertainty.

Exact reused evidence:
- **59,700** row-level predictions;
- five frozen variants;
- no refit;
- no current named-player evidence;
- no final-holdout relabeling.

## 1. Target-horizon age nonlinearity alone is not broadly supported

Comparison:
`target_poly` vs `base_linear`.

Across the 20 position×horizon cells:
- no cell has a supported total-MSE improvement;
- no cell has a supported total-MAE improvement;
- QB Y4 shows supported improvement in conditional-active MSE and MAE;
- RB Y5 and Y6 show supported **worse** total MAE;
- RB Y8 shows supported worse survival Brier;
- TE Y4-Y7 show supported worse survival Brier in four cells;
- TE Y7 shows supported worse total MSE and conditional MSE;
- TE Y8 shows supported worse conditional MSE/MAE.

Symmetric conclusion:
**simple target-age polynomial substitution does not earn general long-horizon authority.**
The QB Y4 conditional-production signal is real but component/cell-specific.

## 2. Cumulative exposure does not earn a universal role

Comparison:
`target_poly_exposure` vs `exposure_ablation`.

Supported positive evidence:
- RB Y7 and RB Y8 improve total MAE.

Supported negative evidence:
- RB Y6 worsens conditional-production MSE;
- WR Y8 worsens survival Brier;
- TE Y7 and TE Y8 worsen total MSE and MAE;
- TE Y7 worsens conditional MSE;
- TE Y8 worsens survival Brier.

No position/horizon cell shows a supported total-MSE gain from cumulative exposure.

Symmetric conclusion:
**cumulative workload is not a generally authoritative long-horizon feature block.**
It may carry useful role/survival information in selected RB settings, but the evidence does not justify a universal accumulated-workload term and still does not support interpreting workload causally as wear.

## 3. Nonlinear HistGB age/exposure is a serious component, not a blanket replacement

Comparison:
`target_exposure_histgb` vs `base_linear`.

Supported positive evidence:
- TE Y4 improves total MSE;
- TE Y4 improves survival Brier;
- QB Y5 improves conditional-active MSE.

Supported negative evidence:
- total MAE is worse for RB Y4, Y5, Y6 and Y7;
- total MAE is worse for TE Y6;
- WR conditional-active MAE is worse at Y4, Y5 and Y8;
- QB Y8 and TE Y8 have worse total MAE, but Y8 cannot earn exact authority in any event.

Most other differences remain clustered-uncertain.

Symmetric conclusion:
**nonlinear age/exposure has selected component/cell value but no universal authority.**
The prior composite statement that the nonlinear model was “better” in many QB/TE cells must be read as a multi-objective directional result, not as a supported across-metric replacement.

## 4. Survival and conditional production must remain separate

The new pairwise evidence reinforces the decomposed long-horizon contract:
- an age/exposure representation can improve survival while failing to improve conditional active scoring;
- or improve conditional active scoring without improving total production.

Therefore a single manual dynasty-age multiplier would collapse distinct empirical mechanisms and is not supported.

## 5. Y8 remains evidence-limited

Y8 still has only two valid repeated outer origins.

Some Y8 point differences are statistically directional inside those two origins, but the frozen chronology does not provide enough independent outer evidence for exact-cardinal Y8 authority.

No Y8 age/exposure variant is promoted.

## Authority disposition

- no universal manual age curve;
- no universal youth premium;
- no universal workload penalty;
- no universal age/exposure HistGB replacement;
- preserve selected nonlinear/age/exposure signals as component-level evidence for future explicitly bounded cell work;
- treat remaining age/exposure disagreement as model uncertainty.

Production Forecast, H3 and Intrinsic remain unchanged.
