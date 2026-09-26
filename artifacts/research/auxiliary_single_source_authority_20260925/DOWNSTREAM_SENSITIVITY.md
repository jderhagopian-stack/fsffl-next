# FSFFL NEXT — Auxiliary Coordinate Downstream Sensitivity

Date: 2026-09-25  
Directive: bounded auxiliary single-source authority study  
Authority: **RESEARCH ONLY — NON-PROMOTING**

## Purpose

Measure whether omission/addition of candidate auxiliary coordinates materially changes lineup, team, and simulated league outcomes.

This is a **paired sensitivity experiment**, not a prediction model and not a production authority promotion.

## Evidence and fixture

Historical outcomes:
- nflverse weekly player-stat evidence for 2024 regular season;
- retained via `Lolindhir/fantasy-app`;
- 2024 raw blob `7a18861cf2f19f9d6b13b4c764606cc3d5ab66bf`;
- source metadata records nflverse / CC BY 4.0.

Roster construction:
- 12 synthetic teams;
- deterministic 2024 pre-opener projection consensus from retained provider rows in `ashishkab0b/fantasy_football_2024`;
- no 2022 startup data;
- position-stratified snake allocation;
- each team: 2 QB / 4 RB / 5 WR / 2 TE / 2 K / 2 D/ST.

Starting lineup:
- QB / RB / RB / WR / WR / WR / TE / FLEX / SUPERFLEX / K / D/ST.

Each candidate was evaluated twice each week:
1. full realized scoring;
2. the same scoring with only the candidate coordinate omitted.

Lineups were independently re-optimized in both conditions.

D/ST caveat:
- this sensitivity fixture uses the reconstructable **linear D/ST event score**;
- it intentionally excludes nonlinear points-allowed buckets because aggregate PA is not valid distributional evidence;
- D/ST results are therefore event-family sensitivity, not a full Hodor-total replay.

## 50,000-run paired Simulation sensitivity

Simulation setup:
- deterministic seed: `20260925`;
- 50,000 paired runs per coordinate;
- fixed 12-team round-robin-derived 14-week schedule;
- six-team playoffs;
- historical 2024 weekly score states bootstrapped with the same random draws under full vs omitted conditions;
- paired draws isolate the candidate-coordinate effect rather than Monte Carlo noise.

Probability deltas below are **percentage points**, not relative percent changes.

| Coordinate | Lineup change | Mean abs team-week Δ | P95 team-week Δ | Max team-week Δ | Mean 14-week team Δ | Max 14-week team Δ | Max exp-wins Δ | Max playoff Δ | Max title Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FUMBLES_LOST (-2) | 2.94% | 1.126 | 4.0 | 6.0 | 15.108 | 21.960 | 0.292 | **3.026 pp** | **1.576 pp** |
| TWO_POINT_CONVERSIONS | 0.98% | 0.545 | 2.0 | 8.0 | 7.933 | 12.000 | 0.176 | **3.132 pp** | 0.558 pp |
| PLAYER_SPECIAL_TEAMS_TD | 0.49% | 0.025 | 0 | 5.2 | 0.433 | 5.2 | 0 | 0.018 pp | 0.048 pp |
| FUMBLE_RECOVERY_TD | 0% | 0.029 | 0 | 6.0 | 0.500 | 6.0 | 0 | 0.004 pp | 0.022 pp |
| K_FG_60PLUS_INCREMENT (+1) | 0% | 0.010 | 0 | 1.0 | 0.167 | 1.0 | 0 | **0.040 pp** | **0.008 pp** |
| K_FG_MISS (-1) | 3.92% | 0.216 | 1.0 | 2.0 | 3.083 | 6.0 | 0.175 | **2.312 pp** | **1.360 pp** |
| K_XP_MISS (-1) | 0.98% | 0.049 | 0 | 1.0 | 0.833 | 2.0 | 0 | **0.052 pp** | **0.034 pp** |
| DST_SAFETY (+2) | 1.47% | 0.049 | 0 | 2.0 | 0.500 | 2.0 | 0 | **0.070 pp** | **0.018 pp** |
| DST_BLOCKED_KICK (+2) | 0.98% | 0.201 | 2.0 | 4.0 | 2.750 | 6.0 | 0.059 | **1.188 pp** | **1.002 pp** |
| DST_DEF_2PT_RETURN (+2) | 0% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DST_SPECIAL_TEAMS_TD (+6) | 1.47% | 0.348 | 3.55 | 12.0 | 5.417 | 24.0 | 0.182 | **3.444 pp** | **1.484 pp** |
| DST_FORCED_FUMBLE (+1) | 4.41% | 1.005 | 2.0 | 5.0 | 13.583 | 22.0 | 0.147 | **2.536 pp** | **2.060 pp** |
| DST_FUMBLE_RECOVERY (+1) | 5.39% | 0.657 | 2.0 | 4.0 | 8.917 | 16.0 | 0.059 | **0.484 pp** | **0.176 pp** |

