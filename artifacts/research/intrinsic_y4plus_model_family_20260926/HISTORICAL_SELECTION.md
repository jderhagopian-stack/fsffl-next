# FSFFL NEXT — Comparative Y4+ Historical Model-Family Selection

Date: 2026-09-26  
State: **HISTORICAL SELECTION FROZEN BEFORE NEW CURRENT-PLAYER SHADOWS**  
Authority: Research only. Production H3 unchanged.

## Empirical result

Management reopened the study specifically to avoid assuming that Y5 was a breakpoint or that one model family should be assigned in advance.

The six-family chronological comparison does **not** support promoting a position/horizon-routed cardinal architecture.

For the primary universal annual-production problem from Y4 through Y8, Research retains the incumbent **`two_part_state`** family as the robust historical selection for all four positions.

No breakpoint is promoted.

## Why the development routing map is not promoted

The frozen development selector produced an apparently attractive routed map:
- QB: survival_hazard Y4-Y8;
- RB: conditional_cohort Y4-Y5, direct_ridge Y6-Y8;
- WR: two_part_state Y4-Y6, direct_ridge Y7-Y8;
- TE: two_part_state Y4-Y5, direct_ridge Y6-Y8.

All cells passed the predeclared carry-baseline holdout confirmation. However, the architecture-level holdout shows that the route is trading one loss function for another rather than discovering a broadly superior model.

Against the incumbent two_part_state, paired holdout bootstrap shows:
- Y4: routed MAE is indistinguishable/slightly worse while MSE is significantly worse;
- Y5: MAE is indistinguishable while MSE is significantly worse;
- Y6-Y8: routed MAE is significantly lower, but MSE is significantly worse at every horizon.

The main cause is direct_ridge shrinkage:
- direct_ridge wins MAE in **17/20** position × horizon holdout cells;
- direct_ridge wins RMSE in **0/20** cells versus two_part_state;
- direct_ridge never clears a three-of-four win over two_part_state across RMSE, MAE, Spearman and survival Brier;
- top-decile production is materially more underpredicted by direct_ridge, especially at RB/WR/TE Y6-Y8.

Because Shapley/Intrinsic is sensitive to high-end deployable production, that tail compression is economically material.

## Incumbent robustness

Across the 20 position × horizon holdout cells, two_part_state has:
- best RMSE in **14/20**;
- best survival Brier in **14/20**;
- best Spearman in **8/20**;
- best tail RMSE in **11/20**; carry_y3 wins the remaining 9 tail-RMSE cells.

No challenger dominates it across the multi-objective problem.

### Survival/hazard

The purpose-built survival_hazard model is often almost numerically identical to two_part_state and occasionally improves survival/rank metrics, especially for QB.

The paired gains are too small/unstable to justify a separate QB route, and QB Y8 is materially worse than the incumbent. It remains a useful model-risk challenger.

### Career-state transition

The four-state transition model occasionally has the best RMSE, especially in sparse/terminal QB cells, but is consistently weaker on MAE and often rank. That makes it more promising as a **terminal persistence/state representation** than as the cardinal annual-production model.

### Conditional cohort

The conditional-production/cohort survival model does not beat the incumbent robustly enough to justify a routed role.

## H3 authority

No H1-Y3 replacement claim is made.

The Y1-Y3 governed Forecast path is explicitly used as an input feature to the post-H3 challengers. Reusing those inputs to claim that one of these challengers beats the existing H1-Y3 problem would not be an independent comparable validation.

Production `intrinsic-shapley-i1-v1` remains unchanged.

## Frozen current-shadow rule

The next post-selection current-player run will:
1. use two_part_state for the primary Y4-Y8 cardinal research curve;
2. preserve production H3 as the comparison oracle;
3. show the development-routed/direct/hazard alternatives only as sensitivity/model-risk shadows;
4. make no named-player coefficient or route changes.

This document is the freeze point before the reopened study inspects new current-player results.
