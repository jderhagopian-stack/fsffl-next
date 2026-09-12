# Multi-Year Intrinsic Forecast Trajectory-Shape / Horizon-Consistency Results

**PR:** #131  
**Status:** research-only, non-authoritative, not for production promotion  
**Authority:** Forecast owns football trajectory, survival, and football uncertainty. Value was not changed. Model B was not fitted.

## Executive conclusion

A real multi-year Forecast path defect was found, but it has two different parts and they should not be conflated.

1. **Recursive uncertainty propagation is structurally incomplete.** The current research Forecast recursion computes each new horizon's uncertainty from the new transition alone and does not carry the incoming forecast state's existing variance into the next step. As a result, forecast dispersion contracts deeper into the path even while realized error increases. A parameter-free delta-method repair that carries the existing state variance forward passes direct chronological Forecast validation and is accepted as a **research-only Forecast challenger**. It is not promoted to production here.
2. **Mean trajectory shape is still imperfect, especially in the elite tail, but no tested mean-path repair passes the frozen direct-Forecast gate.** New information materially improves cumulative multi-year production forecasts, yet the relative Year-1/Year-2 shape becomes slightly worse on average. Elite QBs and young breakout WRs show the clearest under-persistence deeper into the path. Freezing the latest observed production percentile across recursive horizons substantially improves slope and far-horizon correlation, but worsens absolute slope error, so that challenger is rejected.

Therefore the unresolved appreciation/decline and elite-QB longevity failures are **not isolated enough to Value to justify Model B yet**. The narrow remaining issue remains Forecast-owned: how player-specific state and conditional-production information should persist and evolve across recursive horizons.

## Point-in-time design

The audit uses the same supported historical folds and strict chronology as the existing PR #131 benchmark. For every adjacent preseason fold `T -> T+1`, it compares the common future targets for the same player:

- old fold Year 2 vs new fold Year 1;
- old fold Year 3 vs new fold Year 2.

Each fold's transition calibration is rebuilt only from evidence whose outcomes were known before that cutoff. No through-2025 calibration is back-applied. Market value is not a Forecast target. The historical player universe and reconstruction rules are unchanged.

## Full-path audit

There are **6,916** same-player adjacent-fold common-path observations.

| Direct Forecast target | Result |
|---|---:|
| Near common-year revision direction | **67.9%** |
| Near revision vs needed-change correlation | **0.555** |
| Near revision magnitude MAE | **36.205** |
| Far common-year revision direction | **62.0%** |
| Far revision vs needed-change correlation | **0.396** |
| Far revision magnitude MAE | **39.069** |
| Path-slope change direction | **58.1%** |
| Path-slope change correlation | **0.135** |
| Common-path slope MAE, old -> new | **32.514 -> 33.064** |
| Common-path cumulative MAE, old -> new | **81.793 -> 67.398** |
| Nominal-80% coverage, near / far | **75.6% / 67.7%** |
| Mean far/near Forecast SD ratio | **0.858** |
| Within-path production-quartile reclassification | **26.9%** |
| Within-path fallback-status change | **4.1%** |

The central pattern is important: **new information is useful in level but not fully reliable in shape**. The cumulative two-year forecast improves substantially, while the slope between the two common years gets slightly worse.

## Persistence of newly learned information

Across observations with a defined near-horizon revision:

- median modeled far/near revision persistence: **0.637**;
- median subsequently needed persistence: **0.666**;
- player-level persistence correlation: approximately **0.000**.

The aggregate medians are superficially close, but that hides the core problem: the model does not reliably know **which players** should preserve more or less of the newly learned information deeper into the path.

This is why a universal persistence multiplier is not justified.

## Recursive-mechanics diagnosis

Correlation with the difference between far- and near-horizon revisions was:

| Recursive component | Correlation |
|---|---:|
| Survival change across path | **0.005** |
| Conditional production-multiplier change | **0.276** |
| Forecast-SD change | **0.442** |
| Production-quartile change | **0.077** |
| Fallback-status change | **0.058** |

This does not prove a single causal mechanism, but it narrows the field materially:

