# FSFFL NEXT — 100,000-League Scalable Storage Plan

**Planning checkpoint: 2026-10-10.** This is a documentation-only scale model. It does not amend PR #443, authorize a purchase, change production, or establish a launch capacity. The primary long-term design point is **100,000 leagues**; 1,000/10,000 are growth gates and 1,000,000 is an upper-bound architecture sensitivity.

## Decision summary

A credible path to 100,000 leagues exists if FSFFL treats PostgreSQL as the authoritative transactional catalog/publication plane, immutable hash-verified artifacts as object data, reads as cacheable, and simulations/refreshes as queue-controlled work. The October 10 measurements support payload compression and reconstruction only. They do not prove 100,000-tenant throughput, concurrent-user latency, service capacity, or unit economics.

PR #443 remains the bounded nonproduction write-safety prototype: its tested mechanism and 12 focused tests are preserved, with **PROTOTYPE PASS / PRODUCTION NO-GO**. No source, tests, or PR scope are expanded by this planning checkpoint. Supabase Standard Upload with `upsert=false` is the documented create-only candidate used by the prototype; production still needs a pinned provider-contract test and a PostgreSQL integration/concurrency proof. The tested S3 conditional PutObject route remains NO-GO.

## Evidence labels and baseline

**Measured October 10 real-artifact pair, n=9 latency samples per artifact:**

- Forecast: 161,373 B PostgreSQL JSONB datum; 86,020 B compressed object; exact reconstruction passed; S3 GET/rebuild p95 349.86 ms versus PostgreSQL get/decode p95 354.17 ms.
- Simulation: 118,887 B PostgreSQL datum; 67,816 B compressed object; exact reconstruction passed; object p95 135.78 ms versus PostgreSQL p95 136.97 ms.
- Across those two measured artifacts: 280,260 B PostgreSQL payload versus 153,836 B object payload (45.1% fewer payload bytes).
- Separate prototype evidence: 12 focused offline tests passed, and focused GitHub CI run `38053806931` passed for PR #443 head `863279cff8581d7e7e3bd98c8fcce65551e2ba47`. Storage API and SQLite stand-ins were used; there was no live provider or PostgreSQL integration.

**Extrapolation inputs used below:**

- 12 Forecast + Simulation publication pairs per league per month.
- Historical family averages: 252,025 B PostgreSQL JSONB payload and 137,825 B compressed objects per publication pair. These are portfolio averages; actual league payloads vary.
- Each pair creates two tenant-namespaced immutable objects. At 12 pairs/month, that is 24 objects/league/month or 288 objects/league/year.
- Historical payload identities and PIT/State/manifest/last-good/replay relationships are retained indefinitely in the capacity model. The five-year columns are a planning window, **not** an approved expiration policy or deletion plan.
- No cross-tenant deduplication credit is assumed. Object retention, hash identity and authorization stay tenant-scoped.
- PostgreSQL artifact-reference/index overhead is allowed at 1–4 KiB per distinct object. This is an unmeasured planning range, not observed FSFFL row cost. It excludes other product tables, backup/PITR copies, WAL, bloat, rewrite headroom and Storage's own internal metadata.

## Workload envelope

For a tractable product-level model, assume 8 monthly active users per league, with 25% daily active (2 DAU/league), a peak of 10% of DAU concurrently connected, two refresh intents per DAU per day, one simulation per DAU per week, and four Forecast/Simulation pair reads per DAU per day. This implies 8 MAU per league and treats all memberships as distinct users; shared users across leagues would reduce Auth MAU. Refresh intent is an application event, **not** a provider request; each refresh can fan out to multiple provider/page requests. CDN hit rate is a target sensitivity, not measured.

| Leagues | Daily active users | Peak concurrent sessions (10% DAU) | Refresh intents/day | Simulations/month | Published pairs/month | PG artifact payload written/month | Object payload written/month | Pair-view egress/month |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 2,000 | 200 | 4,000 | 8,600 | 12,000 | 3.0 GB | 1.7 GB | 37 GB |
| 10,000 | 20,000 | 2,000 | 40,000 | 86,000 | 120,000 | 30.2 GB | 16.5 GB | 369 GB |
| **100,000** | **200,000** | **20,000** | **400,000** | **857,000** | **1,200,000** | **302 GB** | **165 GB** | **3.69 TB** |
| 1,000,000 | 2,000,000 | 200,000 | 4,000,000 | 8,570,000 | 12,000,000 | 3.02 TB | 1.65 TB | 36.9 TB |

The pair-view column is 4 pair restorations × 2 DAU × 30 days × 153,836 B per pair per league. It represents client-delivered bytes if every modeled view transfers both objects. The corresponding object GET count is up to two per view. It excludes application JSON, provider data, retries, static assets, protocol overhead and all non-Forecast/Simulation artifacts. At 100k it is ~48 million GETs/month. Apply measured browser/CDN caching before turning this into origin load or a bill.

