# FSFFL NEXT — K/DST Empirical Evidence & Source-Gate Research Ledger

Date: 2026-09-25
Workstream: Forecast Research
State: ACTIVE — MANAGEMENT AUTHORIZED
Directive: K/DST empirical evidence/source-gate research
Controlling implementation checkpoint: `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`

This ledger records durable evidence as it is established. It does not promote production Forecast authority and is not itself a model implementation artifact.

## 1. FSFFL-retained 2026 preseason K/DST evidence

### Production persistence search

Read-only inspection of `fsffl.derived_artifact` before 2026-09-11T00:00:00Z established:

- 17 `current_forecast_evidence` artifacts exist between 2026-09-08 and 2026-09-10.
- one `preseason_forecast_baseline` exists at 2026-09-10T21:36:41.346326Z.
- no pre-opener derived-artifact payload contains a K or D/ST position marker, kicker/defense projection evidence, team-defense evidence, or `def_st_*` evidence.
- expanding every pre-opener `raw_forecasts` array yields only QB/RB/WR/TE observations.
- those observations contain only offensive raw metrics (pass/rush/receiving/INT coordinates).
- there is no persisted 2026 `annual_preseason_projection_snapshot`.
- previously retained artifact 145 remains authentic PIT offense evidence only; it is not K/DST evidence.

**Current determination:** FSFFL production persistence contains no authentic retained 2026 preseason K/DST raw projection corpus. External/archival recovery remains a separate research track.

## 2. FSFFL repository/history search

Repository search and commit-history review did not recover a pre-opener K/DST raw-data artifact. K/DST-specific repository work appears after the 2026-09-24 Research/Implementation authorization, while pre-opener provider adapters were offense-only.

This is evidence of absence from the currently indexed canonical history, not yet a claim that no abandoned branch or external retained copy exists.

## 3. Independent historical PIT projection discovery — 2024

A materially stronger historical source was recovered from public GitHub repository:

- repository: `ashishkab0b/fantasy_football_2024`
- repository created: 2024-08-31T09:19:11Z
- relevant commit: `d02f24161e7c08b4e99faacc2481b688b8487704`
- commit author/committer timestamp: 2024-08-31T19:02:12Z
- 2024 NFL regular-season opener occurred after this retained commit.
- repository license: none declared.

The repository's `preseason_analysis_1.Rmd` explicitly requests 2024 week=0 projections for QB/RB/WR/TE/K/DST via `ffanalytics::scrape_data()` across multiple named providers. Source-specific raw K and D/ST CSVs are retained in the commit.

### FantasySharks retained 2024 K

Path:
`data/proj_scrape/fantasysharks/K_projections.csv`

Blob:
`da9e29b728567d876dded3f006ef949265a57a9f`

Rows:
40

Raw columns include:
- XP made / attempts;
- FG made / attempts;
- FG made 1-19, 20-29, 30-39, 40-49, 50+;
- FG misses;
- projected fantasy points;
- source URL.

### FantasySharks retained 2024 D/ST

Path:
`data/proj_scrape/fantasysharks/DEF_projections.csv`

Blob:
`8141794aafce29730771deda816a621d650dfe40`

Rows:
32

Raw columns include:
- sacks;
- interceptions;
- fumbles;
- defensive TDs;
- safeties;
- projected fantasy points;
- source URL.

### ESPN retained 2024 K

Path:
`data/proj_scrape/espn/K_projections.csv`

Blob:
`8eb0bf6ec9aed7697752da34298c5845cf3b3390`

Rows:
32

Raw columns include:
- FG made/attempted 1-39;
- FG made/attempted 40-49;
- FG made/attempted 50+;
- XP made/attempted;
- projected fantasy points.

### ESPN retained 2024 D/ST

Path:
`data/proj_scrape/espn/DEF_projections.csv`

Blob:
`0393f5b60c5e74ff6e9df24001260e75e170a626`

Rows:
32

Raw columns include:
- tackles;
- sacks;
- forced fumbles;
- fumble recoveries;
- interceptions;
- projected fantasy points.

### CBS retained 2024 K

Path:
`data/proj_scrape/cbs/K_projections.csv`

Blob:
`60a7fe60cf5105787374900e0f4a974eb2985850`

Rows:
32

Raw columns include:
- games;
- FG made/attempted;
- FG made/attempted 1-19, 20-29, 30-39, 40-49, 50+;
- XP made/attempted;
- projected fantasy points.

### CBS retained 2024 D/ST

Path:
`data/proj_scrape/cbs/DEF_projections.csv`

Blob:
`fb40ee9100c8b009108f8be56b8104569a560d06`

Rows:
32

Raw columns include:
- interceptions;
- safeties;
- sacks;
- tackles;
- fumble recoveries/forced;
- defensive TDs;
- points allowed / points allowed per game;
- pass/rush/total yards allowed;
- projected fantasy points.

### Authority implication

This discovery materially changes the historical-source assessment:

- a second independent historical PIT K/DST corpus **does exist for 2024** in retained pre-opener form;
- multiple independent provider candidates exist in the same pre-opener repository snapshot;
- historical-looking provider URLs are no longer the provenance basis — the Git commit time plus retained source-specific raw rows are;
- the discovery does **not** automatically clear production/calibration authority because:
  - the public repository declares no license;
  - provider content remains governed by provider rights;
  - 2025 continuity is not yet proven;
  - source/raw granularity differs by provider and may not cover every league scoring coordinate;
  - aggregate sources such as FantasyPros still cannot count as independent of their components without provenance proof.

**Gate status — historical independent PIT source discovery:** PARTIALLY CLEARED.

## 4. 2025 historical false-positive explicitly rejected

A public `heechy33/fantasy_football_assistant` 2025 projection freeze was inspected.

Its own provenance file states:
- frozen at 2026-08-23;
- both candidate 2025 projection sources failed its predeclared vintage audit;
- the freeze cannot recover August 2025 values;
- ESPN exposes no as-of field;
- Sleeper rows were bulk re-synced after the season.

Therefore this corpus is **not** qualifying 2025 PIT evidence and must not be used to satisfy the calibration source gate.

## 5. Rights findings established so far

Public technical availability is not production permission.

- CBS: current terms are personal/non-commercial; production/commercial ingestion remains permission/license-gated.
- Sleeper: public/current terms and API documentation do not establish commercial FSFFL ingestion/storage authority; commercial/business use requires express permission/licensing.
- Razzball: current terms reserve projection/calculation rights and require permission for non-personal/commercial use.
- ESPN: the projection endpoint is undocumented/internal rather than a public commercial data license. Technical retrievability does not establish production/commercial rights.
- FantasyPros: official API documentation offers an explicit commercial tier, including commercial licensing and historical/bulk-data access. Standard/free access is personal/non-commercial. A commercial agreement is therefore a legitimate potential resolution path, but source-independence/underlying-expert overlap must be proven before FantasyPros aggregate evidence can satisfy the independent-source gate.
- FanDuel, 4for4, and Fantasy Guru: public projection content may be technically available, but current terms support personal use and/or prohibit commercial reuse without written permission.

FFToday and FantasySharks rights remain under active research.

## 6. Sleeper scoring truth established so far

Official Sleeper support documentation establishes:

### Points allowed
- opponent offensive field goals count;
- PATs and 2-point conversions count;
- offensive touchdowns count;
- special-teams return touchdowns against the D/ST count;
- an opposing defensive touchdown itself does not count against D/ST points allowed;
- the PAT/2-point try following that defensive touchdown does count.

This supports deterministic points-allowed truth fixtures.

### Yards allowed
- Sleeper uses official NFL gamebook net rushing plus net passing;
- net passing subtracts sack yardage;
- return yards do not affect standard defensive yards allowed by default;
- an optional Special Teams Defense setting can add opposing punt/kick return yards to total yards allowed.

This supports deterministic yards-allowed truth fixtures where the optional setting is specified.

### Subject separation
Official Sleeper documentation separately identifies Special Teams Player scoring and Special Teams Defense scoring, supporting the existing `st_*` versus `def_st_*` subject boundary.

### Still unresolved
Do not infer without exact evidence:
- obscure `def_st_ff` / `def_st_fum_rec` attribution;
- defensive two-point-return edge semantics where exact scored truth is required;
- blocked-kick stacking/attribution across punt/FG/XP plus special-teams fumble events.

## 7. Gate decomposition — provisional

The evidence dependencies are not monolithic.

- **Current-forward expected K/DST production:** does not require a 2026 preseason snapshot. It does require qualifying current independent providers, rule-complete raw evidence, rights/content health, and whatever uncertainty authority the production Forecast contract requires.
- **Season-error empirical uncertainty:** requires genuine historical PIT projections from >=2 independent sources plus realized outcomes. The 2024 discovery materially advances this gate; multi-season validation and rights remain under research.
- **Weekly volatility:** can be estimated from realized weekly outcomes and does not inherently require a second historical projection provider, but target scoring semantics must be reconstructable exactly.
- **Preseason-baseline comparison:** specifically requires authentic 2026 pre-opener K/DST evidence. Absence here must not block separately authoritative current-forward Forecast.
- **Value:** source evidence is necessary but not sufficient; K/DST replacement/scarcity remains Value-owned and cannot be invented by Forecast.
- **Simulation:** requires promoted weekly K/DST distributions/uncertainty; a point estimate alone is insufficient.
- **Private beta:** private-beta status alone does not prove a provider's “personal/non-commercial” license applies to FSFFL. Permission classification remains a rights question.
- **Commercial production:** requires explicit commercial rights from every provider whose data is ingested/stored/used under the production architecture, plus Sleeper commercial/approved-integration permission where applicable.

Further research will turn this provisional decomposition into gate-by-gate closeout dispositions.
