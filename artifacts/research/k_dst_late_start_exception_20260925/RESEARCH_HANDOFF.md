# FSFFL NEXT — 2026 Late-Start K/DST Forecast Exception

Date: 2026-09-25  
Workstream: Forecast Research  
State: **DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**

## Management authorization

Management authorizes a one-season-only 2026 exception allowing a K/DST Forecast baseline to be acquired **now**, after Week 1, from qualifying independent current season-long/rest-of-season projection sources.

This exception changes the permissible **time origin** for the 2026 K/DST baseline. It does not weaken Forecast authority.

Binding rules:

- preserve the true acquisition timestamp;
- preserve source identity, source URL/API identity, provider-reported effective timestamp when available, raw/content identity permitted by source rights, projection horizon, and source-health evidence;
- use `ForecastHorizon.REST_OF_SEASON` for a provider's ROS evidence;
- never call the artifact preseason;
- never backdate it;
- never use it for a 2026 pre-Week-1 comparison;
- 2026 preseason comparison remains unavailable where authentic pre-Week-1 evidence is unavailable;
- the exception is **2026 only**;
- beginning with 2027, the normal governed annual preseason snapshot process is mandatory and this late-start path must fail closed;
- existing two-independent-source, anti-double-counting, rule-completeness, source-health and uncertainty governance remain in force.

Source-acquisition evidence:
`artifacts/research/k_dst_late_start_exception_20260925/SOURCE_ACQUISITION_LEDGER.json`

Prior empirical/source closeout:
`artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`

## Executive result

The Management exception materially changes the gate decomposition:

1. **Missing 2026 preseason K/DST evidence is no longer a blocker for current-forward 2026 Forecast.**
2. It remains a blocker only for any product claim comparing current 2026 K/DST Forecast to a pre-Week-1 baseline.
3. A truthful 2026 current-date ROS acquisition path is implementable with the existing `REST_OF_SEASON` Forecast horizon and the K/DST subject contracts merged in PR #215.
4. Current public research proves multiple candidate ROS providers exist, but **Hodor's current K/DST fantasy-point authority is still blocked** by rule-coordinate completeness, K/DST-specific uncertainty, and deployable source rights.
5. Existing historical evidence is sufficient to build and test a **bounded, non-promoting K/DST empirical uncertainty candidate**, but it is not sufficient to declare or borrow a production Hodor-total uncertainty coefficient today.
6. No unsupported coefficient is authorized by this handoff.

## Current-date source findings

### CBS Sports — candidate current ROS source

Acquired:
`2026-09-25T12:28:54.671206Z`

K:
https://www.cbssports.com/fantasy/football/stats/K/2026/restofseason/projections/ppr/

D/ST:
https://www.cbssports.com/fantasy/football/stats/DST/2026/restofseason/projections/ppr/

Evidence:
- content explicitly says 2026 Rest of Season projections;
- K exposes FGM/FGA, distance bands through 50+, XPM/XPA;
- D/ST exposes INT, safety, sacks, defensive FR/FF/TD, aggregate PA and yards allowed.

Health caveat discovered against the actual acquisition instant:
- Atlanta beat Green Bay on Thursday, 2026-09-24;
- on Friday morning CBS still showed 15-game ROS quantities for Atlanta/Green Bay K/DST rows;
- those subject rows are stale and must be quarantined;
- this does **not** automatically require quarantining unrelated teams that still truthfully have 15 regular-season games remaining.

Rule coverage:
- K has 50+ but not a separate 60+ count;
- D/ST aggregate PA/PA-per-game is not a game-level PA bucket distribution;
- blocked kicks, defensive 2-point returns and team special-teams FF/FR/TD are not established by the exposed ROS table.

Disposition:
**candidate provider; source-health must be subject-aware; not Hodor-rule-complete.**

### LineupExperts — technically promising independent ROS source

Acquired:
`2026-09-25T12:32:36.550668Z`

K:
https://www.lineupexperts.com/football/projections?flt_pos=K&flt_proj_time_period=RestOfSeason

D/ST:
https://www.lineupexperts.com/football/projections?flt_pos=DST&flt_proj_time_period=RestOfSeason

