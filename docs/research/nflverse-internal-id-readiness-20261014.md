# NFLverse historical pilot — first executable internal ID readiness audit

**Date:** 2026-10-14  
**Method:** Read and parse the existing 335-row FSFFL NEXT CSV in the connected GitHub repository (no NFLverse dataset downloads and no production changes). Exact source: [FINAL_CONNECTED_LEAGUE_BOARD_335.csv](https://github.com/jderhagopian-stack/fsffl-next/blob/main/artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv), blob SHA `72a2254a50aa96b2636064730f4b7cfccc005c21`. Counts checked against all 335 data records, 55 columns.

## Measured result — existing GSIS identity readiness

| Position | Frozen subjects | Historical GSIS present | Historical GSIS absent | Matched by exact name+position | Matched by direct ID |
|---|---:|---:|---:|---:|---:|
| QB | 61 | 56 | 5 | 33 | 23 |
| RB | 89 | 79 | 10 | 67 | 12 |
| WR | 121 | 104 | 17 | 85 | 19 |
| TE | 64 | 61 | 3 | 42 | 19 |
| **Total** | **335** | **300** | **35** | **227** | **73** |

- All 300 nonempty `historical_gsis_id` values have GSIS-form `00-` prefixes; no repeated nonempty GSIS ID found.
- Exactly **35** entries lack `historical_gsis_id`; all have `mapping_status=UNMATCHED` and `history_status=UNMATCHED_COLD_START`.
- The 35 use Sleeper player IDs in the **13xxx** range, and consist of draft/new-player subjects such as Fernando Mendoza, Jeremiyah Love, KC Concepcion, Carnell Tate, and Kenyon Sadiq. No claim is made that an ID has been assigned by NFLverse or that absence indicates a faulty join; their identity availability must be examined at an appropriate historical/NFL-season cutoff.
- **Seven further subjects have existing GSIS IDs but `history_status=MAPPED_NO_2025_ROW`:** Tommy DeVito, MarShawn Lloyd, Jonathon Brooks, Jordan James, Will Howard, Deshaun Watson, and Tank Dell. This is a **2025 evidence-availability distinction, not an ID failure**. Do not invent a zero or label retired.
- A valid GSIS mapping in FSFFL does **not** show that a given historical season/field is complete in NFLverse; that comparison remains unrun until source-data rights allow a scoped read.

## Immediate meaning

A properly cleared NFLverse historical-dataset pilot should use these 300 existing GSIS keys for strict joins; for the remaining 35, first check whether current-season NFL IDs exist **as of evaluation time** rather than forcing name joins or treating no prior NFL performance as a data error.

Coverage outcomes must distinguish:
1. Exact ID available and source has the historical row.
2. Exact ID available but no recorded game/opportunity for that year.
3. Identity assigned only after the historical as-of cutoff (cannot backfill into past point-in-time features).
4. No GSIS ID yet, such as some rookie/draft-only candidates.
5. True source record missing, join collision, or schema/alias error.

No conclusion about the nine unresolved Career #405 outcomes can be drawn from this September frozen reference; the exact current State must be checked separately.

## Rights / provenance finding from public production-code inspection

Official `stats_player` weekly and season files are aggregated in `nflverse-pbp/R/update_stats.R`. `nflfastR::calculate_stats` depends on **both** `nflreadr::load_pbp` and `load_playstats`; derived metrics include EPA/CPOE. Upstream rights to the raw material are a real dependency distinct from the repository's CC BY 4.0 declaration. See [separate evidence and rights gate](./nflverse-stats-provenance-gate-20261014.md).

## Next gate

**Hold external NFLverse raw-file acquisition and product-model training** until source-level free commercial rights for the exact field subset/use are supportable. The first technical step afterward is a bounded read of regular-season player statistics, joined by GSIS to these 335 identities, followed by the up-to-date exact-State roster and historical 2019–2025 panel; report source-week/field missingness, PIT and update dates, and compare to existing FSFFL historical evidence. No production authority changes.

**Operational lane:** research only, separate from active Career #405 / PR #454.
