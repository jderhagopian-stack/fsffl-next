# FSFFL NEXT Forecast Research — K / D/ST + New-League Bootstrap

**Research date:** 2026-09-24  
**Workstream:** Forecast Research  
**Canonical directive:** `docs/operations/workstreams/RESEARCH.md` on `ops/management-workflow-20260924`  
**Research branch:** `research/forecast-k-dst-bootstrap-20260924`  
**Status:** implementation-ready architecture complete; production K/DST promotion remains gated by historical calibration evidence and source-rights review.

---

## 1. Executive determination

The active production incident is two separate Forecast problems and they must remain separate:

1. **K / D/ST Forecast support**
   - K is a distinct Forecast family, but remains an individual-player asset.
   - D/ST is not a player. It must be represented as a canonical NFL team-unit Forecast subject.
   - Neither family may be routed through the existing QB/RB/WR/TE raw-stat or uncertainty machinery.
   - The current two-independent-source rule remains the default production authority. It must not be weakened just to make the newly connected league load.
   - Current public provider evidence is useful but does **not** universally span arbitrary Sleeper K/DST scoring. Provider eligibility therefore has to be evaluated against the active league rule set at the raw-stat level.

2. **New-league late-connect bootstrap**
   - FSFFL NEXT already has the correct durable concept: a league-agnostic annual preseason raw-stat snapshot that can later be rescored under any league's rules.
   - Production has no persisted 2026 `annual_preseason_projection_snapshot`.
   - A genuine point-in-time 2026 offense artifact does exist: legacy preseason baseline artifact **145**, derived from FFToday + Razzball, with **1,675 raw ensemble observations**, effective 2026-09-10 13:32:43Z.
   - That evidence can be migrated as immutable season-level evidence if and only if lineage, timestamps, source identities, hashes, and raw observations are preserved byte-for-byte/equivalently. It must not be regenerated from current pages or backdated.
   - The preserved offense evidence is still incomplete for arbitrary league scoring: it contains no `fumbles_lost` observations, while the newly connected league scores `fum_lost=-2`. Current scoring code can silently omit this because `FUMBLES_LOST` is not in the material-domain completeness guard. The bootstrap contract must close this hole.
   - No equivalent authentic two-source 2026 preseason K/DST raw artifact is presently persisted. Therefore K/DST preseason evidence must remain unavailable unless a separately verified point-in-time reconstruction satisfies the same authority rules.

**Bottom line:** implement additive K/DST subject + metric contracts, rule-aware source eligibility, separate empirical uncertainty families, and an evidence-preserving late-connect bootstrap. Do not weaken offensive Forecast authority and do not fabricate a 2026 K/DST preseason baseline.

---

## 2. Evidence actually inspected

### Repository authority

The research read the canonical operating state from:

- `docs/operations/OPERATING_PROTOCOL.md`
- `docs/operations/CURRENT_STATE.md`
- `docs/operations/ACTIVE_WORKSTREAMS.md`
- `docs/operations/ACCEPTANCE_GATES.md`
- `docs/operations/workstreams/RESEARCH.md`
- `docs/forecast/next-2-design.md`
- `docs/forecast/historical-source-research.md`
- `docs/forecast/modern-historical-window.md`

Relevant implementation contracts inspected include:

- `src/fsffl/state/models.py`
- `src/fsffl/providers/sleeper.py`
- `src/fsffl/providers/sleeper_snapshot.py`
- `src/fsffl/forecast/models.py`
- `src/fsffl/forecast/league_scoring.py`
- `src/fsffl/forecast/live_ensemble.py`
- `src/fsffl/forecast/current_runtime.py`
- `src/fsffl/forecast/annual_preseason_snapshot.py`
- `src/fsffl/forecast/preseason_baseline.py`
- `src/fsffl/forecast/projection_history.py`
- `src/fsffl/forecast/season_uncertainty.py`
- `src/fsffl/forecast/weekly_volatility.py`
- current FFToday/CBS/NFL Fantasy/Razzball adapters
- Value and Team Utility interfaces that consume `ForecastObservation`.

### Production evidence

Read-only production inspection established:

- Two league snapshots are persisted.
- Original FSFFL has no K/DST starters.
- The newly connected league includes one K and one D/ST starter.
- Production contains **no** `annual_preseason_projection_snapshot` for 2026.
- Legacy preseason baseline artifact **145**:
  - kind: `preseason_forecast_baseline`
  - scope: original FSFFL league-season
  - evaluation timestamp: 2026-09-10T21:36:41.346326Z
  - successful sources: FFToday + Razzball
  - raw ensemble rows: 1,675
  - positions: QB/RB/WR/TE only
  - metrics: pass yards/TD/INT, rush yards/TD, receptions, rec yards/TD
  - no `fumbles_lost`
  - raw ensemble provenance effective time: 2026-09-10T13:32:43Z