Provider documentation:
- identifies the projections as internally modeled LineupExperts projections;
- offers an API in-season projection product with a rest-of-season interval;
- API pricing offers standard and premium in-season projection subscriptions.

Public K fields:
- XP made/attempted;
- FG made/attempted;
- no visible distance split.

Public D/ST fields:
- sacks;
- INT;
- FF;
- FR;
- aggregate points allowed;
- aggregate yards allowed.

Health caveat:
- Atlanta/Green Bay D/ST rows also still showed 15 projected games after the Thursday game, so those rows are stale at the Friday acquisition instant and require quarantine.

Rights:
- LineupExperts website terms prohibit website data mining/extraction;
- API usage is a distinct subscribed product, requires declared usage forums, and does not automatically grant rights beyond the API terms;
- production implementation must use a permitted API/contract path, not scrape the public page.

Independence:
- LineupExperts documents its projections as its own internally modeled system, which is positive evidence of provider-level independence from CBS;
- because the API terms can also expose some third-party content, the specific projection endpoint must be contract-tested/documented as the internal LineupExperts projection product before it receives an independent vote.

Disposition:
**strong candidate second provider after API access/rights/schema validation; not currently Hodor-rule-complete from publicly visible fields.**

### RotoWire — healthy ROS product, inaccessible/rights-gated values

Acquired:
`2026-09-25T12:29:08.299806Z`

URL:
https://www.rotowire.com/football/projections-ros.php

Evidence:
- explicitly identifies 2026 rest-of-season projections;
- states totals apply to the remainder of the season;
- K scoring inputs expose XPM, FGM29, FGM39, FGM49, FGM50;
- current player pages expose a K ROS schema including FGM/FGA/50+/XP.

Limitations:
- raw ROS values are paywalled;
- no separate 60+ K count is visible;
- the complete current DEF raw schema and row-level remaining-game health cannot be verified without licensed access;
- RotoWire rights remain restrictive and require written authorization/license for FSFFL's automated/storage use.

Disposition:
**possible licensed independent source; not authority until access, rights and current schema pass.**

### Razzball — quarantine

Acquired:
`2026-09-25T12:29:02.640334Z`

The current ROS K/Team Defense pages failed semantic health:
- K content identified itself as 2025;
- rows carried impossible roughly 30–32 games remaining.

Disposition:
**quarantined. Reachability is not source health.**

### FFToday — not eligible for this exception

The currently recoverable 2026 K/DST season projections are preseason/full-season material updated before Week 1.

Disposition:
**not a current-date ROS baseline. Do not relabel or subtract actuals heuristically.**

### SportsDataIO — useful future weekly source, not this ROS exception as documented

Provider documentation states:
- season-long NFL projections are preseason-only;
- after Week 1, those projections are not maintained for current regular-season performance;
- in-season game projections are available separately.

Its K schema also exposes 50+ rather than 50–59 / 60+.

Disposition:
**not eligible for the current Management-authorized season-long/ROS late-start path without a separate Management decision to allow aggregation of remaining game forecasts.**

### FantasyPros — aggregate/reference, not automatically independent

FantasyPros API materials advertise rest-of-season projection access and a commercial licensing path, but FantasyPros projections are an aggregate product.

Disposition:
**may be useful under license, but cannot become an independent second vote unless source decomposition proves it does not re-vote present component providers.**

## Exact current-forward gate analysis

### A. 2026 time-origin / no-preseason gate
Status: **CLEARED FOR CURRENT-FORWARD 2026**

Management has explicitly authorized a current-date 2026 late-start baseline.

Implementation must persist:
- `season=2026`;
- `baseline_class=late_start_current_ros_exception`;
- exact `captured_at`;
- provider identity;
- provider URL/API endpoint;
- provider-reported effective timestamp when available;
- `ForecastHorizon.REST_OF_SEASON`;
- period/evaluation boundary;
- content hash or other immutable identity where rights allow retention;
- source-health disposition/evidence.

This artifact is never eligible to answer "what did we expect before Week 1?"

### B. 2026 preseason comparison
Status: **UNAVAILABLE BY DESIGN; NOT A CURRENT-FORWARD BLOCKER**

