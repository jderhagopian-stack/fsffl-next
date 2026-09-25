# Workstream — Forecast Research: League-Agnostic Scoring Coverage

## State
**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**

Authorized: 2026-09-25  
Completed: 2026-09-25

Durable artifacts:
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PLATFORM_COVERAGE_MATRIX.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PRIMARY_SOURCE_LEDGER.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/GAP_ANALYSIS.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/IMPLEMENTATION_HANDOFF.md`

Prior K/DST Research remains complete and authoritative:
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`
- `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`
- `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`

## Objective

Audit common fantasy-football scoring configurations across major platforms and determine whether FSFFL NEXT's canonical Data → Forecast → scoring contracts can represent and forecast them without heuristic reconstruction.

The directive required:
- a league/provider-independent Scoring Coordinate Registry;
- a governed platform/rule coverage matrix;
- FULL/PARTIAL/UNSUPPORTED capability taxonomy;
- provider-acquisition gap analysis;
- historical-stat/data-retention gap analysis;
- scoring-engine audit;
- extensible contract recommendations;
- prioritized gaps without fabricated prevalence;
- deterministic fixtures;
- an implementation-ready handoff.

All required deliverables are complete.

## Primary-source scope completed

Current primary-source or direct platform evidence was reviewed for:
- Sleeper;
- ESPN;
- Yahoo;
- NFL Fantasy;
- CBS;
- Fantrax;
- MyFantasyLeague;
- DraftKings Best Ball.

Provider/data-schema evidence was also reviewed where useful to determine whether richer raw Forecast inputs can technically be preserved without making any provider authorization decision.

The research distinguishes:
- documented defaults/public or contest presets;
- documented configurable/custom rules;
- engine-capability examples.

Configurability is not treated as prevalence.

## Scoring Coordinate Registry result

The machine-readable registry currently contains **89 canonical football coordinates or scoring-semantic requirements** spanning:
- passing;
- rushing;
- receiving;
- turnovers;
- player special teams;
- kicking;
- team D/ST;
- IDP;
- punting;
- head-coach/team-result scoring;
- position predicates;
- fractional/negative scoring policy;
- threshold/bucket/stacking/conditional semantics;
- platform attribution semantics.

The platform matrix contains **48 documented platform/preset or rule-family mappings** to those registry coordinates.

These counts describe the audit artifact, not a permanent maximum. Future coordinates must be added through registry governance rather than platform-specific Forecast code.

## Major findings

### 1. Conventional offense is the strongest current area

FSFFL already natively Forecasts and scores:
- passing yards/TD/INT;
- rushing yards/TD;
- receptions/receiving yards/TD;
- fumbles lost.

This covers the core of conventional non-PPR/half-PPR/PPR scoring and must remain regression-clean.

### 2. Direct 2PT and common rare defaults are still provisional/missing

Current ordinary scoring uses bounded priors for:
- pass/rush/rec 2PT;
- selected player fumble/special-teams events.

Multiple major platforms directly score 2PT, player return TD and offensive fumble-recovery TD.

League-agnostic end state should preserve/Forecast those events directly where evidence permits rather than rely on a TD-rate residual.

### 3. The next scalar-coordinate gap is material

Major platforms expose configurable scoring for:
- pass attempts;
- completions;
- incompletions;
- sacks taken;
- rush attempts;
- first downs;
- receiving targets;
- fumbles;
- player return yards;
- pick-six thrown.

FSFFL's current ordinary provider normalization discards these fields even if a provider can supply them.

### 4. Nonlinear scoring is a distinct Forecast-evidence problem

Documented scoring includes:
- 300+/400+ passing games;
- 100+/200+ rushing/receiving games;
- completion/carry thresholds;
- long-play bonuses;
- D/ST PA/YA buckets;
- IDP threshold bonuses;
- punt-average ranges;
- conditional rules.

For these:
`score(E[X]) != E[score(X)]` generally.

A season mean is not sufficient. Forecast needs per-game distributions, bucket probabilities, event-count distributions or joint distributions depending on the rule.

DraftKings 2026 Best Ball uses yardage milestone bonuses as a current contest default, making this a commercial P0 architecture gap rather than merely an exotic custom-league feature.

### 5. Position-sensitive scoring belongs in scoring semantics

Sleeper and Fantrax evidence demonstrate position-sensitive scoring such as TE/position reception bonuses.

Correct design:
- Forecast one canonical `RECEPTIONS` coordinate;
- apply a position predicate in the scoring rule.

Do not create separate TE-reception Forecast truth.

### 6. Current canonical ScoringRule is too narrow

Current:
`ScoringRule(stat: str, points: float)`

