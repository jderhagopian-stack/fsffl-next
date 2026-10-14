# Historical player statistics — exact provenance and adoption gate

**Date:** 2026-10-14  
**Program:** [Research #458](https://github.com/jderhagopian-stack/fsffl-next/issues/458)  
**Scope:** Core NFLverse numerical `stats_player` data, not any FFverse model, NFL imagery, or a production provider change.  
**Disposition:** **SOURCE-CHAIN VERIFIED / COMMERCIAL SOURCE-DATA RIGHTS STILL HOLD**. Do not mistake a read-only code/provenance inspection for dataset ingestion, row-by-row coverage, a backtest, or legal signoff.

## Primary factual evidence: how stats_player files are produced

1. [`nflverse-pbp/R/update_stats.R`](https://github.com/nflverse/nflverse-pbp/blob/master/R/update_stats.R) creates `stats_player_week_{season}` using `nflfastR::calculate_stats(seasons=..., summary_level="week",stat_type="player")`. It creates `stats_player_reg_{season}` with `summary_level="season"`, `season_type="REG"`; postseason and combined files are separate. Published into [`nflverse-data` stats_player release](https://github.com/nflverse/nflverse-data/releases/tag/stats_player) as CSV, CSV.gz, Parquet and RDS.
2. [`nflfastR/R/calculate_stats.R`](https://github.com/nflverse/nflfastR/blob/master/R/calculate_stats.R) defaults to `nflreadr::load_pbp(seasons=...)` and separately calls `load_playstats(seasons=...)` to obtain game/play statistical events and GSIS player IDs. Aggregation is indexed by season/week/player_id; EPA/CPOE metrics are calculated from PBP and other inputs. This is **an aggregation of underlying game/play records**, NOT an independently sourced, wholly self-created set of factual box scores.
3. [`nflverse-pbp/R/update_playstats.R`](https://github.com/nflverse/nflverse-pbp/blob/master/R/update_playstats.R) populates the playstats stage through `nflfastR::save_raw_pbp` and `build_playstats`. [`nflfastR/R/save_raw_pbp.R`](https://github.com/nflverse/nflfastR/blob/master/R/save_raw_pbp.R) obtains raw game files from the nflverse raw-release chain. The read-only inspection has not verified every original data collection contract or rights holder in that chain. Its provenance extends beyond the output repository's CC BY 4.0 label.
4. The output API [`load_player_stats()`](https://nflreadr.nflverse.com/reference/load_player_stats.html) advertises player stats intended to match NFL official box scores; it is a *description of the numbers*, not a grant of upstream commercial rights. The [`nflreadr` project terms](https://nflreadr.nflverse.com/) state that NFL data accessed by the package belong to their respective owners, governed by owners' terms.
5. [NFLverse dataset license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) declares CC BY 4.0. The license grants permitted royalty-free commercial use of **rights held by the licensor**, with required attribution and notices, but does not affirmatively warrant all original upstream sources were cleared. [GitHub licensing issue #101](https://github.com/nflverse/nflverse-data/issues/101) asked the precise paid-stats/ML reuse question and was closed without a substantive response; it cannot be counted as an authorization or refusal.

### Legally material distinction (U.S. research guidance, not legal signoff)

The U.S. Supreme Court's [`Feist Publications v. Rural Telephone`](https://www.law.cornell.edu/supremecourt/text/499/340) establishes that historical facts themselves are generally not copyrighted; original selection/arrangement may be protected. That supports a **potential independent-factual-record route** for individual player/week totals. It does **not** eliminate enforceable contractual acquisition restrictions, rights outside copyright, jurisdiction-specific database protections, or special third-party provider terms. [NFL.com terms §1.3](https://www.nfl.com/legal/terms/) prohibit commercial or systematic retrieval from NFL-owned services without written consent; [Sports Reference Terms](https://www.sports-reference.com/termsofuse.html) restrict direct use of site stats/data for ML training and substitute databases. **These terms should not be casually imputed to a separate third-party data acquisition without an actual contractual link, nor should a public GitHub mirror be assumed to waive them.**

## Offline audit implementation delivered (2026-10-14)

A [small Python standard-library audit tool](../../scripts/research/nflverse_historical_coverage_audit.py) is committed on this research branch. It reads an **existing local FSFFL CSV**, counts canonical historical GSIS identifiers, and optionally reads one **already lawfully approved** local historical player-stat CSV. It does **not** download any data, install packages, train a forecast, or change the live product.

- Internal reference-only usage from a repository checkout:

```bash
python scripts/research/nflverse_historical_coverage_audit.py \
  --reference artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv \
  --output /tmp/fsffl-history-internal
```

- Once separately **approved data** and its source-rights manifest have been supplied:

```bash
python scripts/research/nflverse_historical_coverage_audit.py \
  --reference artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv \
  --stats /approved/local/season-or-week-stats.csv \
  --rights-manifest /approved/local/rights.json \
  --output /tmp/fsffl-history-coverage --start 2019 --end 2025
```

- Rights manifest required fields: `{"decision":"GO","allow_offline_research":true,"license_evidence_url":"https://...","origin":"...","file_sha256":"<64 hex chars>"}`. The actual source decision must be made **independently**; filling this JSON does not itself grant rights. The tool checks SHA256 before reading stats, refuses unapproved/no-manifest stats, forbids duplicate reference GSIS, uses exact ID-only matching, and never infers zero/retirement from absent rows.
- Synthetic fixture testing in the research environment passed four local cases (reference-only, approved synthetic CSV, reject missing manifest, reject invalid season window); **GitHub Actions/committed-head CI has not been run**, and no external historical dataset was processed.
- `subject_coverage.csv` and `summary.json` are deliberately written outside the repository by default, to avoid publishing third-party rows. Outputs still require rights review before user display.
- The prior [frozen-335 internal ID audit](./nflverse-internal-id-readiness-20261014.md) recorded **300/335** existing GSIS identifiers. This is a source-readiness result, not a historical NFLverse match rate.

### Commercial launch caveat from separate existing Sleeper dependency

[Official Sleeper API documentation](https://docs.sleeper.com/) states its read-only free API is for **noncommercial** use and directs commercial users to discuss licensing. The [Sleeper Terms, updated 2026-10-06](https://support.sleeper.com/en/articles/5486620-general-terms-of-use) also restrict third-party commercial access/synchronization without written consent. This is **outside the NFLverse data-source decision**, but is material to FSFFL's planned paid launch and should be separately tracked. No assumption that existing League/Sleeper use is commercially cleared, and no interruption of Career #405. There may be a way to operate through approved integrations or authorization; no entitlement has been confirmed.

---

## Smallest commercially relevant rights question

For **only** `stats_player_week_2019` through `stats_player_week_2025`, corresponding `stats_player_reg` season summaries, and completed weeks of `2026`:

- **Fields:** `player_id` / GSIS identifier, `season`, `week`, `season_type`, `game_id`, `team`, `opponent_team`, and basic numerical QB/RB/WR/TE counting events, including attempts, completions, passing yards/TDs/INTs, carries/rushing yards/TDs, targets/receptions/receiving yards/TDs, and known first-down outcomes.
- **Allowed actions sought:** access a released archival dataset via GitHub (not direct scraping of NFL/PFR websites), store internal snapshots with original provenance and SHA256, calculate original FSFFL historical features and calibrated career/forecast parameters, display factual player statistics and original FSFFL-generated predictions in paid SaaS. No resale or bulk redistribution of raw NFLverse files, no logos/headshots/video, no special negotiated commercial fee, no FSFFL proprietary-source release.
- **Separate later question:** per-play advanced features (EPA, CPOE, air yards, YAC, expected points), raw PBP, and third-party snap count, draft, FTN, or injury datasets. These carry different origins and/or modeling/derivative considerations; they are not silently included in narrow basic box-score approval.
- **Right-holder/provenance evidence to establish:** whether the data publisher has a lawful existing basis to make these CC BY numerical files available for the above actions and which upstream use agreements, if any, apply to us. Evaluate actual access contracts separately from copyrightability of bare facts. A specialist commercial data/IP counsel opinion may be needed if upstream records remain ambiguous. No request for fee-bearing licenses.

## Research-only technical readiness (no raw data downloaded)

| Test | Source of readiness | Current result |
|---|---|---|
| Published weekly and regular-season files | `stats_player` GitHub release metadata | Available for 2019–2025; partial 2026 exists; **no row count checked** |
| Developer access from Python | `nflreadpy` under MIT | Candidate loader only; **no data license inherited** |
| Factual schema | `load_player_stats()` docs and `calculate_stats()` code | Stable `player_id`/season/week semantics documented; **actual field schema and null rates unverified** |
| Provenance | `nflverse-pbp` and `nflfastR` generation code | `stats_player` uses both PBP and `playstats`; **ultimate upstream contractual basis unverified** |
| Commercial use without third-party fees or FSFFL code disclosure | CC BY release license plus Feist and external site terms | **HOLD**, not unconditionally cleared |
| FSFFL 335-player + latest exact-State subject joins | Requires acquisition and canonical ID mapping | **NOT RUN** |
| Career historical model improvement | Requires held-out PIT benchmark | **NOT RUN** |

## Determinate next decision (not another open-ended general survey)

**Gate H1: Confirm one of two defensible paths for the narrowly identified basic numeric fields before materializing them into FSFFL products.**

- **Path A — Existing license/release rights:** sufficient actual provenance and existing terms establish paid storage, model training and display of the `stats_player` numerical field subset, with only CC BY notices and without special commercial permission. Then **GO for bounded offline player-coverage pilot**, NOT for automatic production use.
- **Path B — Lawfully independent public factual records:** reliably establish a separate lawful acquisition route for the same bare facts without breaching a site/service contract; legal and data-quality requirements still apply. Then **GO for that explicitly separate source**, with its own ledger, NOT an implied clearance of the mirrored NFLverse files.
- If neither can be established from existing rights and documented provenance, mark the source HOLD (or NO-GO for the specific planned integration if a restriction affirmatively conflicts), and do not spend Codex effort on dataset ingestion.

**When a path passes:** use GSIS/canonical ID-only matching against the 335 frozen reference and exact-State roster; count match/missing/ambiguous by cohort and year, assess 2026 week cutoff, cross-check League scoring, record per-asset checksum, source timestamp, wall time and peak memory. Do not treat missing weeks as zeros or injury/retirement. Do not alter Career #405 or production Forecast/Simulation.

**Conclusion:** source derivation is now specifically documented. The next unresolved question is **commercial reuse of the derived numerical file via the released GitHub source**, not whether nflreadpy is MIT or whether CC BY in general allows paid use. No unsupported claims of permission.