**Activity burst target:** design for at least 10× the average refresh-intent rate during game-day windows. At 100k, the baseline is ~4.6 refresh starts/second averaged over a day and ~46/s at 10×; provider request rate equals that rate times actual per-refresh provider/page fan-out, which remains unmeasured. Queue, deduplicate identical in-flight work within a tenant/State identity, enforce provider quotas, and shed/retry with bounded backoff. Do not convert user refresh taps directly to unbounded provider fan-out.

**Simulation compute sensitivity at 100k:** 857k simulations/month is a workload count only. If a run consumes 1 / 10 / 60 CPU-seconds, that is about 238 / 2,381 / 14,286 vCPU-hours/month respectively. At an explicitly illustrative $0.05–$0.10 per vCPU-hour, worker CPU alone is ~$12–$24 / $119–$238 / $714–$1,429 per month, before memory sizing, queue idle capacity, retries, autoscaling overhead and API/worker orchestration. FSFFL simulation CPU seconds have not been measured in this exercise.

## Retained data and capacity

| Scale | New object payload/year | Object payload after 5 years | PG artifact payload eligible to move/year | Estimated PG reference/index overhead/year (1–4 KiB/object) | 5-year PG reference/index overhead |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 19.8 GB | 99.2 GB | 36.3 GB | 0.3–1.2 GB | 1.5–5.9 GB |
| 10,000 | 198 GB | 992 GB | 363 GB | 2.9–11.8 GB | 14.7–59.0 GB |
| **100,000** | **1.98 TB** | **9.92 TB** | **3.63 TB** | **29.5–118 GB** | **147–590 GB** |
| 1,000,000 | 19.8 TB | 99.2 TB | 36.3 TB | 295–1,180 GB | 1.47–5.90 TB |

Object values are payload only. Reserve approximately 20% additional *capacity headroom* for operational slack and provider/internal overhead until measured; that is not a statement that the object provider bills 20% overhead. At the 100k point, five-year object capacity planning is therefore about 12 TB. One-time artifact payload moving out of PostgreSQL is large, but database metadata remains: at 100k the 5-year reference/index allowance is 147–590 GB before the rest of the application DB. Allow further headroom for indexes, State/PIT/history, WAL/backups, maintenance and table rewrite.

For context, the current Supabase compute/disk table recommends a 4XL project (16 vCPU/64 GB, 2 TB recommended maximum DB size) at about $960/month and 8XL (32 vCPU/128 GB, 4 TB) at about $1,870/month; this only indicates a possible managed-Postgres capacity range. It does **not** predict that 4XL can sustain 20k active sessions, 48m object GETs, 1.2m monthly publication sets, or 400k refresh intents/day. All clients must go through bounded APIs and connection pooling; user concurrency must never map to direct Postgres connections. 100k requires a staged load test with realistic tenants, publications, history, refresh bursts, read replicas/cache behavior, failover and PITR recovery.

At 1m, even the upper five-year PG reference estimate is ~5.9 TB before 1.5× operational margin (~8.9 TB); a 16XL's documented recommended DB size is 10 TB. Application data, indexes and maintenance headroom can exceed that. Plan stable tenant routing and a shard/partition-ready repository boundary now; do not assume one project will carry the million-league case.

## Operating cost envelope (USD, public list-price inputs; not a quote)

Supabase pricing currently lists Pro at $25/month; Pro includes 100 GB Storage, 250 GB each of cached and uncached egress, and 100,000 MAU. Additional MAUs are currently $0.00325 each. Overages shown in its current docs are $0.0213/GB-month for Storage, $0.03/GB for cached egress and $0.09/GB for uncached egress. Compute is separate and is billed per project. The table below approximates an end-of-year-5 month with all modeled objects retained, a 95% Storage-CDN hit rate, and one database project sized by *data-envelope only*: XL at 1k/10k, 4XL at 100k, 16XL at 1m. Compute tier selection is a placeholder to expose cost order, not an approved sizing recommendation. The tier subtotals show gross Pro plus compute list prices before any applicable compute credits.

| Scale | Pro + illustrative DB compute | Storage overage at year 5 | Egress overage (95% cached) | Auth MAU overage | Priced subtotal/month |
|---:|---:|---:|---:|---:|---:|
| 1,000 | ~$235 (Pro + XL) | ~$0 | ~$0 | ~$0 | **~$235** |
| 10,000 | ~$235 (Pro + XL) | ~$19 | ~$3 | ~$0 | **~$257** |
| **100,000** | **~$985 (Pro + 4XL)** | **~$209** | **~$98** | **~$2,275** | **~$3,567** |
| 1,000,000 | ~$3,755 (Pro + 16XL) | ~$2,113 | ~$1,188 | ~$25,675 | **~$32,731** |