This cannot generically express:
- position predicates;
- thresholds/ranges;
- cumulative vs exclusive stacking;
- fractional/quantization policy;
- negative-yardage policy;
- conditional expressions;
- platform-specific D/ST semantic profiles.

Sleeper raw numeric scoring ingestion is relatively flexible, but cross-platform canonical rule semantics are not.

### 7. IDP requires State expansion, not just more Forecast metrics

Current `Position` and `RosterSlot` do not include IDP positions.

Sleeper, ESPN, Yahoo, NFL Fantasy, Fantrax, CBS and MyFantasyLeague all provide evidence that IDP is a commercially relevant configurable family.

D/ST team-unit stats cannot be reused as IDP player stats.

Full IDP support requires:
- defensive player/slot identity;
- Forecast coordinates;
- provider evidence;
- historical truth;
- separate uncertainty;
- downstream lineup/Value/Simulation support under their own authority.

### 8. K/DST architecture is the best model for future expansion

The K/DST work already demonstrates useful patterns:
- explicit rule-to-coordinate requirements;
- exact transforms;
- subject-family isolation;
- per-coordinate source independence;
- distributional evidence for nonlinear buckets;
- scoring-fingerprint-bound calibration.

The broader scoring registry should generalize those patterns rather than create a second architecture.

### 9. Raw provider evidence is currently lost too early

Ordinary provider adapters populate a narrow canonical subset before Forecast sees the data.

Research recommends preserving a rights-permitted provider-native numeric superset with:
- source/effective/capture time;
- horizon;
- raw provider field;
- value;
- mapping version;
- content identity;
- rights class.

A field may remain unmapped without being discarded.

This is especially important for attempts, completions, carries, targets, 2PT, return stats and IDP.

### 10. Historical Data is structurally flexible but replay is incomplete

`SleeperWeeklyStatsSource` already preserves arbitrary numeric stat keys, which is a strong Data-layer foundation.

However:
- those keys lack a governed cross-platform canonical registry mapping;
- broader nonlinear/IDP replay is not implemented;
- D/ST attribution remains semantic-profile dependent;
- annual/PIT provider evidence today may omit fields discarded by provider adapters.

Historical retention should preserve raw coordinate supersets and mapping versions before future calibration needs arise.

## Capability taxonomy

Runtime capability is evaluated at:
`league × rule × subject family × horizon × evidence cutoff`.

### FULL
Every active material rule:
- maps to canonical coordinates and semantics;
- has supported subject identity;
- has exact or governed distributional Forecast evidence;
- satisfies independence/rights;
- has compatible uncertainty where required.

### PARTIAL
The rule maps, but one or more evidence/uncertainty/source requirements are missing.

PARTIAL is diagnostic only. It does not authorize an incomplete fantasy-point total.

### UNSUPPORTED
The rule/subject semantics cannot yet be represented or mapped safely.

Required reason codes include:
- `missing_forecast_coordinate`
- `missing_distributional_evidence`
- `unsupported_subject_family`
- `unsupported_rule_semantics`
- `platform_semantics_unresolved`
- `insufficient_independent_sources`
- `rights_not_cleared`
- `uncertainty_not_compatible`

## Proposed architecture

Separate two contracts:

### Scoring Coordinate Registry
Owns football/statistical facts:
- canonical coordinate;
- subject family;
- evidence shape;
- exact transforms;
- historical/calibration requirements.

### Canonical Scoring Rule Contract
Owns league scoring semantics:
- operator;
- period;
- coefficient;
- thresholds/ranges;
- position predicate;
- stacking policy;
- fractional/negative policy;
- semantic profile;
- provenance to raw platform rule.

Forecast remains league-agnostic.

## Implementation priority

### P0
- registry + rule contract v2;
- capability diagnostics;
- raw provider superset preservation;
- direct common 2PT/return/fumble-recovery events;
- position predicates / TE premium;
- per-game yardage milestone distributions;
- D/ST semantic profiles.

### P1
- attempts/completions/incompletions/sacks;
- rush attempts;
- first downs;
- targets;
- fumbles;
- player return yards;
- linear D/ST PA/YA;
- core IDP subject/Forecast family.

### P2
- long-play event counts;
- reception-distance buckets;
- combined rush+rec milestones;
- drive outcomes;
- IDP threshold bonuses.

### P3
- punter;
- head coach/team offense;
- arbitrary conditional rule support beyond capability reporting.

These priorities are based on documented defaults/presets, repeated configurable availability, current commercial contest use and architectural leverage. They are not percentage-of-leagues estimates.

## Recommended bounded implementation

**Stage 0 + Stage 1 only** should be the first implementation package:
1. registry definitions;
2. canonical scoring-rule/capability contracts;
3. compile existing scoring through compatibility lane;
4. raw provider superset preservation;
5. explicit FULL/PARTIAL/UNSUPPORTED reporting;
6. zero new production scoring/model authority.

