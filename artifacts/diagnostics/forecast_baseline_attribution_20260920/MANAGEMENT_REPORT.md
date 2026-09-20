# FSFFL NEXT - Forecast Baseline Attribution Diagnostic

Date: 2026-09-20  
Authority: diagnostic only  
Recovered implementation checkpoint: PR #147 head `34470dce369df2c9d5454ebbd481317c5ab76d12`; protected main `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.  
Diagnostic branch: `research/forecast-baseline-attribution-diagnostic-20260920`.

## Executive answer

**Required classification: B. LOCALIZED RB BASELINE / SHRINKAGE PROBLEM.**

Y2/Y3 forecasts are not generic player-independent baselines. State survival and state mix are strongly individualized by player evidence. However, once a player is assigned to a positive future state, D1 conditional production is strongly pooled around shared position/state anchors and only modestly separated by source magnitude/history. This pooling mechanism exists across Forecast, but the evidence that it becomes materially problematic is concentrated in **developmental RB Y3**, not Forecast-wide.

For developmental RB Y3 at the current high-source/top-decile surface (n=3), the median source level is 289.4 standard points, the median D1 elite-state mean is 198.0, and the corresponding anchor-only elite mean is 170.0. Player-specific production evidence therefore adds about 28.1 points at the elite state, but still leaves a large source-to-future conditional gap. An exact source-to-Y3 expected-points decomposition over those three rows assigns 56.2% of the decline to elite-state mean compression, 30.2% to positive-state mix below elite, and 13.7% to disappearance. The previously persisted all-top-decile-RB decomposition likewise assigns 71.0% of total decline to production/state means, 9.4% to state composition, and 19.6% to disappearance. Different decomposition definitions, same conclusion: conditional production is the largest downward-pull component.

The architecture-wide cross-position evidence does **not** justify a Forecast-wide baseline fix. Current top-decile Y3 conditional-retention medians are QB 0.774, RB 0.568, WR 0.708, TE 0.793. RB Y3 active probability (0.831) is essentially the same as WR (0.831), so the RB gap is principally conditional production rather than disappearance. A prior cross-position application of the same bounded magnitude-location correction produced positive pooled CRPS gain in 0/6 tested QB/WR/TE developmental/established Y3 routes, with 0/6 clustered intervals clearing zero.

## 1. Exact architecture recovered

The frozen production path is:

```
Frozen preseason raw stats
        |
        +--> direct standard/non-PPR Y1 points
        |         |
        |         +--> P0 state probability models
        |         |      persistence / out
        |         |      ordered positive-state thresholds
        |         |
        |         +--> P0 conditional-production model
        |                D1: one mean per future state
        |                D0: one common mean for all positive states
        |
        +--> direct connected-league Y1 points
                  |
                  +--> same-player connected-Y1 / standard-Y1 ratio
                           applied exactly once to every Y2/Y3 state mean
```

Expected future points are reconstructed as:
```
E[Y_h] = sum_s p_h(s | player evidence) * mu_h(s | player evidence),  s in {depth, usable, starter, premium, elite}
```
with out-state production fixed at zero.

State probabilities use regularized logistic components. Conditional production uses frozen linear predictors with a zero floor. D1 contains shared position/future-state anchors plus player-specific source magnitude, source percentile, age/experience, prior-1 history, and internal prior-2 features. D0 has no future-state-specific production term: the same positive-state mean is used for depth through elite.

## 2. What is actually player-specific

Player-specific evidence enters multiple layers:

- **Active/disappearance probability and state mix:** source production magnitude, prior production, age/experience, source state, state percentile, role/opportunity evidence where available, and QB memory terms where governed.
- **Conditional production:** source log-points, source percentile, age, experience, prior-1 history, and for D1 the internal prior-2 mean/gap family; D1 also interacts source magnitude/percentile with the future state.
- **League scoring translation:** player-specific connected-Y1 / standard-Y1 ratio, downstream only, applied once. It does not change P0 probabilities or relative state geometry.
- **Uncertainty in the current P0 output:** discrete future-state uncertainty only. The fitted package contains diagnostic/fitted covariance-scale quantities, but the runtime does not emit or sample a within-state conditional-production distribution.

