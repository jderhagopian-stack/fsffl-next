# FSFFL NEXT — Architecture Recovery Workstream

Updated: 2026-10-06

## Purpose

This is the durable execution/handoff record for the P0 Architecture Simplification and Development Recovery program governed by:

`docs/operations/directives/20261005_ARCHITECTURE_SIMPLIFICATION_AND_DEVELOPMENT_RECOVERY.md`

Management has accepted the read-only audit and assigned **Work as the sole writer** for the P0 corrective program while Work capacity remains available.

This file exists so execution continuity does **not** depend on Work chat history or remaining Work allowance.

If Work becomes unavailable or exhausts its usage allowance, Management may reassign the exact remaining work to Implementation. Implementation must resume from this file plus the governing directive and live GitHub state rather than reconstructing scope from conversation history.

## Mandatory checkpoint rule

Work must update this file **before and after every material P0 slice**, and whenever it is about to:
- open or merge a PR;
- deploy;
- begin a materially different subsystem;
- pause for Management;
- stop because of tool/session/usage limits;
- hand execution to another worker.

Do not wait until the end of the entire recovery program.

Every checkpoint must record:

1. **Timestamp / phase / slice**
2. **Current main SHA**
3. **Active branch / PR / exact head SHA**
4. **Live Render deploy/commit if relevant**
5. **What was proven before changes**
6. **What changed**
7. **Files/subsystems touched**
8. **Before/after measurements**
   - restore/useful-State timing;
   - foreground/API latency where relevant;
   - Supabase calls/bytes or artifact-read counts where relevant;
   - refresh/publication timing where relevant;
   - Render current/high-water memory where relevant;
   - browser polling/retry/lifecycle handoffs where relevant.
9. **Focused tests run and result**
10. **Full-suite status**
    - run only at the stable merge gate unless a materially broad contract change warrants otherwise.
11. **Physical/hosted acceptance status**
12. **Known unresolved findings**
13. **Frozen safeguards / explicit non-goals**
14. **Exact next action**
15. **Safe handoff instruction**
    - what another worker should read first;
    - exact commit/branch to resume from;
    - what must not be repeated or reopened.

## Work-allowance discipline

Management currently has limited weekly Work capacity.

Therefore:
- prioritize finishing one bounded slice cleanly over partially touching several later slices;
- avoid repeating broad repository/audit scans already captured in the accepted audit unless new evidence requires them;
- reuse the audit, directive, this workstream file, and live code evidence;
- keep changes PR-sized;
- checkpoint early and often;
- if remaining Work capacity appears insufficient to finish the current slice safely, stop at a clean durable checkpoint rather than beginning another architectural tranche.

## Current accepted execution sequence

### P0.1 — measurable customer read path
Establish the authoritative end-to-end saved/current-session journey through Product Context and League Atlas to visible current-generation Dynasty Position & Depth evidence.

Include the unresolved live Dynasty failure.

Baseline:
- restore stages;
- State lookup;
- publication/manifest lookup;
- payload reads;
- first useful render;
- generation identity;
- Supabase calls/bytes;
- foreground latency;
- Render memory;
- browser retry/poll/handoff count.

Do not broadly refactor before this baseline exists.

### P0.2 — metadata-first persistence / egress
Add metadata-only artifact/presentation lookups for existence, identity, generation and freshness. Fetch large payload only on actual consumption. Remove repeated same-process full-payload reads where safe.

### P0.3 — automatic static-asset identity
Replace manual cache-buster maintenance with centrally generated content-derived fingerprints.

### P0.4 — simpler published-reader contract
Move ordinary product reads toward one inexpensive publication manifest/read contract. Remove duplicate restore/manifest discovery only after tracing consumers and proving continuity/freshness behavior.

### P0.5 — lifecycle/resource ownership consolidation
Collapse genuinely redundant readiness/promotion/polling/coordinator mechanisms behind stable idempotent job/read boundaries. Declare cache/resource ownership, lifetime, bounds and invalidation centrally.

### P0.6 — development/operations simplification
Establish one authoritative current-operations source, archive/supersede stale current-state prose, use focused tests during development, one full suite at stable merge gate, and a small set of real end-to-end runtime/browser acceptance journeys.

## Future-facing architecture constraints

