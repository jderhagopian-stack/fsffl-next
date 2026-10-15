# NFLverse historical data — independent 2024→2025 forward-production pilot

**Performed:** 2026-10-14 (read-only GitHub connector analysis; no Codex, GitHub CI/Actions, cloud deployment, Supabase, Sleeper refresh or product code).  
**Status:** **Exploratory research complete; product/model promotion NOT authorized.**  
**Related:** [Research #458](https://github.com/jderhagopian-stack/fsffl-next/issues/458), [executed 335 reference ID audit](./nflverse-real-2024-2025-id-coverage-20261014.md), [commercial source-use decision](./nflverse-upstream-contract-reach-decision-20261014.md).

## Actual data and reproducible analysis recipe

Used `matttoppi/ffsim` public GitHub archive, [archival source note](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/README.md), citing NFLverse's original `stats_player` releases and stating downloads were captured **2026-08-10**.

| Season | Archived file | Exact Git blob SHA |
|---|---|---|
| 2024 | [stats_player_week_2024.csv](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2024.csv) | `cfc8e8951c2d0d47d4a512c672d0a8328ebc147f` |
| 2025 | [stats_player_week_2025.csv](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2025.csv) | `565ecae19212048b44a52f4eb6cf3c7ed41d31e8` |

**Processing:** Parse CSV correctly with quoted embedded commas, filter `season_type == REG` and `position ∈ {QB,RB,WR,TE}`, group by exact `player_id` in each year; sum weekly `fantasy_points` and `receptions` into annual `half_ppr_proxy = sum(fantasy_points) + 0.5 × sum(receptions)`. NFLverse `fantasy_points` is standard fantasy scoring; this proxy is **not confirmed parity** with every FSFFL customized scoring rule. Keep per-player totals for targets, carries and receiving air yards. Construct the 2024 eligible population, then determine whether each identifier has any 2025 regular-season stat row. **No 2025 data is used to construct predictors or position averages.**

**Data handling:** The historical archives were parsed transiently into memory from public GitHub blobs; **no 2024 or 2025 raw rows copied into FSFFL Git**, no model fit or trainable artifact, no distribution to users. Snapshot files differ from the subsequently revised official releases on 2026-08-13; archive Git SHAs are NOT current official asset SHA256. This is a historical/backtest feasibility signal, not a data-source rights warranty or point-in-time production-ready archive.

## 1. Forward observed-statistical-record evidence (2024→2025)

| Position | Any 2024 regular-season row | Also has any 2025 regular-season row | No 2025 row | Observed-row rate |
|---|---:|---:|---:|---:|
| QB | 78 | 63 | 15 | 80.8% |
| RB | 148 | 106 | 42 | 71.6% |
| WR | 235 | 177 | 58 | 75.3% |
| TE | 127 | 106 | 21 | 83.5% |
| **Total** | **588** | **452** | **136** | **76.9%** |

**Crucial:** A missing statistics row is **not** proof of retirement, injury or a zero-value outcome; `observed-row` only means a player ID has one or more published regular-season NFLverse stat rows. This is a distinct input to Career modeling's probability of future production/participation, **not yet a validated survival probability**.

An informative source-observed stratification: Of the 156 players with at least **100 half-PPR points in 2024**, **150 (96.2%)** had a 2025 stat row. Among **251** players with **0 to under 25 points in 2024**, only **145 (57.8%)** had a 2025 row. Negative-score cases, if any, fall outside that latter bucket. This supports evaluating production/usage as a predictor of subsequent *recorded production*, but 2025 availability is not the same thing as NFL employment, health or career survival.

## 2. Simple out-of-year production predictor comparison

**Evaluate only the 452 players with both-year source rows**, i.e. conditional 2025 fantasy production, not unconditional Career expected value. This selection knowingly excludes source-absent subjects; do not use its error metrics as a complete career-distribution accuracy statement.

Two pre-specified simple *2024-information-only* predictions of 2025 season-total points:

- **Carry-forward**: `prediction = 2024 player half_ppr_proxy`.
- **Illustrative 25% positional shrinkage**: `prediction = 0.75 × player's 2024 half_ppr_proxy + 0.25 × mean half_ppr_proxy of all 2024 players at their same position`. The position average includes **all 2024 subjects** (not just survivors) and is calculated without accessing 2025 data.

MAE and RMSE below refer to **season-total half-PPR points**, with **lower better**:

| Position | Observed both years | Carry-forward MAE | Shrunk MAE | Carry-forward RMSE | Shrunk RMSE | RMSE improvement |
|---|---:|---:|---:|---:|---:|---:|
| QB | 63 | 64.92 | **64.24** | 92.97 | **84.02** | 9.6% |
| RB | 106 | **41.62** | 42.69 | 64.64 | **61.21** | 5.3% |
| WR | 177 | 35.85 | **34.18** | 52.02 | **46.51** | 10.6% |
| TE | 106 | 25.12 | **23.69** | 34.73 | **32.06** | 7.7% |

The 75/25 formula is a simple sensitivity comparison (among an exploratory 0%, 25%, 50%, 75%, 100% previous-year weighting sweep), **not a fitted or validated optimal coefficient**. Choosing it by examining the same 2025 results would be hindsight; this table proves only that the chosen formula is consistent with useful mean reversion in this sample. It does **not** compare against the current FSFFL Year-1 forecast and does **not** measure lift from adopting NFLverse.

## 3. Signals about historical usage features

Pearson correlation with **2025 half-PPR production among players who have 2025 rows**. These are single-variable correlations, not additive feature contributions:

| Position | 2024 fantasy points → 2025 points | 2024 targets → 2025 points | 2024 receiving air yards → 2025 points | 2024 carries → 2025 points |
|---|---:|---:|---:|---:|
| QB | 0.712 | 0.235 | 0.221 | 0.540 |
| RB | 0.756 | 0.637 | -0.002 | 0.732 |
| WR | 0.738 | 0.727 | 0.664 | 0.233 |
| TE | 0.762 | **0.816** | **0.809** | 0.045 |

For tight ends, 2024 targets and receiving air yards have higher standalone correlations with 2025 total fantasy scoring than 2024 fantasy points in this one-year sample. This suggests testing opportunity-based inputs. **It does NOT show that targets or air yards improve a model already using 2024 points**; requires properly held-out multivariate comparison, point-in-time feature availability, and accepted baseline parity. QB rushing and RB workload also merit position-specific tests.

## Model implications worth testing, not adopting

1. **Career Intrinsic:** Separate conditional next-year production from probability of seeing a next-year production record. Sample 2024→2025 row coverage (588→452) highlights need for this two-part design and explicit no-row reasons.
2. **Year 1/three-year forecasts:** Historical production/usage can inform mean reversion, age-stage calibration, year-to-year repeatability and opportunity-adjusted outcomes; do not overwrite currently accepted projections based on one retrospective year.
3. **TE opportunity:** Historical targets and air yards may be valuable test features, but standalone correlations are not evidence of additional predictive lift conditional on existing accepted inputs.
4. **Broader analysis:** Add earlier seasons to create true chronological development and holdout periods; fit on years strictly before the evaluation season, test separately on held-out 2025 or 2026 after availability/PIT gating, compare *accepted FSFFL forecast* not merely carry-forward. Separate participation and production scoring.
5. **Career #405:** No effect on the current implementation. A research result is not a mandate to retune ongoing Career calculations or expand any model's coverage.

## Important constraints / non-results

- **Only 2024→2025** evaluated; *no* multi-year age/experience development panel or multiple independent held-out years. The archived files predate late-August 2026 revisions of the official CSVs.
- **No evidence about incremental gains over FSFFL's current predictive stack** until a direct forecast comparison is run on matching exact-State and league scoring rules.
- **Sample selection bias:** Conditional production metrics exclude 136 players without 2025 rows. We have *not* treated them as zeros; participation inference remains limited.
- **Raw 145 source columns include potentially distinct provider/rights information (headshot URLs, advanced features).** This pilot did not download images or display them, and did not test integration rights beyond scoped research.
- **No full commercial product rights certification** was conferred by this research.

**Management position:** This demonstrates a viable **independent historical-research lane today**, without interrupting Codex's Career #405 work. Next meaningful step is more seasons / multiple genuine chronological holdouts, with strict source rights and publication-date checks. No production code, models, database, CI or deployment changes authorized.
