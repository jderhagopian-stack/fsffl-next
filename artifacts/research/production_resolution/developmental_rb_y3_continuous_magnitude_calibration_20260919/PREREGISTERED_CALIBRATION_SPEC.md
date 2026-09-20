# FSFFL NEXT - Y3 developmental-RB continuous-magnitude calibration preregistration

Research only. Frozen starting head: 984ab2755f8d014b191785bfdd92f434f104a462. PR #147, protected main, production runtime, P0/D1 authority, Value, Intrinsic, Shapley, Simulation, league scoring, merge, and deploy are out of scope.

This specification is persisted before candidate evaluation. D1 state probabilities, state routing, career-stage routing, and the D1-vs-D0 route decision remain frozen.

## Canonical coordinate

Primary Y3 developmental-RB origins: 2014-2022 inclusive. At each origin T:
- rebuild the exact governed point-in-time source coordinate;
- fit the frozen D1 state/production machinery using only outcomes fully resolved by T-1;
- estimate the calibration using only Y3 developmental-RB rows whose outcomes are fully resolved by T-1;
- evaluate source-season T prospectively.
No incomplete 2026 outcomes are used. Source-2023 -> target-2026 remains untouched prospective confirmation.

## Control parity

Before evaluating candidates:
1. exact rolling D1 predictions for 2014-2022 must reproduce the durable historical prediction artifact within 1e-10 for probabilities and 1e-8 for point outputs;
2. state probabilities must remain byte-for-byte/numerically unchanged by candidate scoring to floating-point tolerance.

## Candidate family

Both candidates are threshold-free, location-only calibrations. They do not alter scale/uncertainty separately, state probabilities, or state labels. They define valid Forecast distributions by multiplying every positive-state D1 support point by the same smooth row-level factor while leaving the D1 state probabilities unchanged.

Let u = source_percentile in [0,1] and z = 2*(u-0.5). Let A = log(1.50), fixing the multiplicative adjustment to the bounded interval [2/3, 1.5].

For an evaluation row with D1 positive-state mean m_s:
  m_s^cal = m_s * exp(A * tanh(g(u))).

Candidate C1 - bounded affine:
  g(u) = b0 + b1*z.

Candidate C2 - bounded quadratic:
  g(u) = b0 + b1*z + b2*(z^2 - 1/3).

C2 adds exactly one nonlinear degree of freedom. No knots, breakpoints, splines, trees, threshold states, or hyperparameter searches are allowed.

## Origin-specific fitting

For each origin T, fit the candidate coefficients on resolved, target-active Y3 developmental-RB rows only. D1 outputs for these calibration rows are generated from the same origin-T frozen D1 fit, using only information available by T.

The fit target is log multiplicative conditional-production residual:
  y_i = log(target_points_i / D1_conditional_active_mean_i).

Coefficients minimize:
  mean((y_i - A*tanh(g(u_i)))^2) + 0.05 * sum_j b_j^2.

The ridge weight 0.05, bound A=log(1.50), feature definitions, optimizer, and initial coefficients (all zeros) are frozen here. Use deterministic L-BFGS-B with max 2000 iterations and tolerance 1e-10. If optimization does not converge, candidate fails that origin; do not change settings.

The D1 conditional-active mean is the D1 expected points divided by p_active. State probabilities are never refit by the calibrator.

## Full predictive distribution

For each row:
- p_out remains frozen D1 p_out at point 0;
- each positive-state probability p_s remains frozen;
- each positive-state support point is m_s^cal;
- probabilities are normalized only for numerical roundoff if absolute sum error exceeds 1e-12.
This is a coherent discrete Forecast distribution. There is no second collapse draw, survivor classifier, or downstream haircut.

## Primary scores

Primary authority score:
- raw-point CRPS of the full six-state predictive distribution.

Point guardrail:
- raw-point MAE of the predictive expectation.

State diagnostics:
- active Brier/log loss and six-state Brier/log loss are reported from frozen D1 and must be exactly unchanged.

Continuous magnitude co-primary:
- fixed source-percentile deciles [0,.1), ... [.9,1];
- within active rows, compute D1 and candidate conditional-active retention bias in each bin;
- integrated magnitude-conditioned calibration error (IMCE) is the active-row-count-weighted mean absolute bin bias;
- report a smooth LOWESS-style visualization only for presentation; it has no authority role.

Tail diagnostics:
- p75+, p90+, p95+ active-retention bias, CRPS, expected-point bias, and row counts, reported only after candidate freeze.

Low/mid-source no-harm:
- source_percentile < 0.75 raw-point CRPS and MAE.

## Uncertainty and temporal robustness

Use the persisted player/source-year Bayesian bootstrap for pooled gain intervals (5,000 reps; deterministic seed 20260919).
Use moving source-year block bootstrap sensitivity with block length 3 (5,000 reps; seed 20260920).
Report all nine origin gains, share improved, median gain, worst-origin regression, and leave-one-origin-out pooled gain range/sign.

For IMCE, recompute the fixed-bin statistic inside the same player/source-year Bayesian bootstrap.

## Promotion gates

A candidate earns research authority only if all are true:

1. Full-cell Y3 developmental-RB CRPS gain (D1 minus candidate) > 0, clustered 95% CI lower bound >= 0, at least 6/9 origins improve, median origin gain > 0, and no leave-one-origin-out pooled sign reversal.
2. Continuous magnitude calibration: pooled IMCE improves by at least 10% versus D1 and the clustered 95% interval for IMCE improvement has lower bound >= 0.
3. Supported high-source compression improves directionally without becoming material overprediction: absolute p75+ and p90+ active-retention bias must not worsen; p95+ is descriptive/influence only and cannot decide authority alone.
4. MAE guardrail: pooled MAE gain (D1 minus candidate) >= -0.50 points and its clustered 95% interval is not wholly below zero.
5. Low/mid-source no-harm: source_percentile < 0.75 CRPS gain >= -0.50 points and its clustered 95% interval is not wholly below zero.
6. Temporal shape stability: the fitted high-vs-mid adjustment [multiplier at u=.95 minus multiplier at u=.50] has the same sign in at least 6/9 origins and no single origin removal changes the full-cell CRPS conclusion.
7. Distribution validity and frozen-state parity pass exactly.
8. No downstream double counting is introduced.

If both candidates pass, prefer C1 unless C2 improves pooled CRPS over C1 by at least 0.25 raw point with a clustered 95% interval lower bound >= 0. C2 may still be reported as directionally better without earning preference.

If neither passes, do not retune from the results.

## Cross-position diagnostic

Only after the RB candidate disposition is frozen, apply the selected mathematical form diagnostically to adequately supported Y3 developmental/established QB, WR, and TE routes using the same per-origin fitting recipe and frozen D1 controls. Report whether the form improves CRPS/calibration directionally. Do not change or reopen those routes.

## Classification

Use exactly one directive classification:
A. CONTINUOUS-MAGNITUDE CALIBRATION EARNS RESEARCH AUTHORITY
B. DIRECTION SUPPORTED, SPECIFIC CALIBRATION NOT YET SUFFICIENT
C. CONDITIONAL-PRODUCTION CALIBRATION DOES NOT RESOLVE THE PROBLEM
D. EVIDENCE IMPLICATES A DIFFERENT D1 COMPONENT
E. REPRODUCIBILITY / IDENTIFIABILITY BLOCKER