- survival compounding is not the dominant source of the mean path-shape problem;
- fallback hierarchy is not the dominant source;
- production-tier reclassification is associated with the problem but does not explain it by itself;
- recursive conditional-production treatment and uncertainty propagation are much more material.

## Important subgroups

### Elite QBs

Elite-QB adjacent path updates are directionally strong but substantially under-persistent deeper in the path:

- `n = 236`;
- near revision direction: **85.4%**;
- far revision direction: **80.5%**;
- near revision correlation: **0.456**;
- far revision correlation: **0.288**;
- slope-change direction: **65.3%**;
- slope-change correlation: **0.085**;
- slope MAE: **87.43 -> 96.62**;
- cumulative MAE: **211.34 -> 154.16**;
- near/far nominal-80% coverage: **93.9% / 59.8%**;
- far/near SD ratio: **0.830**;
- median modeled revision persistence: **0.658**;
- median subsequently needed persistence: **1.023**.

This is strong evidence that the elite-QB longevity failure is not simply replacement economics. The latest information often moves elite-QB forecasts in the right direction, but the new state is not carried through the deeper trajectory strongly or consistently enough, and uncertainty is especially under-propagated.

No QB bonus or manual elite-player override was added.

### Young breakout WRs

The same pattern appears more mildly for young improving WRs:

- `n = 269`;
- near/far direction: **84.8% / 71.7%**;
- near/far correlation: **0.501 / 0.269**;
- slope MAE: **51.08 -> 54.54**;
- cumulative MAE: **111.94 -> 86.55**;
- near/far coverage: **92.2% / 74.7%**;
- far/near SD ratio: **0.808**;
- modeled vs needed median persistence: **0.634 vs 0.717**.

### Young TEs

- `n = 219`;
- near/far direction: **72.2% / 66.7%**;
- slope MAE: **25.74 -> 26.91**;
- cumulative MAE: **62.47 -> 51.74**;
- near/far coverage: **82.2% / 74.4%**;
- modeled vs needed median persistence: **0.639 vs 0.704**.

### Aging RBs

Aging RBs are an important counterexample:

- `n = 840`;
- near/far direction: **56.1% / 51.0%**;
- slope MAE: **20.24 -> 20.07**;
- modeled vs needed median persistence: **0.614 vs 0.613**.

Their aggregate persistence is already very close to calibrated. This is direct evidence against a universal "make long-horizon updates stick more" rule.

## Production-tier reclassification

When recursive production quartile changes:

- `n = 1,860`;
- near/far direction: **86.0% / 73.4%**;
- slope-change correlation: **0.279**;
- slope MAE: **40.24 -> 42.89**.

When quartile is unchanged:

- `n = 5,056`;
- slope-change correlation: **0.080**;
- slope MAE: **29.67 -> 29.45**.

This suggested that recursive re-ranking might be part of the mean-path problem, so it was tested directly rather than assumed.

## Forecast challengers

Three narrow, parameter-free challengers were evaluated on direct Forecast targets before any downstream Model A consideration.

| Variant | Slope MAE | Slope corr | Far revision corr | Near / far 80% coverage | Far/near SD | Decision |
|---|---:|---:|---:|---:|---:|---|
| Current baseline | **33.064** | **0.135** | **0.396** | **75.6% / 67.7%** | **0.858** | Baseline |
| Carry recursive uncertainty | **33.064** | **0.135** | **0.396** | **75.6% / 83.0%** | **1.303** | **ACCEPT research-only** |
| Preserve observed percentile state | 33.209 | **0.409** | **0.521** | 75.6% / 67.3% | 0.871 | **REJECT** |
| Both changes | 33.209 | 0.409 | 0.521 | 75.6% / 82.7% | 1.275 | **REJECT mean-path change** |

### Accepted research-only uncertainty repair

The baseline recursive variance equation did not carry the incoming state's already-existing forecast variance into the next horizon. The challenger adds the mathematically implied delta-method term:

`(survival * production_multiplier)^2 * incoming_state_variance`

No coefficient was fitted and no mean forecast was altered.

