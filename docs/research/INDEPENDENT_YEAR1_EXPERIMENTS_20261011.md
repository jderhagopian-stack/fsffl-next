# Independent Year 1 forecasting experiments — 2026-10-11

## Decision

**Experiment 1 accepted as research evidence; challenger status REVISE. Experiment 2 also REVISE. Neither experiment authorizes production use or changes accepted Forecast/P0.** The independent history-first dynasty/career objective remains a separate roadmap workstream and does not depend on perfecting Year 1 forecasting.

## Recovered panel and evidence authority

The accepted recovery rebuilt **15,492** QB/RB/WR/TE player-season rows for **3,770** unique canonical players across **1999–2025**. It provides **14,876** season-end origins and **11,106** observed same-player next-season rows. Missing next-season rows remain missing. The future-derived `last_observed_season` and contemporary status/latest-season fields were excluded. The panel verifies season-end temporal feature/target separation but has no record-level historical publication timestamps, so it does **not** establish exact calendar-date availability. Rookies without completed NFL seasons, nonparticipants/injured players absent at the origin, and provider-projection availability cannot be labeled from this evidence.

Inputs were supplied `player_stats_seasonal.RData` and NFLverse `players.csv`; the Phase 2 generator, full source SHA-256 hashes, transformations, identity checks, and original panel validation are preserved in the recovery reproducibility package in ChatGPT Library. The textbook repository license states CC BY 4.0, but its scope over embedded third-party NFL statistics is unresolved; the NFLverse source-specific license and FSFFL research/commercial use permission are also unresolved. No production/commercial use is authorized by these experiments.

## Experiment 1 — baseline independent signal

Rolling chronological season-end origins **2014–2024** (held-out targets **2015–2025**). For each origin `t`, the position-specific model trained only on earlier origins with observed target rows. The modest history-only challenger used completed source-season points, age, experience, games, position-specific opportunity/game, past observed seasons, and a role band derived from the completed source season. It used no external projection or Market inputs. Position persistence was the comparator. All features precede the next-season target; this is season-end temporal validation, not calendar-date preseason PIT proof.

| Position | Scored pairs | Persistence MAE / RMSE | Experiment 1 MAE / RMSE | Experiment 1 bias | Nominal 80% interval coverage |
|---|---:|---:|---:|---:|---:|
| QB | 645 | 67.18 / 95.45 | 67.77 / 88.44 | +1.74 | 70.1% |
| RB | 1,353 | 41.32 / 60.54 | 39.16 / 53.17 | +3.68 | 76.6% |
| WR | 1,828 | 32.06 / 44.04 | 30.27 / 39.37 | +3.53 | 78.9% |
| TE | 1,036 | 21.78 / 30.82 | 20.36 / 28.23 | +0.47 | 77.3% |
| **Pooled** | **4,862** | **37.11 / 56.22** | **35.61 / 50.76** | **+2.68** | **76.7%** |

Experiment 1 reduced observed-pair pooled MAE **4.0%** and RMSE **9.7%**, beating persistence MAE in 33/44 position-season cells. QB MAE did not improve. One-completed-season players had MAE **33.34** vs persistence **31.52**. Nominal 80% intervals covered 76.7% overall and 70.1% for QB.

## Experiment 2 — targeted revision and direct comparison

The same underlying HGB football predictor, test origins and observed-pair cohort were retained. Experiment 2 added two leak-safe research procedures:

1. **Selection sensitivity:** for each origin `t`, a logistic model trained on earlier origin features estimated whether a next-season source row would be observed. Inverse-probability weights used prior-row prevalence / estimated probability, propensity bounds `[0.05, 0.95]`, and weight cap 5. Metrics use observed outcomes only. This is an **IPW sensitivity under missing-at-random conditional on measured features**, not recovery of missing outcomes or a correction for unknown MNAR exits.
2. **Prequential calibration:** affine position/history-group calibration fitted on out-of-origin forecasts from 2005–2009. A separate 2010–2013 out-of-origin block scored the 80% conformal interval radius; it did not fit its own calibration map. The final untouched comparison remains 2014–2024. The held-out coverage, not an assumption of exchangeability, is reported.

Experiment 2's base predictor exactly reproduced Experiment 1 for all **4,862** observed held-out pairs. It predicted all **6,548** held-out origins; the **1,686** absent targets remained unscored and unimputed.

