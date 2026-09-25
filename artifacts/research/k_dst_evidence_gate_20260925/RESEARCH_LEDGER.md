# FSFFL NEXT — K/DST Empirical Evidence & Source-Gate Research Ledger

Date: 2026-09-25
Workstream: Forecast Research
State: ACTIVE — MANAGEMENT AUTHORIZED
Directive: K/DST empirical evidence/source-gate research
Controlling implementation checkpoint: `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`

This ledger records durable evidence as it is established. It does not promote production Forecast authority and is not itself a model implementation artifact.

## 1. FSFFL-retained 2026 preseason K/DST evidence

### Correct preseason cutoff

The NFL's official 2026 kickoff announcement establishes that the regular season began **Wednesday, 2026-09-09 at 8:20 p.m. ET** in Seattle, i.e. **2026-09-10T00:20:00Z**.

Authority:
https://www.nfl.com/news/seahawks-to-kick-off-2026-nfl-regular-season-on-wednesday-sept-9-in-seattle

This corrects an earlier project assumption that treated 2026-09-10/11 as still preseason.

### Production persistence search under the corrected cutoff

Read-only inspection of `fsffl.derived_artifact` with the exact cutoff `computed_at < 2026-09-10T00:20:00Z` established:

- multiple `current_forecast_evidence` artifacts existed before kickoff;
- the last qualifying pre-kickoff artifact recovered is **artifact 63**:
  - kind: `current_forecast_evidence`;
  - computed: `2026-09-09T23:26:16.657633Z`;
  - successful providers: FFToday + Razzball;
  - raw observations as-of `2026-09-09T23:23:53.152680Z`;
  - ensemble provenance effective at `2026-09-09T19:40:02Z`;
  - QB/RB/WR/TE only;
  - no K or D/ST rows;
  - no `fumbles_lost` coordinate.
- no qualifying pre-kickoff derived-artifact payload contains a K or D/ST position marker, kicker/defense raw projection evidence, team-defense projection evidence, or `def_st_*` evidence.
- there is no persisted 2026 `annual_preseason_projection_snapshot`.

### Artifact 145 correction

Artifact **145** is **not** preseason point-in-time evidence under the actual NFL kickoff:

- computed: `2026-09-10T21:36:41.346326Z`;
- retained raw provenance effective timestamp: `2026-09-10T13:32:43Z`;
- both timestamps are after the 2026-09-10T00:20:00Z kickoff instant.

It remains useful retained offense evidence, but it must not be described or migrated as a pre-opener snapshot.

**Current determination:** FSFFL's own governed persistence contains authentic pre-opener **offense** evidence (artifact 63), but no authentic pre-opener K/DST raw projection corpus. Any K/DST preseason recovery must therefore come from an external retained PIT artifact and must preserve its original provenance rather than be relabeled as an FSFFL-native snapshot.

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

### Additional semantics now resolved

Official Sleeper scoring-option documentation further establishes:

- Team Defense contains a **2-Pt Conversion Return** scoring category;
- Special Teams Defense contains **Special Teams TD**, **Special Teams Forced Fumble**, and **Special Teams Fumble Recovery**;
- Special Teams Player exposes separate player-level categories, preserving the `def_st_*` versus `st_*` subject boundary;
- a blocked field goal or blocked PAT counts as a kicker miss;
- points-allowed and yards-allowed ranges are mutually exclusive bucket outcomes;
- Sleeper's general scoring rule is additive when an NFL play truthfully qualifies for multiple enabled scoring categories.

Authority:
https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available

**Residual truth-fixture requirement:** rare combined-event plays still require exact official-stat/gamebook evidence to prove which NFL stats were actually credited. Research should not guess that a blocked kick also creates a forced-fumble/recovery score unless the underlying official play/stat record says so. This is now an outcome-reconstruction fixture requirement rather than an unresolved definition of `def_st_ff`, `def_st_fum_rec`, or the defensive two-point-return category.

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


## 8. 2023-2025 retained weekly K/DST projection panels

A separate public repository, `GiulSposito/newDudesFantasyFootball`, retains source-separated Week 1 K and D/ST raw projection panels across three seasons.

### 2025 Week 1
Commit:
`a6dd835db04060982149faeaa574f5ce43176486`

- K blob `9c64ed8251fe34cebca6278dbaee5f2e387d74eb`, 200 rows.
- D/ST blob `5055a0589a34cc59def68fb793f36f3d8755dafd`, 192 rows.
- retained provider labels include CBS, ESPN, NFL, FantasyPros and FleaFlicker.