- Prior retained implementation evidence proves baseline 145's raw arrays exactly match its persisted source artifact and were not freshly refetched.

### Current newly connected league scoring that materially drives this research

The active non-zero K rules include:

- FG made by 0-19 / 20-29 / 30-39 / 40-49 / 50-59 / 60+ bands
- overall FG miss penalty
- XP made and XP miss

The active non-zero D/ST rules include:

- sacks
- interceptions
- forced fumbles
- blocked kicks
- safety
- defense TD
- defensive two-point return
- fumble recovery
- special-teams defense TD / forced fumble / recovery
- mutually exclusive points-allowed bands

The league also has player special-teams rules (`st_*`) in addition to team-defense special-teams rules (`def_st_*`). Those are different scoring subjects and must not be collapsed.

---

## 3. Current-interface diagnosis

### 3.1 State understands K and D/ST only partially

`Position` and `RosterSlot` already include K and DST. Sleeper normalization maps `K` and `DEF`.

However:

- roster and player models are player-shaped;
- Sleeper D/ST roster IDs are team-like identifiers (for example `DET`, `CLE`);
- unrostered enrichment in `sleeper_snapshot.py` only includes QB/RB/WR/TE, so K/DST free-agent universe coverage is incomplete;
- D/ST should not be forced to masquerade as a human `Player` in Forecast merely because Sleeper uses a common roster identifier namespace.

### 3.2 Forecast observations are player-centric

`ForecastObservation` is keyed by `player_id` and `position`. Raw metrics are offensive plus `FUMBLES_LOST`; no K/DST raw metric vocabulary exists.

Therefore D/ST cannot enter the authoritative Forecast contract honestly without an additive subject model.

### 3.3 Provider adapters are offense-only even when provider pages expose K/DST

The current FFToday, CBS, NFL Fantasy and Razzball full-season adapters request only QB/RB/WR/TE. This is an adapter limitation, not evidence that the providers lack K/DST data.

### 3.4 Current scoring coverage is rule-name aware but not evidence-completeness aware enough

`league_scoring.py` intentionally fails closed on configured K/DST rules when the league starts those positions, which is correct.

But it has a separate defect relevant to late-connect replay:

- `fum_lost` is classified as a supported linear rule;
- `FUMBLES_LOST` is not included in `_MATERIAL_SCORING_DOMAINS`;
- if all other offensive metrics exist but fumble-loss evidence does not, the current scorer can still publish fantasy points with the active fumble penalty omitted.

The replacement contract must be **active-rule complete**, not merely broad-domain complete.

### 3.5 Uncertainty is offense-only by design

Production full-season uncertainty has promoted empirical calibration only for QB/RB/WR/TE, using the retained 2024-2025 equal-weight two-plus-source benchmark. Missing K/DST calibration correctly raises.

No K/DST implementation may reuse an offensive position's residual coefficient.

### 3.6 Downstream interfaces are mixed

Team Utility lineup eligibility already contains K and D/ST slots, but it consumes player-shaped `ForecastObservation` keyed by `player_id`. Value `intrinsic_runtime.py` explicitly restricts intrinsic paths to QB/RB/WR/TE.

Therefore:

- lineup/simulation can become K/DST-aware after a Forecast-subject adapter;
- intrinsic Value needs an explicit K/DST extension and replacement/scarcity research boundary;
- K/DST must not be omitted from team competitive simulation once the league requires them;
- Decision/Search must consume whatever Value promotes, not create K/DST forecasts themselves.

---

## 4. Source inventory

This table is a **capability inventory**, not automatic production approval. Every live use still needs provenance, content-health checks, PIT semantics, rights approval, and rule-level metric coverage.

