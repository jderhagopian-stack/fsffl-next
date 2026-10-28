# P0 Worker Separation — controlled implementation tranche (October 28, 2026)

## Authority / status

Management explicitly approved beginning architecture separation after #490 demonstrated the same 353 Career values with full numerical parity under an isolated worker on a preserved historical State. **Not** an authorization to change production, run a live refresh, apply migrations to Supabase, provision a new worker, or spend money. Repository main initially `271a8a8be8dc7611f9fc6df1a8f5f9182b5a747c`; existing research PR #491 and memory fix PR #489 remain independent. This workstream is **ACTIVE — implementation candidate**, not accepted/released.

## Execution boundary selected

Keep all governed model and publication owners unchanged. Add a replaceable, opt-in worker dispatch *contract*, NOT a second forecast/Career calculator or web refresh lifecycle:

- A deterministic job identity binds tenant user, league, exact State, current publication generation, source manifest fingerprint, accepted model version and allowed capability (`career_intrinsic`). No raw roster/provider payload in job row.
- One queued or running job per user; additive work must be explicitly sequenced. PostgreSQL row-level `FOR UPDATE SKIP LOCKED` + a partial unique constraint provide database-owned claim isolation. Bounded attempts, bounded lease, heartbeat and token-fenced finish/fail. Exhausted dead-worker leases are terminalized; they cannot block a tenant indefinitely.
- Compute writes the **existing accepted Career artifact** through the existing PersistenceStore first. A fenced worker may then mark the dispatch record *computed*, never published. Readers cannot treat a receipt as a model value. Existing Career loader must still verify exact State, source, full cohort and artifact version; the existing guarded publication owner alone may publish.
- Use one `PostgresPersistenceStore.connection()` bounded pool per process; do not introduce a second unbounded connection adapter/Redis/queue technology.
- No new web endpoints, refresh hooks, background scheduler or worker process are enabled in this tranche. SQL migration is committed **but NOT applied**; all code is inert in the live app. No production permissions change.

## Why not activate this immediately?

The published `IntelligenceJobCoordinator` currently holds Python callbacks/active runtime context inside the web process. Moving that closure across processes is not safe. The producer inputs must first become immutable and recoverable by a separate worker, and publication completion must continue to be committed under the existing State/generation lifecycle owner. The in-process beta lifecycle is therefore intentionally left untouched pending a vertical slice that demonstrates full restore/build/commit through the new boundary on an exact private State.

## Focused acceptance for this tranche

1. Static contract tests: exact identity differences, tenant/generation supersession, no false publication, missing/invalidated artifacts, no unrecognized model/capability.
2. Throwaway GitHub Actions PostgreSQL service on Python 3.12.10: two independent processes, lease claim + crash, expiry/reclaim, old-token fence, bounded attempts, duplicate work coalescing, per-user fairness, no private payload transfer and success receipt, using existing bounded pool. The disposable schema is reset only on `127.0.0.1` in a database explicitly named `fsffl_worker_test` with an explicit test-only env flag.
3. Generic CI and stable full suite only at merge gate per `OPERATING_PROTOCOL.md`; **keep draft** while under review. No merge until management approves SQL/worker operational costs and exact-head stable suite passes.

## Remaining to complete the actual restructuring

- Build one separately invoked production-Python worker that restores immutable source evidence for a pinned State, executes existing Career/3-Year cohort, persists accepted exact artifacts and returns a validated receipt.
- Make the existing refresh lifecycle enqueue instead of running heavy Career locally only behind an explicitly tested guarded cutover, with safe disabled fallback; do not expose a competing user-visible status controller.
- Worker death at all phases, State supersession, stale receipt, no-op retry, last-good preservation, full cohort, read-only API/Franchise Safari under active compute, exact State and generation cross-surface and multi-tenant behavior.
- Measure real cgroup memory, p95 real authenticated web reads, production 3.12 numeric parity, provider/DB traffic, refresh latency and one-run CPU/RAM/service cost before approving extra infrastructure. Design paid worker size from peaks, not arbitrary CPU/RAM promises.
- New-tenant scale scenarios and task/state retention policy before 100,000-league claims.

## Explicit non-claims

This milestone is a concrete **job dispatch and fencing protocol**; it is not yet a running production worker, full refresh route integration, a validated hosted memory solution, or a release. Never close #490/#481/#405/#479 on this evidence alone.