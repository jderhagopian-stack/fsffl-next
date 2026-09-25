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


### JerryGM Projections API — strongest exact-rule candidate found

Research check finalized against deployed API documentation at:
`2026-09-25T13:50:45Z`.

Docs:
https://api.jerrygm.com/api/ext/v1/docs

Terms:
https://www.jerrygm.com/terms/

Technical evidence:
- current 2026 `week=current&horizon=ros` is explicitly supported;
- ROS carries schedule-aware `gamesRemaining`, `ros.statLine`, `generatedAt` / current-week semantics and a current-source model;
- K supports custom scoring with separate `fg50to59` and `fg60plus` weights;
- D/ST exposes sacks, INT, FR, FF, TDs, return TDs, safety, blocked kicks and defensive two-point returns;
- D/ST retains a points-allowed spread and exposes `paTierExpectedPPG`, explicitly integrating a configurable PA ladder over the distribution instead of scoring only mean PA;
- arbitrary `paTiers` can reproduce the Hodor PA bands.

Important evidence boundary:
- the documented raw K `statLine` explicitly lists distance buckets only through `50plus`;
- the custom scorer nevertheless accepts a distinct `fg60plus` rule;
- therefore JerryGM cannot be mapped to raw `FG_MADE_60_PLUS` merely from the public schema text.
- A live licensed/API-key response must prove whether a report-only/custom-scoring breakdown can expose the expected 60+ contribution separately enough to satisfy FSFFL's `DISTRIBUTIONAL` rule-evidence contract.
- No live provider payload was acquired in this Research directive because API access requires an enabled account/key.

Independence:
- JerryGM describes this as its own model output derived from nflverse.
- its internal `jgm_baseline` / `jgm_cofactor` / `nflverse_naive` variants are one provider ecosystem and must never count as multiple independent votes.

Rights:
- the self-serve API grants application use; Pro permits commercial display;
- the terms prohibit use of output to train or calibrate a competing projection product and prohibit raw-feed redistribution;
- because FSFFL would ingest JerryGM as one input to a derived multi-source Forecast, written provider clarification / partner terms are required before treating self-serve access as production-authorized ensemble input.

Disposition:
**best technical exact-rule candidate found; live response validation + direct rights clarification required; counts as at most one independent provider.**

### Second exact-capability source search — exhausted at public evidence level

Materially distinct current ROS/API candidates were checked after JerryGM surfaced:
- CBS: no 60+ split; aggregate PA only;
- LineupExperts: no public distance split; aggregate PA/YA only;
- RotoWire: public ROS K schema exposes 50+ rather than 60+; DEF exact distribution fields not public;
- FantasyPros: ROS API exists but product is aggregate/consensus evidence;
- Fantasy Nerds: ROS API exists and commercial API use is possible, but public documentation does not establish the required K 60+ and D/ST PA-distribution coordinates; it is also a consensus/aggregation-oriented product and cannot be assumed independent;
- SportsDataIO: season projection K schema collapses 50+ and current maintained in-season product is game-level rather than the authorized ROS path;
- Razzball: current ROS content failed source health;
- FFToday: wrong current horizon for the exception.

No second public, provenance-clean, current ROS source was found that explicitly proves both:
1. the Hodor 60+ K coordinate; and
2. distributional PA-tier D/ST evidence.

Further resolution now requires provider/API access or direct provider answers, not another undirected public search.

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
Status: **CLEARED FOR TECHNICAL EXISTENCE / PARTIALLY CLEARED FOR AUTHORITY**

Current ROS K/DST products unquestionably exist.

At the actual 2026-09-25 acquisition/research instant:
- CBS has usable ROS content for many subjects but stale Atlanta/Green Bay rows;
- LineupExperts has usable ROS content for many subjects but stale Atlanta/Green Bay rows;
- RotoWire exposes a current ROS product but usable values/access require licensing;
- JerryGM explicitly supports 2026 schedule-aware ROS K/DST and is the first public candidate found whose scoring layer can represent Hodor's 60+ K rule and distributional PA tiers;
- FantasyPros/Fantasy Nerds expose ROS APIs but require aggregate/independence treatment;
- Razzball fails health;
- FFToday is the wrong time horizon;
- SportsDataIO's maintained in-season product is game-level rather than current ROS.

The remaining question is no longer whether current ROS K/DST sources exist. It is whether **at least two independent, rights-cleared sources cover each required active scoring coordinate with healthy current rows**.

The runtime therefore needs **subject-row health**, not only provider-global health.

### D. Two-source independence
Status: **PARTIALLY CLEARED GENERALLY / STILL BLOCKED ON THE HODOR-ONLY COORDINATES**

CBS, LineupExperts, RotoWire and JerryGM are plausible distinct provider systems, subject to rights and source-health validation.

For ordinary shared coordinates such as K makes/attempts/XP and D/ST sacks/INT/FF/FR, a two-source path is technically plausible.

For the Hodor-specific hard coordinates, Research found only one current provider candidate with explicit technical support:
- JerryGM for custom 60+ K scoring;
- JerryGM for distributional D/ST PA-tier expectation.

No second provenance-clean provider was found publicly proving those same exact coordinates.

Before any implementation counts providers:
- use a permitted source-access path;
- preserve provider IDs and underlying source provenance;
- treat JerryGM internal source variants as one provider;
- treat aggregate providers as aggregate unless decomposition proves independence;
- apply the existing per-subject/per-metric/horizon two-source gate.

A provider being healthy elsewhere in the dataset does not satisfy an undercovered Hodor-specific group.

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

JerryGM proves that a current ROS provider can technically price a separate 60+ rule, but the public raw schema does not independently expose a `FG_MADE_60_PLUS` stat and no second independent current ROS provider was found with explicit 60+ evidence.

