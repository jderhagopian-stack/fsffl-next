# Rolling FUMBLES_LOST Authority Contract

Date: 2026-09-29  
Status: **SUPPORTED — RESEARCH AUTHORITY FOR BOUNDED IMPLEMENTATION**

## Decision

The accepted first-party exact lost-fumble opportunity-rate model may roll automatically from canonical completed Week **2 through Week 17**.

There is no evidence-based need for:
- a second model family;
- a cutoff router;
- a manual early/mid/late season regime;
- a position-specific calibration coefficient;
- a player-specific fumble propensity.

The smallest supported extension is one cutoff-parameterized version of the already accepted model.

## Exact rolling algorithm

For canonical `completed_through_week = c`, where `2 <= c <= 17`:

1. acquire current-season player opportunity evidence for **all completed weeks 1..c only**;
2. preserve the frozen historical position lost-fumble rates from the accepted 2021-2025 evidence;
3. preserve the four-pseudo-game player-role prior;
4. update only the current role sample with all available completed weeks;
5. apply the precomputed train-only global calibration scalar for cutoff `c`;
6. emit a 17-game season-equivalent exact lost-fumble pace;
7. apply the cutoff/position uncertainty floor.

Formula:

`role_c = (current_opportunities_1..c + 4 * historical_role) / (current_games_1..c + 4)`

when current games exist.

`raw_c = 17 * role_c * frozen_position_lost_fumble_rate`

`mean_c = calibration_scalar_2026[c] * raw_c`

Exact semantics remain:

`sack_fumbles_lost + rushing_fumbles_lost + receiving_fumbles_lost`

Total fumbles are not allowed.

## Production calibration scalars

These are generated only from 2022-2025 pseudo-current historical evidence and therefore use no 2026 outcomes.

| Completed week | Scalar |
| ---: | ---: |
| 2 | 0.615875608 |
| 3 | 0.618340607 |
| 4 | 0.617270329 |
| 5 | 0.604519448 |
| 6 | 0.610455587 |
| 7 | 0.606159780 |
| 8 | 0.612119942 |
| 9 | 0.601575454 |
| 10 | 0.591753389 |
| 11 | 0.606924417 |
| 12 | 0.587250065 |
| 13 | 0.586529095 |
| 14 | 0.604408369 |
| 15 | 0.581014992 |
| 16 | 0.558225014 |
| 17 | 0.577452698 |

The range is 0.5582-0.6183. There is no discontinuity supporting a regime split.

Machine-readable values, per-position uncertainty floors and materiality bounds are frozen in:
`ROLLING_PRODUCTION_TABLE.json`.

## Historical rolling validation

OOT held-out seasons:
- 2023;
- 2024;
- 2025.

Every cutoff Week 2..17 was scored with:
- strictly prior-season position/player history;
- only held-out-season weeks <= cutoff as current evidence;
- only prior pseudo-current seasons for calibration;
- post-cutoff exact lost fumbles as target.

Week 2 reproduces the accepted model numerically:
- RMSE **0.8105091976**;
- MAE **0.4868439130**;
- bias **+0.0508840912**;
- zero-calibration gap **0.0347225013**.

All later cutoffs pass all frozen rolling gates.

Selected checkpoints:

| Week | Rolling RMSE | Zero RMSE | Bias | Zero gap |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 0.8270 | 1.0730 | +0.0365 | 0.0279 |
| 5 | 0.8694 | 1.0847 | +0.0479 | 0.0333 |
| 8 | 0.9242 | 1.1426 | +0.0515 | 0.0280 |
| 12 | 1.0917 | 1.2307 | +0.0851 | 0.0234 |
| 14 | 1.3051 | 1.4352 | +0.0751 | 0.0149 |
| 17 | 2.4526 | 2.4958 | +0.0879 | 0.0048 |

Across all cutoffs:
- maximum pooled absolute bias: **0.08791**;
- maximum pooled zero gap: **0.03575**;
- rolling RMSE improvement over omission ranges from **1.73% to 22.93%**.

The shrinking remaining window becomes noisier in season-equivalent units late in the season, but the model remains superior to omission and within the frozen bias/calibration gates.

## Position diagnostics

The known QB weakness remains visible and is not repaired post hoc.

At Week 3:
- QB RMSE **1.7808**, bias **+0.2646**, zero gap **0.1672**;
- RB RMSE **0.7365**, bias approximately zero;
- WR RMSE **0.4407**;
- TE RMSE **0.4614**.

For context, accepted Week-2 QB diagnostics were already weaker:
- RMSE **1.7266**;
- bias **+0.3760**;
- zero gap **0.1965**.

No QB-specific calibration coefficient is introduced. The larger QB uncertainty floor remains the governed response.

## Scope boundary

Week 18 is outside this contract because there is no meaningful remaining regular-season Forecast window after the final completed week.

This contract changes no other Forecast coordinate and grants no preseason/historical backfill authority.