Preserve:
- one obvious current publication head without erasing immutable PIT/history;
- bounded Trade/What-If/counterfactual derivative jobs separate from baseline publication;
- shared historical State/event/lineage infrastructure for future Owner Intelligence, League Market, historical analysis and league-history products;
- replaceable artifact payload storage behind stable identity/metadata/payload interfaces;
- private-beta simplicity **and** eventual horizontal web / independent worker scalability;
- accepted analytical/model authority unless direct contradictory evidence proves otherwise.

Do not introduce Redis, queues, microservices, distributed locks, paid infrastructure, or broad storage migration merely for architectural neatness.

## Feature hold

Until Management changes the gate:
- no #375;
- no PIT/history product expansion;
- no Owner Intelligence implementation;
- no unrelated product breadth.

## Current checkpoint

**State:** P0.1 PR #394 — focused Actions exposed asset-key and test-harness issues; route redaction is also hardened, final-head validation pending.  \
**Owner:** Work per latest Issue #393 Management ownership correction.  \
**Current main:** `0ef839ef9edeae7dad85fb6e52984c2998699e2a`.  \
**Branch:** `work/p0-1-baseline-20261006`. Exact instrumentation/test/privacy/RSS/delivery head before this handoff commit: `a2e069b0f8a22a1dd8076722ee9e0f52ca1b8aa8`; fetch the resulting PR head before takeover.  \
**PR:** #394 — https://github.com/jderhagopian-stack/fsffl-next/pull/394.  \
**Live deploy:** Render `fsffl-next-private-beta`, deploy `dep-db229jvlot8c73dieqtg`, live #391 commit `583f48dca0c6b763b7d249e420b82964a15291d2`; unchanged.

The accepted pre-change baseline above remains the only production measurement. No post-change runtime or physical-browser values are available until deployment.

### Implementation in this slice

Instrumentation only. No restore order, read contract, API response semantics, retry limits, publication fencing, Dynasty formula, Current ranking, model authority, or product behavior changed.

Files changed:

- `src/fsffl/journey_telemetry.py`: bounded allowlisted structured events; opaque request/restore IDs; bounded browser batch intake; persistence read decorator.
- `src/fsffl/product/persistent_runtime.py`: timings/outcomes for durable context restore, State activation, and exact-State intelligence restore under one startup restore ID.
- `src/fsffl/persistence/postgres.py`: correlated call/read/row/hit-miss/elapsed and returned serialized JSON byte counts for runtime context, State snapshots, sync cursor and reusable artifacts. Payload bytes are application JSON serialization size, **not** exact Supabase wire egress.
- `src/fsffl/product/persistent_webapp.py`: request/restore correlation headers, journey request timings, and authenticated same-origin telemetry intake limited to 64 KiB / 80 events.
- `src/fsffl/product/static/app.js`: session-scoped opaque ID, actual API attempt/status/latency counts, Product Context restore, Safari memory availability, coalesced bounded batch flushed once at success/failure/pagehide.
- `src/fsffl/product/static/product_shell.js`: actual shared-readiness poll counts, bounded promotion retry wait, generation handoff, and asset identity.
- `src/fsffl/product/static/league_comparison.js`: value-lens/Atlas alignment/Dynasty attempts/retry waits; exact Dynasty State/generation failure; visible exact-generation first useful render.
- `src/fsffl/product/static/index.html` and `product_shell.js`: refreshed required static cache identities so the modified JavaScript reaches browsers.
- `tests/test_architecture_recovery_journey_telemetry.py`: allowlisting, bounded batches, payload-byte/call counts, restore identity and Dynasty failure/success fence.
- `.github/workflows/league-atlas-north-star.yml`: new regression tests and JS syntax checks included.

Safari `performance.memory` may be unavailable and will be reported as unsupported. Render RSS is a separate hosted sample.

### Validation and measurements