### 2024 Week 1
Commit:
`4b2b64f59b91039f2974a4cc7d42782f62412b65`

- K blob `e9a525d0f43e7e8021af99c6d25c7b53e37d43a9`, 228 rows.
- D/ST blob `2076692e34523ff0b15d521994139857e4b08593`, 224 rows.
- retained provider labels include CBS, ESPN, FantasySharks, NFL, NumberFire, FantasyPros and FleaFlicker.

### 2023 Week 1
Commit:
`28571c4b3eb3f147e134c75e269aedec14533f70`

- K blob `4e34afad96983ff0540aa693bdf1ceb3ef697c41`, 190 rows.
- D/ST blob `d13b51f552b116f01770b0671b091501f83c31fa`, 192 rows.
- retained provider labels include ESPN, FantasySharks, NFL, NumberFire, FantasyPros and FleaFlicker.

The same repository contains 2025 code explicitly calling `ffanalytics::scrape_data(... season=2025, week=0)` for K/DST and writing source-level RDS files, but those RDS artifacts are not committed. Its rendered 2025 draft-day material proves a preseason season-projection workflow ran, but does not preserve the source-specific raw full-season package needed by this authority contract.

**Authority implication:** these weekly panels materially strengthen the weekly forecast-error / provenance research path. They do not substitute for a retained full-season preseason raw corpus.

## 9. 2026 K preseason evidence recovered externally

Public repository `Lolindhir/fantasy-app` preserves immutable normalized 2026 preseason K snapshots from **two named providers** before the actual 2026 kickoff.

### FFToday — 2026-09-07 snapshot
Path:
`fantasy-management/sources/external-rankings/projections/fftoday/redraft-kicker-preseason/snapshots/2026-09-07/`

Metadata:
- fetched `2026-09-07T04:02:50.311844Z`;
- source updated date `2026-09-06`;
- horizon: full 2026 regular season preseason projection;
- 32 K rows;
- raw fields: FGM, FGA, FG%, EPM, EPA and provider fantasy points;
- normalized ranking SHA-256:
  `d571fe7a90b5df6e8e84ec894cc8c72f13cbd9ce4369822e691467862b320902`;
- source-raw SHA-256 at snapshot:
  `a65d0fe0de5e26234885c47237f79f487f5d645eb5c020833009709976049099`.

### CBS — 2026-09-07 snapshot
Path:
`fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-kicker-preseason/snapshots/2026-09-07/`

Metadata:
- fetched `2026-09-07T04:12:54.244212Z`;
- horizon: full 2026 regular season preseason projection;
- 33 K rows;
- raw fields include FGM/FGA, made/attempted bins 1-19, 20-29, 30-39, 40-49 and 50+, XPM/XPA and provider fantasy points;
- normalized ranking SHA-256:
  `d471a25720b7b5c45d5b20389b5646a8256ab5882d9b3ed955c15f472670e9eb`;
- source-raw SHA-256 at snapshot:
  `6d4ade5976d18705858d9239020d50a7bb941b4191e180b92d7965da850b87f0`.

Earlier August 8 snapshots are also retained for both providers.

**Recovery status — 2026 K PIT existence/provenance: CLEARED.**

This does **not** make Hodor K scoring authoritative. Hodor separately values 50-59 and 60+ field goals; CBS collapses those into 50+, while FFToday supplies aggregate FGM/FGA. The accepted no-heuristic-split rule therefore still withholds exact Hodor K preseason scoring, and production rights are unresolved.

## 10. 2026 D/ST preseason evidence recovered externally

### FantasyPros retained consensus export

Public repository `McCadeP8/Portfolio`, commit
`a58ebc9fa941d0ad2b0100368b385598d4da4daf`
was committed at `2026-09-08T00:28:38Z`, before the Sept. 9 kickoff.

Retained D/ST export:
`Thanos/Snap Prep/data/raw/fantasypros/FantasyPros_Fantasy_Football_Projections_DST.csv`

Blob:
`49f89db1b4b3440220e3dac805f89c3205f5ef87`

Rows:
98, including consensus/high/low scenarios.

Raw coordinates include:
- sacks;
- interceptions;
- fumble recoveries;
- forced fumbles;
- defensive TDs;
- safeties;
- points allowed;
- yards allowed;
- fantasy points.

A matching K export is also retained:
blob `7cd698bc9414d25f19d0aafef1b59ed044a86df6`.

