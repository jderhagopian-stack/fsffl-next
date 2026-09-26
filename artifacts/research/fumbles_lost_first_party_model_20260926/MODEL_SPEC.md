# FSFFL NEXT — First-Party FUMBLES_LOST Forecast Model Specification

Updated: 2026-09-26 UTC  
Research directive: first-party exact player `FUMBLES_LOST` recovery  
Proposed production model version: `next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`

## Authority scope

This model owns exactly one current Forecast coordinate:

`ForecastMetric.FUMBLES_LOST`

It does **not** alter, rebase, blend, or recalibrate any passing, rushing, receiving, K, D/ST, Value, Intrinsic, Simulation, or other Forecast coordinate.

The target is exact **lost fumbles**, never total fumbles.

Historical target semantics are reconstructed from the governed nflverse weekly components:

`sack_fumbles_lost + rushing_fumbles_lost + receiving_fumbles_lost`.

## Current target

For canonical State with `completed_through_week = 2`, the model predicts a 17-game season-equivalent current pace for exact lost fumbles over the remaining 15-game structural window:

`target = 17 * exact_lost_fumbles_weeks_3_plus / 15`

This is a current scoring/Simulation target-shape bridge. It is not a claim that the model existed preseason and it is not a projected final-season box score.

For the current FSFFL State persisted at `2026-09-26T02:07:22.445124Z`, canonical State reports `completed_through_week=2`, exactly matching the validated cutoff.

Do not silently use this v1 model for a different completed-week cutoff. A rolling later-cutoff version requires either:
- a separately validated cutoff contract; or
- a governed transformation whose equivalence is demonstrated.

## Inputs

### Historical training inputs

Strictly prior seasons only.

For each position:
- exact lost fumbles;
- games played;
- opportunity events.

No future season is used in a fitted rate, role prior, or calibration scalar.

### Current point-in-time inputs

Weeks 1–2 of the target season only.

Opportunity definition:
- QB: `pass_attempts + sacks_suffered + carries`;
- RB/WR/TE: `carries + receptions`.

The QB schema was explicitly corrected from the nonexistent generic `sacks` field to nflverse `sacks_suffered`; the schema-corrected rerun retained the accepted result.

## Model

The selected model is deliberately small.

### 1. Historical position lost-fumble rate

For position `p`:

`position_rate_p = prior_season_lost_fumbles_p / prior_season_opportunities_p`

Only seasons strictly before the target season are eligible.

### 2. Current role estimate

Player historical role:

`historical_opportunity_per_game = prior_season_opportunities / prior_season_games`

If the player has no history, use the prior-seasons position opportunity/game rate.

For a player with Weeks 1–2 current evidence:

`role_opportunity_per_game = (current_opportunities + 4 * historical_opportunity_per_game) / (current_games + 4)`

The four pseudo-games are a fixed predeclared role stabilizer.

### 3. Uncalibrated expectation

`raw_expectation = 17 * role_opportunity_per_game * position_rate`

### 4. One global train-only calibration scalar

The uncalibrated opportunity model showed useful rank/RMSE signal but systematic positive bias. The only accepted challenger adds one global scalar trained from earlier pseudo-current seasons.

For held-out season `Y`, the scalar is fitted only on pseudo-current seasons before `Y`.

Chronological scalars:
- held-out 2023: `0.6955593949914197`;
- held-out 2024: `0.6645928163671334`;
- held-out 2025: `0.6376446223777328`;
- current 2026 fit from pseudo-current 2022–2025 evidence: `0.6158756078393594`.

Production mean for the current validated cutoff:

`mean_fumbles_lost = 0.6158756078393594 * raw_expectation`

No named-player, team, age, or position-specific calibration coefficient is used.

## Models rejected

The governed study explicitly tested and rejected:
- zero/omission as a predictive Forecast;
- position game-rate;
- uncalibrated position opportunity-rate;
- player-history-shrunk fumble rate;
- player-history plus current-season fumble-rate update.

The player-specific rate challengers were less stable and materially worse in OOT RMSE. V1 therefore does not use a player's personal fumble history to tune his fumble propensity.

## Out-of-time validation

Chronological folds:
- hold out 2023; train through 2022;
- hold out 2024; train through 2023;
- hold out 2025; train through 2024.