No current-date ROS source can be transformed into pre-Week-1 truth.

Presentation/analytics must explicitly expose:
`preseason_comparison_status = unavailable_no_qualifying_pre_week1_k_dst_evidence`.

Do not substitute the late-start baseline into a field labeled preseason.

### C. Current source existence
Status: **PARTIALLY CLEARED**

Current ROS products exist from multiple providers.

At the actual 2026-09-25 acquisition instant:
- CBS has usable ROS content for many subjects but stale Atlanta/Green Bay rows;
- LineupExperts has usable ROS content for many subjects but stale Atlanta/Green Bay rows;
- RotoWire exposes a current ROS product but usable values/access require licensing;
- Razzball fails health;
- FFToday is the wrong time horizon;
- SportsDataIO's maintained in-season product is game-level rather than current ROS.

The runtime therefore needs **subject-row health**, not only provider-global health.

### D. Two-source independence
Status: **PARTIALLY CLEARED TECHNICALLY / BLOCKED FOR DEPLOYED AUTHORITY**

CBS + LineupExperts are plausible independent projection systems.

Before an implementation may count them as two voters:
- use a permitted source-access path;
- preserve independent provider IDs;
- verify the LineupExperts in-season endpoint is its internal projection model for the relevant rows;
- map source component provenance;
- apply the existing per-subject/per-metric two-source gate.

A provider being healthy somewhere in the dataset does not satisfy a group with only one source.

### E. K mean/scoring completeness for Hodor
Status: **STILL BLOCKED**

Hodor K scoring:
- 0–19 = 3;
- 20–29 = 3;
- 30–39 = 3;
- 40–49 = 4;
- 50–59 = 5;
- 60+ = 6;
- generic miss = -1;
- XP make = 1;
- XP miss = -1.

Exact derivations that are allowed:
- because 0–19 and 20–29 have the same coefficient, a provider-native 0–29 made count is algebraically sufficient for those two Hodor bands;
- generic FG misses may be exactly derived as `FGA - FGM` when both provider coordinates represent the same horizon and are complete;
- XP misses may be exactly derived as `XPA - XPM`.

Not allowed:
- 50+ cannot be split into 50–59 and 60+ without direct evidence;
- a 50+ projection can support the base five points per 50+ make, but the extra one point for each 60+ make remains a missing active scoring coordinate;
- do not use actual-to-date 60+ frequency, league average, kicker career rate, or a heuristic allocation unless separately authorized as a governed empirical residual.

Current public healthy candidate feeds do not prove two independent `FG_MADE_60_PLUS` projections.

Therefore Hodor authoritative K fantasy points remain fail-closed.

### F. D/ST mean/scoring completeness for Hodor
Status: **STILL BLOCKED**

Hodor active D/ST coordinates include:
- sack;
- INT;
- forced fumble;
- fumble recovery;
- blocked kick;
- defensive TD;
- defensive two-point return;
- team-special-teams TD;
- team-special-teams FF;
- team-special-teams FR;
- safety;
- mutually exclusive PA buckets.

Current healthy ROS candidates establish overlapping support for:
- sack;
- INT;
- defensive FF/FR;
- some defensive TD/safety evidence.

They do not establish two-source rule-complete support for all active coordinates.

Most importantly:
- aggregate ROS points allowed is not a distribution of remaining game PA outcomes;
- `score(E[PA])` is not `E[score(PA)]` for bucket scoring;
- aggregate PA/PA-per-game cannot satisfy the Hodor PA bucket coordinate.

Therefore Hodor authoritative D/ST fantasy points remain fail-closed.

### G. K/DST uncertainty
Status: **BOUNDED RESEARCH TREATMENT AUTHORIZED BY EVIDENCE; PRODUCTION COEFFICIENT NOT YET CLEARED**

Existing historical evidence is materially sufficient to **run** a bounded empirical study:
- genuine pre-opener 2024 multi-provider raw K/DST corpora exist;
- source-separated weekly K/DST projection panels exist across multiple historical seasons;
- realized NFL K/DST outcomes are reconstructable for a substantial common coordinate;
- PR #215 already merged non-promoting season-error and weekly-volatility harnesses.

