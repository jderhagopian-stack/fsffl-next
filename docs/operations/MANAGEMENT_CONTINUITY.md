# FSFFL NEXT — Management Continuity

## 2026-10-10 — Scalable computation foundation decision

The bounded execution and reuse contract is now captured in [Scalable Computation Foundation](workstreams/SCALABLE_COMPUTATION_FOUNDATION.md). Safe shared work is keyed by provider evidence, historical/model identity, canonical player forecast inputs, and scoring-rule/horizon cohorts; immutable league State/Simulation and bilateral team Decisions remain isolated. Existing fingerprint and publication authorities stay in place. Immediate weakness: the in-process `IntelligenceJobCoordinator` has an unbounded pending executor queue and process-local locks; do not build additional high-fan-out callers on it until bounded admission/backpressure and an injected execution contract are implemented and tested. Cross-process durable queue and independent worker are deferred until measured demand. No code, tests, migration, deployment, infrastructure purchase, #405 checkpoint change, or #443 change in this documentation-only tranche. Supabase Pro is active.

## 2026-10-10 — Supabase Pro plan confirmed by connected account

Management reports the Supabase Pro upgrade is complete. Connected Supabase organization verification confirms `Jimmy’s Lab` on `pro` / `tier_pro`, with FSFFL NEXT project `gldxkbqcprzuffgmamxl` reporting `ACTIVE_HEALTHY`. Supabase Free-tier database overage is no longer an immediate Free-plan operational blocker; **do not use the old 512 MiB allocation to justify urgent storage migration or infrastructure spending**. Retain disciplined storage growth/retention economics, PR #443 strict production NO-GO and independently approved real PostgreSQL/Supabase write-safety validation. No additional billing/compute changes, schema migrations, production deployment or deletion are authorized by this confirmation. Product-led Career → Explore → Trade sequence remains unchanged.


## 2026-10-10 — Management decision: product-led strategic reset and commercial execution boundaries

**Decision:** Management accepts the program-wide strategic assessment. FSFFL NEXT's differentiated State, Forecast, Value, Decision, Simulation 2.0, Career, PIT/replay, atomic publication, last-good and tenant-isolation contracts remain authoritative. No wholesale rewrite or new research program. Design interfaces for **100,000 leagues** without premature infrastructure purchases or deployment.

**Product is the lead lane.** Continue Career Coverage #405 at its exact current accepted checkpoint, including complete roster/waiver subject coverage, preserved 335-player parity reference, governed season rollover and reuse of unchanged evidence. Then deliver bounded Explore discovery quality (credible, diversified, cheap-first opportunities) and Trade Center usefulness (specific bilateral consequences and targeted deep analysis). Verify each product slice through an authenticated iPhone/Safari owner task and real user-perceived latency. Preserve the later Owner Intelligence, historical grading, What-If, league history and publication roadmap.

**One short architecture/interface contract, not a blocking audit.** Classify computation by widest mathematically and privacy-safe reuse scope: provider/season/week evidence; shared model fit; rules-signature player outputs; exact league State/scenario simulations; team/user-specific decisions and presentation. Identify existing seams, semantic dependency fingerprints, single-flight/coalescing, tenant fences, durable/idempotent job ownership, backpressure and eventual multiple worker/application instances. Specify KEEP / CHANGE NOW / CHANGE LATER, with CHANGE NOW restricted to an actual lock-in affecting #405 or next product work. No immediate distributed queue, broad lifecycle rewrite, schema migration or new infrastructure. Architecture work must not delay unaffected Career work.

**Infrastructure remains a supporting lane.** Preserve PR #443's offline write-safety proof and strict production NO-GO. Complete only a separately approved narrow real Supabase/PostgreSQL safety gate before any storage migration. Observe naturally occurring PR #442 provider request/byte telemetry before proposing cohort reuse. PostgreSQL Free allocation overage remains an immediate independent operational risk; any upgrade, deletion or migration requires Management approval.

**Execution governance:** one primary product implementation lane and at most one narrow enabling/support lane. Existing workers checkpoint exact authorized work rather than restart. Every change must provide an owner-visible improvement or remove a measured correctness, reliability, cost or future scale lock-in. Avoid redundant full-suite testing when contracts are unchanged; retain focused correctness and required acceptance gates. Report weekly: shipped owner outcome, real latency/cost evidence, active blocker, and one next decision. Near-term proof: multiple leagues and stable restores, followed by proportionate 100-/1,000-league measurement; 10k/100k/1m remain modeled scenarios until evidenced. This is a 30-day management direction, not a fixed feature-delivery deadline.

**First Management action:** issue the bounded computation/reuse and job-identity contract to an architecture worker, while Career #405 continues unaffected; then route Explore/Trade work. See [Living Product Priorities](../FSFFL_NEXT_PRODUCT_PRIORITIES.md) for the active product sequence.


Updated: 2026-10-09  
Authority: canonical durable record of Management direction, sequencing, deferred work, and roadmap changes across Management chats.

This document answers **where Management is going and why**.  
For **what is happening right now**, read [CURRENT_OPERATIONS.md](CURRENT_OPERATIONS.md).  
For exact tranche implementation evidence, read the linked workstream checkpoint.  
For the broad long-range capability plan, read [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) and [../FSFFL_NEXT_PRODUCT_PRIORITIES.md](../FSFFL_NEXT_PRODUCT_PRIORITIES.md).

## 2026-10-10 — commercial scale design point raised to 100k leagues

Management's intended success scale is thousands through hundreds of thousands of leagues, with **100,000 as the primary long-term design point** and 1,000,000 as an upper-bound sensitivity. The [100k-league scalability plan](SCALABILITY_PLANNING_100K.md) replaces the former 100-league illustration with explicit workload, retention, PG/object capacity, bandwidth and cost assumptions at 1k/10k/100k/1m. The model distinguishes the two measured real artifacts and offline PR #443 tests from extrapolation. A credible path exists only if publication identity, tenant routing, immutable create-only writes, one authoritative DB publication/CAS boundary, job idempotency/backpressure and retention promises are fixed into interfaces now. Large tier purchases, replicas, shard count, and migration/reclamation wait for measured demand. This is a planning correction only; PR #443 stays open/draft and tested, with no implementation scope change, spend, production change, or data migration.

## 2026-10-10 — write-safety correction prototype: PASS / production NO-GO

The contract review found a documented Supabase-native create-only path: Standard Storage Upload with upsert=false. Supabase documents that concurrent uploads to one path are first-completer-wins and losing writers receive “Asset Already Exists”; its current storage source stages a distinct upload version then serializes object-row completion. This is separate from the S3 conditional PutObject route, which remains NO-GO. See [Standard Upload concurrency](https://supabase.com/docs/guides/storage/uploads/standard-uploads#concurrency) and the draft prototype [PR #443](https://github.com/jderhagopian-stack/fsffl-next/pull/443), based on this documentation checkpoint.

**Offline prototype result:** PR #443 adds tenant-namespaced SHA-256-addressed zlib objects, create-only collision verification, first-writer metadata registration, complete manifest generation, transactional compare-and-swap publication, State/PIT/tenant fences, hash-checked reads and last-good fallback. Its SQLite transaction and API model are local stand-ins. **12 focused tests pass** locally; GitHub focused CI is running. No live Supabase call, credentials, schema change, deployment, migration, or production wiring. Status is **PROTOTYPE PASS / PRODUCTION NO-GO** pending provider, PostgreSQL, reader, security, rollback and migration acceptance.

**Capacity estimate (not guaranteed physical recovery):** existing Forecast + Simulation families contain **90,548,515 B** of JSONB datum across 692 rows inside a **407,797,760 B** derived_artifact physical relation and **604,040,339 B** database. Applying only the measured 0.533/0.570 object ratios estimates ~**49.3 MB object bytes**, ~**87.8–89.9 MB logical PostgreSQL reduction** after an explicitly estimated 1–4 KiB/object metadata allowance. At the standing 12-publications/month scenario, 100 leagues project ~**3.63 GB/year** of those PostgreSQL payload datums moved, ~**1.98 GB/year** of object payload, and ~**1.53–1.62 GB/year** less combined bytes before egress/retention effects. These are modeled values, not measured future bills or database shrink. To return allocated PostgreSQL disk space, a separately authorized relation rewrite/repack/table swap is needed; DELETE/VACUUM alone is not a shrink guarantee. Current database size already exceeds the 500 MB Free allowance, so temporary rewrite headroom is unresolved.

## 2026-10-10 — real Forecast/Simulation storage validation accepted; S3 write gate NO-GO

Management accepts the real nonproduction comparison executed by the isolated Render Workflow on PR #441 head `c3bf666a5251ff9748abb2c3d4ddf1b8372e0b23`. Run `trn-0b14gdb4nmaa396pc73ec6sng` ended NO-GO after 12.1 seconds (8.1 CPU seconds; $0.0004815 recorded task cost), solely because the immutable conditional `PutObject` gate failed. Compression and reconstruction evidence justify bounded storage development; they do not authorize production use.

| Artifact | PostgreSQL JSONB datum | Canonical bytes | zlib object bytes | Compression ratio | S3 GET + rebuild p50/p95 | PG get + decode p50/p95 |
|---|---:|---:|---:|---:|---:|---:|
| Forecast | 161,373 B | 3,073,225 B | 86,020 B | 0.533 (46.7% smaller) | 232.39 / 349.86 ms | 178.46 / 354.17 ms |
| Simulation | 118,887 B | 689,400 B | 67,816 B | 0.570 (43.0% smaller) | 96.04 / 135.78 ms | 36.24 / 136.97 ms |

Each latency used 9 samples. Both records passed exact reconstruction, record/hash and deployed-decoder parity, restart and corruption checks. Process peak RSS was 327,585,792 B (312.5 MiB), 101,910,928 B below the 429,496,720 B working budget. The final conditional immutable-write probe failed; its sanitized exception does not reveal whether the condition was rejected, ignored, or failed for another reason. Supabase's S3 compatibility matrix lists conditional operations for `HeadObject`/`GetObject`, not `PutObject`: https://supabase.com/docs/guides/storage/s3/compatibility.

Cleanup evidence: the task log recorded zero test objects remaining; the Supabase Dashboard key list was independently observed empty after revocation; and the Workflow environment was independently checked with only `PYTHON_VERSION` after secret removal. Management confirms later Workflow deletion in the Dashboard; the deletion itself was not independently reverified. The test bucket was not reported deleted. No production app, database rows, or deployment were changed.

**Status: accepted validation / tested S3 conditional-write implementation NO-GO.** Preserve strict immutability. Next authorized tranche: establish a documented atomic create-without-overwrite path, content-addressed identity/hash verification, and one authoritative database transaction for immutable registration plus publication, with concurrency/failure tests. Continue to preserve State, manifest, PIT, last-good, replay and tenant isolation. No Workflow, credentials, experiment rerun, production change, migration or purchase is authorized.

## 2026-10-09 — Provider acquisition PR #442 LIVE: bounded Render verification / natural-traffic gate still OPEN

**Management authorization used:** Operator explicitly confirmed Render workspace `My Workspace` (`tea-dae6if9t0dsc73918us0`) solely for existing FSFFL NEXT deployment and read-only natural-traffic verification, with no new paid services, infrastructure changes, credentials, or artificial refreshes. Render verified existing one-instance `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`) on `0.5c-512mb` Starter Virginia, `autoDeploy=no`, serving earlier commit `26be30ccf9f6a3e184fe221456cb316451d60f2b`. GitHub comparison confirmed all five commits after accepted squash merge `db643f3368a0ccc21bd01dd616b16e066acf2741` only changed operations documentation. A single existing-service API deploy without cache reset, env/plan changes or a new service pulled main `2f89e83edbfbf31f72157735ced5fff4b0c4de5c`.

