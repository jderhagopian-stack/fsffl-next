# Stage C S1 Pre-Holdout Resolution

Date: 2026-09-18

## Recovery correction
The earlier df5e644 recovery artifact was valid I1 material but insufficient by itself for Stage C because it lacked h=3 and did not cover every B2a pre-holdout coordinate. No S1/S2 fit used that incomplete coordinate.

An already-durable exact selected-Forecast artifact was then recovered from PR #150 workflow run 35055361960, artifact 10430792617. Its selection_rows.csv is player-keyed, covers direct I1 h=1/2/3 for source seasons 2014–2020, uses global C=0.25, and joins the B2a pre-holdout coordinates exactly: Y2 2,376/2,376; Y3 1,911/1,911; no duplicate keys or unexplained losses. No replay/refit was required for this recovery.

## S1 implementation
The frozen Stage-C family was applied only to QB/WR at Y2/Y3. Inputs remained the three frozen continuous source-time depth features. Risk directions frozen in the Stage-C specification were enforced monotonically; no threshold was introduced. Missing depth evidence caused no adjustment.

The structural term was fit as a regularized offset to the frozen I1 persistence log-odds, with C=0.25 and no free intercept. Conditional persistent-state proportions were preserved, so the Stage-C term could move only out-vs-persist probability rather than conditional-production magnitude. Training for each evaluation season used only prior rows satisfying source_season + horizon < evaluation source season. Early rows with no legally prior fitted Stage-C sample remained unchanged.

Holdout 2021–22 and the current board remained sealed.

## Result
S1 does improve the exact cases it was designed to catch: among eventual out outcomes, persistence Brier improves by about 0.0301 at Y2 and 0.0075 at Y3.

But that benefit is outweighed by false-positive probability suppression among players who persist. Broad replicated metrics worsen:
- Y2 mid persistence Brier +0.000214; validation +0.012278.
- Y3 mid +0.000981; validation +0.003166.
- State Brier and state log loss also worsen in both evaluable mid/validation horizons.
- The validation deterioration is materially larger than the mid-fold deterioration.

This fails the Stage-C selection standard requiring observable-risk improvement without broad drag. The role/security signal is real descriptively, but the bounded source-time adjustment does not improve the frozen Forecast probability layer sufficiently to justify promotion.

## S2 disposition
S2 is not justified. It would use the same failed structural-risk probability machinery with a richer conditional-production magnitude. The Stage-C question is whether observable role/security evidence can safely absorb collapse risk at the probability layer. Because S1 worsens that layer on broad replicated evidence, changing the magnitude model cannot cure the demonstrated probability-calibration drag and would add an unnecessary second degree of freedom.

## Outcome
Outcome B: none of the authorized Stage-C challengers justifies replacing B2a. Keep B2a as the provisional Forecast candidate and product forward. Do not reopen Stage-B feature selection, do not tune thresholds/weights, and do not use holdout/current-board evidence to rescue Stage C.

No main, PR #147, production authority, Intrinsic/Shapley, C=0.25, or 0.85 discount change.
