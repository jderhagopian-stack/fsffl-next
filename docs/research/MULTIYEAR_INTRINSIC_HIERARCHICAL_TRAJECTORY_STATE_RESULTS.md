# Multi-Year Intrinsic — Hierarchical Trajectory-State Forecast Results

**PR:** #131  
**Status:** research-only, non-authoritative, unmerged  
**Production Forecast changed:** no  
**Production Value changed:** no  
**Model B fitted:** no

## Executive conclusion

The hierarchical trajectory-state hypothesis contains a real Forecast signal, but the tested challenger does **not** clear the direct Forecast gate and is rejected.

The challenger materially improves several path-shape targets:

- far-horizon revision correlation: **0.396 -> 0.545**;
- path-slope correlation: **0.135 -> 0.437**;
- path-slope MAE: **33.064 -> 32.886**.

However, the central research target remains unresolved:

- player-specific persistence correlation remains approximately **0.000**;
- persistence MAE worsens slightly from **109.005 -> 109.172**.

The challenger therefore learns something useful about **group-level trajectory shape** without learning which individual players should preserve more or less newly learned information. Under the frozen rule that a Forecast challenger must improve the direct target it is designed to repair, it is **not accepted**.

Because the direct Forecast gate fails, Model A is **not rerun** in this cycle. The existing Model A result remains authoritative for this research branch: 20.307 MAE versus 26.968 for the affine control, 4/6 economic checks, with elite-QB longevity and appreciation/decline still failing.

The accepted recursive uncertainty carry-forward repair remains a separate **research-only** finding. It is not promoted to production here.

## Exact repo / chronology guardrails

This work continues on draft PR #131. At the start of the cycle:

- `main`: `f38e2f029a0d9563986635012336434a3f9beb63`;
- PR #131 head: `70bccfda97ea5c57c9825bb9eabc407f69a32be7`;
- the only newer open parallel PR was roadmap-only PR #132, with no overlapping research implementation.

The historical universe and Forecast reconstruction rules are unchanged from the prior PR #131 work.

Every learned persistence parameter is estimated only from historical targets whose outcomes were resolved before the relevant preseason cutoff. A training record enters fold `T` only when its target season is at most `T-1`. No through-2025 parameter is back-applied to earlier folds, and no current-fold holdout outcome is used for fitting.

## State definition

The challenger deliberately remains narrow and interpretable.

### Player-specific state

The player-specific anchor contains only Forecast-owned point-in-time football information:

- latest production percentile;
- recent observed production direction;
- position;
- age / experience through the career-stage classification;
- production tier.

It does not use market value, Team Utility, roster need, owner preference, trade behavior, or downstream economics.

### Cohort state

The existing recursive Forecast path remains the cohort anchor. It retains the existing transition mechanics for:

- position;
- age progression;
- experience progression;
- production-state transition;
- survival;
- conditional production;
- fallback hierarchy.

### Horizon-specific evidence

Persistence is estimated separately for deeper horizons rather than applying one universal coefficient.

The learned parameter is a convex blend:

- `0` = retain the current recursive cohort path;
- `1` = fully retain the latest observed percentile-state path;
- intermediate values = empirically estimated balance between the two.

No fixed persistence bonus, QB bonus, elite-player override, damping factor, or amplification factor is introduced.

### Uncertainty

Mean-path persistence and uncertainty propagation remain separate dimensions. The four requested combinations are evaluated:

1. baseline mean + baseline uncertainty;
2. baseline mean + repaired recursive uncertainty;
3. hierarchical mean + baseline uncertainty;
4. hierarchical mean + repaired recursive uncertainty.

## Hierarchical fallback and evidence sufficiency

A subgroup cell must have at least **100 resolved historical observations** before it can set its own persistence weight. Otherwise it falls back through:

1. position × career stage × production tier × recent direction;
2. position × career stage × production tier;
3. position × career stage;
4. position;
5. global.

This prevents sparse elite or breakout subgroups from becoming manual special cases disguised as fitted parameters.

Across 19,950 player/horizon forecast applications, the hierarchy frequently used broader parents where the narrow cell lacked evidence. Mean learned weights generally remained modest rather than collapsing to the fully sticky path.

Selected aggregate learned weights:

| Group | Year 2 mean weight | Year 3 mean weight |
|---|---:|---:|
| QB | 0.320 | 0.174 |
| RB | 0.244 | 0.208 |
| WR | 0.299 | 0.267 |
| TE | 0.184 | 0.130 |
| Elite production tail | 0.293 | 0.166 |
| Middle production tier | 0.275 | 0.269 |
| Replacement tail | 0.192 | 0.118 |
| Improving recent production | 0.266 | 0.226 |
| Declining recent production | 0.246 | 0.218 |

