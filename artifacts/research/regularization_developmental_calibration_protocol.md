# FSFFL NEXT — Regularization Stability & Developmental Calibration Protocol

Status: FROZEN BEFORE NEW CALIBRATION RESULTS
Authority: research only; management directive dated 2026-09-15
Research base: PR #146 head `c12402df1b7fa0bfbb3d994bdcf791d80e103a0c`
Production main observed at study start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
Active implementation PR at study start: #147, branch `implementation/forecast-intrinsic-i1-shapley`, observed head `5792e532db8fc39c70a0a5240f1df3e8b1718589`

## 1. Scope and authority

This is a bounded calibration study inside the already-selected I1 Forecast architecture. It does not reopen Forecast model-family selection and does not modify production authority.

Locked outside this workstream:
- Intrinsic Constitution;
- B4 holding-right governance;
- frozen Shapley game W and discounting;
- Broad Market / League Market / Team Utility / Decision / Search / Simulation;
- owner behavior, trade behavior, fantasy ownership or market coordinates;
- named-player tuning;
- new feature families, AutoML or open-ended hyperparameter search.

PR #147 is read-only from this workstream. No production or implementation branch may be modified, rebased, merged or deployed here.

## 2. Phase A implementation map — frozen before experiments

The selected I1 research implementation in `scripts/run_integrated_multivariate_forecast.py` uses scikit-learn `LogisticRegression` through a `DictVectorizer` feature matrix.

For I1:
- one regularized binary logistic model estimates persistence;
- four regularized binary logistic models estimate conditional ordered thresholds: useful+, starter+, premium+, elite;
- the four conditional probabilities are monotonically clamped and converted into depth/usable/starter/premium/elite masses;
- final state probabilities multiply the conditional positive-state mass by the persistence probability;
- anticipated production is the state-probability-weighted chronological state-mean coordinate.

Current explicit estimator settings:
- `C`: supplied identically to persistence and all four ordered threshold models;
- solver: `lbfgs`;
- max iterations: `2000`;
- random state: `20260915`;
- minimum training rows: `100`;
- minimum binary class count: `15`.

Library-default settings not overridden by I1 include L2 regularization, fitted intercept and no class weighting. There is no `StandardScaler`; categorical coordinates are one-hot encoded by `DictVectorizer` and numeric coordinates are manually transformed/scaled in the governed feature builder. There is no existing position-specific or career-stage-specific C. Rich-evidence and reduced-evidence models are separate fits but currently receive the same C.

For scikit-learn logistic regression, C is inverse regularization strength: smaller C means stronger coefficient shrinkage; larger C means less shrinkage.

The original integrated research grid was exactly `{0.25, 1.0, 4.0}`. Repository artifacts document the grid but do not provide a defensible empirical rationale for those three exact values. Both integrated candidates selected `0.25`, the smallest/most strongly regularized value allowed. This follow-up therefore treats `0.25` as provisional rather than as a proven interior optimum.

## 3. Developmental population — predeclared

The developmental prediction population is defined only from facts known at prediction time:

`developmental_candidate = low_end_current_production AND age_band == "young"`

`low_end_current_production` is the existing governed low-end threshold computed from historical information available before the prediction season. The population is not defined by future success, future survival, named players or 2026 outcomes.

Primary developmental success for this study is factual resolved target state `useful` or better. The prior legacy-production definition will be reported only as a comparability diagnostic.

The frozen usefulness decision threshold remains `P(useful+) >= 0.50`.

## 4. Historical chronology

The study will reconstruct the maximum defensible strict point-in-time history supported by the existing evidence pipeline.

Rolling-origin evaluation:
- candidate-selection / stability folds: source seasons 2014 through 2022;
- each fold trains only on rows whose required targets are known before the source-season cutoff;
- H1 and H2 are included only when the factual target is resolved under the existing source-agnostic evidence contract;
- no random cross-validation is allowed.

New final confirmation candidate:
- source season 2023, horizon 1 only, targeting 2024;
- it is excluded from all C and treatment selection;
- it may be used once after a challenger is frozen, provided the regenerated evidence resolves it defensibly;
- if it is unavailable or materially under-resolved, there is no pristine new holdout and the study must say so rather than substitute 2021-2022.

Source season 2021-2022 may appear as ordinary rolling historical folds but is not an untouched test because its results are already known.

## 5. Phase C global C grid — predeclared

I1 features, target semantics, evidence handling, estimator family and state conversion remain fixed.

Primary bounded grid:

`C ∈ {0.0625, 0.125, 0.25, 0.5, 1.0}`

This is a geometric grid centered around the provisional `0.25`, extending two steps into stronger regularization and two steps into weaker regularization without reopening broad hyperparameter optimization.

One bounded extension is preauthorized only if `0.0625` is the strongest candidate on the rolling evidence and the direction of improvement remains coherent:

`C = 0.03125`

No additional lower C values and no continuous optimization are allowed in this workstream.

### Global selection rule

`0.25` remains defensible if it lies on a broad stable plateau. Define the plateau as candidates whose aggregate factual state Brier is within 1% of the best candidate and that are not more than 1% worse than the best candidate on both factual state log loss and anticipated-production MAE.

A global change may be recommended only if all are true:
1. `0.25` falls outside the stable plateau;
2. the challenger has lower aggregate factual state Brier than `0.25`;
3. at least four of these five secondary measures are no worse than `0.25`: persistence Brier, useful+ Brier, state log loss, anticipated-production MAE, absolute anticipated-production bias;
4. the challenger wins more rolling folds than it loses versus `0.25` on factual state Brier;
5. no adequately sized position, horizon, age/career-stage or temporary-absence safety subgroup worsens by more than 3% on factual state Brier or its directly relevant safety loss.

Paired season-block bootstrap intervals will be reported for loss differences as uncertainty evidence, but no candidate will be selected from a p-value alone.

If multiple challengers satisfy the rule, prefer the broad/stable region and the smaller change from current production rather than a razor-thin optimum.

## 6. Phase D career-stage-aware treatment — predeclared

The stage-aware treatment remains recognizably I1 and changes only regularization at prediction time.

Let `Cg` be the frozen global C selected from Phase C. Fit otherwise identical I1 models over the same training evidence at:
- `Cg` (global/established path);
- `Cd = 2 × Cg`, capped at `1.0`;
- `Cd = 4 × Cg`, capped at `1.0`.

Duplicate values after capping are removed.

For a developmental-candidate row only, the stage-aware challenger may use the prediction from the less-regularized `Cd` fit. Every non-developmental row continues to use the `Cg` prediction. Both fits use the same full training population, same features, same targets and same evidence contract; there is no developmental-only bespoke model and no position-specific model family.

This design isolates the management hypothesis: slightly less coefficient shrinkage may allow real developmental patterns to survive while established-player restraint remains exactly unchanged.

### Stage-aware selection rule

Relative to the frozen global-C control, a stage-aware challenger may be recommended only if all are true on rolling selection folds:
1. it catches additional factual developmental useful+ successes at the frozen 0.50 threshold;
2. added false developmental useful+ positives do not exceed added true hits;
3. added true hits occur in at least two distinct source-season folds rather than one season only;
4. developmental useful+ Brier and developmental factual state Brier both improve;
5. overall factual state Brier and anticipated-production MAE each worsen by no more than 0.5%;
6. temporary-absence safety does not materially deteriorate.

Because non-developmental rows keep `Cg`, established-player predictions must be numerically identical by construction. Any mismatch is an implementation defect.

If the evidence is mixed, underpowered, or the extra hits are purchased mainly with false optimism, retain the global treatment.

## 7. Required diagnostics

For every global C and every stage-aware candidate report:
- total resolved rows by fold and horizon;
- developmental-candidate count and factual developmental-success count by fold;
- state Brier and state log loss;
- persistence, useful+, starter+ and premium+ Brier;
- anticipated-production MAE and bias;
- position, horizon, age/career-stage and era splits;
- temporary-absence safety cohorts already used by the integrated study;
- fallback / rich-evidence / reduced-evidence path rates;
- fold wins/losses versus `C=0.25`;
- paired season-block bootstrap uncertainty;
- developmental TP / FN / FP / TN at `P(useful+) >= 0.50`;
- incremental real hits recovered and false positives added.

Plain-English developmental translation is mandatory: “for every X additional real breakouts caught, Y additional false breakouts were created.”

## 8. Untouched confirmation protocol

Only after Phase C and Phase D selections are frozen may the source-2023/H1 confirmation rows be evaluated.

The confirmation set cannot change the candidate definitions or thresholds. It can:
- support the research challenger;
- fail to confirm it;
- be labeled too small / unresolved to decide.

A stage-aware promotion recommendation cannot rely on a confirmation cohort with fewer than 5 factual developmental successes; such a result is descriptive only.

## 9. Dispositions

Final management disposition must be exactly one of:
- `KEEP C=0.25 AS-IS`
- `CHANGE GLOBAL REGULARIZATION`
- `ADOPT CAREER-STAGE-AWARE REGULARIZATION`
- `INSUFFICIENT EVIDENCE - KEEP PROVISIONAL SETTING`

A changed setting is a research challenger only. No production implementation is authorized here.

## 10. Stop rules

Stop without expanding scope if:
- no candidate has a material repeatable advantage over provisional `C=0.25`;
- stronger developmental recall mainly restores false optimism;
- the stage-aware treatment is unstable or underpowered;
- the new confirmation set is unavailable and rolling evidence is insufficient;
- a result would require new feature families or a different model architecture to rescue it.

Do not merge anything. Return evidence to management.