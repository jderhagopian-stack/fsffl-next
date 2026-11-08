# Player card and roster correction — November 8, 2026

## Reopened physical acceptance

User screenshots after the successful refresh show roster 3-Year indexes present, raw Career totals present but Career indexes unavailable, and Player Intelligence history HTTP 503 with no chart actuals. Core/Career persistence success remains valid; rendered acceptance is reopened. Dameon Pierce is unsigned and legitimately lacks accepted projections; this is not a coverage bug to patch with invented inputs.

Verified canonical main: `259c7b9e28b157577d3782b6ee77fa2c249d5277`. Live deployment remains `dep-dbnupbh5efls73cdm2j0` on that commit. Candidate branch `fix/player-card-history-career-20261108`; no production data mutation or refresh initiated.

## Evidence and diagnosis

At 04:05:35 UTC, released Current restoration timed out waiting for heavy-work admission. The roster Career endpoint calls Current `current()` just to recover reference identities. A released/temporarily un-restorable contract produces an empty reference and blank display indexes, even though raw Career remains ready. The published value-lens path already uses the retained bounded Current cohort identity summary and has ready indexes. The roster renderer ignored those published indexes and consumed only the separate Career endpoint.

During ordinary page reads at 04:05:36–51, multiple compatibility workspaces overlapped because immutable input objects differed. They independently replayed authority, as required, but resource use was unbounded by the existing same-object coalescing. Process high-water reached **575,471,616 B (548.81 MiB)**; one sampled RSS reached 577,101,824 B. This supersedes 489.37 MiB as the session-wide process peak; that earlier figure described refresh publication only. RSS differs from charged container memory.

Historical endpoints returned 202 then 503 at 04:06:53–56 and repeated 503 afterward for multiple players. The history coordinator permanently caches every exception as FAILED. The heavy-work lane refuses admission above its hard memory limit; these observed requests ran while RSS exceeded it. Memory admission is a strongly supported contributor, but the failed record's exact error was not logged, and cannot be recovered from the existing read-only tools. Do not claim a proven provider outage or complete historical recovery from this evidence alone.

## Small correction

- Roster Career display prefers an already-ready Career player lens from its exact matching published State/generation; stale or missing indexes remain unavailable. Raw endpoint evidence remains the fallback. No browser-derived coordinate.
- Career endpoint reads the existing bounded completed-player summary instead of restoring Current for IDs. An absent summary still fails closed.
- Distinct-context compatibility checks remain independent and freshness checked, but their transient workspaces execute serially inside the existing loader; exact-input in-flight sharing remains. Release unused allocator pages after the resolver frame exits. No TTL, State-only cache, model or source selection change.
- A typed pre-work memory-admission refusal is retryable for history after 2.5 seconds. One coalesced task per key and existing queue/record limits remain. Provider/model failures remain terminal and now log their actual exception. The HTTP result stays loading for admission waits, allowing the existing browser polling contract to work. Hard memory cap remains enforced.
- Update content-specific browser asset versions and focused CI regression selection.

## Validation and limits

Focused history/compatibility tests: 9 passed. Career endpoint with the real 335-player test fixture, released-Current restore forbidden and missing-cohort fail-closed: 1 passed (72.19 s). Browser card/asset-generation, Career client lifecycle and history regressions: 29 passed. Final focused history/resource/compatibility selection: **16 passed**, 84 deselected. One initial invocation named a nonexistent test file and collected nothing; the corrected selections above passed.

Private saved-input four-reader replay uses distinct immutable State objects, the same accepted baseline/fumbles and warmed Future contract, with provider I/O excluded. Before: four overlapping authority reads, **0.558 s / 189,388 KiB peak**. After: four serialized reads, **0.854 s / 180,852 KiB peak**. Every fingerprint is unchanged (`431c56ef5443084de599e3e9cc6e06dcc8f7ff4d47ebcfeea5c4453a0753e929`). This trades ~0.30 s total local replay time for lower overlap/retention, and is not a full hosted memory-capacity proof.

No source/model/scoring/provider/plan/schema/worker change. Historical snapshots and canonical roster coverage are preserved. Hosted normal-page verification must confirm roster indexes, history service/actual chart data, memory, and any newly logged provider error. No second intelligence refresh is needed or authorized merely to test these read-path fixes.


## PR #519 deployed; restart guard blocker found

PR #519 exact head `d1dbc34db9f50c039bd04787f13c62e0cff6962c` passed clean automated review at 04:20:56 UTC, CI `42446321694` and Stable `42446330544` / job `128625925767`: **2,670 passed / 5 skipped**, 749.26 s, before/after exact-head checks. Squash merge `7898f79cb7ad6f16bd21686932709d323449b092` has identical tree `a019ec916492e0e20757e2afe8e621feb25324a0`. Render `dep-dbnvnd6417fc73esqkog` became live at **04:35:34.081936 UTC**, event `evt-dbnvo5jhf81s73bd89a0`, unchanged `0.5c-512mb` single service, auto-deploy off. Startup RSS **309,551,104 B**, peak **334,229,504 B**, but Forecast/Simulation restoration was unavailable and Career's compatible lookup missed. Do not claim complete restart/product acceptance.

Read-only hosted artifact inspection identifies a deterministic restart validation bug: exact published Forecast has valid v5 first-party supplement bound to State `703e822c...`, one FUMBLES_LOST partial for **unrostered** `sleeper:player:7528`, zero materiality assessments, and an empty simulation-relevant partial scope. No active subject is affected. `fumbles_lost_runtime_authority_compatible` rejects all empty assessment lists before checking that scope. That drops Forecast, prevents Simulation restore, and changes Career's dependency lookup. This is independent of unsigned Dameon Pierce.

Post-refresh Render 30-second charged-memory samples before the new deployment reached **526,413,820 B (502.03 MiB)** at 04:06:00, remaining around **517,136,400 B (493.18 MiB)** at 04:23. No restart/OOM was recorded. Samples are not instantaneous peaks.

### Narrow restart correction

Branch `fix/restart-inactive-partial-20261108`, base verified current main `7898f79c`. Preserve exact scope matching first. Only when no partial subject is active, permit the already valid exact-State/current-version supplement without manufacturing an irrelevant assessment. Active partials still need the unchanged cutoff/contract/status checks. Missing/wrong supplement metadata with no assessments remains rejected; the previously accepted assessed inactive path remains compatible. No scoring, raw point, source or projection alteration.

Three new unrostered/Taxi/IR cases fail before the fix and pass after; also reject wrong-State/version supplements and newly active partials, with both empty and matching stored scopes. Full focused rolling-materiality/persistence selection: **89 passed**. A real saved-guard replay using the exact production supplement/partial/scope plus all **214 active roster IDs** returns **false before / true after**, with zero provider requests/database writes. This is exact guard-input evidence, not a full decoder/hosted restore claim. A new manifest-bound persistence roundtrip verifies the partial row and raw evidence are preserved across restart.

No additional intelligence refresh was initiated. Hosted restart must restore Forecast/Simulation/Career before physical roster/history acceptance can close.