This moves far-horizon nominal-80% coverage from **67.7% to 83.0%**, while near coverage remains **75.6%** and all mean-path metrics remain identical. It therefore passes the direct Forecast target it was designed to repair.

This is an **accepted research finding only**. Production Forecast authority is unchanged in PR #131.

### Rejected mean-path challenger

Preserving the latest observed percentile across recursive horizons, instead of re-ranking after each forecasted year, materially improves:

- slope-change correlation: **0.135 -> 0.409**;
- far-horizon revision correlation: **0.396 -> 0.521**.

However, absolute slope MAE worsens **33.064 -> 33.209**, and far uncertainty coverage also slightly worsens when used alone. Under the frozen rule that a Forecast repair must beat the direct target it claims to fix rather than merely improve a downstream metric, this challenger is rejected.

The result is still diagnostically useful: recursive state re-anchoring/reclassification is implicated, but simply freezing the observed production tier is too crude.

## Model A retest

Because the accepted uncertainty repair changes only Forecast dispersion and **does not change any Forecast mean**, Model A's point-estimate economics remain the existing context-valid benchmark:

- Model A MAE: **20.307**;
- affine MAE: **26.968**;
- relative improvement: **24.7%**;
- Superflex/1QB scarcity: **PASS, 17/17 folds**;
- market independence: **PASS**.

The uncertainty-only challenger leaves the two failing mean-based economic checks unchanged in substance:

- elite-QB longevity correlation: **0.1948 — FAIL**;
- expected appreciation/decline: approximately **44.6% direction / -0.269 correlation — FAIL**;
- economic-usefulness checks: **4/6**.

The existing calibrated Model A uncertainty gate already passed at **87.3%**. In the finalized research-only retest with recursive player-state variance carried forward, calibrated Model A coverage remains within gate at **87.2%**.

Therefore the frozen production-promotion gate remains **NOT CLEARED**.

## What is fixed versus what remains

### Evidence-supported Forecast defect found

**Recursive uncertainty propagation** is incomplete. That defect is now isolated and a mathematically derived research repair passes direct out-of-time validation.

### Mean trajectory defect remains unresolved

The unresolved mean-path problem is narrower than before:

- new information improves cumulative multi-year production;
- the model is not broadly overreactive;
- survival calibration is not the main cause;
- fallback changes are not the main cause;
- universal persistence changes are contradicted by subgroup evidence;
- elite players, especially elite QBs, need more player-specific persistence than the current recursive path supplies;
- aging RB persistence is already well calibrated;
- preserving observed percentile state improves directional structure but worsens absolute shape error and therefore is not an acceptable repair.

The narrowest remaining Forecast-owned research question is therefore:

> **How should player-specific trajectory state persist and transition across horizons, conditional on position, age/career stage, production state, and uncertainty, without freezing cohort membership or applying arbitrary persistence bonuses?**

A reasonable next Forecast research challenger would be a chronologically estimated hierarchical trajectory-state transition that explicitly distinguishes short-horizon observed-state information from deeper-horizon cohort transition evidence. It should remain transparent and bounded, and it must beat the current engine on direct path-shape targets before downstream Model A testing.

## Model B decision

**Do not fit Model B yet.**

The remaining appreciation/decline and elite-QB residuals cannot yet be cleanly assigned to Value because a material mean-path Forecast defect remains unresolved upstream. The earlier elite-tail Value residual may still be real, but it is not sufficiently isolated from Forecast trajectory-state persistence to justify fitting a Value challenger now.

## Governance / guardrails preserved

- Forecast remains the sole owner of football trajectory, survival, and football uncertainty.
- Value economics were not changed to compensate for Forecast behavior.
- The context-valid replacement formulation remains unchanged.
- Market Value was not used as a Forecast or intrinsic training target.
- Team Utility remains downstream.
- No arbitrary damping, persistence multiplier, QB bonus, or elite-player override was introduced.
- No opaque master score was created.
- Model B was not fitted.
- No production behavior or authority changed.
- PR #131 remains research-only and requires explicit review before any production promotion.