But existing evidence does **not** justify declaring a Hodor-total K or D/ST uncertainty coefficient without performing and validating the fit.

The reason is scoring-coordinate mismatch:
- K historical providers generally collapse 50+ and do not support Hodor's 60+ incremental point;
- D/ST historical raw coverage is incomplete for the full Hodor rule set, especially PA-bucket distribution and rare special-teams coordinates;
- a coefficient fit on a reduced standard scoring subscore cannot silently be applied to a larger Hodor score.

Required implementation:
1. introduce a deterministic `CalibrationScoringFingerprint` identifying exactly which raw metrics/rule transformations the empirical sample represents;
2. reconstruct realized scores under that exact fingerprint;
3. construct equal-weight historical projection samples only where >=2 independent PIT providers cover the fingerprint;
4. run `fit_k_dst_season_error` and `fit_k_dst_weekly_volatility`;
5. persist sample size, seasons, source IDs, source hashes/provenance, residual diagnostics and held-out/replay checks;
6. compare calibration fingerprint to target league scoring coverage;
7. promote an empirical uncertainty floor only when the target coordinate is proven compatible;
8. otherwise persist the fit as research evidence only and keep target Forecast uncertainty unavailable.

No coefficient value is authorized by this Research handoff.

### H. Provider rights for deployed 2026 beta
Status: **STILL BLOCKED UNTIL SOURCE-SPECIFIC RIGHTS ARE SATISFIED**

Management's model exception does not override third-party terms.

Examples:
- CBS public content does not establish FSFFL automated production ingestion/storage rights;
- LineupExperts website extraction is prohibited, while a paid API product exists and requires declared usage;
- RotoWire requires authorization/license;
- FantasyPros offers commercial/API licensing paths.

Research/manual inspection is distinct from deployed ingestion.

### I. Eventual commercial production
Status: **STILL BLOCKED, BUT SEPARATE FROM THE 2026 TIME-ORIGIN EXCEPTION**

Commercial production requires executed/explicit rights for the actual provider set and the actual storage/derived-output architecture.

A source can be technically sufficient for beta research and still remain commercially unusable.

### J. 2027+
Status: **NO EXCEPTION**

For season >= 2027:
- the late-start exception constructor must reject;
- preseason snapshot scheduling/capture is the only governed baseline path;
- a failure to capture preseason evidence must remain explicit rather than automatically invoking the 2026 exception.

## Implementation architecture

### 1. New exception artifact class

Add a Forecast-owned artifact separate from annual preseason state, e.g.:

`late_start_current_projection_snapshot_v1`

Required metadata:
- `season`;
- `exception_version = "2026-late-start-v1"`;
- `baseline_class = "late_start_current_ros_exception"`;
- `captured_at`;
- `evaluation_as_of`;
- `horizon = "rest_of_season"`;
- `period_start`;
- `period_end`;
- source list;
- source-specific captured timestamp;
- provider-reported effective timestamp nullable;
- provider/source version;
- URL/API endpoint;
- usage/rights classification;
- payload/content hash where permitted;
- source-health events;
- subject-row quarantine list/reasons;
- metric coverage map;
- independent-source coverage map;
- explicit `preseason_eligible=false`.

The artifact must never satisfy the annual-preseason snapshot interface by coercion.

### 2. One-season hard boundary

The constructor/service must require:
`season == 2026`.

Tests must prove:
- 2026 accepted when all other gates pass;
- 2027 rejected;
- 2025 rejected;
- no generic "late start if missing" fallback exists.

### 3. ROS acquisition path

Do not reuse a provider adapter that calls a season URL and assumes `ForecastHorizon.SEASON`.

Create horizon-explicit acquisition, e.g.:
- `CBSRosKDstProjectionSource`;
- a second rights-cleared API adapter such as `LineupExpertsRosKDstProjectionSource` if licensed/schema-validated;
- optional RotoWire ROS adapter only if licensed.

Each source adapter must declare:
- provider;
- endpoint;
- horizon;
- captured_at;
- provider_effective_at if present;
- source version;
- usage class;
- content identity;
- row-level raw stats.

### 4. Schedule-aware source health

At acquisition, load canonical NFL schedule/state as of `captured_at`.

