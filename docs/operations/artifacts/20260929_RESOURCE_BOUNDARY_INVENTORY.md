# 2026-09-29 Resource Boundary Inventory

## Scope

This artifact closes the inventory requirements in `20260929_RESOURCE_BOUNDARY_CLOSURE.md`.
It describes process-local mutable holders and every supported canonical State/league transition path.
It does not change Forecast, Simulation, Value, Intrinsic, K/DST, FUMBLES_LOST, or Player Intelligence authority.

## Ownership classes

1. **Authoritative durable/current lifecycle** — survives transitions when contractually valid; never cleared merely for memory.
2. **Intentionally cross-league reusable immutable cache** — bounded exact-result/read-only reuse; not owned by one transitioning user.
3. **User/league-scoped execution cache** — disposable process-local state; must be released at the shared resource boundary before replacement heavy work.
4. **Request/job temporary** — must become unreachable or fail closed when its lifecycle identity loses authority.
5. **Bounded diagnostics** — small metadata only, bounded in count, and non-identifying when publicly exposed.

## Process-local holder inventory

| Holder | Class | Material contents / risk | Boundary disposition |
|---|---:|---|---|
| `PrivateBetaRuntimeStore._contexts` | 1 | Current published State + Forecast/Simulation/Value for each active user | Preserve. This is live runtime authority. Cross-league activation replaces the user's published context under #294/#295/#296 semantics. |
| `_working_contexts`, publication guards, pending intelligence | 1/4 | Current unpublished reconciliation graph | Preserve current lifecycle; stale workers fail closed by generation/team identity. Boundary does not weaken atomic publication. |
| Persistent checkpoint queues/futures and managed-team checkpoint barrier | 1 | Ordered durability / restart authority | Preserve. Per-user queues retire when idle. |
| Durable Postgres artifacts, State history, published presentation manifest/surfaces | 1 | Restart/replay/publication authority | Preserve. Resource cleanup never deletes or mutates them. |
| `PresentationContinuityStore._validated_snapshots` | 3 | Process-local validation hints | Clear transitioning user's hints; durable presentation artifacts remain intact. |
| Market economics wrapper cache | 3 | Up to thousands of package economics payloads | Keyed by user; clear only transitioning user's entries. |
| Opportunity Search catalog cache | 3 | Full structural candidate catalog | Keyed by user; clear only transitioning user's entries. |
| Opportunity workspace cache | 3 | Full Search/Decision workspace payload | Keyed by user; clear only transitioning user's entries. |
| `MarketDecisionEnrichmentCoordinator._records/_active_by_scope` | 3/4 | Completed enrichment result payloads and queued/running job handles | Clear transitioning user's records; cancel queued work; running work cannot reattach after identity invalidation. |
| `BehavioralRuntimeCoordinator._records/_future_by_user` | 3/4 | User's current Behavioral result and worker | Clear transitioning user's record/future; stale completion/failure cannot recreate it. Durable Behavioral history remains reusable. |
| Behavioral `_profile_cache` | 2 | Immutable OwnerBehaviorProfile rows for exact State/team | Bounded to four States; preserve as shared exact-State read cache. |
| Hosted Behavioral Postgres adapter cache | 2 | Database adapter/schema validation object | Process infrastructure, not league payload; preserve. |
| `ShapleyIntrinsicBackgroundCoordinator._records/_futures` | 3/4 | User-scoped Intrinsic lifecycle and contract object | Clear transitioning user's records/futures; durable contract remains authority. |
| `PrivateBetaShapleyContractLoader._cached_contract` | 3 | One process-local Intrinsic contract | Explicit user owner; clear only owner on transition. |
| `PlayerFutureForecastCache` | 3 | One process-local Future Forecast contract | Explicit user owner; clear only owner on transition. Durable continuity artifact remains available. |
| `PlayerHistoryBackgroundCoordinator._records/_futures` | 3/4 | Completed per-player career history rows and pending work | Key includes user; clear user's records/futures; durable player-season/career artifacts remain reusable. |
| Simulation scenario cache `_cache/_inflight` | 2/4 | Exact immutable 50K Simulation results, keyed by exact State/Forecast/loader; optional durable backing | Preserve completed exact results as shared bounded reusable authority-neutral execution cache. Inflight work is temporary and exact-key coalesced; HeavyWorkCoordinator bounds overlap. |
| Forecast/provider payloads in Sleeper loaders | 4 | Per-call provider JSON and local thread-pool results | No process-global payload cache; become unreachable after call/reconciliation phase. |
| Intelligence reconciliation closure/local evidence | 4 | State/evidence while job runs | Generation/team guards prevent stale attachment; HeavyWorkCoordinator bounds heavy overlap. No completed full-result store beyond published runtime. |
| `IntelligenceJobCoordinator` job records | 5 | Status/timing/error metadata only | Bounded to 32; not a model/result cache. |
| `LeagueConnectCoordinator` job records | 5 | Connect status metadata only | Bounded to 32. |
| HeavyWorkCoordinator active/recent phase telemetry | 5 | Phase kind, hashed key, RSS samples | Recent events bounded to 16; keys are SHA-256 fingerprints, not user/team/request identifiers. |
| StateResourceBoundary recent events | 5 | Reason, hashed identity fingerprint, counts/RSS deltas | Bounded to 16 and non-identifying. |
| Forecast replay decision cache | 5 | Small per-user diagnostic/selection metadata | State-gated; not a material model payload and not publicly identity-bearing. |
| Runtime lifecycle-lock/generation maps | 5 | Small synchronization/identity metadata | Preserve for lifecycle correctness; no model payloads. |
| Acceptance report state | 5 | Scalar/summarized step/resource evidence | One current report. Full surface payloads are inspected sequentially and released; previous full runtime reference is explicitly dropped before replacement heavy work. |

