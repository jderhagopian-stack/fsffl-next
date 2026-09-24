# Stage 0 Performance Baseline and Architecture Audit

Date: 2026-09-23/24 UTC  
Workstream: Free-tier performance hardening  
Base `main`: `f4a46f7fe5651192dc5a5e2a7d648006ea635ff7`  
Render service: `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`)  
Live Render deploy: `dep-daq6kfgu01pc73f0vg90`  
Live SHA: `f4a46f7fe5651192dc5a5e2a7d648006ea635ff7`  
Runtime tier: Render Free, Virginia, one instance, Python/Uvicorn  
Recurring infrastructure change: none  
Paid-compute experiment: not authorized and not performed

## Scope and authority

This checkpoint closes Stage 0 only. It records the current performance baseline and existing reuse/job architecture before optimization. It does not alter Forecast, Simulation, Value, Intrinsic, Decision, Search, Team Utility, Behavioral authority, evidence identity, provenance, fail-closed behavior, or the canonical 50,000-run Simulation.

## Live configuration verified

Render is connected to `jderhagopian-stack/fsffl-next`, branch `main`, auto-deploy on commit, Free plan, one Virginia instance. Build command is `python -m pip install -e '.[web]'`; start command is `uvicorn fsffl.product.persistent_webapp:app --host 0.0.0.0 --port $PORT`. Render's workspace reports no Render-hosted Postgres instance; application persistence is therefore external to the Render workspace and must be treated separately in Stage 3 rather than guessed.

The service's latest live deploy matches current main exactly. The immediately preceding deploy was `be856a2b08869ec6529fec7fd286fe989803f168` (Home North Star); live advanced to `f4a46f7f...` after PR #184 Home presentation cleanup.

## Current measured live observations

These are observed wall-clock application timings from Render logs on the current/adjacent live deployment, not synthetic estimates:

| Path/work | Cold/warm evidence | Observed time | Notes |
| --- | --- | ---: | --- |
| `GET /api/product-context` | first useful/restored request | 3.103-3.704 s | Later same-session request observed at 0.013 s |
| `GET /api/my-team` | mixed cold/warm | 0.004-0.497 s | Demonstrates large reuse benefit |
| Market structural catalog | cold miss | 0.896 s | 663 candidates |
| Market structural catalog | exact warm hit | 0.000 s logged | Existing exact-runtime cache |
| `GET /api/opportunities/workspace/quick` | cold quick composition | 1.453 s | Internal quick timing 1.354 s |
| Trade analysis | cold bounded analysis | 14.003 s | roster_decision=13.007 s; state validation=0.097 s; package economics=0.005 s; lineup/legality=0.895 s |
| Full Market workspace | cold miss | 15.068 s | Internal workspace 14.860 s; dominated by Trade/Decision work |

Render metrics around the current deploy show roughly 178.5 MB resident memory on the active instance and very low idle CPU (~0.0013 CPU). Render's HTTP latency/count series was empty for the queried window, so request-log timings are the authoritative Stage 0 live evidence for those paths.

A fresh 50,000-run Simulation was not observed in the available current live log window. Stage 0 therefore does **not** relabel the historical ~87.8 s total / ~86.8 s kernel observation as a current measurement. The existing benchmark harness remains the reproducible source for a fresh-kernel measurement and must be run on the same Free runtime before any Stage 5 before/after claim.

## Historical management baseline retained, explicitly labeled historical

The 2026-09-22 management review recorded: fresh 50k Simulation ~87.8 s total / ~86.8 s kernel; fast Trade ~12-36 s; My Team/read surfaces ~0.006-14.5 s; exact repeated Simulation ~1-2 s; and 214 repeated Behavioral CREATE INDEX calls with ~89 minutes cumulative waste. These values remain comparison evidence only until remeasured on the current exact runtime.

## Existing architecture audit

### Reuse and identity — IMPLEMENTED / strong foundation

- `league_material_fingerprint(...)` hashes substantive league facts while ignoring retrieval/provenance timestamp churn.
- `forecast_input_fingerprint(...)` narrows Forecast reuse to the canonical inputs Forecast actually consumes.
- `PrivateBetaRuntimeStore.set_league_state(...)` reuses a complete intelligence bundle when the league material fingerprint is unchanged and supports narrower Forecast reuse when only non-Forecast state changed.
- `PersistentPrivateBetaRuntimeStore` persists canonical State and exact derived Simulation artifacts, restores matching bundles after process restart, and uses strict model/input/state identity.
- Scenario cache persists exact 50k Simulation outputs with state/model/input fingerprinting and strict compatibility checks.
- Market structural candidate search and workspace composition have exact-runtime caches; current live logs demonstrate cold miss then exact hit behavior.

