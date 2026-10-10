# Scalable Computation Foundation

Updated: 2026-10-10  
Status: architecture decision recorded; no runtime change, migration, deployment, or infrastructure purchase.  
Authority: October 10 Management strategic reset; applies to Career, Explore, Trade, and future computation work.

## Decision

Build shared computation around **semantic dependency identity**, while keeping league State and team decisions isolated. Reuse is a correctness decision before it is a cache optimization. A cache hit is valid only when the exact inputs, model/configuration versions, provenance and permitted sharing scope match. Freshness policy is checked separately and must not be bypassed by a matching content key.

The current implementation already contains meaningful fingerprints, durable artifact interfaces, exact State/forecast reuse, process-local single-flight for scenario simulations, and publication/last-good safeguards. Keep those authorities. Do not create a new lifecycle controller, queue service, cache tier, or broad compute rewrite.

## Reuse boundaries

| Work | Widest safe reuse scope | Required identity / isolation |
|---|---|---|
| Provider evidence and acquisition | Provider/source × NFL season × endpoint/data family × horizon/week × normalization/source revision, further constrained by provider rights and freshness. Deduplicate equivalent requests across leagues only when canonical player identity/mapping and source inputs match. | Provider, season, endpoint family, canonical subject set, source revision/content digest, normalization version, effective/freshness policy, request cause. Keep raw evidence and provenance separate from fantasy scoring. Tenant-private or license-restricted material must not cross its permitted boundary. |
| Historical fitting and Career outputs | Fit once per exact historical PIT corpus, training/target definition, model code, parameters and fit configuration. Player-level NFL-space outputs can be shared across leagues when identity, target horizon and model/evidence versions match. | Historical PIT snapshot/corpus fingerprint, target/label policy, feature and route/policy versions, fitting code/environment identity, model and parameter versions, player identity, horizon, uncertainty method. Scoring transforms remain scoring-cohort-specific. Preserve #405's accepted research, numerical parity gate and exact worker checkpoint. |
| Forecasts and scoring cohorts | Raw NFL-space provider forecast can be shared across equivalent season/player/source fingerprints. Apply fantasy points/coverage once per unique scoring + lineup + schedule/horizon signature; leagues with the same signature can share that deterministic transform. | Raw: season, canonical player set/mapping, accepted source evidence/provenance and forecast implementation. Scored: raw fingerprint plus scoring rules, lineup requirements, fantasy horizon/schedule/bye inputs, and scoring implementation version. Never put roster ownership into raw acquisition identity. |
| League State, Value and Simulation | State is league-specific and immutable. Reuse league outputs only for the exact material State and all consumed evidence/configuration. Identical rules do not make distinct rosters, schedules, standings or ownership interchangeable. | League/State identity and material dependency fingerprint; exact forecast/Value identities; rules and authority versions; Simulation model, RNG protocol, seed/count/configuration. PIT, replay, publication generation and State fences remain authoritative. |
| Team Trade and Decision | Reuse underlying shared forecasts and compatible asset-level evidence. Evaluate each candidate against its exact league State, both participating teams, transaction, strategy/preferences and decision policies. Identical proposals in different teams/leagues are not equivalent by default. | State + proposal/asset identities + both team identities/rosters + team utility/context + decision policy/model version. User identity is authorization/ownership context, not a substitute for semantic computation identity. |

An identity describes dependencies; it does not itself grant authority. Source licensing and tenant access are independent gates.

## Existing seams and disposition

