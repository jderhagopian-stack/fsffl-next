# Rolling FUMBLES_LOST Authority — Frozen Research Protocol

Date: 2026-09-29  
Status: **FROZEN BEFORE ROLLING-CUTOFF SCORING**  
Directive: `docs/operations/directives/20260929_FUMBLES_LOST_ROLLING_AUTHORITY.md`

## Scope

This study asks only whether the already accepted first-party exact `FUMBLES_LOST` opportunity-rate model can advance automatically with canonical completed week.

No broader Forecast family search, Y2/Y3/Y4-Y7 change, K/DST change, Intrinsic-math change, or runtime-architecture change is authorized.

## Immutable scientific semantics

Target:
- exact **lost fumbles** only;
- historical components: `sack_fumbles_lost + rushing_fumbles_lost + receiving_fumbles_lost`;
- total fumbles are forbidden as a substitute.

Opportunity:
- QB: pass attempts + sacks suffered + carries;
- RB/WR/TE: carries + receptions.

Historical rate:
- position-level lost-fumbles per opportunity;
- for a held-out season, only seasons strictly before that season may enter;
- production 2026 retains the already frozen 2021-2025 position rates.

Player role prior:
- historical opportunity/game from strictly prior seasons when available;
- otherwise prior-seasons position opportunity/game;
- fixed role stabilizer: **4 pseudo-games**.

No player-specific fumble propensity, named-player override, market input, owner input or 2026 outcome tuning is permitted.

## Frozen rolling formulation

For completed-through cutoff `c`:

1. Current evidence is **all regular-season weeks 1..c** available at that cutoff.
2. `current_games` is the player's observed game rows through `c`.
3. `current_opportunities` is the sum of accepted opportunities through `c`.
4. Historical role is unchanged from the accepted model.
5. Role estimate remains:

`role_c = (current_opportunities_c + 4 * historical_role) / (current_games_c + 4)`

when current games exist; otherwise historical role.

6. Raw season-equivalent expectation remains:

`raw_c = 17 * role_c * position_lost_fumble_rate`.

7. Global calibration is the **same accepted train-only ratio procedure**, generalized to the matching cutoff:

`scale(Y,c) = sum(actual season-equivalent post-cutoff target from pseudo-current seasons <Y) / sum(raw_c from those same rows)`.

For production 2026, `scale(2026,c)` may use only pseudo-current 2022-2025 evidence.

There is still only one global scalar per cutoff:
- no position scalar;
- no age scalar;
- no player scalar;
- no 2026 outcome refit.

8. Rolling mean:

`mean_c = max(0, scale(2026,c) * raw_c)`.

This is one algorithm parameterized by canonical cutoff, not a family/router search.

## Historical target normalization

The accepted Week-2 target was a 17-game season-equivalent pace over the remaining 15 games.

For later cutoffs, preserve that exact rate semantics with a schedule-neutral league structural denominator:

`R(Y,c) = average regular-season team games remaining after week c`.

`target(Y,c) = 17 * exact_lost_fumbles_after_c / R(Y,c)`.

`R(Y,c)` is reconstructed only from games already completed through the cutoff plus the known 17-game regular-season schedule length. No future game result or player outcome enters the denominator.

At Week 2, `R=15`, reproducing the accepted target exactly.

## Cutoffs

Evaluate **every completed cutoff Week 2 through Week 17** on recoverable 2023-2025 OOT seasons.

This includes, without privileging them:
- Weeks 3, 4, 5;
- midseason Weeks 8 and 12;
- late-season Weeks 14-17.

Week 18 has no meaningful remaining-season current forecast and is outside the rolling contract.

## Chronology

OOT folds remain:
- hold out 2023; prior seasons only;
- hold out 2024; prior seasons only;
- hold out 2025; prior seasons only.

For each held-out season/cutoff:
- target-season rows through cutoff are features;
- rows after cutoff are target only;
- calibration uses only earlier pseudo-current seasons at the same cutoff;
- no random split;
- no future season leakage.

## Rolling authority gates

The existing model is not required to “beat” a new family. The question is whether its rolling extension remains adequate.

For each cutoff c = 3..17, on the primary non-cold-start OOT population:

1. pooled rolling RMSE must be <= pooled zero/omission RMSE;
2. each held-out season RMSE must be <= 1.10 × that season's zero/omission RMSE, preserving the original stability rule;
3. pooled absolute bias must be <= 0.15 season-equivalent lost fumbles, preserving the original bias gate;
4. pooled zero-calibration gap must be <= 0.05, preserving the original zero-calibration gate.

Decision:
- if every cutoff passes, authorize one Week-2..17 rolling contract;
- if a contiguous prefix passes and later cutoffs fail because the remaining target becomes structurally too sparse, do not tune a new late-season model; stop cardinal rolling authority at the last supported cutoff and use the separately frozen materiality rule for explicit partial authority afterward;
- if failures are non-contiguous/material earlier in season, return a Management gate rather than inventing regimes after scoring.

## Uncertainty — frozen rule

Mean uncertainty remains non-zero:

`stddev = max(sqrt(mean), rolling_position_floor[position, cutoff])`.

Start from the already accepted Week-2 OOT position floors.

For each position and cutoff, compute the OOT residual RMSE of the frozen rolling mean.

The production rolling floor is the **smallest monotone empirical safety floor**:

`floor(p,c) = max(accepted_week2_floor[p], OOT_RMSE[p,k] for all validated k <= c)`.

This rule is frozen before results. It prevents later cutoffs from claiming narrower empirical residual uncertainty merely because the target window shrinks.

Cold-start / identity-light additionally retain:

`max(..., accepted_cold_start_floor)`.

Report normal-reference 80% and 90% coverage diagnostics, but do not retune the model to hit a coverage target.

## Frozen materiality / downstream-authority rule

This is separate from predictive authority.

### General rule

A missing supplemental scoring coordinate may be classified **NON_MATERIAL_PARTIAL** for a downstream fantasy-point consumer only when all of the following are true:

1. the omission is explicit in provenance; it is never marked complete;
2. exact scoring sign/multiplier is known;
3. Research provides a finite conservative one-sided **90% plausible score-impact bound** for the omitted coordinate;
4. the consumer already has a non-zero governed fantasy-point uncertainty for the same subject/horizon;
5. for every subject that can enter that consumer, the omitted-coordinate bound is no more than **10% of the consumer's existing 90% fantasy-point uncertainty half-width**:

`impact_bound_90 <= 0.10 * (1.645 * supported_fantasy_point_stddev)`.

Why 10% is frozen:
- it is a practical nuisance-scale threshold, not selected from 2026 players;
- on a centered SD scale, 10% corresponds to at most ~1% incremental variance under independence;
- the test uses a stronger one-sided bound that includes both location and uncertainty, so it does not depend on independence to describe the missing score scale.

If the consumer has zero/missing uncertainty, or any simulation-relevant subject fails the bound, downstream remains blocked.

### FUMBLES_LOST impact bound

For each position/cutoff, derive a conservative event bound using only historical OOT evidence:

`event_bound_90(p,c) = max(empirical_p99_actual_target(p,c), reference_mean(p,c) + 1.645 * floor(p,c))`.

For a league scoring coefficient `s`:

`impact_bound_90 = abs(s) * event_bound_90`.

The `reference_mean` is the position-only rolling reference used **only for impact bounding**. It is not inserted as a player Forecast when player authority is unavailable.

### Downstream semantics

If the gate passes:
- keep the fantasy-point row explicitly partial/degraded;
- retain `fum_lost` in omitted coordinates;
- retain the numeric impact bound;
- central downstream math may use the supported subtotal **only with this explicit non-material-partial authority label**;
- never relabel the subtotal as a complete Forecast;
- never write a fabricated zero `FUMBLES_LOST` observation.

Existing roster-scope rules still apply. Taxi/IR/non-consumed subjects need not block a consumer.

This materiality rule is intended to be reusable for other supplemental scoring coordinates only after each coordinate has its own governed plausible-impact bound.

## Outputs

Persist:
- cutoff/season/position metrics;
- calibration scalar table;
- rolling uncertainty floors and coverage diagnostics;
- materiality impact-bound table;
- exact contract conclusion;
- limitations;
- bounded Implementation handoff.

No production code is modified by this Research branch.