| Source | Role | K raw detail | D/ST raw detail | PIT / history | Independence | Key limitations |
|---|---|---|---|---|---|---|
| Sleeper league API | rules / roster identity / realized-score validation, not Forecast source | league scoring config; rostered kicker IDs | team IDs appear in roster namespace; league scoring config | current league state; historical matchup access | N/A | public API is stated as non-commercial; commercial product requires licensing contact |
| FFToday | independent projection candidate | FGM, FGA, FG%, XP made/attempted; dated 2024/2025/2026 preseason pages | sacks, FR, INT, defensive TD, points allowed, pass/rush yards per game, safety, kick-return TD | strong dated preseason page evidence for 2024/2025/2026 | independent candidate | no FG distance bins; no exact 60+ split; D/ST lacks several active Sleeper events and aggregate PA cannot exactly score per-game PA buckets |
| CBS Sports | independent projection candidate | FGM/FGA; attempts/makes by 1-19,20-29,30-39,40-49,50+; XP | INT, safety, sacks, tackles, fumble recoveries/forced, defensive TD, PA/PPG, yards allowed | current pages available; URL path can look historical while content resolves to current year | independent candidate | content-year/horizon validation mandatory; K 50+ does not split 50-59 vs 60+; D/ST lacks several special-teams/blocked-kick fields; PA is aggregate |
| Razzball | independent projection candidate | FG/FGA, XP/XPA, made FG bands through 50+ | tackles, sacks, INT, forced fumbles/recoveries, safety, return TD, return yards, points/yards allowed and other team components | current / ROS; provider pages expose update timestamps | independent candidate | page title/nav/current-season inconsistencies observed; 50+ not 60+; some D/ST semantics are aggregated; premium/proprietary usage needs rights review |
| FantasyPros | aggregate reference / comparator | consensus FG/FGA/XP/FPTS | consensus sack/INT/FR/FF/TD/safety/PA/yards/FPTS | dated 2026 draft consensus visible | **aggregate, not automatically independent** | component overlap unknown; do not count as second independent vote when components overlap |
| nflverse / nflfastR | realized-outcome + identity backbone | PBP exposes field-goal result, kick distance, extra-point result | PBP/team records support sacks, turnovers, scoring, safety, two-point returns and weekly team outcomes | historical, auditable | outcome source, not Forecast provider | must validate exact Sleeper scoring semantics, especially points allowed and special-teams classifications |

### Public evidence URLs reviewed 2026-09-24

- Sleeper API: https://docs.sleeper.com/
- Sleeper scoring options: https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available
- FFToday K 2026: https://www.fftoday.com/rankings/playerproj.php?PosID=80&Season=2026
- FFToday D/ST 2026: https://www.fftoday.com/rankings/playerproj.php?PosID=99&Season=2026
- FFToday K 2025/2024: same route with `Season=2025` / `Season=2024`
- FFToday D/ST 2025/2024: same route with `Season=2025` / `Season=2024`
- CBS K: https://www.cbssports.com/fantasy/football/stats/K/
- CBS D/ST: https://www.cbssports.com/fantasy/football/stats/DST/
- FantasyPros K: https://www.fantasypros.com/nfl/projections/k.php?week=draft
- FantasyPros D/ST: https://www.fantasypros.com/nfl/projections/dst.php?week=draft
- Razzball K ROS: https://football.razzball.com/projections-pk-restofseason/
- Razzball D/ST ROS: https://football.razzball.com/projections-teamdefense-restofseason/
- Razzball projections FAQ: https://football.razzball.com/fantasy-football-tools-faq/
- nflreadr team stats: https://nflreadr.nflverse.com/reference/load_team_stats.html
- nflfastR kick-result implementation evidence: https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R

---

## 5. Forecast subject contract

### 5.1 Required additive abstraction

Forecast should introduce a subject discriminator rather than redefining all roster assets as players.

Conceptual contract:

```text
ForecastSubject =
    PlayerSubject(player_id)
  | NflTeamUnitSubject(season, nfl_team, unit="DST")
```

Rules:

- QB/RB/WR/TE: `PlayerSubject`
- K: `PlayerSubject` with `Position.K`
- D/ST: `NflTeamUnitSubject`, never a human player
- canonical team alias normalization belongs at State/identity boundary
- provider-specific team strings remain provenance, not canonical identity
- Sleeper roster IDs such as `DEN` map to the canonical D/ST team subject through an explicit crosswalk
- season belongs in D/ST identity because franchise/team-unit evidence is season-specific and prevents accidental cross-season identity leakage

### 5.2 Compatibility strategy

Do not force a risky rewrite of offensive Forecast.

Preferred implementation sequence:

1. Add `ForecastSubject` and K/DST-specific observation types or a v2 discriminated observation union.
2. Keep the current `ForecastObservation(player_id=...)` path authoritative for QB/RB/WR/TE.
3. Add a compatibility accessor that returns a roster-asset key for lineup consumers.
4. Migrate downstream consumers behind that accessor.
5. Only then consider a unified v2 observation model.

This preserves accepted offensive behavior while adding the missing asset family.

---

## 6. K contract

### 6.1 Identity

K is an individual player asset. Existing player identity/crosswalk rules apply.

### 6.2 Raw metric vocabulary

Minimum canonical metrics needed to support Sleeper's documented kicker scoring space:

```text
FG_ATTEMPT
FG_MADE
FG_MISS
FG_MADE_0_19
FG_MADE_20_29
FG_MADE_30_39
FG_MADE_40_49
FG_MADE_50_59
FG_MADE_60_PLUS
FG_MISS_0_19
FG_MISS_20_29
FG_MISS_30_39
FG_MISS_40_49
FG_MISS_50_59
FG_MISS_60_PLUS
FG_MADE_YARDS
FG_MADE_YARDS_OVER_30
XP_ATTEMPT
XP_MADE
XP_MISS
```

Derived totals are allowed only when algebraically exact from finer components.

Examples:

- `FG_MADE = sum(distance-made bins)`
- `FG_MISS = sum(distance-miss bins)`
- `FG_MADE_50_PLUS = FG_MADE_50_59 + FG_MADE_60_PLUS`

A source that exposes only `50+` cannot exactly support a league that gives 50-59 and 60+ different point values.

A source that exposes only total FGM/FGA cannot exactly support any active distance-weighted FG scoring.

### 6.3 Provider eligibility

Eligibility is **league-rule dependent**.

A provider can be healthy and independent but still be ineligible for a specific K scoring coordinate because it lacks the active raw metrics. That is not a provider-health failure; it is a `RULE_COVERAGE_INSUFFICIENT` result.

### 6.4 K scoring

Score raw-event forecasts after ensemble construction. Do not ensemble provider-native fantasy points under provider/default scoring.

Any active non-zero kicker rule without exact raw support causes K fantasy-point promotion to fail closed for that league/horizon.

---

## 7. D/ST team-unit contract

### 7.1 Identity

D/ST is a team unit:

```text
NflTeamUnitSubject(
    season=2026,
    nfl_team="DEN",
    unit="DST",
)
```

Provider references can include Sleeper team identifier, provider display name, and aliases, but the canonical key is normalized team-season-unit identity.

### 7.2 Raw metric vocabulary

Minimum event families required for current Sleeper coverage:

```text
SACK
INTERCEPTION
FUMBLE_RECOVERY
FORCED_FUMBLE
SAFETY
BLOCKED_KICK
DEFENSIVE_TD
DEFENSIVE_TWO_POINT_RETURN
TEAM_ST_TD
TEAM_ST_FORCED_FUMBLE
TEAM_ST_FUMBLE_RECOVERY

# optional / scoring-config dependent
INT_RETURN_YARDS
FUMBLE_RETURN_YARDS
BLOCKED_KICK_RETURN_YARDS
SACK_YARDS
TACKLE
SOLO_TACKLE
ASSISTED_TACKLE
TACKLE_FOR_LOSS
QB_HIT
PASS_DEFENDED
TEAM_ST_SOLO_TACKLE
PUNT_RETURN_YARDS
KICK_RETURN_YARDS
MISSED_FG_RETURN_YARDS
THREE_AND_OUT
FOURTH_DOWN_STOP
FORCED_PUNT
```

Points/yards allowed are **distributional weekly/game-level families**, not a single additive season scalar when the league uses buckets:

```text
PA_BUCKET_PROBABILITIES_BY_GAME
YARDS_ALLOWED_BUCKET_PROBABILITIES_BY_GAME
```

or an equivalent per-game discrete predictive distribution from which exact expected bucket points can be calculated.

### 7.3 Why season totals are insufficient

For mutually exclusive points-allowed bands:

```text
E[league_score(PA_game)] != league_score(E[season_PA] / games)
```

in general.

Therefore an annual projected PA total, or even PA/game mean, is not enough to reproduce expected fantasy points for bucket scoring. The scorer needs per-game bucket probabilities or a governed distribution that can integrate over each game's bands.

This is a material reason D/ST is a separate Forecast family.

### 7.4 Special teams separation

Sleeper documents distinct categories for:

- **Special Teams Defense** — awarded to the team D/ST
- **Special Teams Player** — awarded to an individual player

Therefore:

- `def_st_*` rules belong to the D/ST subject.
- `st_*` rules belong to player subjects.
- Never apply the existing player rare-event priors for `st_*` to a D/ST team-unit.
- Never count both families against the same event unless Sleeper's official scoring semantics explicitly award both to different subjects as configured.

---

## 8. Scoring translation contract

Replace global “supported stat name” logic with explicit subject- and rule-aware coverage.

### 8.1 Coverage result

For every active non-zero scoring rule relevant to a subject family, produce:

```text
RuleEvidenceCoverage:
  rule_stat
  subject_family
  status:
    EXACT
    EXACT_DERIVED
    DISTRIBUTIONAL
    PROVISIONAL_GOVERNED
    UNSUPPORTED
  required_metrics
  eligible_source_ids
  provenance_refs
  explanation
```

League fantasy-point promotion requires:

- no `UNSUPPORTED` active rules;
- every exact/derived raw metric to meet authoritative source count;
- every distributional rule to have a promoted distribution contract;
- provisional rules only where a separately versioned, empirically justified Forecast prior has been authorized.

### 8.2 Rule-level completeness

The scorer must fail closed on **every active linear metric missing for a subject**.

The current domain-only guard is insufficient because it can miss isolated active metrics such as `fum_lost`.

Required invariant:

```text
for each active nonzero rule relevant to subject:
    if rule requires raw metric M
    and M is not present with authoritative coverage
    and rule has no authorized provisional residual:
        do not publish authoritative FANTASY_POINTS
```

### 8.3 Zero rules

Zero-point rules are non-material and may be ignored, but they remain visible in diagnostic coverage output.

### 8.4 Source independence remains metric-specific

Current NEXT behavior requiring at least two independent projection sources should be retained.

A provider counts only for metrics it actually exposes. Do not let a provider's K total-FG projection count as independent evidence for a 60+ FG bin it does not project.

FantasyPros consensus remains an aggregate unless component provenance proves independence from the other selected providers.

### 8.5 Source-health requirements

K/DST adapters need all current health checks plus content-aware checks:

- expected season in content, not just URL
- expected horizon (preseason full-season vs ROS vs weekly)
- expected position/unit
- expected table headers
- non-empty canonical identity coverage
- plausible games horizon without silent “32 games”/multi-season contamination
- source update/effective timestamp extraction
- content hash
- malformed/year-title inconsistency quarantine

Observed live Razzball pages demonstrate why URL and page-title assumptions are insufficient; observed CBS routes demonstrate why path year is not reliable evidence of content year.

---

## 9. Historical outcome + uncertainty/calibration proposal

### 9.1 Realized outcomes

Use nflverse/nflfastR as the primary raw realized-outcome backbone, consistent with existing Forecast research.

K outcomes can be reconstructed from play-by-play using:

- kicker identity
- field-goal result
- kick distance
- extra-point result

Sleeper states that blocked FG/PAT attempts count as kicker misses, so the realized scorer must encode that platform semantic and test it.

D/ST outcomes should be reconstructed at team-game level from play-by-play/team outcomes, including the exact event attribution needed by active Sleeper rules.

Where practical, validate reconstructed fantasy points against Sleeper's own weekly scored outcomes for synthetic/reference leagues. Disagreement is a scoring-semantics defect until reconciled, not noise.

### 9.2 Season forecast-error calibration

Do not reuse QB/RB/WR/TE coefficients.

Promote separate calibrations:

```text
Position.K -> K full-season forecast-error calibration
TeamUnit.DST -> D/ST full-season forecast-error calibration
```

Use the existing governed method as the first benchmark candidate for consistency:

1. recover dated preseason/full-season PIT projection artifacts;
2. require at least two genuinely independent sources per subject/metric coordinate;
3. raw-score them under a declared scoring fixture;
4. equal-weight the eligible independent forecasts unless historical evidence justifies weights;
5. compare with realized scoring;
6. calculate empirical residual scale;
7. validate held-out coverage/calibration;
8. promote versioned parameters only from retained research artifacts.

Production should continue using:

```text
stddev = max(provider_disagreement, empirical_error_floor)
```

rather than adding them, unless research demonstrates independence; this retains the current anti-double-counting principle.

### 9.3 Evidence gap

FFToday supplies recoverable dated 2024 and 2025 preseason K/DST projection pages. That is valuable historical PIT evidence, but one independent provider is not enough to reproduce the current two-plus-source benchmark by itself.

CBS current pages expose useful raw fields, but URL-year drift means historical PIT snapshots need separate recovery proof. FantasyPros is an aggregate and cannot automatically provide the second independent vote.

Therefore **no K/DST uncertainty coefficient is promoted by this research**. Production K/DST simulation remains gated until the historical projection benchmark is actually recovered and retained.

### 9.4 Weekly volatility

Do not use offensive weekly CVs for K/DST.

Build separate weekly realized scoring panels:

- K: kicker-game points under scoring fixtures
- D/ST: team-game points under scoring fixtures

Because D/ST bucket scoring is strongly game/matchup dependent, prefer a schedule-aware weekly predictive distribution over “season mean / 17” plus generic CV.

---

## 10. New-league bootstrap contract

### 10.1 Durable target state

The annual preseason authority remains:

```text
one league-agnostic immutable raw-stat snapshot per NFL season
```

captured before the opener and later rescored under any league's rules.

League scoring must never be part of the snapshot identity.

### 10.2 Valid origins

A seasonal bootstrap package may originate from either:

**A. Native capture**
- captured through the normal pre-opener annual snapshot window;
- satisfies source health and independent-source requirements;
- immutable after promotion.

