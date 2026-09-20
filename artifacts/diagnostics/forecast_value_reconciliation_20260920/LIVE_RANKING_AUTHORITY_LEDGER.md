# Full live ranking / value authority ledger

Date: 2026-09-20

Rule: every displayed rank/value/percentile/score names its actual coordinate. `FSFFL Value` is not accepted as a generic alias.

| Product surface / API | Displayed or ordering quantity | Exact driver / endpoint | Level | Additive? | Authority / disposition |
| --- | --- | --- | --- | --- | --- |
| Players & Assets | default asset order | `fsffl_cardinal_values[].score` from current Value runtime | player/pick | Cardinal: yes within one coherent context | **FSFFL Cardinal Value**; Stats Guy-backed market-cardinal reference, not Broad Market or Intrinsic |
| Players & Assets | Broad Market percentile | current Value `estimates[]` on `dynasty-market-percentile` | player | **No** | Broad Market; relative market-position lens |
| Players & Assets | NFL-season projection | season `fantasy_points` Forecast mean | player | not a Value sum | Forecast |
| Player detail | projection/rank-at-position | displayed season Forecast mean ordered within position | player | no | Forecast + presentation ordering |
| Player detail | current cardinal number when shown | `FSFFLCardinalValueScore.score` | player | yes only under Cardinal accounting semantics | label **FSFFL Cardinal Value** |
| Player detail / future comparison contract | Market vs Intrinsic | `/api/league/value-lenses`: Broad Market percentile vs Shapley Intrinsic presentation percentile | player | **No** | separate lenses; raw values never subtracted |
| Franchise / My Team | position strength | optimized starter expected points at actual position, league-relative index/rank | team-position | no | Forecast-backed Team Utility descriptive diagnostic |
| Franchise / My Team | core / optionality asset callouts | descending Cardinal player score | player within roster | Cardinal accounting only | **FSFFL Cardinal Value**, not Intrinsic |
| Franchise / My Team | legacy Value Lens | `/api/value/intrinsic-v1` weighted replacement-adjusted surplus | player | not promoted as team total | **legacy Intrinsic v1**; not the Shapley Atlas authority |
| Franchise / My Team | competitive outlook / fragility | Simulation outcomes and Team Utility resilience diagnostics | team | no generic aggregation | Simulation / Team Utility |
| League | QB/RB/WR/TE rank | optimized starter expected points by position | team-position | no | Forecast-backed descriptive position strength |
| League | expected wins / playoff / first-place / championship ranks | corresponding 50k Simulation outcome | team | no | Simulation; each metric independent |
| League | competitive state | governed Team Utility competitive-state policy | team | no | Team Utility |
| League | age ordering | canonical player ages aggregated descriptively | team | no | State / Analytics |
| League | pick-count ordering | owned draft-pick count | team | count only | State; no pick economics implied |
| League | Cardinal portfolio comparison | sum of coherent Cardinal players + generic picks | team | **Yes, Cardinal only** | market-cardinal accounting view; not universal franchise worth |
| League | Total Market Value | intentionally unavailable | team | n/a | Broad Market percentile is non-additive; fails closed |
| League Atlas value-lens contract | Broad Market | `/api/league/value-lenses` Broad Market percentile | player | no | Value — Broad Market |
| League Atlas value-lens contract | FSFFL Intrinsic | same endpoint; Shapley raw values converted to centered percentile rank for presentation | player | percentile: no | Value — Shapley Intrinsic |
| League Atlas value-lens contract | Difference | `intrinsic_percentile - broad_market_percentile` | player | no | presentation comparison only; no recommendation |
| Market / Opportunities | structural market plausibility / asset magnitude | existing FSFFL Cardinal market-cardinal evidence where magnitude is required | player/package context | Cardinal only | Search consumes Value; Search does not create Value |
| Market / Opportunities | disagreement discovery | `/api/opportunities/value-disagreements`, Broad Market percentile vs Shapley Intrinsic percentile | player | no | discovery lens only; acceptance remains unknown |
| Market / Opportunities | opportunity ordering | governed multi-lane Search/Decision criteria, not a hidden master Value score | opportunity | no | Search/Decision; no composite opportunity score |
| Trade Center browser | asset value badge | `fsffl_cardinal_values` | player/pick | Cardinal only | now labeled **FSFFL Cardinal** |
| Trade Center analyze | bilateral economics / consequence | Decision + Team Utility deltas + market evidence summaries | trade/team | package semantics owned downstream | Decision; Cardinal display does not determine verdict |
| Trade Center simulation / League Impact | changed-roster expected wins and probabilities | exact 50,000-run Simulation | team/scenario | no | Simulation |
| Trade Center frontier | nearby package feasibility | Search over governed Decision results | package | no | diagnostic price discovery, not acceptance probability |
| Owner Intelligence | owner behavior / tendency ranks and counts | persisted Behavioral events/profiles | owner | no | Behavioral only; cannot mutate universal Value |
| Owner Intelligence | asset/value references | governed Value coordinates passed through when present | asset | depends on named coordinate | no owner-adjusted Value is fabricated |
| Home | top opportunity / action cards | existing governed Opportunity/Decision outputs | opportunity | no | presentation of Search/Decision authority |
| Home | competitive state / expected wins / playoff context | Team Utility / Simulation | team | no | named competitive metrics only |
| Home | any Cardinal asset callout | current Cardinal score | player | Cardinal only | explicit Cardinal label required |
| Simulator | scenario delta | `/api/what-if/player-unavailable` changed-state Simulation | team/scenario | no | Simulation; ownership and governed Value coordinates remain unchanged |
| `/api/values/current` | `estimates` | `dynasty-market-percentile` market estimates | player | no | Broad Market |
| `/api/values/current` | `fsffl_cardinal_values` | direct governed Cardinal reference | player/pick | yes under Cardinal semantics | FSFFL Cardinal |
| `/api/values/current` | `team_cardinal_portfolios` | sum of Cardinal values | team | yes | Cardinal accounting only |
| `/api/values/current` | `team_market_value_portfolios` | unavailable while additive market scale absent | team | n/a | fail closed |
| `/api/value/intrinsic-v1` | raw value | weighted expected FP surplus above lineup replacement | player | not promoted as team total | legacy Intrinsic v1 |
| `/api/value/intrinsic-shapley-v1` | raw value | discounted Y1/Y2/Y3 Shapley deployment contributions | player | Shapley game efficiency; no product team-total authority | current Shapley Intrinsic contract |
| `/api/league/value-lenses` | Market / Intrinsic / gap | distinct player-level lenses | player | no | Atlas-safe comparison contract; Cardinal excluded |

## Silent-substitution audit

- Broad Market is not replaced by Cardinal when Broad Market evidence is missing.
- Shapley Intrinsic is not replaced by Cardinal or legacy Intrinsic when unavailable.
- `League Market Value` remains unavailable.
- Team Utility remains downstream and does not become universal Value.
- Cardinal team sums remain explicitly Cardinal accounting; they are not renamed `Franchise value` or `Total Market Value`.
- Forecast projection ranks remain Forecast ranks rather than Value ranks.
- Simulation outcome ranks remain Simulation ranks rather than asset-wealth ranks.

## Known unresolved semantic mismatch

The current Franchise Value Lens still uses legacy `/api/value/intrinsic-v1`. Current Market disagreement and the League value-lens contract use `/api/value/intrinsic-shapley-v1`. The two are mathematically different, so this reconciliation does not silently migrate the Franchise lens.