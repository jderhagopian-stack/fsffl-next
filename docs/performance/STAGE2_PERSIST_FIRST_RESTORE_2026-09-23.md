# Stage 2 — Persist-first restoration checkpoint

Date: 2026-09-23 / 2026-09-24 UTC  
Base main: `a264d4042dd1eec109087cac4ef648d612066879`  
Branch: `performance/stage2-persist-first-restore-20260923`

## Stage 1 live gate

Render service `fsffl-next-private-beta` was behind main on `06ac99de3df5fb19ef26493e77fb6de0c7ebc345`.
The established API-triggered private-beta deployment mechanism deployed Stage 1 main
`a264d4042dd1eec109087cac4ef648d612066879` as deploy
`dep-daq83ih42hec738matjg`. Build completed successfully and Uvicorn reported
`Application startup complete`; Render then marked the service live. Because the
Behavioral Postgres adapter is constructed before the app object is served, successful
startup proves the read-only required-relation, RLS-enabled, and required-index validation
did not fail. No runtime DDL was restored.

The hosted surface is Basic-auth protected, so this execution environment could not issue
authenticated live product-route smoke requests directly. Pre-merge full CI and focused
Home/Atlas/product regressions were green, and Render startup was healthy. This is retained
as a live-validation limitation rather than inventing authenticated smoke evidence.

## Restore audit — before

The repository already had the correct persistence and identity foundations:

- `PersistentPrivateBetaRuntimeStore.get()` lazily restored a persisted runtime on the
  first request when process memory was empty.
- `restore_runtime_snapshot()` required the persisted user context and canonical
  `LeagueState.state_id` to agree, decoded only current model versions, rejected malformed
  or stale Forecast artifacts, required Simulation to match the exact State and current
  team-view version, and required Value to match the exact State.
- exact Simulation persistence remained keyed by State scope, current Simulation model
  version, and the persisted Forecast artifact fingerprint.
- State/Forecast/Simulation/Value checkpoints were serialized through the existing
  persistence worker. No second persistence framework is needed.
- Home, My Team, and League Atlas consume already-attached runtime evidence. Home launches
  no Forecast, Value, Decision, Search, or Simulation work.
- Sleeper refresh already has a background coordinator and persisted sync cursor/probe
  path that can skip an unnecessary full provider refresh.
- Intelligence and connect job lifecycle state remains in process memory; durable job
  lifecycle belongs to later Stage 6.

Two Stage 2 gaps were concrete:

1. the first `/api/product-context` request paid the lazy durable-restore read after a
   process restart even though the single private-beta user is known at startup;
2. an intelligence refresh progressively replaced a completed known-good bundle with
   Forecast-only and then Forecast+Simulation partial state before Value completed.

## Stage 2 change

1. Hosted startup now invokes the existing durable runtime store's exact restore for the
   configured private-beta username (or `local-beta-user` when auth is disabled) before
   accepting product traffic. This is persistence reuse only: it performs no provider,
   Forecast, Value, Decision, Search, or Simulation work.
2. A successfully restored complete bundle is explicitly marked as reused in runtime
   metadata.
3. Refresh orchestration now stages Forecast and Simulation in the existing pending
   intelligence snapshot while a complete last-good bundle remains served.
4. Value promotes the staged State+Forecast+Simulation+Value bundle atomically only after
   the exact pending identity is complete. If Simulation or a later phase fails, the
   completed last-good bundle remains attached.
5. When no completed last-good bundle exists, existing progressive/fail-closed behavior
   remains intact.

No new persistence store, cache, fingerprint, queue, model, or authority path was added.

## Measurement

The Stage 0 process-cold restored `/api/product-context` observation was approximately
3.103–3.704 seconds; same-session warm was approximately 0.013 seconds. Those historical
observations are not relabeled as current Stage 2 timings.

The deterministic Stage 2 first-request I/O delta is covered by regression: after explicit
startup restore, the first runtime `get()` performs **0 additional persistence context
reads**, versus **1 lazy restore read** before startup prewarm. A trustworthy hosted
post-change wall-clock comparison requires deployment of this PR and is therefore not
fabricated here.

Stage 1 live deployment timing observed during this work: checkout of the target SHA began
at 01:50:09Z, build success at 01:50:41Z, application startup completed at 01:51:30Z, and
Render marked the service live at 01:51:33Z. These are deployment observations, not Stage 2
request-latency claims.

## Acceptance / authority audit

Focused regressions added for startup restore memory reuse, incompatible persisted State
fail-closed behavior, atomic promotion, and failed-refresh preservation of last-good
evidence. Existing Home and Simulation persistence regressions remain authoritative for
their boundaries and will run in full CI.

Unchanged authority: Data → Point-in-Time State → Forecast → Value → Decision →
Search/Optimization → Analytics/API → Presentation. Simulation still owns stochastic
competitive outcomes and remains 50,000 runs. Forecast math, Simulation math/distribution,
Value/Intrinsic, Decision economics, Search authority, Team Utility, owner-behavior
inference, evidence/provenance, and product presentation are unchanged.

Cost remains $0 recurring beta infrastructure. No paid Render plan, paid compute, paid
database/cache/queue, or infrastructure migration was introduced.

## Collision audit / limitations

Active PR #182 overlaps `src/fsffl/product/webapp.py`, so Stage 2 deliberately does not
modify that file or any Franchise/presentation file. Consequently, no new API/UI readiness
fields are added here; existing readiness/freshness presentation remains downstream.

The private-beta authenticated live routes cannot be directly exercised from this execution
environment without credentials. Stage 6 remains the owner of durable job lifecycle.
Stage 3+ database connection/pooling, broader exact-reuse expansion, Simulation kernel
optimization, durable jobs, and broader progressive delivery are explicitly deferred.
