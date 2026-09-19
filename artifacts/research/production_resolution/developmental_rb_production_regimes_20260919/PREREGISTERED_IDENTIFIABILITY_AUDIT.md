# FSFFL NEXT - Developmental RB sustainable-breakout identifiability preregistration

Research only. This audit is authorized only because source-magnitude structure is real while the preregistered magnitude-only candidates are not yet sufficient for authority. It is frozen before inspecting additional ex-ante feature associations and before any locked 2021-2022 evaluation.

## Cohort and outcome

Primary cohort: developmental RB source_percentile >= 0.90, source seasons 2014-2020, Y3.

Outcome classes:
- productive survivor: target remains active and target_points/source_points >= 0.70
- major decline: target is out OR active retention < 0.40
- middle: active retention in [0.40, 0.70); excluded from the binary identifiability fit but fully reported

These thresholds are descriptive research labels only, not production tiers or decision thresholds.

## Baseline information already represented

The baseline comparison includes point-in-time source magnitude and already-governed D1 information: log source points, source percentile, dpts, age, experience, prior1 production / coverage, prior2 age-state residual mean / gap / coverage, and source state.

No family earns incremental identifiability merely by reproducing information already present in these variables.

## Eligible additional point-in-time families

Only fields recoverable from the frozen Phase-2 player-season panel are eligible:
1. Source-season role / opportunity: opportunity_per_game and governed role_band.
2. Workload mix / efficiency: RB carries, targets, receptions, target share of carries+targets, and fantasy points per opportunity where denominator is positive.
3. Availability / durability: source-season games.
4. Prior role / opportunity stability: prior-season opportunity_per_game, prior games, and change in opportunity_per_game when genuine prior coverage exists.

Draft capital / prospect pedigree, contracts, future role, later injuries, retrospective labels, and any current-player information are excluded because they are not in the frozen governed coordinate for this stage.

## Identifiability test

Use regularized logistic regression with training-only standardization and fixed L2 regularization (C=0.25), no hyperparameter sweep.

Chronological tests:
- early -> mid: train 2014-2016, test 2017-2018
- early+mid -> validation: train 2014-2018, test 2019-2020
- leave-one-source-season-out pooled diagnostic

Report AUC, Brier, log loss, coefficient sign stability, coverage, and sample sizes. The baseline model is compared with each additional family separately and with one union model only if at least two individual families show the same stable incremental direction.

A feature family passes the identifiability gate only if:
- it improves Brier and log loss over baseline in both chronological tests;
- AUC does not fall in either test and improves by at least 0.05 in one;
- the main effect direction is stable;
- coverage is >=80% of the eligible binary-outcome cohort without retrospective imputation;
- and the improvement is not driven by one source season under leave-one-season-out influence checks.

If no family passes, no richer sustainable-breakout challenger may be fit. Research moves to the uncertainty/distribution-shape conclusion. If one passes, a separate richer challenger would require a new preregistration before fitting.