## 3. Baseline pull versus player-specific conditional authority

A baseline-only production counterfactual retained the fitted intercept plus position/source-state/future-state anchors while zeroing the player-specific continuous/history families. The full-vs-anchor comparison shows that player evidence materially moves means, but the state anchors remain dominant.

On continuous P10-to-P90 governed evidence sweeps (all non-target inputs held fixed at a cell-median representative), Y3 D1 **elite-state** response slopes, in future-state points gained per one source-point increase, are:

| Position / career | Y3 route | Elite-state response slope |
|---|---:|---:|
| QB developmental | D1 | 0.147 |
| QB established | D1 | 0.139 |
| QB veteran | D1 | 0.144 |
| RB developmental | D1 | 0.161 |
| RB established | D1 | 0.101 |
| WR developmental | D1 | 0.235 |
| WR established | D1 | 0.183 |
| TE developmental | D1 | 0.166 |
| TE established | D1 | 0.146 |

Thus, for the D1 Y3 routes, roughly 10-24 cents of elite-state production separation is created for each one point of source-evidence separation over these governed central ranges. The relationship remains increasing; it does not literally flatten to a constant. But it is strongly sublinear and therefore exhibits substantial baseline pull.

This is **not unique to RB as a mathematical mechanism**. What is unique is the combination of that pooling with the RB historical/current magnitude geometry: elite/high-source RBs enter the future-state layer much farther above the shared state anchor than the other positions, so the same strongly pooled architecture creates visibly larger absolute compression.

## 4. Developmental RB Y3

The current high-source developmental-RB subset is inside the frozen historical support envelope:

- route: D1
- selection-block support: 329 / 219 / 225 rows
- distinct source seasons: 7
- active historical top-decile n: 72
- historical active top-decile source p90: 295.27
- historical maximum: 357.20
- current high-source median: 289.4

So the compression is not explained by simple extrapolation.

For these current high-source developmental RBs:

| Quantity | Median |
|---|---:|
| Source Y1 standard points | 289.4 |
| Y3 active probability | 0.900 |
| Y3 elite-state mean | 198.0 |
| Anchor-only elite-state mean | 170.0 |
| Player-specific elite-state lift above anchor | +28.1 |
| Y3 conditional active points | 162.6 |
| Y3 expected points | 146.3 |

Descriptively, this is **modestly individualized around a shared state anchor**, not effectively player-independent, but not substantially individualized relative to the source-evidence spread.

The prior-2 family is not the cause: earlier frozen counterfactuals moved the representative high-source developmental-RB conditional values by less than one point when the prior-2 family was neutralized.

## 5. Historical error relationship

Across the eight position x horizon cells (QB/RB/WR/TE x Y2/Y3), the descriptive relationship between measured high-source baseline pull and historical median conditional-retention bias is weak: Pearson = -0.208 and Spearman = -0.024. This is descriptive only; n=8 is not used for an inferential claim.

The chronology-correct, origin-clustered developmental-RB evidence is more informative. The latest preregistered gap-aware magnitude challenger did express the intended mechanism and improved point MAE by 0.94, but full-cell CRPS gain was only +0.0145 with clustered 95% interval [-0.4045, +0.3399]. Six of nine origins improved, the median origin gain was +0.2232, five leave-one-origin fits produced negative gains, and moving-block uncertainty spanned [-0.1873, +0.1813]. The challenger therefore did **not** earn authority. This prevents turning the baseline-pull diagnosis into an unearned mean correction.

Cross-position control evidence points the same way: the common bounded magnitude-location correction had negative pooled CRPS gain in every tested QB/WR/TE developmental/established Y3 route. Therefore there is no empirical basis to declare a Forecast-wide baseline/shrinkage defect.

## 6. Uncertainty containment

Current P0 does not emit a within-state production distribution. It emits state probabilities, point state means, and expected points. Downstream Shapley/Intrinsic evaluates the discrete state scenarios, but there is no productive-survivor draw above (or below) the selected state's central mean. Consequently, the current uncertainty representation cannot fully preserve the historically observed high-side survivor spread when the conditional mean itself is compressed.