- Pre-change baselines remain those in the 01:25Z entry: restore-ready success p50 10.89s/p95 127.48s/max 223.04s; failure p50 11.98s/max 96.76s; accepted previous egress 12.69 GB; Render high-water about 524.4 MB; no correlated browser/API stage measurements.
- On PR head `c6f95217d621614c48a8eac75b976178a6e921c0`, the focused JS syntax step passed; the Atlas and Home suites exposed stale inner/outer cache keys after the modified shipped asset. Those keys were recalculated from the Git blob identities.
- On PR head `1da8a14eeb111d4143c837bea5584134b1650482`, Home passed; Atlas syntax passed but telemetry tests needed INFO capture and a `Path` import. Head `b7f5fe7f0e275e70e60da8ca5647c6cfa51a0bf1` fixed those, and exact guarded-selector assertion alignment landed in `621c24c0e500e4cd3af6e7d093ed63fa766a3f49`. Atlas focused validation, including composition sanity and final-acceptance authority audit, then passed on `621c24c…`. A final privacy review restricted logged route names and added an identifier-redaction regression at `f2c7898b0d057c408735835831b916da0e4376a5`; final-head checks are pending.
- Full CI was started on earlier heads and had not completed at this checkpoint. Full CI on `621c24c…` was still in progress before the final path-redaction change; exact final-head checks must be fetched after this checkpoint commit and used for disposition. The stable final full suite remains required.
- No local checkout or local tests were attempted; cloud-browser/Git-transport recovery was not retried. No Codex review requested per P0.1 gate.
- Physical iPhone/Safari acceptance and production post-change measurements remain pending deployment. The unresolved Dynasty failure remains preserved; actual live failing stage is unknown.

### Frozen safeguards

Approved #370 Dynasty metric, Current ranking semantics, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, exact State/team/publication-generation fences, atomic publication, verified last-good, tenant isolation, no P0.2, #375/PIT-history/Owner Intelligence hold.

### Exact next action and safe takeover

1. Fetch PR #394’s exact post-checkpoint head and associated Actions.
2. Require focused Atlas checks and standard CI to pass at a stable exact head. Fix only demonstrated defects; avoid broad refactors and repeated full suites beyond the final stable merge gate.
3. Record final PR/head/check disposition. Then follow Management’s hosted deployment process and have Management run the saved-session iPhone/Safari journey once; correlate Render events by `journey_id` and `restore_id`, and compare server/browser State + generation IDs, retries/polls/handoffs, timings, payload bytes and Render memory.
4. Resume from this file, the governing directive, Issue #393 and PR #394. Do not repeat the broad audit or pre-change baseline, treat `ERR_BLOCKED_BY_CLIENT` as product evidence, reopen frozen semantics, or start P0.2 before P0.1 is complete and checkpointed.
---

## Execution log

### 2026-10-05 — Management handoff baseline

- Audit: complete and accepted.
- Phase B owner: Work.
- Separate Implementation stream: paused for this program.
- New feature breadth: HOLD.
- Next action: P0.1 baseline and unresolved Dynasty customer-journey trace.
- No P0 corrective implementation has yet been accepted under this workstream record.


### 2026-10-06 01:25Z — P0.1 baseline / safe pre-implementation checkpoint

