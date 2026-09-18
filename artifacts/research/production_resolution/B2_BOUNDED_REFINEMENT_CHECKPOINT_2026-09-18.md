# FSFFL NEXT — B2 bounded refinement checkpoint

Date: 2026-09-18

## Authority
Executed the management-authorized B2 final bounded upper-tail / role-security refinement only. Candidate B remained the baseline. Persistence, routed state probabilities, exact-age machinery, identity/materialization, Shapley/Intrinsic, C=0.25, and cold-start separation were not redesigned.

## Validation integrity
Selection evidence used only pre-holdout rolling chronological folds:
- early: 2014–2016
- mid: 2017–2018
- validation: 2019–2020

The previously inspected 2021–2022 block was treated only as non-pristine secondary replication and did not control selection.

## Micro-variants
B2a: fixed five-bin monotone nonlinear within-position production-percentile correction in log-point space, partially pooled by position/horizon via n/(n+50) shrinkage toward the global bin effect.

B2b: B2a plus exactly one regularized interaction between the B2a magnitude correction and the frozen conditional-active starter+premium+elite probability. Ridge alpha=50, zero intercept. No other feature or interaction was added.

## Result
**NONE ADVANCED.**

B2a increased upper-tail retention and often improved upper-tail MAE, but the improvement was not clearly replicated at both horizons. More importantly, it worsened role-loss stress MAE in every pre-holdout fold/horizon:
- early Y2: B 33.80 → B2a 35.61
- early Y3: 30.81 → 32.95
- mid Y2: 31.77 → 33.13
- mid Y3: 38.99 → 41.70
- validation Y2: 32.59 → 34.20
- validation Y3: 29.92 → 32.69

B2b was effectively neutral relative to B2a and added no clear replicated value.

Young-player accuracy remained broadly stable.

Exact remaining gap: magnitude carry-forward can raise high-producer retention, but this bounded magnitude-only refinement cannot distinguish durable elite production from subsequent role deterioration well enough to satisfy both upper-tail calibration and role-loss safeguards. The one authorized frozen role-security interaction did not solve that separation.

Because no B2 variant froze under the advance rule, the preserved 335-player current board was **not** run through B2.

## Stop
No new model family or feature search was opened. No implementation, promotion, merge, deploy, main modification, PR #147 modification, or Shapley redesign was performed. STOP for management review.
