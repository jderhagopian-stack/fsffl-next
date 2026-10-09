# FSFFL NEXT — Storage Architecture Foundation (nonproduction POC)
Management-gated handoff • 2026-10-08 • production unchanged

## Scope and decision

Start from main `785d79ee0191293ae86a6e47a341202bf15345e5`.
Accepted Supabase A (pooled transport) and B (market-value batch writes) remain
untouched. Tranche C whole-publication skip is CLOSED. Career #405 PR2,
Supabase D-F and Player Intelligence #436 remain independently paused.

**Recommend a deliberately small hybrid:** existing PostgreSQL retains small
immutable-artifact identities, hash/codec/length/object references, metadata
reads, PIT history, exact State/team/model and generation fences, and the
existing atomic publication owner. Large immutable Forecast, Simulation,
presentation and other verified eligible payload bytes live in an
S3-compatible object store, compressed and content-addressed. No global
provider-only deduplication without a separate identical-semantics/tenant proof.
No second lifecycle controller. The actual provider for production is NOT
selected or provisioned in this tranche.

This public GitHub repository MUST NOT contain copies of identifiable
production raw data. Real Forecast (id 9196) and Simulation (id 6730)
payloads were inspected read-only and reconstructed transiently in memory;
raw copies were not checked in or deployed. Production-copy LZW32
experimental codec measurements below are NOT the production zlib codec.
The committed stdlib executable zlib adapter is tested with anonymized
representative Forecast/Simulation fixtures; full production-zlib
equivalence and actual cloud latency remain acceptance gates in Phase 2.

## Executable proof

* `hybrid_adapter.py`: isolated immutable content-addressed local object backend
  (filesystem S3 stand-in), SQLite metadata stand-in, zlib canonical-JSON v1,
  write-blob-before-metadata, SHA-256 verification, exact 6-coordinate identity,
  process restart and explicit legacy fallback; `PersistenceContractBridge`
  retains the existing `ReusableArtifactRecord` API.
* `tests/test_storage_foundation_poc.py`: focused round-trip, identity,
  first-writer conflicts, idempotency, missing/corrupt object, tenant/model/State
  isolation, process restart, legacy fallback, failed write, memory, and original
  application-facing `ReusableArtifactRecord` equality.
* Run locally from repo: `pytest -q tests/test_storage_foundation_poc.py`.
  No production secrets or network are required. GitHub CI includes this test
  in focused PR validation. Keep PR draft until Management acceptance; no
  stable-head full suite or merge-ready claim on this draft.

Independent local synthetic sample with stdlib zlib level 6, 15 iterations:
Forecast-shaped 87,854 canonical JSON bytes => 21,353 zlib bytes (4.11x),
encode/store median 13.536 ms; read/decode median 16.237 ms; sampled
Python allocation peak 1,135,688 bytes. Simulation-shaped 52,985 => 13,302
bytes (3.98x); encode median 8.421 ms, read median 10.142 ms,
Python allocation peak 710,774 B. In local focused environment 8 tests
passed, 1 optional private real-export test skipped. These tiny fixtures
DO NOT predict production latency or compression.

Real production **complete** Forecast JSON test copy (3,039,440 JS
characters) reconstructed exactly after an isolated LZW32 bytecode round-trip:
408,252 encoded bytes, encode 842 ms, decode 43 ms; corresponding retained
PostgreSQL JSONB datum 159,137 B. Complete Simulation (552,937 chars):
214,156 LZW32 bytes, 122 ms encode / 18 ms decode; PostgreSQL datum
89,037 B. The temporary codec is less compact than PostgreSQL JSONB;
it is **not** recommended for production. The ephemeral tests demonstrate
whole-real-payload reconstructability without sharing raw production user data,
but do NOT establish end-to-end zlib+object-cloud compatibility.

## Physical measured baseline (Oct 8, not extrapolated)

PostgreSQL database: 590,605,459 B; `derived_artifact`: 400,146,432 B
(including 392,757,248 B shared TOAST and index). Family columns below are
`sum(pg_column_size(payload))`, NOT individually allocated physical files.

