# Independent Forecasting — Historical Recovery and Year 1 Experiment 1 (2026-10-11)

**Management status:** Historical dataset recovery ACCEPTED as a research foundation; Independent Year 1 Experiment 1 evidence ACCEPTED with model disposition **REVISE**. **Research-only, not production Forecast authority.** No P0 replacement, merge/deployment of forecasting code, or commercialization clearance is implied.

## Objective and architectural boundaries

FSFFL NEXT's objective is an independently developed, history-driven Year 1 and **separately evaluated history-first multi-year dynasty/career forecasting** system with broad QB/RB/WR/TE eligibility. Third-party projections may be optional evidence/benchmarks, never a mandatory independent-model feature or permanent prerequisite for dynasty value. Preserve accepted P0/Career/Value authorities and 335-player regression parity. This research is not a Career Coverage #405 implementation or an approved fallback.

## Historical evidence recovered

Two user-provided source files, `player_stats_seasonal.RData` and NFLverse `players.csv`, plus preserved Phase 2 extraction logic, enabled reconstruction. Reported validated panel: **15,492 player-season rows**, **3,770 unique players**, QB/RB/WR/TE, **1999–2025**; **14,876** season-end Year 1 origins from 1999–2024; **11,106** observed next-season same-player rows and **3,770** absent target rows (not assumed zero). Canonical identity, duplicate-key and temporal feature/target checks passed; full-history `last_observed_season` excluded. Retrospective source files do **not** establish calendar-date PIT availability or distinguish absent target reasons. Source-specific research/commercial licensing unresolved. These are research artifact results, not independent production runtime validation.

## Experiment 1 design

Rolling season-end origins **2014–2024**, outcomes **2015–2025**, training only on examples with completed prior origins and observed next-season targets. Independent position-specific shallow histogram gradient boosting uses completed-season fantasy points, age, NFL experience, games, opportunity per game, observed history count and weak/established role band; no provider projection or Market input. Comparators: prior-season persistence and training-only position mean. Held-out errors below are **conditional on a next-season row being observed**, not whole-population accuracy.

| Position | Scored | Persistence MAE | Challenger MAE | Persistence RMSE | Challenger RMSE | Nominal 80% interval coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QB | 645 | 67.18 | 67.77 | 95.45 | 88.44 | 70.1% |
| RB | 1,353 | 41.32 | 39.16 | 60.54 | 53.17 | 76.6% |
| WR | 1,828 | 32.06 | 30.27 | 44.04 | 39.37 | 78.9% |
| TE | 1,036 | 21.78 | 20.36 | 30.82 | 28.23 | 77.3% |
| **Pooled** | **4,862** | **37.11** | **35.61** | **56.22** | **50.76** | **76.7%** |

Pooled challenger MAE improved **4.0%** and RMSE **9.7%** versus persistence on scored pairs. MAE won **33/44** position × held-out season comparisons: QB 5/11, RB 9/11, WR 9/11, TE 10/11. QB MAE **worsened**, despite improved RMSE. Nominal 80% intervals under-covered, especially QB.

## Limitations that prohibit promotion

- Of **6,548** held-out origin rows, **1,686 (25.7%)** lack next-season target rows; no retirement/no-play/injury/source-missing attribution. Conditional scored-pair results risk survivorship selection. Do not silently zero-fill or drop the issue.
- Players with **one completed NFL season**: challenger MAE **33.34** vs persistence **31.52**, **5.8% worse** (1,015 scored of 1,421 origins).
- Rookies/no prior NFL season, players absent from origin panel, no-provider-projection subgroups and history-first dynasty outcomes **not evaluated**. No accepted P0 or provider projection head-to-head could be computed from this panel.
- Season-end temporal separation is validated, **not historical calendar-date as-of publication**.
- Rights: source repository CC BY 4.0 notice does not independently clear embedded third-party NFL statistics; NFLverse rights and commercial-use scope remain unconfirmed. No production/commercial use authorized.

## Management disposition and next gate

1. **CLOSE historical recovery**; retain the validated panel and its exact reproducibility artifacts without repeating discovery/feasibility searches.
2. **ACCEPT Experiment 1 research evidence; REVISE challenger**, with P0 untouched. Do not describe it as beating P0, universal eligibility, or production readiness.
3. **Proposed bounded Experiment 2, subject to Management authorization:** establish governed next-season absence/outcome semantics, then test chronological QB and one-season-history improvements and calibrated uncertainty, directly against Experiment 1; report both conditional and defensible population-aware metrics with subgroup safety. Do not invent missing outcomes. Separate legal/source-rights approval is required before commercial use.
4. **Independent history-first dynasty/career forecasting is a separate empirical lane** and must not wait for perfect Year 1 accuracy; do not mechanically anchor future-year predictions to provider Year 1.
5. **Product delivery priority remains Career Coverage #405 → Explore → Trade**. Research work must stay bounded and nonblocking; no additional architecture/recovery cycle, merge, deploy or infrastructure change is authorized by this record.

## Evidence custody and reproducibility

The user-provided ChatGPT Library contains:
- `FSFFL_NEXT_Independent_Year1_Experiment1_Report_2026-10-11.md` and duplicate `REPORT(1).md`;
- `experiment1_reproducibility_package.zip` with `historical_recovery/run_experiment1.py`, `results.json`, `heldout_predictions.csv` and recovered-panel assets, per the report;
- historical source inputs `player_stats_seasonal.RData` and `players.csv` were provided in the Work session.

The report records a corrected run of **17.25 s**, peak RSS **164,253,696 bytes**. These assets are **not claimed to be committed to this GitHub repository**. An executing worker must retrieve/verify the exact package and its manifests before reproducing or extending Experiment 1. Do not commit licensed/raw source data or large artifacts without a separate rights and repository-storage decision.

**Related draft:** PR #450 independent forecasting architecture assessment remains a separate, unmerged documentation proposal as of this checkpoint. Reconcile overlapping docs before either PR is merged.
