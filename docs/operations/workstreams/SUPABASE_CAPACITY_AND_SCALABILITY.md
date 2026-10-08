# Supabase Capacity & Scalability Recovery


## 2026-10-08 — Tranche B live acceptance closeout; Management review

**Worker recommendation: ACCEPT Tranche B only**, pending explicit Management promotion. Tranche A previously ACCEPTED by Management. Stable-tested PR #434 head `48d78375cce957dca5faee71a8c39108c3e006a2`, full-suite run `37805666770` **2,248 passed / 1 warning / 87.03s**, exact-head verified. Squash merge **`3f079ca6df48fbae3e6adb83fa3df877dc05f1b1`**, Render deployment **`dep-db3ruiqjnfac738ibiag`** LIVE on Free service `srv-dae6k7vqj5pc73af7bt0`.

**Bounded batching / preserved contract.** `src/fsffl/persistence/postgres.py` adds `append_market_value_snapshots` using up to **300 deterministic ordered VALUES** rows per transaction, original exact five-part conflict key, `ON CONFLICT DO NOTHING`, and earliest input lineage on within-chunk collisions. Individual append remains; `src/fsffl/persistence/session.py` routes published Market observations through batch when supported and retains individual-writer fallback. No PIT, provenance, as_of, recorded_at, value, scale/context, tenant, first-writer or atomic publication semantic changes. No schema, migration, provider refresh experiment or model modifications.

**Automated and backend gates.** Focused tests on exact head and full suite passed. Deterministic 540-record fixture: 540 original SQL statements versus 2 batch statements; exact row, value, timestamp, context, lineage equivalence and rerun idempotence; duplicate conflicts inside/between chunks, partial second-chunk failure with first committed chunk preserved, 1,201-input deterministic chunk bound and Python memory <20MiB. Independent isolated real PostgreSQL two-conflict VALUES rollback probe passed with original first-writer retained during subtransaction, and **0 residual probe rows** afterwards. Not a Render-credential write test by itself.

**Actual hosted post-deploy evidence.** Natural startup/restore with actual pooled Render credentials produced two new `pg_stat_statements` market INSERT SQL shapes: **300 and 235 VALUES records; 1 execution each** (`224.12ms` + `127.64ms` server execution), **0 new rows** due idempotent first-writer conflicts. Legacy one-row statement count **unchanged at 329,447 calls**. This proves actual hosted B path; measured SQL attempt savings against legacy writer's 535 calls: **535 -> 2 (-99.626%)** for this workload. Market table **169,384 retained rows**, PIT States **444**, latest recorded market observation unchanged; no history or accepted lineage removed or overwritten.

**Matched startup restore:** Tranche A 14:49 UTC vs B 16:07 UTC, identical 25 persistence reads in same order and **22,318,183** logged serialized bytes. Restore 7,987.60 -> 8,114.12ms (small variance); persistence-read p50 344.51 -> 297.18ms, p95 1,200.87 -> 1,107.31ms. Combined derived-artifact write phase 11.920 -> 1.867 seconds (cannot assign the full duration difference solely to batching). Forecast/Simulation/Value complete, product readiness full; no inspected B app warnings/errors. B peak process RSS **346,505,216** bytes versus A **335,355,904** (+11.15MB), below budget **429,496,720** and hard limit **536,870,900**. Aggregate Supavisor 3-minute startup window A auth 5/term 2/log events 10/message chars 453; B auth 2/term 1/events 4/message chars 179. This is project-wide, not app-only connections or billed log bytes. Pool checkout/wait/error counters were not available in Render logs; no numerical claim is made for them, or for database SQL p95 under broad traffic.

**Critical capacity limitation:** allocated PostgreSQL physical bytes `584,715,411` pre-B and `586,435,731` after normal B startup; still above 0.5GB Free quota. Tranche B corrects prospective market SQL amplification, not existing physical storage. No cleanup, migration, new model, refresh policy, paid Supabase, Career #405 PR2, or **Tranches C-F** is authorized by this closeout. Management must separately approve any next tranche or capacity reclamation. Live runtime remains B merge SHA, regardless of subsequent docs-only commits.


## 2026-10-08 — Management ACCEPTS Tranche A; authorizes B ONLY (active draft)

