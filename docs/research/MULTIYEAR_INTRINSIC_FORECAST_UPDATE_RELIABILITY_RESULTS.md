# Multi-Year Intrinsic Forecast Update Reliability Audit Results

**Status:** research-only. Canonical workstream: draft PR #131. This document records the Forecast-update reliability audit that followed the Model A repair cycle. It does not change production Forecast behavior, production Value behavior, model authority, or production promotion status. Model B was not fitted.

## Executive conclusion

The audit does **not** support the hypothesis that historical Forecast updates broadly overreact to one new season of information.

Across 13,832 adjacent-fold same-target Forecast revisions, the current Forecast update moved toward the subsequent realized outcome 65.0% of the time, produced a revision-to-needed correlation of 0.480, and reduced revision-magnitude MAE from 44.024 under a no-update counterfactual to 37.637. That is a 14.5% improvement over simply retaining the prior fold's Forecast.

The remaining Forecast weakness is narrower: **multi-year trajectory / horizon consistency degrades as the shared target moves farther into the future.** For the nearer shared target, adjacent updates achieved 67.9% directional accuracy and 0.555 correlation. For the farther shared target, performance fell to 62.0% and 0.396. This degradation is especially relevant because Model A's remaining appreciation/decline failure is driven by changes in overlapping multi-year Forecast paths rather than by the quality of the immediate one-year update alone.

Two evidence-based scalar update repairs were tested chronologically and both were rejected:

1. a pooled/position-specific shrinkage challenger; and
2. a position-by-shared-horizon gain calibration that could amplify or damp updates depending on prior resolved evidence.

Neither improved out-of-time Forecast-update reliability. The gain challenger slightly worsened revision error, elite-QB update correlation, elite-QB longevity, and appreciation/decline correlation. Therefore **no Forecast recalibration is accepted from this cycle**.

Model A remains at 4/6 economic-usefulness checks and does not clear the frozen promotion gate. No Value-only residual has yet been isolated strongly enough to justify fitting Model B.

## Research state and guardrails

At the final audit rerun:

- `main`: `f38e2f029a0d9563986635012336434a3f9beb63`
- PR #131 research head used for the successful final audit: `b04489dc5ca4d2a3ef50cfce198da6064ff90443`
- successful research workflow run: `34721828616`
- successful research artifact: `10306417424`
- repository validation: 1,153 tests passed; 2 unrelated deprecation warnings

Guardrails retained throughout:

- Forecast owns football trajectory, development/decline, survival/attrition, and football uncertainty.
- Value owns intrinsic economics; Value was not patched to compensate for Forecast behavior.
- `marginal_lineup_opportunity` remained the context-valid replacement formulation.
- Model A's Value construction and fixed research weights were not changed.
- Market Value was not a Forecast or intrinsic training target.
- Team-specific need remained outside Forecast and intrinsic Value.
- Survival remained Forecast-owned and was not double-counted.
- All tested update parameters were estimated only from resolved pre-cutoff evidence.
- No through-2025 calibration was applied backward.
- No Model B was fitted.
- No production behavior or authority changed.

## Audit design

For each adjacent chronological fold T -> T+1, the audit compared forecasts for the **same future season** before and after one new season of point-in-time information became available:

- old fold Year 2 versus new fold Year 1; and
- old fold Year 3 versus new fold Year 2.

Each revision was scored against the subsequently realized outcome for that same target season. The row-level audit retained provenance and decomposed the transition information available at each cutoff, including:

- new realized production information;
- age and experience progression;
- production-quartile / cohort movement;
- conditional production multiplier;
- survival probability;
- Forecast dispersion and uncertainty;
- empirical cell versus parent fallback status;
- cohort/cell change;
- rookie/young/veteran state;
- prior-season improving/declining production;
- position, age band, career stage, production tier, uncertainty band, and survival-risk band.

The audit used the same historical player universe and fold-local calibration discipline as the PR #131 benchmark. The production-tier reporting bands were aligned to the historical source representation: observed source states are quartile midpoint percentiles, so audit tiers use >=0.75 for elite-tail, 0.25-0.75 for middle, and <0.25 for replacement-tail. This is an audit-reporting correction only; it does not change Forecast or Value behavior.