MAU overage assumes 8 distinct MAU per league and the current Pro allowance of 100,000. The egress estimate treats 95% as Storage cached egress and 5% as uncached. At 100k, modeled pair-view egress is 3.69 TB/month: ~3.51 TB cached and ~185 GB uncached. With no caching, the same view traffic would be roughly $310/month uncached overage; with 80% cache it is about $125/month combined egress overage. Cacheability and cache hit rate require production-like CDN/load evidence. Figures use decimal GB/TB and are rounded. Gross Pro+compute subtotal is before applicable account compute credits.

**Not included in the subtotal:** FSFFL web/API and worker fleet, simulation CPU above, Auth/Realtime features or usage beyond modeled MAU charges, extra read replicas, high availability, backup/PITR retention, disk IOPS/throughput add-ons, IPv4, log ingestion, taxes, support/enterprise terms, provider licensing/usage, and non-artifact traffic. Therefore the ~$3.6k/month priced 100k data-plane subtotal is not a total operating-cost forecast. A plausible service-wide budget cannot be closed until load and simulation profiling establish app and worker CPU/memory, and product telemetry measures actual requests and bytes. No spend is authorized.

## Decisions to make now versus defer

**Fix into interfaces and invariants now:**

1. PostgreSQL remains the authoritative source for tenant-scoped immutable artifact registration, complete manifest, generation identity, PIT/State lineage, last-good reference and publication pointer. Blob upload precedes a single DB publication transaction; failure leaves an unreferenced orphan, never a partially advanced pointer.
2. Keep tenant ID and full provenance in every unique key, registry row, manifest and CAS predicate. Require object SHA-256 verification on first use and read; prohibit overwrite. Preserve no cross-tenant dedupe unless a separately reviewed privacy model proves it safe.
3. Version canonical serialization, compression and payload schema. Content-address the exact stored bytes; distinguish artifact-content hash from logical/model/fingerprint identity. Make retries idempotent and publication compare-and-swap safe.
4. Put storage and job execution behind replaceable adapters. Keep per-tenant ownership/routing in an authoritative map so one tenant can later move as a unit to another DB shard without changing artifact IDs or violating its transaction boundary.
5. Model the publication sequence through a transactional outbox/job ledger. Coalesce identical in-flight refresh/simulation work by tenant + State + input fingerprint, apply queue backpressure and bounded retries, and record provider request budgets. Never make correctness depend on best-effort message delivery.
6. Define the historical retention promise before shipping: this capacity model assumes indefinite artifact identity and payload retention. If payload expiration is ever desired, preserve State, PIT, manifest, last-good, replay and lineage independently and require an explicit audited policy.

**Defer until demand and evidence justify it:** buying large database/worker tiers; choosing a specific Postgres shard count or production partition scheme; read replicas; cache/CDN vendor changes; precomputing global capacity; archival/cold tiers; object lifecycle expiration; cross-region replication; a paid-provider migration; and any data migration/reclamation. Defer them behind measurable gates: sustained CPU/IO/connection headroom, p95/p99 under peak load, queue age, provider quota utilization, database physical growth, cache hit rate, egress, restore time, and verified rollback.

## Next engineering decision

Decide whether to authorize a **separate follow-on nonproduction integration proof** that uses PR #443 as the unchanged reference: pinned Supabase Standard Upload with `upsert=false`, byte/hash verification of create-only collisions, and the actual PostgreSQL transaction/CAS/outbox owner under concurrent and injected-failure loads. Put any integration code and tests in a new isolated branch/PR, not #443. Include tenant/State/PIT/last-good/replay assertions and a staged 10k→100k synthetic load profile; report before requesting production wiring. The decision must separately specify allowed test project/credential handling. It does not authorize production writes, migration, purchase, merge or deployment.

## References

- October 10 write-safety evidence: [PR #443](https://github.com/jderhagopian-stack/fsffl-next/pull/443), [Supabase capacity workstream](workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md), [Current Operations](CURRENT_OPERATIONS.md), [Management Continuity](MANAGEMENT_CONTINUITY.md).
- Supabase [Standard Upload concurrency contract](https://supabase.com/docs/guides/storage/uploads/standard-uploads#concurrency); S3 conditional PutObject gate remains documented separately in the workstream.
- Supabase [compute and recommended database sizes](https://supabase.com/docs/guides/platform/compute-and-disk), [compute rates](https://supabase.com/docs/guides/platform/manage-your-usage/compute), [storage rates](https://supabase.com/docs/guides/platform/manage-your-usage/storage-size), and [egress rates](https://supabase.com/docs/guides/platform/manage-your-usage/egress).
