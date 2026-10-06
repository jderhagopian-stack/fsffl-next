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

### P0.3 merged, deployed, and hosted-verified — automatic static-asset identity

- **Main / merge:** PR #398 merged from validated head `fe954b5078b2828d57088fd61d3399296dba430b`; current main and merged commit are `e90e96b18bc48d026d7cb971e9a09dc49dae80cb`.
- **Actions:** full CI run `37474382144` passed; focused Atlas, Home, Forecast, and PR164 workflows also passed. Full suite: **2,184 passed, 1 existing Starlette/httpx deprecation warning**. Focused asset tests passed 3/3 and Atlas cache-key regression 1/1.
- **Render:** service `fsffl-next-private-beta` / `srv-dae6k7vqj5pc73af7bt0`; deployment `dep-db2fupajnfac73cnmnfg` is live on exact main commit above. Auto-deploy is disabled.
- **Hosted asset evidence (2026-10-06 15:32 UTC):** after the free instance woke and startup completed, Render logs show `HEAD /static/app.js` and `GET /static/app.js` returning 307, followed by the computed SHA-256 URL `/static/app.js?v=sha256-4245304858de52d3bf8d994911be6f8d7b7d563d822ef422e561074abb429ab3` returning 200. This confirms redirect and fingerprinted delivery on the deployed instance. Request logs do not expose response headers; immutable caching was verified in the earlier hosted check recorded in the Work conversation, while this log-only check does not independently remeasure the cache header.
- **P0.3 scope/files:** centrally hash served static-file bytes; redirect missing/stale `v` values while preserving unrelated query parameters; serve current fingerprint URLs with immutable one-year caching. Files: `src/fsffl/product/static_assets.py`, `src/fsffl/product/webapp.py`, `tests/test_static_asset_fingerprints.py`.
- **Outcome:** implementation, focused coverage, the single merge-gate full suite, merge, deployment, and hosted redirect/200 verification are complete. No model, State, publication, or Dynasty behavior changed.
- **Frozen safeguards:** exact State/team/publication-generation safety; atomic publication; verified last-good; tenant isolation; Current, approved Dynasty, Career Intrinsic, Foundation 4 economics, Simulation 2.0/50k/RNG/replay. No #396 patch, #375, PIT/history product expansion, Owner Intelligence, or distributed infrastructure.

### P0.4 in progress — simpler published-reader contract

- **P0.3 closeout:** PR #398 merged from validated head `fe954b5078b2828d57088fd61d3399296dba430b`; app/main commit `e90e96b18bc48d026d7cb971e9a09dc49dae80cb`. Full CI `37474382144` passed 2,184 tests / 1 existing warning; focused asset tests 3/3 and Atlas cache-key regression 1/1. Render deployment `dep-db2fupajnfac73cnmnfg` was live on that exact commit. Render logs independently confirmed stale `/static/app.js` redirected 307 to content-derived SHA URL and the fingerprinted URL returned 200. Earlier hosted verification also confirmed immutable caching.
- **P0.4 implementation:** PR #399 merged from exact validated head `7ad1a2dcc0113de9df8915d10589f8064299e7d7` as app commit `d13817b57d51fa8533eb3117a5dc1d227d5733af`. It reused the manifest already fetched by `load_for_runtime` during cold snapshot validation. Required-surface metadata checks and exact generation/team/league/State/payload-hash gates remain intact. No caching across requests or processes was added.
- **PR / files:** PR #399; `src/fsffl/product/presentation_continuity.py`, `tests/test_presentation_continuity.py`, and this workstream file.
- **Validation:** the one stable merge-gate full suite passed **2,185 tests, 1 existing Starlette/httpx warning, 174.09 seconds** (Actions run `37489117515`). The exact test `test_cold_surface_read_reuses_manifest_during_snapshot_validation` was included in this suite. The PR-triggered PR164 focused workflow also passed **123 tests** (run `37489117569`). GitHub connector does not expose workflow dispatch for running the single test separately.
- **Render:** service `fsffl-next-private-beta` / `srv-dae6k7vqj5pc73af7bt0`; deployment `dep-db2he5ajnfac73csiitg` is live on P0.4 app commit `d13817b57d51fa8533eb3117a5dc1d227d5733af`; build/deploy completed at 2026-10-06 15:45:05 UTC. Auto-deploy remains disabled.
- **Hosted restore observation:** new instance startup completed and durable-context restore reached ready in **9,098 ms** (restore ID `535c2c6b-7eee-456b-b59c-8ac01be57ec7`). Logs showed runtime context, State snapshot, published-generation, Forecast, Simulation, and Value persistence hits. This was startup restoration only; it is not a comparable saved-session/product journey and does not prove Dynasty visibility, P0.4 egress reduction, or foreground latency improvement.
- **Consumer trace / safety:** `PresentationContinuityStore.promote` writes surface payloads then the manifest last. Hosted readiness uses a process-local availability hint; cold availability reads a manifest and required-surface metadata. Ordinary reads load a manifest and requested payload, verifying exact publication generation, selected team, league, State, surface, and payload hash. Current and same-league last-good remain distinct candidates. Availability hints are not integrity proof.
- **Remaining P0.4 work:** the merged change removes duplicate manifest discovery only within the cold surface-validation path. Other restore/readiness and ordinary-reader manifest lookups remain. Continue bounded consumer tracing and prove freshness/continuity before reducing any other reads; do not cache publication authority in process-local state or weaken identity checks.
- **Measurements / acceptance:** preserved P0.1 baseline remains 158 persistence-read events / 67,074,210 application-serialized JSON bytes (not wire egress). No post-change customer-journey comparison exists. The physical saved-session iPhone/Safari acceptance remains outstanding; Dynasty ranks are not claimed to render.
- **Frozen safeguards:** exact State/team/publication-generation safety; manifest-last atomic promotion; payload integrity; verified same-league last-good; tenant isolation; Current, approved Dynasty, Career Intrinsic, Foundation 4 economics, Simulation 2.0/50k/RNG/replay. Do not revisit #396 or P0.1/P0.2/P0.3. Do not begin P0.5 early.
- **Exact next action:** continue P0.4 from the current main descendant of `d13817b`. Use the preserved saved-session journey to assess remaining duplicate discovery and freshness behavior before further edits. Keep subsequent code changes bounded and focused-test-first; use one full suite at that slice's stable merge gate. Do not claim end-to-end acceptance from startup logs.
- **Safe handoff:** start from current GitHub main and this checkpoint, with P0.4 active. Preserve the stale/dirty local scratch clone. Do not patch #396, reopen completed P0.1/P0.2/P0.3, alter publication identity fences, or start P0.5.


### P0.2 implementation merged and deployed — hosted read verified

