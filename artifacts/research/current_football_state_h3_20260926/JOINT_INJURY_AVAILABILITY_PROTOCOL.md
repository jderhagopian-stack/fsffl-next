# Joint Injury-Availability Follow-up Protocol

Date: 2026-09-27  
State: **FROZEN BEFORE JOINT SCORING / FOLLOW-UP COMPARATIVE VALIDATION / RESEARCH ONLY**

## Purpose

Test one coherent injury-availability architecture that produces both:
1. return-time probabilities/distribution; and
2. expected remaining-season availability,

while preserving the already-supported separate remaining-availability benchmark and all existing authority boundaries.

This is a **post-result follow-up comparative validation**. The 2019-2024 holdouts have already been observed in the separate-model study, so this is not represented as a pristine untouched final holdout and cannot by itself authorize production promotion.

## Frozen historical population

- exact governed injury episode population: **4,793 episodes**;
- episode seasons: 2012-2024;
- scored outer holdouts: 2019, 2020, 2021, 2022, 2023, 2024;
- use the same episode definitions, severity labels, injury-family derivation, structural calendar rules, target bounding, and structurally-inconsistent return exclusions as the completed separate-model study;
- PIT-only information set.

No episode or label definitions may be changed after scoring.

## Joint architecture: availability_latent_hazard

One shared architecture is frozen:

### Stage A — shared availability latent
For each outer origin T:
- fit the exact previously-supported HistGradientBoosting remaining-availability architecture using only seasons < T;
- fixed PIT inputs: position, contemporaneous severity, broad injury family, event week, structural weeks remaining, pre-event fantasy points per active game, pre-event opportunity per active game, age, NFL experience;
- fixed model settings: learning_rate=0.05, max_iter=180, max_leaf_nodes=15, l2_regularization=3.0, min_samples_leaf=30, random_state=20260927;
- its bounded [0,1] prediction is the joint system's remaining-season availability output and the scalar **shared availability latent** used by Stage B.

### Stage B — return-hazard head conditioned on the shared latent
The return-time head is a discrete weekly hazard model. It may use only:
- shared availability latent from Stage A;
- position;
- contemporaneous severity;
- broad injury family;
- event week;
- structural weeks remaining;
- delay/week-ahead.

It may **not** directly re-read pre-event production, opportunity, age, or experience; those features can affect return timing only through the shared Stage-A latent.

Fixed return head:
- HistGradientBoostingClassifier;
- learning_rate=0.06;
- max_iter=160;
- max_leaf_nodes=15;
- l2_regularization=3.0;
- min_samples_leaf=30;
- random_state=20260927.

The hazard sequence is converted to cumulative return probabilities using the same survival-product derivation as the separate-model study.

### Nested chronology for the shared latent
The Stage-B training rows must use chronology-preserving out-of-fold Stage-A latent scores:
- for inner season S, fit Stage A only on seasons < S and score season S;
- use only such prior-season scores to train the outer-origin return head;
- no same-row outcome-fitted latent may be used in Stage-B training;
- no future outer-holdout season may enter fitting, preprocessing, calibration, imputation, category handling, or threshold selection.

At outer evaluation season T:
- Stage A is fit on all seasons < T and scores T;
- Stage B is fit only on valid inner chronology-preserving latent rows from seasons < T.

## Targets

### Remaining-season availability
Same bounded [0,1] target as the separate-model study.

### Return timing
Same first active-game return target and right-censoring semantics as the separate-model study:
- cumulative return by 1, 2, 3, 4 weeks;
- probability of any same-season return;
- integrated Brier over structurally possible delay thresholds.

Rows previously classified as structurally inconsistent return timing remain excluded from return-time fitting/scoring, not relabeled.

## Frozen comparators

Direct benchmark evidence is the already-scored separate-model artifact from workflow run `36323231951` / artifact `10933510516`:
- severity-only return and availability baselines;
- selected separate HistGradientBoosting remaining-availability model;
- unpromoted separate HistGradientBoosting return-time challenger.

The joint study must compare to those exact predictions/metrics. It may not recompute a friendlier comparator after seeing the joint score.

## Leakage prohibitions

Prohibited:
- post-event role or production;
- recurrence/reinjury flags or later injuries;
- future roster state;
- provider revisions;
- Market, Owner, Team Utility, fantasy transactions;
- named-player tuning;
- current-season named-player manual overrides.

## Authority guards

This study may not change:
- conditional healthy production;
- post-return role/opportunity;
- recurrence/durable H2/H3 effects;
- production H3;
- Intrinsic;
- current provider ROS authority;
- the no-double-counting rule.

If the joint candidate fails any frozen gate, retain the separate supported remaining-availability model and leave time-to-return unpromoted.