## Baseline adjacent-fold reliability

Across 13,832 adjacent-fold revisions:

| Metric | Current Forecast update |
|---|---:|
| Directional accuracy | 64.96% |
| Revision-to-needed correlation | 0.4801 |
| Revision-magnitude MAE | 37.637 |
| No-update magnitude MAE | 44.024 |
| Relative error improvement vs no update | 14.51% |
| Absolute-error improvement rate | 58.84% |

Classification of the current updates:

- right direction but too small: 7,150;
- right direction but too large: 1,835;
- wrong direction: 4,847.

The dominant failure mode is therefore **not generic overreaction**. Among directionally correct updates, under-sized revisions are much more common than oversized revisions.

## Horizon consistency is the clearest weakness

The update signal deteriorates as the common target moves farther into the future:

| Shared target | N | Direction | Correlation | Revision MAE | No-update MAE | Improvement |
|---|---:|---:|---:|---:|---:|---:|
| nearer shared year | 6,916 | 67.93% | 0.5547 | 36.205 | 44.864 | 19.30% |
| farther shared year | 6,916 | 61.99% | 0.3960 | 39.069 | 43.183 | 9.53% |

This is the most important substantive result of the audit. New information is useful, but its incorporation into the recursively propagated multi-year trajectory is less reliable in the farther shared year.

The aggregate absolute magnitude of farther-horizon revisions is also materially smaller than the subsequent movement needed from the prior forecast. Approximate revision/needed absolute-magnitude ratios for the farther shared year were:

- QB: ~46%;
- RB: ~43%;
- WR: ~40%;
- TE: ~40%.

That pattern is consistent with **underreaction / insufficient persistence of new information into deeper trajectory years**, but the scalar-gain challenger described below did not validate as an adequate repair. The problem is therefore more likely trajectory-shape/horizon-consistency than a single missing multiplier.

## Position and career-stage diagnostics

All four positions benefit from updating relative to leaving the prior forecast untouched:

| Position | Direction | Correlation | Revision MAE | No-update MAE | Improvement |
|---|---:|---:|---:|---:|---:|
| QB | 67.28% | 0.4932 | 79.543 | 94.145 | 15.51% |
| RB | 64.33% | 0.4681 | 34.378 | 39.673 | 13.35% |
| WR | 64.74% | 0.4415 | 34.029 | 39.970 | 14.86% |
| TE | 64.85% | 0.4660 | 22.966 | 26.691 | 13.96% |

The update process is especially useful for early-career players:

- rookie / Year-2: 69.78% directional accuracy, 0.643 correlation, 24.0% magnitude-error improvement versus no update;
- young: 66.03%, 0.483, 14.8% improvement;
- prime: 64.20%, 0.472, 14.6% improvement;
- veteran: 62.64%, 0.424, 9.7% improvement.

This does not support a blanket claim that young breakouts are systematically ignored. New information is incorporated most effectively for the youngest group, although deeper-horizon persistence remains a separate issue.

## Production-tier diagnostics

With quartile-aligned audit tiers:

- elite tail: 75.02% direction, 0.408 correlation, 21.8% improvement over no update;
- middle: 57.80% direction, 0.358 correlation, only 2.8% improvement;
- replacement tail: 68.50% direction, 0.220 correlation, 22.7% improvement.

The broadest weak subgroup is therefore the **middle tier**, where updates add little magnitude-error improvement even though they remain somewhat directionally informative. This is a more defensible concern than an unsupported claim of universal overreaction.

## Improving versus declining prior production

- after improving production: 65.34% direction, 0.503 correlation, 18.4% magnitude-error improvement;
- after declining production: 64.67% direction, 0.382 correlation, 10.3% improvement.

The audit does not show that one strong season universally causes excessive upward revision. In fact, revisions following improving seasons are more informative than revisions following declining seasons.

## Cohort and fallback behavior

