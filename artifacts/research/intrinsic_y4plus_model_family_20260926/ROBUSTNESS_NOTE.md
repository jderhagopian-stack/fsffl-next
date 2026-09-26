# FSFFL NEXT — Y4+ Comparative Robustness Note

Date: 2026-09-26  
Authority: Research only  
Primary evidence artifact: workflow `36250669362`, artifact `10909006505`, digest `sha256:0befa35ef1d75eeb8cf160d141e9296cde4c83edd3df7127979afb7f2b8430ba`.

## Why the development routing map was not promoted

The predeclared development selector was allowed to choose a different model family by position and horizon. It produced apparent breakpoints, but the untouched holdout evidence shows that those switches primarily trade lower central-error MAE for worse squared/tail error rather than produce a broadly superior cardinal model.

Across the 20 position × horizon holdout cells:

| Family | Best RMSE cells | Best MAE cells | Best Spearman cells | Best survival-Brier cells | Best top-decile tail-RMSE cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| carry_y3 | 2 | 1 | 0 | 0 | 9 |
| direct_ridge | 0 | 17 | 3 | 0 | 0 |
| two_part_state | **14** | 1 | **8** | **14** | **11** |
| conditional_cohort | 0 | 0 | 2 | 0 | 0 |
| survival_hazard | 1 | 1 | 5 | 5 | 0 |
| career_state_transition | 3 | 0 | 2 | 1 | 0 |

This multi-objective pattern favors `two_part_state` as the robust annual cardinal family.

## Direct-ridge shrinkage tradeoff

Direct ridge is the clearest example of why MAE alone is not a sufficient Intrinsic selection target:
- it wins MAE in 17/20 cells;
- it wins RMSE in 0/20 cells;
- it wins top-decile tail RMSE in 0/20 cells.

Mean top-decile RMSE across positions:

| Horizon | two_part_state | direct_ridge |
| --- | ---: | ---: |
| Y4 | 133.74 | 165.54 |
| Y5 | 137.13 | 168.44 |
| Y6 | 133.98 | 163.79 |
| Y7 | 120.43 | 141.56 |
| Y8 | 79.28 | 93.03 |

Because FSFFL Intrinsic uses a lineup-capacity Shapley deployment economy, suppressing high-end production errors is economically material. A model that improves typical absolute error by shrinking the upper tail is not automatically a better Intrinsic input.

## Paired dynamic-route versus incumbent holdout

Paired bootstrap uses deterministic seed 20260926 and resamples the same player observations at each horizon.

| Horizon | Δ MAE route−incumbent | 95% CI | Δ MSE route−incumbent | 95% CI | Interpretation |
| --- | ---: | --- | ---: | --- | --- |
| Y4 | +0.119 | [-0.014, +0.253] | +49.9 | [+22.1, +80.1] | no MAE gain; significantly worse squared error |
| Y5 | +0.022 | [-0.144, +0.184] | +46.9 | [+12.0, +86.9] | statistical tie on MAE; worse squared error |
| Y6 | -0.574 | [-1.044, -0.091] | +254.2 | [+147.9, +371.9] | lower MAE, materially worse squared error |
| Y7 | -1.681 | [-2.210, -1.151] | +190.0 | [+95.8, +284.7] | lower MAE, materially worse squared error |
| Y8 | -1.516 | [-2.002, -1.017] | +175.6 | [+86.9, +276.0] | lower MAE, materially worse squared error |

The routed architecture therefore does not establish a defensible cardinal-model breakpoint.

## Survival / hazard challenger

The hazard model is the most credible alternative for QB and often nearly matches the incumbent:
- it has occasional rank/survival-calibration gains;
- it does not show a stable material aggregate advantage;
- QB Y8 is materially worse than the incumbent on paired holdout error.

Research retains it as a model-risk / persistence diagnostic, not as a separate QB cardinal route.

## Career-state transition challenger

The four-state career-transition model occasionally wins RMSE in sparse long-horizon cells, but performs poorly on MAE and often ranking. Its most defensible future role is as a terminal/career **state** lens rather than an annual cardinal points model.

## Frozen disposition before new current-player shadows

Primary annual Y4–Y8 cardinal research family:
**`two_part_state` for QB, RB, WR and TE at every tested horizon.**

Promoted empirical breakpoint:
**none**.

Alternative families remain sensitivity/model-risk evidence and may inform a separate terminal/persistence representation.

Production H3 remains unchanged.