For every subject:
- calculate actual remaining regular-season games at that instant;
- compare provider projected-GP semantics when exposed;
- if a team already played in the current week but provider still includes that game, quarantine that row;
- do not backdate acquisition to make it pass;
- do not subtract provider-predicted/actual completed-game values heuristically.

Provider-level health still applies for:
- wrong year;
- wrong horizon;
- impossible population/cardinality;
- malformed table;
- content hashes/revision drift;
- broad numerical-scale anomalies.

### 5. K normalization

Extend K stat mapping into canonical `ForecastMetric`:
- FG attempts/makes;
- exact distance bins where supplied;
- 50+ only as `FG_MADE_50_PLUS`;
- XP attempts/makes;
- exact misses where supplied or algebraically derivable.

Use `ForecastObservation` with `Position.K` and `ForecastHorizon.REST_OF_SEASON`.

Coverage logic must understand exact coefficient-equivalence transforms:
- Hodor 0–19 + 20–29 can be satisfied by an exact 0–29 count because both score 3;
- 50+ cannot satisfy distinct 50–59/60+.

### 6. D/ST normalization

D/ST provider rows must become `TeamUnitForecastObservation` with `NflTeamUnitForecastSubject`.

Never create ordinary player observations for D/ST.

Map only provider-supported metrics.

PA bucket authority requires a provider-native or separately governed **remaining-game distributional** coordinate. Season aggregate PA is diagnostic only.

### 7. Ensemble / independence

Retain `minimum_independent_sources=2` per subject/metric/horizon group.

Retain aggregate-source de-duplication.

A source may pass provider health and still be ineligible for a particular K/DST metric.

### 8. Uncertainty

Do not publish zero-variance K/DST Forecast as authoritative.

Implement calibration as a separate research-to-authority stage:
- fit K and D/ST separately;
- source historical PIT projections from >=2 independent providers;
- use matching scoring fingerprints;
- combine empirical floor with provider disagreement only after the floor is promoted;
- no QB/RB/WR/TE fallback coefficient.

### 9. Persistence / presentation contract

A 2026 late-start baseline may support:
- current-forward ROS values;
- later deltas versus the **late-start baseline**, if Product explicitly labels them that way.

It may not support:
- preseason expectation;
- preseason vs current delta;
- a chart point labeled preseason;
- any timestamp earlier than actual capture.

Suggested product label:
**2026 late-start baseline — acquired Sep. 25, 2026**

Do not use "preseason" in its presentation metadata.

## Acceptance fixtures

Implementation must include at least:

1. **2026 exception accepted** — valid ROS sources, real timestamp, no preseason label.
2. **2027 exception rejected** — normal preseason path required.
3. **No backdating** — artifact capture/effective provenance cannot precede actual source acquisition evidence.
4. **Thursday freshness** — at Friday acquisition, ATL/GB provider row with 15 remaining games is quarantined; a Sunday-team row with 15 remains eligible.
5. **Wrong-year Razzball** — 2025 title/impossible game count quarantines source.
6. **FFToday preseason horizon** — stale preseason/full-season page cannot become current ROS.
7. **K exact aggregation** — Hodor 0–19 + 20–29 may use provider 0–29 because coefficients are identical.
8. **K 60+ fail closed** — provider 50+ cannot satisfy Hodor 50–59/60+.
9. **K generic miss exact derivation** — FGA-FGM accepted only when same subject/horizon evidence is complete.
10. **D/ST subject identity** — D/ST cannot become ordinary player Forecast.
11. **D/ST aggregate PA rejection** — season PA/PA-per-game cannot satisfy bucket scoring.
12. **Rare D/ST coordinate coverage** — one-source blocked-kick/ST/2pt evidence cannot acquire two-source authority.
13. **Per-group two-source rule** — provider count somewhere else does not rescue an undercovered metric.
14. **Aggregate anti-double-counting** — FantasyPros consensus cannot re-vote named components.
15. **Uncertainty fingerprint mismatch** — reduced historical fixture cannot be promoted as Hodor-total uncertainty.
16. **No zero uncertainty fallback** — missing K/DST empirical floor stays unavailable.
17. **2026 preseason comparison unavailable** — late-start artifact never satisfies pre-Week-1 analytics.
18. **Original FSFFL regression** — no-K/DST league remains unchanged.

