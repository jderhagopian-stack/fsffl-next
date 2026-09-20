# FSFFL NEXT - Y3 developmental-RB gap-aware prospective log1p partial-pooling challenger

Research only. Starting mechanism-diagnostic head: bb66b7f6e6bdac946d42a2414c59f618aea341e4. PR #147, protected main, production runtime, P0/D1 authority, Value, Intrinsic, Shapley, Simulation, league scoring, merge, deploy, and source-2023 -> target-2026 outcomes are out of scope.

This specification is frozen before challenger performance is inspected. Exactly one challenger is authorized.

## Frozen control and coordinate

Control: exact D1 Y3 developmental-RB Forecast.

Canonical evaluation origins: source seasons 2014-2022 inclusive.

At each evaluation origin T:
- reconstruct the governed point-in-time Y3 row coordinate;
- use the exact D1 state probabilities and state-conditional production means generated prospectively at T;
- fit the calibrator only from earlier source-origin prospective residuals whose Y3 target outcomes are fully resolved by T-1;
- never calibrate against a row using a D1 mean from a model that was fit on that same row.

D1 p_out, positive-state probabilities, developmental classification, state routing, D0/D1 selection, and distribution-scale treatment remain unchanged.

## Prospective residual training library

Construct D1 prospective state means for the earliest reproducible Y3 source origins permitted by the frozen Phase-2 coordinate. An origin s is eligible for the residual library only when the frozen D1 production model can be fit from earlier Y3 rows resolved by s-1.

For an eligible source-origin row with realized positive future state:
  r_i = log1p(target_points_i) - log1p(D1_mean_for_realized_state_i_at_origin_s).

For evaluation origin T, the calibrator may use only residual-library rows with source origin s satisfying s+3 <= T-1.

The primary 2014-2022 evaluation coordinate is unchanged; earlier residual origins are training evidence only.

## State groups and continuous magnitude

Upper group: starter, premium, elite.
Lower group: depth, usable.

u = governed source_percentile.
z = 2*(u-0.5).
A = log(1.50), recovered exactly from the mechanism artifact.

Four fitted parameters per evaluation origin:
- a0 shared intercept
- a1 shared magnitude slope
- d0 lower-group intercept deviation
- d1 lower-group magnitude-slope deviation

Upper correction:
  c_U(u) = A * tanh(a0 + a1*z).

Row-specific D1 log1p ordering gap:
  G(r) = log1p(D1_starter(r)) - log1p(D1_usable(r)).

Lower deviation score:
  h(u) = d0 + d1*z.

Lower correction:
  c_L(u,r) = c_U(u) + G(r) * tanh(h(u)).

Adjusted positive-state means:
- upper state s: expm1(log1p(D1_mean_s) + c_U)
- lower state s: expm1(log1p(D1_mean_s) + c_L)

No p75/p90/p95 state, knot, breakpoint, extra latent state, mixture, scale model, or survival classifier is allowed.

## Ordering invariant

Within-group order is inherited because all states in a group receive the same log1p correction.

For usable vs starter:
  log1p(adjusted_usable) - log1p(adjusted_starter)
  = -G(r) + G(r)*tanh(h)
  = G(r)*(tanh(h)-1) < 0.

Therefore usable < starter is guaranteed algebraically for finite h when G(r)>0.

Every training and evaluation row must also pass numerical checks for all adjacent positive-state pairs.

## Fixed objective and regularization

For each eligible prospective residual-library row, predicted residual is c_U or c_L according to the realized future-state group.

Minimize:
  mean((r_i - predicted_residual_i)^2)
  + 0.05*(a0^2+a1^2)
  + 0.10538922155688623*(d0^2+d1^2).

These penalties are frozen from the mechanism/feasibility artifacts. No search or sensitivity replacement is allowed.

Optimizer is inherited unchanged from the prior partial-pooling challenger:
- deterministic SLSQP
- initial parameters all zero
- maxiter 2000
- ftol 1e-12
- no extra parameter constraints are required because final ordering is guaranteed by the gap-aware map.

