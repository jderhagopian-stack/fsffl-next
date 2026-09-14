# Fundamental Intrinsic Value v6 — final structural, growth, and scale audit

## Decision

The architecture survives the final audit, but the prior **uniform position-wide scarcity multiplier does not**. Production now uses **player-specific starter relevance** derived from canonical league starter demand and the governed positional Forecast production curve. No market, Team Utility, replacement surplus, owner behavior, or transaction evidence enters the conversion.

No Forecast mean-growth repair was promoted. Two bounded career-state challengers increased chronological error, including for young and low-experience players. Forecast distributions already carry breakout probability through governed uncertainty; a separate full-distribution Intrinsic challenger was also rejected because it underperformed the deterministic nonlinear starter-relevance conversion, particularly in the elite tail.

## Final equation

For governed Forecast means `Y1, Y2, Y3`, discount `d = 0.85`, continuation factor `c`, residual pedigree `p`, positional Y1 production curve `S`, and neutral starter demand `D`:

1. `C = Y1 + d·Y2 + d²·Y3 + d³·c·Y3`
2. `P = max(0, C + p)`
3. `R(y) = min(1, D / rank_S(y))`, where rank is the player's production-supply rank on the governed positional curve. This is scarcity/relevance, not replacement subtraction.
4. `E = R(Y1)·Y1 + d·R(Y2)·Y2 + d²·R(Y3)·Y3 + d³·c·R(Y3)·Y3`
5. `Intrinsic_raw = max(0, E · (1 + p/C))`
6. With final nonlinear PIT economic-raw p99 `A = 897.9723670871264`, display is `9500·sqrt(raw/A)` through the apex and an asymptotic tail toward 10,000 above it.

## Factor classification

- **Empirically fitted:** Forecast career-transition evidence; post-Year-3 continuation slopes; residual pedigree residualizer/coefficient.
- **Rule/formula-derived:** lineup starter demand; FLEX/SUPERFLEX eligibility; positional production-supply rank; player-specific starter relevance; effective-supply diagnostics.
- **Policy-defined:** 0.85 future-production discount; discrete continuation age bands where retained.
- **Presentation-only:** the 0–10,000 monotonic square-root/apex mapping.

## Perfect-Forecast structural test

The old uniform factor failed. In controlled football-realistic synthetic careers, a solid non-elite QB could outrank elite RB/WR/TE profiles mainly because every QB inherited the same positional uplift. The nonlinear conversion removed that pathology: elite production receives scarcity credit when it is actually scarce, while ordinary production does not inherit the same premium.

## Historical structural challenger result

On 6,758 chronological holdouts across 12 folds:

- incumbent uniform position factor MAE: **87.7818**
- deterministic nonlinear starter relevance MAE: **79.0363**
- fold wins: **12/12**
- aging subgroup MAE: **99.5718 → 89.1828**
- young subgroup MAE: **96.5946 → 90.2041**
- elite-tail MAE: **362.7570 → 354.4232**

Position MAE improved across all four positions:

- QB: **221.3255 → 202.5797**
- RB: **79.6550 → 71.3880**
- WR: **75.8301 → 67.4314**
- TE: **42.2562 → 38.0851**

A full-distribution starter-relevance challenger improved on the old uniform factor overall but was materially worse than the deterministic nonlinear curve and worse in the elite tail, so it was not promoted.

## Forecast growth audit

The current explicit Y2/Y3 **means** rarely rise. Realized next-season growth is common:

- QB: any +40.1%, +10% 38.4%, +20% 36.6%, +30% 34.3%
- RB: any +31.7%, +10% 29.7%, +20% 27.5%, +30% 25.7%
- WR: any +35.6%, +10% 33.3%, +20% 31.4%, +30% 29.1%
- TE: any +37.3%, +10% 35.1%, +20% 32.5%, +30% 30.6%

The richer age/experience/production-state mean-growth challenger was worse overall (**29.3652 → 29.6633 MAE**), worse for young players (**34.6607 → 35.1225**), worse for players with ≤2 years experience (**30.1386 → 30.9671**), and won only **6/17** folds. It was rejected.

Forecast distributions do carry growth probability. Diagnostic Y2 +20% growth probability versus realized frequency:

- QB: forecast **37.8%** vs realized **36.6%**
- RB: forecast **32.9%** vs realized **27.5%**
- WR: forecast **42.0%** vs realized **31.4%**
- TE: forecast **32.6%** vs realized **32.5%**

Thus breakout possibility exists in the governed distribution even where the expected mean is flat or declining. WR uncertainty is too optimistic/wide and remains a future Forecast-calibration opportunity, but the tested mean-growth repair does not improve the model and is not promoted in this PR.

## Final scale

After nonlinear structural repair, the old p99 anchor `1540.989...` is superseded. Final all-positive PIT raw p99 is `897.9723670871264`.

Full PIT display distribution (9,975 examples):

- `<1,000`: 3,637 (36.46%)
- `1,000–2,500`: 2,842 (28.49%)
- `2,500–4,500`: 1,926 (19.31%)
- `4,500–6,500`: 952 (9.54%)
- `6,500–8,000`: 326 (3.27%)
- `8,000–9,200`: 180 (1.80%)
- `>9,200`: 112 (1.12%)

The 12×18 roster-capacity cohort remains a diagnostic, not a universal scale input:

- `<1,000`: 0
- `1,000–2,500`: 392 (10.08%)
- `2,500–4,500`: 1,926 (49.54%)
- `4,500–6,500`: 952 (24.49%)
- `6,500–8,000`: 326 (8.38%)
- `8,000–9,200`: 180 (4.63%)
- `>9,200`: 112 (2.88%)

## Independence

All final audit/calibration metadata records:

- `market_inputs_used = false`
- `league_market_inputs_used = false`
- `team_utility_inputs_used = false`
- `replacement_inputs_used = false`
- `owner_inputs_used = false`
- `transaction_inputs_used = false`

Broad Market may be shown as an external comparison coordinate but is never an Intrinsic fitting target or input.