| Position | Observed | Experiment 1 MAE / RMSE | Experiment 2 MAE / RMSE | Experiment 2 bias | E1 → E2 interval coverage | E1 → E2 mean width |
|---|---:|---:|---:|---:|---:|---:|
| QB | 645 | 67.77 / 88.44 | 67.90 / 89.29 | −0.03 | 70.1% → 76.7% | 185.0 → 199.5 |
| RB | 1,353 | 39.16 / 53.17 | 39.89 / 53.42 | +2.76 | 76.6% → 79.2% | 120.9 → 121.9 |
| WR | 1,828 | 30.27 / 39.37 | 30.57 / 39.77 | +4.62 | 78.9% → 85.0% | 99.9 → 111.1 |
| TE | 1,036 | 20.36 / 28.23 | 20.67 / 28.37 | +1.04 | 77.3% → 86.0% | 60.4 → 77.5 |
| **Pooled** | **4,862** | **35.61 / 50.76** | **36.01 / 51.17** | **+2.72** | **76.7% → 82.5%** | **108.6 → 118.7** |

**Point accuracy regressed slightly:** pooled MAE increased 1.1% and RMSE 0.8% vs Experiment 1. QB bias moved close to zero, but QB MAE/RMSE did not improve; vs persistence, QB MAE remains worse (67.90 vs 67.18). E2 intervals moved pooled coverage above the 80% target, but were wider and over-covered WR/TE while still under-covering QB (76.7%). One-season-history intervals covered 82.5% pooled, but only 72.7% for QB. This is not uniformly calibrated uncertainty.

### Missingness and selection

Across held-out origins, **4,862/6,548 (74.3%)** have a next-season row and **1,686/6,548 (25.7%)** do not. Row rates were QB 76.8%, RB 73.6%, WR 73.5%, TE 74.9%. The source does not say whether an absent row means retirement, injury, no participation, zero-stat season, identity failure, or source omission. Neither experiment converts absence to zero or claims population-unconditional error.

Observed-row status is predictable from prior-season measured features (position AUCs: QB **0.755**, RB **0.805**, WR **0.823**, TE **0.798**), so row absence is not safely treated as completely random. The model underpredicted held-out observed-row rates by 1.4–3.7 percentage points by position. Under the conditional-MAR IPW sensitivity, pooled Experiment 1 vs Experiment 2 MAE/RMSE were **33.69/49.12** vs **34.07/49.47**; this does not reverse E2's slight regression and cannot identify target outcomes for absent players. No IPW weights hit the cap; effective sample sizes remain in `results.json`.

### One-season history and QB failures

| Subgroup | Origins / observed / missing | Persistence MAE | Experiment 1 MAE | Experiment 2 MAE | E2 IPW sensitivity MAE |
|---|---:|---:|---:|---:|---:|
| All positions, one completed NFL season | 1,421 / 1,015 / 406 | 31.52 | 33.34 | 34.52 | 32.01 |
| QB, one completed NFL season | 134 / 99 / 35 | 68.49 | 72.73 | 73.47 | 71.05 |

The targeted affine correction **worsened** the one-season subgroup relative to both Experiment 1 and persistence. Sparse QBs remain particularly weak. Four-plus-season history improved modestly over Experiment 1 (pooled subgroup MAE 38.08 → 37.83), but other buckets/positions did not consistently benefit. Rookies with no completed NFL season are not part of these subgroup counts.

## Decision and bounded next choice

**REVISE.** Independent history-only forecasting shows signal for returning observed outcomes, but the Experiment 2 calibration layer did not improve point accuracy; sparse-history and QB weaknesses remain; target missingness is predictable but its cause/outcome is unavailable; and conformal intervals are still position-miscalibrated. No P0 or external projection head-to-head is possible from this panel. No production authority, P0 change, deployment, merge, or commercial-use permission follows.

Any next Year 1 experiment should first use an approved source that distinguishes true zero/no-participation/retirement from missing coverage, or explicitly keep the estimand conditional on an observed next-season row. Do not impute zeros without such evidence. Revisit the one-season/QB segment only with the missing-outcome scope stated. Independently, retain **history-first dynasty forecasting** as a separate roadmap objective; it must not wait on resolving Year 1 selection or rookie coverage.

## Reproducibility

Experiment 1 report and reproduction package are retained in ChatGPT Library as `FSFFL_NEXT_Independent_Year1_Experiment1_Report_2026-10-11.md` and `experiment1_reproducibility_package.zip`. Experiment 2 report, script, results JSON, and held-out predictions are retained with the same Management evidence package. Experiment 2 used the same recovered panel and source hashes. The corrected run took **12.98 seconds**, peak process RSS **182,321,152 bytes** (~173.9 MiB), Python 3.12.14 / pandas 2.2.3 / NumPy 2.3.5 / scikit-learn 1.8.0. These experiments changed no production files and ran no infrastructure or full product test suite.
