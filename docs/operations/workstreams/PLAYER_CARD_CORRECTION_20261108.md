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
