# FSFFL NEXT - Developmental RB production-regime / nonlinear preregistration

Research only. This preregistration is frozen before either candidate is fit and before locked 2021-2022 is inspected in this stage. P0/D1 remains the production control. PR #147, main, production code, P0 authority, Value, Intrinsic, Shapley, Simulation, league scoring, and deployment are out of scope.

## Pre-candidate diagnosis used to justify the bounded forms

Using only frozen 2014-2020 developmental-RB rows and the exact season-relative source-percentile coordinate:
- Active Y3 absolute future points show clear nonlinearity versus source magnitude. A one-knot continuous segmented regression beats a single linear slope by BIC for every tested knot from p75 through p95; pooled BIC is best at p90.
- The p90 knot is also the leave-one-source-season-out best knot in 6 of 7 years. In a two-way player/season weighted bootstrap over the finite diagnostic grid {p75,p80,p85,p90,p95}, p90 is the plurality choice (953/2000); p85=386, p95=327, p75=271, p80=63. This is evidence of a high-end slope change but also nontrivial boundary uncertainty.
- Y3 p90+ rows have materially higher absolute future production and persistence than p75-p90 rows; however realized retention is noisy and does not support treating the old diagnostic 225.5-point boundary as a production tier.
- Within active p90+ Y3 rows, dpts is not reliably negative after conditioning on log source points; therefore the prior global negative spike penalty is not independently justified inside the exceptional-magnitude region.

The old 154.1-188.9 / 189.4-225.5 / >225.5 diagnostic bands are not reused as model tiers.

## Candidate A - D1T90 discrete regime

D1T90 is identical to the frozen D1 state-conditional production model except for exactly one extra binary feature in the production layer:
  rb_dev_p90 = 1 when position=RB, career_stage=developmental, and source_percentile>=0.90; else 0.

- Same raw future-point target, training rows, BayesianRidge family/hyperparameters, scalers, base D1 features, future-state conditioning, prior-history features, chronology, and pooling as D1.
- State/persistence probabilities remain exactly frozen to the authoritative historical D1/P0 prediction artifact.
- The binary feature is a single additive production-regime shift; there are no state-specific regime coefficients, no dpts override, no floor/cap, and no current-player input.
- The p90 boundary is season-relative and point-in-time. It is not optimized during candidate fitting.

## Candidate B - D1H90 continuous nonlinear

D1H90 is identical to D1 except for exactly one extra continuous production-layer feature:
  rb_dev_hinge90 = max(0, (source_percentile - 0.90) / 0.10)
for developmental RB rows; 0 otherwise.

This creates a continuous change in source-magnitude slope above p90 without a discontinuous tier jump. All other restrictions are identical to D1T90. The knot is fixed at p90 before fitting and is not optimized.

## Evaluation chronology

Development / promotion evidence: source seasons 2014-2020 only.
Chronological reporting blocks: early 2014-2016, mid 2017-2018, validation 2019-2020.
Locked replication: 2021-2022 exactly once, only after the pre-holdout decision is persisted.
No candidate is revised after holdout.

## Primary scores and gates

For each horizon, D1 is the control. Candidate predictive distributions use the frozen six-state probabilities and their candidate state-conditional point masses.

A candidate can earn developmental-RB research authority only if all are true before holdout:
1. Full developmental-RB raw-point CRPS gain (D1 minus candidate) is positive in early, mid, and validation and the pooled two-way player/season bootstrap 95% CI is above zero.
2. Ordinary expected-point MAE does not materially/significantly degrade: pooled MAE gain is >= -1.0 point and its two-way bootstrap 95% interval is not wholly below zero.
3. Y3 p90+ active conditional-production bias is materially reduced: mean candidate minus realized retention bias moves at least 0.05 toward zero relative to D1, without crossing above +0.05.
4. Developmental-RB source-percentile <0.90 is a no-harm control: pooled CRPS degradation may not exceed 1.0 point and may not have a 95% interval wholly below zero.
5. State/persistence calibration is identical by construction; collapse/downside probability may not be suppressed.
6. Temporal stability: all three frozen blocks must have the same CRPS direction. D1T90 additionally cannot be promoted if the p90 boundary evidence is contradicted by leave-one-season-out influence analysis.
7. Y2 is an independent no-harm/control horizon and changes only if it independently clears the same CRPS/MAE/no-harm gates plus a horizon-specific bias improvement; the Y3 retention-bias gate cannot force a Y2 change.
8. If both candidates pass, prefer D1H90 unless D1T90 has materially better pooled CRPS by at least 0.5 points with uncertainty support, because the directive prefers the continuous representation when it performs as well or better with less boundary fragility.

After the pre-holdout decision is frozen, an earned candidate must preserve positive full-cell CRPS direction on locked 2021-2022, satisfy the MAE guardrail, and not reverse the Y3 p90+ bias improvement. If no candidate earns pre-holdout authority, holdout cannot rescue it.

No richer ex-ante signal candidate may be fit unless source-magnitude structure proves real but these two magnitude-only candidates are insufficient and the separate identifiability gate is passed.