- cohort/cell changes occurred in 54.5% of adjacent comparisons;
- fallback-status changes occurred in only 3.8%.

Fallback transitions were **not** the primary source of instability. Rows with a fallback-status change had 68.36% directional accuracy and 0.611 correlation versus 64.82% and 0.472 when fallback status did not change. They also improved magnitude error by 19.6% versus 14.3%.

Accordingly, the evidence does not justify stabilizing or suppressing fallback changes merely because they create a discontinuity. A more targeted future audit may examine particular cohort transitions, but no fallback repair is supported here.

## Survival and uncertainty

Survival calibration did not show a material adjacent-fold defect:

- old-fold survival Brier: 0.2211;
- new-fold survival Brier: 0.2208.

The new fold is marginally better. No survival-specific correction was justified.

For the same future targets, raw Forecast nominal-80% interval coverage rose from 60.1% under the old fold to 71.7% under the newly informed fold. The direct Forecast intervals remain below nominal in this same-target audit, but the downstream Model A uncertainty system already uses the separate rolling point-in-time residual calibration established in the prior repair cycle and remains inside its frozen gate. This cycle therefore did not alter Forecast SDs merely to force a coverage target.

One subgroup warrants future investigation: the audit's medium relative-uncertainty band performed worse than leaving the old forecast untouched, while the much larger high-relative-uncertainty group improved materially. That is not enough evidence to introduce a separate uncertainty rule in this cycle.

## Elite-QB audit

Elite QBs do **not** show evidence of simple one-season overreaction.

Across 468 adjacent elite-QB revisions:

- directional accuracy: 80.98%;
- revision-to-needed correlation: 0.4655;
- revision-magnitude MAE: 109.140 versus 151.598 with no update;
- magnitude-error improvement versus no update: 28.0%.

By shared horizon:

- nearer shared year: 85.4% direction, 0.458 correlation; update magnitude was roughly 57% of needed movement;
- farther shared year: 76.1% direction, 0.477 correlation; update magnitude was roughly 42% of needed movement.

Thus the context-valid Model A elite-QB longevity failure is not explained by elite QBs reacting in the wrong direction to ordinary annual noise. The direct update direction is very strong. The remaining issue is more consistent with how elite-QB information persists and ranks across the full multi-year path, especially deeper horizons, together with the context-valid replacement baseline.

No QB bonus was introduced.

## Rejected repair challenger 1: generic / position shrinkage

The first repair challenger estimated a partial-update coefficient from already-resolved prior folds, using position-specific estimates only after the existing 100-observation evidence threshold and otherwise pooling evidence.

It was rejected.

The direct update direction stayed unchanged, while correlation and magnitude error worsened. The same challenger also worsened elite-QB longevity and did not repair appreciation/decline. This rules out the simple explanation that Forecast updates merely need broad damping.

## Rejected repair challenger 2: position x shared-horizon gain calibration

Because the audit showed deeper-horizon underreaction, a second challenger allowed the update magnitude to be either damped or amplified:

`repaired = old forecast + gain * (new forecast - old forecast)`

Each gain was estimated chronologically from **resolved earlier revisions only**, with a position x shared-horizon cell used after the same 100-observation sufficiency floor and hierarchical fallback otherwise. No arbitrary upper cap was imposed; gains greater than 1 were permitted when prior evidence supported underreaction.

Final-fold estimates illustrate that the evidence is heterogeneous rather than a universal shrinkage problem:

| Position | Nearer shared year | Farther shared year |
|---|---:|---:|
| QB | 0.958 | 0.788 |
| RB | 0.921 | 1.158 |
| WR | 1.017 | 1.135 |
| TE | 1.004 | 1.221 |

However, the frozen out-of-time evaluation rejected this challenger:

| Forecast-update metric | Baseline | Gain challenger |
|---|---:|---:|
| Directional accuracy | 64.96% | 64.96% |
| Revision-to-needed correlation | 0.4801 | 0.4750 |
| Revision-magnitude MAE | 37.637 | 37.779 |
| Absolute-error improvement rate | 58.84% | 58.63% |