- **Authority and current main:** latest commit found on main is `0ef839ef9edeae7dad85fb6e52984c2998699e2a` (“Require durable Work checkpoints for P0 recovery”). Issue #393 is open; its latest Management ownership correction confirms Work is the sole writer. The P0 directive, current-state files, this handoff, Issue #393 and latest Render deploy were reread.
- **Branch / PR / head:** branch `work/p0-1-baseline-20261006` created from `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; no PR. This checkpoint commit changes this handoff file only. Resolve the exact current branch head from GitHub before continuing.
- **Live deploy:** service `fsffl-next-private-beta`, deploy `dep-db229jvlot8c73dieqtg`, commit `583f48dca0c6b763b7d249e420b82964a15291d2` (#391), live. Main/live application difference remains documentation-only; no new deployment occurred.
- **Journey evidence:** #391 binds Dynasty ready/preparing/unavailable/verified-last-good responses to publication generation and retains the client's exact-generation fence. Physical iPhone/Safari acceptance of visible Dynasty ranks remains unresolved. Current live visible publication ID and the actual user-facing failing stage are **not established** by this checkpoint; do not describe the browser-access failure below as an application failure.
- **Restore baseline (Supabase `user_perceived_latency`, prior 7 days):** `restore_ready` success n=52, p50 10,889.5 ms, p95 127,479.05 ms, max 223,043 ms (latest 2026-10-05 23:03:36Z); failed n=10, p50 11,978.5 ms, p95 58,609.95 ms, max 96,756 ms (latest 2026-10-05 19:06:45Z). These are restore-ready totals, not per-stage timings.
- **State / manifest / payload journey reads:** no correlated journey-level counts or timings currently exist in the observed data. Existing app artifact queries retrieve full payloads; per-stage read counts/bytes remain **not measured**.
- **Supabase baseline:** current `pg_stat_statements` shows 12,749 calls / 12,261 rows / 102,394.1 ms total execution for one full-payload `derived_artifact` identity lookup; 11,747 calls / 8,011 rows / 149,234.8 ms for the latest-by-scope full-payload lookup; 10,685 full-payload upserts / 212,541.9 ms. Query statistics reset was recorded as 2026-09-08. These totals are not journey- or artifact-kind attribution; query-level bytes are not recorded. Latest canonical egress figure remains 12.69 GB (directive; not independently refreshed here).
- **Foreground latency:** Render returned no `http_latency` or `http_request_count` samples for the seven-day window. A last-24-hour request-log filter for Product Context and Dynasty paths returned no rows. Therefore current endpoint p50/p95 and request counts are unavailable.
- **Memory:** Render seven-day samples: 194 points across 136 instance IDs; min 2,252,800 bytes; max 524,447,740 bytes (about 524.4 MB). This approaches the 536.9 MB runtime ceiling; the sparse, many-instance-ID telemetry does not establish cause or a leak.
- **First useful render / generation identity:** no browser performance mark or end-to-end trace links restore → Product Context → Atlas render → visible Dynasty room generation. Not measured.
- **Browser retry/poll baseline (source inspection, not physical request counts):** Atlas value-lens loader has up to 80 requests with default 1,500 ms retry delay; Dynasty position-room loader up to 20 requests with the same default delay; Atlas/team view alignment up to 3 attempts at 150 ms spacing; shared readiness polling caps at 36 ticks; Atlas publication promotion allows one bounded 250 ms retry; Forecast refresh maintenance runs on a 2,500 ms interval. These are configured bounds/intervals, not observed counts in a real saved-session run.
- **Physical/browser observation:** a single attempt to open the live host from the available cloud browser failed with `net::ERR_BLOCKED_BY_CLIENT`. It did not reach an auth page or app response and is not evidence the service/Dynasty endpoint is failing. No alternate route or repeated browser probing was attempted. A testable local repository checkout could not be created because outbound Git transport is blocked in this environment. No code or tests were changed/run.
- **Files/subsystems changed:** handoff documentation only. No app/runtime/browser code, persistence data/schema, Render configuration, or model semantics touched.
- **Focused tests / full suite:** none; documentation-only checkpoint. Full suite remains reserved for stable merge gate.
- **Frozen safeguards / non-goals:** Simulation 2.0 mathematics, 50k/RNG/replay, Foundation 4 and accepted #370 Dynasty semantics; exact State/team/publication-generation fences; atomic publication, verified same-league/team last-good, tenant isolation; no #375/PIT-history product expansion/Owner Intelligence; no broad model changes, distributed infrastructure, or unrelated product breadth.
- **Exact next action:** in a code-capable repo checkout, fetch current main and this branch, confirm main has not advanced, then use a saved-session customer context to run and instrument exactly one before-change journey: restore/current State → Product Context → League Atlas → visible Dynasty rooms, capturing State/manifest/payload reads and bytes, generation IDs, per-stage timings, first useful render, foreground latencies, memory and actual browser requests/retries/polls/handoffs. Preserve the failing stage and response as a regression case. If a physical saved-session browser is unavailable, record that as an explicit acceptance gap and do not invent its evidence. Keep P0.1 limited to this measurement/authoritative journey slice.
- **Safe takeover:** read this file, the governing directive and Issue #393 first; verify exact GitHub branch/main/live deploy. Continue only on `work/p0-1-baseline-20261006` or a Management-reassigned successor; do not repeat the broad audit, do not treat `ERR_BLOCKED_BY_CLIENT` as the product failure, and do not start P0.2 until P0.1 has a complete baseline/checkpoint and Management-authorized sequencing.


### 2026-10-06 — P0.1 implementation-ready stop checkpoint

- **Main / branch / PR / live head:** current main at start of this continuation was `0ef839ef9edeae7dad85fb6e52984c2998699e2a`. Active branch is `work/p0-1-baseline-20261006`, previous checkpoint head `092225cf92144ec919f3bfcc74a213d2e6143deb`. No PR. The only change in this continuation is this handoff update. Fetch the resulting branch HEAD before resuming. Live remains #391 commit `583f48dca0c6b763b7d249e420b82964a15291d2`, deploy `dep-db229jvlot8c73dieqtg`.
- **Stop reason:** workspace `/workspace/scratch/51c53025bec4` is not a Git checkout; `git ls-remote https://github.com/jderhagopian-stack/fsffl-next.git HEAD` failed because outbound Git transport could not connect to the configured browser proxy; one live-host browser navigation failed with `net::ERR_BLOCKED_BY_CLIENT`. No application changes or tests were attempted. These are execution-environment limits, not proof of app/Dynasty failure.
- **Established unresolved regression:** #391 is deployed and the server/client exact-generation contract is present, but physical iPhone/Safari still has not accepted visible Dynasty Position & Depth ranks. The actual failing live response/generation/UI stage remains unknown. P0.1 must preserve this as an explicit unresolved/reproducible test case; do not invent a backend failure or change the generation fence.
- **Exact instrumentation scope (instrumentation-only; no lifecycle behavior change):**
  1. `src/fsffl/product/persistent_runtime.py`: `PersistentPrivateBetaRuntimeStore.restore_user()` (around line 598), `_set_league_state_under_lifecycle()` (around 799), and `restore_exact_state_intelligence()` (around 1159). Emit timing/outcome for durable context restore, State selection/activation, and exact-State intelligence restore. Do not change locking, restore, or promotion order.
  2. `src/fsffl/product/persistent_webapp.py`: `_gate_restored_session_reads()` (around 645), `_presentation_payload_loader()` (614), `_promote_presentation_for_user()` (1690), and `_publish_dynasty_presentation_followup()` (1839). Correlate request, restore, presentation promotion, and route timing; include target/served State and publication generation identities.
  3. `src/fsffl/product/presentation_continuity.py`: `promote()` (143), `has_snapshot()` (388), `load_for_runtime()` (470), and `load_candidate()` (531). Count manifest/surface lookups, hit/miss, elapsed time, and serialized payload bytes; keep candidate selection and same-league/team last-good behavior unchanged.
  4. `src/fsffl/persistence/postgres.py`: `get_user_runtime_context()` (41), `get_league_snapshot()` (79), `get_reusable_artifact()` (211), `get_latest_reusable_artifact()` (224), and `append_user_perceived_latency()` (328). At adapter boundaries, record per-journey call count, query kind, duration, row count, and returned JSON/payload byte count when measurable. Do not emit SQL parameters, payloads, raw user IDs, provider credentials, or add schema/migrations. Clearly distinguish exact payload bytes from estimates; pg_stat_statements remains aggregate-only.
  5. `src/fsffl/product/foundation4_shadow_routes.py`: `dynasty_position_rooms()` (90) and `_dynasty_publication_payload()` (31). Record ready/preparing/unavailable/last-good outcome and target/served `league_state_id` + `publication_generation_id`; preserve exact-match rejection and do not relabel last-good.
  6. `src/fsffl/product/static/product_shell.js`: `fsfflAtlasPublicationPromotionTarget()` / promotion flow (49–86), `fsfflStartSharedReadinessPolling()` (334), and the `fsffl:product-context-updated` listener (378). Count actual polls, retry waits, generation handoffs, request-owner cancellations, and asset URL/fingerprint used.
  7. `src/fsffl/product/static/league_comparison.js`: instrument the value-lens retry loop (around 304), Dynasty-room retry loop (328), Atlas alignment loop (435), and the final render path that visibly paints Position & Depth. Emit first-useful-render only after the visible room rows carry the requested current State/generation; loading/empty/last-good UI must not count as current-generation success.
