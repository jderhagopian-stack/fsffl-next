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


## Live Forecast provider-health classification

The corrective live-provider numerical trace is an external provider-health diagnostic, not a League Atlas model-authority gate. On PR head `a367362ee36fb16cb1e70a34806aee68a6a74427`, run #99 failed closed because the live Forecast runtime found only one healthy independent source (`razzball`) while the authoritative contract requires at least two. No Forecast threshold or two-source requirement was changed.

After the only product-branch change was alignment of the stale League Atlas presentation test with the already-approved final IA, run #100 succeeded with two independent providers (`fftoday` and `razzball`). A later ad-hoc fragility diagnostic also encountered transient provider-health disagreement before Simulation could start. These alternating outcomes, with unchanged Forecast code and authority, classify the red trace as live provider/source-health volatility rather than a PR #174 regression.

Decision: preserve the existing two-independent-source Forecast authority and fail-closed behavior. Do not weaken source-health governance merely to make a network/provider diagnostic green. Deterministic League Atlas acceptance uses the governed regression suites plus the real Sleeper State/Max-PF sanity path; live provider-health diagnostics are recorded separately.


## Persisted real-league fragility identity verification

The latest persisted production 12-team Simulation coordinate before this pass was independently replay-checked from its stored team-view inputs and the matching stored Forecast coordinate. The verification preserved the governed lineup eligibility, active-roster availability, position-floor fallback for missing active forecasts, and exact starter-removal counterfactual. For all 12 teams, the independently recomputed maximum drop matched the already-persisted numeric `largest_single_player_lineup_drop` within the existing 1e-9 exact-tie tolerance, and every argmax player ID resolved to a rostered player name.

| Team | Persisted drop | Exact argmax player ID | Resolved player |
| --- | ---: | --- | --- |
| jaco057 | 381.5100 | `sleeper:player:4984` | Josh Allen |
| jder52 | 173.6250 | `sleeper:player:6904` | Jalen Hurts |
| Drigs24 | 170.8075 | `sleeper:player:9509` | Bijan Robinson |
| Ballard22 | 149.9300 | `sleeper:player:4892` | Baker Mayfield |
| nuckyniners | 69.1275 | `sleeper:player:8138` | James Cook |
| PVos | 209.6025 | `sleeper:player:9221` | Jahmyr Gibbs |
| chuckthegoat77 | 167.2200 | `sleeper:player:9758` | C.J. Stroud |
| ddersimon | 173.5150 | `sleeper:player:11563` | Bo Nix |
| CoachKoko | 84.3350 | `sleeper:player:6790` | D'Andre Swift |
| MochaSmev | 244.7125 | `sleeper:player:9224` | Chase Brown |
| Anthonyder | 174.4550 | `sleeper:player:4034` | Christian McCaffrey |
| jimmygoodjob | 47.5225 | `sleeper:player:4881` | Lamar Jackson |

This proves the missing identity was a persistence/version-contract defect rather than missing roster identity or a need to change the fragility calculation. PR #174's v2 resilience contract emits these exact deterministic argmax IDs; Team View already carries the matching canonical IDs and names, and Atlas resolves those IDs into tappable Player Intelligence names.