Stages adding new coordinates, nonlinear Forecast distributions, IDP or new production authority should follow separate evidence/acceptance gates.

Implementation details:
`artifacts/research/scoring_coordinate_coverage_20260925/IMPLEMENTATION_HANDOFF.md`

## Deterministic fixtures

The handoff/gap analysis defines fixtures for:
- current conventional PPR regression;
- Yahoo default half-PPR;
- ESPN volume scoring;
- Sleeper TE premium;
- points-per-first-down;
- DraftKings milestone bonuses;
- nested/exclusive long-play stacking;
- fractional-off scoring;
- negative-yardage policy;
- K exact distance transforms;
- cross-platform D/ST semantic profiles;
- IDP;
- player vs team special teams;
- Fantrax position-sensitive scoring;
- MFL conditional fail-closed;
- provider raw-superset retention;
- unknown custom-rule fail-closed.

## Authority boundary

This Research directive does **not**:
- add production Forecast coordinates;
- promote provider evidence;
- change scoring outputs;
- add IDP to production;
- change uncertainty;
- authorize provider use;
- merge model behavior.

Existing production authority remains unchanged.

## Operating-protocol closure

Required research paths across major platforms, advanced configurable platforms, current FSFFL code, provider normalization, historical stat ingestion, nonlinear scoring, subject families and commercial best-ball scoring have been materially exhausted.

Question: **Is there another authorized Research action available now that could materially change the implementation contract?**

Answer: **No.** Remaining work is bounded implementation and later coordinate/provider/model evidence, not another undirected scoring-option survey.

The next authority decision belongs to Management: authorize or defer the recommended zero-authority-change Stage 0 + Stage 1 implementation package.

**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**


---

## Preserved prior Management decision — 2026 provisional K/DST degraded-authority mode — 2026-09-25

**State: AUTHORIZED FOR BOUNDED FORECAST IMPLEMENTATION**

Management accepts the completed Research finding that the normal full Hodor K/DST authority gates remain red, but clarifies the product purpose of the one-season-only late-start exception: the 2026 private-beta league must be able to obtain useful current-forward K/DST intelligence without fabricating unsupported scoring coordinates.

This is a second, explicit and strictly bounded 2026 exception. It does not alter the normal Forecast authority standard and must expire for 2027+.

### Authorized behavior
Forecast Implementation may produce a clearly identified **2026 provisional K/DST Forecast** from qualifying current ROS evidence using only scoring coordinates that are actually supported by governed evidence.

The provisional Forecast must:
- use the true current-date ROS horizon and acquisition/provenance/source-health metadata;
- retain the strongest available independence/governance for supported coordinates;
- score only evidence-supported coordinates and exact algebraic transforms;
- explicitly identify omitted/undercovered active scoring coordinates;
- expose partial-rule-coverage / provisional authority in machine-readable contracts and Presentation;
- preserve uncertainty honestly and distinguish empirically supported uncertainty from additional uncertainty caused by omitted coordinates;
- remain ineligible to masquerade as full-rule-complete Hodor Forecast authority;
- remain ineligible for any 2026 preseason comparison;
- fail closed outside season 2026 and be impossible to use as the 2027+ preseason/production standard.

### Specific treatment
For K, a provider's governed 50+ projection may support the Hodor base five-point contribution for 50+ makes. The additional +1 contribution specific to 60+ makes must remain omitted unless governed 60+ evidence exists. Do not estimate or allocate 60+ frequency heuristically under this authorization.

For D/ST, governed projected coordinates may contribute where supported. Unsupported nonlinear PA-bucket expectation and unsupported rare-event coordinates must remain omitted rather than imputed, reverse-engineered, or fabricated. Aggregate PA must not be passed through the nonlinear Hodor PA ladder as though it were a distribution.

### Authority and downstream use
This provisional tier exists for 2026 private-beta usability. Downstream consumers must be able to distinguish it from full Forecast authority. Implementation must explicitly determine and test which downstream surfaces/calculations can safely consume provisional K/DST evidence and which require full authority; no consumer may silently upgrade provisional evidence.

The existing full-authority gates remain recorded and unchanged. If they clear, full governed K/DST authority supersedes the provisional tier.

### Implementation directive
Do not reopen generic source Research. Resume Forecast Implementation from PR #233/main and implement the minimum bounded contracts, calculations, provenance, coverage reporting, downstream gating, tests, and presentation/readiness semantics necessary for this 2026 provisional mode. Preserve all existing fail-closed behavior for 2027+ and for claims requiring full-rule authority.

Persist an implementation handoff and follow OPERATING_PROTOCOL.md to a permitted terminal state.