No unclassified material process-local holder remains in the current hosted composition.

## Supported transition-path inventory

| Transition path | Canonical State activation | Shared resource boundary | New heavy work begins after boundary? |
|---|---|---|---|
| Background Sleeper Connect | `app.state.activate_state_with_resource_boundary` | Yes | Yes — Behavioral/intelligence start only after activation+release |
| Synchronous `POST /api/connect/sleeper` | Same activator in `webapp.py` | Yes | Yes — Behavioral follows boundary |
| Explicit cross-league switch | Same background or synchronous connect path | Yes | Yes |
| Material same-league background refresh | Generation-gated shared activator | Yes when State ID changes | Yes |
| Manual/sync intelligence State refresh | Working State activation, then `apply_state_resource_boundary` before model restore/build | Yes when State ID changes | Yes |
| Restored-session activation in same process | Durable restore establishes current State; no replacement heavy work is started by restore itself | Equivalent: no prior replacement scope to clear; subsequent material refresh uses shared boundary | Yes for subsequent refresh |
| Process restart restore | New process has no prior process-local league scope | Equivalent by construction; durable authority restored, execution caches empty | Yes for subsequent refresh |
| Hosted acceptance internal activation | Uses `app.state.activate_state_with_resource_boundary` | Yes | Yes |
| Low-level store setters used by unit tests/internal lifecycle primitives | Runtime authority primitive only; does not itself launch application heavy work | Not a supported application transition bypass | N/A |

## Boundary ordering contract

For every supported replacement transition:

`load/validate candidate State -> publish/activate valid canonical State -> release prior user execution scope -> GC/malloc_trim -> start new Behavioral/Forecast/Simulation/Value/Intrinsic/PI/Market work`.

For manual sync reconciliation, current published presentation remains visible while the new working State is staged; the resource release occurs after the replacement State has been validated/staged and before replacement heavy model work.

## Cross-user rule

A transition for user A may remove only A-owned execution records. It must not clear user B's Market caches, enrichment results, Behavioral result, Intrinsic lifecycle, Player Intelligence caches, or durable/presentation authority. Shared exact immutable caches are either bounded and preserved or keyed by exact State/Forecast identity.

## Memory interpretation

Deterministic tests prove retained-object boundedness and release ordering. Hosted acceptance remains responsible for real RSS/current/peak evidence and the unchanged hard memory gate. Allocator high-water alone is not classified as a leak if retained object counts are bounded and current RSS recedes after the boundary; a monotonic A→B→A retained-object or RSS pattern remains a blocker.