## Gate table after Management exception

| Gate | Current-forward 2026 K | Current-forward 2026 D/ST | 2026 preseason/history | Commercial |
|---|---|---|---|---|
| Late-start time origin | **CLEARED** | **CLEARED** | Not preseason | N/A |
| Current ROS source existence | **PARTIAL** | **PARTIAL** | N/A | N/A |
| Source health | **PARTIAL** — row quarantine required | **PARTIAL** — row quarantine required | N/A | N/A |
| >=2 independent sources | **CANDIDATE, not deployed-cleared** | **CANDIDATE, not deployed-cleared** | historical 2024 panel exists | license-specific |
| Hodor rule completeness | **BLOCKED: 60+** | **BLOCKED: PA distribution + rare events** | preseason comparison unavailable | same technical rules |
| K/DST empirical uncertainty | **BLOCKED FOR PROMOTION** | **BLOCKED FOR PROMOTION** | enough evidence to run bounded study | validation still required |
| Rights for deployed beta | **BLOCKED until provider rights** | **BLOCKED until provider rights** | historical research evidence retained | separate licenses |
| 2026 preseason comparison | Not required | Not required | **UNAVAILABLE BY DESIGN** | N/A |
| 2027 preseason snapshot | N/A | N/A | normal process required | N/A |

## Final authority disposition

### What the Management exception clears
- the requirement that a 2026 current-forward K/DST baseline itself must have been captured before Week 1;
- the ability to persist a truthful current-date ROS baseline artifact for 2026;
- the ability to compare future 2026 states against that late-start baseline if clearly labeled.

### What still blocks current-forward 2026 Hodor authority
1. rights-cleared deployable source access;
2. two independent sources for every required active scoring coordinate;
3. K: exact evidence for the 60+ incremental scoring coordinate;
4. D/ST: game/distributional PA bucket evidence and remaining rare event coordinates;
5. K-specific and D/ST-specific promoted uncertainty compatible with the target scoring fingerprint.

### What no longer blocks current-forward authority
- absence of a 2026 preseason K/DST snapshot;
- inability to compute a true preseason-vs-current K/DST delta.

### What remains historical/preseason-only
- 2026 preseason comparison;
- any claim about Week-1 expectations for K/DST where authentic pre-Week-1 evidence is unavailable.

### What remains commercial-only / external
- executed commercial/storage/derived-output rights for the eventual provider set;
- sublicensing clarity for underlying third-party content.

## Recommended next implementation sequence

1. Implement the exception artifact contract + hard 2026 boundary.
2. Implement schedule-aware row-level ROS source health.
3. Implement CBS ROS K/DST adapter for evidence-independent contract testing, but do not promote provider authority without rights.
4. Implement a second adapter only against a rights-cleared API/source contract; LineupExperts is a promising candidate to evaluate first because it offers explicit in-season ROS API intervals and documents an internal projection model.
5. Add K/DST ROS normalization and active-rule coverage maps.
6. Add the exact coefficient-equivalence transform for equal-scored K distance bands.
7. Add D/ST team-unit ROS normalization and reject aggregate PA for bucket authority.
8. Run the historical K and D/ST empirical calibration study under explicit scoring fingerprints; persist results without promotion.
9. Promote uncertainty only if the target scoring fingerprint is compatible and validation passes.
10. Only then re-run Hodor current-forward Forecast/readiness acceptance.
11. Keep preseason comparison unavailable for 2026.
12. Verify 2027 cannot enter the exception path.

## Operating-protocol conclusion

The Management question was whether the late-start exception changes which evidence gates block current-forward 2026 K/DST authority.

It does.

The missing-preseason gate has been removed from current-forward authority. The remaining current-forward blockers are now precisely rule completeness, independent source coverage, source rights/health, and target-compatible K/DST uncertainty.

Further generic public-source searching is not the next highest-value action. The remaining source questions require rights-cleared API/schema access (particularly for a second source), while the uncertainty question requires bounded implementation/execution of the already-designed empirical harness rather than guessing a coefficient.

**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**
