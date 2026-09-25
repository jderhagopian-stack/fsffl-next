# FSFFL NEXT — K/DST Empirical Evidence & Source-Gate Research Closeout

Date: 2026-09-25  
Workstream: Forecast Research  
Terminal state: **DIRECTIVE COMPLETE — RESEARCH**

## Scope

This closeout resolves the 2026-09-25 Research directive to investigate and decompose the empirical/source gates remaining after Forecast K/DST contract implementation PR #215.

The prior K/DST architecture is not reopened. No production Forecast/model implementation, authority promotion, persistence mutation, merge, or deployment was performed by this Research directive.

Detailed evidence ledger:
`artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_LEDGER.md`

Controlling prior implementation checkpoint:
`artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`

## Executive determination

The original evidence gate was materially over-compressed.

Research recovered:
- a genuine pre-opener **2024 multi-provider raw K/DST projection corpus**;
- authentic **2026 K preseason snapshots from FFToday and CBS**;
- authentic **2026 D/ST component evidence from RotoWire via Sleeper**;
- a pre-opener **FantasyPros D/ST aggregate projection export**;
- 2023-2025 source-separated weekly K/DST panels;
- official Sleeper documentation resolving most previously ambiguous K/DST scoring-category ownership.

Those findings substantially improve the evidence position, but **production K/DST Forecast authority remains fail-closed** because source rights, rule-complete independent provider coverage, and promoted uncertainty are still missing.

## Critical timeline correction

Official NFL scheduling establishes the 2026 regular season began **Wednesday, September 9, 2026 at 8:20 p.m. ET** (2026-09-10T00:20:00Z):

https://www.nfl.com/news/seahawks-to-kick-off-2026-nfl-regular-season-on-wednesday-sept-9-in-seattle

Therefore:

- artifact 145, computed `2026-09-10T21:36:41.346326Z` with raw provenance effective `2026-09-10T13:32:43Z`, is **post-opener** and must not be described as preseason PIT evidence;
- the last recovered authentic FSFFL pre-kickoff offense evidence is artifact **63**, computed `2026-09-09T23:26:16.657633Z`, with FFToday + Razzball ensemble evidence as-of `2026-09-09T23:23:53.152680Z`;
- artifact 63 contains QB/RB/WR/TE only and no K/DST or `fumbles_lost`.

This correction is authority-relevant and must be reconciled into canonical Management state before any annual-preseason migration work.

## Gate-by-gate disposition

### 1. Historical independent PIT K/DST projection evidence
**Status: PARTIALLY CLEARED**

Evidence:
- public repository `ashishkab0b/fantasy_football_2024`;
- pre-opener commit `d02f24161e7c08b4e99faacc2481b688b8487704`;
- source-specific K and D/ST raw CSVs from FantasySharks, ESPN and CBS;
- retained provider identities, URLs, raw components and Git blob identity.

Authority implication:
- the earlier claim that no qualifying historical independent source #2 exists is no longer correct;
- a two-plus-source 2024 empirical exercise is now provenance-supported;
- this is not enough to promote full K/DST uncertainty because rule coverage differs, PA/YA bucket distributions are absent, rights are unresolved, and a reduced common-coordinate fixture is not equivalent to full fantasy-point uncertainty.

Resolution path:
- acquire rights-cleared historical provider data with rule-representative raw coordinates and, preferably, additional full-season PIT vintages;
- then fit/validate through the merged non-promoting calibration harness before any authority promotion.

### 2. 2026 K preseason evidence
**Status: CLEARED for existence/provenance; STILL BLOCKED for Hodor authority**

Evidence:
- FFToday 2026-09-07 full-season K snapshot, fetched before kickoff, with retained normalized/raw hashes;
- CBS 2026-09-07 full-season K snapshot, fetched before kickoff, with retained normalized/raw hashes.

Authority implication:
- qualifying two-provider 2026 K PIT evidence exists externally;
- Hodor separately scores 50-59 and 60+ field goals, while CBS collapses 50+ and FFToday is still more aggregate;
- accepted no-heuristic-split governance therefore prevents exact Hodor preseason K scoring from these two sources.

Resolution path:
- obtain a rights-cleared provider that explicitly projects separate 50-59 and 60+ coordinates, or a provider-native exact equivalent;
- do not split 50+ heuristically.

### 3. 2026 D/ST preseason evidence
**Status: PARTIALLY CLEARED**

Evidence:
- pre-opener RotoWire component projections retained through Sleeper;
- pre-opener FantasyPros D/ST aggregate export with event/PA/YA coordinates;
- independent research code confirms Sleeper projection payload carries `company: "rotowire"`.

Authority implication:
- a component-level 2026 D/ST provider exists;
- FantasyPros aggregate cannot automatically count as an independent second vote because FantasyPros itself states NFL projections are aggregated from multiple sources;
- the retained Sleeper season-level PA fields are not a game-level PA distribution and cannot satisfy bucket scoring.

Resolution path:
- recover/license a second independent component-level D/ST provider, or obtain licensed aggregate source decomposition proving independence;
- obtain game-level/distributional PA/YA evidence for bucket scoring.

### 4. Sleeper scoring truth
**Status: PARTIALLY CLEARED, with the prior semantic ambiguity materially narrowed**