No competing fingerprint/cache framework should be introduced.

### Persist-first restore — PARTIAL

Durable State and exact Simulation restore exist, and current live evidence shows a first product-context request around 3.1-3.7 s followed by warm reads in milliseconds. However, not every surface has yet been audited against the full Stage 2 contract: last-good matching intelligence -> immediate render -> explicit freshness/readiness -> independent refresh -> atomic replacement. Stage 2 remains necessary.

### Background jobs — PARTIAL

`IntelligenceJobCoordinator` and hosted connect/background coordinators provide queued/running/completed/failed states and asynchronous in-process execution. Intelligence phases are timed. Job state itself remains process-memory scoped; process restart therefore loses job lifecycle state. Stage 6 must extend this framework rather than create another coordinator.

### Runtime DDL / Behavioral bootstrap — PARTIAL and Stage 1 target

Behavioral Postgres bootstrap is idempotent and shared/prewarmed at hosted process startup, which is materially better than repeated construction. But schema/index/RLS bootstrap logic still exists in application runtime code. Historical evidence recorded repeated CREATE INDEX work. Stage 1 must audit every ordinary path and move creation to governed migration/startup validation as appropriate, with a regression proving repeated ordinary use performs no DDL.

### Database access — UNKNOWN / evidence required

Render has no Postgres resource in the selected workspace. The app uses psycopg persistence from environment configuration, consistent with an external/Supabase-style database, but Stage 0 does not infer its plan, pooler, connection latency, or exhaustion risk. Stage 3 must measure this directly before changing connection behavior.

### 50k Simulation kernel — IMPLEMENTED fidelity, optimization MISSING

The canonical default remains 50,000 runs with governed seed/model identity. The kernel still performs the Monte Carlo season loop primarily in Python. Exact persisted reuse is high leverage, but no Stage 5 kernel optimization has been applied here. Profile first; preserve run count, distributions, inputs, and parity contract.

### Progressive delivery — PARTIAL

Quick Market delivery, background intelligence, cached exact evidence, and status/readiness concepts already exist. A single durable cross-restart job/result contract is not yet complete, so Stage 7 remains downstream of Stage 6.

## Collision audit

At Stage 0 closeout, stale/open product PR #182 still targets Home files but its accepted successor work is already merged through PR #184. PR #160 is an older North Star visual-system reference branch. Research PRs remain isolated. This Stage 0 branch changes documentation only and does not touch Home, Franchise, League Atlas, Market presentation, Forecast/Value/Decision authority, or research files.

Before every later stage, re-fetch main and active PR filenames again. If an active product PR touches a file required by performance work, stop and reconcile rather than race it.

## Repeatable benchmark matrix

The same matrix is the contract for Stage 0 baseline completion and Stage 8 rebenchmark. Every executable run must record timestamp, main/head SHA, runtime tier, state/material fingerprint, relevant model versions, simulation count, cache hit/miss, cold/warm classification, median/p95 when multiple runs are reasonable, and separate DB/provider/app/Simulation time where observable.

1. Restore / first useful State: process-cold restore followed by `/api/product-context`; record persisted-state lookup and total.
2. Cached Home: exact unchanged State, repeated Home command-center composition; no model launch.
3. Cached Franchise/My Team: exact unchanged State; cold composition then repeated warm reads.
4. Cached League Atlas: exact unchanged State; cold composition then repeated warm reads.
5. Fast Trade: fixed governed package and exact State; record state validation, package economics, lineup/legality, roster/Decision, finalize, total.
6. Fresh 50k Simulation: use `scripts/benchmark_simulation_performance.py`; record setup/kernel/post-processing/total, model version, seed, run count, memory where available.
7. Exact cached Simulation: same authoritative identity immediately after fresh run and again after process restart; verify identical persisted result identity and retrieval time.
8. Bounded Search/Opportunity: quick and full workspace; record catalog cache miss/hit, candidate count, Decision budget and total.
9. Intelligence refresh: record Forecast, Simulation, Value and persistence phases plus total; distinguish provider/network time.
10. DB-only evidence: persistence reads/writes and artifact lookup independently where instrumentation exposes them.

For median/p95 collection, use repeated identical requests only where doing so does not trigger external provider work or mutate authoritative state. Do not manufacture p95 from too few samples. Record single observations as such.

## Stage 0 disposition

Stage 0 is durable when this checkpoint is committed and reviewed. No optimization is included. There is no authority blocker. The highest-confidence next target is Stage 1: eliminate ordinary-runtime DDL/schema work and prove it with regression tests, while measuring DB time before and after. Re-fetch main and active PRs before touching code.