Elite-QB direct update correlation also fell from 0.4655 to approximately 0.442 under the challenger.

Because the repair worsened the direct out-of-time target it was designed to fix, it is not accepted despite being chronologically estimated.

## Model A retest with unchanged economics

The position x horizon challenger was also passed through the unchanged Model A economics as a downstream falsification test.

| Metric | Pre-audit context-valid Model A | Forecast gain challenger |
|---|---:|---:|
| Model A MAE | 20.307 | 20.296 |
| comparable affine MAE | 26.968 | 27.016 |
| relative MAE improvement | 24.7% | 24.9% |
| calibrated nominal-80% coverage | 87.3% | 87.2% |
| elite-QB longevity correlation | 0.1948 | 0.1661 |
| appreciation/decline direction | 44.60% | 44.80% |
| appreciation/decline correlation | -0.2689 | -0.2790 |
| economic checks passed | 4/6 | 4/6 |
| market independence | PASS | PASS |
| frozen promotion gate | NOT CLEARED | NOT CLEARED |

The negligible MAE improvement is not sufficient reason to retain a Forecast repair that worsens its direct calibration target and both unresolved economic signals. The challenger is therefore research evidence only, not an accepted Forecast change.

Under the challenger, Superflex/1QB structural scarcity still passed 17/17 folds, with mean QB relative gain about 29.79 and negligible non-QB movement. Market independence also remained healthy: Spearman correlation with market was about 0.649 and material disagreement remained about 38.9% across the available market-history folds.

## Accepted Forecast repair from this cycle

**None.**

This is an important positive research result. The audit found a real reliability pattern but neither tested scalar correction passed chronological validation. No arbitrary damping, QB longevity premium, position bonus, or downstream Value compensation should be introduced.

## What was actually wrong?

The strongest supported diagnosis is:

> Forecast updates are broadly useful and usually directionally sensible, but the reliability and persistence of new information degrade across the recursively generated multi-year trajectory, especially in the farther shared year. This is a horizon-consistency / trajectory-shape problem, not a broad one-season overreaction problem.

The audit also shows that:

- survival updating is not the primary defect;
- fallback changes are not the primary defect;
- fixed Model A annual weights are not the primary defect—the prior equal-weight sensitivity only modestly improved the failing signal;
- replacement movement is not the primary appreciation problem—the prior decomposition worsened when replacement movement was removed;
- elite QBs are not simply being revised in the wrong direction after noisy seasons.

## Narrowest remaining authoritative cause

The narrowest remaining authoritative issue is still inside **Forecast**, but it is now more specific than "Forecast updating":

**multi-year recursive trajectory-shape / horizon-consistency calibration.**

A next Forecast research step, if pursued, should compare the shape of the full path generated at T and T+1 rather than multiplying the observed adjacent revision by a scalar. It should ask whether the conditional transition process carries newly learned player information too weakly or inconsistently into Year 2 / Year 3 and whether that differs by career stage, production tier, and elite-QB lifecycle state.

That work should preserve the same chronological discipline and directly test path-shape features before considering any production change.

## Does the residual now justify Model B?

**No.**

There may still be a stable elite-tail Value residual, as noted in the prior Model A repair report, but this audit has not isolated it from the remaining Forecast trajectory-shape problem. Because the downstream appreciation/decline failure is still strongly associated with Forecast-path updates and the elite-QB longevity signal worsens under the tested scalar Forecast repairs, fitting a nonlinear Value Model B now would risk teaching Value to compensate for unresolved Forecast path behavior.

The correct research state remains:

1. Model A retains a material raw predictive advantage over the affine control;
2. context-valid scarcity and uncertainty are repaired and passing;
3. Forecast updates are useful, not broadly overreactive;
4. a deeper-horizon trajectory consistency issue remains;
5. no scalar Forecast repair passed validation;
6. economic usefulness remains 4/6;
7. Model A does not clear the frozen production-promotion gate;
8. Model B remains premature;
9. no production promotion is recommended from this cycle.