**B. Evidence-preserving migration**
- source evidence was genuinely persisted before the opener;
- raw observations are available, not only provider-native fantasy points;
- original effective/retrieved timestamps are retained;
- source identities and roles are retained;
- content/raw hashes and lineage are retained;
- migration itself has a later `migrated_at` timestamp and never rewrites `effective_at`;
- no current-page refetch or inferred reconstruction is introduced.

### 10.3 2026 offense migration

Legacy artifact 145 is eligible to be considered for **evidence-preserving migration** of its raw offensive observations because it is genuine retained PIT evidence from FFToday + Razzball and prior repository evidence validates exact raw-array lineage.

It is **not** automatically valid for every newly connected league.

Replay must first run `RuleEvidenceCoverage` against the target league.

For the newly connected league, active `fum_lost=-2` is not represented in the preserved raw observations. Unless another retained pre-opener raw source artifact can authentically supply fumble-loss evidence with the required authority, offense preseason replay for that coordinate must report incomplete coverage rather than silently score fumble losses as zero.

### 10.4 2026 K/DST

No persisted two-independent-source 2026 K/DST preseason raw package was found.

Current pages that still display a preseason update date are **research leads**, not automatically equivalent to an immutable captured PIT artifact.

A retrospective 2026 K/DST bootstrap can be promoted only if recovery work proves:

- content is genuinely the dated preseason projection, not a current mutable page with a stale label;
- two independent sources exist;
- every active target scoring rule is covered at the required raw/distributional granularity;
- provenance and content hashes are retained;
- rights permit storage/use.

If those conditions fail, 2026 K/DST preseason remains unavailable. Do not backfill it from present-day data.

### 10.5 Late-connect behavior by season phase

**Before opener**
- capture or load the annual preseason raw snapshot normally.

**After opener, annual snapshot exists**
- replay annual raw snapshot under new league rules.
- if rule coverage is complete, bootstrap valid.
- if incomplete, surface explicit missing rule families.

**After opener, no annual snapshot but qualifying retained PIT evidence exists**
- perform evidence-preserving migration.
- then replay exactly as above.

**After opener, no qualifying PIT evidence**
- preseason baseline is unavailable by definition.
- use current live/ROS Forecast only where its own source + uncertainty gates pass.
- do not manufacture a preseason baseline.
- surfaces that require preseason-vs-current comparison should show “preseason evidence unavailable,” while current-forward surfaces may operate if independently authoritative.

This keeps “new league connected late” from being confused with “Forecast incapable of current forward outlook.”

---

## 11. Downstream migration / compatibility contract

### Forecast -> Value

- Forecast owns K/DST expected scoring and uncertainty.
- Value may consume promoted K/DST Forecast but must not invent projections.
- Current Intrinsic v1 intentionally excludes K/DST. Additive K/DST Value requires a separate implementation step:
  - replacement level based on league roster/start requirements and eligible asset pool;
  - scarcity/replacement must live in Value;
  - dynasty longevity/market assumptions must not feed back into Forecast.
- If Value has not yet promoted K/DST economics, it should fail closed or mark them unvalued rather than zero-valued.

### Forecast -> Simulation / Team Utility

- lineup optimizer already understands K/DST slots but needs roster-asset/Forecast-subject compatibility.
- D/ST bye handling should use the D/ST team's canonical NFL team directly.
- weekly K/DST distributions must be supplied by Forecast; Team Utility cannot reuse offensive weekly volatility.
- a K/DST league is not simulation-complete if required starting slots lack promoted distributions.

### Forecast -> Decision / Search

- Decision/Search remain downstream.
- legality and roster construction must recognize D/ST as a tradable/rosterable asset if the source league supports it.
- search should not create placeholder values for unsupported K/DST.
- any package using unvalued K/DST must be marked incomplete until Value support exists.

---

## 12. Synthetic league fixtures and test matrix

The fixture suite should be deterministic and provider-network independent.

### Fixture A — no K / no D/ST

Lineup: QB/RB/WR/TE only.

Expected:

- existing offense Forecast path byte/semantic compatible;
- K/DST scoring rules, if present but no corresponding lineup slot and platform semantics make them irrelevant, remain ignored exactly as governed today;
- no regression to current FSFFL.

### Fixture B — K only, exactly supported scoring

Example scoring:

- FG 0-19 = 3
- 20-29 = 3
- 30-39 = 3
- 40-49 = 4
- 50-59 = 5
- 60+ = 6
- FG miss = -1
- XP = 1
- XP miss = -1

Provider fixtures contain full bin/miss/XP detail from two independent synthetic sources.

Expected:

- K ensemble promotes;
- league-scored K fantasy points match hand calculation exactly;
- K uncertainty uses K calibration fixture, never offensive coefficient.

### Fixture C — K only, insufficient 60+ evidence

One or both sources expose only 50+.

Expected:

- rule coverage identifies 50-59/60+ split deficiency;
- K fantasy-point authority fails closed;
- offense remains healthy and independently available;
- no proportional or heuristic split.

### Fixture D — D/ST only, linear event scoring

Scoring: sack, INT, FR, FF, safety, blocked kick, defensive TD.

Two independent synthetic team-unit providers expose every event.

Expected:

- D/ST subject identity is team-season-unit;
- no player identity is fabricated;
- exact score matches hand calculation.

### Fixture E — D/ST points-allowed buckets

Provider supplies per-game PA distribution.

Expected:

- expected bucket points are integrated game by game;
- no score is derived from season PA average;
- hand-computed discrete expectation matches.

### Fixture F — D/ST aggregate PA only

Same league as E, providers expose season PA / PA per game only.

Expected:

- points-allowed rule marked distributionally unsupported;
- D/ST fantasy-point authority fails closed.

### Fixture G — K + D/ST

Both families valid.

Expected:

- lineup can fill both starter slots;
- team scoring distribution includes both;
- offense behavior unchanged;
- no double counting between `def_st_*` and `st_*`.

### Fixture H — team vs player special teams

One return TD is attributed in raw fixture to:
- team D/ST special teams;
- an individual returner.

League enables both team and player special-teams TD rules.

Expected:
- D/ST gets `def_st_td` credit;
- player gets `st_td` credit;
- each subject receives exactly its configured scoring;
- no duplicate credit within either subject.

### Fixture I — active fumble-loss rule with missing raw evidence

League has `fum_lost != 0`; raw offense ensemble has no `FUMBLES_LOST`.

Expected:
- authoritative player fantasy points are withheld for affected subject/coordinate;
- coverage reports the missing metric;
- never interpret missing as zero.

### Fixture J — late-connected league with annual snapshot

Expected:
- same immutable snapshot replays under two materially different league scoring systems;
- raw ensemble hash identical across leagues;
- only league-scored fantasy points differ.

### Fixture K — 2026 migrated legacy offense evidence

Input equivalent to artifact 145.

Expected:
- lineage points to legacy persisted evidence;
- effective timestamp remains original;
- migration timestamp is distinct;
- raw hash preserved;
- target league with unsupported active metric receives incomplete coverage.

### Fixture L — late connect with no reconstructable PIT evidence

Expected:
- preseason state explicitly unavailable;
- current live Forecast may still publish if independently healthy;
- no current data is relabeled as preseason;
- readiness reports the exact missing authority rather than generic loading failure.

---

## 13. Acceptance tests required before implementation can claim K/DST support

### Identity

- D/ST cannot be instantiated as a human player Forecast subject.
- provider alias normalization is deterministic and season-aware.
- Sleeper team roster IDs map to the correct canonical team unit.
- unrostered K/DST asset universe is available where league workflows require waivers/replacement.

### Scoring

- every active non-zero rule has explicit coverage.
- 50+ cannot satisfy distinct 50-59 and 60+ rules.
- PA/Yards buckets cannot be scored from a season average.
- team special-teams and player special-teams semantics are separate.
- active missing `fum_lost` fails closed.
- zero-point rules do not block promotion.
- hand fixtures reproduce exact league points.

### Source governance

- at least two eligible independent projection sources per authoritative promoted metric/subject.
- aggregate source overlap cannot masquerade as independence.
- season/horizon/content checks fail malformed provider pages.
- source coverage and health are diagnostic separately.
- provider evidence records effective time, retrieval time, URL/ref, content hash, schema version.

### Uncertainty

- K and D/ST have distinct promoted empirical calibration.
- no offense coefficient fallback.
- provider disagreement cannot be the sole simulation-grade uncertainty without a promoted residual calibration.
- weekly K/DST volatility is family-specific.
- D/ST schedule/bucket uncertainty is not reduced to mean/17.

### Bootstrap

- annual snapshot is league-agnostic.
- native capture remains immutable.
- migration requires previously persisted PIT evidence.
- migration preserves raw hash and original timestamps.
- no post-opener refetch can become preseason authority.
- replay checks target league rule coverage before publishing.
- missing preseason evidence is an explicit governed state, not an exception swallowed by readiness.

### Downstream

- K/DST league lineup simulation cannot report complete if required slots lack authoritative forecasts.
- Value cannot silently treat unsupported K/DST as zero.
- Decision/Search cannot create economics from Forecast-missing assets.
- no-K/no-DST league remains regression-clean.

---