This limitation is empirically meaningful. Frozen developmental-RB distribution-shape research held D1 state probabilities and expected means fixed and added within-state spread. The preregistered S1 shape improved Y3 CRPS by +0.811 with 95% interval [+0.519, +1.109] in the 2014-2020 selection window and by +0.513 [+0.160, +0.876] in the locked 2021-2022 replication. However, both tested shapes worsened the p95+ productive-survivor/downside tail-calibration gate. The direction is supported; the tested representations are not promotable.

## 7. Simulation and Value handoff / double counting

The current NEXT-4 regular-season Simulation consumes governed season forecast means, decomposes them to active-game means, and applies an independently calibrated weekly-volatility model. That volatility is explicitly not derived from season-forecast uncertainty. The P0 Y2/Y3 future-state distribution implemented in PR #147 is instead consumed by the live Intrinsic/Shapley calendar path.

For the P0 future path, Shapley receives probabilities plus point state means and computes the expected marginal value across those states. It does not apply another RB-age-collapse penalty. Intrinsic then applies the uniform frozen horizon discount (0.85 for Y2 and 0.85^2 for Y3). No second RB-specific collapse haircut was found in the verified P0 -> Shapley/Intrinsic path.

Therefore:
- the current P0 path does not double-count RB collapse;
- the regular-season Simulation does not currently sample P0 Y3 survivor outcomes;
- the Intrinsic path can represent discrete elite/starter/etc. states, but cannot sample within-state productive-survivor tails because Forecast does not emit them.

## 8. Causal candidates

- **A. Poor generic baseline level:** not supported as a Forecast-wide explanation. Cross-position corrections do not improve proper scoring.
- **B. Baseline reasonable, player-specific response too weak:** supported directionally for developmental RB Y3 conditional production, especially high-source survivors.
- **C. Compression mainly from state probability / genuine regression:** incomplete. Genuine historical regression is substantial, but current high-source RB disappearance is not the main source of the gap.
- **D. Multiple mechanisms:** yes inside developmental RB Y3. Conditional mean compression is largest, state mix is second, disappearance is smaller; missing within-state uncertainty prevents the distribution from restoring plausible tail width.

## 9. Decision

**B. LOCALIZED RB BASELINE / SHRINKAGE PROBLEM**

The pooling architecture is shared, but only developmental RB Y3 currently has sufficient evidence that the pooling becomes a material Forecast limitation. The evidence does not support changing QB, WR, TE, or the full Forecast architecture. The limitation is real enough that **PR #147 should remain on management hold**, because the present P0 future output does not fully represent productive-survivor uncertainty for the one route where compression is materially exposed. This is a hold for architecture/uncertainty disposition, not authorization to change the frozen mean model.

### Minimum next architectural research question

Can one pre-specified **developmental-RB Y3 within-state conditional-production uncertainty** representation preserve the frozen D1 state probabilities and central means while calibrating productive-survivor tail mass without creating a new p95+ survivor/downside failure?

### Bounded preregistration boundary

One candidate family only. Freeze D1 probabilities, routes, central means, scoring coordinate, and expected points. Fit uncertainty/scale only on chronology-correct pre-origin data. Evaluate on the same frozen 2014-2020 origin blocks with origin-clustered uncertainty; unlock 2021-2022 exactly once only if every selection gate passes; keep source-2023 -> target-2026 untouched. Promotion would require: positive clustered proper-score gain, no worsening of p95+ combined survivor/downside calibration, no state-ordering violation, Y2 no-harm, and no QB/WR/TE authority change. No mean boost, state-probability change, alternate candidate search, or named-player tuning is authorized.

## Hard stop honored

This diagnostic changed neither PR #147 nor main, did not refit/tune P0/D0-D1, did not change routes, coefficients, distributions, Simulation, Value, Intrinsic, or Shapley, and did not merge or deploy anything. Only diagnostic artifacts are persisted on the separate research branch.
