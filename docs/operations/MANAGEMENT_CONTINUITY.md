# FSFFL NEXT — Management Continuity

Updated: 2026-10-08  
Authority: canonical durable record of Management direction, sequencing, deferred work, and roadmap changes across Management chats.

This document answers **where Management is going and why**.  
For **what is happening right now**, read [CURRENT_OPERATIONS.md](CURRENT_OPERATIONS.md).  
For exact tranche implementation evidence, read the linked workstream checkpoint.  
For the broad long-range capability plan, read [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) and [../FSFFL_NEXT_PRODUCT_PRIORITIES.md](../FSFFL_NEXT_PRODUCT_PRIORITIES.md).

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
