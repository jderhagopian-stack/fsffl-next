# FSFFL NEXT — Comparative Y4+ Intrinsic Model-Family Research Closeout

Date: 2026-09-26  
State: **MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**  
Authority: Research only. Production H3 remains unchanged.

## Executive conclusion

Management reopened the long-horizon study to test whether the prior H5-centered conclusion had assumed too much:
- Y5 was not allowed to be a preset breakpoint;
- `two_part_state` was not allowed to be preassigned after H3;
- position-specific and horizon-specific routes were permitted only if chronological evidence justified them.

The expanded six-family study does **not** support a separate cardinal model family by position or horizon.

For the universal annual-production problem at Y4, Y5, Y6, Y7 and Y8, Research retains:

**`two_part_state` for QB, RB, WR and TE at every tested horizon.**

Promoted model-family breakpoint: **none**.

This is a model-selection conclusion, not a claim that all Y4-Y8 annual values have equal precision. Precision degrades materially with horizon, so product presentation and terminal/career semantics remain separate Management questions.

## Families compared

The frozen candidate set was:
1. `carry_y3` — simple persistence baseline;
2. `direct_ridge` — regularized direct conditional-production regression;
3. `two_part_state` — incumbent survival/relevance probability × conditional production;
4. `conditional_cohort` — age/production-cohort survival plus conditional production;
5. `survival_hazard` — purpose-built sequential survival/hazard model plus conditional production;
6. `career_state_transition` — four-state career/role transition model.

Candidate definitions, complexity penalties, route-switch penalties and holdout confirmation rules were frozen before the reopened study inspected new current-player model-sensitive ranks.

## Chronological validation

Each Y4-Y8 horizon used:
- point-in-time historical Y1-Y3 Forecast inputs;
- only football outcomes available before each evaluation fold;
- no random future-season mixing;
- no current-player outcome leakage;
- no named-player tuning.

Holdout windows were the last three target-complete base seasons available for each tested horizon.

Production H3 was not re-litigated because the post-H3 challengers explicitly use the governed Y1-Y3 Forecast path as input features. Reusing those same inputs to claim an H1-Y3 replacement would not be an independent comparable test.

## Comparative matrix result

Across the 20 position × horizon holdout cells:

| Family | Best RMSE | Best MAE | Best Spearman | Best survival Brier | Best top-decile tail RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| carry_y3 | 2 | 1 | 0 | 0 | 9 |
| direct_ridge | 0 | **17** | 3 | 0 | 0 |
| two_part_state | **14** | 1 | **8** | **14** | **11** |
| conditional_cohort | 0 | 0 | 2 | 0 | 0 |
| survival_hazard | 1 | 1 | 5 | 5 | 0 |
| career_state_transition | 3 | 0 | 2 | 1 | 0 |

No challenger dominates the incumbent multi-objectively.

### Why direct_ridge is not promoted despite MAE wins

`direct_ridge` wins MAE in 17/20 cells but RMSE in 0/20 and tail-RMSE in 0/20. It reduces typical absolute error by shrinking high-end production.

Mean top-decile RMSE:

| Horizon | two_part_state | direct_ridge |
| --- | ---: | ---: |
| Y4 | 133.74 | 165.54 |
| Y5 | 137.13 | 168.44 |
| Y6 | 133.98 | 163.79 |
| Y7 | 120.43 | 141.56 |
| Y8 | 79.28 | 93.03 |

Because Intrinsic uses lineup-capacity Shapley deployment, suppressing the upper production tail is economically material. Lower MAE alone is not sufficient.

### Why the development-routed architecture is not promoted

The frozen development selector produced:
- QB: survival_hazard Y4-Y8;
- RB: conditional_cohort Y4-Y5, direct_ridge Y6-Y8;
- WR: two_part_state Y4-Y6, direct_ridge Y7-Y8;
- TE: two_part_state Y4-Y5, direct_ridge Y6-Y8.

Paired holdout bootstrap against the incumbent showed:

| Horizon | Route−incumbent MAE | 95% CI | Route−incumbent MSE | 95% CI |
| --- | ---: | --- | ---: | --- |
| Y4 | +0.119 | [-0.014, +0.253] | +49.9 | [+22.1, +80.1] |
| Y5 | +0.022 | [-0.144, +0.184] | +46.9 | [+12.0, +86.9] |
| Y6 | -0.574 | [-1.044, -0.091] | +254.2 | [+147.9, +371.9] |
| Y7 | -1.681 | [-2.210, -1.151] | +190.0 | [+95.8, +284.7] |
| Y8 | -1.516 | [-2.002, -1.017] | +175.6 | [+86.9, +276.0] |

At Y6-Y8 the route lowers MAE but materially worsens squared error. That is a tail-compression tradeoff, not a robustly superior cardinal architecture.

## Challenger interpretation

### Survival / hazard
Most credible alternative for QB and a useful model-risk check. It sometimes improves ranking/survival calibration, but gains are small/unstable and QB Y8 is materially worse than the incumbent. Do not create a separate QB annual-cardinal route from current evidence.

### Career-state transition
Occasionally wins RMSE in sparse long-horizon cells but is weaker on MAE and often ranking. Its more defensible future role is as a **terminal/career-state lens**, not the annual cardinal points engine.

### Conditional cohort
Does not establish durable enough gains to warrant a routed role.

## Current 335-player shadows after historical freeze

Primary current shadow uses `two_part_state` at Y4-Y8 for all positions.

Production H3 comparison:
- 335/335 matched;
- H3 shadow vs persisted production H3 Spearman: **0.99654**;
- mean absolute H3 rank gap: **5.63**.