## 14. Recommended implementation sequence

This sequence minimizes risk to accepted offense behavior.

### Stage 1 — contracts and scoring integrity

1. Add subject discriminator and canonical D/ST team-unit identity.
2. Add K/DST raw metric enums/contracts.
3. Add rule-to-subject scoring semantics.
4. Replace domain-only completeness with active-rule completeness, including the existing `fum_lost` hole.
5. Add deterministic synthetic fixture suite A-L.

**Do not add live providers yet.**

### Stage 2 — outcome reconstruction + calibration research harness

1. Add nflverse K and D/ST realized-outcome reconstruction.
2. Validate against Sleeper weekly scoring fixtures.
3. Recover retained/datable historical K/DST projection sources.
4. Run K and D/ST empirical forecast-error and weekly-volatility benchmark.
5. Promote coefficients only with retained artifact/digest/provenance.

This is the evidence gate for simulation-grade production authority.

### Stage 3 — provider adapters

Add K/DST adapters source by source.

For each:
- parse raw components;
- run source-specific content health;
- record rule coverage;
- preserve provider role/independence;
- add golden fixtures;
- never parse provider-native fantasy points as raw authority.

Prioritize FFToday plus another genuinely independent source whose raw granularity satisfies the target rule coordinate. CBS/Razzball are candidates but require rights and content-health validation.

### Stage 4 — annual snapshot v2 + evidence migration

1. Extend annual preseason snapshot to support subject union and K/DST metrics.
2. Implement evidence-preserving legacy migration path.
3. Migrate 2026 offense artifact 145 only after rule-completeness fix.
4. Keep 2026 K/DST absent unless independent PIT recovery passes.

### Stage 5 — downstream consumption

1. Team Utility roster-subject bridge and K/DST weekly distributions.
2. Value K/DST replacement/scarcity extension.
3. Decision/Search asset handling.
4. Readiness and surfaces consume explicit authority states.

### Stage 6 — new-league acceptance

Run full lifecycle on:
- original no-K/DST league;
- synthetic K-only;
- synthetic D/ST-only;
- synthetic K+DST;
- newly connected production league.

7/7 cannot be declared merely because UI loads. It requires the upstream Forecast authority state demanded by the surface.

---

## 15. Unresolved evidence / management dependencies

These are not reasons to weaken the contract.

1. **Historical independent PIT source #2 for K/DST calibration**
   - FFToday 2024/2025 is recoverable and dated.
   - a second independent historical projection corpus still needs to be recovered and retained before empirical promotion matching current Forecast standards.

2. **Provider rights**
   - Sleeper's documentation explicitly says the public API is free for non-commercial use and commercial use requires licensing discussion.
   - Razzball K/DST projection products are proprietary/premium-facing.
   - CBS/FFToday usage/storage rights need review before commercial promotion.
   - Research capability does not equal production data rights.

3. **Exact Sleeper scoring semantics**
   - create truth fixtures for obscure events and D/ST points-allowed accounting rather than infer semantics from rule names.

4. **2026 K/DST preseason**
   - no qualifying persisted two-source raw package is currently proven.
   - do not fabricate it.

5. **Value model for K/DST**
   - Forecast can define football production without deciding dynasty economics.
   - replacement/scarcity and long-horizon value require Value-owned work after Forecast evidence is promoted.

---

## 16. Explicit prohibitions carried forward

Implementation must not:

- lower the two-independent-source requirement simply because a league has K/DST;
- treat FantasyPros aggregate as independent from its component providers without provenance proof;
- split 50+ field goals into 50-59/60+ heuristically;
- turn season PA average into bucket fantasy points;
- apply offensive uncertainty coefficients to K/DST;
- model D/ST as a human player;
- mix `def_st_*` and `st_*` subject semantics;
- silently ignore an active scoring rule whose raw metric is missing;
- refetch current pages and backdate them as preseason evidence;
- make Value/Team Utility/Decision invent missing Forecast production;
- merge/deploy model-authority changes without management authorization.

---

## 17. Research completion determination

The directive's required outputs are now specified:

- source inventory — complete
- K contract — complete
- D/ST team-unit contract — complete
- scoring translation contract — complete
- uncertainty/calibration proposal — complete, with explicit evidence gate
- new-league bootstrap contract — complete
- synthetic fixtures/test matrix — complete
- Forecast -> Value -> Simulation -> Decision/Search migration map — complete
- unresolved gaps — explicit
- implementation handoff + acceptance tests — complete

The architecture is implementation-ready **without weakening existing Forecast authority**.

Production support for the newly connected K/DST league remains correctly blocked until the implementation completes the contracts and the empirical K/DST uncertainty/source-evidence gates are satisfied.
