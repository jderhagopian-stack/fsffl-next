# NFLverse historical player-data pilot — FIRST ACTUAL TWO-SEASON COVERAGE RESULT

**Executed:** 2026-10-14; independent read-only GitHub connector runtime; **no Codex, CI, GitHub Actions, Render, Supabase, production API or application writes**.  
**Decision:** **Technical coverage pilot PASS for 2024–2025 archival records**. Not an official-release parity test, production-source acceptance or paid commercial data clearance.  
**Purpose:** Confirm that real historical NFLverse player-week numerical data matches FSFFL's frozen canonical GSIS references; distinguish source absence from identity gaps.

## Sources / reproducibility

- **FSFFL frozen reference:** `jderhagopian-stack/fsffl-next`, [FINAL_CONNECTED_LEAGUE_BOARD_335.csv](https://github.com/jderhagopian-stack/fsffl-next/blob/main/artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv), Git blob `72a2254a50aa96b2636064730f4b7cfccc005c21`, 335 rows.
- **Historical source mirror:** `matttoppi/ffsim`, [provenance README](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/README.md), explicitly identifies [nflverse's `stats_player` official releases](https://github.com/nflverse/nflverse-data/releases/tag/stats_player) as source and states its snapshots were downloaded **2026-08-10**.
- **2024 historical weekly file:** [snapshot in git](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2024.csv), Git blob `cfc8e8951c2d0d47d4a512c672d0a8328ebc147f`, 8,279,397 characters of decoded CSV (Git tree reports 8,279,410 bytes; line endings/connector decoding may differ).
- **2025 historical weekly file:** [snapshot in git](https://github.com/matttoppi/ffsim/blob/main/data/historical/nflverse/weekly_stats/stats_player_week_2025.csv), Git blob `565ecae19212048b44a52f4eb6cf3c7ed41d31e8`, 8,461,825 characters of decoded CSV (Git tree 8,461,830 bytes).
- **Exact matching** via `historical_gsis_id` (FSFFL) = `player_id` (NFLverse). Exclude `season_type=POST` from regular-season matching. No name joins or synthetic zeros. Metadata/provenance from public GitHub source, not a source rights warranty.
- **Version caveat:** These are **third-party Git-tracked archives** captured Aug 10, **NOT** the official release artifacts last updated Aug 13. Their Git blob hashes are *not* the SHA256 release-artifact digests in [our official asset manifest](../../artifacts/research/nflverse_stats_player_release_manifest_20261014.csv). We did not claim official-release checksum parity, 2026 up-to-date coverage, full historical longitudinal accuracy, or canonical 2025 season-model readiness.
- **Data handling:** GitHub connector read only into transient in-memory parsing; no copied NFLverse player rows committed to FSFFL repo, no local permanent raw archive, no model fit, no customer display.

## Quantitative source coverage — actual executed analysis

| Measurement | 2024 weekly archive | 2025 weekly archive |
|---|---:|---:|
| CSV data rows (regular + postseason) | 18,981 | 19,421 |
| Regular-season rows | **18,128** | **18,539** |
| Postseason rows (excluded from match) | 853 | 882 |
| Distinct regular-season source player IDs (all positions) | 1,997 | 2,020 |
| Distinct weeks represented | 18 (1–18) | 18 (1–18) |
| Recorded columns | 145 | 145 |
| FSFFL frozen subjects with GSIS IDs (denominator) | 300 | 300 |
| FSFFL subjects with any regular-season source row | **245** | **293** |
| Frozen ID-mapped coverage | **81.7%** | **97.7%** |
| Subjects with GSIS ID, but no regular-season row | 55 | **7** |

**Combined 2024-or-2025:** **298 of 300** historical GSIS-mapped FSFFL players have at least one regular-season row in one of the archives (**99.3%**). Exactly **2 GSIS-mapped subjects** have none in either season: **Jordan James (RB)** and **Will Howard (QB)**. The separately known **35 of 335** frozen subjects without any historical GSIS ID have **not** been counted as matching. They are largely newer draft/rookie candidates; this is not an argument they should have played in 2024/2025.

### Position-level mapped-ID coverage

| Position | Frozen subjects with GSIS ID | 2024 any regular-season row | 2025 any regular-season row |
|---|---:|---:|---:|
| QB | 56 | 48 | 53 |
| RB | 79 | 59 | 76 |
| WR | 104 | 86 | 103 |
| TE | 61 | 52 | 61 |
| **TOTAL** | **300** | **245** | **293** |

**All 7 unmatched 2025 records exactly agree with the frozen reference's own `MAPPED_NO_2025_ROW` classification:** Tommy DeVito (QB), MarShawn Lloyd (RB), Jonathon Brooks (RB), Jordan James (RB), Will Howard (QB), Deshaun Watson (QB), Tank Dell (WR). This is consistent with a **lack of 2025 statistical participation data**, not a GSIS identity-key failure. An absence of row is not proof of injury, zero fantasy points, free agency, or retirement.

### Available statistical column verification

Both copies have explicit fields `passing_yards`, `passing_tds`, `passing_interceptions`, `carries`, `rushing_yards`, `rushing_tds`, `targets`, `receptions`, `receiving_yards`, `receiving_tds`, and `fantasy_points`. None of those 11 fields were blank/NA in any of the 18,128 (2024) or 18,539 (2025) regular-season source rows. **Nonblank is not a proof that numerical fields are nonzero, individually correct, point-in-time available, or compatible with FSFFL's half-PPR league scoring**; the basic model-integration tests remain pending.

## What this proves

1. **Real archival NFLverse counting-stat player records can join to most of FSFFL's existing 335-player reference through canonical GSIS IDs** without name matching.
2. **2025 matches the frozen identity/history classifications exactly** at the mapped subject level (293 rows present, seven explicit absence statuses). That is a meaningful credibility sanity check and narrows future work to longitudinal/field-level usefulness.
3. The 35 subjects with no GSIS and the seven with no 2025 row are **different** problems: no historical identity ID vs no statistical record in one particular year.
4. The next analysis should work on **actual career/age/usage cohorts, held-out prediction impact, and exact-State Career #405 missing-input relevance** after that workstream is released. A 2024/2025 match does not magically fill Year 1 projected inputs or the nine unresolved Career subjects.
5. The research result does **not** establish production rights, numerical forecast uplift, historical PIT-safe features, or uninterrupted reproducibility against the newest official release.

## Governance and next research stage

- This **read-only archival coverage audit** was possible directly through a connected public GitHub *blob* API despite failed direct release binary downloads from the restricted chat runtime. It required **zero Codex effort, GitHub Actions jobs, app deployment or shared hosted compute**, satisfying [#458 management noninterference](https://github.com/jderhagopian-stack/fsffl-next/issues/458).
- The archive's extra mirror/republication provenance is an **additional rights/version dimension**; [original CC BY 4.0 license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) is the public license signal for licensed NFLverse material. The interim [research-only upstream decision](./nflverse-upstream-contract-reach-decision-20261014.md) supports small offline studies of this 2024/2025 counting-stat data but is not a warranty about original source contracts, or a grant to copy the mirror for public paid redistribution.
- **Next when independently available:** repeat against actual official release SHA256, then expand to 1999–2025 (27 completed seasons), age and career trajectories, field missingness and independent holdout calibration. Any promotion to product inputs needs a further commercial-rights judgment and approval.
- **Do not interrupt Career #405**, use Codex, run CI/Actions, or change Forecast, Career, Simulation 2.0, Render/Supabase production as part of this lane.

**Disposition:** first real-data historical coverage audit **COMPLETE** (archived 2024/2025 snapshots); official release parity and broad longitudinal/value tests **NOT RUN**; production **UNCHANGED**, paid-commercial source adoption **HOLD**.
