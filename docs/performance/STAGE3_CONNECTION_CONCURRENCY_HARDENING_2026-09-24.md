# Stage 3 — connection / concurrency hardening checkpoint (2026-09-24)

## Scope and coordinates

- Directive: bounded Stage 3 only; attribute before optimizing.
- Base/main SHA: `bac7c43b319993f772bcff7dcfe5192702bc8fec` (merged Franchise North Star, PR #190).
- Stage 2 merge remains in ancestry: `7fbe2368e3ed6634f46a45641e8c72f39b8ec54a` (PR #189).
- Render live checkpoint before branching: `bac7c43b319993f772bcff7dcfe5192702bc8fec`, deploy `dep-daq97qh7lnhs73c5odbg`, Free/Virginia/one instance.
- Branch: `performance/stage3-connection-concurrency-hardening-20260923`.
- Collision audit: active PR #182 overlaps `src/fsffl/product/webapp.py`; Stage 3 does not touch that file. No active PR inspected overlaps the Stage 3 implementation files.

## Attribution before optimization

The hosted stall is not attributed to PostgreSQL connection acquisition or a runtime lock.

1. At 03:00:14Z, authenticated `/api/product-context` was 0.014s; `/api/my-team` was 0.126s at 03:00:15Z.
2. A legitimate intelligence refresh started at 03:00:29Z. During it, My Team completed in 32.008s and 30.804s. Cheap status/Home routes continued returning while those requests were pending.
3. The My Team route reads the already-attached in-memory runtime and builds a governed presentation payload. It does not acquire a PostgreSQL connection or wait for refresh completion.
4. Render CPU rose from ~0.001 cores before refresh to 0.107 at 03:01:00Z and the exact 0.150-core service limit at 03:01:30Z and 03:02:00Z. Memory rose from ~227 MB to ~333 MB against a ~537 MB limit, so memory was not exhausted.
5. The intelligence coordinator executes Forecast/Simulation/Value on a dedicated Python thread in the same single free-tier process. The 50,000-run Simulation is CPU-heavy Python work. This matches the observed request starvation and the service CPU ceiling.

**Root cause:** host CPU scheduling contention on the single 0.15-core free instance while CPU-heavy background intelligence work competes with request-serving threads. Database pooling would not address the measured wait.

## Smallest causal change

`src/fsffl/product/background_jobs.py` lowers only the dedicated intelligence executor thread to Linux nice 10 using `os.setpriority(PRIO_PROCESS, native_thread_id, 10)`. Request-serving threads remain at their normal scheduler priority. This preserves the same process, worker count, job contract, inputs, model math, Simulation seed and canonical 50,000-run count. Unsupported/denied priority adjustment fails open to the previous scheduler behavior and cannot fail the intelligence job.

This is deliberately not a connection pool, new queue/cache/service, worker-count increase, Simulation-kernel rewrite, or fidelity reduction.

## Regression proof

`tests/test_background_jobs.py` adds focused proof that the background executor targets only its own native thread and that a scheduler-priority failure does not fail the intelligence job. Existing job lifecycle/phase-timing tests remain authoritative. Stage 1/2 persistence/runtime and full CI are required before merge.

## Live acceptance still required

After green CI and merge, deploy normally and repeat one bounded authenticated refresh. During the refresh collect small samples for product-context/Home, My Team/Franchise, League and Market where safe. Report sample count plus min/median/max; do not manufacture p95. Confirm no 30-second-class My Team stall, last-good reads remain available, complete evidence promotes only after required phases, and collect CPU/memory around the window.

Stop after Stage 3 live measurement. Do not begin Stage 4 automatically.