**Authorization.** Management explicitly ACCEPTED Tranche A pooled transport and closed Gate 2 on its naturally occurring hosted publication evidence. Accepted live identity: PR #433 tested `8d3c17cdf0f9f81cc4360f3c85f76845c151cbe8` (2,240 tests), merge `1c5b5325791cddaf49d35d372270a9aba0586afb`, Render deploy `dep-db3qq4vlk1mc73cj3910`. Batching alone is now the P0 execution priority. **Tranches C-F and Career #405 PR2 remain paused.** No paid tier, deletion, migration, refresh policy, provider experiment, or model/analytics work.

**Tranche B implementation:** `work/supabase-tranche-b-market-batching-20261008`, draft [PR #434](https://github.com/jderhagopian-stack/fsffl-next/pull/434), based on main `29d2395c213829ed9fbcbf648d552c96089f0c05`. Only three runtime files are affected: (1) immutable `MarketValueSnapshotRecord` and batch PersistenceStore protocol; (2) `PostgresPersistenceStore.append_market_value_snapshots` performs deterministic <=300-row multirow VALUES, parameterized, each bounded chunk in one transaction, exact original five-column `ON CONFLICT DO NOTHING` and preserves earliest lineage for duplicate keys; (3) `persist_runtime_snapshot()` routes published market estimates through batch when supported, falling back to the individual method for legacy/custom stores. Same per-estimate mean/time/scale/market_context/evidence sources, unchanged publication order. No schema or market history rewrite. Existing individual append remains unchanged. No retry after SQL execution or implicit batch rebuild.

**Validation plan:** focused 540-row simulation of SQL rows comparing legacy 540 separate statements with two <=300-row multirow statements, first-writer conflict within and across chunks, rerun idempotence, partial-failure first-chunk durable/second-chunk rolled back, full value/timestamp/lineage equality, deterministic SQL, 1,201-row bounded memory, and actual caller publish_context/legacy-fallback tests. These prove mocked DB SQL semantics, not yet live backend performance. One stable-head full suite only after focused CI and final draft candidate. No deployment before exact-head gate. Hosted acceptance must not trigger provider refresh or broad publication; rely on natural live market writes where available, additionally bounded rollback-only database checks if safe/needed. If actual pooled batch cannot be verified without forbidden heavy work, return an explicit Management gate rather than claim success.

**Before B (read-only snapshot Oct 8 15:57 UTC):** Supabase allocated `584,715,411` bytes (~558 MiB), `169,384` retained market_value_snapshot rows, `5,617` derived_artifact rows, `444` State history records. Cumulative historical simple `INSERT market_value_snapshot` shape: `329,447` calls; `169,385` rows affected (cumulative statistics may exceed retained counts); mean SQL execution 0.939 ms, total 309.4 sec. Hypothesis at ~540 estimates/valuation: legacy 540 SQL statements -> 2 batch SQL statements (99.63% reduction in SQL statements), BEFORE accounting for pool/transaction overhead; only measured in fixture until verified live. Cumulative counters do not directly reveal current rate. **Physical ~585 MB storage remains over Free Plan quota; B does not reclaim it.** No retention/compaction is authorized.

**Status:** DRAFT IMPLEMENTATION / focused CI; production still **Tranche A**, no B deploy or data changes; no C-F approval.


## 2026-10-08 — Tranche A live hosted-write acceptance reconciliation (Management review; B-F NOT AUTHORIZED)

**Recommendation: ACCEPT Tranche A transport / close Gate 2 natural-write proof.** No manual operator telemetry POST is necessary. Live host identity: PR #433 tested head `8d3c17cdf0f9f81cc4360f3c85f76845c151cbe8` (stable suite `37781664575`: 2,240 passed, 1 warning); squash merge **`1c5b5325791cddaf49d35d372270a9aba0586afb`**, Render deploy **`dep-db3qq4vlk1mc73cj3910`** live on service `srv-dae6k7vqj5pc73af7bt0`, Free one instance / one Uvicorn worker. Protected DB transport independently confirmed by Management: Supavisor shared session pooler on port 5432; no secret disclosed. Pooled mode is default absent explicit legacy override; no environment change in deployment. The opening pool itself did not emit a counted checkout metric in available logs.

**Gate 2 substitute proof (stronger than a telemetry-response-only assertion):** same hosted Render startup/restore `restore_id=325ad471-a88a-4cc3-86b9-574dc882e69a` logged phase `persistence.derived_artifact_encode_and_write` (finished 14:51:49.022 UTC) and `persistence.atomic_manifest_and_pointer` (finished 14:51:49.641 UTC), while independent Supabase reads identify saved artifacts dated 14:50:09-14:51:49 UTC: 8 `runtime_presentation_surface`, 1 presentation manifest, current Forecast/Simulation/Market evidence, published generation, last-good user and league bundles, player-future continuity. Normal live workload supplied writes; no probe was injected. `FSFFL_TRANCHE_A_GATE2_20261008_PR433_8D3C17_C7A91F3E` has **0** matching telemetry rows, so no delete or clean-up action is required. No artificial refresh/analytics change initiated by the acceptance investigation. Market snapshot rows 169,384; PIT State rows 444 in the observed aftermath. Projection observation count increased from 91,563 to 96,837 in natural runtime activity, NOT attributable to the probe (there was none).

**Matched 10-minute Supavisor startup-centered windows:** previous release 2026-10-07 23:58-2026-10-08 00:08 UTC versus deployed Tranche A 2026-10-08 14:49-14:59 UTC: auth **468 -> 5 (-98.93%)**, terminations **451 -> 4 (-99.11%)**, total Supavisor log events **1,078 -> 14 (-98.70%)**, event-message characters **47,761 -> 830 (-98.26%)**. Supavisor events are across project clients, not explicitly app-only connections or billed log bytes; matched startup restores increase confidence but do not establish perfect workload controls. Do not extrapolate this to all dayparts or traffic.

**Matched persisted restore workload:** both startup restores performed **25 reads in the same artifact order**, each totaling **22,318,183 logged serialized payload bytes** (not actual wire transfer bytes). Legacy `restore_id=a509f688-23f6-4c0e-a9b5-b66e71a3de8a`: ready in **8,699.28 ms**, read p50 **354.37 ms**, read p95 **1,207.12 ms**, process peak RSS **343,904,256 bytes**. Pooled: ready in **7,987.60 ms**, read p50 **344.51 ms**, read p95 **1,200.87 ms**, process peak RSS **335,355,904 bytes**, `rss=328,314,880` at full startup readiness; underlying hard limit **536,870,900 bytes**. The new host also logged `forecast=True simulation=True value=True complete=True` and product readiness `full`. Zero app warning/error logs in selected post-deploy 14:49-15:25 UTC window; Supabase inspected connection-error terms absent.

**Bounded acceptance and limitations:** This is real live startup saved-context restore and persistence-read evidence, not a newly issued authenticated browser GET; browser saved-session physical view was NOT independently exercised in this checkpoint. User-visible startup behavior and measured p95 are not broad load guarantees. Internally instrumented app-created connection counts, ConnectionPool opens/checkouts/waits/timeouts and transaction retries are **not exported** on this tested head; only bounds (min=0,max=3,wait=5s,max idle=75s,lifetime=720s), absence of observed pool-timeout/errors, and Supavisor aggregate event counts are available. No pre/post **database SQL execution p95** was captured; p95 values above are app-side persistence-read timings. The unchanged ~22.32 MB restore payload means Tranche A does not address Tranches D/E. Supabase physical database size remained above Free quota (~582,864,019 bytes at the observed inspection). Never claim the 70-95% target as an app-created connection counter; only the observed project-wide auth reduction is measured.

**Management gate disposition:** Recommend **ACCEPT** Tranche A as a bounded transport correction that has exercised actual hosted writes and matched restore reads, with a measured >98% reduction in startup-window Supavisor auth/log churn and no observed memory or persistence regression. Before extending this improvement to sustained traffic or marking physical saved-session acceptance, obtain a single no-refresh authenticated Safari saved-session confirmation and/or future counters where proportionate; these are residual observability/physical-acceptance notes, not grounds to repeat artificial Gate 2 POST. **Tranche B is NOT AUTOMATICALLY AUTHORIZED**. Management may separately evaluate row-wise idempotent market-write batching next using the Gate B design, while preserving PIT/lineage. No new code/deploy, billing upgrade, retention cleanup, migration, refresh policy, Career #405 PR2, or B-F work performed in this reconciliation.

**Standing regression boundary after Tranche A acceptance:** bounded connection reuse is now the accepted hosted persistence transport contract. Future persistence, publication, restore, or background work must not reintroduce one-connection-per-operation behavior or silently bypass the pooled adapter. Preserve the focused pool regressions in CI. For future changes that can affect this boundary, compare matched-workload connection/authentication/termination/log behavior, pool waits/timeouts where observable, affected persistence latency, errors/retries, and peak RSS against the latest accepted baseline. If connection churn materially regresses under comparable work, reopen this narrow resource gate before promotion. The legacy transport flag remains an emergency rollback path, not an alternate normal operating mode.

**Observability follow-up:** current acceptance does not export app-only pool opens/checkouts/waits/timeouts. Add low-volume aggregate counters only when proportionate to an authorized tranche; do not create high-volume per-operation logging merely to observe the pool.



## 2026-10-08 — Tranche A draft implementation checkpoint / pre-stable-head gate

- **Main baseline:** `55f9ce5da494466a107f4664f06385935c7b2ff7`; branch `work/supabase-tranche-a-pooled-connections-20261008`; draft PR **#433**. Latest implementation/documentation branch head before this checkpoint: `2f2157a9659fdb6272ce79c9ab26b4c2b9cc2dc3`; the new checkpoint commit becomes the exact next head.
- **Scope changed in draft:** `src/fsffl/persistence/postgres.py` only alters `_connect()` transport and adds `close()`; all existing SQL and `with self._connect()` transaction sites are unmodified. `pyproject.toml` adds `psycopg-pool>=3.2,<4` to hosted extras, `src/fsffl/product/persistent_webapp.py` closes the global runtime adapter on FastAPI shutdown, `.github/workflows/ci.yml` includes new Tranche A focused regressions; `tests/test_postgres_connection_pool.py` covers lazy bounded initialization, concurrent reads/writes/tenant parameters, rollback isolation, checkout timeout, stale-check preflight, shutdown/restart, and legacy-equivalent telemetry statement/parameters.
- **Pool settings:** min_size=0, max_size=3, wait=5s, max_waiting=12, idle=75s, max lifetime=720s, reconnect_timeout=5s, 1 background maintenance worker. `check=ConnectionPool.check_connection` tests stale connections before a caller executes its SQL. No replay of attempted writes. Disabled prepared statements maintain compatibility with session or transaction Supavisor mode. `FSFFL_PERSISTENCE_CONNECTION_MODE=legacy` retains prior direct-connect semantics (requires restart/redeploy to change).
- **Focus validation:** Draft PR `CI / test` **passed** run `37780997029` on earlier head `1c5b5d603d88f467cc53769780c2cb125d9853f6`. The branch then added a concurrent real-adapter read/write isolation test and operating checkpoints; latest-head focused run must pass before marking ready. Full suite intentionally **not run** on draft. No production work/deploy.
- **Deployment/observability gate:** Render has one Free instance / single Uvicorn process (no worker flag), underlying PostgreSQL max_connections=60 and current observed active=6. Recent Supavisor logs show postgres session-mode pool, but Render credential URL has not been directly inspected. Render connector has **no selected workspace**; a workspace selection from Management is required to access hosted log/metrics and safely complete a Render-credential rollback-only telemetry acceptance. Do not make an inferred host-credential acceptance claim, deploy without a viable acceptance path, or perform a discretionary refresh.
- **Acceptance requirement:** one stable full-suite run at final ready PR head; exact diff/identity review; hosted rollback-only telemetry insert+no residue, comparable Supavisor auth/termination/log bytes, app-connection attempts, p95 persistence/restore and peak RSS; stop if unsafe or benefit does not materialize. If the testing route is inaccessible, preserve the draft PR and return to Management for workspace/acceptance resolution.
- **Not authorized:** Tranches B-F, Career #405 PR2, billing, migrations, historical deletion, new refresh, provider retrieval, analytical/model updates, or lifecycle rewrite.

## 2026-10-08 — Tranche A implementation start (Management-authorized, NOT DEPLOYED)

- **Management scope:** bounded PostgreSQL connection ownership/reuse ONLY. Supabase stays Free; B-F and Career #405 PR2 remain paused. No SQL, migrations, retention, refresh, value, model, or lifecycle changes.
- **Starting main:** `55f9ce5da494466a107f4664f06385935c7b2ff7`. **Branch:** `work/supabase-tranche-a-pooled-connections-20261008`. Draft PR/testing/deployment status: not yet started.
- **Live before:** Render `srv-dae6k7vqj5pc73af7bt0` on `dep-db3dp1d9fdbs73dbo7eg` / `b43fa8690fb6fe3dc4c28e9b203c51fd5a860480`, one free instance; Uvicorn start command has no `--workers` (one worker per instance). PostgreSQL `max_connections=60`, three reserved and six observed active at the read-only check. Historical and recent Supavisor logs show `mode: :session` for role `postgres`, but the exact encrypted `FSFFL_DATABASE_URL` transport endpoint from Render has not been directly inspected; verify at hosted acceptance, don't claim it is proven by log strings alone.
- **Verified transport mechanism:** `src/fsffl/persistence/postgres.py` currently calls `psycopg.connect` for every individual `with self._connect()` SQL operation. Existing `psycopg_pool.ConnectionPool.connection()` API commits on success, rolls back on exception and returns the connection; connection health-check can discard stale connections before caller SQL.
- **Proposed bounded parameters:** lazy per-adapter/process pool, min_size=0, max_size=3, timeout=5s, max_idle=75s, max_lifetime=720s; explicit shutdown; session/transaction-compatible disabled prepared statements; legacy mode escape `FSFFL_PERSISTENCE_CONNECTION_MODE=legacy`.
- **Pre-deploy gates:** focused concurrency/isolation/rollback/timeouts/disconnect/shutdown tests, stable-head full-suite on ready PR, exact dependency and pooler mode compatibility, RSS and connection headroom; deploy only after stable candidate acceptance. Hosted rollback-only telemetry test and measured comparable windows must pass before marking tranche accepted. If credentials/observability inaccessible or risk elevated, stop and report to Management without claiming production acceptance.
- **Frozen:** every existing SQL statement, publication/pointer ordering and tenancy, PIT lineage, replay, last-good, model authority, and explicit no-silent-heavy-refresh saved-session policy. Baselines: Gate A forensic and Minimal Write-Capability PDFs; Gate B design (15 pages).


Updated: 2026-10-08  
Status: **P0 OPERATIONAL PRIORITY — GATE A AUTHORIZED; PRODUCTION REMEDIATION NOT YET AUTHORIZED EXCEPT SEPARATE NARROW EMERGENCY BRIDGE**

## Management objective

Restore safe operation, identify the mechanism behind the late-September Supabase resource inflection, and redesign persistence/egress behavior so FSFFL NEXT can scale to thousands or tens of thousands of leagues without multiplying shared work by raw league count.

A temporary paid Supabase tier may be used only as a **short-lived access/headroom bridge** if required to regain normal operation. It is not evidence that the present architecture is acceptable and must not replace root-cause correction, retention design, or scale validation.

## Current incident evidence

- Supabase Free Plan database allowance: 0.5 GB per project.
- Observed FSFFL NEXT database size: **568.16 MB**, with Supabase reporting the project over quota and Management observing the project locked/read-only.
- Billing-cycle log ingestion: **1.12 GB** against 1 GB included.
- Egress was low through most of September, began rising materially around 2026-09-23..25, and showed a clear step-change around **2026-09-26/27**, followed by repeated daily volumes around roughly 0.5–2 GB.
- Log ingestion shows a similar late-September step-change, strengthening the hypothesis of increased runtime/persistence/read/write/connection activity rather than storage retention alone.
- Prior read-only inspection found approximately:
  - `derived_artifact`: 376 MB, including roughly 369 MB TOAST;
  - `market_value_snapshot`: 114 MB;
  - `state_snapshot_history`: 24 MB;
  - `projection_observation`: 19 MB.
  The two largest relations total roughly 490 MB. This is **not** permission to delete them.

## Immediate sequencing

This workstream temporarily supersedes Career Coverage #405 PR2 as the active operational priority. PR1 is complete and preserved. PR2 remains authorized in principle but **paused from implementation/promotion** until the Supabase Gate A audit/design determines that its dynamic materialization plan will not amplify the current database/egress failure mode.

Do not launch new persistence-heavy features, broad rematerialization, retention cleanup, migrations, destructive SQL, or scale simulations while the incident is unclassified.

## Phase 0 — incident containment

Objective: regain and preserve enough operational headroom to inspect safely without confusing temporary capacity relief with remediation.

1. Record exact Supabase project status, quota state, database size, billing-cycle timestamps, live deployment identity and repo head before intervention.
2. Preserve current database/evidence and identify whether writes/refreshes are actually rejected versus only quota-flagged.
3. If Management uses a paid tier to regain access, record it explicitly as a **temporary emergency bridge** with before-state evidence. Do not infer that a larger quota resolves the architecture.
4. Avoid destructive cleanup. Any emergency data reduction requires a separately itemized action, preservation/backup path, expected reclaimed bytes, rollback and post-action verification.
5. Keep the current resource curves visible so a paid upgrade does not hide continuing growth.

## Phase 1 — targeted read-only audit

Objective: produce a defensible resource ledger and identify the late-September inflection.

Use **2026-09-24 through 2026-09-29** as the first forensic comparison window, with **2026-09-26/27** as the primary observed breakpoint. Correlation is not causation.

Measure:
- daily/hourly egress before and after the breakpoint;
- bytes and request counts by table/payload family/surface where available;
- derived-artifact generation/write rate and repeated read rate;
- market snapshot creation/read rate;
- publication-generation count and retained payload sizes;
- State/history reads, restore reads and last-good reads;
- connection/authentication/termination churn;
- hosted Render traffic versus development/CI/manual audit traffic;
- identical or semantically identical payloads repeatedly fetched in the same process/publication;
- log volume by logger/path/workload;
- database table/index/TOAST size, dead tuples and growth by timestamp/generation.

Cross-reference deployments/commits around the breakpoint, especially persistence/publication/lifecycle changes, without presuming they caused the usage increase.

Deliverable: quantified before/after resource ledger; causal hypotheses with confidence; consumer/dependency map; immediate safe-headroom requirement.

## Phase 2 — architecture and retention design

Objective: specify the permanent fix before cleanup.

Define the widest safe semantic ownership/reuse scope for every expensive stored/read artifact:

`global/provider evidence → model/training authority → scoring/rules signature → lineup/team-count signature → exact league State → publication generation → team/user presentation context`

Required design:
- no unnecessary league/user key in shared upstream cache/artifact identity;
- current-head versus immutable PIT history versus last-good/rollback/replay responsibilities;
- bounded retention/compaction policy by artifact family and consumer;
- deduplicated/shared payload references where mathematically and privacy-safe;
- metadata-first reads and no repeated large-payload download merely to determine freshness;
- coalesced publication writes and reads;
- bounded connection/log behavior;
- tenant-private State isolation;
- no reintroduction of the P0 lifecycle complexity already removed.

Deliverable: retention matrix, target read/write architecture, quantified expected savings, migration/rollback plan, and capacity model.

## Gate B — mandatory Management pause

No production-modifying cleanup/remediation proceeds from Gate A alone.

Management must review:
- exact proven cause(s);
- affected tables/artifacts/readers/writers;
- bytes/request/log savings expected;
- PIT/replay/last-good preservation guarantees;
- downtime/locking/compute/memory risks;
- rollback;
- tests and hosted/physical acceptance.

Only then authorize itemized Phase 3 changes.

## Phase 3 — controlled stabilization

After Gate B only:
- correct proven redundant writers/readers/materialization/polling/logging;
- retire/archive only explicitly approved materializations;
- reclaim physical storage using an operation selected with lock/downtime consequences understood;
- verify database size, egress, logs, latency and model/product correctness before/after.

## Phase 4 — scale validation

Do **not** instantiate 1,000 or 10,000 live leagues on current infrastructure.

Measure real per-scope costs, bounded representative fan-out/concurrency, reuse ratios, bytes/action, bytes/publication and changed-subject rates. Project resource envelopes at 1, 100, 1,000 and 10,000 leagues. Expensive shared stages should scale primarily with unique semantic signatures and changed evidence, not raw league count where reuse is valid.

## Non-negotiable safeguards

- Preserve point-in-time State, market evidence, lineage, accepted research artifacts, immutable replay inputs, audit trails and required last-good generations unless Management explicitly approves a replacement preservation mechanism.
- Do not change Career/Y4–Y7 authority, #370 Dynasty economics, Current semantics, Foundation 4 or Simulation 2.0 as a storage side effect.
- Do not use a paid service tier as a substitute for efficient architecture.
- Do not reopen P0.1–P0.6 lifecycle/presentation plumbing absent evidence that a surviving mechanism is directly responsible.
- Prefer fixing the mechanism consuming resources over deleting the evidence it produced.

## Acceptance

This workstream is complete only when:
1. the late-September resource inflection is causally classified to a useful engineering level;
2. normal operation has material headroom;
3. redundant egress/write/log behavior is demonstrably reduced;
4. retained-history policy is explicit and auditable;
5. the application preserves PIT/replay/last-good and analytical authority;
6. scale projections demonstrate non-naïve league multiplication;
7. current limits and upgrade triggers are documented.