- **P0.1 disposition:** measurement complete; physical Dynasty acceptance still fails. Exact Safari run remains a mandatory end-to-end acceptance journey. No further #396 patch.
- **Failure class:** B — the 07:12 ET request carried Atlas State 606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3 and generation 58d3d6edb95d30e52159b58df8fa5a269f7637158dbc1487fde252f8486bbc23, returned HTTP 200, but showed no Dynasty ranks. Exact State/generation safety remains frozen; remaining visible-render path is per-surface persistence/readiness/generation/promotion machinery scheduled for P0.4/P0.5.
- **PR #397:** branch work/p0-2-metadata-first-20261006; tested code head 42433d166a9674c3fbcf07302b962202aba89a75; exact merge head f495c9e04dc4f3d2980c9d4a8b19aa9b465986ef; merge commit d3b3bc9cff33a4f2491139c39128f8aabbe648e8. Commits after tested code head changed only the handoff file. The review bot's initial P1 cache-rename finding was at commit 026d32f; the current code head has a consistent method/dictionary rename, covered by successful full CI.
- **Bounded change:** metadata-only exact/latest reusable-artifact SQL queries; presentation availability checks small manifest plus metadata for required artifacts instead of downloading all surface payloads; exact requested surface payload remains hash-checked before serving.
- **Files:** src/fsffl/persistence/contracts.py, src/fsffl/persistence/postgres.py, src/fsffl/product/presentation_continuity.py, tests/test_presentation_continuity.py, tests/test_persistence_metadata_reads.py.
- **Validation:** focused Actions completed successfully. Full pytest -q on code head 42433d1…: **2,181 passed, 1 existing Starlette/httpx deprecation warning**, 171.99 seconds. Only subsequent commits changed this handoff. No extra full suite was triggered manually.
- **Render deployment:** private-beta service srv-dae6k7vqj5pc73af7bt0; deployment dep-db2dr70ae00c73a085o0, status live; deployed main commit 3a43ba8b36f60883d51e1924cc286bb9e6ab476e (PR #397 merge plus pre-deploy docs checkpoint). Render build succeeded; app startup completed; deployment event evt-db2ds0ahabec73d06pf0 succeeded at 2026-10-06 11:39:45 UTC. The read-only GET /health/runtime-resources returned 200 at 11:39:52 UTC. No acceptance workload endpoint was called.
- **Hosted observation, not a before/after comparison:** startup restore 53dafac7-7852-42c8-8992-2fb04dbceeff reached durable-context ready in 8,595.84 ms. Startup logs showed several full payload reads and a manifest miss; this did not exercise the metadata-first availability hit path, so do not claim a measured customer-journey egress reduction. Original P0.1 baseline remains 158 persistence reads / 67,074,210 application JSON bytes (not wire bytes). Re-measure on the preserved end-to-end journey after the scheduled reader/lifecycle simplification.
- **P0.2 outcome:** implementation, tests and hosted deployment are complete. Customer-visible Dynasty acceptance remains unresolved and is not represented as passing. The P0.1 physical journey stays a required e2e acceptance test.
- **Frozen safeguards:** exact State/team/generation fences; atomic publication; verified last-good; tenant isolation; Current; approved #370 Dynasty semantics; Career Intrinsic; Foundation 4 economics; Simulation 2.0/50k/RNG/replay. No #396 patch, #375, PIT/history expansion, Owner Intelligence, or distributed infrastructure.
- **Exact next action:** with P0.2 checkpointed, begin P0.3 automatic static-asset identity in sequence; do not begin P0.4/P0.5 early. First inspect current main static asset references/cache-busters and existing build/test conventions; keep the slice bounded to centrally generated content-derived fingerprints and focused regression coverage.
- **Safe handoff:** latest main currently contains the P0.2 deployment checkpoint; fetch exact main before creating P0.3 branch. Read governing directive and this latest checkpoint. The scratch clone is on a stale, dirty unrelated branch; use connected GitHub tools and preserve those workspace changes. Do not repeat P0.1 baseline gathering, patch #396, weaken invariants, or treat the /health/runtime-resources check as Dynasty acceptance.

### P0.1 measurement checkpoint (completed; physical acceptance failed)

### Latest checkpoint — P0.1 measurement complete; Dynasty acceptance remains a required architecture test

- **Status:** P0.1 measurement/instrumentation objective is complete. Dynasty Position & Depth still fails physical acceptance, but no further #396 request-handoff patch is authorized. Carry the exact Safari journey as a mandatory end-to-end acceptance test through the approved P0 sequence; do not block P0.2 on repairing the old per-surface plumbing.
- **Classification:** **B — simplification target.** The 07:12 ET Safari request contained the Atlas State and publication generation, and Render returned HTTP 200. The failure is therefore no longer evidence of a missing identity request contract. The remaining visible-render failure sits in the overlapping per-surface manifest/read, generation negotiation and Product Context promotion/readiness handoff mechanisms that P0.4 simplifies and P0.5 consolidates. The exact State/generation fence remains a foundational invariant and stays frozen; this classification does not relax it.
- **Main checkpoint:** documentation checkpoint commit `773468301654fd56f65743ec4852769bcc7898ef` preceded this measurement update. The commit produced by this update becomes the P0.2 base.
- **Live Render:** service `fsffl-next-private-beta` / `srv-dae6k7vqj5pc73af7bt0`; deployment `dep-db28eoks728c73bgnu00`; live on app commit `d7cbbb5820a03de8309165752e124ecd0dce30fe`. Auto-deploy disabled.
- **PR #396:** merged as `d42593ed73aed4ca1fe62338273df9fa61947fed`, from reviewed exact head `a88f7c0349f855f49ad0a149ca2b089b5eb95dc4`, branch `work/p0-1-dynasty-publication-request-fence-20261006`. Exact-head full CI and focused workflows passed; fresh review found no major issues.
- **Preserved physical journey:** Management reports no Dynasty ranks at 07:12 ET on 2026-10-06. Render journey ID `3a5f455b-fde9-4daf-9c6a-585cb2d7b0a4`; log window 11:07–11:12 UTC. Atlas served State `606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3`; Dynasty request at 11:12:37Z included that exact `state_id` plus publication generation `58d3d6edb95d30e52159b58df8fa5a269f7637158dbc1487fde252f8486bbc23`. It completed HTTP 200 at 11:12:43Z in 5,401 ms; request-time RSS was 356,597,760 bytes, journey peak RSS 365,068,288 bytes. The HTTP log does not expose the semantic response body/status, so do not infer that Dynasty evidence was ready or that this was a state mismatch. The user-observed absence of visible ranks is the acceptance result.
- **Journey measurements:** durable context restore ready in 7,939 ms; Product Context completed in 8,095 ms and later 12,153 ms; Atlas request completed in 2,039 ms. The exact journey also had repeated publication-manifest and presentation-surface reads. Browser diagnostics POST for this journey ended HTTP 401 after 136,297 ms, so the server-side journey/request logs are the reliable trace; browser outcome telemetry was not successfully ingested.
- **Baseline retained:** the earlier complete P0.1 journey remains the egress baseline: 158 persistence-read events and 67,074,210 application-serialized JSON bytes (not wire bytes), including repeated large forecast and runtime presentation payload reads. Do not regather the baseline. These are direct P0.2 targets.
- **Frozen safeguards:** exact State/team/publication-generation safety; atomic publication; verified last-good; tenant isolation; Current ranking; approved #370 Dynasty semantics; Career Intrinsic; Foundation 4 economics; Simulation 2.0/50k/RNG/replay. No #375, PIT/history expansion, Owner Intelligence, unrelated product work, or broad lifecycle refactor ahead of sequence.
- **Exact next action:** start P0.2 metadata-first persistence/egress as the next approved bounded slice. Add metadata-only existence/identity/generation/freshness lookup for reusable artifacts and presentation surfaces, load large payload only when consumed, and eliminate repeat same-process full-payload reads only where safe. Use the preserved journey above plus the earlier 67.1 MB journey as regression/measurement fixtures. Do not alter Dynasty semantics or start P0.3/P0.4/P0.5 early.
- **Safe handoff:** begin from the main commit created by this checkpoint. Read the directive, this latest checkpoint, Issue #393, then inspect storage adapter and reusable-artifact/presentation call sites. Do not patch #396 again, rerun P0.1 baseline, weaken any identity fence, or treat a 200 response/startup as product acceptance.

### Historical checkpoint (superseded by latest execution entry)

**State:** P0.1 remains open after the #395 physical acceptance failure documented above. Complete the request-contract correction and one final physical iPhone/Safari saved-session acceptance before closing P0.1 or beginning P0.2.
**Owner:** Work is the sole writer under Issue #393.
**P0.1 application commits:** PR #394 instrumentation merged as `5b243b00179deeeeda26c6a06b72bd4abfd38506`; corrective PR #395 merged from validated head `3baeecb292481ac322bbab6c705bbf9374c47ac0` as `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`.
**Current main before this documentation-only correction:** `f54c7eee9e97d1215cc541a7a1ea5bf37c33adaa`; fetch GitHub `main` for the exact resulting documentation commit.
**Live Render:** `fsffl-next-private-beta` service `srv-dae6k7vqj5pc73af7bt0`, deployment `dep-db26ufh7lnhs73drheqg`, status `live`, exact app commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`.
**Corrective validation:** PR #395 validated at app/test head `3a4eb0272ea969c46315ff382b01c518f040b949` and merged from exact PR head `3baeecb292481ac322bbab6c705bbf9374c47ac0`; full CI 2,175 passed / 1 warning, focused 123 passed, trace passed. Initial RSS ceiling failure did not reproduce. The code change requires persisted Dynasty State and generation to match current publication; continuity still verifies team/payload.
**Physical run evidence:** seven screenshots IMG_0175–IMG_0181 show phone times from 11:01 to 11:13 and the FSFFL Dynasty league. Correlated Render logs run 2026-10-06 03:00:55–03:13:28Z (consistent with about 11:01–11:13 p.m. EDT on Oct 5; exact seconds/timezone were not provided by the tester). Browser journey ID: `a4e54323-b003-45ef-84ac-6cd50dea55c9`.
**Visible outcome:** IMG_0176 shows Current ranks populated. IMG_0177 and IMG_0181 show Dynasty selected, but the table still shows roster counts and “Loading Dynasty room values… roster counts are breadth only”; no Dynasty ranks appear in the submitted captures. IMG_0181 simultaneously shows global “Intelligence current.” IMG_0178–IMG_0180 show a rebuild/last-good period; IMG_0180 shows 6/7 build with Forecast, Simulation and Current Value unavailable and Intrinsic Full.
**Measured journey:**
- Product Context completed five times with HTTP 200; latency 5.8–21.0 seconds (median 16.2 seconds). Browser trace recorded product-context restore ready in 5,950 ms.
- Shared readiness polling recorded 13 polls with a 30,000 ms retry wait. Journey failure was recorded after 483,081 ms. Safari memory support was reported as unavailable.
- Dynasty endpoint logged three GETs, each HTTP 200, with server latency 39,999.95 ms, 23,501.25 ms, and 5,619.5 ms. Highest request-time Render RSS sample was 428,916,736 bytes.
- The 13-minute journey window contains 124 correlated API request starts/completions and 158 persistence-read events. Those reads report 67,074,210 returned application-serialized JSON bytes across the logged artifact kinds; these are not exact Supabase wire bytes. Full details and per-artifact totals are in the 2026-10-06 physical-run execution-log entry below.
- The client’s flushed Dynasty summary reported `request_count=2`; Render records three same-journey Dynasty requests across the window, including a later request after the failure batch had been flushed. Treat server request logs as the full window count; the client summary is not a complete count for the continued session.
**Root cause / deployed correction:** with canonical Career evidence still preparing for active State `ee05aa91…`, the Dynasty route accepted any ready persisted presentation with a generation ID and returned it, including verified last-good State `3d7808d4…`. The browser correctly rejected this mismatch. A separate matching last-good telemetry event belonged to a different request. PR #395 now requires active league, exact State and current publication generation before returning a persisted Dynasty surface; the continuity loader continues enforcing exact team and payload integrity. No stale evidence is relabeled current.
**Unresolved:** physical iPhone/Safari acceptance of visibly populated current-generation Dynasty ranks remains outstanding. High foreground and endpoint latency, repeated persistence reads, the client/server Dynasty request-count discrepancy, and the measured serialized read volume remain findings for later approved slices; P0.2 is held until this customer journey passes.
**Frozen safeguards:** approved #370 Dynasty metric; Current ranking semantics; Simulation 2.0/50k/RNG/replay; Foundation 4 economics; exact State/team/publication-generation fences; atomic publication; verified last-good; tenant isolation. No #375, PIT/history expansion, Owner Intelligence, broad model changes, or distributed infrastructure.

### Exact next action

Implement the bounded publication-bound Dynasty request contract described in the current checkpoint, validate and deploy it, then stop for one final physical iPhone/Safari acceptance. P0.1 closes only after Dynasty ranks visibly render with the exact Atlas State and publication generation. Begin P0.2 only afterward.

### Safe handoff

Read the governing P0 directive, this current checkpoint, the P0.1 exact-State corrective and physical-run entries, Issue #393, and merged PRs #394/#395. Main’s corrective app commit is `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`; live Render deployment is `dep-db26ufh7lnhs73drheqg` on the same commit. Do not redo the baseline, reopen frozen semantics, treat deployment/startup as physical acceptance, or begin P0.2 before the saved-session acceptance is captured and checkpointed.

**State:** P0.1 remains open. Physical acceptance of PR #395 failed again; the new evidence isolates a request-identity race. This checkpoint records the failure before implementation. Do not begin P0.2.
**Owner:** Work remains the sole writer under Issue #393.
**Current main before checkpoint:** `c49295a56ce5ac676a271e0e6112af53a7064f36`.
**Live Render:** service `srv-dae6k7vqj5pc73af7bt0`, deployment `dep-db26ufh7lnhs73drheqg`, live on PR #395 application commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`.
**Failed physical journey:** Safari captured visible Atlas State `3d7808d45587314cafa3e8fb1e694a57158cd16524b2c2a86b9dfb0e5b5176bf`, publication generation `da5a06b340a8ab7868f1876a91500d53b6da67c89338185d7944fa8eace8a8ab`. Dynasty returned State `e582e5ce160226c0ab65f88277c12d5dd4b957a97eacc4d70841f6f360f3a21d`; browser correctly recorded `state_mismatch`. The acceptance was 11:54–12:00 ET. #395 was already live.
**Root cause:** the browser captured Atlas State/publication identity but called Dynasty without either value. The route independently called `runtime_store.get(user_id)`, which had advanced to a different State. This is distinct from #395’s persisted-fallback defect.
**Approved bounded correction:** require `state_id` and `publication_generation_id` in the Dynasty GET. Compare the requested pair with the runtime publication before resolving or building evidence. If different, return an explicit `status: superseded` response containing requested and superseding identities and no rooms; do not serve B under A’s request. The browser must refresh Product Context read-first once and rely on the existing product-context-updated Atlas promotion path. Keep exact State/team/generation validation intact.
**Branch / PR / head:** not started; create `work/p0-1-dynasty-publication-request-fence-20261006` from the checkpointed main commit returned by the doc update. One PR only.
**Files expected:** Dynasty route, Atlas Dynasty request/promotion handling, focused route and browser contract regressions, and this handoff.
**Measurements:** no new latency/RSS/egress baseline gathered; explicitly deferred P0.2. Failed journey identity above is the only new physical evidence.
**Validation / unresolved:** no implementation/tests yet. The missing request pair is confirmed. Focused exact A-visible/B-runtime regression plus frontend request/superseded-promotion test required, then full CI at stable merge gate, fresh exact-head review, merge/deploy and live verification.
**Frozen safeguards:** approved #370 Dynasty metric; Current semantics; Simulation 2.0/50k/RNG/replay; Foundation 4 economics; exact State/team/publication-generation fence; atomic publication; tenant isolation. No model change, P0.2, #375, history expansion, Owner Intelligence, or broader persistence refactor.

## Execution log

### 2026-10-06 — Render deployment blocked pending workspace selection

- **Main:** merged application commit `d42593ed73aed4ca1fe62338273df9fa61947fed`; post-merge handoff commit `030df12cf533074a97f10d7cdacfc2cae1a44ebc`. This note will advance main; use resulting current main for deployment.
- **PR / validation:** #396 merged from exact head `a88f7c0349f855f49ad0a149ca2b089b5eb95dc4`; all exact-head required tests passed and fresh Codex review found no major issues.
- **Render:** target is service `srv-dae6k7vqj5pc73af7bt0` (`fsffl-next-private-beta`), currently live on #395 deploy `dep-db26ufh7lnhs73drheqg`. Service config confirms auto-deploy disabled.
- **Deploy attempt:** manual trigger was rejected before deployment with `no workspace selected`. Connector instructions require Management to select a workspace and explicitly forbid choosing one automatically. Read-only workspace listing returned one option, “My Workspace” `tea-dae6if9t0dsc73918us0`; no deploy has started.
- **Exact next action:** obtain Management’s explicit selection of the Render workspace; then select that workspace and trigger deployment of the current main commit. Verify live deploy/commit and hosted delivery, then stop for one final physical iPhone/Safari acceptance. Do not begin P0.2.
- **Unresolved / safeguards:** deployment and physical acceptance remain outstanding. All P0.1 fences and frozen Current/#370/Simulation/Foundation semantics remain unchanged.

### 2026-10-06 — PR #396 merged; Render deployment pending

- **Main / merge:** PR #396 merged from reviewed/green head `a88f7c0349f855f49ad0a149ca2b089b5eb95dc4`; squash merge commit `d42593ed73aed4ca1fe62338273df9fa61947fed`. Full CI and all focused checks passed on the PR head; Codex review of exact head said no major issues.
- **Branch / PR:** #396 `work/p0-1-dynasty-publication-request-fence-20261006`, merged. App changes include API route, internal publication builder caller, Dynasty loader, telemetry whitelist, asset keys, and focused regression/callsite tests.
- **Live before deploy:** service `srv-dae6k7vqj5pc73af7bt0`, live deployment `dep-db26ufh7lnhs73drheqg`, app commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`. Render service confirms auto-deploy disabled.
- **Change:** exact State + publication generation travel from visible Atlas through the Dynasty request. Runtime mismatch returns explicit `superseded` (requested and superseding identities, no rooms) before coordinator/presentation reads. Browser refreshes Product Context through the existing Atlas promotion path. Internal presentation builder passes captured identity. Cache keys are refreshed.
- **Validation:** full CI `37415031517` passed; Atlas `37415031461`, Home `37415031670`, Franchise `37415031454`, PR164 `37415031538`, private-beta diagnostics `37415031491`, forecast trace `37415031448` passed. Fresh Codex review at `a88f7c0349f855f49ad0a149ca2b089b5eb95dc4` reported no major issues.
- **Physical acceptance / measures:** not yet rerun; the #395 capture remains failed. No new latency, RSS, or egress measurements. P0.1 remains open.
- **Exact next action:** trigger manual Render deployment of the current main commit (Render auto-deploy is off), verify the deployment is live on the exact commit and hosted assets are current. Then stop for one final saved-session physical iPhone/Safari acceptance. Do not begin P0.2.
- **Safeguards:** all current-generation State/team/generation fences, Current semantics, approved #370 metric, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, atomic publication and tenant isolation remain frozen.

### 2026-10-06 — green merge checkpoint; documentation-only advancement

- **Main / live:** PR base `408431fd4bb0fb96daf800e7ec036616ba79c12c`. Render still serves #395 app commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`, deployment `dep-db26ufh7lnhs73drheqg`.
- **PR / branch / tested code head:** #396, `work/p0-1-dynasty-publication-request-fence-20261006`; code/test head `e7272f48210b878d6e520bbb4579d201bdc0b56c`. This handoff commit is docs-only and will advance PR head; refetch exact head.
- **Validation at code/test head:** full CI `37414650538`, Atlas `37414650507`, Home `37414650509`, Franchise `37414650518`, PR164 `37414650568`, private-beta diagnostics `37414650546`, forecast trace `37414650535` all completed successfully.
- **Fresh review:** Codex manually reviewed exact code/test head `e7272f48210b878d6e520bbb4579d201bdc0b56c` and reported “Didn't find any major issues.” Its earlier P1 about the internal route caller is fixed in `persistent_webapp.py` and covered by a focused test. Its cache-key finding is fixed; Atlas focused cache checks pass with refreshed bundle identities.
- **Correction:** endpoint contract includes State + generation; server returns superseded/no rooms if either differs. Browser sends both and refreshes Product Context once through existing Atlas promotion. Superseded telemetry uses explicitly named superseding identity fields. Exact #395 A-visible/B-runtime test uses captured State IDs.
- **Pre-merge / next:** because this record is docs-only, no application code changed since the green/reviewed code head. Require the exact updated PR head’s CI and mergeability to be green, then merge with expected head SHA. Deploy exact resulting main commit to Render (auto-deploy disabled), verify live, update this handoff with identities and stop for final physical iPhone/Safari acceptance.
- **Unresolved:** final physical acceptance only. P0.1 stays open; no P0.2.
- **Frozen safeguards:** exact State/team/generation fence; #370 formula; Current ranks; Simulation 2.0/50k/RNG/replay; Foundation 4 economics; atomic publication and tenant isolation.

### 2026-10-06 — Codex review P1 corrected; validation pending

- **PR / branch / code head:** #396, `work/p0-1-dynasty-publication-request-fence-20261006`; code/test head before this note `2dee8ac27deb2884ac51c62d9797d091c52edfab`.
- **Review finding:** initial Codex review was anchored to stale head `248fd83` and correctly identified an internal caller in `persistent_webapp.py`: Dynasty presentation promotion calls the route function directly without HTTP query arguments. This would break the publication builder after making IDs required. It also observed stale bundle keys; those were already updated before the latest full passing workflow.
- **Correction:** internal presentation builder now passes the captured `context.league_state.state_id` and `context.publication_generation_id`. Added focused test assertions. Request contract remains required and server still returns superseded with no evidence on mismatch. Existing cache tokens reference final app/Atlas/shell bundle hashes and passed Atlas focused cache tests.
- **Previous exact-head gate:** at `ffa78ec82bf0f99e68c8f94b8cf388044b00242b`, full CI `37414284224`, Atlas `37414284231`, Home `37414284246`, Franchise `37414284305`, PR164 `37414284207`, and forecast trace `37414284218` all passed. Because backend code changed after that gate, those results do not validate the new head.
- **Next:** re-fetch PR head after this note; rerun focused and full CI, then request fresh Codex review on the final exact head. Merge and deploy only if green/clean. Stop for final physical iPhone/Safari acceptance. No P0.2.
- **Safeguards:** exact State/team/generation validation stays intact; #370, Current, Simulation 2.0, Foundation 4 economics and all unrelated model semantics are unchanged.

### 2026-10-06 — full CI contract callers updated; rerun pending

- **PR / branch / code head:** #396, `work/p0-1-dynasty-publication-request-fence-20261006`; code/test head before this checkpoint `e3adc4cdc79c9383fc435603ca6ab9b5d6c91be2`.
- **Full CI result at prior head:** run `37414005570` failed only five legacy cases in `tests/test_foundation4_career_forward_runtime.py`, all sending the newly publication-bound route no request IDs (3 returned HTTP 422; 2 failed reading error payload). The route correctly requires identity; the tests now provide the matching State/generation, preserving their intended ready/preparing/unavailable assertions. The new captured A/B case is separate and asserts superseded/no coordinator or presentation lookup.
- **Already green at prior head:** Atlas focused `37414005536`, Home focused `37414005564`, PR164 focused `37414005546`, forecast trace `37414005555`. Earlier Atlas cache-key failures were corrected; this run’s Atlas focused suite passed with the refreshed tokens.
- **Next / exact head:** this note advances PR head; re-fetch it. Wait for CI and focused checks to rerun. No merge until all required exact-head checks and fresh Codex review are clean.
- **Scope:** test callsites only; no route/UI changes since the prior successful focus. Keep P0.1 and all safeguards unchanged.

### 2026-10-06 — focused Atlas failures corrected; final-head validation pending

- **PR / branch / exact code head:** PR #396, `work/p0-1-dynasty-publication-request-fence-20261006`; code head before this note `df42c1a7bdaeee47db1bfb994d0210d38e6ecc89`. Documentation update advances it again; refetch before review.
- **First focused result:** League Atlas North Star run `37413856028` failed 5 of 85 tests. Four failures were stale asset fingerprints after changing the Atlas/app bundles (including affected sha-derived assertion values); one static assertion still required the old unparameterized Dynasty URL. This did not identify a route logic failure. Full CI for the then-head was not complete and is not sufficient.
- **Correction:** updated the static contract assertion; updated Atlas cache token to the modified bundle identity and the app/shell cache tokens in `index.html`. Changed assets are now reachable on physical Safari after deployment. The superseded trace fields remain explicitly named; no State B evidence is represented as served under A.
- **Current CI queued:** run `37413969476` CI; League Atlas focused `37413969517`; Home `37413969498`; Franchise `37413969491`; PR164 `37413969485`; forecast trace `37413969541`. Runs refer to code head `df42c1a7bdaeee47db1bfb994d0210d38e6ecc89`, before this doc note.
- **Next:** wait for exact-head reruns after this checkpoint, inspect any failures; when green, fresh exact-head Codex review, merge expected head, deploy resulting main to Render and verify exact live identity. Then stop for final physical Safari acceptance.
- **Safeguards:** the superseded branch returns no rooms and exits before Career coordinator or presentation reads. Existing browser evidence fences remain active. No P0.2, #370 formula, Current, Simulation, or Foundation 4 economics changes.

### 2026-10-06 — telemetry identity refinement; checks rerunning

- **PR / branch:** #396, `work/p0-1-dynasty-publication-request-fence-20261006`; code/test head before this note `a648bbaa20426c0490f6aeca27fcb32d5d4637df`. This note advances the head; fetch exact head again.
- **Material refinement:** on a superseded response, journey telemetry now records `superseding_state_id` and `superseding_publication_generation_id` explicitly. It no longer labels State B as `served_state_id`, since no B evidence was served under A’s request. The existing telemetry whitelist now preserves these names. Browser regression checks the distinction.
- **Files:** route; League Atlas Dynasty loader; app journey telemetry whitelist; `tests/test_dynasty_presentation_handoff.py`; this handoff.
- **Validation:** exact-head Actions must rerun after this change. Original #396 runs at the preceding head are not sufficient for merge.
- **Next:** record exact new head; inspect all changed files, wait for focused and full checks, obtain fresh review at final exact head; merge/deploy only when green. Then stop for final physical Safari acceptance.
- **Safety:** request mismatch exits before coordinator, persistence loader, or room assembly. All prior fences and frozen semantics remain.

### 2026-10-06 — PR #396 opened; exact-head validation running

- **Main / live:** PR base main `408431fd4bb0fb96daf800e7ec036616ba79c12c`; Render is unchanged, live deployment `dep-db26ufh7lnhs73drheqg` on app commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`.
- **Branch / PR / head:** PR #396, `work/p0-1-dynasty-publication-request-fence-20261006`, initial exact PR head `248fd83f7b5356686e7913f2555b8867a1f96b9b`. This note will advance the branch head; re-fetch PR head before review/merge.
- **Validation running at recorded head:** League Atlas focused workflow run `37413730682`; Home focused run `37413730639`; full CI run `37413730702`. All were queued when checked. Focused local command remains `pytest tests/test_dynasty_presentation_handoff.py`; repository mutation/testing is performed through GitHub and Actions.
- **Next:** inspect full PR diff, wait for exact-head checks, fix any concrete failure on this same PR, rerun checks on final head, conduct fresh review, merge only the exact green head, deploy the resulting main commit and verify it live. Then stop for final physical iPhone/Safari acceptance. P0.2 remains held.
- **Unresolved / safeguards:** physical acceptance has failed on the request-contract race. No code has been deployed for this correction. Keep every publication/team fence and all frozen #370/Current/Simulation/Foundation safeguards.

### 2026-10-06 — publication-bound Dynasty request implemented; validation pending

- **Main / live:** base main before pre-implementation checkpoint `c49295a56ce5ac676a271e0e6112af53a7064f36`; checkpoint commit `408431fd4bb0fb96daf800e7ec036616ba79c12c`. Live Render remains service `srv-dae6k7vqj5pc73af7bt0`, deployment `dep-db26ufh7lnhs73drheqg`, application commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`.
- **Branch / PR / head:** `work/p0-1-dynasty-publication-request-fence-20261006`, no PR yet. Code/test head `21b94cffcf10ea560101f311305be0aa43f9ab9c`; this documentation checkpoint will produce the head to open as one PR.
- **Files:** `foundation4_shadow_routes.py` requires the requested Atlas `state_id` and `publication_generation_id`, compares both with the runtime publication before coordinator/presentation reads, and returns explicit `superseded` with requested and superseding identities and no rooms on mismatch. `league_comparison.js` sends both values; on superseded it clears only its in-flight loading state and calls the existing read-first `loadContext()` hook, whose context update invokes existing Atlas promotion. Added regression uses exact captured A/B State IDs and generation A; it asserts the runtime’s coordinator and presentation loader are not consulted. Added static browser contract assertions.
- **Validation:** not run yet; GitHub Actions PR validation required. Focused tests: `pytest tests/test_dynasty_presentation_handoff.py`.
- **Measurements / acceptance:** no new latency, RSS, egress or browser measurements. The 11:54–12:00 ET failed physical journey and #395 telemetry remain the before-change evidence. No claim of hosted acceptance.
- **Unresolved / exact next action:** checkpoint this record, open one PR, run focused and full CI at stable head, obtain fresh exact-head review, merge and deploy the exact approved main commit. Then stop for final physical iPhone/Safari acceptance. P0.2 remains blocked until it passes.
- **Frozen safeguards:** current State/team/generation fence, #370 formula, Current ranks, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, atomic publication, tenant isolation. No model change or persistence refactor.

### 2026-10-06 — #395 physical acceptance failed; request-contract checkpoint

- **Main / live:** main `c49295a56ce5ac676a271e0e6112af53a7064f36`; Render service `srv-dae6k7vqj5pc73af7bt0`, deployment `dep-db26ufh7lnhs73drheqg`, #395 app commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926` live.
- **Journey:** Management’s Safari capture window was 11:54–12:00 ET. Atlas remained on State `3d7808d45587314cafa3e8fb1e694a57158cd16524b2c2a86b9dfb0e5b5176bf` / publication generation `da5a06b340a8ab7868f1876a91500d53b6da67c89338185d7944fa8eace8a8ab`. Live Dynasty telemetry recorded response State `e582e5ce160226c0ab65f88277c12d5dd4b957a97eacc4d70841f6f360f3a21d`; browser outcome was correctly `state_mismatch`.
- **Finding:** browser held exact Atlas identity locally, but Dynasty GET sent neither State nor generation. Server independently resolved mutable runtime via `runtime_store.get(user_id)`, now State B. #395 correctly fenced the old persisted fallback; this new failure is a request-contract race.
- **Change:** none yet. This is the pre-implementation checkpoint. Correction must pass both captured IDs to the route, compare before evidence resolution, and return explicit superseded identities without rooms when publication advanced. Frontend refreshes Product Context once and uses the existing context-update Atlas promotion hook.
- **Validation / measurements:** no new tests or runtime measurements. The physical mismatch is conclusive; P0.2’s 67 MB/repeated-read evidence remains deferred.
- **Unresolved / next:** create the bounded request-fence branch from checkpointed main; add route regression for Atlas A/runtime B and browser regression for IDs plus superseded promotion; validate, fresh review, PR, merge and deploy. Stop for final physical iPhone/Safari acceptance; no P0.2 until it passes.
- **Frozen:** all safeguards from the current checkpoint; no Dynasty formula, Current, Simulation, Foundation 4 economics, or persistence architecture changes.

### 2026-10-06 — PR #395 merged/deployed; physical acceptance gate

- **Merge:** PR #395 merged from exact validated PR head `3baeecb292ea969c46315ff382b01c518f040b949` as main application commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`. Main was verified at this SHA before deploy.
- **Render:** private-beta service `srv-dae6k7vqj5pc73af7bt0`; manual deploy `dep-db26ufh7lnhs73drheqg`; exact deployed commit `3c8c04a5eb6eb225f77b831c1a98d5ac7998e926`; status `live`, finished 2026-10-06 03:48:39Z.
- **Hosted verification:** Render logs show server start and “Application startup complete.” No error-level logs in the sampled startup window. Unauthenticated HEAD / returned 405 and GET / returned 401; these are not physical saved-session acceptance. Startup emitted ordinary customer-journey restore events.
- **Validation:** PR #395 head checks green: full suite 2,175 passed / 1 warning; focused workflow 123 passed; trace workflow passed. The initial unrelated RSS ceiling failure did not reproduce on the full rerun. No application code changed after validated code head; later commit only updates this handoff.
- **Change:** only the Dynasty presentation fallback handoff now enforces active league, State and publication generation; exact team and payload validation remain in the continuity loader. A ready stale last-good from old State is no longer returned as current Dynasty evidence; canonical Career lifecycle supplies current-State preparing/ready response.
- **Measurements:** previous failed physical baseline remains the only customer journey. No new physical requests, latency, RSS or journey telemetry after the corrective deploy yet.
- **Unresolved / stop:** visible current-generation Dynasty ranks have not yet been confirmed on iPhone/Safari. P0.1 remains open. Do not start P0.2.
- **Frozen safeguards:** exact State/team/publication-generation identity, last-good’s truthful stale identity, Current rank semantics, approved #370 formula, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, atomic publication and tenant isolation. The measured 67 MB serialized application reads remain deferred to P0.2.
- **Exact next action:** conduct the saved-session physical acceptance described in Current checkpoint, capture result/local time/timezone, then correlate telemetry by browser journey ID and update this file with pass/fail and exact IDs.
- **Safe handoff:** resume from live main after this documentation-only checkpoint. Do not repeat baseline capture or treat Render live/startup as product acceptance. If acceptance succeeds, checkpoint P0.1 closed before considering P0.2; if it fails, investigate only the newly captured State/team/generation evidence.


### 2026-10-06 — PR #395 exact-head validation complete; merge gate

- **Main / live:** base main is `da045325bd3916d8b1014f49dcacc24a5bbc1141`; live Render remains service `srv-dae6k7vqj5pc73af7bt0`, deploy `dep-db266fe7bikc73cjl5jg`, app commit `5b243b00179deeeeda26c6a06b72bd4abfd38506`.
- **Branch / PR / code head:** PR #395, branch `work/p0-1-dynasty-state-fence-20261006`; validated app/test commit `3a4eb0272ea969c46315ff382b01c518f040b949`. This handoff update is docs-only; fetch exact PR head afterward.
- **Correction:** Dynasty persisted fallback now must match active league, exact current State and current publication generation; continuity’s preexisting exact-team and integrity checks remain in force. A mismatch falls through to canonical Career evidence and returns current-State preparing/current response, never stale rooms presented as current.
- **Files:** `src/fsffl/product/foundation4_shadow_routes.py`; new `tests/test_dynasty_presentation_handoff.py`; updated `tests/test_foundation4_career_forward_runtime.py`; this handoff.
- **Validation:** PR check `test` passed **2,175 tests, 1 warning** in 171.32 s; focused workflow passed 123 tests; forecast trace passed. The new captured State pair regression is collected in the full suite. First full run’s legacy last-good expectation was revised to assert the current-generation fence. The unrelated RSS ceiling test passed on rerun; no resource code changed.
- **Measurements / physical acceptance:** hosted baseline is still the captured failed Safari journey; no new runtime measurement before deployment. No claim of visible Dynasty ranks yet.
- **Review / unresolved:** exact code/test diff reviewed against this PR head; no remaining code finding identified. Need merge, explicit Render deploy (service auto-deploy is disabled), verify live commit/health, then one physical iPhone/Safari saved-session acceptance. P0.1 remains open until ranks visibly render under matching current State/generation and the post-deploy journey is checkpointed.
- **Frozen safeguards:** current ranking semantics; approved #370 Dynasty formula; exact State/team/publication-generation fences; Simulation 2.0/50k/RNG/replay; Foundation 4 economics; atomic publication and verified last-good. P0.2 repeated-read/egress changes remain deferred.
- **Exact next action:** merge PR #395 with expected validated head, trigger deploy of resulting main commit, verify Render live identity, and return for physical Safari acceptance. Do not begin P0.2 before acceptance.
- **Safe takeover:** read this entry, the exact-State trace entry, and PR #395; fetch live main/Render deployment identities. If Safari still fails, correlate a new P0.1 journey and preserve response State/team/generation; do not broaden to P0.2 without closing this customer path.


### 2026-10-06 — PR 395 validation checkpoint

- Main / branch / PR / head: main da045325bd3916d8b1014f49dcacc24a5bbc1141; PR #395 work/p0-1-dynasty-state-fence-20261006; prior head ed7b193e9c4796d7bd79b1a8673c6d49ec81d245. This checkpoint bundles with the regression-contract correction; fetch the resulting branch head.
- Validation at prior head: forecast trace passed; focused subset passed 123 tests but did not include the new regression. Full CI ran 2,175 total: 2,173 passed, with failures in test_dynasty_last_good_keeps_verified_presentation_generation and test_resource_boundary_closure::test_browser_manual_refresh_joins_auto_refresh_and_reaches_usable_core_layers. The Dynasty assertion encoded the prior route behavior of serving an older last-good generation despite a different active publication generation; this conflicts with the current-State/current-generation Dynasty contract. The resource test observed 540,524,544-byte peak RSS against its 536,870,900-byte ceiling; investigation/rerun is pending and no resource code is in scope.
- Correction: renamed/revised the old Dynasty test to assert that a stale generation is rejected and canonical current-State evidence is requested. The captured ee05aa91… vs 3d7808d4… route regression remains in place and passed within the prior full suite.
- Files: route, new captured-mismatch route test, existing Dynasty route test, and this handoff.
- Measurements: hosted physical baseline unchanged; no deploy/new runtime measurement.
- Unresolved / exact next action: run both Dynasty route regressions and rerun full CI. If only the resource-boundary RSS test remains failing, check whether the same limit fails on clean repeated runs and record any unrelated baseline issue without expanding this PR. No merge/deploy until required validation is green.
- Safeguards: all P0.1 frozen boundaries remain; no P0.2 or broader resource changes.
- Safe takeover: start from the new exact PR head, read this validation note and the failure log for CI run 37409527843; preserve the distinction between outdated Dynasty expectation and observed RSS failure.


### 2026-10-06 — P0.1 narrow route correction implemented; validation pending

- **Main / live:** main remains `da045325bd3916d8b1014f49dcacc24a5bbc1141`; Render remains deploy `dep-db266fe7bikc73cjl5jg`, app commit `5b243b00179deeeeda26c6a06b72bd4abfd38506` (live).
- **Branch / PR / head:** `work/p0-1-dynasty-state-fence-20261006`; no PR yet. Application and regression-test head before this documentation checkpoint: `acb180c3c7dfb0f8abcc62475ff760c6e8029cce`; this update is docs-only, fetch branch for exact resulting head.
- **Finding / change:** confirmed the route’s persisted fallback passed any ready response with a generation ID, even when its State was the verified older last-good State. It now returns that fallback only when league ID, State ID and publication generation exactly equal the active runtime publication. Existing continuity loader continues to enforce selected team and promotion/payload integrity. On mismatch the route falls through to canonical Career evidence and returns preparing/current State rather than serving stale rooms. Browser fences and last-good labeling remain unchanged.
- **Files:** `src/fsffl/product/foundation4_shadow_routes.py`; new `tests/test_dynasty_presentation_handoff.py` with the captured State pair and target generation.
- **Focused regression:** constructed a ready stale fallback from captured State `3d7808d4…` while active context targets `ee05aa91…`; asserts the stale rooms are rejected and response is preparing under the active State/current generation. **Not yet run.**
- **Measurements:** unchanged baseline as recorded in physical-run entry; no new hosted measurement.
- **Unresolved / gate:** code and regression are committed but need focused test/CI, fresh review, merge/deploy, hosted verification, and one physical iPhone/Safari saved-session acceptance. P0.1 is not closed; do not begin P0.2.
- **Safeguards:** exact State/team/publication-generation fences; approved #370 metric; Current semantics; Simulation 2.0/50k/RNG/replay; Foundation 4 economics; atomic publication and verified last-good remain frozen.
- **Exact next action:** open PR from this branch, run focused regression and required CI; inspect exact head/review before merge.
- **Safe takeover:** fetch the branch’s current SHA, read this entry and the physical journey evidence above. Do not modify P0.2 persistence reads or weaken last-good/freshness identity.


### 2026-10-06 — P0.1 exact-State handoff corrective started

- **Current main:** `da045325bd3916d8b1014f49dcacc24a5bbc1141`. **Live Render:** service `srv-dae6k7vqj5pc73af7bt0`, deploy `dep-db266fe7bikc73cjl5jg`, app commit `5b243b00179deeeeda26c6a06b72bd4abfd38506` (live).
- **Branch / PR / head:** `work/p0-1-dynasty-state-fence-20261006`, created from the exact main SHA above; no PR yet; branch currently points at base SHA `da045325bd3916d8b1014f49dcacc24a5bbc1141`.
- **Finding before change:** the Dynasty route accepts persisted data when only `status == ready` and a publication generation ID is present. Its continuity loader can return a verified same-team/same-league last-good surface whose served State is older than the active State. The route returns that payload without checking its served State against `context.league_state.state_id` or its generation against the current published generation. This is the precise server handoff that allows a legitimate last-good surface from `3d7808d4…` to reach a browser targeting `ee05aa91…`; the browser correctly rejects it. The simultaneous matching last-good telemetry event is a separate request and does not alter this diagnosis.
- **Scope:** add an exact-current State + publication-generation acceptance guard at this Dynasty-only handoff, relying on the continuity loader’s existing league/team integrity checks; if fallback fails the guard, continue to canonical Career lifecycle, which returns preparing/current or current-State evidence. Add a focused regression using the captured State and generation identifiers. No changes to the browser fence, stale evidence identity, Current semantics, Dynasty formula, or persistence architecture.
- **Baseline / measurements:** physical evidence remains as recorded below: target State `ee05aa91…`, stale served State `3d7808d4…`, target generation `94543b58…`; three Dynasty GETs (39,999.95 / 23,501.25 / 5,619.5 ms); 13 readiness polls; 30,000 ms retry wait; no visible Dynasty ranks. No new runtime measurement yet.
- **Validation / unresolved:** implementation and focused route regression are not yet complete; no tests run; P0.1 remains open pending merge/deploy and one physical saved-session acceptance.
- **Frozen safeguards:** preserve exact State/team/publication-generation fences, Current rank semantics, approved #370 metric, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, atomic publication and verified last-good. P0.2’s repeated-read/67 MB work remains deferred.
- **Exact next action:** implement only the Dynasty route fallback guard and a route-level regression for the captured mismatch; run its focused test and CI before PR.
- **Safe takeover:** read this corrective entry and the physical-run entry below, then inspect the exact branch SHA. Do not repeat baseline collection, weaken the browser fence, relabel last-good as current, or start P0.2.


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


### 2026-10-06 — P0.1 implementation and validation complete; hosted journey pending

- **Code/test head validated:** `d2cc376c97e6a7f9ae2bfb5d944f13ef26060a4a` on PR #394, branch `work/p0-1-baseline-20261006`, based on main `0ef839ef9edeae7dad85fb6e52984c2998699e2a`.
- **Validation at that head:** League Atlas North Star focused workflow #1046 passed, including JavaScript syntax, telemetry regression tests, Atlas tests, composition sanity and final-acceptance provider authority audit; Home North Star #946 passed; standard CI #4691 passed **2,174 tests** (one warning); Franchise #503, PR164 #1355, live diagnostics #795, and forecast trace #1370 passed.
- **Final corrections covered:** modified `app.js` delivery identity is fingerprinted; browser retry/retry-wait/alignment summaries retain State + publication generation identity; API path identifiers are redacted; correlated request logs include Render current and peak RSS; startup restore and Postgres call/row/application-payload JSON byte measurements are correlated with browser journey IDs.
- **Post-validation handoff:** this entry is a documentation-only checkpoint after validated code head `d2cc376…`; fetch the resulting current branch/PR head before takeover. No source/test/workflow files change in this checkpoint. The accepted P0.1 instrumentation remains unmerged and undeployed.
- **Measurements:** production still has only the pre-change baseline above. Post-change restore/State/manifest/payload/foreground/retry/poll/handoff/RSS values require the hosted iPhone/Safari run. Actual Supabase wire bytes are not available from this adapter; payload JSON bytes are measured application serialization size. Safari heap may be unsupported.
- **Unresolved customer evidence:** actual live Dynasty failure stage and first visible current-generation ranks remain unknown. Tests preserve generation mismatch as failure and require exact current State/generation for first-useful-render success.
- **Safeguards held:** Current semantics, approved #370 metric, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, exact State/team/publication fences, atomic publication, verified last-good and tenant isolation. No P0.2 or feature expansion.
- **Exact next action:** Management to merge/deploy PR #394 through hosted process, then run the saved-session iPhone/Safari journey once. Correlate Render logs via `journey_id` + `restore_id`, collect State/manifest/payload counts and serialized bytes, foreground latency, actual browser retry/poll/handoff counts, exact publication identity, and per-request RSS; compare first visible Dynasty render against the preserved mismatch fixture.
- **Safe handoff:** read the P0 directive, this workstream, Issue #393 and PR #394. Continue from PR branch’s current exact head. Do not repeat broad audit/baseline, reopen frozen semantics, or begin P0.2 before post-deployment P0.1 evidence is recorded.


### 2026-10-06 — P0.1 merged and deployed; physical acceptance gate

- **Main/application commit:** PR #394 merged from exact head `34bc4f267283e8c35dac9f5457e6ec4713b96475` as merge commit `5b243b00179deeeeda26c6a06b72bd4abfd38506`.
- **Branch / PR:** PR #394 merged; its source branch was `work/p0-1-baseline-20261006`. No open implementation PR remains for P0.1.
- **Render:** auto-deploy is disabled for the Virginia Free service. Manually triggered deployment `dep-db266fe7bikc73cjl5jg` on service `srv-dae6k7vqj5pc73af7bt0`; exact commit `5b243b00179deeeeda26c6a06b72bd4abfd38506`; build and deploy succeeded; status live at 2026-10-06 02:57:25Z.
- **Hosted verification:** Render startup log reports `Application startup complete`, then emits `FSFFL_CUSTOMER_JOURNEY` restore/persistence events. Sample cold restore ID `0b1eaf56-a172-47d7-ac0c-3fd120f7cead`: runtime context read 1 call; State snapshot read 1 row / 547,185 serialized JSON bytes; published-intelligence-generation metadata read 1 call / 1,060 serialized JSON bytes; durable-context restore ready in 8,599.91 ms. This verifies the server instrumentation on the live instance; it does not satisfy the physical customer journey.
- **Validation:** latest pre-merge PR head CI #4694, Atlas #1049, Home #949, Franchise #506, PR164 #1358, diagnostics #798, and forecast trace #1373 all passed. Full suite passed at the validated application code head. The only commits after code validation updated the handoff.
- **Changes in this checkpoint:** exact deployment identity, startup-event proof, physical acceptance procedure, and the stop/P0.2 gate recorded here. No app code, settings, data, or semantics changed after deployment.
- **Measurements still missing:** authenticated saved-session browser journey correlation, Product Context-to-Atlas completion, customer State/manifest/payload reads, foreground latency, publication identity as observed by Safari, visible current-generation Dynasty ranks or exact failure stage, browser retry/poll/handoff counts, and physical Safari memory availability. Do not infer these from the Render startup probe.
- **Frozen safeguards:** Current semantics, approved #370 Dynasty metric, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, exact State/team/publication-generation fences, atomic publication, verified last-good, and tenant isolation. No P0.2 or feature expansion.
- **Exact next action:** Management’s physical iPhone/Safari acceptance using the steps in Current checkpoint; return its recording, local time/timezone, selected league/team and observed result, then correlate Render journey events and checkpoint P0.1. Stop here until that evidence is available.
- **Safe handoff:** read the governing P0 directive, this file’s Current checkpoint, Issue #393, and PR #394. Resume from live main after this documentation commit. Do not redo the baseline, alter the approved formula or frozen safeguards, or begin P0.2.


### 2026-10-06 — Physical iPhone/Safari journey captured; P0.1 failure checkpoint

- **Physical evidence:** Management-provided IMG_0175–IMG_0181 show a saved Safari session in FSFFL Dynasty, local status-bar times 11:01–11:13. Based on the contemporaneous Render logs this corresponds to approximately Oct 5 11:01–11:13 p.m. EDT / Oct 6 03:00:55–03:13:28Z; screenshots did not include exact capture seconds or an explicit timezone.
- **Current lens:** IMG_0176 shows populated Current position ranks. Current ranking semantics remained visible and were not changed by P0.1.
- **Dynasty lens:** IMG_0177 and IMG_0181 show Dynasty selected with roster-count breadth text and “Loading Dynasty room values”; no Dynasty ranks are visible. IMG_0181 also shows global “Intelligence current.” IMG_0178–IMG_0180 show intelligence rebuilding/last-good; IMG_0180 shows 6/7 with Forecast, Simulation and Current Value unavailable and Intrinsic Full.
- **Journey correlation:** opaque browser journey ID `a4e54323-b003-45ef-84ac-6cd50dea55c9`; Render logs on the live #394 deploy cover 03:00:55Z–03:13:28Z. Product Context had five HTTP-200 completions at 5.8, 8.9, 21.0, 16.2, and 16.2 seconds (median 16.2 seconds). Browser Product Context restore-ready event reported 5,950 ms. The trace recorded 13 shared-readiness polls and a 30,000 ms retry wait; journey_end outcome was failure after 483,081 ms. Safari `performance.memory` was unsupported.
- **Dynasty route:** three same-journey GET requests to `/api/league/dynasty-position-rooms` completed HTTP 200 in 39,999.95, 23,501.25, and 5,619.5 ms. The highest request-time RSS sample was 428,916,736 bytes. HTTP 200 did not establish current-generation Dynasty evidence.
- **Exact mismatch regression:** browser target State prefix `ee05aa91`; target publication generation prefix `94543b58`. One logged Dynasty response was rejected with `dynasty_state_mismatch` / `dynasty_request_failed outcome=state_mismatch` because its served State prefix was `3d7808d4`. The same telemetry flush also contains a `dynasty_evidence_loaded outcome=last-good` event whose top-level served State matches the target. Preserve both events as evidence of the observed request window; the trace does not prove they came from the same response. The visible table never showed Dynasty ranks in the provided captures.
- **Journey read totals:** 124 correlated API request-start/completion pairs and 158 persistence-read log events. Artifact-kind totals: `preseason_forecast_baseline` 48 calls / 46,600,704 bytes; `runtime_presentation_manifest` 45 / 77,265 bytes; `runtime_presentation_surface` 63 / 19,652,197 bytes; `player_future_forecast_continuity` 1 / 744,044 bytes; `get_sync_cursor` 1 / 0 bytes. Aggregate returned JSON bytes: 67,074,210 (about 67.1 MB application serialization; not Supabase wire egress). Repeated reads are measured evidence, not a P0.1 fix.
- **Counter discrepancy:** the flushed browser Dynasty summary reports `request_count=2`, whereas three Dynasty endpoint requests appear in the full Render window; the third request begins after the first failure/telemetry flush. Keep the full server count and client aggregate distinct; the session continued after the recorded failure.
- **Changes in this checkpoint:** handoff documentation only, with redacted State/generation prefixes and the saved screenshots’ filenames. No production code, data or configuration changed.
- **Disposition:** P0.1’s measurement objective is met: hosted instrumentation ran, one saved-session journey was correlated, and the unresolved Dynasty failure is now an observed regression with State/generation evidence. Physical product acceptance **failed** because Dynasty ranks did not appear. Do not claim a successful Dynasty journey.
- **Next action / stop:** wait for Management disposition on a bounded corrective to the observed Dynasty failure. Do not start P0.2 or reopen #370, Simulation 2.0, Foundation 4 economics, Current semantics, or exact-generation safeguards.
- **Safe handoff:** resume from main after this documentation-only checkpoint. Read this entry and Current checkpoint first; query live Render logs by journey ID above. Do not repeat the physical run baseline or treat the successful HTTP status as proof of correct State/generation.



### 2026-10-06 — PR #396 deployed; awaiting final physical acceptance

- **Main/deploy commit:** `d7cbbb5820a03de8309165752e124ecd0dce30fe`.
- **PR #396:** merged as `d42593ed73aed4ca1fe62338273df9fa61947fed`, from reviewed exact head `a88f7c0349f855f49ad0a149ca2b089b5eb95dc4` on `work/p0-1-dynasty-publication-request-fence-20261006`.
- **Render:** deployment `dep-db28eoks728c73bgnu00` is live on service `srv-dae6k7vqj5pc73af7bt0`, exact commit above. Auto-deploy remains disabled.
- **Hosted check:** startup completed and customer-journey restore/persistence instrumentation emitted on the new instance. No authenticated Dynasty route was tested and no product acceptance is inferred from startup.
- **Validation:** exact PR-head checks are green (full CI `37415031517` plus focused workflows `37415031461`, `37415031670`, `37415031454`, `37415031538`, `37415031491`, `37415031448`); fresh exact-head review found no major issues.
- **Unresolved:** one final physical iPhone/Safari saved-session acceptance. No new egress/latency/memory baseline; startup restore was 7,598 ms. A FUMBLES_LOST cutoff-mismatch warning appeared during startup and is outside this P0.1 correction.
- **Next:** Management runs same-league/team saved-session journey and captures Dynasty ranks plus local time/timezone. If it passes, close P0.1 and immediately begin P0.2 metadata-first persistence/egress in approved sequence. If it fails, correlate journey telemetry and fix only the proven P0.1 blocker.
- **Safeguards:** approved #370 metric, Current semantics, Simulation 2.0/50k/RNG/replay, Foundation 4 economics, exact State/team/generation fences, atomic publication, last-good, tenant isolation; no P0.2 before acceptance.


### 2026-10-06 — 07:12 ET saved-session journey; P0.1 measurement complete (failure preserved)

- **Evidence source:** Management physical Safari outcome plus Render log correlation; journey ID `3a5f455b-fde9-4daf-9c6a-585cb2d7b0a4`.
- **Result:** no Dynasty position ranks visibly rendered. P0.1 measurement/instrumentation is complete; physical acceptance remains a required end-to-end test for the plumbing redesign, not a reason to perfect the obsolete handoff first.
- **Request-contract proof:** Atlas log says served State `606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3`. Dynasty URL sent exactly that State plus generation `58d3d6edb95d30e52159b58df8fa5a269f7637158dbc1487fde252f8486bbc23`; HTTP 200, 5,401 ms. The trace therefore does not reproduce #395’s omitted-request-identity defect. HTTP status alone does not prove the semantic payload is ready/current; body outcome was not logged.
- **Latency/resource:** durable restore 7,939 ms; Product Context 8,095 ms and 12,153 ms; Atlas 2,039 ms; Dynasty 5,401 ms. Journey peak RSS 365,068,288 bytes; RSS after Dynasty 356,597,760 bytes.
- **Repeated work:** duplicate manifest/presentation reads were observed. Browser diagnostic submission ended 401 after 136.3 s; use server-side logs for this run.
- **Disposition:** classify remaining failure as B: duplicated publication/read resolution, per-surface generation/readiness negotiation and promotion lifecycle targeted in P0.4/P0.5. Preserve exact identity validation as A/frozen invariant. No application code changed for this physical failure.
- **Next:** proceed to P0.2 metadata-first persistence/egress; do not reorder or skip P0.3, P0.4, or P0.5. The mandatory acceptance test is: restore saved Safari session, open same league/team, verify Dynasty Position & Depth ranks appear, and verify response State + publication generation exactly equal the visible Atlas identity with no conflicting stale-generation presentation.
- **Frozen:** approved Dynasty metric, Current, Career Intrinsic, Foundation 4 economics, Simulation 2.0/50k/RNG/replay, exact State/team/generation fences, atomic publication, last-good and tenant boundaries remain unchanged.