If an origin fit does not converge, or numerical ordering/parity fails, stop without changing the optimizer, penalties, amplitude, or form.

## Predictive distribution

Use exact frozen D1 probabilities on support:
  0, adjusted depth, adjusted usable, adjusted starter, adjusted premium, adjusted elite.

No extra within-state spread or magnitude-dependent variance is added.

## Primary scores

Primary authority score: raw-point CRPS of the full six-point predictive distribution.

Point guardrail: raw-point MAE of predictive expectation.

State-probability diagnostics: D1 active and six-state scores remain unchanged by construction and are verified for parity.

## Continuous magnitude co-primary

For target-active evaluation rows:
- fixed source-percentile deciles [0,.1),...,[.9,1];
- realized-state conditional retention bias;
- integrated magnitude-conditioned calibration error (IMCE) = active-row-count-weighted mean absolute decile bias.

Report overall, upper-group, and lower-group IMCE.

Tail slices p75+, p90+, p95+ are diagnostic only and cannot determine authority.

## State, ordering, and coverage diagnostics

Report individual realized-state point/retention bias and CRPS for elite, premium, starter, usable, and depth.

Report by origin:
- minimum adjusted starter-minus-usable gap in raw points and log1p space;
- minimum other adjacent-state gaps;
- max abs(tanh(h));
- fractions with abs(tanh(h)) >= 0.90, 0.95, and 0.99;
- zero final-state ordering violations.

Report 10-90 and 25-75 discrete predictive interval coverage overall and by realized upper/lower group.

## No-harm and robustness

Ordinary / low-mid source region: source_percentile < 0.75.

Report full-cell and low-mid CRPS, MAE, IMCE, active conditional bias, and coverage.

Temporal robustness:
- all nine origin gains;
- >=6/9 origins improved for authority;
- median origin gain;
- worst-origin regression;
- every leave-one-origin-out pooled gain.

Uncertainty:
- player x source-year Bayesian bootstrap, 5,000 reps, seed 20260920;
- moving source-year block bootstrap, block length 3, 5,000 reps, seed 20260921.

Player influence:
- fixed-prediction leave-one-player-out pooled CRPS gain for every evaluation player;
- no sign reversal may be caused by one player.

## Operational promotion gates

All material gates must pass:

1. Full-cell CRPS: D1-minus-challenger gain >= 0; clustered 95% lower bound >= 0; >=6/9 origins improve; median origin gain >=0; no leave-one-origin-out sign reversal.
2. Continuous magnitude: overall IMCE improves by >=10%; clustered 95% lower bound for overall IMCE improvement >=0; upper and lower group IMCE each improve (>0 absolute improvement).
3. Individual states: no state may worsen absolute realized-state retention bias by >0.05.
4. MAE no-harm: pooled MAE gain >= -0.50 points and clustered 95% interval is not wholly below zero.
5. Low/mid no-harm: source_percentile<0.75 CRPS gain >= -0.50 with clustered 95% interval not wholly below zero; low/mid IMCE must not worsen.
6. Coverage: no overall or upper/lower 10-90 or 25-75 coverage loss worse than 0.03 absolute.
7. Ordering and frozen-state parity: zero ordering violations; D1 probabilities/routing/scale unchanged.
8. Influence: moving-block conclusion, leave-one-origin-out, and leave-one-player-out cannot show a single origin/player determining a positive authority conclusion.
9. Source-2023 -> target-2026 remains untouched.

No alternate challenger, penalty, coordinate, state grouping, amplitude, or constraint form may be introduced after results.

## Required classification

A. GAP-AWARE PROSPECTIVE PARTIAL-POOLING CHALLENGER EARNS RESEARCH AUTHORITY
B. MECHANISM WAS CORRECT, BUT CHALLENGER IS NOT STRONG ENOUGH
C. CORRECTLY SPECIFIED CHALLENGER FAILS
D. DIFFERENT FORECAST COMPONENT IS IMPLICATED
E. REPRODUCIBILITY / SPECIFICATION BLOCKER