- **Event contract:** prefer bounded structured logs plus one browser-side batched diagnostic event only if needed to correlate actual browser attempts. Common fields: `journey_id` (opaque UUID), `request_id`, `event`, `stage`, `surface`, `outcome`, `elapsed_ms`, `attempt`, `retry_wait_ms`, `handoff_from_generation`, `handoff_to_generation`, `target_state_id`, `served_state_id`, `publication_generation_id`, `artifact_kind`, `artifact_identity_hash`, `cache_result`, `db_call_count`, `row_count`, `payload_bytes`, and `first_useful_render_ms`. Never log raw user IDs, provider credentials, roster/player payloads, or SQL parameters. Bound/sampling policy and telemetry failure must not affect product responses.
- **Focused regression tests to add/extend:**
  - Add a small `tests/test_architecture_recovery_journey_telemetry.py` with focused tests `test_restore_journey_trace_orders_stage_events_without_double_counting`, `test_artifact_read_trace_reports_calls_rows_and_payload_bytes`, `test_dynasty_generation_mismatch_is_failure_and_current_match_is_success`, and `test_first_useful_render_requires_visible_exact_generation`.
  - Extend `tests/test_phase3_league_surface.py` for the real route contract: mismatch/unavailable is recorded as failure, exact match reports ready, verified last-good retains its own generation.
  - Extend `tests/test_product_league_comparison_static.py` or its existing JS harness to exercise actual retry/poll/handoff counters. Source-string assertions alone do not prove actual counts.
  - If the shared trace hook requires direct adapter coverage, add one narrow case to `tests/test_persistence_contracts.py`; prove call/returned-byte counters without sensitive values and without changing SQL/results.