**Live evidence:** Render deploy `dep-db4n3tvlk1mc73d80q4g` created 2026-10-09 23:00:07 UTC, build succeeded, status `live` by 23:01:28.744 UTC; Render `deploy_ended` reports `succeeded`. Uvicorn started, startup restored existing durable intelligence, Forecast/Simulation/Value all ready and overall product `full`. Internal readiness logging: process RSS **331,960,320 B**, recorded peak RSS **351,354,880 B**, governed budget **429,496,720 B** (peak below budget). One full preseason-baseline read (`get_reusable_artifact`, previously accepted logged logical JSON payload **970,848 B**) plus cheap metadata-only reads were visible; this does not establish provider or billed network transfer. Render system memory sampled before deploy ~**290,426,880 B** idle, new instance **297,549,820 B** at 23:03 UTC; distinct instances/phase and coarse 60-second sampling, **not** a causal apples-to-apples overhead comparison. `instance_count=1` after rollout; no `server_failed` event or error-level logs in queried post-deploy startup window. A graceful server shutdown log during rollout is not a verified failure.

**Important bounded-result limitation:** Read-only Render log search after new startup found **0** `FSFFL_PROVIDER_ACQUISITION` aggregate entries and **0** error-level entries. No operator/artificial heavyweight refresh, scheduled provider experiment, or private storage test was performed. This observation is **not** a finding that providers used 0 requests or 0 bytes; it means **no measured provider acquisition occurred** in that window. Actual outbound provider HTTP counts, body bytes/family, source revision/freshness, repeated-cache opportunities, request p50/p95, and workload CPU/RSS overhead remain **NOT EVALUABLE** until a legitimately occurring acquisition event appears. Do not claim instrumentation has already saved traffic or that production acquisition equivalence is statistically established by a quiet restore. The code-level gate remains exact-head stable full suite **2,262 passed / 1 warning** and focused **84 passed**.

**Next narrow action (no new implementation permission):** Observe the next naturally occurring Sleeper probe/connect/current ROS/weekly/season provider acquisition via existing Render logs filtered by `FSFFL_PROVIDER_ACQUISITION`. Quantify event cause, provider, endpoint family, season/horizon/week, response-body bytes and unknown-byte counts, retries/failures, source freshness, and cohort/revision identities; compare against existing state/no-silent-refresh and app performance. Do not force provider traffic. Only after real duplicate acquisition is proven at safe shared semantic scope propose the smallest separate optimization; **no reuse, retention, frequency, schema or storage change is authorized yet**. Keep PR #441's independent private storage validation and PR #439 draft entirely separate. **Status: #442 LIVE / NATURAL PROVIDER MEASUREMENT GATE OPEN.**

## 2026-10-09 — Provider acquisition instrumentation MERGED / HOSTED VERIFICATION PENDING

Management accepted the Oct 9 physical-capacity/observation-representation diagnosis and specifically authorized the **EVENT / REQUEST / BYTES** instrumentation tranche, **not** provider cohort reuse, retention/deduplication, refresh-frequency edits, new telemetry storage or hybrid migration. Tranches A/B and #440 accepted/live; C whole-publication skip closed; provider commercial strategy develop/validate now, agreements later.