H3-to-long-horizon movement under the primary family:

| Horizon | H3 rank Spearman | Median absolute move | P90 absolute move | Move ≥10 | Move ≥20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| H4 | 0.9939 | 4 | 12 | 15.5% | 3.0% |
| H5 | 0.9857 | 7 | 19 | 36.1% | 9.3% |
| H6 | 0.9768 | 10 | 23 | 52.5% | 17.9% |
| H7 | 0.9710 | 11 | 27 | 55.8% | 23.3% |
| H8 | 0.9672 | 12 | 30 | 59.4% | 25.4% |

There is no discontinuity at Y5. Rank movement grows gradually across the horizon.

## Current model-family sensitivity

Comparing the retained primary family with the rejected development-routed sensitivity curve:

| Horizon | Rank Spearman | Median abs rank difference | P90 | Max | Top-25 overlap | Top-50 overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H4 | 0.9995 | 1 | 2.6 | 25 | 25 | 50 |
| H5 | 0.9988 | 1 | 4.0 | 35 | 25 | 49 |
| H6 | 0.9967 | 2 | 8.6 | 52 | 24 | 48 |
| H7 | 0.9954 | 3 | 10.6 | 61 | 24 | 49 |
| H8 | 0.9947 | 3 | 11.0 | 63 | 24 | 49 |

Most current rankings are robust to the rejected route, but model-family sensitivity widens in the tail and at long horizons. The largest sensitivity is concentrated among lower-current young QBs and some young RB/TE assets, reinforcing the need to expose uncertainty rather than optimize routes around current names.

## Position distribution under the retained primary family

Top-25 share:

| Horizon | QB | RB | WR | TE |
| --- | ---: | ---: | ---: | ---: |
| H3 | 88% | 8% | 4% | 0% |
| H4 | 80% | 8% | 12% | 0% |
| H5 | 76% | 8% | 16% | 0% |
| H6 | 76% | 12% | 12% | 0% |
| H7 | 76% | 12% | 12% | 0% |
| H8 | 72% | 12% | 16% | 0% |

Top-50 share:
- H3: 52% QB / 32% RB / 16% WR / 0% TE;
- H5: 50% / 26% / 24% / 0%;
- H8: 50% / 20% / 30% / 0%.

Top-100 share:
- H3: 31% QB / 31% RB / 32% WR / 6% TE;
- H5: 29% / 29% / 35% / 7%;
- H8: 29% / 28% / 35% / 8%.

No positional shape was imposed manually.

## Age / persistence effects

Mean H3→H5 / H3→H8 rank movement:
- young QB: **+21.3 / +32.7**;
- prime QB: **+5.4 / +7.7**;
- aging QB: **+0.6 / +0.7**;
- young RB: **+0.9 / +4.6**;
- prime RB: **-5.9 / -8.8**;
- aging RB: **-12.6 / -21.2**;
- young WR (n=4): **+7.0 / +14.5**;
- prime WR: **+3.9 / +6.1**;
- aging WR: **-9.4 / -18.0**;
- young TE (n=4): **+7.0 / +11.0**;
- prime TE: **+0.3 / +4.3**;
- aging TE: **-8.3 / -15.3**.

These are consequences of the frozen production/persistence model, not age bonuses.

## Annual uncertainty and precision

Under the retained `two_part_state` holdout:

| Position | Y4 RMSE / mean current Y4 | Y5 | Y6 | Y7 | Y8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| QB | 1.62× | 1.96× | 2.05× | 2.04× | 2.16× |
| RB | 2.28× | 2.14× | 2.46× | 2.71× | 3.75× |
| WR | 1.08× | 1.11× | 1.24× | 1.56× | 1.59× |
| TE | 1.46× | 1.59× | 1.46× | 1.89× | 1.85× |

Rank signal declines gradually rather than at a clean breakpoint. At Y8 holdout Spearman remains about QB **0.477**, WR **0.410**, RB **0.203**, TE **0.212**.

Therefore:
- the same family is the best annual-cardinal research family across Y4-Y8;
- the evidence does **not** justify treating each year as equally precise;
- a terminal/career representation may still be more useful than displaying false exact-year precision, especially for RB/TE.

## Updated architecture recommendation

Research no longer recommends describing H5 as an empirically discovered model breakpoint.

Recommended governed design target:

1. **H1-H3:** production authority unchanged.
2. **Y4-Y8 research Forecast family:** one universal `two_part_state` family, position-aware through its existing position-specific fits, not through separate model-family routing.
3. **User-facing horizon lenses:** expose discrete horizons only where product usefulness warrants them; H4/H5/H6/H7/H8 are not assumed to be separate models.
4. **Terminal/career:** separately investigate a state/persistence representation derived from transition/hazard evidence, because career-state models appear more useful semantically than as annual-cardinal engines.
5. **Uncertainty:** must widen/communicate evidence decay by position and horizon. Do not interpret a single family as uniform confidence.

No hidden master score, market anchoring, owner preference, Team Utility leakage, or named-player tuning is authorized.

## Required Management decisions

1. Accept or reject `two_part_state` as the research-standard Y4-Y8 annual family for the next long-horizon phase.
2. Decide which discrete horizon coordinates are product-worthy (for example H4/H5/H6/H8) versus internal diagnostics; Research found no statistical breakpoint that chooses this for Management.
3. Authorize or reject a separate terminal/career-state research track using transition/hazard evidence without replacing annual cardinal Forecasts.
4. Require a long-horizon uncertainty presentation/scenario contract before any cardinal Y4+ production promotion.
5. Keep production H3 unchanged unless a separately designed H1-Y3 challenger clears an independent validation problem.

**MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**
