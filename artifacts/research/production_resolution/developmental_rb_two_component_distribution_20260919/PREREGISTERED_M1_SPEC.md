# FSFFL NEXT - Developmental RB two-component active-production preregistration

Research only. Frozen production control remains P0/D1. This specification is frozen before M1 is fit and before locked 2021-2022 is inspected in this stage. PR #147, main, production runtime, Value, Intrinsic, Shapley, Simulation, league scoring, deployment, and current-player outputs are out of scope.

## M1 component semantics

M1 preserves the frozen D1 inactive probability exactly. Conditional on being active, it represents production as a two-component latent mixture on log retention:

    y = log(target_points / source_points)

for historical active developmental-RB outcomes. The lower-mean component is labeled `major_decline`; the higher-mean component is labeled `productive_survivor`. These are continuous latent components, not hard retention states. The labels are fixed only by ordering the fitted component means.

The active productive-survivor probability varies smoothly with source magnitude:

    pi_survivor(u) = sigmoid(beta0 + beta1 * (u - 0.5))

where u is the frozen season-relative source_percentile. No p90/p95/>225.5 breakpoint enters the model.

Conditional on component k:

    log(target_points / source_points) ~ Normal(mu_k, sigma_k^2)

so active target production is source_points * exp(y), always positive. Overall predictive distribution is a D1 out point mass at zero plus the two active lognormal-retention components scaled by frozen D1 active probability.

## Fitting

M1 is fit separately for Y2 and Y3 using only developmental-RB historical rows whose target season is fully resolved by the relevant training cutoff. Selection chronology remains early 2014-2016, mid 2017-2018, validation 2019-2020.

Deterministic EM:
- initial component means = training 30th and 70th percentiles of y;
- initial component standard deviations = training y standard deviation;
- initial beta0=0, beta1=0;
- component means/variances use responsibility-weighted maximum likelihood;
- variance floor = 1e-4 for numerical stability only;
- beta0/beta1 are updated by fractional-outcome logistic Newton steps with fixed L2 penalty lambda=1.0 on beta1 only;
- max 200 EM iterations, relative log-likelihood tolerance 1e-8;
- components are re-ordered after every M step so mu_decline < mu_survivor.

A non-authoritative sensitivity check refits from 25th/75th percentile initialization. Material parameter or score divergence is a support warning and blocks promotion; it cannot be used to choose the better run.

## M2 decision

No M2 is authorized in this stage. The immediately preceding governed identifiability audit found no additional eligible point-in-time feature family that stably discriminated productive-survivor versus major-decline outcomes beyond source magnitude and existing D1 information. Adding a second conditioning dimension would therefore violate the directive's `only if justified` requirement.

## Predictive scoring representation

For scoring/quantiles, each active Gaussian component is represented by the fixed 199 midpoint normal quantiles q=(i-0.5)/199, i=1..199. The quantile grid is an evaluation approximation only; it is not fitted or tuned. Overall weights are D1 p_out at zero plus D1 p_active times the fitted component weight times equal within-component quantile weights.

## Evaluation regions

Evaluation only, not model states:
- out/inactive: x=0;
- severe active decline: 0 < x/source_points < 0.40;
- middle active: 0.40 <= x/source_points < 0.70;
- productive survivor: x/source_points >= 0.70.

## Co-primary promotion gates

M1 can earn Y3 developmental-RB research authority only if all pass on frozen 2014-2020 before holdout:
1. Full-cell raw-point CRPS gain D1-M1 is positive in early, mid, validation and pooled two-way player/season bootstrap 95% CI is above zero.
2. Four-region Brier gain is positive pooled with two-way bootstrap 95% CI above zero and is not negative in more than one chronology block.
3. Frozen p95+ tail calibration: combined absolute calibration error for productive-survivor mass plus downside mass (out + active<0.40) improves by at least 0.05 versus D1; neither survivor nor downside predicted mass may undershoot its observed mass by more than 0.05.
4. Ordinary expected-point MAE guardrail: pooled MAE gain D1-M1 >= -1.0 point and two-way bootstrap 95% interval is not wholly below zero.
5. source_percentile<0.90 no-harm: pooled CRPS degradation may not exceed 1.0 point and the two-way bootstrap 95% interval may not be wholly below zero.
6. Component support: in every selection training fit, responsibility effective sample size (sum responsibilities) is >=20 for each active component. The alternative initialization must converge to the same ordered solution within 0.10 in each component mean and 0.10 in beta1, and pooled CRPS gain direction must agree.
7. Frozen D1 p_out is reproduced exactly; probability normalization error <=1e-12. No inactive mass is moved into an active component.
8. Y2 is no-harm only: pooled CRPS degradation <=1.0, pooled MAE degradation <=1.0, neither two-way bootstrap interval is wholly adverse, and no block shows >1.0 CRPS degradation.
9. Forecast -> Simulation -> Value contract has no second collapse draw or Value haircut.

If M1 fails pre-holdout, locked 2021-2022 is still reported once but cannot rescue, retune, or redesign it. If M1 passes, locked replication must preserve positive CRPS direction, non-adverse Brier direction, p95+ tail-calibration improvement direction, MAE guardrail, Y2 no-harm, and probability normalization.