Official Sleeper documentation establishes:
- blocked FG/PAT counts as a kicker miss;
- 0-19, 20-29, 30-39, 40-49, 50-59 and 60+ K categories exist;
- Team Defense has a 2-point conversion return category;
- Special Teams Defense has team ST TD / forced-fumble / fumble-recovery categories;
- Special Teams Player is distinct;
- PA/YA ranges are mutually exclusive buckets;
- documented PA and YA accounting;
- scoring categories stack when the underlying play truthfully earns multiple official stats.

References:
- https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available
- https://support.sleeper.com/en/articles/4126495-how-are-points-allowed-calculated
- https://support.sleeper.com/en/articles/4126427-how-are-yards-allowed-calculated

What remains:
- exact official-stat/gamebook fixtures for rare combined events;
- later Implementation work to extend outcome reconstruction/test fixtures for newly resolved categories.

This is no longer a reason to guess category ownership.

### 5. Production-source feasibility / rights
**Status: STILL BLOCKED — external dependency**

Key dispositions:
- **FantasyPros:** explicit commercial licensing path exists; commercial agreement can potentially provide production and historical/bulk access.
- **Sleeper:** public API is non-commercial; commercial licensing is required.
- **RotoWire:** current terms prohibit automated extraction/archiving/AI-oriented reuse absent authorization; written rights are required.
- **CBS / Razzball:** production/commercial use remains permission/license-gated.
- **ESPN:** undocumented endpoint does not establish production rights.
- **FFToday / FantasySharks:** public availability does not establish commercial ingestion/storage/redistribution rights; direct permission/license is required.

Primary references:
- https://www.fantasypros.com/api-data/
- https://support.fantasypros.com/hc/en-us/articles/49749297704475-How-do-I-request-access-to-the-FantasyPros-API
- https://www.rotowire.com/termsandconditions.php
- https://docs.sleeper.com/
- https://www.fftoday.com/rankings/

External Management action:
- contact/licence candidate providers;
- require written scope covering ingestion, storage, historical use, derived outputs, private beta, commercial production and any sublicensed underlying content;
- if FantasyPros aggregate data is used for independence, require source identity/decomposition sufficient to prove no double counting.

Durable resolution evidence:
- executed license/permission or provider-issued written grant retained in governed project evidence.

### 6. Current-forward K/DST Forecast
**Status: STILL BLOCKED**

Preseason evidence is not required for current-forward Forecast, but current-forward authority still requires:
- >=2 independent current sources per required metric coordinate;
- source/rule completeness;
- rights clearance;
- promoted K/DST uncertainty.

No governance threshold is relaxed.

### 7. Empirical season-error uncertainty
**Status: PARTIALLY CLEARED**

The historical-source discovery gate is materially advanced because true 2024 two-plus-provider PIT raw data exists.

Still required before promotion:
- full rule-representative scoring coordinates;
- realized-outcome truth under the selected calibration fixture;
- rights-cleared use;
- validation adequate to support a production coefficient rather than merely a research fit.

### 8. Weekly volatility
**Status: PARTIALLY CLEARED**

The merged harness correctly fits weekly volatility directly from realized game scores rather than season-total/17.

Research now has:
- official Sleeper semantics sufficient to reconstruct more coordinates;
- historical weekly K/DST projection panels for forecast-error studies.

Promotion still requires complete realized scoring truth for the target rule set and governed validation.

### 9. 2026 Hodor preseason comparison
**Status: STILL BLOCKED**

K:
- two providers exist, but exact 50-59 vs 60+ evidence does not.

D/ST:
- one component source + one aggregate consensus are recovered;
- no proven second independent component source;
- no valid game-level PA distribution for bucket scoring.

Correct product behavior remains explicit preseason-unavailable, not fabricated or silently partial authority.

### 10. Downstream Value / Simulation / Decision / Search
**Status: STILL BLOCKED downstream of Forecast authority**

- Simulation needs promoted weekly distributions/uncertainty.
- Value needs Forecast authority plus Value-owned K/DST replacement/scarcity economics.
- Decision/Search must not invent missing projections or economic values.

### 11. Private beta
**Status: STILL BLOCKED as a source-rights assumption**

“Private beta” does not convert personal/non-commercial terms into organizational ingestion/storage rights. The product may only use provider content under the rights actually granted.

### 12. Eventual commercial production
**Status: STILL BLOCKED — explicit external licensing dependency**

Commercial promotion requires executed rights for the actual providers/content used, including underlying RotoWire content if consumed through Sleeper unless the governing agreement clearly sublicenses it.

## Exhaustion determination

Materially distinct authorized research paths have been exercised:
- FSFFL governed persistence;
- Git/repository history;
- historical public snapshots;
- source-specific retained CSVs;
- independent public research implementations exposing provider provenance;
- official provider licensing/API documentation;
- official Sleeper scoring documentation;
- 2026 pre-opener provider snapshots.

Remaining unresolved dependencies are not generic-search problems. They require:
1. provider licensing/permission;
2. newly supplied private/retained evidence or licensed historical data;
3. a second independent component-level D/ST source;
4. exact K 60+ projection coverage;
5. later bounded Implementation work for truth fixtures/calibration promotion.

## Operating-protocol conclusion

Question: **Is there another authorized research action available now that could materially resolve or better characterize a remaining gate?**

Answer: **No, not from presently available public/governed evidence.**

The unresolved items now depend on external provider permission/data access or later Implementation authority, not additional undirected Research searching.

**DIRECTIVE COMPLETE — RESEARCH**
