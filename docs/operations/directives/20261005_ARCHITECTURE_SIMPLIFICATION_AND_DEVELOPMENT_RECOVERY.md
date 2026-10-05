# 2026-10-05 — Architecture Simplification and Development Recovery

## Management priority

**P0 — URGENT / BLOCKING NEW PRODUCT EXPANSION**

FSFFL NEXT has reached a point where runtime/application complexity, resource behavior, development process overhead, and stale operating state are materially slowing product development and creating repeated physical failures in otherwise bounded features.

This is now a first-class Management corrective.

The objective is not a rewrite. The objective is to restore the founding FSFFL NEXT charter: a fast, understandable, modular, auditable, efficient system that is safe to change and easy to extend.

Until this corrective is dispositioned, do not begin #375, PIT/history expansion, Owner Intelligence implementation, or other new product breadth. The current live Dynasty Position & Depth acceptance failure may continue only as a narrow blocker fix. No competing implementation stream should touch the same runtime surface during the audit.

## Governing authority

Treat these as controlling:

- `docs/charter.md`
- `docs/NORTH_STAR_PRODUCT_DIRECTIVE.md`
- `docs/architecture/overview.md`
- `docs/architecture/authority-boundaries.md`
- `docs/architecture/performance-and-caching.md`
- `docs/architecture/api-ui-boundary.md`
- `docs/operations/OPERATING_PROTOCOL.md`

The charter requires NEXT to be:
- faster and computationally efficient;
- modular and easier to extend;
- safer to modify without hidden interactions;
- auditable and transparent;
- built around one authoritative home for each concept;
- reusable rather than repeatedly recomputed;
- free of presentation-owned business logic;
- free of distributed/runtime complexity until real workload justifies it.

The North Star requires deep analytical sophistication underneath a simple, fast consumer experience.

## Why this corrective is required now

The recent Dynasty Position & Depth rollout exposed a class problem rather than one isolated bug.

Between #383 and #391, a simple read-only product lens encountered repeated failures across:
- saved-session restore;
- persistence continuity;
- Career Intrinsic lifecycle;
- presentation publication generation;
- browser request ownership;
- Safari static-asset delivery;
- server/client response-generation contracts.

Multiple exact-head automated suites passed while the basic physical journey still failed:
`open League Atlas -> select Dynasty -> see ranks`.

Separately, Supabase free-tier egress reached 12.69 GB against the current allowance. Live database inspection shows:
- `fsffl.derived_artifact` is ~357 MB;
- two common full-payload artifact lookup patterns have executed ~12.7k and ~11.6k times respectively since project creation;
- persistence that should reduce recomputation is therefore also creating substantial repeated network transfer.

Current operating documents are also materially stale relative to live production, increasing the risk that worker chats reason from obsolete state.

These are systemic development/runtime signals and must not be treated as a sequence of unrelated endpoint bugs.

## Founding invariant to restore

In plain language:

**Build intelligence once for an exact State, publish it coherently, reuse it cheaply, and let product surfaces read it.**

A normal read-only product feature should not need its own orchestration system merely to display already-governed intelligence.

The target directional runtime should be conceptually close to:

`Provider -> canonical State -> governed intelligence build -> one coherent published intelligence generation -> product readers`

Persistence supports restart/reuse.
Background work builds or replaces intelligence.
Presentation reads published intelligence.
A page read must not quietly become an intelligence-orchestration engine.

## Phase A — read-only whole-system audit

Run one bounded read-only audit before broad corrective coding.

Do not change application code, architecture, persistence data, Render configuration, Supabase schema, or product semantics during the audit.

Review current main and live behavior across these dimensions:

### 1. Runtime lifecycle and orchestration
Inventory every coordinator, loader, lifecycle manager, job registry, restore path, polling loop, publication callback, generation handoff, and last-good mechanism.

For each:
- what problem does it solve?
- is it still necessary?
- is it on the critical path?
- does another mechanism solve the same problem?
- can it be collapsed into a simpler lifecycle owner?

Explicitly count and map the distinct meanings of:
- State current;
- intelligence ready/current;
- building/preparing;
- restored;
- last-good;
- published;
- publication generation;
- per-surface presentation generation.

Recommend one canonical meaning wherever duplication is not necessary.

### 2. Persistence and Supabase
Trace all reads/writes of `fsffl.derived_artifact`, runtime presentation artifacts, last-good bundles, forecast/simulation/value/intrinsic artifacts, and runtime context.

Measure:
- full-payload read frequency;
- payload sizes by artifact kind;
- repeat reads of the same identity during one process lifetime/request journey;
- retention/duplication by artifact kind;
- cold-start restore transfer;
- refresh/reconciliation transfer;
- metadata-only queries versus payload reads.

Required design question:
**Can compatibility/existence/status checks become metadata-first, with large payload fetched only when actually consumed?**

Assess in-process reuse after restore so the same artifact is not repeatedly downloaded from Supabase.

Do not delete historical/evidence data merely to fit quota. Solve waste first.

### 3. Publication architecture
Map working, staged, published, last-good, presentation, and follow-up publication concepts.

