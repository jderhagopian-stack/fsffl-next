# 2026-09-29 Resource Boundary Closure Directive

## Why this directive exists
PR #302 correctly localized the hosted hard-memory blocker to process-local execution retention and allocator high-water behavior around State/league transitions. Its post-merge review nevertheless found an omitted Market enrichment store, an uncovered supported connect route, and identity-bearing retained telemetry.

Those findings are evidence that a component-by-component patch loop is no longer acceptable for this class. This directive replaces narrow cache-by-cache correction with a whole-boundary closure.

## Goal
Prove that every supported transition into a new canonical league/State establishes one governed **resource ownership boundary** before any new heavy work begins.

After the boundary:
- no prior-league execution-only cache, coordinator record, queued result, temporary provider payload, search/decision workspace, or acceptance-only heavyweight object may remain live unless explicitly documented as cross-league authority;
- canonical durable/presentation/model authority that is allowed to survive remains intact;
- allocator reclaim occurs at the correct lifecycle point;
- no supported route can bypass the boundary;
- retained diagnostics are bounded and non-identifying.

## Required inventory before further merge/deploy
Implementation must enumerate every process-local mutable holder that can retain material memory across league/State transitions, including at minimum:
- Market/Search/Decision wrapper caches;
- MarketDecisionEnrichmentCoordinator and similar coordinator/job result stores;
- Behavioral/owner/market workspaces;
- Forecast/Simulation/Value/Intrinsic temporary or reusable execution caches;
- provider payload/history buffers;
- publication/reconciliation staging objects;
- background job registries/result stores;
- acceptance-harness retained payloads;
- diagnostic/telemetry buffers.

For each holder, classify:
1. authoritative durable state;
2. intentionally cross-league reusable immutable cache;
3. user/league-scoped execution cache that must be cleared;
4. request/job temporary that must become unreachable;
5. bounded diagnostics.

No unclassified materially sized holder may remain.

## Required transition-path inventory
Enumerate every supported path that can activate or replace canonical State or managed league identity, including:
- background Sleeper connect;
- synchronous `POST /api/connect/sleeper`;
- explicit league switch;
- material same-league State refresh;
- restored-session activation;
- restart restore;
- any internal/test/acceptance path that invokes the same lifecycle.

All paths that can transition into new heavy work must call the same resource-boundary primitive or prove equivalent behavior. Do not duplicate ad hoc cleanup logic per route.

## Single owning primitive
Prefer one explicit lifecycle-owned primitive, conceptually:
`activate_state -> publish valid State -> release prior-scope execution state -> allocator reclaim -> start new heavy work`.

The primitive must receive enough identity context to clear user/league-scoped coordinator records safely without deleting other users' live work. It must preserve #294/#295/#296 publication/restore semantics.

## Closure tests
Before merge/deploy, require deterministic coverage for:
- A -> B -> A repeated switches with completed focused Market enrichment present before each transition;
- both background and synchronous connect paths;
- same-league material refresh;
- no cross-user eviction;
- no prior-team/prior-league surface leakage;
- prior execution records gone at the boundary;
- authoritative durable publication/restart state preserved;
- bounded non-identifying public telemetry;
- repeated transitions do not show monotonic retained-object growth;
- memory gate remains unchanged.

## Resource evidence
Run phase-level RSS/current/peak telemetry around:
1. pre-transition steady state;
2. State activation;
3. resource-boundary cleanup;
4. new Forecast/behavioral/intelligence start;
5. terminal publication;
6. post-publication idle.

Repeat A -> B -> A enough times to distinguish:
- bounded transient allocation,
- allocator high-water,
- monotonic retention/leak.

Compare process telemetry with Render metrics. Do not classify a harness-local peak as a production-runtime defect or vice versa.

## Acceptance / stopping rule
Do not merge another resource corrective merely because the currently known P1/P2 comments are individually fixed.

Before merge, require:
- complete holder inventory;
- complete supported transition-path inventory;
- one shared resource-boundary mechanism or documented equivalent;
- deterministic closure matrix green;
- full CI green;
- bounded whole-class P1/P2 review with no unresolved findings.

After merge/deploy, rerun the full hosted clean-first-run / managed-team selection / FSFFL -> Hodor -> FSFFL / same-State / restart / restored-session journey under the unchanged hard-memory gate.

Physical Safari remains HOLD until terminal hosted PASS.

## Frozen boundaries
Do not change:
- #294/#295/#296 runtime publication/restore authority except where strictly necessary to wire the shared resource boundary without semantic change;
- #298 FUMBLES_LOST authority;
- PI readiness semantics;
- Forecast/Simulation/Value/Intrinsic model semantics;
- K/DST or Y2/Y3/Y4-Y7 authority;
- the hard memory limit.