| Artifact family | Rows | JSONB datum bytes | SQL JSON text bytes |
|---|---:|---:|---:|
| Presentation surfaces | 2,509 | 154,089,092 | 988,588,595 |
| Forecast | 397 | 63,057,386 | 1,289,698,949 |
| Simulation | 295 | 27,491,129 | 177,908,757 |
| Player-future continuity | 157 | 26,871,747 | 124,923,590 |
| Supplemental forecast coordinate | 294 | 25,732,613 | 349,086,777 |
| Value | 357 | 19,298,066 | 482,476,159 |
| User/league last-good combined | 468 | 24,858,187 | 273,583,428 |

Separate physical relations: Market first-writer history 119,693,312 B,
PIT State history 24,862,720 B and projection observations 23,461,888 B.
Never assume removing 154 MB of presentation JSONB yields 154 MB physical
recovery; 2,471 of 2,509 surfaces were found exact-manifest/published-
generation referenced and their historical/recovery retention is governed.

## Marginal economics: assumptions versus facts

Per-publication **existing-data average datum** proxy, assuming ONE new
Forecast (~158,835 B), Simulation (~93,190 B), Value (~54,056 B), and
8 presentation surfaces (~491,316 B): ~797,397 B compressed JSONB datum.
Market first-writer table total physical bytes / retained rows ~704 B/row;
535 NEW Market observations per publication adds ~376,853 B *physical
historical allocation proxy*. Combined ~1,174,250 B/publication.
These are ratios of mature shared relations, not incremental marginal WAL,
TOAST, transaction or true reserved disk measurements. Publication multiplicity,
unchanged IDs, supplemental, dynasty and last-good can change actual cost.

Base modeled workload **12 publications / league / month, 12 months**;
at least 535 new first-writer Market observations per publication only in
the upper modeling branch (replays may insert none):

| Leagues | Publications/year | Derived proxy GB/year | Market PIT proxy GB/year | Combined PG proxy GB/year |
|---|---:|---:|---:|---:|
| 1 | 144 | 0.115 | 0.054 | 0.169 |
| 10 | 1,440 | 1.148 | 0.543 | 1.691 |
| 50 | 7,200 | 5.741 | 2.713 | 8.455 |
| 100 | 14,400 | 11.483 | 5.427 | 16.909 |

Season proxy, 5 months at 12 publications/month: ~70 MB
combined/league/season. Low/stress alternative: 4 versus 30
publications per month scales all variable estimates by 1/3 or 2.5.
**There is no demonstrated commercial 100-league Free-plan capacity**.

Object-storage compressed size is UNKNOWN on full real zlib blobs.
Sensitivity only, **0.8x-3x** the derived PostgreSQL JSONB datum:
at 100 leagues after 12 months ~9.2-34.5 GB objects; PostgreSQL still
could grow ~5.4 GB from first-writer Market PIT *plus metadata, history,
indexes and other non-migrated families*. Hybrid offloading large derived
payloads is necessary, not sufficient to make PostgreSQL-free costs flat.

Illustrative request traffic at 12 publications/month, 11 writes/publication,
and 25 exact object reads/league/day: 100 leagues => 13,200 PUT/mo and
75,000 GET/mo. Existing accepted restart comparison read 25 artifacts
totalling 22,318,183 logged serialized bytes. At one equivalent uncached
restore/league/day, 100 leagues would represent ~66.95 GB/month of
**uncompressed logical** read material. This is NOT measured wire egress
or cloud cost; object transfers need compression/caching measurements.
CPU and memory for real production zlib, networking p95 and retries are
unmeasured; cannot claim a speedup or unchanged RSS.

## Alternatives and selection

A. Better PostgreSQL JSONB/TOAST and index hygiene: few moving parts,
transactional and fast; still ties payload growth, bloat and read egress
to DB capacity. Compression already strong (~20x for production Forecast
JSON, ~6x Simulation). Insufficient structural change at 50-100 leagues.

B. Compressed immutable artifacts held in PostgreSQL as bytea or a
standalone file repository: canonical digest and easy versioning, but if
bytea remains in PostgreSQL its TOAST/disk limit remains; if file repository
lacks authoritative transaction metadata, failover/recovery is fragile.

C. **Selected**: PostgreSQL small metadata and versioned immutable bytes
in S3-compatible object storage behind ONE existing persistence adapter.
Cheap immutable objects, independent capacity axis and deterministic
content checks, with extra object GET latency, network failure modes and
dual-system publication/recovery gates. Avoid vendor-specific framework;
prototype proves codec/identity boundary only.

