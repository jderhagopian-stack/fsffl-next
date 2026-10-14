# NFLverse historical evidence pilot — research-only checkpoint

**Started:** 2026-10-14  
**Status:** Source-release manifest audit completed; quantitative player-row and forecasting checks **not yet executed**.  
**Lane:** Independent ChatGPT research, separate from Career Coverage #405 / PR #454.  
**Authority:** No changes to production Forecast, Foundation 4, Career, Simulation 2.0, Value, State, model version, provider weights, or live operation are authorized.

## Decision

Use NFLverse as a **candidate historical-evidence and player-identity source**, not an automatic replacement for FSFFL's models. Benchmark FFverse forecasting and empirical weekly-outcome techniques as challengers only. Do not treat realized historical fantasy points or expected points calculated after games as timestamp-valid projections of those same games.

Prior desk review (2026-10-14): `docs/forecast/historical-source-research.md` already approved nflverse/nflreadpy as an outcomes/identity research path. Our existing `src/fsffl/forecast/career_calibration.py` has explicit survival and conditional-production evidence, and Simulation 2.0 already owns league-specific competitive outcomes with 50,000 deterministic trials. We should enrich those established inputs, not duplicate downstream model authority.

## First completed factual check: release availability (metadata only)

Using the official `nflverse/nflverse-data` GitHub release API, checked seasonal asset **names and last-updated timestamps** for each year 2019–2026:

| Release tag | 2019–2025 yearly files | 2026 yearly files | Evidence and caveat |
|---|---|---|---|
| `stats_player` | Available, regular and weekly among release assets | Available; `stats_player_reg_2026.csv` updated 2026-10-14 14:33 UTC | Published asset ≠ verified completeness or forecast |
| `pbp` | Available yearly `play_by_play_YYYY` | Available; updated 2026-10-14 14:31 UTC | Large data; don't acquire until a tested feature requires it |
| `snap_counts` | Available yearly | Available; 2026 updated 2026-10-13 11:01 UTC | Check provider identity and timestamp semantics |
| `injuries` | Available yearly | Available; 2026 updated 2026-10-14 12:50 UTC | A current historical archive is NOT necessarily as-of availability |
| `depth_charts` | Available yearly | Available; 2026 updated 2026-10-14 12:51 UTC | Verify historical effective dates and data provenance |
| `players` | Global identity file, not seasonal assets | Global identity file | Need explicit ID crosswalk and joining audit |

Sample exact released files:
- 2025 player regular-season stats CSV: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2025.csv` (metadata size 882,104 bytes).
- 2026 player regular-season stats CSV: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2026.csv` (metadata size 688,299 bytes).
- 2025 player stats Parquet: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2025.parquet` (metadata size 286,768 bytes).
- Official Python API: `https://nflreadpy.nflverse.com/api/load_functions/`.

**Limit:** These are release-manifest observations only; no asset contents, player IDs, columns, rows, null rates, season-to-season continuity or backtests were actually checked. The research execution environment could read release metadata, but could not retrieve raw GitHub release files. A separate offline executor with approved network access must do the next data-quality step. Do not describe this as a completed 335/252-player audit. Availability dates are when current release assets were uploaded/updated, *not* proof of when the information became knowable during historical seasons.

## Pilot A: historical identity / factual-data quality — NEXT EXECUTABLE GATE

