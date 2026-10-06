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

**State:** P0.1 INSTRUMENTATION IMPLEMENTED — pre-PR validation checkpoint.  \
**Owner:** Work, confirmed by the latest Issue #393 Management ownership correction.  \
**Current main:** `0ef839ef9edeae7dad85fb6e52984c2998699e2a`.  \
**Active branch / exact code head:** `work/p0-1-baseline-20261006` at `48b918350d75029c5b226236fe981dcdd33ddff5`. This head is based on current main and contains the pre-code docs checkpoint plus instrumentation/test/workflow commits.  \
**PR:** none yet.  \
**Live deploy:** Render service `fsffl-next-private-beta`, deploy `dep-db229jvlot8c73dieqtg`, live commit `583f48dca0c6b763b7d249e420b82964a15291d2` (#391); unchanged because the instrumentation branch is not deployed.

The accepted pre-change baseline above remains the only measured production baseline. No post-change performance or hosted/browser values exist yet.

### Implementation in this slice

Instrumentation only. No restore order, read contract, API response semantics, retry limits, publication fencing, Dynasty formula, model authority, or product behavior was changed.

Files changed:

- `src/fsffl/journey_telemetry.py`: bounded allowlisted structured events; opaque request/restore IDs; safe browser batch ingestion; persistence read decorator. It emits no raw user IDs, SQL parameters, player/roster payloads or credentials.
- `src/fsffl/product/persistent_runtime.py`: records durable context restore, State activation, and exact-State intelligence restore stage elapsed time/outcome under one restore-run identity.
- `src/fsffl/persistence/postgres.py`: counts correlated runtime-context, league/team State snapshot, sync cursor, and reusable-artifact reads; records hit/miss, elapsed time, rows, artifact kind, and returned serialized JSON byte count where present. This is application payload serialization size, **not** measured Supabase wire egress.
- `src/fsffl/product/persistent_webapp.py`: traces only API requests carrying the browser journey header; returns request and startup-restore correlation headers; adds an authenticated, same-origin diagnostic intake with 64 KiB request limit and 80-event batch limit.
- `src/fsffl/product/static/app.js`: creates a session-scoped opaque journey ID; traces real fetch attempts/status/latency and saved-session Product Context restore; records browser memory support/value at flush; buffers and coalesces repeated request/retry events; submits once on terminal result or pagehide.
- `src/fsffl/product/static/product_shell.js`: counts actual shared-readiness poll calls, promotion retry waits, generation handoff outcome, and League Atlas asset URL.
- `src/fsffl/product/static/league_comparison.js`: counts value-lens/Atlas alignment/Dynasty attempts and retry waits; logs exact State/generation mismatch as failure; marks first useful render only when Dynasty is selected, the document is visible, rank cells exist, and room State + publication generation exactly match the visible Atlas.
- `tests/test_architecture_recovery_journey_telemetry.py`: covers allowlisting, bounded batch ingestion, persistence byte/count reporting, restore-run identity, and preservation of the exact-generation Dynasty failure/success fence.
- `.github/workflows/league-atlas-north-star.yml`: includes the new focused telemetry regression file and syntax checks for app.js, product_shell.js and league_comparison.js.

The browser captures `performance.memory` only where the browser exposes it. iPhone Safari may report memory as unsupported; this is explicitly represented rather than inferred. Render process memory remains a separate hosted sample.

The unresolved live Dynasty issue remains unclaimed: no physical iPhone/Safari run has yet shown whether the live request returns unavailable, a State/generation mismatch, or a valid room that fails to render. The new terminal browser events preserve whichever failure the physical run observes; automated tests keep generation mismatch as failure and never loosen the accepted generation fence.

### Validation and measurements at this checkpoint

- Baseline numbers remain as recorded in the 01:25Z checkpoint: restore-ready success p50 10.89s / p95 127.48s / max 223.04s; failure p50 11.98s / max 96.76s; 12.69 GB accepted prior egress figure; historical adapter-query totals; Render memory high-water ~524.4 MB; no previous correlated browser counts or foreground request samples.
- No local repository checkout, local JS/Python syntax checks, or local test runs were attempted in this continuation; Git transport/browser limitations are not being retried.
- Focused telemetry + League Atlas GitHub Actions have **not yet run**. They are configured to run on the PR. Standard CI also runs the full suite for a PR; this will be the one stable merge-gate full suite.
- No Codex review requested; the governing P0.1 continuation explicitly excludes Codex review.
- Hosted acceptance and physical iPhone/Safari acceptance remain pending deployment.

### Frozen safeguards

Simulation 2.0 mathematics, 50k/RNG/replay, Foundation 4 economics, approved #370 Dynasty metric, Current ranking semantics, exact State/team/publication-generation fences, atomic publication, verified same-league/team last-good, tenant isolation, P0.1-only scope, and the #375/PIT-history/Owner Intelligence hold remain frozen.

### Exact next action and safe continuation

1. Update this handoff with the validation PR checkpoint and exact resulting head.
2. Open one PR from `work/p0-1-baseline-20261006` to `main`; inspect focused League Atlas and standard CI checks on that exact PR head.
3. Fix only demonstrated instrumentation/test defects. Do not start P0.2.
4. After checks pass, record exact PR/head/review disposition. Deployment and physical acceptance require Management’s hosted process; when deployed, run the saved-session iPhone/Safari journey once and collect correlated `FSFFL_CUSTOMER_JOURNEY` Render logs by `journey_id` + `restore_id`, browser events, generation IDs, and matching Render memory window.
5. Resume from this file + directive + Issue #393 and the PR’s exact head. Do not repeat the broad audit or pre-change baseline; do not treat prior `ERR_BLOCKED_BY_CLIENT` as the app failure; do not reopen frozen semantics or start P0.2 before P0.1 is fully evidenced/checkpointed.
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