Execution began from main `234d7f510da0a4ad953e32ea5617b73d70d5dac1` on separate branch `impl/provider-acquisition-event-request-bytes-20261009`. [Merged PR #442](https://github.com/jderhagopian-stack/fsffl-next/pull/442) adds existing-provider HTTP getter raw-body counting and per-acquisition safe aggregate logging (including status class, provider/season/horizon/week, cohort digest, source freshness/content digest, errors/retries/latency, and demonstrated zero-HTTP connect/state reuse), with explicit Sleeper worker-context propagation, cause annotations when provable, and opt-out environment toggle `FSFFL_PROVIDER_ACQUISITION_TELEMETRY=0`. It makes no intentional provider calls/policy/Forecast/State/PIT/retention/storage/publication changes. The background refresh POST cannot reliably distinguish manual vs automatic browser intent, so it emits `unknown` rather than a false classification; this must be recorded as a measurement limitation.

Focused tests are included in draft CI. Stable-head full-suite gate, merge/deploy SHA, natural hosted event counts/response-body bytes/p95/RSS and acceptance remain PENDING, not assumed. No artificial heavy refresh authorized for verification. [PR #441](https://github.com/jderhagopian-stack/fsffl-next/pull/441) independent real-storage validation and draft PR #439 untouched. Render connector exposes one workspace (`My Workspace`) but requires operator confirmation before connected service read/deploy actions; do not assert verified new live Render metrics until authorized.

**Code-level gate completed:** final PR #442 head `69c07cfc965b94b4cd6dc2cd4ed7ed7338c61d1a` passed focused CI run `38001309606` (**84 tests**) and exact-head Stable full suite `38001394687` (**2,262 passed, 1 unrelated warning; before/after head checks passed**). Squash-merged into main as `db643f3368a0ccc21bd01dd616b16e066acf2741`. **NOT DEPLOYED. No real hosted EVENT/REQUEST/BYTES measurements or production performance acceptance**: the Render connector requires explicit user choice of workspace `My Workspace`, even though it is the only listed workspace. No artificial refresh was run by the worker in hosted production. Next authorize workspace selection, verify live production service and exact SHA, then deploy and collect bounded natural telemetry. No provider optimization or storage changes yet. No claim of provider or Supabase billed egress savings from instrumentation itself. Canonical details in [Supabase Capacity workstream](workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md).

## 2026-10-09 — Tranche 1 EXACT BASELINE READ REUSE / PRODUCTION ACCEPTANCE — COMPLETE

**Authority:** Management's authorized exact-authority preseason-baseline reuse ONLY; first checkpointed on main before implementation. Implemented through existing Forecast owner (`src/fsffl/product/forecast_resilience.py`) in [PR #440](https://github.com/jderhagopian-stack/fsffl-next/pull/440) at exact tested head `b7d0cb56e1601cfb3864de42470ce8102383be39`, merged as `31e68b0f4c48d5094353290f9c1ff8c1808d1452`. Exact merge live via Render deploy `dep-db4hs7vavr4c73f9pal0` on one-worker `fsffl-next-private-beta` (autoDeploy OFF, triggered explicitly). A+B unchanged, C whole-publication skip CLOSED. No provider acquisition or heavy Refresh Intelligence initiated as a test; no schema/data, billing, model, source, refresh-policy, lineage, presentation or publication changes.

**Mechanism:** Bounded in-memory short-lived decoded `PreseasonForecastBaseline` read-through; at most **4 entries**, each expires **150 seconds** after load (no timer/background process). Every call queries *only metadata* from the authoritative persistence adapter and verifies exact store, LeagueState ID, league/season scope, artifact-kind/model/fingerprint and computation time. One cold `get_reusable_artifact` fetch per exact active identity under lock; contemporaneous metadata/row disagreement uses original `get_latest_reusable_artifact` fallback and never serves ambiguous cached content. Immutable raw baseline only is reused; Forecast rescores for CURRENT LeagueState each time, including FUMBLES_LOST semantics. Legacy stores without metadata methods retain original full read. No unbounded process cache or cross-process persistence; tenant-private State and store instance are identity fences. Different user contexts with identical State/league already address the same prior guarded league-season artifact; no new user records are shared. New/invalidated fingerprint, model, State, store, computed time or TTL trigger full read. Annual preseason fallback remains intact.

**CI evidence:** Focused CI at exact head passed **60 tests**, covering eleven-call historical reproduction, same-source and mixed Forecast/Current callers, concurrent cold requests, fingerprint/time change, State/store isolation, TTL, provider-fallback, and original runtime regressions. Stable-head full suite run `37962962828` verified PR head before/after and passed **2,256 tests**, zero failures, one unrelated warning; one full-suite run at the exact accepted head. No unit test proves hosted p95, so independent hosted telemetry was required.

**HOSTED before/after measured comparison**, selected two bounded existing Render restore journeys (not necessarily same user action sequence or external load):
- **Before:** old Render deployment `dep-db3ruiqjnfac738ibiag`, restore ID prefix `768d5b5a`, 2026-10-08 22:39–22:42 UTC. `preseason_forecast_baseline` full SQL read count **11** (`get_latest_reusable_artifact`); logged JSON payload **10,679,328 B** (=11 × 970,848); **3,454.41 ms** sum of SQL read elapsed; nearest-rank **p95 498.05 ms** across 11 full-read samples.
- **After:** exact code deploy `dep-db4hs7vavr4c73f9pal0`, restore ID prefix `f3734db7`, 2026-10-09 17:03–17:06 UTC. Exactly **1 full payload read** (`get_reusable_artifact`) + **11 metadata-only SQL reads** (`get_latest_reusable_artifact_metadata`). Payload bytes **970,848 B** total, metadata payload **zero**. SQL elapsed **398.11 ms full + 400.73 ms metadata = 798.84 ms** (cold metadata 299.49 ms, subsequent reads mostly 9.7–10.8 ms); nearest-rank **p95 398.11 ms** across 12 read calls. Overall SQL statements **increased 11 → 12**, but full-payload queries **decreased 11 → 1**. Full-payload bytes **−9,708,480 B (−90.91%)**; summed baseline SQL read elapsed **−2,655.57 ms (−76.88%)**; all-read SQL p95 **−99.94 ms (~−20.1%)**. These are measured database/logical-transfer benefits, NOT measured billed egress or equivalent browser wall-clock acceleration; including metadata misses and future cache expiry will change rate.
- User/session startup's *durable-context restore stage* telemetry was **8,510.81 ms before / 8,301.52 ms after**, but it **completes before the baseline-read sequence** and does not establish a causal end-to-end latency improvement. Browser p95 for this exact call pattern is **not instrumented**.
- Render coarse **sampled process memory** before at 22:40/22:45/22:50 UTC: **275,689,470 / 370,843,650 / 370,843,650 B**. After at 17:05 and 17:10: **280,735,740 / 301,264,900 B**. Sample maximum **370.84MB before, 301.26MB after**, below internal working budget 429,496,720 B and Render hard 536,870,900 B; this is NOT true peak RSS nor controlled paired-workload memory savings. No `rss` attribution logs emitted for the new restore window; true peak and causal delta **unmeasured**. Four-entry cap and TTL constrain additional footprint.
- No `ERROR` app logs in new inspected window. Independent read-only Supabase check at 2026-10-09 17:06 UTC: **445 PIT State rows, 169,923 Market first-writer rows, 5,681 derived artifacts, 600,321,171 B physical database**; existing storage overage **NOT** reclaimed, as expected. Exact live Render SHA independently verified.

**Disposition: ACCEPT Tranche 1 for its narrow full-payload read-reuse objective.** Correctness, standard CI, exact deployed code and the equivalent 11-request hosted persistence pattern meet the authorized gate; no certified browser wall-clock/true peak RSS gains. Do not claim 2.66s faster UI or 9.7MB billed egress. Preserve current short TTL; watch for accidental cache scope leakage or memory regressions.

**Recommended next separate Management authorization:** *acquisition-event instrumentation only* in existing provider adapters; measure per-provider URL-family/season/horizon/week, HTTP request count, response bytes, latency, acquisition reason (manual, auto probe, explicit refresh, in-season Current), source fingerprint, and version freshness without logging user data/raw payloads. **Do not implement cohort reuse** or adjust refresh/source selection until that ledger proves safe reuse boundaries. Provider commercialization sequence remains settled: validate FSFFL now, negotiate agreements later before commercialization. PR #439 is still draft candidate; Career #405 PR2, D-F, #436 and presentation sub-content work remain paused/separately authorized.

## 2026-10-09 — MANAGEMENT AUTHORIZATION / Intelligence Lifecycle Efficiency Tranche 1

**Management ACCEPTS the October 9 Technical Intelligence Lifecycle Efficiency Gate.** Authorized **Tranche 1 ONLY: exact-authority preseason forecast baseline execution-scoped read-through reuse**. Begin from GitHub main `60c4607fc5945eac6d1b08096dd0e7d48a8b8f9a`. Checkpoint this authorization BEFORE implementation. A+B accepted, C whole-publication skip CLOSED, provider-cohort acquisition/telemetry and presentation content reuse NOT authorized, and draft hybrid PR #439 remains a candidate.

**Scope and acceptance:** Reproduce prior 11 calls / 10,679,328 logged serialized JSON bytes / 3,454.41 ms summed DB time to a retained preseason baseline in one restored journey, and reduce to at most one full DB read per exact league, season, model, governed artifact fingerprint and owner within that execution. Favor narrow bounded execution-context reuse, never unbounded or long-lived process cache; preserve authoritative invalidation, tenant/team/State isolation and last-good/legacy fallback. Require unchanged Forecast, Current Position & Depth, Intrinsic, PIT, replay, downstream outputs, manifest/pointer publication and no-silent-heavy-refresh. Test cold/restart/multi-league/season/model changes, baseline fallback and concurrent isolation; compare SQL counts, logical serialized bytes, actual wall-clock and p95, and peak RSS, with independent before/after hosted check. **Do not turn logical byte savings into billed egress or sum of SQL latency into user-visible wall time.**

**Execution contract:** Focused tests during changes; ONE full suite on exact stable merge-ready head (not every push); accept head before merge/deploy; verify deployed SHA and bounded hosted saved-session/read behavior without initiating provider refresh. Stop/rollback for any analytical mismatch, memory exhaustion, new heavy refresh, incorrect reuse, or failure to measure hosted effects. Document actual measured deltas and terminal status before returning to Management. Commercial agreements remain a future post-validation step; no licensing/pricing reopening.

**Hard exclusions:** No provider source, model, refresh policy, schema, data retention, migration, infrastructure or publication behavior changes; do not start Career #405 PR2, Supabase D-F, issue #436, provider cohort instrumentation or presentation content reuse.

## 2026-10-09 — Management provider-strategy correction / measured technical efficiency gate

**Authoritative correction superseding prior same-day commercialization/licensing action language:** provider strategy is already settled. Build and validate FSFFL NEXT first; seek provider commercial agreements **later, before commercialization**. Do not reopen provider negotiations, licensing review, or create a licensing prerequisite for technical efficiency work. Keep each source replaceable through its adapter and governed evidence contracts; maintain provenance/`usage_class` and existing data-use boundaries. No provider selection or blending change without historical accuracy/coverage proof. This section is a Management instruction and takes precedence over previous historical notes proposing immediate commercial licensing gates.

**Completed bounded read-only technical audit** from GitHub main `e3e4e526b703b2957a3e5c2e21982599c1700efe`, Render and Supabase. Provider ROS Oct 8 retained **8 CBS and 5 Razzball** distinct revision records; their concrete acquisition adapters each fetch 4 position pages, so successful recorded acquisitions imply **≥52 position-page requests**, while HTTP response sizes and failed/unrecorded attempts remain UNKNOWN. No per-cause manual vs automatic refresh count exists in current logs; `/api/connect/sleeper/background/freshness` runs a cheap change probe with age alone insufficient for heavy refresh, and explicit/background POST can use full reconciliation when governed conditions apply. Default 3600s is eligibility in the POST path, NOT observed hourly refresh. Source snapshots must be shareable only under exact provider-season-horizon-week-version/freshness coordinates; league scoring and private State remain isolated. Full-season Forecast uses Razzball, FFToday, CBS, NFL Fantasy; Current uses ROS CBS/Razzball + Sleeper completed actuals. PIT/replay rules preserved.

**Two specific measured saving ceilings, not achieved gains:**
1. One Render startup/restore interval `2026-10-08T22:39:30Z–22:41:35Z`: **11 repeated reads** of single immutable `preseason_forecast_baseline` at **970,848 logged JSON bytes/read**, totalling **10,679,328 bytes**, **3,454.41ms cumulative SQL read time**. The baseline loader decodes via `get_latest_reusable_artifact` on every caller. Within this identical-authority window, one read could satisfy the eleven consumers if safe shared in-process decode/pointer authority is proven: **10 fewer DB full reads / 9,708,480 fewer logical serialized bytes**; p95/user-visible time benefit needs test, not automatically 3.45s.
2. Oct 8 SQL content-hash check on **64 presentation surface rows** shows, after removing ONLY `publication_generation_id`, four families (Home, Franchise, League Atlas, Dynasty Position Rooms) each have 8 rows/2 distinct bodies/**6 exact duplicate bodies**. **24 repeated bodies / 1,291,732 B stored JSONB datums**. Other four families have NO exact matches under this test. These bytes can be considered for content reuse ONLY after consumer parity; all published generations, manifest hashes, late Dynasty and independently changing Current evidence are protected. Logical datum count is not physically reclaimable relation size.
Other facts: `596,110,483 B` database physical, presentation 2,525 rows/155,170,202 B compressed JSONB datum, Forecast 63,057,386 B, Simulation 27,491,129 B. Retained 2026 ROS CBS 31/31 fingerprints; Razzball 23/22, 282 latest player IDs overlap; provider predictive accuracy comparison remains separate. Accepted A pool/B batch/coalesced queues and no-silent-heavy-refresh behavior already exist, do not recreate them.

**Priority / fastest independently gated development authorization (none given here):** (1) narrowly bound and test preseason baseline repeat-read elimination inside existing owner with exact identity/invalidation, (2) non-sensitive acquisition-reason/URL-family/body-bytes/freshness ledger and test provider-cohort acquisition sharing under same governed refresh evidence, (3) private content-equivalence and compact representation study of duplicate presentation bodies without a publication skip or loss of historical manifest/last-good identity. Compare A optimized PG, B optimized workload+object storage, C selective compact representations by measured bytes/CPU/p95/operating cost, not by preference. The draft hybrid PR #439 remains nonproduction candidate only and its private full-real zlib/S3 gate unresolved. Code changes, migration, server refresh, schema, deletion, licensing negotiations and paid plans NOT authorized. Retain the larger product roadmap, paused Career #405 PR2/D-F and issue #436. See canonical Supabase workstream for exact statistics and method.

**Gate:** DIRECTIVE COMPLETE — TECHNICAL LIFECYCLE EVIDENCE; MANAGEMENT MUST APPROVE FIRST NARROW IMPLEMENTATION.

## 2026-10-09 — Management correction: optimize the INTELLIGENCE LIFECYCLE before choosing storage

**Authority:** Management explicitly retracts any assumption that large JSONB artifacts must move wholesale into object storage. The hybrid prototype and draft PR #439 are **one candidate**, not an accepted production selection. This is a bounded read-only, no-runtime-change evaluation against current main `554225c66d32646beccb0ddf091fe01dd5bf1cd8`, production Render unchanged on accepted A+B. Whole-publication C skipping stays CLOSED; do not pursue new dependency-watermark engineering. Exact evidence/classifications and 1/10/50/100 league sensitivity model: `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`.

**Measured:**
- Current Supabase database **596,110,483 B** allocated, 445 PIT States and 169,923 Market first-writer observations. Presentation surfaces **2,525 / 155,170,202 B compressed JSONB datum**, compared with Forecast **397 / 63,057,386 B** and Simulation **295 / 27,491,129 B**. Presentation SQL JSON text is ~995 MB; none of this can be treated as isolated reclaimable physical files or as disposable historical data.
- League-specific Sleeper full State fetch includes league, roster, users, picks, global NFL player catalog, NFL season schedule/state, and weekly matchups. Cheap change probe still issues multiple HTTP requests and is not exhaustive. Default configured full-provider interval 3600 s is NOT observed automatic refresh cadence. Four source full-season Forecast; ROS CBS/Razzball plus Sleeper actuals; direct in-season routes are acquisition-active. Normalize/score under league rules before 50,000-trial Simulation and Value; Current and late Dynasty readiness can change after same-State core publication. Single publication owner retains exact generation/manifest/hash/last-good and PIT.
- 2026 CBS ROS snapshot revision history **31/31 distinct contents**, Razzball **23/22**, latest player overlap **282**, unique provider coverage materially differs. No observed accuracy/coverage backtests justify dropping one source or changing blend. Source HTTP counts, actual network payload bytes, refresh trigger distribution, cache hit/miss, SQL duplicate-byte classes, real GET response bytes, p95 and cloud costs remain unmeasured.
- Current app has accepted A connection reuse, B market batches, queued same-State checkpoint coalescing, metadata-first presentation read bundles, bounded existing caches. Never erase these gains or recreate a second orchestrator. Sample restart previously used 25 exact reads/~22.3 MB logged serialized data; repeat API and Atlas retries were observed in one Safari session but are not proof of population traffic or cache rates.
- **Commercial source licensing is a blocker to address before scale:** Sleeper API noncommercial free use and commercial inquiry; Razzball and CBS published noncommercial projection/content restrictions; FFToday/NFL Fantasy and other scopes require legal review. No public scraping license assumption. Tenant/private data and source license terms also govern shared caches and PIT retention.

**Ranked next Management-controlled work, not implemented:** (1) approved provider-rights verification + privacy-safe acquisition/refresh/size/trigger ledger and licensed season/provider cohort sharing; (2) exactly contract-preserving sub-payload compression/dedup of eight presentation surfaces, preserving every generation and materially changing Current/Dynasty outputs; (3) narrow per-request/full-payload read and repeated serialization reuse inside current metadata/reader boundary, with resource instrumentation. Workload optimization precedes object destination selection. A optimized PG is simplest near-term, B optimized workload + hybrid possible later, C selective compact/hybrid merits a gated semantic and consumer-parity test; **zero verified incremental savings** claimed. Baseline 12 fresh publications/league/month modeled ~0.169 GB PostgreSQL combined derived+Market growth/league-year, rising to ~16.9 GB at 100 leagues before other families, with 25%-presentation-reuse an unproven sensitivity only. Neither proposed sharing nor dedup qualifies as blanket publication suppression.

**Next explicit authorization if Management chooses:** 1 narrowly scoped instrumentation/source-rights ledger and a private content-equivalence POC with no production source/refresh/model/retention changes; wait for Management before code. Phase 2 private real-artifact zlib/S3 proof may proceed separately ONLY if safe private test bridge is available. A+B remain ACCEPTED, C skip CLOSED; Career #405 PR2, other Supabase D-F and Player Intelligence #436 remain paused. Product roadmap retained.

## 2026-10-08 — Phase 2 nonproduction storage validation: NO-GO / private export blocker

Management accepted the Foundation as a **viable nonproduction direction only**, and authorized limited Phase 2 full-real Forecast+Simulation zlib, governed Pydantic, and real S3-compatible local backend validation. The project remains PUBLIC; production user raw data must not appear in GitHub or CI.

The bounded gate cannot currently complete. Connector-side read-only Supabase access verifies current Forecast row 11540 (JSONB 161,373 B) and Simulation row 11541 (JSONB 118,887 B), but does NOT securely materialize either complete unmodified payload into the isolated Python test filesystem. The isolated runner has no protected Supabase credentials and no reachable project network. Local boto3 is present but MinIO/Moto is absent and package installation failed for lack of package-index DNS. No production data, code or infrastructure was changed; no public raw bytes published. Existing Phase 1 synthetic zlib and in-memory LZW demonstrations are NOT counted as Phase 2 real-data/Pydantic/storage-backend acceptance.

**Decision: STOP / NO-GO for Phase 2 production readiness.** No accepted zlib-vs-JSONB ratio, full-model roundtrip, GET p95, network/eject cost, RSS or incremental object-scale claim is available. Retain hybrid as a conditional architecture candidate, keep draft PR #439 unmerged, and do NOT authorize shadow migration, production schema, storage provisioning, deployment, database cleanup or index changes. The exact next possible authorization is an isolated private authenticated export/test session for just the full unchanged ids 11540/11541 with metadata, Python zlib and model decoders, alongside genuine local S3 (MinIO/Moto or equivalent), using owner-only temporary files and no production secrets or user raw bytes in Git or Management report. If that cannot be provisioned, do not continue speculative development. Accepted Tranches A+B remain; C closed; Career #405 PR2, unrelated Supabase D-F and issue #436 stay separate. Workstream: `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`.

## 2026-10-08 — Management strategic shift: Storage Architecture Foundation POC

Management prioritizes sustainable **commercial multi-league storage**, not another isolated Free-tier index or presentation deletion. Accepted Supabase pooled transport A and batch Market persistence B remain immutable. Whole-publication skip C is CLOSED. One bounded analytical/design/**nonproduction executable** foundation tranche was authorized. The empirical Oct 8 capacity ledger is recorded in `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`, with appendix and runnable POC on draft [PR #439](https://github.com/jderhagopian-stack/fsffl-next/pull/439), branch `work/storage-architecture-foundation-poc-20261008` (**NOT MERGED**).

**Architecture candidate:** single existing persistence adapter, small PostgreSQL State/PIT/manifest/published generation/hash/tenant metadata, content-verified immutable large analytic objects in S3-compatible storage. Production implementation NOT APPROVED. The working isolated Python zlib+filesystem object/SQLite metadata POC proves first-writer immutable identity, model/State/tenant separation, SHA-256, restart, explicit legacy read, and unchanged `ReusableArtifactRecord` interface using nonidentifiable fixtures; focused CI PASS. Complete real Forecast and Simulation production payloads were round-tripped privately in ephemeral JavaScript/LZW32 tests, NOT through the chosen zlib/cloud adapter. They were not committed to the **public** repository. This is an intentionally OPEN Phase 2 readiness gate, not concealed as full contract parity.

**Scale model**, assumptions clearly distinguished: physical database 590,605,459 B currently; one fully new Forecast, Simulation, Value, eight presentation surfaces plus up to 535 new first-writer Market observations proxies ~1.174 MB/publication. At 12 monthly publications/league: ~0.169 GB year/league; at 10 leagues ~1.69GB/year, 50 ~8.46GB/year, 100 ~16.91GB/year before other families. Hybrid moves large immutable bytes to cheaper independent storage, but Market PIT and historical State remain PostgreSQL growth. Actual object compression, egress, restore p95 and real-cloud operating costs require hosted nonproduction proof; no Free-tier commercial-scale claim.

**Approved result only:** NONPRODUCTION foundation demonstrated, Management ACCEPT/REJECT gate. Four new separately authorized phases in workstream: (1) capacity measurement/stabilization, optionally separately assess nonunique ~31.79MB Market index; (2) production-worthy real-blob storage adapter tests (real full zlib, real object GET latency, crash, tenant, exact model decode); (3) hash-verified incremental shadow-copy migration with dual-reads and PG originals retained for rollback; (4) explicit separately-approved physical PostgreSQL reclaim/scale acceptance. Do not drop PIT/Market histories, rewrite DB, change service plans or deploy the draft POC. Do not reopen C watermark engineering or start Supabase D-F, Career PR2, #436.

**Next decision:** accept the nonproduction *methodological* foundation and authorize a separate **private full-real-zlib + selected S3-compatible backend acceptance test**; only after it passes should production adapter implementation be considered. Do not bypass the stable-head full-suite gate if draft PR is eventually made merge-ready. No production code, data, schemas, billing or deploys changed during foundation.

## 2026-10-08 — Supabase Physical Capacity Recovery Gate / READ-ONLY CLOSEOUT

Management ACCEPTS the Tranche C NO-GO and formally CLOSES the whole-publication skip/coalescing proposal. A+B remain accepted. The separately authorized read-only presentation-generation reachability and physical-disk audit measured 590,605,459 B total database allocation, 53,734,547 B above the 512 MiB Free allocation. The shared `derived_artifact` relation totals 400,146,432 B, including 392,757,248 B TOAST+index. Presentation surfaces hold 2,509 rows/154,089,092 B of JSONB datum within this **shared** relation, not a standalone removable file.

Exact generation joins by user/league, State, selected team, promotion ID, and model contract: 959 surfaces (55,525,544 B) linked by manifest AND published-generation; 357 (20,230,262 B) linked by manifest only; 1,155 (75,932,853 B) linked by published-generation only; only 38 (2,400,433 B) lack both exact links. The 38 also have no matching current user pointer or most recent league-last-good State, but interrupted publication, legacy restore, delayed Dynasty/Intrinsic, PIT/replay or other consumer obligations remain unproven: **zero rows declared safe to delete or authorized for deletion**. Even deleting them would not guarantee relation file reduction; a rewrite would raise lock, storage and recovery risks. PostgreSQL TOAST churn estimates are not guaranteed reclaimable pages. This presentation-cleanup approach is **NO-GO as a meaningful immediate physical capacity recovery**.

**One recommended next Management option, entirely unapproved at present:** narrowly evaluate possible redundancy of the NONUNIQUE `market_value_snapshot_history_idx` (31,793,152 B physical; 6 recorded scans) against the REQUIRED first-writer unique index `market_value_snapshot_asset_ref_asset_kind_scale_id_market__key` (31,031,296 B; 331,059 scans). The nonunique index has identical five keys except its final estimate timestamp is descending; a backward unique-index scan may support common four-key equality plus descending-time reads, but mixed-direction or range consumers require query-plan/performance proof. A separately approved index-only schema change could directly release ~31.79 MB without deleting PIT observations; modeled database afterward 558,812,307 B, still **21,941,395 B over quota**. Never remove the unique key. Validate all reader templates and potential rollback space before any DDL. These are modeled bytes, not achieved savings; no paid upgrade is requested.

See `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md` for complete allocation ledger, protection categories, and the single conditional acceptance plan. **Status: DIRECTIVE COMPLETE - READ-ONLY PHYSICAL AUDIT; MANAGEMENT GATE BEFORE ANY STORAGE MUTATION.** No runtime code, schema/data change, cleanup, VACUUM, migration, paid tier, refresh, deployment, or model work. Career #405 PR2 and Supabase D-F paused; Player Intelligence #436 separate. Live Render remains accepted B deployment.

## 2026-10-08 — Supabase Tranche C DEPENDENCY-AUTHORITY DESIGN COMPLETE / NO-GO

Management ACCEPTED the conditional implementation STOP and authorized **one design-only dependency-authority gate**. The code trace confirms Current Position & Depth fetches independently changing CBS/Razzball ROS projections, Sleeper NFL-state and completed-week actuals (with possible corrected weekly stats), plus preserved preseason baseline, league rules, scoring coverage, configured lineup policy, current clock and fallbacks. Existing `projection_snapshot.content_fingerprint` is a useful inexpensive **retained after-fetch** version, not a current source version before new acquisition; no cheap complete pre-build version exists for weekly actuals. In three same-State/core-FSV publications, CBS fingerprints changed A→B→C, Razzball A→B→B, while governed Current player and strength numbers changed across both transitions. Dynasty/intrinsic late-completion statuses/contracts/timestamps, team changes, Market execution timing, and atomic manifest/pointer/last-good integrity remain separate publication contracts.

Two historical read-only output-transition assertions confirmed stale-copy risk; eight focused deterministic design counterexample checks passed (not a production integration test). Full proposed cheap dependency proof **fails**. **Management recommendation: ABANDON the current whole-publication C no-op guard; do not broaden into a new provider-version controller or change refresh policy. Certified C savings = 0.** The 129 extra generation IDs and 17-generation case are not safe-skip counts. Physical Supabase database still `590,605,459` B; 2,509 presentation surfaces account for `154,089,092` B JSONB datum, with no reachability/deletability decision yet.

**One concrete follow-up for separate Management decision:** non-destructive read-only published/last-good/presentation-generation reachability and storage-byte audit, focused on `runtime_presentation_surface`. Establish exact consumer, manifest, restart, Dynasty evidence, and PIT dependencies before considering any compaction/retention change. This is NOT authorization for D/E/F, deletion, storage migration or paid tier. A+B remain accepted and live; issue #436 and Career #405 PR2 remain separate; no provider refresh, model change, code change or C deployment occurred. See the canonical Supabase workstream for exact data, code-path trace, and tests.

## 2026-10-08 — Supabase Tranche C CONDITIONAL IMPLEMENTATION STOP

Management conditionally authorized the existing-owner metadata-first C no-op guard **only after complete dependencies are demonstrated**. New read-only comparisons of three exact same-State, same-team, same core-evidence presentation generations found material independent Current Position & Depth drift: 9 then 2 player season outlook score changes, 24 strength indexes and league-average expected-point values, and four expected-point changes. Current deliberately derives from separately evolving ROS/completed-week and preseason forecast observations; the current State/core Forecast/Simulation/Value hashes do not cover that authority. The two Value Lens execution timestamps and Market Workspace elapsed-time metric are additional visible differences requiring explicit consumer-policy decisions. Thus the existing metadata **cannot safely certify full publication equivalence before rebuilding surfaces**. The authorized conditional implementation gate fails closed: **no skip code, CI rerun, merge, deployment, provider refresh or model changes**. Zero Tranche C savings claimed. Keep A and B ACCEPTED.

Draft documentation PR [#438](https://github.com/jderhagopian-stack/fsffl-next/pull/438) was stale relative to newer canonical Tranche C evidence. Its confirmed correction has been incorporated *as an additive section* in the canonical Supabase workstream: the post-B explicit refresh attempted **1,074** observations in four bounded SQL batches (300+300+235+239), with **539** newly retained first-writer records, not the earlier misreported 1,070/zero. Its docs-only full suite failed one resource assertion (current RSS 537,247,744 B versus 536,870,900 B hard gate), 2,247 other tests passed. Do not dismiss the memory failure or merge stale PR; investigate that resource gate separately if authorized.

**Next Management decision:** authorize only the prerequisite metadata-authority/reachability design for independent Current forecast input versions (ROS, completed actuals, preseason data, scoring/lineup policy), plus Dynasty readiness/Market execution semantics. Any future implementation needs tests demonstrating identical and changed variants, exact publication fencing, PIT and last-good safety, and eventual hosted measurements. No broad hashing, second lifecycle owner or presumptive coalescing. Full evidence in `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`. Live Render remains accepted B deployment `dep-db3ruiqjnfac738ibiag`; database > Free quota without physical reclamation.

## 2026-10-08 — Supabase Tranche C EVIDENCE gate finished; implementation awaiting Management

Read-only C investigation of accepted A+B live runtime found repeated same-semantic **published-generation IDs**: 169 retained production generation records but 40 exact State/selected-team/Forecast/Simulation/Value fingerprint identity groups, leaving 129 extra generations sharing the same core evidence; one single exact State had 17 generation IDs for one immutable upstream evidence triple. Three recent same-State surface publications each materialized 8 surfaces / ~3.08MB encoded, although only 4/8 were byte-identical after removal of the top-level generation field; remaining differences are not yet proven cosmetic. Two historical same-State scopes contain genuinely distinct Forecast/Simulation/Value fingerprints, and the newest Oct 8 full refresh also changed State. Hence **State-only skipping is forbidden**.

Cumulative derived-artifact UPSERT calls 11,559, table updates 5,583 (not all proven redundant). PIT history 445 rows / 445 distinct State hashes: permanently preserved. Explicit full refresh max RSS ~440.96MB exceeds accepted 429.5MB work budget, below Render 536.9MB hard limit. Logical presentation payload family 2,509 rows / ~154.09MB JSONB datum storage; physical database ~590.61MB still over Supabase Free quota. C proposes only a dependency-complete pre-publication metadata guard within the existing publication owner, no heavy foreground hashing, and skip only fully proven identical State/team/core evidence/presentation and Dynasty readiness. Always retain State history, last-good, PIT Market, lineage, manifest-before-pointer and restart recovery.

**Management gate:** evidence delivered; **NO C bypass implementation authorization**. No code, deployment, refresh-policy, cleanup, migrations, paid tier, D-F or Career #405 PR2 work. Canonical detailed measurements/limitations: `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`. Live Render remains `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1` on `dep-db3ruiqjnfac738ibiag`; documentation-only main changes do not require deployment.

## 2026-10-08 — Management handoff: Tranche B accepted; C evidence gate is next

Management **ACCEPTS Supabase Tranche B** and closes its implementation/production gate. Accepted runtime remains PR #434 merge `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1` on Render `dep-db3ruiqjnfac738ibiag`; later docs commits are not runtime changes. The stable candidate passed `37805666770` with 2,248 tests / 1 warning. B's governed contract is now permanent: Market publication uses bounded deterministic set-oriented writes while preserving exact conflict identity, PIT history, timestamps/context, first-writer lineage, publication order and tenant/model authority. Do not permit future code to regress to one INSERT per observation without reopening this gate.

Management also physically exercised one ordinary **Refresh Intelligence** on iPhone/Safari. That journey completed through publication and produced live PostgreSQL evidence of **1,070 observation attempts in four batch statements (2x300 + 2x235)** with zero new retained rows because existing exact identities correctly conflicted. This reinforces B's real hosted-path acceptance. The same refresh exposed a separate transient Player Intelligence bug: `IntrinsicBuildSuperseded` surfaced as HTTP 500 during State handoff, while history stayed available and Player Intelligence worked normally after publication. Track/fix this narrowly under **issue #436**; do not reopen P0 architecture or B because of it.

The explicit refresh also peaked at ~440,963,072 bytes RSS: above the 429,496,720 internal heavy-work budget but below the 536,870,900 hard Render limit. Preserve this as capacity evidence. It is not currently attributed to Tranche B and does not undo B acceptance.

**Immediate authorized sequence from this handoff:**
1. **Supabase Tranche C evidence gate only** — instrument/trace current A+B behavior enough to count unnecessary same-semantic republish/materialization attempts, identify exact fingerprints/invalidation coordinates, and distinguish unchanged repetitions from same-State genuinely changed evidence. No skip/coalescing behavior yet; return to Management with measured evidence and a bounded proposal.
2. Keep **D-F, physical retention/reclamation, paid Supabase, migrations, refresh-policy/model changes and Career #405 PR2 paused** until separately authorized.
3. Preserve A and B as regression boundaries in every relevant persistence/publication change.
4. Resolve issue #436 narrowly when scheduled: expected State supersession must return a governed non-500 response/last-good-or-rebuilding state, not stale evidence.

Physical database allocation is still above the Supabase Free 0.5GB quota (~586MB at the B closeout). A and B slow future resource burn; neither reclaims existing bytes. Storage reclamation remains a later evidence/reachability gate, not an emergency deletion authorization.

A new Management chat should start from `AGENTS.md`, `CURRENT_OPERATIONS.md`, `OPERATING_PROTOCOL.md`, this file, and `workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`. The first decision/execution target is **Tranche C evidence**, not Career PR2 or storage deletion.

## 2026-10-08 — Tranche B live; worker acceptance recommendation

The Management-authorized Tranche B market batching correction passed focused parity tests and the single stable full suite `37805666770` (2,248 passed, one warning) on head `48d78375cce957dca5faee71a8c39108c3e006a2`; merged `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1` and is live on Render `dep-db3ruiqjnfac738ibiag`. Hosted natural publication used 2 idempotent multirow INSERTs for **535** market observations; preserved 169,384 historical rows, original first-writer provenance, stable PIT State count and accepted model/publication contracts. Same 25 restore reads, read p95 improved, no inspected warning/error, and peak RSS below Render limit. Full measured ledger and limitations live in `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`.

**Worker recommendation: ACCEPT Tranche B**, subject to Management's independent promotion gate. This does not authorize C-F, Career #405 PR2, paid Supabase, cleanup, migration, refresh policy or model work. PostgreSQL physical allocation rose from ~584.7MB to ~586.4MB across B's normal startup; Free quota remains exceeded. Do not conflate SQL attempt reduction with storage reclamation. Documentation-only commits after B's merge SHA are not runtime code changes.

## 2026-10-08 — Tranche A accepted; Tranche B alone authorized

Management has **ACCEPTED Tranche A** transport on existing hosted write + matched restore evidence, with manual Gate 2 telemetry probe waived as unnecessary. Its exact live code stays `1c5b5325791cddaf49d35d372270a9aba0586afb` on Render `dep-db3qq4vlk1mc73cj3910`. This supersedes the earlier *recommended acceptance* and *B not authorized* checkpoint, which remains below as historical evidence.

Management authorized only **Tranche B idempotent 300-row set-oriented market-value persistence**, with original PIT/first-writer identity and publication semantics preserved. Active draft PR [#434](https://github.com/jderhagopian-stack/fsffl-next/pull/434) on `work/supabase-tranche-b-market-batching-20261008` starts from main `29d2395c213829ed9fbcbf648d552c96089f0c05`. Do not deploy until focused parity, one stable-head full suite, and governable hosted equivalence acceptance plan. No automatic transition to C-F. Career #405 PR2 remains paused, as do paid Supabase, deletion, retention, migration, refresh policy, provider experiments, and model/analytics work. Supabase database allocation ~585 MB exceeds Free quota; batching will not reclaim physical bytes.

## 2026-10-08 — Supabase Tranche A production write/read evidence (Management review)

**Durable regression rule:** Tranche A's bounded pooled connection ownership is now an architectural/runtime invariant, not a temporary incident patch. Future persistence, restore, publication, and background-work changes must preserve bounded reuse or return to Management with a measured replacement design. Connect-per-operation behavior, bypass adapters, unbounded pool/waiter growth, or material matched-workload regression in connection churn automatically reopens the narrow Supabase resource gate. Keep legacy mode only as emergency rollback. Add low-volume pool counters in a later relevant tranche if useful; do not create a new telemetry-volume problem to observe the old one.

The earlier operator-assisted Gate 2 telemetry probe was **not required** because independent Supabase artifact records aligned with the actual Render-hosted publication write phases. This is a management-acceptance recommendation, not an implicit authorization of the subsequent workstream. PR #433 stable-tested at `8d3c17cdf0f9f81cc4360f3c85f76845c151cbe8` (2,240 tests), merged to `1c5b5325791cddaf49d35d372270a9aba0586afb`, live on Render `dep-db3qq4vlk1mc73cj3910`. Authentications 468 -> 5 in comparable 10-minute startup windows, total Supavisor events 1,078 -> 14, same 25 persisted restore reads, successful readiness and safe peak RSS. Full ledger and limitations: `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md`. **Recommendation: ACCEPT Tranche A transport, without interpreting the total project-wide auth decrease as a direct app-only connection count.** Direct authenticated browser saved-session GET and internal pool checkout/wait counters remain unverified and should not be invented.

Supabase Free Plan remains in force and allocated size exceeds its quota. **Tranches B-F, paid tier, retention cleanup, migration, refresh-policy and model changes and Career Coverage #405 PR2 remain paused pending separate Management direction.** Tranche B market-write batching may be evaluated next, but this checkpoint does not authorize it. Repository-only checkpoint commits after `1c5b... ` do not change the exact Render-deployed runtime commit.

## Management handoff rule

A new Management chat must, before issuing new scope:

1. read `AGENTS.md`;
2. read `docs/operations/CURRENT_OPERATIONS.md`;
3. read this `MANAGEMENT_CONTINUITY.md`;
4. read `docs/operations/PRODUCT_ROADMAP.md`;
5. read `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`;
6. read the currently active workstream checkpoint(s);
7. verify current GitHub main / open PR / Render deployment state rather than assuming the documents are perfectly current.

Do not recreate priority order from chat memory alone.

## 2026-10-08 Supabase Gate B / Tranche A authorization

Management authorized **Tranche A alone**: one bounded lazy psycopg connection pool for the existing hosted PostgreSQL persistence adapter, initially min 0 / max 3 connections, 5s checkout wait, 75s idle lifetime and 720s lifetime, plus a legacy transport escape. Exact SQL, PIT/history, publication/last-good, tenant and model semantics are frozen. Do not deploy without focused validation, one stable-head full-suite gate, connection/pooler/resource checks, and bounded hosted Render-credential acceptance. Tranches B-F remain **not authorized**. Paid Supabase, deletion, migration, provider-refresh experiments, refresh policy changes and Career #405 PR2 stay blocked. The management-approved Gate B design and Gate A / minimal-write PDFs are read-only evidence. Work in draft PR [#433](https://github.com/jderhagopian-stack/fsffl-next/pull/433), NOT yet promoted. An app-specific credential write has not been verified. See `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md` for live checkpoint.

## 2026-10-08 Supabase P0 priority change

Management has elevated **Supabase Capacity & Scalability Recovery** above Career #405 PR2 as the immediate operational priority. The database is over the Free Plan quota (568.16 MB vs 0.5 GB) and Management reports it locked/read-only. Egress and log-ingestion charts show a major late-September step-change centered around **2026-09-26/27**; subsequent plumbing rewrites appear to have reduced usage somewhat but not restored the pre-inflection baseline. Treat that as evidence that some waste may already have been removed while a deeper mechanism remains.

A temporary paid Supabase tier may be used to regain access/headroom, but only as an **emergency bridge**. It must not become the architectural answer or hide ongoing growth. The permanent goal is to restore efficient behavior that remains viable at thousands/tens of thousands of leagues.

Immediate sequence:
1. Phase 0 containment and before-state evidence;
2. Phase 1 targeted read-only audit using 2026-09-24..29 and the 09-26/27 inflection as the first forensic window;
3. Phase 2 semantic-sharing/retention architecture;
4. mandatory Management Gate B before production cleanup/remediation;
5. controlled stabilization and resource-proportionate scale validation.

Career PR1 remains complete. Career PR2 is still approved conceptually but is **paused from implementation/promotion** until the Supabase audit/design establishes safe persistence/materialization boundaries. Do not allow dynamic Career work to compound an unclassified egress/storage problem.

Canonical checkpoint: [Supabase Capacity & Scalability Recovery](workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md).

## 2026-10-07 Management reconciliation

The larger FSFFL NEXT roadmap has **not** been replaced by the recent corrective program.

The project spent the recent period closing prerequisite reliability, architecture, Simulation, Intrinsic, League Atlas, Current Position & Depth, and managed-team product consolidation work. Those corrections are enabling work. They are not the new long-term roadmap.

Management intent remains to return to forward product development once the bounded immediate gates below are closed.

### Program position now

- **P0 Architecture Recovery:** architecturally complete. Preserve the simplified published-reader / lifecycle model. Do not resume endpoint-specific plumbing repair unless new evidence proves a surviving architectural invariant is violated.
- **Simulation 2.0:** core program accepted. Preserve 50,000-run authority, replay identity, week-by-week current-season semantics, governed postseason, common-world counterfactuals, team-of-origin ordering, and accepted Multiverse foundations unless a separately approved directive changes them.
- **Foundation 4 / Career Intrinsic:** career-forward model foundation is live. The remaining material gap is **coverage/completeness**, tracked in Issue #405 and the Career Coverage checkpoint.
- **League Atlas / Current Position & Depth:** physically accepted. Current follows the lineup; Dynasty follows the assets. Do not create another Current positional authority.
- **Home → Franchise Overview:** PR #418 is merged/deployed and physically accepted by Management on authenticated iPhone/Safari. Franchise is now the managed-team landing experience. Standalone Home is retired as a product surface.
- **Navigation / product hierarchy:** PR #421 is merged, deployed and physically accepted on authenticated iPhone/Safari. Primary navigation is now `Franchise | League | Explore | Trade | More`. The former Home item is removed; this tranche is closed.
- **Franchise visual-polish note:** Management preferred the original Home treatment where the “What Matters Most” card was red. This is a non-blocking presentation preference for a future Franchise polish pass, not a reason to reopen navigation or change Franchise semantics.
- **Dynamic Career Intrinsic invariant:** Career Intrinsic is current point-in-time intelligence, not a hard annual player-value table. The accepted model family/policy may be frozen and versioned, but player inputs and resulting Career values must respond to materially changing governed football evidence during the season and must rematerialize for each new season. Prior values should remain preserved as historical point-in-time snapshots. Selective invalidation/recomputation should follow dependency fingerprints; this does not authorize request-time model fitting or unnecessary whole-platform refreshes.
- **Career refresh scalability invariant:** freshness must be evidence-driven and coalesced, not page-driven or timer-driven by default. Cheap provider/change detection decides whether Career dependencies changed; unchanged fingerprints reuse last-good artifacts. Expensive fitted model authority should be reused across in-season evidence updates when its historical-training/model fingerprint is unchanged. Changed/new player evidence should be materialized in batch, and any league-wide economics/ranks that mathematically depend on the full cohort should recompute once for the resulting publication generation, not once per player/event. Broad waiver coverage should prewarm with the publication; unusual long-tail subjects remain on demand. A season rollover or promoted model/training-data change may legitimately trigger a full rematerialization.
- **Multi-league scale invariant:** design Career/Forecast refresh for thousands to tens of thousands of leagues, not for the current beta league. One league changing must not imply one historical model fit, provider ingest, or full player-universe rebuild unique to that league when the underlying evidence/authority is shared. Every expensive stage must declare its true dependency scope and cache/reuse at the widest mathematically safe level: provider/global evidence → model/training authority → scoring/rules signature → lineup/team-count signature → exact league State → team/user context. Identical semantic fingerprints should share computation/artifacts across leagues while tenant/private State remains isolated. Per-league work is reserved for facts/economics that genuinely depend on that league.
- **Global scale/resource invariant:** the same dependency-scope discipline applies to every FSFFL NEXT capability, not only Career Intrinsic. Commercial-scale architecture is required now; commercial-scale brute-force load is not. The private beta's limited CPU/RAM budget must be protected. Scale validation should use real measured stage costs, bounded synthetic/reuse tests and projected 1,000/10,000-league envelopes unless a larger execution is both necessary and explicitly resource-safe.
- **Deferred Python-runtime modernization:** do not broaden Career #405 to a Python upgrade. Python 3.11 remains a historical reproducibility fixture for the accepted Foundation 4 replay; the platform may later validate a newer production/materialization runtime (3.12 is already within the repository's declared supported range) through explicit dependency/provider compatibility, parity, performance and memory testing. Revisit only as a separate modernization tranche after the current Career/product priorities, and do not infer that historical 3.11 replay requires permanent production pinning.

## Immediate approved development sequence

### 1. Navigation / product hierarchy tranche — COMPLETE

Target primary product hierarchy:

`Franchise | League | Explore | Trade | More`

Management direction:
- remove the obsolete/inert Home primary-nav item;
- **Franchise** remains the managed-team landing/product surface;
- **League** remains the competitive landscape / League Atlas surface;
- rename **Market** to **Explore** for discovery/opportunity work;
- surface **Trade Center** in primary navigation as **Trade**;
- **More** holds secondary destinations rather than forcing every surface into the primary row.

This is a bounded information-architecture/product-navigation tranche. It does **not** authorize changes to Forecast, Value, Decision, Search economics, Simulation semantics, Current/Dynasty authority, lifecycle/publication plumbing, or Career Intrinsic.

Authenticated iPhone/Safari physical acceptance completed on 2026-10-07.

### 2. Career Coverage #405 — ACTIVE

**PR1 COMPLETE (2026-10-07 ET):** accepted after exact source/route/policy/identity/terminal provenance plus bounded downstream semantic sensitivity. Stable head `223241edcccf44af6e1c236cbab84751820c6ddf` passed Stable full suite `37723655257` attempt 2 (**2,231 passed / 1 warning**) and merged as `9141c12f3d69e8fa012b4e4db664f96e54f94aec`. The original strict numerical replay comparator remains red and visible; no back-fit epsilon or memory-limit relaxation was adopted. The first stable-suite attempt had one GitHub-runner absolute-RSS failure on the identical head; unchanged retry passed, so no product/runtime corrective was introduced. No Render deploy required. **PR2 is now the active authorized tranche:** subject resolver + dynamic evidence/materialization + complete rostered coverage under the recorded season-rollover, multi-league reuse, resource-bounded and no-retuning contracts.

The preserved 25-player roster gap is evidence of a broader production-universe boundary, not evidence that the accepted Y4–Y7 methodology was lost.

Management correction:
- the accepted Y4–Y7 authority is a deterministic **fit-on-materialization pipeline**;
- exact research code is durably preserved at commit `be2541a496227b33c12c755f576843dc4ab5a0bb`;
- accepted workflow `37096263982` restores that exact development/route code plus governed historical inputs and frozen route policy, then calls the preserved fitting path to produce the season board;
- no standalone serialized Y4–Y7 scorer was required by the accepted design, so Implementation must not reverse-engineer or “rediscover” one.

Approved production populations:
- **Reference cohort:** the frozen 335-player accepted calibration/parity cohort.
- **League accounting population:** every rostered QB/RB/WR/TE in the exact League State.
- **League decision universe:** the accounting population plus a broad, precomputed fantasy-relevant waiver/free-agent cohort so users can see Career information *before* making a waiver claim.
- **Extended universe:** unusual/deep candidates scored/materialized on demand through the same accepted pipeline when they become relevant.

The broad waiver cohort must be governed by football/eligibility evidence rather than an arbitrary top-N list. Market/Search/waiver signals may identify which players belong in the decision universe, but Market value/rank/percentile must not become a Career Intrinsic model feature.

Implementation authority:
- preserve remaining accepted historical artifacts/provenance before retention expiry;
- reuse the exact accepted Y4–Y7 code, historical evidence, frozen feature/model/route policy, seeds/settings and normalization;
- first reproduce the frozen 335 reference outputs within governed tolerance as a parity check;
- do **not** use the 25 missing rostered players or waiver candidates for model/route selection or tuning;
- do **not** reopen model-family research or change Career economics/#370;
- after parity, generalize only the subject/evidence/materialization boundary for rostered + waiver decision-universe + long-tail candidates.

The existing runtime is explicitly 2026-season scoped and carries frozen Y4–Y7/terminal assets. That is now recognized as an implementation limitation relative to the broader charter, not the intended end-state. #405 must not entrench that limitation: the reusable coverage/materialization design must be evidence-updating and season-rollover capable. Exact scheduling can remain bounded and selective, but materially changed governed football evidence must be able to invalidate/rematerialize the affected Career outputs under the same accepted model authority.

Checkpoint: [Career Coverage Extension](workstreams/CAREER_COVERAGE_EXTENSION.md).

### 3. Resume the broader product roadmap deliberately

After the two bounded items above, do **not** default into another indefinite corrective loop.

The next major program should be selected from the reconciled roadmap according to dependency and leverage, with primary emphasis on:

1. **Core product usefulness / actionability**
   - one coherent product hierarchy;
   - high-quality Explore/opportunity discovery;
   - strong Trade decision experience;
   - plain-English governed consequences and drill-through evidence;
   - repeated-session usefulness and latency.

2. **Historical intelligence foundation**
   - canonical point-in-time historical State reconstruction;
   - durable transaction/player/pick lineage;
   - player franchise history;
   - pick conversion history;
   - dated Forecast/Simulation snapshot archive and replay provenance.

3. **Decision uncertainty + Owner Intelligence**
   - simulation-sensitivity / sign-stability where useful;
   - context-normalized behavioral evidence;
   - owner tendencies as directional/descriptive intelligence;
   - no fabricated acceptance probabilities and no contamination of universal Value.

4. **Productize the league's memory**
   - Record Book;
   - franchise timelines;
   - trade/pick genealogy;
   - historical trade review;
   - generalized forward/historical What-If;
   - Multiverse / alternative futures;
   - rivalries, season stories and shareable league artifacts.

5. **Publications / analyst surfaces**
   - Preseason Preview, weekly reports, Trade Deadline / Playoff / Draft publications;
   - Year in Review / Almanac;
   - Analytics / investigation surfaces;
   - presentation remains downstream of governed truth.

6. **Commercialization / scale / league agnosticism**
   - unusual scoring/roster validation;
   - provider resilience;
   - multi-league support;
   - privacy/deletion controls;
   - observability and capacity;
   - public-scale architecture review before broad launch.

## Long-term intent that remains active

Do not lose or silently retire:
- historical PIT truth and hindsight isolation;
- origin-aware draft-pick economics;
- Broad Market / Intrinsic / League Market / Team Utility separation;
- Owner Intelligence;
- generalized What-If / Alternate History;
- Mock Draft / future behavior and needs-aware draft intelligence;
- Record Book, league history, lore and franchise identity;
- asset/pick lineage and player franchise history;
- Multiverse / alternative-futures product;
- polished FSFFL publications;
- horizon-specific/value-over-time Intrinsic presentation;
- league-agnostic scoring/provider expansion;
- evidence warehouse / proprietary calibration flywheel subject to governance;
- commercialization/public-scale hardening before broad launch.

## Frozen authority boundaries

Preserve:
`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Management-specific guardrails:
- recent bug-fix work does not automatically become roadmap priority;
- Presentation may organize/visualize/explain governed truth but may not create model truth;
- Explore/Search discovers; Trade/Decision evaluates;
- Simulation evaluates stochastic competitive outcomes and shortlisted scenarios; it is not broad discovery;
- Current follows configured lineup slots; Dynasty follows Career-forward assets;
- Current / 3-Year Intrinsic and Career Intrinsic remain distinct visible concepts;
- no hidden composite/master score merely to simplify the UI;
- no fabricated acceptance probability;
- no return to redundant per-surface publication/lifecycle negotiation.

## Documentation responsibilities

- `CURRENT_OPERATIONS.md`: live status / blockers / exact merge-deploy position.
- `MANAGEMENT_CONTINUITY.md`: Management direction, changed sequencing, deferred work, and next approved development path.
- `PRODUCT_ROADMAP.md`: broad long-range capability roadmap and reconciled program location.
- `FSFFL_NEXT_PRODUCT_PRIORITIES.md`: product-phase framing, user jobs, exit gates.
- workstream checkpoints: exact tranche contract, implementation evidence and acceptance.
- Charter / North Star: durable principles; change only when Management changes the principle itself.

## Handoff state

As of this reconciliation, the clean handoff is:

**Franchise Overview accepted → navigation/product hierarchy accepted → Career Coverage #405 active decision gate → resume broader roadmap from the reconciled position.**

The next Management chat should verify live repository/runtime state first, but should not invent a different sequence merely because older roadmap sections contain stale historical “NEXT” language.


## 2026-10-09 18:03 ET — Parallel Supabase capacity and acquisition-efficiency read-only checkpoint

**Management scope:** Separate read-only capacity/acquisition analysis while independent operator works on private Storage Phase 2 validation. Starting main `26be30ccf9f6a3e184fe221456cb316451d60f2b`. Do NOT run real-artifact compression or S3/MinIO tests, access storage credentials, touch draft [PR #439](https://github.com/jderhagopian-stack/fsffl-next/pull/439) or storage access checkpoint [PR #441](https://github.com/jderhagopian-stack/fsffl-next/pull/441), or change source/refresh/analytics/schema/retention/production/deployment/billing. Supabase project `gldxkbqcprzuffgmamxl`, organization Free, project `ACTIVE_HEALTHY`. Render production service independently observed on paid `0.5c-512mb` one-instance tier with live deployment `dep-db4m539srm7s73881fg0`, source SHA `26be30ccf9f6a3e184fe221456cb316451d60f2b`. This observation is not an acceptance or override of the separate worker's validation.

**Fresh read-only physical capacity (2026-10-09 22:03:26 UTC):** `pg_database_size=604,040,339 B` (**604.04 decimal MB, 576 MiB**), already over Free's approximately 0.5 GB project allowance. PostgreSQL inspected session `transaction_read_only=off`; this alone does NOT prove normal writes cannot fail and is not a substitute for a live write test. Last accepted actual write capability on Free was previously shown by Tranche A/B evidence; no new write attempted in this read-only gate. Earlier known physical checkpoints: Oct 8 `590,605,459 B` (increase **13,434,880 B**, +2.27%) and Oct 9 17:06 UTC `600,321,171 B` (increase **3,719,168 B** in ~4h57m). **Do not extrapolate the uneven short-window rate into a daily cost forecast**.

**Largest current physical relations / growth:** `derived_artifact` **407,797,760 B** (67.5% of entire database; heap 3,203,072 + indexes 4,210,688 + TOAST incl index 400,351,232). Earlier Oct 8 relation `400,146,432 B`: **+7,651,328 B**. `market_value_snapshot` **119,693,312 B** (19.8%; 169,923 preserved first-writer PIT rows), unchanged from comparable earlier relation measure; `projection_observation` **28,598,272 B** (4.7%; 130,258 normalized rows), versus Oct 8 `23,461,888 B`: **+5,136,384 B**; `state_snapshot_history` **24,862,720 B** (4.1%; 445 PIT rows), unchanged. Derived+projection observation relation growth = **12,787,712 B**, about **95.2%** of the 13,434,880 B database-size increase between approximate older checkpoints. PostgreSQL physical relation allocation is not equivalent to incremental payload bytes or physically reclaimable DELETE bytes, and timing of baseline snapshots differs.

**Large growing artifact families:** `runtime_presentation_surface` **2,557 rows / 157,332,289 B `sum(pg_column_size(payload))` compressed JSONB datum**; 48 rows/~3,243,197 datum bytes in past rolling 24h; 96/~6,491,096 B in 48h. Earlier October 9 13:05 UTC checkpoint: 2,525 rows/155,170,202 B; since then +32 rows/+2,162,087 B compressed datums. Forecast **397 rows/63,057,386 B**, Simulation **295/27,491,129 B** (only 1 new row of each past rolling 24h). Player-future continuity **157/26,871,747 B**; supplemental Forecast **294/25,732,613 B**; Market value artifact **357/19,298,066 B**. Last 24h presentation appended 48 rows, indicating more generation-specific presentation records than 1 Forecast/1 Simulation; **not a license to skip publications or remove historical records**. `derived_artifact` had ~1,111 dead tuple estimate per `pg_stat_user_tables`, last autovacuum Oct 3; this is a diagnostic note only, not proof of safely reclaimable bytes or an authorization for VACUUM/DDL. Family logical datums are not isolated file sizes.

**Projection/acquisition storage:** 59 retained `projection_snapshot` records (all providers/horizons), `projection_observation` 130,258 rows, with **23,807 normalized rows** attributable to snapshots recorded in past 24h and **47,609** over 48h. Calendar Oct 9 (partial day at measurement): four CBS ROS saved revisions -> **8,457 normalized observations**; three Razzball ROS -> **7,890 observations**. Oct 8 eight CBS / five Razzball -> **31,262 normalized rows**. Each successful ROS position page acquisition uses 4 HTTP page requests per provider under current adapter code; saved revisions only imply minimum successful fetches (**>=28 position pages for Oct 9 partial-day**), not total attempts, retries, site changes, HTTP response bytes, or cache hits. Current retained revision/content fingerprint uniqueness cannot automatically distinguish provider numerical changes from retrieval time/version metadata; instrument stable normalized-content coordinates separately before claiming duplication.

**Accepted Tranche 1:** Exact deployed read-through did not change database storage, persistent history, Market PIT or SQL write behavior. One paired existing natural restore pattern: **11 -> 1 baseline full-payload reads**, **0 -> 11 metadata-only reads**, total SQL statements **11 -> 12**, logical JSON in read telemetry **10,679,328 -> 970,848 B** (minus **9,708,480 B / 90.9%**), summed SQL read elapsed **3,454.41 -> 798.84 ms** (minus 2,655.57 ms), baseline-call SQL p95 **498.05 -> 398.11 ms**. NOT physical storage recovered, NOT measured billed Supabase egress, NOT a proven improvement in browser full-journey latency or peak RSS. New DB-size increase is fully compatible with this read-only optimization.

**Free-tier urgency:** Database remains materially over allowance and continues growing; project currently `ACTIVE_HEALTHY`, SQL readable, inspected connection role writable, no evidence in this gate of quota-enforced read-only or failed governed writes. This is an **operational capacity warning requiring Management attention and regular read-only measurement**, not a demonstrated immediate need to upgrade. Avoid destructive 'cleanup' and production schema edits or artificial refreshes. If a required normal write fails with quota/SQLSTATE evidence, or projects become unhealthy/restricted, **stop and escalate to Management** with precise failure and smallest temporary paid intervention/rollback if proven necessary. The separate private Render/Supabase Storage validation is evaluating a structural alternative; do not infer its results from draft PR #441. Supabase egress and log-ingestion dashboard numbers are not provided live by these SQL measurements; never treat read-log JSON as billing transfer.

**Recommended NEXT narrow authorization, NOT IMPLEMENTED:** Instrument provider **EVENT/REQUEST/BYTES** inside existing adapter ownership only. Add bounded, low-cardinality structured logs/counters to each established HTTP transport (`src/fsffl/providers/{sleeper_live,sleeper_weekly_stats,cbs_live,razzball_live,fftoday_live,nfl_fantasy_live,in_season_projection_sources}.py`) and the existing acquisition owners (`src/fsffl/product/hosted_connect.py`; `src/fsffl/forecast/in_season_orchestration.py`; existing full-season Forecast adapter entry). For each actual request attempt capture: provider, endpoint *family/template* (never a private URL or league/player ID), season/week, forecast horizon, source_version, attempt/success/status/error class, raw response byte length **at the response.read() boundary** (decoded text length distinct), monotonic latency and bounded acquisition trace; aggregate per acquisition event: request count, total bytes, per-request latency p50/p95 and failures, normalized row count, stable content fingerprint distinct from retrieval timestamp, provider captured/effective freshness, and permitted initiator enum (`manual_refresh`, `saved_session_probe`, `connect`, `current_route`, `scheduled_authority`, `other`). Propagate initiator across worker threads explicitly when required; do not rely on implicit context propagation. Preserve existing pluggable `http_get_text/http_get_json` fixture seams and provider normalization contracts. **No tables, telemetry payload persistence, new controller, provider call, caching, model, or refresh-policy change.** Emit one compact aggregate event per acquisition plus only bounded necessary request metrics to avoid log ingestion amplification and leakage.

**Acceptance for a separately authorized instrumentation PR:** Same exact HTTP attempts and provider observations before/after including retry, timeout, 4-page success, 0-request cached/restored path, multi-league/tenant no identity leaks, source error handling; response byte counters equal observed raw bytes (distinguish Content-Length and decoded text); freshness timestamps and version/PIT unchanged; all Forecast/Current/Simulation/Value outputs and publication hashes invariant; no added GETs/POSTs or silent refreshes; comparable CPU/RSS, run-time p95 and log-output bytes; focused tests then stable-head full suite, exact deployed SHA and bounded natural hosted events (no forced provider refresh). **The measurement tranche saves zero provider calls or bytes by itself.** Its value is identifying defensible future provider-cohort reuse at correct provider/season/horizon/week/version scope. Defer cohort reuse, provider selection/weight changes, presentation content compactness and hybrid migration to separate acceptance gates.

**Status: MANAGEMENT GATE - PARALLEL CAPACITY MEASUREMENT COMPLETE; NO PRODUCTION CHANGE.**

## 2026-10-09 22:23 UTC — Read-only capacity handoff continuation: snapshot identity and acquisition measurement

Continuation of the separate read-only capacity task from live main `8700bcf86b00628de738a623aa23779ca27f22cf`; this is a documentation-only handoff and **not** permission for runtime/schema/retention/provider/refresh/deployment changes. Read-only Supabase SELECTs at Oct 9 22:22–22:23 UTC independently reproduce physical DB **604,040,339 B**, derived relation **407,797,760 B**, projection observation relation **28,598,272 B**, retained **5,699** derived artifacts, **59** provider snapshots and **130,258** observations; the earlier Oct 8->9 baseline growth is +7,651,328 B derived and +5,136,384 B observation (~95.2% of whole-DB +13,434,880 B). This is physical allocation, not a daily growth forecast or reclaimable/billed egress. Project `ACTIVE_HEALTHY` and inspected `transaction_read_only=off`; **no new write attempted**. Over the ~0.5GB Free allowance but no demonstrated malfunction or immediate mandatory upgrade; escalate on actual SQLSTATE/write failure/project restriction.

**New causal distinction, not record deletion:** 23,807 observations written in a rolling 24h are exactly 10 source revisions: 6 CBS / 12,771 and 4 Razzball / 11,036. They comprise **20,184** normal canonical Forecast-observation rows (8 revisions) plus **3,623** mapped-history rows (2 revisions), with differing metrics, evaluation periods, mapping metadata and coverage even where the provider/source_version label is identical. No repeated key *within* a snapshot. For Oct 7 onward full normalized-content hashes are unique across 24 CBS and 15 Razzball ROS revisions. Comparing only like-for-like canonical adjacent snapshots Oct 8–9, CBS 20,328/21,408 matched numeric values unchanged (94.96%); Razzball 15,974/18,742 unchanged (85.23%). Thus repeated complete snapshot materialization is real and may be wasteful, but materially revised/historically governed observations also exist; whole-publication C skip, snapshot deletion and premature provider-cohort reuse remain closed. Per-request triggers, provider-byte traffic and cache behavior remain **unmeasured**; code proves 4 pages per successful CBS/Razzball ROS acquisition, not actual total provider attempts. See the canonical Supabase workstream for full SQL and source-code boundaries.

**One proposed separately authorized implementation:** smallest existing-adapter **EVENT/REQUEST/BYTES** recorder (raw `response.read()` bytes, HTTP status/error/latency, endpoint-family, provider/season/horizon/week, bounded trigger classification and source freshness, stable normalized content identity, zero-request/cache status); one aggregate structured log per acquisition, no tables or payload logging, no provider/refresh/Forecast/Simulation/model change. Preserve injected HTTP getters and explicit thread-context across Sleeper concurrency. Require unit fixture parity for 4-page calls, errors/retries, bytes and zero-request path; confirm no extra upstream fetch, semantic/publication changes, memory/latency/log regression, one stable-head full suite and natural live observation only after Management GO. Budget ~1–3 focused engineering days, **zero immediate provider-call or storage saving**; its benefit is reliable attribution before any future cohort reuse. Roll back/disable for correctness, request-count, privacy, or resource regressions.

**Parallel dependency:** #441 is still draft/unmerged and owns private real Forecast/Simulation Pydantic+zlib/S3 integrity/latency/CPU/RSS testing; no real-results acceptance at this cutoff. Do not touch #439/#441 or reproduce experiments. Render workspace was not selected in this session, so no newly verified Render logs/deploy attribution; retain preceding accepted Render evidence. Commercial rights sequence remains develop/validate first, negotiate later. **Management gate: approve acquisition instrumentation ONLY or defer.**