Illustrative October 2026 vendor pricing: Cloudflare R2 Standard $0.015
per GB-month after 10 GB included, Class A $4.50/million after
1 million included, Class B $0.36/million after 10 million included,
direct egress free, per official pricing
https://developers.cloudflare.com/r2/pricing/ . Supabase object storage
Free 1GB / Pro 100GB and $0.0213/GB-month beyond plan quota:
https://supabase.com/docs/guides/storage/pricing .
Supabase Free PostgreSQL remains 500MB/project, Pro included DB 8GB and
additional DB disk priced separately:
https://supabase.com/docs/guides/platform/billing-on-supabase .
At 100 leagues, sample base 9.2-34.5GB objects may incur roughly $0-$0.37
R2 Standard storage/month after free capacity, exclusive of account,
compute/SQL, API, caching, backups, inter-region effects, actual rate
rounding and any storage durability requirements. Vendor costs are
illustrations, not a procurement or infrastructure approval.

## Phased implementation and acceptance (NOT authorized yet)

### Phase 1 — Immediate capacity stabilization (1-3 engineer-days, planning)
Keep A+B; metric dashboards of physical DB, TOAST growth, artifact rows,
R2 hypothetical bytes, last-good and publication, write/read/error p95.
Preserve separate read-plan approval for nonunique ~31.79MB Market history
index; even if removed it leaves >21.94MB quota deficit. No database
mutations or billing changes in this gate. Escalate with explicit minimal
temporary paid-access evidence only if real writes become blocked.

### Phase 2 — Harden adapter and object commit semantics (5-10 days estimate)
Select supported S3-compatible backend and credential model via separate
Management approval; use existing `PersistenceStore` boundary, immutable
zlib/optional later governed codec marker, tenant/private or explicitly
approved shared-semantic namespace, content SHA-256, version and byte length.
Persist object and verify its read-back SHA **before** publishing small PG
metadata. Existing manifest-first/pointer-last publisher is unchanged.
Bound concurrency, object GET timeout, retries only pre-commit or
idempotent exact-key, and memory. Test against **complete real production
artifact copies in a private isolated nonproduction run**, including
`decode_forecast_evidence` and `decode_simulation`, replay, PIT and
tenant/fencing, corruption, restart and rollback. Reject production if
reader p95 worsens materially (proposed threshold <=20% versus matched
baseline), memory exceeds existing ~429.5MB working budget, or publication
atomicity differs. This is NOT yet proven.

### Phase 3 — Backward-compatible existing-history migration (5-15 days estimate)
Read-only existing derived artifacts -> deterministic canonical serialization
-> immutable object -> checksum and decoder verification -> **shadow** blob
pointer under exact original five-key artifact identity; do not recompute
model truth. PostgreSQL original remains the source of truth during shadow.
Dual-read comparator requires exact byte digest + hydrated
`ReusableArtifactRecord`/Pydantic contracts, publication generation and
selected-team State. Cut over a bounded family/time cohort only after
explicit acceptance, preserving legacy read rollback and last-good reachability.
Never rewrite Market first-writer PIT or historic State/replay rows.

### Phase 4 — Measured physical recovery + scaling (separate risk gate, 3-10 days + soak)
After dual-read acceptance, evaluate actual archived PostgreSQL byte
reachability, object backups, PIT/replay retention and rollback period.
Only a separately approved plan may remove old bytes and perform a
physical shrink/repack/rewrite; normal DELETE/VACUUM does not guarantee
DB file release, and rewrites can require full duplicate temporary disk,
strong locks or paid headroom. Measure pg_database_size before/after,
TOAST/index allocation, row/source checksums, restore and read p95, RSS,
GET/PUT/error/egress and actual 1/10/50/100 modeled cardinality, with
bounded synthetic tests, not 100 live leagues. Fail closed if data
integrity, exact State/publication, last-good, replay or rollback breaks.

## Gate result

**FOUNDATION POC: demonstrated at an isolated adapter boundary; NO GO for
production without Phase 2 full-real-zlib/backend parity and operational
reliability.** No live schema, migration, paid services, code deployment,
provider refresh, retention or deletion. PR intentionally draft/unmerged
pending Management acceptance and one stable-head full-suite merge gate.
