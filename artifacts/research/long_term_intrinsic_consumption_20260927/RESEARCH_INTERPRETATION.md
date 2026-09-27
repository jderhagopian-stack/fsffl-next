# Long-Term Intrinsic Consumption — Research Interpretation

Date: 2026-09-27  
Authority: **Research only / no production change**

## Conclusion

The economically defensible Y4-Y7 Value consumer is:

> **mean annual horizon-specific Shapley marginal lineup capacity over Y4-Y7**

`LT_RAW = (phi_4 + phi_5 + phi_6 + phi_7) / 4`

where each `phi_h` is the league-aware expected Shapley marginal contribution generated from the governed Forecast for that literal year.

This contract is supported as a Research Value architecture.

It is preferred over:
- a Y5-only shortcut;
- a Y7 terminal snapshot;
- raw future fantasy points without league scarcity economics;
- a discounted Y4-Y7 present value with an arbitrary dynasty time-preference parameter;
- any hidden blend with Current Intrinsic.

The division by four is a unit conversion from four-season total marginal capacity to one-season-equivalent marginal capacity. It is not an arbitrary horizon-weight vector.

## Historical PIT validation

Exact reused Forecast evidence:
- prior rolling artifact: `10916355135`;
- exact common player-origin rows: 11,940 before the full-window restriction;
- consumer validation uses only complete Y4-Y7 windows;
- complete outer origins: **2018 and 2019**;
- complete player-origin observations: **1,129**;
- Shapley permutations: **2,048**;
- connected-league lineup contract: 12-team QB/RB/RB/WR/WR/WR/TE/FLEX/SUPERFLEX.

This is comparative historical replay, not a pristine new final holdout.

### Consumer accuracy by frozen policy

| Forecast policy | MAE | RMSE | Bias | Spearman | 80% band | 90% band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 17.26 | 42.13 | -10.46 | 0.561 | 80.43% | 89.73% |
| hard router | 17.18 | 38.84 | -5.91 | 0.589 | 76.79% | 88.40% |
| soft stack | 16.93 | 38.64 | -6.48 | 0.592 | 77.33% | 88.49% |
| blanket 75/25 | **16.79** | **38.32** | -6.40 | **0.597** | 77.77% | 88.75% |

These numbers are not used to reopen Forecast selection. They show that the Value consumer preserves useful long-term discrimination under every already-frozen Forecast policy.

## Continuous Y4-Y7 versus shortcuts

The continuous consumer is not dominated by the Y5 headline shortcut.

Across all four frozen policies:
- continuous Y4-Y7 has **better MAE** than Y5-only;
- continuous Y4-Y7 has **better Spearman** than Y5-only;
- Y5-only has slightly lower RMSE, by roughly 0.25-0.49 raw Shapley units depending on policy;
- Y7-only is materially worse on RMSE for all four policies and usually worse on MAE/rank.

Examples:
- soft stack: continuous MAE **16.93** / Spearman **0.592** vs Y5-only **17.22 / 0.571**;
- blanket 75/25: continuous **16.79 / 0.597** vs Y5-only **16.92 / 0.575**.

Interpretation:
**H5 remains a useful headline lens, but not a defensible substitute for consuming the continuous Y4-Y7 path.**

## Economic validity

The consumer passes the mechanical Value checks:
- maximum Shapley efficiency residual: **2.91e-11**;
- monotonic scenario violations: **0**.

Thus:
- increasing a player's annual Forecast does not mechanically reduce that player's annual Value contribution under the frozen scenario consumer;
- the four-year mean is monotone in each annual Shapley coordinate;
- Value is still determined by marginal lineup capacity rather than raw positional points.

## Exact versus set-valued Forecast authority

The Y4-Y7 Forecast authority map remains unchanged.

Exact cells:
- QB Y5 → `blanket_75_25`;
- WR Y5 → `hard_router`.

Every other Y4-Y7 position×horizon cell is set-valued.

Therefore **no current position can produce a fully exact scalar Y4-Y7 Long-Term Intrinsic**: each player traverses at least three unresolved long-horizon cells.

The scientifically authoritative Long-Term Intrinsic is consequently:
- an exact annual contribution where Forecast authority is exact;
- a per-year supported policy set elsewhere;
- a four-year **model-authority envelope** after Value consumption.

A scalar midpoint may exist for sorting/presentation, but is not Forecast authority.

## Why model-authority uncertainty must remain separate

On the historical full-window replay:
- median central model-authority envelope width: **1.26 raw Shapley units**;
- p90 width: **9.75**;
- the central model-authority envelope alone contains the realized long-term economic target only **3.54%** of the time.

That low coverage is not a defect. It proves that **model disagreement is not forecast-error uncertainty**.

When the already-governed annual within-model residual bands are propagated and then enveloped across the supported model set:
- combined nominal 80% coverage: **81.84%**;
- combined nominal 90% coverage: **91.23%**.

This is the core uncertainty finding:
1. between-model authority uncertainty describes which central Forecast representation is supportable;
2. within-model residual uncertainty describes outcome error around a given representation;
3. they must remain separately typed even when a product shows a combined outer band.

## Current Intrinsic relationship

The available 335-player current shadow is a previously frozen single-architecture long-horizon shadow. It is used only to test whether a Long-Term lens would be meaningfully distinct from Current Intrinsic, not to choose Forecast or the consumer.

Current reference versus long-term reference:
- Spearman: **0.663**;
- median absolute rank difference: **45** places;
- p90 absolute difference: **137.2**;
- **75.5%** of players differ by at least 20 ranks.

This is strong evidence that Current Intrinsic and Long-Term Intrinsic answer different questions and should not be silently averaged.

Position-level current-vs-long rank divergence is also large:
- QB median absolute difference: 61;
- RB: 51;
- WR: 42;
- TE: 48.5.

Descriptive age-band shadows show expected time-profile separation, for example young QBs rise materially in the long-term lens while aging RB/WR cohorts fall. These are diagnostics only and do not create manual youth or age coefficients.

## Raw scale relationship

The raw quantities have intentionally different semantics and magnitude.

Current 335-player reference:
- Current Intrinsic raw median: about **110.7**;
- Long-Term annual-equivalent raw median: about **9.2**.

Historical realized Y4-Y7 Long-Term raw economics are strongly zero-inflated:
- median: **0**;
- 75th percentile: **9.07**;
- 90th: **67.61**;
- 95th: **124.61**.

Therefore raw Current and Long-Term Intrinsic must not share a linear numeric calibration and must never be added.

## Research disposition

Supported:
- horizon-specific league-aware Shapley;
- continuous Y4-Y7 annual-equivalent mean;
- exact/set-valued Forecast authority preservation;
- separate model-authority and within-model uncertainty;
- separate Current and Long-Term Intrinsic lenses;
- Y8 exclusion from precise cardinal Long-Term Intrinsic.

Not supported:
- arbitrary horizon weights;
- long-term discount selected from intuition;
- Y5-only consumer;
- Y8 cardinal contribution;
- master Current+Long-Term value;
- Market or Team Utility input inside Intrinsic.

The remaining production question is implementation/promotion, not another Forecast or Value-family search.
