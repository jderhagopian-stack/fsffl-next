# NFLverse historical research — executed 2024-to-2025 baseline predictive check

**Date:** 2026-10-14 (independent read-only GitHub-connected research).  
**Status:** EXECUTED preliminary year-over-year comparison; **not a finished historical model / FSFFL accepted baseline comparison / commercial-use clearance**.  
**Career #405 protection:** no Codex invocation, GitHub Actions, CI, Supabase, Render, production code, or changes to PR #454.

## Source and exact audit cohort

- 2024 archived weekly stats: [matttoppi/ffsim NFLverse 2024](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2024.csv), Git blob `cfc8e8951c2d0d47d4a512c672d0a8328ebc147f`.
- 2025 archived weekly stats: [matttoppi/ffsim NFLverse 2025](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2025.csv), Git blob `565ecae19212048b44a52f4eb6cf3c7ed41d31e8`.
- [Archive's provenance README](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/README.md) says NFLverse weekly release source and snapshot download date **2026-08-10**. These are **not** the official 2026-08-13 versioned release assets, so this report does not claim official checksum parity or current official-release results.
- Source CSV contains **145 columns** in each year. Count **REG** games only. Restrict `position` to **QB, RB, WR, TE**; group by exact `player_id` (GSIS), count distinct `game_id`, and sum each regular-season `fantasy_points` and `fantasy_points_ppr` (the NFLverse fantasy-score columns).
- Calculate the comparison's **half-PPR fantasy points per game** as `[sum(fantasy_points) + sum(fantasy_points_ppr)] / [2 × distinct_game_ids]`. This is the uniform NFLverse half-PPR midpoint, **not proof of exact FSFFL custom scoring**. Include only players with **at least four recorded REG games in both 2024 and 2025**, and matching QB/RB/WR/TE position across years. Do not infer absent 2025 game records as fantasy zero, injury, retirement, or career exit.
- For each position independently, the **position-only baseline** predicts 2025 points/game using the mean 2024 points/game of all 2024 players at that position with ≥4 2024 games. **Carry-forward baseline** predicts a player's observed 2024 points/game. **Fixed hypothetical blend** predicts `0.7 × 2024_player_ppg + 0.3 × 2024_position_mean_ppg`. Coefficients are illustrative, not optimized on 2025 and not calibrated against FSFFL's production model.
- Compare predictions to realized **2025 points per recorded game**; report Pearson correlation and mean absolute error (MAE) in fantasy points per game. No claim of significance, generalization or model replacement from one year.

## Executed findings

| Pos | 2024 players with ≥4 games | Paired players with ≥4 games in 2025 | Paired percentage | Pearson r: 2024 → 2025 PPG | Pos-mean MAE | Carry-forward MAE | 70/30 blended MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| QB | 58 | 44 | 75.9% | 0.653 | 5.223 | 4.123 | **3.838** |
| RB | 117 | 88 | 75.2% | 0.809 | 4.565 | **2.521** | 2.649 |
| WR | 199 | 151 | 75.9% | 0.798 | 3.490 | 2.224 | **2.061** |
| TE | 103 | 87 | 84.5% | 0.759 | 2.618 | 1.704 | **1.698** |
| **All** | **477** | **370** | **77.6%** | **0.823** | **3.747** | **2.398** | **2.327** |

**Combined illustrative error reduction:** `(2.3984934687 - 2.3268318129) / 2.3984934687 ≈ 2.99%` lower MAE vs only prior-season PPG. This is **not** a measured FSFFL forecast accuracy gain, and blending hurts RBs here. Pooled Pearson r partly reflects stable differences *between positions*; prefer the within-position numbers.

### Preliminary opportunity evidence

The source also contains usage columns that can be used as historical lagged predictors. Within the same paired ≥4-game cohort, Pearson correlation between **2024 opportunity/game** and **2025 fantasy PPG**:

| Pos | 2024 opportunity measure | r to 2025 points/game |
|---|---|---:|
| QB | Pass attempts per 2024 recorded game | 0.463 |
| RB | Rush carries + targets per 2024 recorded game | **0.805** |
| WR | Receiving targets per 2024 recorded game | **0.798** |
| TE | Receiving targets per 2024 recorded game | **0.791** |

These are **univariate observational relationships**, not evidence that usage *adds incremental prediction beyond 2024 PPG*, age, injury or position, nor proof that a source field was known before an individual 2024 game. A true challenger must measure **out-of-time, conditional incremental benefit** against the accepted FSFFL baseline.

### Availability / continuity caution

Of 477 subjects who appeared for four or more 2024 games, **370** also had four or more 2025 games (**77.6%**). A cohort's failure to meet the same future threshold can arise from fewer appearances, missing stats, non-fantasy roles, roster churn, or leaving the NFL. **Do not label 22.4% as retirements or official attrition probability.** The paired PPG correlations and MAEs are subject to **survivorship/availability selection**: they describe players who met the participation requirement in **both** years. A full Career/SIM continuation model must handle separately the chance of appearance and conditional fantasy production.

### Why this matters to FSFFL NEXT

- Historic year-prior production **does correlate** with year-next per-game production, making longitudinal history a plausible calibration challenger.
- The fixed shrinkage trial improves QB/WR/TE a little, but **worsens RB**. That suggests **position-specific shrinkage** and explicit age/workload/role stratification might be worth *testing*, not that either is automatically correct.
- Historical rushing attempts, targets, and passing attempts are available and predictive in this univariate snapshot. The next meaningful research problem is whether they beat established FSFFL forecasts *incrementally*, after guarding against age/experience confounding, 2025 availability conditioning, cutoff and data revisions.
- **Exactly one held-out next season, 2025**, is not enough for production model acceptance. A proper longitudinal replay needs many historical training cutoffs (e.g. 2003–2023 features predicting 2004–2024; leave latest seasons held out), with time-safe license/documented inputs and corresponding outcomes.
- Do not treat 2025 realized fantasy performance as a 2025 preseason forecast or add current/revised 2026 model data into the 2024 state. Data archive created in 2026 is suitable for retrospective research, **not proof original values were frozen PIT as of a historical preseason cutoff**.
- Before charging users to access any transformed original source content or deploying models trained on it, the distinct commercial upstream-rights gate documented in [contract-reach research](./nflverse-upstream-contract-reach-decision-20261014.md) still applies.
- This research result has **no automatic bearing on the nine explicit unresolved Career #405 outcomes**: those are current exact-State pipeline/inputs, not a consequence of our 2024–2025 empirical correlations.

## Source and audit method

The numbers were computed in a separate transient in-memory JS aggregation after reading the above two public GitHub blobs through the connected GitHub account. Method:
1. Parse all CSV columns including quoted fields; filter `season_type == REG`.
2. Retain four offensive fantasy positions; aggregate half-PPR fantasy points, targets, carries, pass attempts by GSIS player ID and distinct game ID separately per year.
3. Restrict 2024 baseline universe to ≥4 recorded 2024 games. Compute 2024 position means **only using 2024**.
4. For paired error/correlation universe, require ≥4 recorded 2025 games and same position; no missing-player zero-fill.
5. Compute per-position Pearson correlations with usual centered covariance divided by centered standard deviation product; compute MAE `sum(abs(observed - predicted))/N`.
6. Illustrative blend fixed at 70/30, not optimized to 2025.
7. No raw NFLverse rows, player-level proprietary evaluations, forecast models or output distributions were committed, and no external data was added to product sources.

**Next independent task:** Expand source-year pairs if licensed archived GitHub history is reachable; conduct a more credible multi-year time-split test and study whether 2024 opportunity adds incremental value over 2024 fantasy PPG; optionally audit PIT-era schemas/revisions. **Do not request Codex or shared CI until Career #405 is released**. Follow Management's noninterference requirement in [Issue #458](https://github.com/jderhagopian-stack/fsffl-next/issues/458).

**Summary verdict:** **Promising exploratory signal; research gate passes for further historical testing. No demonstrated FSFFL model improvement yet.**
