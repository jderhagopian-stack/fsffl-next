# FSFFL NEXT - Y3 developmental-RB preregistered partial-pooling challenger

Research only. Starting feasibility commit: 6d21b4900ee9dc6345f8b9c2cf78f9806f8d6545. PR #147, protected main, production runtime, P0/D1 authority, Value, Intrinsic, Shapley, Simulation, league scoring, merge, deploy, and source-2023 -> target-2026 outcomes are out of scope.

This specification is frozen before challenger performance is inspected. Exactly one challenger is authorized.

## Control and coordinate

Control is exact frozen D1 for Y3 developmental RB. Canonical prospective evaluation origins are 2014-2022 inclusive. At each origin T:
- reconstruct the exact governed point-in-time row coordinate;
- fit the exact D1 state and production machinery using only outcomes fully resolved by T-1;
- fit the partial-pooling calibrator only on target-active Y3 developmental-RB rows fully resolved by T-1;
- evaluate source-season T prospectively.

D1 p_out, all positive-state probabilities, routing, developmental classification, and state membership are frozen.

## Two-group state structure

Upper group: starter, premium, elite.
Lower group: depth, usable.

Let u=source_percentile and z=2*(u-0.5). Let A=log(1.50).

The challenger has four fitted parameters per origin:
- a0: shared intercept
- a1: shared continuous-magnitude slope
- d0: lower-group intercept deviation
- d1: lower-group magnitude-slope deviation

Upper linear predictor:
  g_U(u)=a0+a1*z

Lower linear predictor:
  g_L(u)=a0+a1*z+d0+d1*z

Bounded state-mean multipliers:
  M_U(u)=exp(A*tanh(g_U(u)))
  M_L(u)=exp(A*tanh(g_L(u)))

For each D1 positive state s:
  mean_challenger(s,u)=D1_mean(s) * M_U(u), if s in {starter,premium,elite}
  mean_challenger(s,u)=D1_mean(s) * M_L(u), if s in {depth,usable}

No separate state-specific slopes, breakpoints, tiers, mixture weights, or scale parameters are allowed.

## Calibration fit target

For active calibration rows, use the realized future state s_i and frozen origin-specific D1 state mean m_i:
  y_i = log(target_points_i / m_i).

The fitted residual predictor is A*tanh(g_U) or A*tanh(g_L), depending on the realized future-state group.

The deterministic objective is:
  mean((y_i - yhat_i)^2)
  + 0.05*(a0^2+a1^2)
  + lambda_dev*(d0^2+d1^2)

The shared ridge 0.05 is inherited unchanged from the prior preregistered continuous-calibration research.

The lower-state deviation penalty is frozen from feasibility support before performance:
  lambda_dev = 0.05 * (N_upper / N_lower)
where pooled feasibility active support is N_upper=352 and N_lower=167.
Therefore lambda_dev = 0.10538922155688623.

This fixed value is used identically at every origin. It is not tuned to CRPS, tail slices, 2026, or named players.

Optimizer: deterministic SLSQP, initial parameters all zero, maxiter=2000, ftol=1e-12.

## Ordering constraint

Because within-group multipliers are common, D1 within-group order is inherited. To guarantee usable < starter across the entire continuous magnitude range, enforce:
  d0 + d1*z <= 0 for all z in [-1,1].

For an affine deviation this is exactly enforced by the two endpoint constraints:
  d0+d1 <= 0
  d0-d1 <= 0.

Thus M_L(u) <= M_U(u) for every u in [0,1]. Report whether either constraint is binding within 1e-6.

If optimization fails or constraints are violated above 1e-8, that origin is a fitting failure; do not change the optimizer or penalty.

## Predictive distribution and scale

The challenger uses the frozen D1 probabilities on support:
  0, challenger depth mean, challenger usable mean, challenger starter mean, challenger premium mean, challenger elite mean.

No magnitude-dependent variance, mixture component, or new uncertainty parameter is added. This preserves the D1 distributional scale treatment except for the preregistered state-group location calibration.

## Scores and diagnostics

Primary: raw-point CRPS of the full six-point predictive distribution.

Co-primary continuous magnitude calibration:
- fixed source-percentile deciles [0,.1),...,[.9,1];
- active-row realized-state conditional retention bias;
- integrated magnitude-conditioned calibration error (IMCE) = active-row-count-weighted mean absolute decile bias;
- report overall, upper group, and lower group.

State diagnostics:
- realized-state conditional retention/point bias for depth, usable, starter, premium, elite;
- no independent state fitting.

Guardrails:
- raw-point MAE of predictive expectation;
- source_percentile <0.75 CRPS, MAE, and active conditional-calibration no-harm;
- 10-90 and 25-75 predictive interval coverage overall and by upper/lower realized-state group;
- exact probability parity with D1;
- exact ordered positive-state supports.

Tail continuity diagnostics after freeze only: p75+, p90+, p95+.

## Temporal and influence robustness

Report all nine origin CRPS gains, origins improved, median gain, worst-origin regression, and leave-one-origin-out pooled gain.

Uncertainty:
- player x source-year Bayesian bootstrap, 5,000 reps, seed 20260919;
- moving source-year block bootstrap, block length 3, 5,000 reps, seed 20260920.

Influence:
- fixed-prediction leave-one-player-out pooled CRPS gain for every player;
- report minimum/maximum leave-one-player-out gain and most influential player;
- no named-player tuning or refitting.

## Promotion gates

Research authority requires every material gate:
1. Full-cell pooled CRPS gain D1 minus challenger >=0; clustered 95% lower bound >=0; >=6/9 origins improve; median origin gain >=0; no leave-one-origin-out sign reversal.
2. Overall IMCE improves, and upper-group and lower-group IMCE each improve or credibly preserve; lower-group IMCE must strictly improve because the feasibility signal is a lower-vs-upper difference.
3. State diagnostics do not reveal a new material calibration failure; upper/lower opposite-direction bias is reduced without manufacturing five curves.
4. Pooled MAE gain >= -0.50 and clustered 95% interval is not wholly below zero.
5. Source_percentile<0.75 CRPS gain >= -0.50 with clustered 95% interval not wholly below zero; low/mid active calibration does not materially worsen.
6. Overall and group coverage does not materially degrade by more than 0.03 absolute at either the 10-90 or 25-75 interval.
7. Ordering constraints and probability parity pass exactly.
8. Temporal, leave-one-origin-out, moving-block, and leave-one-player-out analyses do not show a single origin/player determining the conclusion.
9. Source-2023 -> target-2026 remains untouched.

If any material gate fails, no second challenger may be fit and no penalty may be retuned.

## Classification

End with exactly one:
A. PARTIAL-POOLING CHALLENGER EARNS RESEARCH AUTHORITY
B. DIRECTION SUPPORTED, CHALLENGER NOT SUFFICIENT
C. PARTIAL-POOLING CHALLENGER FAILS
D. RESULTS IMPLICATE A DIFFERENT FORECAST COMPONENT
E. REPRODUCIBILITY / FITTING BLOCKER