- **Acceptance criteria for P0.1:** a reproducible saved-session run reaches Product Context and League Atlas; every server/browser event shares a traceable opaque journey ID; State, manifest, payload, publication identity, Supabase calls/bytes, stage and foreground timings, first useful render, memory sample, and actual retry/poll/handoff counts are captured; one exact Dynasty mismatch/failure is retained as a failing-regression fixture; matching-generation Dynasty room ranks are the only success signal; instrumentation adds no readiness polling, no duplicate requests, no UI behavior change, no generation-fence weakening, and no extra heavy work. Then run only the named focused tests, observe a real saved-session browser run, and write the post-slice checkpoint. Do not begin P0.2.
- **Literal next commands/actions for Implementation in a code-capable checkout:**
  ```bash
  git fetch origin main work/p0-1-baseline-20261006
  git switch --track origin/work/p0-1-baseline-20261006
  git status --short --branch
  git rev-parse HEAD origin/main
  ```
  If the branch is already local, use `git switch work/p0-1-baseline-20261006` instead of `git switch --track ...`. Confirm the base/head and clean tree before editing. Implement only the instrumentation points above, then run:
  ```bash
  python -m pytest -q tests/test_architecture_recovery_journey_telemetry.py
  python -m pytest -q tests/test_phase3_league_surface.py -k 'dynasty_position_rooms'
  python -m pytest -q tests/test_product_league_comparison_static.py -k 'journey_telemetry'
  # Add only if the adapter hook changes its contract:
  python -m pytest -q tests/test_persistence_contracts.py -k 'journey_telemetry'
  ```
  Capture one real authenticated saved-session journey in the permitted engineering-controlled browser/iPhone path. If that journey cannot be observed, stop P0.1 with the instrumentation/test evidence and an explicit physical-acceptance gap; do not promote or claim completion. Only after P0.1 is complete and checkpointed may Management authorize the next slice.
- **Frozen safeguards / excluded work:** exact State/team/generation fences, atomic publication, verified same-league/team last-good, tenant isolation; Simulation 2.0/50k/RNG/replay, Foundation 4 economics, approved #370 Dynasty formula; no #375, PIT/history expansion, Owner Intelligence, provider refresh, model changes, architecture refactor, schema migration, or distributed infrastructure.
- **Handoff status:** P0.1 is not complete. Resume from this branch after validating its current head in a code-capable environment. Do not repeat the accepted audit or baseline collection; do not start P0.2.


### 2026-10-06 — P0.1 authorized implementation start (pre-code checkpoint)

- **Main:** 0ef839ef9edeae7dad85fb6e52984c2998699e2a; latest main remains docs-only relative to live #391.
- **Active branch / head:** work/p0-1-baseline-20261006, exact pre-code head 6da7fa6ae515c48724d4e97635c4624ca0c4bdad. No PR yet.
- **Live deploy:** #391 commit 583f48dca0c6b763b7d249e420b82964a15291d2, deploy dep-db229jvlot8c73dieqtg; unchanged.
- **Accepted baseline:** see prior 01:25Z entry; do not repeat broad audit or baseline gathering. Remaining measurement gaps are journey-correlated restore/read/byte timings, visible generation/first useful render, foreground API timings, and actual browser retry/poll/handoff counts. Physical saved-session Safari remains unobserved.
- **Change scope authorized now:** P0.1 instrumentation-only using the exact source files/functions and event/test design in the prior implementation-ready checkpoint. Preserve the unresolved #391 Dynasty mismatch as a deterministic regression case. No architecture refactor, P0.2, or production deployment in this slice.
- **Before-code tree:** this commit updates only this handoff to record slice start. Next action is implement telemetry on the named code paths, then focused tests and the league-atlas-north-star.yml PR validation. The repository ci.yml runs the full suite; reserve that for the stable merge gate.
- **Frozen safeguards:** unchanged as enumerated above.


### 2026-10-06 — P0.1 instrumentation implementation / pre-PR checkpoint

