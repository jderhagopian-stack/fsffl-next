# Latest Intrinsic Result — Forecast Role / Opportunity Foundation

## Decision

**REJECT STATE MODEL / DEFINE NEXT DEFECT. Keep A as the temporary incumbent. Do not merge PR #138.**

The Forecast workstream added a bounded PIT role/opportunity coordinate and reran frozen D2 without changing Value economics.

## Forecast role evidence

The research layer uses only lagged football opportunity:

- QB: prior-season passing attempts/game percentile
- RB: prior-season carries + targets/game percentile
- WR: prior-season targets/game percentile
- TE: prior-season targets/game percentile

Matched role coverage on the evaluation population is **71.6%**. No market, transaction, owner, roster, team-specific, or named-player evidence is used.

## Current-state calibration

| Anchor | Multiclass Brier |
|---|---:|
| Hard Forecast Y1 mean | 0.2155 |
| Y1 distribution | 0.1217 |
| Y1 distribution + role evidence | **0.1203** |

The role model reaches 39.2% argmax accuracy, 1.446 log loss, and 1.159 ordered-state distance. Role evidence is genuinely predictive, but the gain over the Y1-distribution anchor is modest and not sufficient by itself for promotion.

## Transition calibration

The original inference-space defect was large: upward **21.8% predicted vs 36.3% observed** and downward **49.1% vs 29.2%**.

A direct deployment-feasible challenger showed the mismatch itself is repairable: upward **29.4% vs 26.9%**, downward **44.7% vs 46.7%**, with young upward **39.3% vs 42.2%**.

The role model also calibrates reasonably overall: upward **23.9% vs 21.7%**, downward **47.8% vs 49.7%**, persistence **28.4% vs 28.6%**. Young players still show some residual bias.

## Frozen D2 result

| Model | Historical MAE | Wins vs A |
|---|---:|---:|
| **A** | **23.26** | — |
| Old D2 | 34.87 | 0/12 |
| First inference-aligned D2 | 49.13 | 0/12 |
| Best direct deployable D2 | 46.10 | 0/12 |
| Role/opportunity D2 | 47.81 | 0/12 |

Therefore the hypothesis that poor state-transition calibration is the primary remaining D2 blocker is no longer supported. Even much better calibrated transition probabilities do not make frozen D2 competitive.

## Synthetic and current sanity

D2 itself remained frozen, so the established synthetic semantics remain intact: stable starter QB **11.46** > weak-path high-variance backup **1.43**; credible developmental QB **10.81**; strong-upside developmental WR **8.05** > weak-upside WR **1.44**.

No role-state model was promoted to live Forecast. The prior governed current-player sanity therefore remains authoritative: Bijan > Darnold and JSN > Judkins are coherent; KC Concepcion > Brock Bowers remains incoherent; Trey McBride > Brock Bowers remains questionable.

## Single next defect

Frozen D2 uses each player's Y1 Forecast directly, but for Y2/Y3 it substitutes the **average contribution of everyone in the predicted position/state**. That erases within-state player quality even when state probabilities are correctly calibrated.

That is the next specific defect to investigate. It is not a reason to create D3 or add another Intrinsic coefficient.

TE-premium scoring propagation remains a separate upstream Forecast/scoring-normalization integration issue.