## League-relative / Team Utility proxy

The research fixture does not call or contaminate production Team Utility. It uses two transparent proxies:

1. player/position rank displacement in `AUXILIARY_COORDINATE_MATERIALITY.csv`;
2. 14-week synthetic team scoring rank under full vs omitted conditions.

Observed team-rank effects:
- FUMBLES_LOST: mean shift 0.167, max 1;
- DST_SPECIAL_TEAMS_TD: mean shift 0.333, max 2;
- DST_FORCED_FUMBLE: mean shift 0.167, max 1;
- all other tested candidates: zero mean team-rank shift in this fixture.

Zero team-rank shift is not sufficient by itself for auxiliary classification. Playoff/title sensitivity and source quality remain separate gates.

## Worst observed / bounded empirical stress

The study treats:
- p99 seasonal contribution as an empirical bounded stress case;
- max observed seasonal contribution and max team-week delta as worst-observed evidence.

This prevents a six-point event from qualifying merely because 95% of subject-seasons are zero.

Examples:
- K 60+ incremental: p95 1 point, p99 ~2.29, max season 3, max team-week 1;
- XP miss: p95 3, p99 4, max season 4, max team-week 1;
- player special-teams TD: p95 0, but max season 12 and max team-week 5.2;
- D/ST special-teams TD: p95 12, max season 24, max team-week 12.

The latter two are therefore not bounded auxiliaries despite high zero-rates.

## Main conclusions

### Clearly bounded by outcome sensitivity
The following pass the **materiality** side of the proposed auxiliary contract in this evidence:
- K 60+ **incremental** point above an already-supported 50+ base;
- K XP miss at -1;
- D/ST safety at +2;
- defensive two-point return at +2.

Passing materiality does **not** establish source authority.

### Clearly material / core
The following fail materiality or downstream sensitivity:
- FUMBLES_LOST at common -1/-2 profiles;
- FG misses at -1;
- two-point conversions;
- D/ST blocked kicks in the tested +2 profile;
- D/ST special-teams TD;
- D/ST forced fumbles;
- D/ST fumble recoveries.

### Rare but high-severity tails
Player special-teams TD and fumble-recovery TD are extremely rare, but their six-point event size creates large worst-case jumps. They should remain explicit tail/unsupported coordinates unless a separate governed model/source earns authority; rarity alone is not sufficient.

## Limitations

- This is a 2024 downstream sensitivity fixture, not a production forecast.
- It uses synthetic rosters seeded by authentic pre-opener projection evidence, not the 2022 startup.
- D/ST PA bucket scoring is excluded because this study refuses to substitute aggregate PA means for game-level distributions.
- Simulation is a sensitivity microscope: paired conditions use identical random draws.
- A coordinate must also pass source-quality, rights, semantics, health, and uncertainty gates before any production use.