- **Authority:** current main remains `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; latest Issue #393 confirms Work as sole writer. Live service/deploy remains #391 / `583f48dca0c6b763b7d249e420b82964a15291d2` / `dep-db229jvlot8c73dieqtg`.
- **Branch/head/PR:** `work/p0-1-baseline-20261006` at `48b918350d75029c5b226236fe981dcdd33ddff5`; no PR at checkpoint start.
- **Before-change evidence:** see the accepted baseline above. The physical saved-session iPhone/Safari journey and actual failing Dynasty stage are still unknown.
- **Changes:** instrumentation-only in journey telemetry, startup restore/runtime and persistence read boundaries, API request correlation/diagnostic intake, browser restore/API/retry/poll/handoff/useful-render/memory capture, focused regression coverage, and focused workflow inclusion. Exact files and event contract are in Current checkpoint.
- **After-change measurements:** none yet; branch has not run in GitHub Actions or production. Application-level JSON byte counts are measured on returned payload serialization; actual Supabase wire bytes remain unavailable from this adapter-level instrumentation.
- **Tests:** added focused tests but not executed yet. The PR will trigger the focused League Atlas action and standard CI once, at stable merge head. Full-suite result pending.
- **Unresolved:** physical Safari acceptance; exact live Dynasty failure stage; Safari JS heap measurement may be unsupported. No service/runtime measurements can be attributed to these code changes until deployed.
- **Frozen:** #370 metric, Current lens, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, publication fences, last-good and tenant boundaries; no P0.2 or product expansion.
- **Exact next action:** checkpoint doc update, then open PR and inspect focused Actions on its exact head.
- **Safe takeover:** continue this P0.1 PR only. Do not retry local cloud-browser/Git transport setup; use GitHub APIs/Actions. Do not deploy/merge based on unrun checks or claim the browser failure is resolved.


### 2026-10-06 — P0.1 PR #394 opened

- **PR / branch:** #394 opened against main from `work/p0-1-baseline-20261006`. Pre-PR exact code head: `48b918350d75029c5b226236fe981dcdd33ddff5`; PR initially reported head `c6f95217d621614c48a8eac75b976178a6e921c0` after the pre-PR handoff update. This post-PR checkpoint itself advances the branch once more; fetch the current exact head and its Actions before proceeding.
- **Checks at PR creation:** focused League Atlas North Star workflow, standard CI, Home/Franchise/other path-triggered Actions and diagnostics were in progress. No conclusions about validation yet.
- **Changes/measurements:** same instrumentation-only P0.1 slice detailed above; no production measurements after code because no deployment. Existing baseline remains authoritative.
- **Next action:** fetch exact current branch/PR head, inspect only its associated Actions, and handle concrete failures. No merge/deploy until exact-head checks are understood.
- **Safe takeover:** read this checkpoint, P0 directive, Issue #393, then PR #394. Continue sole-writer P0.1 only; keep all frozen safeguards and do not begin P0.2.


### 2026-10-06 — P0.1 PR validation corrections

- **Authority / PR:** main `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; PR #394; branch `work/p0-1-baseline-20261006`. Live Render remains #391 commit `583f48dca0c6b763b7d249e420b82964a15291d2`, deploy `dep-db229jvlot8c73dieqtg`.
- **Exact code/test head before this checkpoint:** `b7f5fe7f0e275e70e60da8ca5647c6cfa51a0bf1`. This handoff update advances branch head; fetch exact PR head for final validation.
- **Findings:** first PR checks passed JS syntax but failed Atlas/Home focus on stale asset cache identities. After key refresh, Home focus passed; Atlas syntax passed but telemetry tests had INFO capture and import errors. Those test-only causes are corrected in `b7f5fe7f0e275e70e60da8ca5647c6cfa51a0bf1`.
- **Validation:** exact corrected-head Action results pending. Earlier full-suite Actions were in progress and are not disposition for the corrected head.
- **Changes:** no new runtime change in test harness correction; cache keys are aligned with modified source asset blob hashes. P0.1 instrumentation remains the sole scope.
- **Next action:** fetch exact PR head after checkpoint and inspect Actions; proceed only on precise results.
- **Safe handoff:** continue #394 P0.1 on its exact branch; do not retry cloud transport/browser setup, deploy without green exact-head checks, weaken Dynasty generation fence, or start P0.2.


### 2026-10-06 — P0.1 final instrumentation/privacy checkpoint before final Actions

