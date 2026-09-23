# League Atlas final-acceptance authority audit — 2026-09-23

Scope: bounded League Atlas final acceptance only. This record is intentionally completed before presentation changes.

## Verified starting coordinate

- Repository: `jderhagopian-stack/fsffl-next`.
- GitHub `main` at execution start: `1c180c7a422535982a2af71d6080cc56d7b27857`.
- Render private-beta live SHA at execution start: the same `1c180c7a422535982a2af71d6080cc56d7b27857`.
- Fresh branch: `corrective/league-atlas-final-acceptance-20260923`.

## Matchup-completion coordinate

Live Sleeper evidence on 2026-09-23 exposed:
- league `settings.leg = 2`;
- NFL state `week = 3`, `leg = 3`, `display_week = 2`, regular season;
- roster cumulative `fpts/fpts_decimal` exactly matched the sum of raw Week 1 + Week 2 matchup points for all 12 teams.

The existing PR #173 normalizer preferred `display_week - 1`, which produced completed-through Week 1 and omitted a genuinely completed Week 2. The authority correction is provider-factual only: derive all valid same-season regular-season candidates (league leg - 1, NFL week - 1, NFL leg - 1, display week - 1) and use the strongest nonnegative completed-week boundary. No Forecast, Simulation, Value, Decision, Search or Team Utility model authority changes.

## Max Points For authority

The live Sleeper roster payload exposes `settings.ppts` and `settings.ppts_decimal` for all 12 rosters. On the same acquisition:
- `ppts >= fpts` for every roster;
- `fpts` exactly matched raw provider scoring through the provider-completed Week 2 boundary for all 12 teams;
- therefore `ppts/ppts_decimal` is accepted as Sleeper's cumulative potential-points / Max PF coordinate at the same standings boundary.

Decision: normalize this provider fact into canonical point-in-time Team State as `max_points_for` with explicit Sleeper roster-settings provenance. Atlas consumes only that canonical State field. It is not recomputed from Forecast projections and no alternate Max PF model is introduced.

## 2026 preseason baseline recovery

Persisted evidence was inspected before implementation:
- the preserved league-season Forecast baseline is timestamped `2026-09-10T21:36:41.346326Z`;
- Sleeper's governed regular-season schedule reports the earliest Week 1 date as `2026-09-09`;
- available State-history snapshots begin after that opener date and already contain Week 1 scoring evidence;
- the existing 50,000-run Simulation artifact near the preserved Forecast is likewise post-opener.

Decision: a valid 2026 pre-first-kickoff State + Forecast pair cannot be proven from governed evidence. Do **not** backfill from current rosters, post-kickoff Forecast, or guesses. 2026 remains explicitly unavailable in Atlas, using a compact unavailable state. Future-season automation must freeze the latest valid State before the governed opener coordinate and pair it with preserved preseason Forecast / 50,000-run Simulation evidence.

## Fragility-driver persistence/version path

The latest persisted real-league Simulation artifact before this pass:
- state scope `d23e454cc48fca518a13a0dcb19616e847a224eba5f3b3c5c689b3dbace12001`;
- Simulation artifact model version `next8-live-simulation-analytics-v7:scoring-dispersion-diagnostic`;
- Team Utility lineage `next4-live-team-utility-v4`;
- roster-resilience model version `next4-roster-resilience-v1`;
- all 12 teams had a nonzero `largest_single_player_lineup_drop`, but the persisted payload omitted `largest_single_player_lineup_drop_player_ids`.

The underlying resilience code already computes the exact deterministic argmax IDs without changing the numeric drop. The live failure is stale reusable evidence produced under unchanged version coordinates.

Decision: bump only the affected resilience / Team Utility lineage and live Simulation reusable-artifact contract so stale payloads cannot be reused. Rebuild downstream Simulation/Team Utility evidence under the new version. Do not alter the resilience math or the 50,000-run Simulation fidelity.

## Hard boundaries retained

No League Market Value, team Intrinsic total, summed Broad Market total, hidden power score, owner-adjusted universal Value, recommendation strength, or acceptance probability is created. Forecast, Value, Simulation, Decision and Search mathematics remain unchanged. Home/Franchise is out of scope.
