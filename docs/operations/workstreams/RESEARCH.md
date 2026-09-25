# Workstream — Forecast Research: K/DST + New-League Bootstrap

## State
**DIRECTIVE COMPLETE — RESEARCH**

Completed: 2026-09-24  
Completion artifact: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`  
Research implementation-history PR: #213  
Research commit: `91018b39967a0775ad830a6a750a2588e7f041d0`

## Objective
Produce an evidence-backed, implementation-ready governed Forecast architecture for leagues containing K and/or D/ST, while separately defining new-league Forecast bootstrap when no preserved preseason baseline exists.

**Outcome:** complete. No implementation, production model-authority change, merge, or deployment was performed by Research.

## Final governed research outcome

### K
- K is a distinct Forecast family but remains an individual-player subject.
- K requires a raw-stat contract that can represent FG attempts/makes/misses, distance buckets, XP attempts/makes/misses, and any other active league-scoring component.
- Provider eligibility is rule/metric specific. A source with only aggregate or 50+ FG data cannot satisfy scoring that separately values 50–59 and 60+.
- Existing independent-source authority is retained; it is not weakened to make a league load.

### D/ST
- D/ST is a canonical NFL **team-season unit** Forecast subject, not an ordinary human player.
- Team special-teams scoring (`def_st_*`) and player special-teams scoring (`st_*`) remain distinct subject families.
- Linear D/ST events require explicit raw evidence.
- Points-allowed and yards-allowed bucket scoring require game-level/distributional evidence. Season averages are not an exact scoring substitute.

### Scoring / completeness
- Forecast scoring must become active-rule complete: every active non-zero rule relevant to a subject must have exact, exact-derived, distributional, or separately authorized provisional evidence.
- Missing material evidence must fail closed rather than be interpreted as zero.
- Research identified a current integrity hole: `fum_lost` is classified as supported, but `FUMBLES_LOST` is not covered by the existing material-metric completeness guard. The preserved 2026 offensive raw ensemble contains no fumble-loss observations, so late-league replay can otherwise silently omit an active fumble penalty.

### Uncertainty
- K and D/ST require their own empirical season-error and weekly-volatility calibration.
- QB/RB/WR/TE uncertainty coefficients must not be reused.
- Provider disagreement alone is not sufficient simulation-grade uncertainty.
- No new K/DST production coefficient was promoted by this directive.

### New-league bootstrap
- The durable target remains one immutable **league-agnostic annual preseason raw-stat snapshot per NFL season**, later rescored under each league's rules.
- A post-preseason league may bootstrap only from:
  1. a valid existing annual snapshot; or
  2. an evidence-preserving migration of genuinely retained point-in-time raw Forecast evidence.
- Migration must preserve original source identity, effective/retrieved timestamps, hashes, raw observations, and lineage. Current pages cannot be refetched and backdated.
- If no qualifying preseason evidence exists, preseason comparison is explicitly unavailable; current-forward Forecast may still operate independently if its own authority gates pass.

## Production evidence inspected
Read-only production evidence established:
- the original FSFFL league has no K/DST starters;
- the newly connected 2026 league has one K and one D/ST starter;
- no `annual_preseason_projection_snapshot` is persisted for 2026;
- legacy preseason baseline artifact **145** is genuine retained 2026 point-in-time offense evidence:
  - FFToday + Razzball;
  - evaluation time `2026-09-10T21:36:41.346326Z`;
  - 1,675 raw ensemble observations;
  - QB/RB/WR/TE only;
  - no `fumbles_lost`;
  - prior retained evidence proves raw-array parity with its source artifact.
- artifact 145 is therefore a candidate for governed **offense evidence migration**, not universal replay authority for arbitrary scoring.
- no qualifying persisted two-independent-source 2026 preseason K/DST raw package was proven.

## Source/provenance findings
The complete source inventory and URLs are retained in the completion artifact.

High-level dispositions:
- FFToday: independent projection candidate with recoverable dated K/D/ST historical pages; raw detail is insufficient for some arbitrary scoring coordinates.
- CBS: independent projection candidate with useful K/DST raw components; content year/horizon must be validated from content, not URL.
- Razzball: independent projection candidate with useful K/DST components; page/content semantics and rights require explicit validation.
- FantasyPros: useful aggregate/reference evidence; not automatically an independent second vote.
- nflverse/nflfastR: preferred realized-outcome / reconstruction backbone, not a Forecast provider.
- Sleeper: authoritative for league roster/scoring configuration and useful validation evidence; not itself a replacement projection source.

## Implementation handoff
The authoritative implementation contract is:
`artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Implementation should proceed in this order **only after Management authorizes it**:
1. subject contracts + rule-complete scoring integrity;
2. realized-outcome reconstruction and K/DST calibration research harness;
3. provider adapters and source-health/rule-coverage gates;
4. annual snapshot v2 + evidence-preserving legacy migration;
5. downstream Team Utility / Value / Decision compatibility;
6. full new-league lifecycle acceptance.

The handoff includes deterministic fixtures for:
- no K/DST;
- K only;
- K scoring with insufficient distance detail;
- D/ST linear scoring;
- D/ST points-allowed buckets;
- insufficient D/ST distribution evidence;
- K + D/ST;
- team vs player special teams;
- missing `fum_lost`;
- late-connect annual replay;
- migrated 2026 offense evidence;
- late connect with no reconstructable preseason evidence.

## Acceptance requirements handed to implementation
Implementation must prove at minimum:
- D/ST is not modeled as a human player;
- K/DST identity and team aliases are deterministic;
- every active scoring rule has explicit evidence coverage;
- aggregate PA/Yards cannot stand in for bucket distributions;
- 50+ FG data cannot satisfy a distinct 50–59 / 60+ coordinate;
- team and player special-teams scoring do not contaminate each other;
- active missing `fum_lost` fails closed;
- two-source/independence governance remains intact;
- K and D/ST use separate promoted uncertainty evidence;
- annual snapshot replay remains league-agnostic;
- no post-opener refetch is relabeled as preseason evidence;
- downstream systems never invent missing Forecast or Value truth;
- the original no-K/DST FSFFL league remains regression-clean.

## Unresolved risks / evidence gaps
These remain explicit downstream gates, not unfinished Research work:
1. A second genuinely independent historical point-in-time K/DST projection corpus is still needed for empirical production calibration matching current two-source standards.
2. Provider commercial/storage/redistribution rights need review before commercial promotion.
3. Exact Sleeper semantics for obscure K/DST events and points-allowed accounting need truth fixtures.
4. No qualifying 2026 two-source preseason K/DST raw package is currently proven; it must not be fabricated.
5. K/DST dynasty economics, replacement, and scarcity remain Value-owned work after Forecast production evidence is promoted.

## Management disposition
Research acceptance criteria in `../ACCEPTANCE_GATES.md` are satisfied.

Next authority belongs to **Management**:
- review/accept this research contract;
- authorize a bounded implementation directive if desired;
- keep Performance at its existing Forecast dependency gate until governed implementation and lifecycle acceptance are complete.

Research must not begin implementation under this completed directive.

## Original prohibitions remain binding
- Do not lower evidence thresholds just to turn a gate green.
- Do not fabricate K/DST projections.
- Do not force D/ST through ordinary-player semantics.
- Do not let Team Utility/Behavioral contaminate Forecast or universal Value.
- Do not merge/deploy model-authority changes without Management authorization.
