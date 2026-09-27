# Stage 4 Forecast → Intrinsic Downstream Impact Protocol

Date: 2026-09-27  
Status: **FROZEN BEFORE CURRENT N1/N2 INTRINSIC SCORING**  
Authority: Research only. Production Forecast, H3 and Intrinsic remain unchanged.

## Purpose

Measure whether the scientifically best-supported/tied Forecast representations from the symmetric authority audit produce material downstream changes in the existing three-year Intrinsic economy.

This stage cannot tune Forecast. It cannot use named-player aesthetics to select a family. It cannot alter the frozen Shapley economics, lineup caps, discount, seed, permutations, scoring translation, or production Intrinsic.

## Forecast set

Score these already-frozen whole-Forecast representations on the governed 335-player current board:

- D1 — existing state-conditioned magnitude representation;
- N1 — frozen nonlinear HistGradientBoosting state + conditional-magnitude family;
- N2 — frozen spline two-part state + conditional-magnitude family.

No fourth family may be added.

D1 is the current production reference, not an authority prior.

## Current fit chronology

N1/N2 current shadows must use the exact already-frozen family definitions from the bounded family challenge.

For target Year 2 from completed source 2025:
- training target must be available no later than 2024.

For target Year 3 from completed source 2025:
- training target must be available no later than 2024.

No 2026 result, current named-player rank, current market value, owner behavior, roster ownership or downstream Intrinsic output may enter fitting.

## Scoring translation

The current 335-player source retains:
- standard-source Y1 fantasy points;
- connected-league Y1 fantasy points;
- the existing player-specific scoring multiplier used by the governed P0/Shapley bridge.

Apply that same already-governed multiplier to every audited future-family state mean and expectation. Do not create a family-specific scoring adjustment.

## Frozen Intrinsic economy

Use:
- exact connected league rules already persisted by the implementation research;
- frozen 2,048 Shapley permutations;
- frozen seed;
- frozen discount 0.85;
- identical Year-1 current projection for all candidate families.

Only Year-2 / Year-3 Forecast distributions may differ.

## Required outputs

### 1. Trajectory
For every player/model persist:
- Y1 points;
- Y2 and Y3 anticipated points;
- persistence probability;
- state probabilities;
- state-conditioned point means;
- Y1 Shapley;
- Y2/Y3 expected Shapley contribution;
- total raw Intrinsic.

### 2. Ranking / value deltas
Persist:
- absolute and percentage raw-Intrinsic differences for every pair;
- rank differences for every pair;
- Spearman rank correlation;
- median / p90 / max absolute rank movement;
- share moving >=10 and >=20 ranks;
- crossings of top-25, top-50, top-100 and top-200 cutoffs.

No family is declared better because its current ranks “look right.”

### 3. Uncertainty propagation
For every future horizon and model:
- state-outcome Shapley mean;
- probability-weighted Shapley outcome standard deviation;
- Monte Carlo Shapley standard errors.

Because cross-horizon state/outcome covariance is not validated, do **not** publish one exact total-Intrinsic standard deviation. Instead persist:
- zero-covariance RSS proxy;
- perfect-positive-covariance upper envelope;
- model-authority envelope across D1/N1/N2;
- explicit covariance limitation.

### 4. Material player reversal — frozen rule
A player is a material downstream reversal if **any** of the following occurs across the three audited families:
- max-min rank >= 20;
- the player crosses a top-25, top-50, top-100 or top-200 boundary;
- max-min raw Intrinsic >= 15% of the three-family median **and** >= 25 raw Shapley points.

### 5. Archetype reversal — frozen rule
Archetypes are defined only from source-time facts:
- position;
- career stage (developmental / established / veteran);
- age band.

An archetype with at least 10 players is material if either:
- >=20% of its players meet the frozen material-player-reversal rule; or
- its median max-min Intrinsic envelope is >=10% of its median three-family Intrinsic.

Named examples may be reported only after these mechanical cohort rules are applied.

## Interpretation

The downstream analysis answers:
- whether Forecast-family scientific ambiguity matters economically;
- where it matters (position/stage/age);
- whether a cell-specific Forecast difference remains material after deployment economics;
- how much of the variation is trajectory versus lineup-capacity economics;
- how model uncertainty compares with within-model state/outcome uncertainty.

It does **not** grant production authority to D1, N1, N2, or a cell router.

## Terminal requirement

Persist:
- STAGE4_PLAYER_TRAJECTORY_AND_INTRINSIC.csv
- STAGE4_PAIRWISE_RANK_VALUE.csv
- STAGE4_UNCERTAINTY.csv
- STAGE4_ARCHETYPE_REVERSALS.csv
- STAGE4_MATERIAL_PLAYER_REVERSALS.csv
- STAGE4_RESULT.json
- FINAL_AUTHORITY_CONCLUSION.md

Then close the symmetric Forecast Model Authority Audit under OPERATING_PROTOCOL.md before beginning the separately preserved Y4–Y8 Research program.
