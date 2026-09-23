# League Atlas North Star — persisted real-league sanity checkpoint

Date: 2026-09-22
Source: connected read-only FSFFL NEXT Supabase production persistence
Branch: `phase3/league-atlas-north-star-20260922`

## Exact current production State coordinate

- League: `sleeper:1312071960615731200`
- Season: 2026
- State hash: `00a5234e4e8e5d61c0d8bb4819d6e6ce3ed7cf5a58076a21f53ca33943a557a8`
- Persisted at: 2026-09-22 21:40:56.616478+00
- Teams: 12
- Canonical draft picks: 108
- Canonical pick ownership rows: 108
- Matchups: 84
- Last completed week in State: 14
- Persisted selected managed team exists at this exact State coordinate.

## Matching governed runtime artifacts

For the exact current State hash, the production artifact store contains non-invalidated:

- `current_forecast_evidence` — `next8-live-forecast-evidence-v5:revision-agnostic-source-health`
- `live_simulation_analytics` — `next8-live-simulation-analytics-v7:scoring-dispersion-diagnostic`
- `current_market_value` — `next3-current-market-runtime-v7:market-total-fail-closed`

The matching Simulation artifact reports:

- 50,000 simulations;
- 12 team outcomes;
- 12 team Analytics views;
- all 12 teams with the four supported QB/RB/WR/TE positional-strength rows;
- all 12 teams with governed roster-resilience evidence;
- governed competitive-state evidence spanning contender, competitive, developing, and rebuilding.

The latest non-invalidated canonical Shapley artifact uses:

`intrinsic-shapley-contract-v2:effective-horizon-seeds|forecast=forecast-vnext-a2-burr-20260922`

It contains 335 player estimates and currently reports degraded rather than fabricated completeness. The matching current Broad Market artifact contains 537 estimates. The Atlas Value Map therefore has genuine live player-level Market and current A2+Burr-backed Intrinsic evidence to consume, while preserving degraded/unavailable state explicitly.

## Pick Map sanity

Canonical State exposes 2027, 2028 and 2029 rounds 1-3. Ownership identity is materially nontrivial, so the Pick Map will not collapse to a decorative equal-count display:

| Season | Round | Picks | Retained by original team | Moved |
| --- | ---: | ---: | ---: | ---: |
| 2027 | 1 | 12 | 3 | 9 |
| 2027 | 2 | 12 | 7 | 5 |
| 2027 | 3 | 12 | 4 | 8 |
| 2028 | 1 | 12 | 7 | 5 |
| 2028 | 2 | 12 | 7 | 5 |
| 2028 | 3 | 12 | 7 | 5 |
| 2029 | 1 | 12 | 11 | 1 |
| 2029 | 2 | 12 | 6 | 6 |
| 2029 | 3 | 12 | 7 | 5 |

## Product sanity conclusion

The real persisted 12-team production coordinate contains the governed evidence required by the North Star surfaces:

- **League Race / Outlook:** current State plus matching 50,000-run Simulation;
- **Position & Depth:** QB/RB/WR/TE strength on all 12 teams plus governed roster resilience;
- **Value Map:** current Broad Market plus canonical Shapley Intrinsic, with degraded status retained rather than hidden;
- **Pick Map:** true by-team/year/round ownership with own/acquired/traded-away distinctions;
- **team-position drilldown:** the team views that back the matrix are the same views that contain actual rostered players, projected roles/projections, and the positional evidence.

No team Intrinsic total, summed Market percentile, League Market Value, hidden power score, homemade contender score, arbitrary pick-value score, recommendation strength or acceptance probability is introduced.

## Live-validation boundary

This connected environment can inspect production persistence but cannot supply the private-beta HTTP Basic password to an authenticated browser. Therefore this checkpoint does **not** claim authenticated hosted iPhone/Safari rendering or hosted Atlas cold/warm browser latency. Those remain explicit management-acceptance items after exact-SHA deployment.

