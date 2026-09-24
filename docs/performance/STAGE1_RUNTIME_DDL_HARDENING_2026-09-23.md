# Stage 1 Runtime-DDL / Schema Hardening Checkpoint

Date: 2026-09-23/24 UTC  
Base main SHA: `355b0c20457f2acf4f99e59257b274afb66598aa` (merged Stage 0 PR #185)  
Scope: Stage 1 only

## Objective

Eliminate schema/index/RLS creation from ordinary hosted runtime use while preserving the existing Behavioral persistence architecture and every model/product authority boundary.

## Re-fetch and collision result

Before code changes, main had advanced through Home readiness PR #186 to `7f2ff9e7...`. Stage 0 PR #185 remained green, clean and documentation/evidence-only, so it was merged as directed, producing current base `355b0c20457f2acf4f99e59257b274afb66598aa`. Render was live on #186 immediately before the Stage 0 merge deployment cycle.

Open PR #182 remains superseded Home work and touches presentation/webapp files, not the Behavioral Postgres adapter changed here. PR #160 is an older visual-system reference. Research branches are isolated. Stage 1 does not modify any of their model/research files.

## DDL trace and classification

Hosted PostgreSQL runtime DDL was concentrated in `PostgresBehavioralIntelligenceStore._initialize()`: CREATE SCHEMA, four CREATE TABLE statements, CREATE INDEX, and four ALTER TABLE ... ENABLE ROW LEVEL SECURITY statements. This constructor can be reached through hosted Behavioral store construction; process-level store reuse reduced frequency but did not make the boundary migration-owned.

The general `PostgresPersistenceStore` and the inspected historical/projection/state persistence adapters contain ordinary SELECT/INSERT/UPDATE persistence SQL and no schema DDL.

The local/test SQLite `BehavioralIntelligenceStore` still creates its local cache schema when a local SQLite store is constructed. That path is intentionally classified as local/test cache initialization, not hosted PostgreSQL request-time DDL. It is not used when `FSFFL_DATABASE_URL` selects the hosted Postgres store and is outside this bounded production-runtime change.

Canonical PostgreSQL schema establishment already exists in governed migrations:
- `20260909_004_durable_behavioral_evidence.sql`
- `20260909_005_behavioral_runtime_context.sql`
- `20260910_007_enable_rls_new_private_persistence.sql`

## Change

`PostgresBehavioralIntelligenceStore._initialize()` is now read-only validation. It queries PostgreSQL catalog state to require all four Behavioral relations, verifies RLS is enabled on each, and verifies the governed `behavior_event_family_time_idx` index exists. Missing schema, missing index, or disabled RLS raises `RuntimeError` with a migration-required message.

No runtime code creates, alters, drops, or repairs PostgreSQL schema. Governed migrations are the sole creation/change authority. The existing shared hosted store and startup prewarm remain; their comments now describe validation rather than deploy-before-migration bootstrap.

## Regression proof

Focused tests prove:
- repeated Postgres Behavioral store initialization executes catalog SELECTs only and zero DDL;
- missing required relation fails closed;
- disabled RLS fails closed;
- missing required index fails closed;
- static regression rejects CREATE TABLE / CREATE INDEX / ALTER TABLE bootstrap SQL from the Postgres runtime adapter.

Existing Behavioral/persistence tests remain part of full CI.

## Timing evidence

Stage 0 historical management evidence recorded 214 repeated Behavioral CREATE INDEX calls and roughly 89 minutes cumulative waste. That is retained as historical before evidence, not relabeled as a current measurement.

No direct external database timing surface is available from the Render workspace: Render hosts the web service but no Render Postgres resource. Stage 1 therefore does not manufacture an after-latency statistic. The deterministic structural delta is stronger than a synthetic timing claim: hosted runtime DDL statements at this boundary change from schema/index/RLS mutation to zero, replaced by two read-only catalog validation queries at store construction. Live post-merge timing can be sampled safely after deployment if management requests it; connection/pooling optimization remains Stage 3 and is not pulled forward.

## Authority and cost audit

No Forecast, Simulation, Value/Intrinsic, Decision, Search, Team Utility, Behavioral inference/owner authority, evidence identity, provenance, cache identity, or product presentation semantics changed. Simulation remains 50,000 runs. No paid compute, Render upgrade, database upgrade, or new infrastructure was introduced.

## Files changed

- `src/fsffl/behavioral/postgres_store.py`
- `src/fsffl/product/behavioral_runtime.py`
- `src/fsffl/product/persistent_webapp.py`
- `tests/test_durable_behavioral_store.py`
- `tests/test_behavioral_runtime_ddl.py`
- this checkpoint and machine-readable evidence

## Stop condition

Stop after Stage 1 is durable and green. Do not begin Stage 2 or later work without management authorization.
