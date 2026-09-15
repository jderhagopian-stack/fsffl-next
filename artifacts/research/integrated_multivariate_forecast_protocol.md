# FSFFL NEXT - Integrated Multivariate Forecast Research Protocol

Status: FROZEN BEFORE FINAL HOLDOUT RESULTS
Authority: research only; management directive dated 2026-09-15
Base research state: PR #145 head `f19b197e7650813062bd2dcb7b13eb18cb2b16ca`
Production main at study start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`

## 1. Locked boundaries

This study is Forecast-only. It does not change Intrinsic Constitution, B4 holding governance, frozen Shapley/W, Value authority, Team Utility, Simulation, Decision, Search, market inputs, owner behavior, trades, fantasy ownership, or production authority. Shapley/Value outputs cannot select or tune Forecast. No named-player tuning. No future breakout/return/status information may enter predictors.

## 2. Primary question

Which smallest defensible integrated multivariate Forecast architecture gives the strongest strict point-in-time out-of-sample probability forecasts from already-governed football evidence while preserving source-agnostic semantics and safety?

## 3. Canonical provider-neutral evidence contract

Only canonical football facts may enter model features. Provider adapters may supply them, but raw provider codes cannot enter model matrices.

Allowed families:
- identity/context: position, age band, experience band, rookie/career-stage indicator, horizon;
- production: current fantasy production, prior-season production when chronologically present, production change/trajectory, current governed production state;
- role/opportunity: games, pass attempts / carries / targets / receptions as position-appropriate, opportunity per game, role band, participation/snap trend where governably mapped;
- organizational attachment: active share, released share, practice/reserve share, last active/attached/released/practice/reserve facts;
- churn/transitions: status-transition count, active-return count, release-entry count, practice-entry count, reserve-entry count, team-change count;
- availability: injury-limited weeks, non-IR injury-limited weeks/flag, inactive-injury weeks/flag, reserve-injury weeks;
- evidence coverage: roster/availability/usage/participation coverage flags.

Missing evidence never means healthy, retained, released, or dead. It triggers explicit coverage features and/or fallback.

## 4. PIT target semantics

Primary target is the factual horizon-specific career state used by PR #145:
- if a chronologically observed target-season production row exists, map realized production into governed state boundaries;
- if no production row exists but target-season football-state evidence establishes continued organizational attachment, target is persistence with `depth` state;
- if target-season football-state evidence establishes retirement or non-persistence, target is `out`;
- unresolved target evidence remains unresolved and is excluded from primary factual-state loss while retained in coverage diagnostics.

Legacy production-panel state remains a secondary comparability diagnostic only.

Anticipated-production target is realized target-season fantasy production (zero when factual target is `out`; observed points when a production row exists; unavailable for attached-but-no-production cases unless the factual outcome is zero-production depth by contract). No future information is used as a predictor.

## 5. Frozen candidate set

Controls:
- **B0 - Existing baseline:** current C0 / governed historical transition estimator.
- **B1 - PR #145 persistence-first control:** frozen M2 predictions from PR #145, no retuning.

Integrated candidates:
- **I1 - Structured two-stage ordered-state model.** Stage 1: regularized logistic persistence model using the full canonical evidence set. Stage 2: conditional-on-persistence ordered threshold models for `usable+`, `starter+`, `premium+`, `elite`, converted into coherent `depth/usable/starter/premium/elite` probabilities. Final probabilities are `P(out)=1-P(persist)` and `P(state)=P(persist)*P(state|persist)`.
- **I2 - Direct regularized multinomial career-state model.** One L2-regularized multinomial model directly estimates `out/depth/usable/starter/premium/elite` from the same canonical evidence set. This is the main architectural contrast to I1.

No additional model family may be created after final holdout results are visible without new management authorization.

## 6. Anticipated production

For I1 and I2, expected fantasy production is integrated with predicted career-state probabilities via chronologically fitted position x horizon x realized-state mean production coordinates. Means are estimated only from each training window, with position/horizon then global-state fallback. This is not a blanket low-end haircut and does not use Shapley or market values.

## 7. Model form and regularization

All learned probability models use transparent L2-regularized logistic regression with deterministic feature vectorization. Candidate regularization is selected only from `C in {0.25, 1.0, 4.0}` using the development/validation period. No AutoML or wider hyperparameter search. If a class is unsupported, the model falls back fail-closed to the next governed level rather than fabricating a probability.

## 8. Chronology and final holdout

Evidence era: source seasons 2012-2022 where one- and two-year factual targets can be resolved through 2024.

Development/tuning chronology:
- development folds: source seasons 2014-2018;
- validation folds for choosing fixed `C`: 2019-2020;
- final untouched holdout: source seasons 2021-2022.

For every scored fold, all model fitting, state boundaries, state-production coordinates, calibration quantities, and priors use only source/target information strictly earlier than that fold cutoff. The final holdout is not used to choose candidate family, features, thresholds, regularization, or selection rules.

## 9. Fail-closed fallback hierarchy

1. full canonical evidence model when support/coverage is sufficient;
2. reduced canonical evidence model using production/context/usage without rich roster/availability facts;
3. position/age/current-state/horizon empirical prior trained chronologically;
4. B0 broad fallback.

Every prediction records the path used. Early eras/positions are never silently dropped.

## 10. Predeclared metrics

Calibration:
- persistence/non-persistence Brier and log loss;
- state Brier and state log loss;
- useful/starter/premium Brier;
- calibration bins and mean predicted vs realized rates.

Discrimination:
- non-persistence AUROC;
- useful/starter/premium AUROC where both classes exist;
- rank correlation for anticipated production.

Development balance:
- true-developmental recall at frozen useful-probability threshold 0.50;
- breakout false-negative share;
- false-positive developmental optimism.

State/production quality:
- conditional positive-state Brier/log loss;
- anticipated-production MAE and bias overall, low-end, true-developmental, ordinary useful, premium/elite.

Safety:
- later-return;
- non-IR injury;
- reserve/practice;
- active-roster/no-production.

Robustness:
- QB/RB/WR/TE;
- age/experience bands;
- early/middle/recent era;
- evidence coverage and fallback path.

Architecture/governance:
- PIT leakage audit;
- source-agnostic schema audit;
- market/Value/Shapley isolation;
- reproducibility.

## 11. Holistic selection framework

Selection is not controlled by any single legacy threshold.

Mandatory rejection conditions:
- any future leakage or market/owner/Value/Shapley feedback;
- provider-specific raw-code dependence in model semantics;
- incoherent probabilities;
- a clearly material safety failure that systematically treats temporary injury/reserve/return as permanent disappearance;
- a catastrophic position/era failure hidden by aggregate metrics.

Otherwise:
1. Prefer strict Pareto dominance across calibration, discrimination, development balance, state quality/production, safety, and robustness.
2. If no candidate dominates, compare equal-weight dimension ranks across those six performance dimensions; architecture/governance is mandatory pass/fail, not a compensating score.
3. A candidate may be selected with a documented tradeoff only if no safety-critical regression is material, its advantage is replicated across more than one holdout dimension, and it is not dependent on one position/era/fallback stratum.
4. If integrated candidates are not materially better than B0/B1 holistically, stop with NO PROMOTABLE CANDIDATE.

## 12. Post-selection diagnostics

Only after the leading Forecast candidate is selected/frozen from the final holdout:
- bounded evidence-family ablation (production/context; role; organizational continuity/churn; availability; participation) on the selected architecture;
- controlled sensitivity to age, production, continuity, injury/availability, and role evidence;
- provider-dependence audit.

Ablation may explain the selected model but cannot retroactively choose another winner after seeing holdout results.

## 13. Downstream Intrinsic authorization

Only if the final Forecast status is `PROMOTABLE FOR MANAGEMENT REVIEW` may the workstream run frozen 2048-permutation Shapley and the locked 10-point Intrinsic Constitution. Forecast selection must already be frozen. Shapley cannot select or tune Forecast.

## 14. Final status vocabulary

Return exactly one management status:
- `PROMOTABLE FOR MANAGEMENT REVIEW`;
- `NO PROMOTABLE CANDIDATE`;
- `BLOCKED BY A SPECIFIC DEFECT`.

No merge or production promotion occurs in this workstream.