FantasyPros official support states its NFL weekly projections are aggregated from several sources, naming examples such as CBS, numberFire and STATS:
https://support.fantasypros.com/hc/en-us/articles/115001319147-Where-do-player-projections-come-from

Therefore the FantasyPros artifact is **aggregate evidence**, not automatically a second independent provider vote.

### Sleeper projection snapshot with RotoWire provider attribution

Public repository `MileHighRips/gridlord` preserves a pre-opener 2026 Sleeper projection snapshot:

- file: `frontend/public/data/players.json`;
- commit: `9a52b7c10054038cb386f47ed27f4a49b5c5fe8c`;
- commit date: 2026-09-05;
- blob: `87a6972d023a6a3889fc03fd0ebbfb07e023a18f`;
- 32 D/ST team units.

Retained D/ST raw coordinates include sacks, interceptions, fumble recoveries, blocked kicks, defensive/special-teams TD fields, provider points and points-allowed fields.

An independent public research implementation, `alexanderdfree/Fantasy_Football_ML_AWS`, documents the underlying Sleeper projection payload and preserves the payload field `company: "rotowire"`. Its D/ST normalizer maps:
- `sack`;
- `int`;
- `fum_rec`;
- `ff`;
- `safe`;
- `def_td`;
- `blk_kick`;
- `st_td`;
- `pts_allow`;
- `yds_allow`.

This is strong evidence that the Sleeper projection feed is a **RotoWire provider feed**, not a multi-provider consensus. The endpoint remains undocumented by Sleeper and the RotoWire content rights remain separately governed.

The retained season-level points-allowed bucket-like fields must **not** be treated as a game-level PA distribution. They do not satisfy the accepted distributional contract for league bucket scoring.

**Recovery status — 2026 D/ST PIT existence/provenance: PARTIALLY CLEARED.**

One component-level provider corpus (RotoWire via Sleeper) and one aggregate consensus corpus (FantasyPros) are proven pre-opener. Systematic public recovery did not produce a second provenance-clean, component-level D/ST provider package whose overlap can be ruled out.

## 11. Source-rights closeout

Technical availability and production permission remain separate.

### FantasyPros
Official API materials provide an explicit commercial licensing path, including commercial/API agreements and historical/bulk-data capability. Free/personal tiers do not establish the rights required for FSFFL commercial production.

References:
- https://www.fantasypros.com/api-data/
- https://support.fantasypros.com/hc/en-us/articles/49749297704475-How-do-I-request-access-to-the-FantasyPros-API

**Disposition:** legitimate external resolution path exists: negotiate a commercial agreement that explicitly states ingestion, storage, derived-output, historical access, and — if used for source independence — underlying projection-source identity/selection.

### RotoWire
Current RotoWire terms prohibit automated extraction, archiving/corpus construction, redistribution/derivative use, and AI-oriented ingestion/storage outside authorized use absent written permission.

Reference:
https://www.rotowire.com/termsandconditions.php

**Disposition:** RotoWire-via-Sleeper projection content is not production-authorized by public technical accessibility. Written authorization/licensing is required, and any Sleeper commercial agreement must clarify whether it sublicenses the underlying RotoWire projection content.

### Sleeper
Sleeper's public API documentation states the API is free for non-commercial purposes and directs commercial users to contact Sleeper.

Reference:
https://docs.sleeper.com/

**Disposition:** eventual commercial use is licensing-gated.

### CBS / Razzball
Prior research established current personal/non-commercial or permission-gated terms. Production use remains license/permission-gated.

### ESPN
The projection route is an undocumented internal endpoint, not a public commercial data license. Technical retrieval is not permission.

### FFToday
Public pages clearly expose 2026 K and D/ST projections, but research did not recover an authoritative public grant permitting commercial ingestion/storage/redistribution. “Free to read” is not a production license.

Reference:
https://www.fftoday.com/rankings/

**Disposition:** rights not established; direct permission/license is required before production promotion.

### FantasySharks
No authoritative public commercial-use grant was recovered. Third-party evidence of provider-specific permission reinforces that access can be licensed case-by-case.

**Disposition:** rights not established; direct permission/license is required before production promotion.

**Gate status — current candidate source rights: STILL BLOCKED on external permission/licensing.**

## 12. Empirical-calibration implication

The merged calibration harness requires samples with `independent_source_count >= 2`; it does not hard-code a multi-season minimum. The 2024 archive therefore proves that a two-source empirical exercise is mechanically possible for coordinates shared by multiple providers.

However, full production K/D/ST uncertainty is not yet authorized:

- K providers have a common simple coordinate such as total FGM + XPM, but retained sources do not all preserve the distance granularity needed by arbitrary league rules.
- D/ST common raw coverage is uneven by provider.
- season-average points/yards allowed cannot be used as game-bucket scoring evidence.
- a reduced “sacks + interceptions only” fixture would be useful research but would not represent the full K/DST fantasy-point process.
- public-source rights remain unresolved.

**Gate status — empirical season-error calibration:** PARTIALLY CLEARED.  
A genuine two-plus-source PIT panel is now proven for 2024, correcting the earlier “source #2 does not exist” assumption. What remains blocked is promotion of a **full, rule-representative** K/DST uncertainty model with governed source rights and validated scoring coverage.

## 13. Final gate decomposition

| Gate | Status | Durable evidence | What remains |
|---|---|---|---|
| Historical independent PIT K/DST source discovery | **PARTIALLY CLEARED** | 2024 pre-opener FantasySharks/ESPN/CBS raw K+D/ST corpus; 2023-2025 weekly panels | Full rule-representative calibration panel, rights, and preferably additional full-season PIT vintages |
| 2026 K PIT recovery | **CLEARED** for existence/provenance | pre-opener FFToday + CBS hashed snapshots | Hodor 50-59 vs 60+ exact rule coverage; rights |
| 2026 D/ST PIT recovery | **PARTIALLY CLEARED** | RotoWire-via-Sleeper component snapshot + FantasyPros aggregate before kickoff | second provenance-clean independent component provider; game-level PA/YA distribution evidence |
| Sleeper K/DST scoring semantics | **PARTIALLY CLEARED** | official PA, YA, K, Team Defense, Special Teams Defense/Player and stacking documentation | exact official-stat fixtures for rare combined-event attribution; implementation of the now-documented categories in outcome reconstruction |
| Weekly realized volatility research | **PARTIALLY CLEARED** | merged direct realized-score harness; richer official Sleeper semantics; historical weekly panels | validated complete realized K/DST outcome reconstruction for target rules before promotion |
| Current-forward K/DST Forecast production | **STILL BLOCKED** | architecture + contracts + candidate feeds established | >=2 independent, rights-cleared, rule-complete current providers per required metric; promoted K/DST uncertainty |
| 2026 Hodor K preseason baseline | **STILL BLOCKED** | two pre-opener K providers exist | no exact evidence for separate 50-59 and 60+ rule; rights |
| 2026 Hodor D/ST preseason baseline | **STILL BLOCKED** | one component source + aggregate consensus recovered | no second proven independent component source; no valid game-level PA bucket distribution; rights |
| Private-beta provider operation | **STILL BLOCKED** as a rights assumption | public-access sources identified | written terms/permission must actually cover FSFFL beta ingestion/storage/use; “private beta” is not a license category |
| Commercial production | **STILL BLOCKED** | FantasyPros and Sleeper expose licensing contact paths | executed commercial/data licenses; RotoWire sublicensing/content scope if used |
| Downstream Simulation authority | **STILL BLOCKED** | non-promoting K/DST calibration harness exists | promoted Forecast weekly distributions/uncertainty |
| Downstream Value authority | **STILL BLOCKED** | Forecast subject/scoring contract exists | Forecast authority plus Value-owned K/DST replacement/scarcity economics |
| New-league 7/7 lifecycle acceptance | **STILL BLOCKED** | lifecycle and contract work exists | governed K/DST Forecast authority must actually be promoted first |

## 14. Research exhaustion / external dependencies

Materially distinct authorized public-research paths were exercised across:

- governed FSFFL persistence;
- repository and commit history;
- public retained Git snapshots;
- historical source-specific CSVs;
- current provider surfaces;
- provider API/licensing documentation;
- official Sleeper scoring documentation;
- independent research implementations exposing provider provenance;
- 2026 pre-opener third-party retained snapshots.

The remaining blockers are no longer “try another generic search” tasks. They require one or more of:

1. **provider permission / commercial data licensing**;
2. **a newly supplied or privately retained second 2026 D/ST component-level PIT corpus**;
3. **a source that explicitly projects the 50-59 versus 60+ K split required by Hodor**;
4. **provider-level source decomposition from an aggregate product under license**, sufficient to prove independence;
5. **later Implementation work** to encode the now-documented Sleeper truth fixtures and promote only validated uncertainty.

Research must not weaken the two-source rule, infer aggregate independence, backdate a current page, or treat an unlicensed public scrape as production authority to clear these dependencies.
