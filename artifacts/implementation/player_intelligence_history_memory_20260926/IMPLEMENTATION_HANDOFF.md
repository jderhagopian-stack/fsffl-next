# FSFFL NEXT — Player Intelligence History Memory Corrective

Updated: 2026-09-26

## Terminal checkpoint

**BLOCKED — PHYSICAL / AUTHENTICATED HOSTED PLAYER INTELLIGENCE HISTORY ACCEPTANCE REQUIRED**

The code corrective is implemented, accepted, merged, and deployed. The only remaining
acceptance step requires a real authenticated Player Intelligence history request on the
live private-beta instance, including the physical iPhone/iPad path Management specified.
No such post-deploy request has reached the new instance yet, so memory-under-load and
physical-device acceptance are not inferred.

## Incident being corrected

Post-PR #266 physical testing produced HTTP 503 on iPhone and HTTP 502 on iPad while
Player Intelligence history was building. Render evidence showed the single web instance
approaching its 536,870,900-byte memory limit and restarting.

Pre-corrective Render evidence from deploy `dep-das3lh0jo6nc73a2tif0`:
- memory ~473 MB at 22:15Z;
- ~482 MB at 22:16Z;
- ~492 MB at 22:17Z;
- ~507 MB at 22:18-22:20Z;
- 509,108,220 bytes at 22:21Z;
- CPU dropped to zero at the restart boundary;
- a replacement instance appeared at ~273 MB at 22:23Z and rebuilt upward.

The root cause was the Player History path, not Intrinsic authority:
- one outer history worker was correctly coalesced per State/player;
- inside it, all historical seasons were requested concurrently;
- each season materialized an entire provider population map;
- each map was persisted and retained in an unbounded in-process season cache;
- `player_history()` simultaneously retained all season maps in `by_season` while
  ultimately returning only one player's rows.

## PR #267

PR: **#267 — Player Intelligence: bound historical materialization memory**

Accepted head:
`e914dafe6a3e59ab41dfebebf3fb7177f6d1bcdd`

Merge:
`d737012079345768ef5cfd19debff97e0ede1bba`

### Implementation

1. **Player-scoped Sleeper season retrieval**
   - Added `SleeperWeeklyStatsSource.fetch_season_player(...)`.
   - The response is reduced to the requested player before creating a transformed
     season result.
   - Direct-map payloads do not copy/transform peer rows.

2. **Sequential career extraction**
   - Player History no longer fans historical seasons out through a thread pool.
   - One player's seasons are processed sequentially.
   - The compatibility `max_workers` argument is bounded internally to one for this path.

3. **No permanent full-season process cache**
   - The Player History service no longer owns the prior full-season population
     `_cache`.
   - The old full-population artifact identifiers remain only as legacy constants; the
     new PI history path does not populate or restore them.

4. **Durable player-season evidence**
   - Raw selected-player season rows persist as
     `player_history_player_season` artifacts.
   - Reuse is keyed by provider/source version, player identity, and season.

5. **Durable final career result**
   - Final scored career history persists as `player_history_career`.
   - Its fingerprint includes provider/source version, player identity, season range,
     and current LeagueRules.
   - Repeated PI opens can therefore reuse the final result without rebuilding the career.
   - Weekly State changes do not invalidate history solely because State hash changed when
     the scoring/source/season coordinate is unchanged.

6. **Fallback remains bounded**
   - Legacy whole-season adapters, if used, are processed only one season at a time and
     only the selected player is retained.
   - Weekly fallback is sequential and retains only the selected player's aggregate.

7. **Existing UX preserved**
   - `PlayerHistoryBackgroundCoordinator` remains single-worker/coalesced.
   - The endpoint continues to return HTTP 202 with loading metadata while the one build
     runs.
   - Repeated polls for the same State/player still coalesce to one build.

## Deterministic acceptance

Final PR head passed:
- full CI: **1,704 passed**;
- PR164 focused corrective regression: success;
- Live Forecast corrective trace: success;
- Corrective live provider numerical trace: success;
- League Atlas North Star focused validation: success.

New regression coverage proves:
- requesting six workers still produces max historical-season concurrency of one;
- player-scoped provider retrieval does not call the full-population transform path;
- the service has no unbounded full-season process cache;
- different players do not depend on retained peer-population data;
- the final career result is reusable across service instances through persistence;
- repeated background polls coalesce to exactly one build;
- existing box-stat, games-played, current-league scoring, and history semantics remain intact.

## Exact Render deploy

Service: `fsffl-next-private-beta`
Workspace: `tea-dae6if9t0dsc73918us0`
Service id: `srv-dae6k7vqj5pc73af7bt0`
Plan: current free 512 MB beta instance / 536,870,900-byte memory limit.

Exact deploy:
`dep-das4k27avr4c73909lsg`

Exact product-code commit:
`d737012079345768ef5cfd19debff97e0ede1bba`

Render checkout log explicitly records that commit. Deploy reached `live` at
2026-09-26T22:42:37Z on instance
`srv-dae6k7vqj5pc73af7bt0-v5qcn`.

Fresh startup memory observations:
- 51,175,424 bytes at 22:42:30Z;
- 259,166,200 bytes at 22:43:00Z;
- ~303 MB at 22:43:30-22:44:00Z;
- ~337 MB at 22:45:00Z;
- ~360 MB at 22:45:30Z;
- ~384 MB at 22:46:00Z.

The new process has not shown a restart since launch in the observed interval. These are
startup/background-runtime observations only; they are **not** substituted for the
required PI-history-under-load acceptance.

## Remaining external acceptance gate

No post-deploy request to
`/api/player-intelligence/{player_id}/history`
has reached the new instance in the observed logs.

The assistant environment does not possess the private-beta Basic Auth/session required
to invoke that user route and does not have a physical iPhone/iPad browser tool. Therefore
the remaining gate requires the authorized physical client:

1. Open Player Intelligence for a real player on iPhone and iPad.
2. Open/load historical stats so the route exercises its normal 202 → ready flow.
3. Confirm the modal remains usable and does not return 502/503.
4. Repeat/open again to exercise persisted career reuse.
5. Observe Render memory through the build:
   - same live instance remains present;
   - no Uvicorn/application restart occurs;
   - memory remains safely below the 536,870,900-byte limit and materially below the
     prior failure curve;
   - second persisted open does not reproduce the career-build memory spike.

After that request exists, Render logs/metrics can close the hosted-memory evidence
without any further model, Intrinsic, State-first, or Forecast-authority changes.

## Non-goals / guardrails

This corrective does **not** reopen or change:
- Intrinsic authority or the 335/335 persisted Intrinsic contract;
- State-first persistence or league switching;
- Forecast model authority;
- K/DST policy;
- Market/Decision authority;
- the existing PI 202/loading/coalescing UX.

Do not propose a paid Render tier as the fix unless this memory-bounded path still fails
on the currently authorized 512 MB beta instance.
