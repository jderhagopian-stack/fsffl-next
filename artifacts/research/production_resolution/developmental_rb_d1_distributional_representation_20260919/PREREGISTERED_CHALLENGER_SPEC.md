# FSFFL NEXT - Developmental RB D1 bounded challenger preregistration

Research only. P0 remains the frozen production control. PR #147, main, production code, state definitions, Value, Intrinsic, Shapley, Simulation, scoring translation, and league-specific logic are out of scope.

## Frozen pre-holdout diagnosis

The exact rebuilt rolling D1 predictions reproduce the 10,336-row historical prediction artifact to floating-point tolerance. In 2014-2020 developmental top-decile RB rows, a controlled +10% source-points perturbation produces very low positive elasticity in the D1 state-conditional production means (median about 0.05 at Y3) and a negative conditional-active state-mix elasticity (median about -0.09 at Y3). The combined conditional-production response is therefore approximately flat to slightly negative while the retention denominator rises. The state-mix contribution is driven mechanically by the already-governed source-minus-prior dpts feature, whose ordered-state coefficients are negative for RB thresholds; the conditional-production layer itself is an absolute-point regression with strongly sub-unit source elasticity.

## One bounded challenger: D1R

D1R is a general conditional-production coordinate change, not an RB premium or player-specific correction.

- State probabilities are identical to frozen P0/D1. No persistence, collapse, or future-state probability is refit or altered.
- Training population, chronology, future-state conditioning, feature dictionary, scaler rules, BayesianRidge family/hyperparameters, pooled position architecture, prior-history features, and no-cap/no-manual-floor policy are identical to D1.
- The only change is the conditional-production target coordinate:
  delta_log_points = log1p(target_points) - log1p(source_points)
  for target-active training rows.
- For a requested positive future state, D1R predicts delta_log_points with the same D1 features and converts back with:
  predicted_state_points = max(0, exp(log1p(source_points) + predicted_delta_log_points) - 1).
- D1R is fit across all positions exactly as D1 is; developmental RB is the authorized decision cohort. QB/WR/TE are no-harm controls only.
- No current-player names or 2026 outputs may enter fitting, threshold choice, or selection.

## Frozen chronology and scoring

Development/selection uses source seasons 2014-2020 with the governed early (2014-16), mid (2017-18), validation (2019-20) blocks. Locked 2021-2022 is not evaluated until the pre-holdout decision is frozen.

Primary metric: raw-point CRPS of the full six-state mixture (out point mass at 0 plus the five positive-state point masses). Ordinary expected-point MAE is a guardrail. Also report conditional-active point/retention bias, high-source retention-ratio CRPS, source-tertile results, and unchanged state calibration.

## Promotion gates

D1R may earn research authority for developmental RB at a horizon only if all are true on 2014-2020 before holdout:
1. Full-cell raw-point CRPS gain D1-D1R is positive in early, mid, and validation blocks and pooled two-way bootstrap 95% CI is above zero.
2. For the pre-existing high-source Y3 anchor source_points > 225.5, mean conditional-active retention bias moves at least 0.05 toward zero, without crossing above +0.05 mean overprediction.
3. Ordinary expected-point MAE is not materially/significantly worse: pooled mean MAE gain D1-D1R is >= -1.0 point and the two-way bootstrap 95% interval is not wholly below zero.
4. No lower or middle developmental-RB source tertile has raw-point CRPS degradation worse than 1.0 point or statistically supported degradation.
5. State/persistence calibration is exactly unchanged by construction.
6. Y2 is judged independently; it changes only if it independently passes the same gates. The Y3-specific 225.5 anchor is diagnostic only for Y3.
7. After the pre-holdout decision is persisted, locked 2021-2022 is evaluated exactly once. An earned candidate must retain positive full-cell CRPS direction, preserve the MAE guardrail, and reduce rather than worsen high-source conditional-retention bias where supported.

If D1R fails, do not revise it from holdout evidence. Persist the failure and stop for management.
