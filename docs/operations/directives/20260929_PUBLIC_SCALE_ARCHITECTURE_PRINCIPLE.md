# 2026-09-29 Public-Scale Architecture Principle

## Management intent
FSFFL NEXT is being developed in private beta on a small Render footprint, but that footprint is **not** the architectural target.

The target is a production-capable multi-user platform that can support a public launch and materially higher daily traffic by adding capacity, workers, and infrastructure **without redesigning the core authority or lifecycle model**.

The current free/small instance is useful as a stress constraint because it exposes leaks, unnecessary retention, blocking foreground work, and poor lifecycle ownership. It must not cause the system to be architected around unrealistic single-process or ultra-low-memory assumptions.

## Public-scale design principle
Design the plumbing so scale is primarily an **operational capacity problem**, not an application-architecture rewrite.

A public deployment should be able to scale through:
- more web instances;
- more background/compute workers;
- larger memory/CPU instances where justified;
- managed durable storage;
- shared/distributed cache where appropriate;
- queueing/backpressure;
- independent scaling of heavy analytical workloads.

Adding traffic should not require moving model authority into Presentation, duplicating Forecast/Value logic, or introducing league-specific shortcuts.

## Required architectural properties

### 1. Stateless/replaceable foreground web tier
The web/API tier should be horizontally scalable. A request must not depend on having reached the same process that handled the user's prior request.

Process memory may accelerate work but must not be the sole authority for:
- canonical State;
- managed-team identity;
- publication generation;
- durable job truth;
- accepted Forecast/Simulation/Value/Intrinsic artifacts.

### 2. Heavy compute separated from request latency
Forecast, Simulation, Intrinsic, Market/Search/Decision enrichment and other expensive work should be schedulable outside the foreground request path.

Foreground requests should:
- activate/read State;
- return truthful readiness;
- enqueue/idempotently request work;
- read already-published governed results.

A public user should not need one web worker to remain occupied for the lifetime of a multi-minute analytical job.

### 3. Durable job identity and idempotency
Heavy jobs must have stable identities derived from their governed inputs so duplicate requests do not create duplicate expensive work.

The system should support:
- deduplication;
- cancellation/invalidation when State changes;
- exact-input reuse;
- restart recovery;
- bounded retries;
- truthful queued/running/failed/complete status.

### 4. Multi-instance lifecycle coordination
Process-local per-user locks are acceptable implementation detail for the current single-instance beta only when correctness does not depend on them across processes.

Before public multi-instance deployment, any lifecycle operation whose correctness requires serialization across instances must use a durable/distributed coordination mechanism or equivalent single-owner job architecture.

Do not rely on sticky sessions as a correctness requirement.

### 5. Explicit resource ownership
The resource-boundary work from PR #303 remains relevant at public scale.

Execution-only caches, coordinator records and temporary payloads must have:
- an owner;
- an identity scope;
- a bounded lifetime;
- an eviction policy;
- cross-user isolation;
- observability.

Memory should not grow as a function of how many users/leagues have ever touched a process.

### 6. Independent workload scaling
Different workloads have different resource profiles and should be separable when scale justifies it:
- lightweight API/read traffic;
- State/provider acquisition;
- Forecast;
- Simulation;
- Intrinsic/Shapley;
- Market/Search/Decision;
- scheduled/history/research capture.

The architecture should permit these to move to separate worker pools or services without changing model authority.

This does **not** require premature microservices during private beta. Clear module/job boundaries are sufficient now.

### 7. Backpressure and fairness
Public scale must not allow one user's large job to starve foreground reads or every other user's work.

The runtime should eventually support:
- bounded concurrency by workload class;
- queue depth limits;
- per-user/per-league deduplication;
- fair scheduling;
- rate limiting where appropriate;
- graceful degradation/readiness rather than process exhaustion.

### 8. Cache strategy
Caches are accelerators, not authority.

Use:
- bounded process-local caches for hot immutable/reconstructable data;
- shared/distributed caches only where cross-instance reuse materially helps;
- durable artifacts for governed results;
- explicit invalidation tied to State/model/input identity.

Avoid giant per-user process caches whose value disappears when traffic is distributed across instances.

### 9. Observability and capacity planning
Public launch should have workload-level measurements for:
- request latency;
- queue wait;
- job duration;
- CPU;
- current/peak memory;
- cache hit/reuse rates;
- provider latency/rate-limit pressure;
- job failure/retry rates;
- publication lag.

Capacity decisions should be made from these measurements rather than forcing all workloads to fit a private-beta free-tier ceiling.

### 10. Security and tenant isolation
Public multi-user scale requires:
- authenticated private user data;
- no identity-bearing public diagnostics;
- strict user/league scoping;
- no cross-user cache eviction/data leakage;
- secrets outside application code;
- provider/licensing constraints preserved.

## Relationship to the current ~512 MB gate
The current hard-memory gate remains useful for PR #303 because it tests whether lifecycle ownership is clean.

It is **not a permanent commercial product requirement**.

After PR #303:
- if memory grows because stale prior-user/prior-league execution state survives, that is an application defect;
- if memory returns to a stable bounded baseline and legitimate analytical work requires more memory than the current small instance provides, that is a capacity/compute-staging decision.

Do not distort correct production architecture merely to make every legitimate workload fit the current free-tier envelope.

## Near-term sequencing
This principle does not broaden the current PR #303 scope.

Current order:
1. finish #303 whole resource-boundary closure under the existing private-beta gate;
2. complete hosted lifecycle acceptance;
3. restore physical Safari acceptance;
4. before any public launch, run a dedicated production-readiness/scaling review covering multi-instance correctness, worker/job separation, queues/backpressure, shared persistence/cache needs, provider limits, security, observability and realistic load testing.

No premature microservice rewrite is authorized now. The rule is to avoid architectural choices that would make that later production scaling require rewriting the core system.


## Practical interpretation
The private-beta free tier is an optimization environment, not a commercial-capacity benchmark.

FSFFL NEXT should minimize avoidable resource use and preserve clean ownership, reuse and asynchronous execution. Once legitimate work is efficient, future throughput demand should be met by scaling infrastructure rather than weakening analytical authority or forcing all workloads through one tiny process.

A future public deployment with hundreds or thousands of users is expected to require materially more CPU, memory, bandwidth, worker capacity and supporting infrastructure than the current private-beta instance.