Determine the smallest architecture that preserves:
- exact-State safety;
- no mixed generations;
- atomic promotion of coherent intelligence;
- last-good continuity;
- late completion of optional/non-core intelligence.

Specifically determine whether per-surface follow-up generations and handoff machinery can be removed or demoted.

### 4. Frontend/runtime boundary
Inventory product surfaces that perform their own polling, generation negotiation, orchestration, retry ownership, or upstream build requests.

Classify each as:
- necessary reader behavior;
- accidental application orchestration in presentation;
- removable duplicate lifecycle logic.

A read-only view should normally request a published result and render it.

### 5. Static asset delivery
Replace manually maintained semantic cache-buster strings where possible with content-derived versioning owned by one mechanism.

Acceptance principle:
**if a shipped browser asset changes, its delivery identity must change automatically.**

### 6. Resource ownership
Reconcile prior resource-boundary work with current reality.

Audit:
- Render memory;
- retained process-local caches;
- restart/cold-start behavior;
- CPU-heavy work;
- provider acquisition;
- Supabase egress;
- browser/network polling.

Define explicit budgets for:
- cold usable State;
- restored-session usability;
- ordinary foreground read latency;
- refresh wall time;
- memory high-water;
- repeated artifact reads;
- Supabase egress per restore/refresh.

### 7. Test and review strategy
Explain why a repository with 2,000+ passing tests repeatedly failed the primary physical customer journey.

Classify current tests into:
- authority/model correctness;
- runtime/lifecycle contracts;
- brittle static/source-string assertions;
- real end-to-end behavior.

Recommend a smaller merge-gate strategy:
- focused tests during development;
- one full suite at stable merge head;
- a small number of authoritative end-to-end journeys;
- no repeated full-suite loop for trivial test/string corrections;
- external/Codex review only when materially useful and allowance permits.

Automatic PR review behavior must be assessed because Management explicitly exhausted the Codex allowance during the #383-#391 corrective chain.

### 8. Operating state and docs
Reconcile stale operations/workstream docs with current main/live.

Recommend the minimum canonical document set that workers must read so Management decisions do not fragment across obsolete files.

Docs should be durable authority, not a second product to maintain.

## Required audit deliverable

Return one concise Management report, in plain English first, containing:

1. exact main/live SHA reviewed;
2. one-paragraph verdict: what is fundamentally wrong and what remains sound;
3. current-reality architecture map;
4. **KEEP / SIMPLIFY / REMOVE / INVESTIGATE** table for major runtime mechanisms;
5. the 5-10 highest-leverage complexity/resource problems with evidence;
6. target simplified architecture;
7. P0/P1/P2 corrective backlog in dependency order;
8. expected practical benefit of each corrective: reliability, speed, memory, egress, development effort;
9. safeguards that must not be lost;
10. what should explicitly *not* be reopened;
11. recommended acceptance journey and resource budgets;
12. estimated scope in bounded PR-sized slices, not a rewrite.

Prefer one violated invariant that explains a class of failures over a long list of endpoint symptoms.

## Phase B — corrective implementation principles

After Management accepts the audit disposition, implement the simplification in bounded slices.

The default corrective direction is:

- one canonical in-memory State owner;
- one ordinary published-intelligence contract for core product reads;
- last-good as recovery/continuity, not a separate competing authority;
- background jobs explicit and idempotent;
- ordinary foreground reads do not start heavy upstream work;
- persistence lookup metadata-first;
- large persisted payloads loaded once and reused in-process where safe;
- content-addressed/static fingerprint delivery;
- product surfaces as readers of governed outputs;
- one shared lifecycle/resource boundary rather than per-endpoint cleanup;
- fewer overlapping status/generation concepts;
- resource observability with explicit limits.

Do not introduce Redis, queues, additional services, distributed locks, paid infrastructure, or a broad rewrite merely to make the diagram cleaner. The charter explicitly says distributed/runtime complexity should be introduced only when justified by real workload.

## Frozen analytical authority

This corrective must not casually reopen accepted model semantics.

Keep frozen unless a direct contradiction is proven:
- canonical State/domain authority;
- Forecast authority boundaries;
- Simulation 2.0 mathematics, replay identity, postseason semantics, Multiverse, and 50k production authority;
- Current Intrinsic economics;
- Career Intrinsic economics;
- origin-aware pick-value semantics;
- Decision/Search authority separation;
- North Star product direction.

The problem under review is primarily runtime/application architecture, persistence/resource behavior, delivery, and development process.

## Immediate concurrency rule

- Current Implementation may finish the narrow live Dynasty Position & Depth physical blocker only.
- The architecture audit is read-only and may run in parallel.
- Do not create a second implementation writer against the same runtime code.
- No new feature program begins until Management accepts the audit and P0 simplification path.

## Terminal condition

This corrective is complete only when Management can truthfully say:

- adding a read-only product feature does not require creating another lifecycle subsystem;
- normal app reads are fast and do not trigger heavyweight work;
- restart/restore is understandable and bounded;
- persistence materially saves work rather than creating excessive egress;
- a browser code change reliably reaches the browser;
- the primary customer journeys are covered end-to-end;
- the repo operating state matches production reality;
- development can again proceed through small, reviewable changes without repeated systemic regressions.