For every held-out season:
- Weeks 1–2 are the only target-season inputs;
- Weeks 3+ are target only;
- future seasons are unavailable;
- no random split is used.

Primary OOT population excludes only true cold starts with neither prior history nor Weeks 1–2 evidence.

Combined primary OOT sample: **1,599 player-seasons**.

Selected-model metrics:
- RMSE: **0.8105091976** lost fumbles;
- MAE: **0.4868439130**;
- bias: **+0.0508840912**;
- Spearman rank correlation: **0.4450645773**;
- actual-zero rate: **0.7761100688**;
- mean predicted-zero probability: **0.7413875675**;
- zero-calibration gap: **0.0347225013**;
- zero Brier score: **0.1416032475**;
- tail RMSE: **1.3696260176**.

Baselines:
- zero/omission RMSE: **1.0425150391**;
- position game-rate RMSE: **1.0475162746**.

Selected-model RMSE improves approximately **22.25%** versus omission and **22.63%** versus position game-rate.

Season RMSE:
- 2023: **0.9103468343**;
- 2024: **0.7819080813**;
- 2025: **0.7332392771**.

Each held-out season clears the predeclared stability gate against its same-season zero baseline.

## Position diagnostics

OOT residual RMSE:
- QB: **1.7266303754**;
- RB: **0.7375205714**;
- WR: **0.4424922528**;
- TE: **0.4524060196**.

All four position groups improve RMSE versus omission.

QB remains the weakest-calibrated subgroup:
- bias: **+0.3760**;
- zero-calibration gap: **0.1965**.

This is not hidden. The production uncertainty floor is therefore materially larger for QBs.

## Predictive uncertainty

Uncertainty is non-zero by construction.

For a normal evidence row:

`stddev = max(sqrt(mean_fumbles_lost), position_OOT_residual_RMSE)`

Position OOT floors:
- QB: `1.7266303753562966`;
- RB: `0.7375205714435535`;
- WR: `0.4424922528480551`;
- TE: `0.4524060195836409`.

Overall diagnostic OOT residual floor:
- `0.8105091976152538`.

Cold-start/identity-light OOT stress floor:
- `0.789918699230448`, from 177 cold-start player-seasons.

For `cold_start` or `identity_light` rows:

`stddev = max(sqrt(mean), position_floor, cold_start_floor)`

Do not convert missing identity/history to zero uncertainty.

## Current-player coverage

Current 335-player Forecast board:
- 335 total QB/RB/WR/TE rows;
- 300 retained GSIS mappings;
- 27 deterministic unique normalized-name + position recoveries;
- 327/335 mapped: **97.6119%**;
- 8 identity-light rows.

Evidence tiers:
- history + current: 258;
- history only: 40;
- current only: 28;
- cold start: 1;
- identity-light/unmapped: 8.

The eight identity-light rows are currently rostered only on BENCH/TAXI in the existing FSFFL State. They must still remain explicit degraded-evidence rows because lineup state can change.

Identity recovery rule is data-only:
- normalized name + position;
- accept only exactly one current match;
- ambiguous or absent match remains identity-light;
- never use player outcome or projection magnitude to resolve identity.

## Production PIT boundary

A deployed first-party model artifact is valid only from its actual model evaluation/acquisition cutoff.

Required metadata:
- model version;
- training seasons;
- target season;
- completed-through week;
- exact source asset hashes;
- evaluation/build timestamp;
- current input effective/capture timestamp;
- canonical State ID/hash;
- model coefficient/scalar;
- uncertainty contract version;
- player evidence tier.

Hard rules:
- `preseason_eligible=false`;
- `annual_preseason_snapshot_eligible=false`;
- no historical PIT claim before the model artifact's actual authority timestamp;
- no backfill into 2026 preseason;
- no mutation of the retained preseason raw Forecast.

## Data lineage

Machine-readable hashes:
- `DATA_LINEAGE.json`.

Research workflow:
- `.github/workflows/fumbles-lost-first-party-research.yml`.

Research implementation:
- `scripts/run_fumbles_lost_first_party_research.py`.

Accepted final research run:
- GitHub Actions run `36215577007` (final evidence-persistence pass after all model/schema/uncertainty changes).

The study is reproducible from public governed football outcome data plus the retained current FSFFL player board.
