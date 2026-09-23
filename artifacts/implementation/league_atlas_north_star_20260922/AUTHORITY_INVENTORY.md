# League Atlas North Star — Stage A authority inventory

Date: 2026-09-22
Base main: `8de97c51c5759129441f61f82c7161a7693ac54e`
Superseded draft reviewed: PR #163 @ `64cd848ec90542f2217641f30883885453bb59f4`

## Product rule

League Atlas is Presentation over governed State, Forecast, Simulation, Value, Team Utility and Analytics evidence. It does not create model truth, a universal team score, a team Intrinsic total, summed Market percentiles, League Market Value, recommendation strength, or acceptance probability.

## Visual / interaction -> authority map

| Atlas concept | Governed source | Authority | Availability / constraint |
| --- | --- | --- | --- |
| Current W-L-T, points-for, current standings rank | canonical `LeagueState.matchups` | Point-in-Time State | Available when completed matchup scores exist. Presentation may deterministically aggregate completed matchups only. |
| Current week / completed weeks | canonical `LeagueState.matchups` | Point-in-Time State | Available from scored matchup rows. |
| Forward expected wins, playoff probability, first-place probability, championship probability | persisted/in-memory `LiveSimulationAnalyticsResult.simulation_result.outcomes` | Simulation | Available only when the current runtime already has matching Simulation. Atlas must not trigger a new 50,000-run Simulation synchronously. |
| Competitive state | `TeamUtilityVector.calculated_competitive_state` on current team views | Team Utility | Available where Simulation-backed team views exist; otherwise explicit unavailable/unclassified. |
| Frozen preseason team expectation | preserved preseason Forecast + point-in-time preseason team State snapshot | Forecast + State + Analytics | Only available if an exact compatible historical State snapshot can be joined without postdating Forecast evidence. Player-level preseason Forecast alone is insufficient to fabricate a team preseason rank. |
| QB/RB/WR/TE positional strength | `TeamAnalyticsView.position_strengths` | Team Utility diagnostic from governed optimized Forecast production | Available. 100 = league-average optimized starter production; exact rank/index shown on interaction. K/DEF unsupported. |
| Position-room players / projected roles / season projections | `TeamAnalyticsView.players` | State + Forecast + Analytics | Available. Order can use governed projected-starter flag/lineup slot then governed full-season projection; no invented football archetypes. |
| Depth / fragility | `TeamUtilityVector.roster_resilience` plus actual position-room player/forecast coverage | Team Utility + State/Forecast | Team-level resilience is governed. Position-room counts/projection coverage are descriptive evidence, not a new depth score. No fabricated position fragility score. |
| Broad Market lens | `/api/league/value-lenses` player rows | Value — Broad Market percentile | Available independently where market evidence exists. |
| FSFFL Intrinsic lens | `/api/league/value-lenses` player rows | Value — canonical Shapley Intrinsic percentile presentation coordinate | Available independently after shared Intrinsic lifecycle resolves. |
| Market vs Intrinsic Difference | `percentile_gap` from governed league value-lens contract | Presentation coordinate explicitly authorized by Value contract | Available only when both lenses exist. Raw Market and raw Shapley quantities are never subtracted. |
| Future pick ownership | canonical `LeagueState.draft_picks` + `pick_ownership` | Point-in-Time State | Available for the real State horizon. Own/acquired/traded-away identity is deterministic from original_team_id vs current owner. |
| Pick concentration / scarcity | counts by team/year/round from canonical ownership | Presentation over State | Descriptive counts only (1sts, total picks, missing rounds). No arbitrary pick-value master score. |
| Age context | `TeamAnalyticsView.roster_average_age`, `starter_average_age`, coverage counts | Analytics over point-in-time State | Secondary context only. Missing ages remain missing. |
| Pressure Point | managed team's governed weakest position rank + strongest current league rooms at same position | Team Utility positional evidence | Descriptive only. May hand off to Market; not a trade partner recommendation, fit score, recommendation strength or acceptance probability. |
| Player drilldown | Player Intelligence handoff via canonical player id | Existing Player Intelligence surface | Available. |
| Pick detail | canonical pick fields and ownership status | State | Available. |
| Provenance / stale / degraded | State as_of, team-view source level, Forecast basis/version, Simulation model/version/count, Value lens status | originating authority | Must be explicit; missing evidence remains unavailable. |

## Explicitly unavailable / prohibited

- Universal team Value rank or team Intrinsic total.
- Summed Broad Market percentiles.
- League Market Value.
- Owner-adjusted universal Value.
- Hidden composite / power score.
- Homemade contender score.
- Numeric recommendation strength or acceptance probability.
- Arbitrary pick valuation master score.
- K/DEF positional strength without governed support.
- Football archetype labels such as change-of-pace / third-down specialist without source evidence.
- A preseason team rank when no compatible point-in-time preseason team State exists.
- Any synchronous Atlas-triggered reduction or rerun of the 50,000-run Simulation.

## PR #163 salvage decision

PR #163 is 219 commits behind current main and diverged. It will not be rebased/merged as-is. A fresh branch from current main is safer.

Salvaged concepts/contracts:
- player-level Broad Market / canonical Shapley lens separation and governed percentile-gap comparison;
- QB/RB/WR/TE positional strength evidence;
- roster resilience evidence;
- roster/starter age context;
- true draft-pick inventory;
- progressive drilldown and explicit unavailable behavior.

Not salvaged as presentation:
- old #163 League Atlas UI hierarchy;
- any stale shell wiring;
- any presentation that does not match the new Overview | Position & Depth | Value Map | Pick Map | Outlook North Star.