These are empirical historical summaries, not promoted production coefficients.

## Direct Forecast comparison

| Metric | Baseline | Hierarchical mean | Hierarchical + repaired uncertainty |
|---|---:|---:|---:|
| Far revision correlation | **0.396** | **0.545** | **0.545** |
| Slope correlation | **0.135** | **0.437** | **0.437** |
| Slope MAE | **33.064** | **32.886** | **32.886** |
| Cumulative multi-year MAE | **67.398** | **67.721** | **67.721** |
| Persistence correlation | **~0.000** | **~0.000** | **~0.000** |
| Persistence MAE | **109.005** | **109.172** | **109.172** |
| Near 80% coverage | **75.6%** | **75.6%** | **75.6%** |
| Far 80% coverage | **67.7%** | **67.4%** | **82.5%** |

The cumulative MAE deterioration is small, about 0.48%, and remains inside the predeclared 1% adjacent-target tolerance. The decisive failure is instead the explicit player-specific persistence target.

### Horizon error

| Horizon | Baseline MAE | Hierarchical MAE |
|---|---:|---:|
| Year 1 | **33.774** | **33.774** |
| Year 2 | **36.979** | **37.167** |
| Year 3 | **35.557** | **37.990** |

The hierarchy does not alter Year 1. Its shape improvements therefore come from redistributing deeper-horizon forecasts, but absolute Year 2 and especially Year 3 level error worsen. This is another reason not to accept the mean-path challenger yet.

### Survival calibration

Survival behavior is unchanged by construction. The direct survival Brier score is **0.18162** for baseline and hierarchical variants. This reinforces the prior finding that survival is not the principal source of the remaining mean-path problem.

## Player-specific persistence target

This was the central test.

The prior trajectory audit found that aggregate persistence medians could look reasonable while player-level persistence correlation was approximately zero. A successful trajectory-state model therefore needed to distinguish high-persistence from low-persistence players better than the current engine.

It did not.

Despite improving aggregate path-shape correlation, the challenger leaves persistence correlation essentially zero and slightly worsens persistence MAE. In plain language:

> The hierarchy can learn that some broad football groups should lean more toward current player state and others more toward cohort reversion, but the state variables used here are not rich enough to tell which individual player within those groups should persist more or less.

That is the narrowest remaining Forecast-owned defect identified by this cycle.

## Important subgroup results

### Elite QBs

The hierarchical mean improves several elite-QB shape metrics:

| Elite-QB metric | Baseline | Hierarchical |
|---|---:|---:|
| Far revision correlation | 0.279 | **0.292** |
| Slope correlation | 0.102 | **0.228** |
| Slope MAE | 96.553 | **92.304** |
| Persistence MAE | 2.315 | **2.046** |
| Persistence correlation | 0.002 | **-0.004** |
| Cumulative MAE | **197.632** | 200.714 |
| Near revision correlation | **0.458** | 0.375 |

This is useful evidence: group-aware persistence helps the elite-QB path slope and persistence magnitude, but it still does not rank which elite QBs require stronger persistence, and it sacrifices near-horizon correlation and cumulative error. The direct Forecast result is therefore not clean enough to claim the downstream elite-QB longevity failure is repaired.

With recursive uncertainty carry-forward, elite-QB far-horizon nominal-80% coverage improves from **59.8% to 77.6%**. That is an uncertainty result, not a mean-path repair.

No QB premium or elite override is used.

### Young breakout WRs

| Metric | Baseline | Hierarchical |
|---|---:|---:|
| Far revision correlation | 0.344 | **0.365** |
| Slope correlation | 0.044 | **0.051** |
| Slope MAE | 41.893 | **41.563** |
| Cumulative MAE | 76.142 | **75.937** |
| Persistence correlation | -0.192 | **-0.057** |
| Persistence MAE | **2.024** | 2.110 |

This is a partial improvement: the hierarchy moves persistence correlation materially toward zero and improves several shape/level metrics, but persistence magnitude worsens and player-level discrimination is still poor.

With repaired uncertainty, far coverage rises from **65.3% to 81.0%**.

### Young TEs

The challenger is essentially neutral on the mean path:

- far revision correlation: **0.467 -> 0.468**;
- slope correlation: **0.116 -> 0.121**;
- slope MAE: **20.614 -> 20.596**;
- cumulative MAE: **42.789 -> 42.835**;
- persistence MAE worsens **5.522 -> 5.828**.

Repaired uncertainty raises far coverage from **63.6% to 80.0%**.

### Aging RBs

Aging RBs remain the key guardrail against indiscriminate persistence increases:

- slope MAE improves slightly **23.567 -> 23.497**;
- far revision correlation worsens **0.368 -> 0.361**;
- persistence MAE worsens **3.346 -> 3.430**;
- cumulative MAE worsens slightly **46.804 -> 46.881**.

The model therefore does not earn permission to increase persistence broadly. Repaired uncertainty does improve far coverage from **76.9% to 88.8%**, again separately from the mean-path issue.

## Accepted uncertainty finding remains separate

The previously accepted research-only recursive variance carry-forward continues to validate independently:

- baseline far 80% coverage: **67.7%**;
- hierarchical mean with baseline uncertainty: **67.4%**;
- hierarchical mean with repaired uncertainty: **82.5%**.

This confirms that uncertainty propagation and mean trajectory-state persistence are distinct problems. The uncertainty repair is **not promoted to production** in this cycle.

## Challenger decision

**Hierarchical trajectory-state mean: REJECT.**

The challenger improves important shape diagnostics, which validates the broad research hypothesis that context-dependent state persistence contains information. But it fails the exact mechanism it was intended to repair: player-specific persistence discrimination.

The direct gate fails because:

- persistence correlation does not improve above approximately zero;
- persistence MAE worsens slightly;
- Year 2 and especially Year 3 absolute level MAE worsen;
- elite-QB improvements are mixed rather than uniformly better;
- aging-RB persistence is not improved.

Accordingly, downstream Model A is not used to rescue the challenger.

## Model A downstream decision

**Model A was not rerun with the hierarchical mean challenger.**

That is intentional and follows the research contract: direct Forecast success must come first.

The unchanged canonical Model A research state therefore remains:

- Model A MAE: **20.307**;
- affine MAE: **26.968**;
- relative improvement: **24.7%**;
- context-valid Superflex/1QB scarcity: **PASS**;
- uncertainty calibration: **PASS**;
- market independence: **PASS**;
- elite-QB longevity: **FAIL**, correlation about **0.1948**;
- expected appreciation/decline: **FAIL**, approximately **44.6% direction / -0.269 correlation**;
- economic checks: **4/6**;
- frozen production-promotion gate: **NOT CLEARED**.

## What the result teaches us

The research has now ruled out several progressively more plausible explanations:

- broad Forecast-update overreaction — not supported;
- one universal update shrink/gain — rejected;
- survival or fallback as the main mean-path cause — not supported;
- globally freezing observed percentile state — rejected;
- subgroup-level hierarchical blending alone — informative, but rejected.

The new narrow conclusion is that the missing Forecast state is **more player-specific than position × career stage × production tier × recent one-season direction**.

The likely missing information is not a downstream economic effect. It is a richer but still auditable description of the player's football trajectory history—for example, multi-season state momentum, stability/volatility of prior production, repeated versus one-off breakouts/declines, or a chronologically estimated player-state residual that is explicitly shrunk toward the hierarchy according to evidence.

Any next challenger should remain transparent and Forecast-owned. A justified next hypothesis would be:

> **Estimate a chronologically updated player-specific trajectory residual from multiple prior seasons, with empirical hierarchical shrinkage toward position/career-state cohorts, rather than deciding persistence solely from coarse subgroup membership.**

Such a challenger would need to demonstrate that it can actually raise player-level persistence correlation and reduce persistence MAE while preserving Year 1 calibration, cumulative accuracy, subgroup stability, and survival calibration.

## Model B decision

**Keep Model B blocked.**

The remaining Forecast defect is still material and is now more precisely isolated to player-specific state persistence. The nonlinear Value residual cannot yet be cleanly separated from that upstream Forecast problem.

If a future player-specific residual/state challenger clears direct Forecast validation and Model A still exhibits a stable elite-tail nonlinear residual, the previously identified bounded nonlinear surplus transformation may then become a legitimate Model B hypothesis for review. It is not fitted here.

## Production recommendation

No production promotion is recommended from this cycle.

- Keep the hierarchical mean challenger research-only and rejected.
- Keep the recursive uncertainty carry-forward repair research-only despite its successful validation.
- Do not change production Forecast or Value behavior.
- Do not merge PR #131 on the basis of this research.
- Continue Forecast research only if pursuing the narrower player-specific trajectory-residual hypothesis.

## Reproducibility

Clean GitHub Actions research run:

- run: `34723442484`;
- artifact: `pr131-model-a-intrinsic-forecast-audit`;
- artifact ID: `10307321079`;
- artifact SHA256: `8736e453a34fc1b7607bc9c17c38b1433049c1338301765e83063a623048b5a2`;
- repository tests: **1,153 passed, 2 warnings**.

The artifact contains the direct Forecast results JSON, report, hierarchical weights/evidence rows, prior trajectory diagnostics, and the unchanged Model A research outputs.