Therefore Hodor authoritative K fantasy points remain fail-closed until:
1. a live JerryGM/API response proves rule-specific 60+ evidence acceptable under FSFFL's governed evidence statuses (or another source exposes the raw coordinate); and
2. a second independent provider supplies the same required coordinate; and
3. source rights are cleared.

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

JerryGM proves a current ROS source can technically carry a PA spread and calculate expected custom PA-tier scoring, and it also exposes many of Hodor's rare D/ST events. That materially clears the **technical-feasibility** question for one provider.

Hodor authoritative D/ST fantasy points nevertheless remain fail-closed because:
1. no second independent current ROS provider was found with proven distributional PA-tier evidence;
2. per-rule rare-event two-source coverage remains incomplete;
3. JerryGM live payload health and rights are not yet cleared.

### G. K/DST uncertainty
Status: **BOUNDED EMPIRICAL TREATMENT MEASURED; HODOR-TOTAL PROMOTION STILL BLOCKED**

Research has now executed the bounded empirical study instead of leaving it hypothetical.

Durable results:
`artifacts/research/k_dst_late_start_exception_20260925/EMPIRICAL_UNCERTAINTY_CHECK.md`

#### K reduced fingerprint
Fingerprint:
`3 * FGM - (FGA - FGM) + XPM`

2024 PIT providers:
FantasySharks + CBS + ESPN, requiring >=2 per kicker.

Season-error result:
- n = 34 kickers;
- relative RMSE = **0.3841884793**.

Weekly realized-volatility result:
- 42 kicker subjects;
- 542 player-games;
- pooled within-subject CV = **0.5223274618**.

#### D/ST reduced fingerprint
Fingerprint:
`1 * DST_SACK + 2 * DST_INTERCEPTION`

2024 PIT providers:
FantasySharks + CBS + ESPN, requiring >=2 per team.

Season-error result:
- n = 30 team units;
- relative RMSE = **0.2140283312**.

Weekly realized-volatility result:
- 32 team units;
- 544 team-games;
- pooled within-subject CV = **0.6381941339**.

#### Authority implication

This changes the evidence-gate wording:

**It is no longer correct to say K/DST lacks empirical uncertainty evidence.**

Historical evidence is sufficient for bounded empirical uncertainty on explicitly defined common scoring fingerprints.

It is still **not** sufficient to promote these four numbers as Hodor-total uncertainty because the Hodor target contains active coordinates excluded from the fitted fingerprints:
- K distance premiums, especially the 60+ increment, and XP miss treatment;
- D/ST FF/FR, safety, blocks, TD families, 2-point returns, special teams and nonlinear PA buckets.

The production-safe implementation requirement is now:
1. encode `CalibrationScoringFingerprint`;
2. reproduce these retained measurements;
3. add replay/holdout diagnostics;
4. measure additional target-compatible fingerprints if qualifying PIT evidence exists;
5. prove how uncertainty for every excluded Hodor coordinate is governed;
6. promote only if the target total is fully covered.

No Hodor-total coefficient is authorized by Research.

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
| Current ROS source existence | **CLEARED technically** | **CLEARED technically** | N/A | N/A |
| Source health | **PARTIAL** — row quarantine / live API validation required | **PARTIAL** — row quarantine / live API validation required | N/A | N/A |
| >=2 independent sources | **PARTIAL; hard 60+ group still one proven candidate** | **PARTIAL; PA-distribution group still one proven candidate** | historical 2024 multi-source panel exists | license-specific |
| Hodor rule completeness | **BLOCKED: second-source 60+ evidence** | **BLOCKED: second-source PA distribution + rare events** | preseason comparison unavailable | same technical rules |
| K/DST empirical uncertainty | **REDUCED FINGERPRINT MEASURED; HODOR TOTAL BLOCKED** | **REDUCED FINGERPRINT MEASURED; HODOR TOTAL BLOCKED** | 2024 empirical results persisted | target compatibility still required |
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
3. K: a second independent 60+ evidence source plus live validation of the first exact-rule candidate;
4. D/ST: a second independent game/distributional PA-tier source plus remaining rare-event two-source coverage;
5. promotion of K-specific and D/ST-specific uncertainty only after full target-scoring compatibility is proven.

The historical uncertainty blocker is now **compatibility**, not absence of empirical measurements.

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
8. Reproduce the now-persisted historical K/DST empirical results under explicit scoring fingerprints and add replay/holdout diagnostics.
9. Use a licensed JerryGM key (or equivalent exact-capability source) to validate live 2026 rule-level evidence for 60+ K and D/ST PA tiers; do not count JerryGM's internal model variants as independent.
10. Obtain/validate a second independent exact-capability source for those hard coordinates, or keep them fail-closed.
11. Promote uncertainty only if the target scoring fingerprint is fully compatible and validation passes.
12. Only then re-run Hodor current-forward Forecast/readiness acceptance.
13. Keep preseason comparison unavailable for 2026.
14. Verify 2027 cannot enter the exception path.

## Operating-protocol conclusion

The Management question was whether the late-start exception changes which evidence gates block current-forward 2026 K/DST authority.

It does.

The missing-preseason gate has been removed from current-forward authority. The remaining current-forward blockers are now precisely rule completeness, independent source coverage, source rights/health, and target-compatible K/DST uncertainty.

Materially distinct public-source searching has now also identified JerryGM as a technically exact-capability candidate and Fantasy Nerds as another ROS/API path, while failing to recover a second public provider that proves the Hodor-specific 60+ K and distributional PA coordinates.

The bounded empirical uncertainty study has now been executed and persisted; its remaining blocker is target-fingerprint compatibility, not lack of a measurement.

The next unresolved source actions require provider/API credentials, rights clarification, or a newly supplied second exact-capability source rather than another undirected public search.

**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**