| Area | Status | Evidence-based disposition |
|---|---|---|
| Canonical provider boundary | **KEEP** | Adapters normalize provider payloads and preserve provenance; provider truth is separate from model and presentation authority. PR #442's event/request/bytes instrumentation is deployed; natural provider evidence is still pending. No source/policy change. |
| Fingerprints | **KEEP; extend by dependency** | `raw_forecast_input_fingerprint` separates NFL-space forecast inputs from broader State. `forecast_input_fingerprint` includes scoring, lineup and horizon inputs. `league_material_fingerprint` captures Simulation/Value/Decision-relevant State. Simulation scenario keys include exact State, forecast fingerprint and loader identity. Do not replace these with league/user-only keys. |
| Persisted artifacts | **KEEP** | `ArtifactKey` carries artifact kind, scope, scope ID, input fingerprint and model version; `PersistenceStore` supports metadata-first reads and reusable artifacts. Current Forecast, Value and Simulation artifacts are conservatively league-State-scoped. Widen artifact reuse only after separating raw and scored payloads and proving exact compatibility; no key broadening in this tranche. |
| Scenario single-flight | **KEEP** | `scenario_cache` uses bounded process-local LRU storage, exact dependency keys, and in-process Future coalescing; optional durable exact-result reuse fails open to authoritative Simulation. It does not provide cross-process single-flight. |
| Current background jobs | **CHANGE NOW: constrain new callers / add backpressure before broader fan-out** | `IntelligenceJobCoordinator` persists lifecycle records, but job IDs are random UUIDs; locks/current-job maps are process-local; a `ThreadPoolExecutor(max_workers=2)` bounds active threads but its submitted-work queue is unbounded. `max_records` bounds visible job history, not queued work. Do not build higher fan-out Career/Explore/Trade workloads directly on this coordinator without bounded admission/rejection and an injected execution boundary. No runtime change is included here because a testable checkout is unavailable in this session. |
| Durable multi-instance jobs | **CHANGE LATER, before adding independent workers/instances** | Persist deterministic idempotency identity, lease/claim fencing, retries, cancellation/expiry and owner authorization in a transactional job store/queue. Require at-least-once-safe work and fenced publication. The current persisted UUID lifecycle record is observability/restart recovery, not a durable queue or cross-instance lock. |
| State/publication/PIT/replay/last-good | **KEEP** | Continue exact State and publication identity fences; write complete immutable evidence before pointer promotion; stale workers cannot publish; readers retain last-good on failure and report freshness. PR #443 remains an isolated prototype / production NO-GO and is not modified by this decision. |
| Capacity and infrastructure | **CHANGE LATER, measure first** | Supabase Pro is active; former Free database allocation framing is not a current gate. Keep bounded pooled PostgreSQL transport, current single-instance deployment and existing persistence. Add workers, queues, object storage or capacity only after measured multi-league demand and a Management gate. |

### Most important current weakness

Unbounded pending work in the in-process coordinator is the clearest immediate resource hazard: a burst can accumulate captured closures and job state even though only two jobs execute at once. Per-user locks do not coordinate multiple processes. This matters before adding new fan-out; it does not justify prematurely deploying a distributed queue.

## Minimum execution contract

1. **Fingerprint the work.** Every reusable result declares artifact kind, semantic scope, canonical input/evidence fingerprint, code/model/configuration version and provenance. A provider request's source content digest and effective freshness remain visible. Random request/job IDs are tracing identifiers, never cache identity.
2. **Reuse only a complete match.** All material dependencies must match; freshness, licensing and tenant authorization must independently permit reuse. Changes invalidate only downstream stages that consume them. A scoring change reuses compatible raw NFL evidence but rebuilds scored Forecast and its dependent Value/Simulation/Decision outputs. A roster change leaves raw evidence/model fitting intact but invalidates State-dependent results and affected team analysis.
3. **Coalesce identical work.** A logical operation uses idempotency identity derived from tenant/league scope where required, operation, target State, input fingerprint, and implementation/configuration version. Concurrent equivalent requests may join one in-flight computation within its permitted scope; different tenants may share computation only when the artifact is explicitly shareable and access is rechecked at read time.
4. **Bound admission and memory.** Bound active workers, pending jobs, per-tenant concurrency, payload size, retained in-memory results and wait time. Reject or defer excess work explicitly; keep last-good readable. Never silently queue unbounded closures or load entire multi-league batches into memory.
5. **Keep execution replaceable.** Product/model functions receive an execution contract (submit or join by idempotency key, read status/result, report progress, cancel where supported) rather than owning a thread pool. The beta may use an in-process implementation; a future independent worker must implement the same semantics without changing model math or product authority.
6. **Fence writes and publication.** Workers validate authorization and exact source State/PIT/input identity before writing. Persist immutable artifacts and a complete manifest before atomically promoting the authoritative pointer. A stale/superseded job cannot overwrite a newer generation. Retries are safe; readers keep the last-good publication and expose truthful freshness/status.
7. **Preserve deterministic replay.** Stochastic work records RNG protocol, seed/stream, sample count and runtime/model identity. Reuse never changes the governed Simulation protocol or substitutes a partial result for authoritative output.

## Career #405 coordination

Do not change or rebase the active Career worker's branch, checkpoint, artifact, parity comparator, or accepted model. The current canonical Career checkpoint remains the authority. The Career worker should continue its exact authorized task; if it builds a new reusable computation, apply the identity/scope rules above without changing the current PR1/PR2 gate or sharing rostered output across leagues. No additional Career action is required for this architecture record.

## Implementation status and next decision

No source code, tests, database schema, deployed service, or PR #443 files were changed. This decision is documentation-only and requires no runtime test.

Before the next broader asynchronous Career/Explore/Trade fan-out, Management should authorize a focused implementation PR that adds bounded admission/backpressure to the current coordinator and defines the injected execution protocol, with focused concurrency, saturation, idempotency and tenant-fence tests. A durable queue and independent worker remain deferred until demand warrants them. Do not merge or deploy that future code without its own review and authorization.
