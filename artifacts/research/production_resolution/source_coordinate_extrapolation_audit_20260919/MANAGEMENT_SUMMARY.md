# FSFFL NEXT - Forecast Source-Coordinate & Extrapolation Audit

Date: 2026-09-19  
Authority: audit-only research continuation  
Final outcome: **A - COORDINATE MISMATCH IDENTIFIED**

## Plain-English result

The audit found a material data-coordinate mismatch before the Forecast's extrapolation question can be judged cleanly.

The historical D0/D1 conditional-production learner was trained on the frozen I1 **standard/non-PPR fantasy-point coordinate**. The governed 2026 Year-1 board is scored in this league's **half-PPR** rules. The Outcome-B current materializer passed those half-PPR Year-1 points directly into P0 as `source_points`.

That means the current board and the historical source coordinate are not the same point unit.

This is not a small naming problem. It materially raises current RB/WR/TE source points relative to what the historical learner was trained to interpret.

## Exact scoring mismatch

Historical frozen standard scoring:
- passing yards: 0.04 / yard
- passing TD: 4
- interception: -2
- rushing yards: 0.1 / yard
- rushing TD: 6
- **reception: 0**
- receiving yards: 0.1 / yard
- receiving TD: 6
- fumble lost: -2

Current governed 2026 Year-1 scoring is identical except:
- **reception: 0.5**

The raw current projection ensemble contains receptions, so a standard-equivalent current coordinate can be calculated without a new data source.

## How large is the scoring-coordinate effect?

Using the exact already-governed current raw projection metrics:

| Position | Half-PPR / standard aggregate ratio | Half-PPR p90 | Standard-equivalent p90 |
|---|---:|---:|---:|
| QB | 1.000 | 431.6 | 431.6 |
| RB | 1.110 | 350.4 | 319.7 |
| WR | 1.285 | 269.9 | 212.4 |
| TE | 1.349 | 203.6 | 152.2 |

The independently persisted future-I1 position scoring multipliers inside the governed current Year-1 artifact are exactly the same ratios:
- QB 1.000
- RB 1.1097054683
- WR 1.2852485043
- TE 1.3491829664

That is an independent durable cross-check that the historical frozen point unit and the connected-league Year-1 point unit are intentionally different coordinates.

## Why this matters to the prior credibility result

The prior Outcome-B board compared future P0 conditional production with the half-PPR Year-1 denominator.

As an accounting-only diagnostic, converting only that denominator back to standard scoring changes the known top-10 median conditional/Y1 ratios:

| Cohort | Y2 prior | Y2 standard denominator | Y3 prior | Y3 standard denominator |
|---|---:|---:|---:|---:|
| Top 10% | 45.2% | 57.1% | 39.7% | 51.1% |
| Young top 10% | 47.5% | 58.4% | 43.1% | 53.9% |

These are **not corrected Forecasts**. P0 itself also received the half-PPR source value, so changing only the denominator is intentionally incomplete. The numbers simply show that the scoring mismatch materially exaggerated the apparent compression.

## Other semantic differences also exist

The audit also found that the two coordinates differ beyond scoring:

### Historical source
- realized season totals;
- broad player-season population;
- missed games and partial seasons are embedded in the realized total;
- zero/negative and low-games rows exist;
- spans 1999-2025;
- no era or season-length normalization.

Historical examples:
- QB median games: 7; 60.4% of rows have fewer than 10 games.
- RB median: 11; 43.5% below 10.
- WR median: 12; 38.8% below 10.
- TE median: 9; 50.3% below 10.

### Current Year 1
- forward-looking full-season projection;
- 335-player projection-covered subset;
- built from governed FFToday/Razzball raw-stat projections;
- undercovered or incomplete projection rows fail closed;
- 2026 season total;
- league half-PPR point total.

Those availability/population differences may still matter after the scoring unit is corrected.

## Why this audit does not classify the remaining support problem

The directive makes Stage 2 conditional on Stage 1 establishing semantic comparability.

Stage 1 failed.

Therefore:
- Stage 2 formal distribution/support audit: **not executed**
- Stage 3 frozen-model response-surface audit: **not executed**
- Stage 4 diagnostic counterfactuals: **not executed**

Running those stages on mixed standard and half-PPR source coordinates would produce a misleading extrapolation classification.

For context only, after mechanically removing the half-PPR reception bonus from current Year 1, the current p90 is still above the 2014-2020 historical source p90 by approximately:
- QB 1.41x
- RB 2.00x
- WR 1.51x
- TE 1.71x

So a genuine support/availability question may remain. This audit does **not** call that Outcome B yet because the prerequisite coordinate equivalence has not been restored.

## Required named examples

The explanation-only export includes Bijan Robinson, Jahmyr Gibbs, Puka Nacua, Christian McCaffrey, Aaron Rodgers, Sam Darnold, plus mechanically selected median developmental/established/veteran examples.

Examples of the scoring effect:
- Bijan Robinson: half-PPR Y1 479.9; standard-equivalent 423.2.
- Jahmyr Gibbs: 460.3 -> 412.5.
- Puka Nacua: 401.5 -> 317.0.
- Christian McCaffrey: 433.5 -> 381.3.
- Aaron Rodgers: 344.3 -> 344.3.
- Sam Darnold: 383.1 -> 383.1.

These examples are illustrations only and did not determine the outcome.

## Smallest governed correction before further Forecast research

1. From the **already-governed raw 2026 FFToday/Razzball stat ensemble**, freeze a second current Year-1 source coordinate scored under the existing `FROZEN_I1_STANDARD_SCORING` rules.
2. Use that standard-scored coordinate as P0 `source_points` and for historical/current production-calibration comparisons.
3. Keep the existing half-PPR Year-1 board as a separate league/presentation coordinate.
4. Do not compare or ratio standard-trained P0 future point quantities directly against half-PPR Year-1 points.
5. Explicitly govern the conversion of P0 future point outputs into league half-PPR units.
6. Then rerun this audit from semantic equivalence and proceed to support/extrapolation analysis only if Stage 1 passes.

This audit does **not** implement that correction.

## Reproducibility / execution accounting

Final deterministic audit verifier:
- pass: yes
- verifier SHA-256: `87f6a93fb406661a58577decabce0dfdd032b97755a9f29c734110e8303db08e`
- verifier result SHA-256: `07526078417765a7c2a48bd361d7dfcaa3b7d5b84a62783d7ca4a12ede139188`
- verifier runtime: 0.005032169 seconds
- Python 3.13.5
- pandas 2.2.3
- numpy 2.3.5

Execution counts:
- model fits: **0**
- candidate selections: **0**
- hyperparameter searches: **0**
- current-player tuning actions: **0**
- route changes: **0**
- production changes: **0**
- new external data families: **0**
- current-board rematerializations: **0**

## Final classification

**OUTCOME A - COORDINATE MISMATCH IDENTIFIED.**

The historical source and current Year-1 coordinates are not semantically equivalent in a material way. The smallest next action belongs in governed data/materialization, not in another Forecast model repair.

**STOP FOR MANAGEMENT REVIEW.**