- **Main / branch / PR:** main `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; PR #394; branch `work/p0-1-baseline-20261006`.
- **Exact code/test/privacy head before this checkpoint:** `f2c7898b0d057c408735835831b916da0e4376a5`. This handoff commit advances PR head; fetch exact branch head and associated Actions.
- **Checks:** focused Atlas workflow passed on preceding head `621c24c0e500e4cd3af6e7d093ed63fa766a3f49` including syntax, telemetry regression tests, League Atlas tests, composition sanity and final-acceptance provider authority audit. Home focused checks also passed on the same head. Full CI and focused workflows passed on exact branch head `dcae01cdc779589c2d5e1c7072fd1679f54537b` (before the final browser merge-key and app-cache-key correction). The later correction ensures differing State/publication generations never share retry summaries and fingerprints the modified app.js delivery URL; it is pending exact-head validation.
- **Final privacy change:** browser and server logs now preserve only the known Product Context, readiness, Atlas, team views, value lenses, Dynasty rooms and diagnostics API route names; any other API route is recorded as `/api/other`. This prevents dynamic endpoint segments from carrying identifiers into diagnostics.
- **Measurements:** production baseline remains pre-change and is unchanged; implementation has not been deployed. Application payload JSON byte counts are not exact wire egress. Physical Safari/browser memory remains unobserved until Management’s acceptance run.
- **Next action:** fetch latest PR head/runs; require final focused + full CI success, then report the ready PR for hosted deployment and physical iPhone/Safari measurement. Do not merge/deploy without explicit hosted acceptance direction; do not start P0.2.
- **Safe takeover:** continue PR #394 at current exact branch head. Do not repeat pre-change audit or baseline, reopen #370/model/runtime semantics, or begin later P0 slices.


### 2026-10-06 — P0.1 correlated memory measurement checkpoint

- **Branch / PR:** `work/p0-1-baseline-20261006`, PR #394. Main remains `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; Render remains #391 commit `583f48dca0c6b763b7d249e420b82964a15291d2`, deploy `dep-db229jvlot8c73dieqtg`.
- **Exact code head before this checkpoint:** `76bb04b27306b8e6066232fd4fdfd405184371eb`. This documentation commit advances the PR; fetch exact head and associated Actions.
- **Change:** correlated request-completion events now include `HeavyWorkCoordinator` current RSS and peak RSS, in addition to browser `performance.memory` supported/value fields. No resource ownership or scheduling behavior changed.
- **Validation:** focused Atlas passed on earlier code head `621c24c…`; exact head with API redaction and RSS sampling is pending focused + full CI.
- **Next action:** inspect Actions at post-checkpoint exact head. After green checks, return PR #394 for Management’s hosted deployment and physical iPhone/Safari journey; no merge/deploy initiated here.
- **Safe takeover:** continue P0.1 only from exact PR head and this file. Keep all accepted model/runtime safeguards closed and do not start P0.2.


### 2026-10-06 — P0.1 saved-session delivery and generation-attribution checkpoint

- **Authority / PR:** main `0ef839ef9edeae7dad85fb6e52984c2998699e2a`; PR #394; branch `work/p0-1-baseline-20261006`; live #391 remains commit `583f48dca0c6b763b7d249e420b82964a15291d2`, deploy `dep-db229jvlot8c73dieqtg`.
- **Exact code/test head before this checkpoint:** `a2e069b0f8a22a1dd8076722ee9e0f52ca1b8aa8`. Fetch post-checkpoint branch head and Actions before disposition.
- **Finding/correction:** retry-event coalescing now includes target State and publication generation, preserving handoff attribution when one generation supersedes another. The instrumented `app.js` URL now carries its Git blob fingerprint so existing saved-session browsers receive the journey ID/header code. Added focused assertions for both.
- **Validation:** focused Atlas, Home, and full CI all passed on preceding head `dcae01cdc779589c2d5e1c7072fd1679f54537b7`; checks for final correction are pending.
- **Scope / safeguards:** no restore/retry/publication behavior, analytical authority, or product ranking changed. #370, Current semantics, Simulation 2.0, Foundation 4, and publication fences remain frozen.
- **Exact next action:** inspect Actions for the exact post-checkpoint PR head, then return #394 for Management’s hosted deployment and physical iPhone/Safari measurement. Do not merge/deploy or start P0.2 in this slice.
- **Safe takeover:** continue PR #394 and this P0.1 only; no broad audit or pre-change baseline repetition, no Cloud browser/Git transport recovery, no product expansion.
