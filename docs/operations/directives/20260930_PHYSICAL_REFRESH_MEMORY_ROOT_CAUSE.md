# 2026-09-30 — Physical Refresh Memory and Lifecycle Corrective

## Trigger

A physical iPhone/Safari session on the #307 live deployment submitted
`POST /api/intelligence/jobs` at approximately `2026-09-30T04:11:47Z`. Render
telemetry then rose from about 344–349 MB to 522.4 MB against a 536.9 MB limit,
CPU was saturated, and the process restarted. Canonical league/roster State
survived; Forecast, Simulation, Value and dependent intelligence did not.
Startup logged `forecast=False simulation=False value=False complete=False` and
the browser showed `Refresh interrupted`, `2/7 build`.

This contradictory physical runtime evidence reopens the lifecycle gate. It
does not reopen football model semantics or Forecast authority.

## Evidence and root cause

- The Render request sequence has automatic
  `/api/connect/sleeper/background/refresh` at `04:10:29Z`, followed by repeated
  `/api/connect/sleeper/background/current` polls through `04:11:41Z`. The
  explicit intelligence POST arrived at `04:11:47Z`. The route owners were
  separate: Hosted Connect performed its State load before handing off to the
  IntelligenceJobCoordinator, while the manual intelligence route could start
  another State load in that handoff gap.
- In the persistent app, State loading was outside `HeavyWorkCoordinator`.
  Forecast, Simulation and Value each claimed the coordinator separately, but
  the coordinator records RSS and serializes claims; it does not reserve memory
  for a phase or prevent one active phase from exceeding the Render limit. The
  resulting lifetime included the published generation, canonical and working
  State during replacement, phase output in the working generation, and any
  execution caches still live until their explicit resource boundary/reclaimer.
- The exact incident has only coarse Render RSS/CPU samples. It does not record
  which Python objects accounted for the 173–178 MB increase, nor prove whether
  two provider State loaders were simultaneously allocating at the instant of
  peak RSS. Treat duplicate State work as a real admitted race and confirmed
  lifecycle defect, not as a proven allocation attribution.
- Market value-lens requests around `04:12:18Z` and `04:12:21Z` logged staged
  first-load behavior and returned empty lightweight payloads. They do not call
  the Intrinsic materializer in that state. They are not the heavy allocation
  source shown by available evidence. Repeated requests can add CPU overhead.
- `/api/product-context` took about 28 seconds and `/api/home` about 5 seconds
  while CPU was saturated. These are capability/read paths; observed latency is
  consistent with process starvation, not evidence that they reconstruct the
  model. No heavy foreground reconstruction was identified in the incident
  route trace.
- PR #306's ~308.5 MB acceptance was a warm durable restore: it reused exact
  State Forecast/Simulation/Value artifacts and staged Intrinsic rehydration.
  It did not exercise the cold/current-State State sync plus live Forecast,
  Simulation and Value build overlapping with Safari reads. Thus it did not
  cover the real path. #307 repaired the physical Connect presentation path,
  not the independent refresh owner gap.
- On process restart, the persisted in-progress job becomes
  `INTERRUPTED/server_restart`; its in-memory working generation is lost. If
  only newer canonical State is durable, old model artifacts correctly fail
  exact-State reuse and runtime remains without core layers. Before this
  corrective, browser polling reported terminal interruption and did not resume
  that missing work, allowing the observed 2/7 state to persist indefinitely.

## Corrective

1. Have an explicit intelligence refresh join the same user's active automatic
   Sleeper refresh rather than start a competing State load.
2. Put production Sleeper State materialization inside the same
   `HeavyWorkCoordinator` lane and release unused allocator memory at the State
   boundaries. Keep the existing hard memory limit and model fidelity.
3. Record current/peak RSS and active/waiting claims at refresh start, after
   State, Forecast, Simulation, Value, Intrinsic and publication, plus abort.
   This identifies phase growth on the next live run; it does not pretend the
   old coarse samples contain object-level attribution.
4. When the browser polls a restart-interrupted job and exact canonical State
   survived, automatically rebuild missing exact-State core layers without
   re-fetching State. Preserve exact-State authority and atomic publication.
   Checkpoint the job's State ID when direct State sync advances, so recovery
   can compare the durable job with the State actually being built. Correct the
   interruption copy so it no longer asserts that stale last-good intelligence
   is active.
5. Deterministically exercise automatic refresh + manual tap + concurrent
   product/status reads + automatic value-lens polls; assert a single State load
   and terminal usable Forecast, Simulation, current Value and Intrinsic. Also
   exercise restart recovery without a second State sync and prove direct State
   sync checkpoints its new identity before downstream work.

## Acceptance and limits

Required before closure: focused and full CI green; exact-head review; merge and
deploy; inspect new phase RSS logs under the realistic browser-driven hosted
journey; verify capability readiness and actual usable payloads; then physical
iPhone/Safari acceptance. Restore-only acceptance is insufficient. A single
phase that still approaches the hard limit after duplicate ownership is removed
must be diagnosed from the new phase logs and fixed at the smallest owning
lifetime/admission boundary, without lowering model fidelity or raising limits.

The old incident cannot establish the per-phase object-level allocation. The
new instrumentation and realistic regression are designed to close that
evidence gap. Until the post-deploy live journey and physical Safari retest pass,
status remains **BLOCKED — runtime acceptance**.