**Population:** frozen 335-player regression cohort; the current exact-State roster population (last PR #454 description: 252 rows, 243 Career numerics and nine explicit unresolved); a bounded cross-position rookie/deep-player sample, plus 2019–2025 historical player-season subjects. Keep these categories distinct. Obtain exact canonical subject/State manifests at execution time; never infer current counts from old PR descriptions.

**Data:** start with small player-season and player-week stats and NFLverse player ID crosswalk. Add historical snaps, roster status, draft, injuries/depth charts only if each field is relevant and provenance can be verified. Historical 2019–2025 is the primary analysis window; 2026 completed weeks are a separate freshness and contemporaneous-identity check, not a full-season holdout.

**Row-level output:** for every subject report canonical FSFFL ID, NFLverse/GSIS identity, exact/missing/ambiguous match status, source/season/week, relevant field availability and types, source availability/effective timestamp, missing/null or coverage reasons, and whether the evidence supplies a previously missing *input* rather than an invented downstream value. For the nine unresolved Career cases, record individual evidence checked and do not claim NFLverse resolves them without a complete valid forward-input chain.

**Metrics:** match rate among identifiers with comparable source eligibility, ambiguity/collision rate, per-season field completeness, historical subject continuity, raw-data revisions, contemporaneous freshness, artifact MB, run wall time, CPU and peak RSS. Provide numerator and denominator by position/cohort; never report a global percentage without missingness definitions. Explicitly distinguish player truly unavailable from join failure, no opportunities, unreported game, or model-ineligible candidate.

**Acceptance:** reproducible manifest (source asset URL/commit, retrieval time, SHA256, schema fingerprint), raw evidence retained only where rights permit, no current player names joined loosely, no silent zero-fill, deterministic aggregates. Publication forbidden.

## Pilot B: forecast challenger — AFTER A

Compare lagged player usage/snap/opportunity features and `ffopportunity`-style expected opportunity metrics with an agreed frozen FSFFL Year-1 model/reference over **the same** historical cohorts and targets. Keep ranking ECR separate from raw-stat projections; expected fantasy points from completed plays is retrospective evidence and must be lagged before predictive testing. Use chronological rolling-origin development/test splits, with strictly earlier training and PIT-available features.

At minimum: QB/RB/WR/TE MAE, bias, interval coverage/CRPS where distributions support it, healthy/availability cohorts, deep-player coverage and bootstrap confidence intervals. Report `baseline`, `baseline + NFLverse features`, and where feasible `isolated opportunity challenger` using identical point-in-time targets. Judge improvements by held-out accuracy, calibration, coverage and compute—not an attractive current-season correlation. No promotion on an aggregate win masking worse QB/rookie performance.

## Pilot C: Career/Simulation methods — AFTER B

- **Career:** test historical survival/remaining-relevant probability and conditional future fantasy production separately. Missing stat rows are not proof of retirement or zero. Compare to the accepted Career transition reference, not replace 335 numeric regression expectations inside #405.
- **Simulation:** compare empirical player-week skew, tails, variance, rare events and conditional availability to accepted weekly distribution assumptions. `ffsimulator` is an experimental MIT-coded R *research comparator*, not a drop-in for FSFFL's fantasy rules, replay, origin picks or 50k kernel. `nflseedR` simulates real NFL seasons; defer absent an explicit team-environment modeling question.

## Rights, resource and architectural gates

- `nflreadpy` is MIT-coded; `nflverse-data` repository declares CC BY 4.0. Upstream dataset rights are separate and must be reviewed dataset-by-dataset before commercial use or redistribution.
- `ffopportunity` code GPL v3, included models and expected points data CC BY-SA 4.0: investigate legal implications before code/model/data reuse. Studying published methods is not commercial clearance.
- Do **not** install R, Polars, or bulk PBP into the production Render web runtime for a research test.
- Do acquisition, joins, fits and benchmarks offline with bounded memory/transfer; retain versioned shared evidence outside browser requests.
- No code changes, automatic PR merge, deployment, Career #405 interruption or new live provider source authority; one explicit Management gate if a promoted change is supported.

## Operational separation / next action

**Career #405:** continues independently through its established PR #454 review, full-suite/CI and release gates. This pilot must not become a prerequisite for that work.

**NFLverse research:** obtain actual dataset bytes via an independent offline runner with network access, load small 2025/2026 player stats and global player IDs, compute first exact-ID join against frozen-335 and the latest saved roster cohort, then expand coverage by season and source only where useful. Attach a reproducible audited table and unresolved-case ledger to this research record. Only after the first quantitative comparison decide whether to authorize a narrowly scoped implementation PR.

**Current handoff:** `metadata verified; dataset bytes not accessible in current ChatGPT research runtime; quantitative pilot pending independent execution`.

## References

- `docs/forecast/historical-source-research.md`
- `docs/forecast/modern-historical-window.md`
- `docs/operations/workstreams/CAREER_COVERAGE_EXTENSION.md`
- `docs/operations/directives/20260928_SIMULATION_2_0_PROGRAM.md`
- `https://github.com/nflverse/nflverse-data/releases/tag/stats_player`
- `https://github.com/nflverse/nflverse-data/releases/tag/pbp`
- `https://github.com/nflverse/nflverse-data/releases/tag/snap_counts`
- `https://github.com/nflverse/nflverse-data/releases/tag/injuries`
- `https://github.com/nflverse/nflverse-data/releases/tag/depth_charts`
- `https://github.com/ffverse/ffopportunity`
- `https://github.com/ffverse/ffsimulator`
