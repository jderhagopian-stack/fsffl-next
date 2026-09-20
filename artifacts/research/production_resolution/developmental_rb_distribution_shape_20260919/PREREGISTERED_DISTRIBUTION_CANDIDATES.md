# FSFFL NEXT - Developmental RB distribution-shape preregistration

Research only. Frozen control is P0/D1. This file is persisted before fitting the new distribution-shape candidates and before inspecting locked 2021-2022 in this stage. PR #147, main, production runtime, Value, Intrinsic, Shapley, Simulation, league scoring, deployment, and current-player outputs are out of scope.

## Exact research question

For Y3 developmental RBs, can Forecast preserve the frozen D1 persistence/state probabilities and state-conditional central means while representing within-state outcome uncertainty well enough to allocate realistic mass to both productive-survivor and collapse/downside regions?

This stage does not attempt to predict which individual player follows which path. No sustainable-breakout classifier is allowed.

## Frozen chronology

Selection evidence: source seasons 2014-2020 in the already-governed blocks:
- early 2014-2016, training data fully resolved by end-2013;
- mid 2017-2018, training data fully resolved by end-2016;
- validation 2019-2020, training data fully resolved by end-2018.

Locked replication: 2021-2022 exactly once after the pre-holdout decision is persisted.

Training rows for a horizon h are historical developmental-RB rows whose target season source_season+h is <= the block training cutoff. State definitions and source percentiles use the frozen point-in-time reconstruction.

## Control

D1 is the authoritative control. Its six state probabilities and five positive-state conditional means are taken from the exact frozen historical predictions. The D1H90 continuous-mean challenger is only a documented prior-stage reference and is not retried, refit, or eligible for rescue.

## Candidate S1 - state-conditioned empirical spread

For each horizon and positive future state, use the fully resolved training rows in that state to estimate an empirical within-state shape.

For state s:
1. Let m_s be the ordinary mean target_points among eligible training rows with target_state=s.
2. For each row i in that state define multiplicative shape q_i=target_points_i/m_s.
3. For an evaluation row, Candidate S1 assigns the frozen D1 state probability p_s across support points D1_mean_s * q_i with equal within-state weights.
4. The frozen D1 out probability remains a point mass at zero.

Because mean(q_i)=1 within each state, S1 preserves every D1 state-conditional mean and therefore preserves the D1 expected-point mean by construction. It only changes within-state uncertainty shape.

No trimming, winsorization, manual tail mass, floor, cap, or current-player adjustment is allowed.

## Candidate S2 - source-magnitude-conditioned empirical spread

S2 is identical to S1 except the empirical within-state shape is conditioned continuously on source_percentile.

For an evaluation source percentile u and training row percentile u_i, use fixed Gaussian weight:
  w_i = exp(-0.5 * ((u_i-u)/0.20)^2).

Within each state, normalize the weights, compute the weighted target-points mean m_s(u), and define q_i=target_points_i/m_s(u). Candidate support is D1_mean_s*q_i with normalized kernel weights.

Bandwidth 0.20 is frozen here and is not tuned. No hard p90/p95/>225.5 tier or breakpoint enters the candidate. Report effective sample size by row/state; any state-row ESS below 10 is a support warning, not a trigger for post-hoc bandwidth changes.

Because the weighted q distribution is centered to one, S2 also preserves D1 state-conditional means and total expected points exactly.

## Economically meaningful outcome regions

For every evaluation row, translate predictive support to retention relative to that row's source_points and report:
- out/inactive: point mass at 0 from frozen D1 out probability;
- severe active decline: active retention <0.40;
- middle active: 0.40 <= retention <0.70;
- productive survivor: active retention >=0.70.

The existing five positive future states are still retained separately; these four regions are evaluation summaries, not new production states.

## Scores

Primary: raw-point CRPS of the full predictive distribution.
Secondary proper scores:
- four-region multiclass Brier score;
- four-region log loss with fixed numerical floor 1e-12;
- survivor-event Brier score;
- downside-event Brier score where downside = out OR active retention <0.40.

Calibration / coverage:
- 10-90 and 25-75 predictive interval coverage and width;
- mid-PIT / rank diagnostics;
- observed vs predicted four-region mass overall and by source-magnitude region.

Point guardrail: ordinary expected-point MAE. S1/S2 are required to reproduce D1 expected points to floating-point tolerance; any material MAE difference is a reproducibility failure.

## Magnitude reporting

Report the full developmental-RB cell plus continuous source-percentile diagnostics and descriptive p75-p90, p90-p95, and p95+ slices. These slices are evaluation summaries only and are not candidate tiers.

## Promotion gates

A candidate can earn research authority only if all are true on frozen 2014-2020 before holdout:
1. Full-cell CRPS gain (D1 minus candidate) is positive in early, mid, and validation and the pooled two-way player/season bootstrap 95% interval is above zero.
2. Four-region Brier improves pooled and does not worsen in more than one chronology block; pooled two-way bootstrap 95% interval for Brier gain must be above zero.
3. In p95+ Y3, the sum of absolute calibration errors for productive-survivor mass and downside mass must improve by at least 0.05 versus D1. Neither historically observed tail may be suppressed by more than 0.05 absolute probability relative to its observed mass.
4. Source_percentile <0.90 no-harm: pooled CRPS degradation cannot exceed 1.0 raw point and cannot have a two-way bootstrap 95% interval wholly below zero.
5. D1 expected-point MAE must reproduce to <=1e-8; this confirms the candidate changed distribution shape rather than central expectation.
6. Y2 is an independent no-harm control. It is not promoted in this stage; pooled Y2 CRPS degradation cannot exceed 1.0 point and its 95% interval cannot be wholly below zero.
7. Candidate support must be auditable. For S2, p90+ state-row effective sample size warnings are reported; systematic ESS <10 in material state mass blocks promotion.
8. Forecast -> Simulation -> Value compatibility must be explicit: Forecast emits state probabilities plus within-state distribution metadata; Simulation samples once from that Forecast distribution; Value consumes governed expectations/distributions and adds no second collapse haircut.

If both S1 and S2 pass, prefer S1 unless S2 improves pooled Y3 CRPS by at least 0.5 additional raw point with uncertainty support, because S1 is simpler.

After the pre-holdout decision is persisted, any earned candidate is evaluated on locked 2021-2022 exactly once. It must preserve positive CRPS and four-region Brier direction, preserve the p95+ tail-calibration improvement, maintain the exact-mean/MAE guardrail, and show no Y2 harm. No retuning is allowed.

If no candidate earns pre-holdout authority, the holdout is still reported once for the required locked replication but cannot rescue or redesign a failed candidate.
