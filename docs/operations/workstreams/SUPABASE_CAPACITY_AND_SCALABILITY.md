# Supabase Capacity & Scalability Recovery

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
