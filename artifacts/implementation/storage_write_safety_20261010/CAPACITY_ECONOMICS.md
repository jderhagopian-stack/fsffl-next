# Storage capacity estimate — Forecast and Simulation only

All storage figures below use binary source bytes as recorded, with MB/GB shown as decimal planning units. They are estimates, not a migration promise or live billing result.

## What the real pair measured

| Pair | PostgreSQL JSONB datums | Supabase object payloads measured | Datum bytes moved out of PostgreSQL | Combined byte reduction before metadata |
|---|---:|---:|---:|---:|
| One Forecast + one Simulation | 280,260 B | 153,836 B | 280,260 B gross | 126,424 B |

Forecast's exact measured object/JSONB ratio was 0.53305; Simulation's was 0.57042. The two-artifact pair therefore stored ~45.1% fewer payload bytes in compressed objects than in the source JSONB datums. Standard Storage would add its own object metadata and the application would retain a small immutable artifact reference plus generation references in PostgreSQL. Those row/index costs were not measured on the project. Allow **1–4 KiB per distinct object** as an explicit planning allowance until `pg_total_relation_size` proves the real cost.

## Existing retained families: upper bound, not physically recovered bytes

The latest canonical read-only capacity snapshot recorded `derived_artifact` at **407,797,760 B physical** inside a **604,040,339 B database**. Current Forecast and Simulation families were **397 rows / 63,057,386 B JSONB datum** and **295 rows / 27,491,129 B JSONB datum**. Their combined datum bytes are **90,548,515 B** across **692 rows**.

Applying only the measured Forecast/Simulation compression ratios to those family datum totals gives an estimated **49.3 MB** of object payload, with **90.5 MB gross PostgreSQL payload datum** eligible to leave the database. At 1–4 KiB of Storage metadata plus application/index overhead per object, reserve another **0.7–2.8 MB** in PostgreSQL. Steady-state net PostgreSQL *logical* reduction is roughly **87.8–89.9 MB** if every one of these payloads is eligible and the relevant consumers have migrated. That is ~22% of the current 407.8 MB relation's size and ~15% of current whole-database bytes.

This does **not** mean `pg_database_size()` falls by 87.8–89.9 MB. Family `pg_column_size` sums do not identify reusable pages, shared TOAST/index space, dead tuples or table fragmentation. Expect physical return to be of the same order only after a measured relation rewrite/repack; until then PostgreSQL may reuse freed pages without shrinking the allocated relation file.

## Per-league annual planning scenario

The existing capacity model uses **12 publications per league per month** (144/year). Historical average Forecast + Simulation datums were ~252,025 B per publication. Applying each measured artifact's own compression ratio yields ~137,825 B of object payload per publication.

| Modeled scale | Forecast/Simulation PG payload eligible/year | Object payload/year | Object+reference metadata allowance/year | Approx. combined byte reduction/year* |
|---|---:|---:|---:|---:|
| 1 league | 36.3 MB | 19.8 MB | 0.3–1.2 MB | 15.3–16.2 MB |
| 10 leagues | 362.9 MB | 198.5 MB | 2.9–11.8 MB | 152.7–161.6 MB |
| 50 leagues | 1.81 GB | 0.99 GB | 14.7–59.0 MB | 0.76–0.81 GB |
| 100 leagues | 3.63 GB | 1.98 GB | 29.5–118.0 MB | 1.53–1.62 GB |

\*Combined reduction subtracts object payload and estimated metadata from gross PG payload movement. Excludes other artifact families, indexes/WAL/backups, duplicate-history retention, egress, GET latency, orphan objects, cache behavior and variation in artifact size. This is an input-workload projection, not measured growth, and must not be added to or double-counted with the canonical **0.169 GB/league/year** all-derived-plus-Market model. Market first-writer PIT remains in PostgreSQL and untouched.

For one measured pair, each complete object restoration entails up to two GETs and transfers about **154 KB compressed** before protocol overhead. Actual object GET counts, CDN cache rates and egress are not measured. The current Supabase Free plan includes 1 GB file storage and 5 GB egress; its published pricing lists Pro at $25/month with 100 GB file storage included and $0.0213/GB-month after that. At the 100-league scenario, the Forecast/Simulation objects alone would reach ~1.98 GB/year, exceeding Free's included file-storage amount; this is a capacity signal only, not a purchase request or approval. Pricing source: https://supabase.com/pricing.

## How PostgreSQL space could actually be returned later

1. Keep every PostgreSQL source payload through shadow reads, exact SHA/Pydantic comparison, restart/replay/PIT/last-good checks, a rollback window, and a separately accepted migration plan.
2. In a later approved migration, remove only payload bytes whose readers have switched and whose original identities/rows, manifests, PIT, replay and last-good references remain preserved. Do not delete State or Market first-writer history.
3. Measure `pg_database_size`, `pg_total_relation_size(derived_artifact)`, TOAST/index sizes, row counts and checksums before and after. Plain DELETE plus autovacuum/VACUUM can make space reusable but is not proof that the relation file or project database allocation shrank.
4. To return disk allocation, plan a table rewrite/repack or new compact relation + copy/swap + old relation drop. That can need temporary space close to the relation size and strong locks; check exact Supabase/extension availability and disk headroom first. Current measured database allocation already exceeds the Free 500 MB allowance, so a rewrite cannot be presumed to fit safely under the present quota. Do not run it without a separate rollback/headroom decision.

