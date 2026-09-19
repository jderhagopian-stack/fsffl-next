# Forecast rejection audit and corrected selection — final checkpoint

Date: 2026-09-18

## Stage 1
Reopening gate outcome B was persisted at commit d83339c8df21d1adbc10655a516c53770bf0ebe7 before corrected re-evaluation.

Collapse-veto casualties: B2a/B2b, B3, R1/R2, H2, and the later I1 conditional-production/magnitude repair component. Legitimate non-collapse closures remain closed: C1/C2/C3, M2/M3, I2 complete architecture, regularization alternatives.

## Corrected selection
Final outcome category: A.

Provisional Forecast freeze candidate: B2a conditional-active production refinement on the otherwise frozen routed Forecast architecture.

Pre-holdout aggregate:
- B Y2 MAE 41.3796; B2a 41.0893. Bias -18.74 -> -16.53. Top10 MAE 61.2469 -> 60.3294. Role-loss MAE 32.8406 -> 34.4633.
- B Y3 MAE 43.1295; B2a 42.5842. Bias -18.19 -> -14.07. Top10 MAE 60.6243 -> 59.8876. Role-loss MAE 32.6485 -> 35.1278.
- B2a broad MAE is better than B in all three pre-holdout folds at both horizons.
- Young MAE is essentially stable/slightly improved in aggregate.
- B2b adds no replicated value.

Richer reopened candidates do not win under the corrected policy for reasons beyond a collapse veto:
- B3: strong top-tail improvement but validation/both later Y3 broad instability and young Y3 deterioration; severe-collapse cost large.
- R1/R2: top-tail improvement but validation broad and young stability deteriorate; severe-collapse cost large.
- H2: no leakage-free early hybrid evaluation from persisted anchors; validation Y3 broad MAE worsens and role-loss penalty remains material.

2021-2022 was not used to rescue/reopen/select. Current 335-player board was not used. No new candidate was fit for final selection.

## Collapse roster
Exported from governed role-loss evidence:
- 808 evaluation rows
- 661 unique player/source-season coordinates
- 411 deep rows with realized retention <25%
- 187 large-decline rows with retention >=25% and <50%
No causal inference performed.

## Boundaries
No production implementation, promotion, merge, deploy, main change, PR #147 change, Shapley/Intrinsic change, external causal research, or new Forecast research chain.

STOP for management.
