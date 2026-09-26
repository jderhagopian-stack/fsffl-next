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


---

## Management directive — Single-source authority for bounded auxiliary Forecast coordinates
**State: MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION**

Management authorizes a narrow Research study to determine whether FSFFL NEXT should permit **one governed production projection source** for selected low-materiality auxiliary scoring coordinates instead of applying the normal two-independent-source standard uniformly to every coordinate.

This directive is motivated by current evidence that missing low-frequency coordinates can block otherwise strong Forecast/Simulation coverage. It does **not** pre-decide that one source is sufficient and it does **not** change production authority. Existing source/rights/uncertainty gates remain in force until Management explicitly accepts a resulting rule.

### Research question
Under what empirically defensible conditions can a single rights-cleared, semantically exact Forecast source support an auxiliary scoring coordinate without materially degrading player, lineup, team, or Simulation outcomes?

The study must distinguish:
1. **core/material coordinates** — remain subject to normal multi-source authority;
2. **bounded auxiliary coordinates** — candidates for single-source authority if empirical impact and source quality support it;
3. **unforecastable/tail coordinates** — remain explicit omissions rather than fabricated values.

Do not define these classes by eccentricity, frequency, or intuition alone. Classification must be based on measured scoring/outcome materiality plus evidence quality.

### Candidate coordinate set
At minimum evaluate:
- `fumbles_lost`;
- 60+ field-goal makes / the incremental 60+ scoring contribution;
- field-goal misses where separately scored;
- XP misses where separately scored;
- common two-point conversion coordinates;
- low-frequency player/team special-teams scoring events already represented in the canonical scoring registry;
- other currently undercovered coordinates that the registry identifies as plausible bounded auxiliaries.

Treat nonlinear D/ST points-allowed distributions, major volume statistics, passing/rushing/receiving yards and TDs, receptions, and other obviously material core coordinates as **controls**, not presumed single-source candidates.

A coordinate with a rare event but a very large scoring coefficient must not qualify merely because the event is infrequent.

### Required materiality measurements
For each candidate coordinate, using authentic historical/PIT evidence where available:
- event frequency and zero-rate;
- mean absolute seasonal fantasy-point contribution;
- median, p90, p95 and p99 absolute seasonal contribution;
- contribution as a share of player fantasy points and of total scored variance;
- impact on positional/player rank ordering;
- impact on optimized lineup selection and starter/bench decisions;
- impact on team projected points;
- impact on league-relative position strength / Team Utility where applicable;
- impact on 50,000-run Simulation outputs when feasible, including expected wins and playoff/championship probability deltas;
- worst observed and bounded stress-case effects.

Use deterministic seeds/replay for Simulation sensitivity. Do not use the 2022 startup as an FSFFL historical acceptance sample.

### Required source-quality measurements
For any proposed single-source coordinate, evaluate:
- exact semantic match to the canonical coordinate and platform scoring meaning;
- production/data-use rights;
- acquisition timestamp and provenance;
- PIT availability and revision behavior;
- missingness/coverage stability;
- historical bias, MAE/RMSE and calibration where target evidence exists;
- source stability across seasons;
- whether the source is direct or derived/aggregate;
- independence status relative to other providers;
- disagreement with additional sources during historical periods where overlap exists.

When two or more historical sources overlap, compare the single-source estimate against both actual outcomes and the multi-source ensemble so Management can quantify the cost of relaxing the second-source requirement.

### Authority framework to test
Research should test and recommend quantitative boundaries rather than assume them.

A candidate **bounded auxiliary** rule should require all of the following in principle:
- exact coordinate semantics;
- rights-cleared production use;
- a direct governed source rather than an opaque consensus unless independence/provenance is resolved;
- empirically bounded scoring/outcome sensitivity;
- non-zero, target-compatible uncertainty;
- explicit provenance and authority tier in machine-readable contracts;
- automatic demotion to PARTIAL/UNSUPPORTED when source health or coverage fails;
- no silent zero, heuristic frequency allocation, or substitution from a neighboring statistic.

Research must determine whether thresholds should be absolute, position-relative, scoring-relative, or multi-dimensional. It must not choose a threshold merely to make Hodor or any one league pass.

### Specific hypotheses to test
- **60+ FG incremental scoring:** likely bounded auxiliary because only the incremental points above the supported 50+ contribution are at issue; test rather than assume.
- **FUMBLES_LOST:** potentially eligible for single-source treatment but presumptively more material than 60+ FG because it applies broadly across offensive players; require stronger historical/source validation.
- **Nonlinear D/ST PA distribution:** presumptively material/non-auxiliary control because it can move D/ST totals substantially and requires distributional evidence; test sensitivity but do not collapse it into the rare-event category.
- **Rare special-teams events:** candidate auxiliary only when both event frequency and scoring sensitivity are bounded.

### Counterfactual comparison
For each viable candidate, compare at least these conditions:
A. coordinate omitted / current partial-authority behavior;
B. one governed source;
C. two-or-more-source ensemble where historically available;
D. realized outcome.

Report whether B materially improves total Forecast accuracy and downstream usefulness relative to A, and how much authority/accuracy is lost versus C.

### Required outputs
Persist a durable Research package containing at minimum:
- `AUXILIARY_COORDINATE_MATERIALITY.csv` — per-coordinate impact metrics and tested scoring profiles;
- `SINGLE_SOURCE_QUALITY_LEDGER.csv` — provider/coordinate provenance, rights, semantic fit and historical error;
- `SINGLE_VS_MULTI_SOURCE_REPLAY.csv` — comparable replay results where overlapping sources exist;
- `DOWNSTREAM_SENSITIVITY.md` — lineup/team/Simulation effects, including 50,000-run sensitivity where feasible;
- `AUTHORITY_TIER_RECOMMENDATION.md` — proposed general rule/thresholds, exceptions and failure behavior;
- `RESEARCH_HANDOFF.md` — exact Management decision options and implementation implications.

The recommendation must be league-agnostic and coordinate-based. Hodor may be used as an illustrative scoring profile, not as the rule definition.

### Authority boundary
This study authorizes research and analysis only. It does **not**:
- weaken the current two-independent-source production rule;
- promote a one-source K/DST, FUMBLES_LOST or other coordinate;
- change current Forecast/Simulation/Value/Decision/Search outputs;
- invent source rights;
- permit heuristic 60+ allocation from a 50+ bucket;
- treat absent evidence as zero;
- reopen unrelated completed Forecast Research.

If evidence supports a generalized single-source auxiliary tier, return at **MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION** with the proposed quantitative contract. If evidence does not support it, return **DIRECTIVE COMPLETE — RESEARCH** with the negative finding and retain current authority.

Follow `OPERATING_PROTOCOL.md`; do not stop at an intermediate source failure while another authorized analysis can materially advance the directive.


### Research closeout — 2026-09-25

The bounded materiality/source-authority study is complete.

Durable package:
- `artifacts/research/auxiliary_single_source_authority_20260925/AUXILIARY_COORDINATE_MATERIALITY.csv`
- `artifacts/research/auxiliary_single_source_authority_20260925/SINGLE_SOURCE_QUALITY_LEDGER.csv`
- `artifacts/research/auxiliary_single_source_authority_20260925/SINGLE_VS_MULTI_SOURCE_REPLAY.csv`
- `artifacts/research/auxiliary_single_source_authority_20260925/DOWNSTREAM_SENSITIVITY.md`
- `artifacts/research/auxiliary_single_source_authority_20260925/AUTHORITY_TIER_RECOMMENDATION.md`
- `artifacts/research/auxiliary_single_source_authority_20260925/RESEARCH_HANDOFF.md`

Research used 2023–2025 authentic nflverse outcomes, retained pre-opener 2024 provider evidence, deterministic lineup replay, and paired 50,000-run sensitivity. The 2022 startup was not used.

The evidence supports a generalized certified `AUXILIARY_SINGLE_SOURCE` tier in principle but supports **zero immediate source/coordinate promotions**.

Materiality-side candidates:
- K 60+ incremental premium above an already-governed 50+ base;
- K XP miss;
- D/ST safety;
- D/ST defensive two-point return.

Current source-quality status:
- 60+ lacks validated rights-cleared historical source-specific quality/stability evidence;
- XP-miss historical singles are unstable and often worse than omission;
- D/ST safety historical singles are no better or worse than omission;
- defensive two-point return lacks qualifying historical projection validation.

Measured core/material coordinates include FUMBLES_LOST, FG misses, common 2PT, D/ST blocked kicks, ST TD, forced fumbles/recoveries, nonlinear PA distributions, and ordinary volume/TD/reception controls.

Research recommends Management accept the **certification framework only**, with zero active certifications at acceptance. Any later provider/coordinate promotion would require its own retained source-quality, rights, health, coverage, and uncertainty evidence.

The quantitative proposal and failure behavior are authoritative only as a Research recommendation until Management accepts them.

No production authority changed.

Operating-protocol test: no further authorized Research action can materially resolve the policy decision without crossing into source-specific certification under a policy Management has not yet accepted.

**MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION**


### Management clarification — provider-neutral rights staging
Research source-quality recommendations must follow `../SOURCE_GOVERNANCE.md`.

FSFFL is provider-agnostic. A provider-coordinate certification must distinguish analytical authority from usage-rights stage:
- a source may qualify analytically and be `PRIVATE_BETA_ALLOWED` while still carrying `commercial_recheck_required=true`;
- commercial licensing is not a prerequisite for a terms-compliant private-beta source;
- ambiguous/prohibited beta use remains ineligible;
- any commercial transition requires explicit re-audit of all non-`COMMERCIAL_ALLOWED` sources.

Accordingly, references in this workstream/handoffs to "production rights" or "rights-cleared" must be interpreted against the intended deployment stage, not automatically as "commercially licensed today." The auxiliary certification framework should require rights eligibility for the intended deployment stage plus a separate commercial-status field.


## Management directive — FUMBLES_LOST evidence recovery
**State: MANAGEMENT GATE — FUMBLES_LOST SAME-HORIZON AUTHORITY**

The State-first/Product corrective is implementation-complete and production evidence now isolates the existing-FSFFL full-capability blocker to missing governed FUMBLES_LOST Forecast evidence. The preserved two-source preseason raw Forecast contains 1,675 observations but no FUMBLES_LOST coordinate; under current material-coordinate policy this yields partial player Forecast and blocks Simulation.

Management authorizes a narrow Research follow-up to determine the shortest evidence-compliant path to full FUMBLES_LOST authority without weakening the core/material rule.

Required work:
- inventory existing and candidate providers that can supply FUMBLES_LOST at the exact required horizon(s), including already-used providers before adding new ones;
- classify each provider under `../SOURCE_GOVERNANCE.md` and `../SOURCE_RIGHTS_LEDGER.md` for actual private-beta use, keeping commercial re-review separate;
- determine whether two genuinely independent same-horizon sources can be acquired for the current 2026 Forecast path and/or authentic pre-opener PIT baseline;
- verify exact semantics (lost fumbles, not total fumbles), timestamp/horizon compatibility, player coverage, source health, and independence;
- quantify source-specific historical error/stability and derive target-compatible non-zero uncertainty where evidence permits;
- reuse existing retained evidence before searching for new providers;
- do not silently zero FUMBLES_LOST, borrow another horizon, or use the accepted auxiliary-single-source tier because Research already classifies this coordinate as core/material;
- if two-source authority can be established under current policy, persist an implementation-ready handoff;
- if not, return the exact remaining external dependency or a Management gate with evidence for any proposed authority-policy change.

This Research may also reconcile the existing external-source inventory so currently deployed sources and new FUMBLES_LOST candidates are governed consistently. Do not reopen unrelated K/DST or broad scoring research.

Return only at a permitted `OPERATING_PROTOCOL.md` terminal state.


### Research closeout — FUMBLES_LOST authority recovery — 2026-09-26

**State: MANAGEMENT GATE — FUMBLES_LOST SAME-HORIZON AUTHORITY**

Durable closeout:
- `artifacts/research/fumbles_lost_authority_recovery_20260926/SOURCE_AUTHORITY_LEDGER.md`
- `artifacts/research/fumbles_lost_authority_recovery_20260926/RESEARCH_HANDOFF.md`

Research exhausted the retained 2026 pre-opener evidence, the retained 2024 exact lost-fumble panel, current provider behavior, public candidate schemas, current source-rights classifications, horizon compatibility, independence and the available non-zero historical error evidence.

Result:
- the authentic 2026 pre-opener FFToday + Razzball baseline contains no `FUMBLES_LOST`;
- no second deployable authentic 2026 pre-opener pair was recovered;
- current Razzball ROS fumble evidence is source-health red and may not be mixed into a season baseline;
- JerryGM + Fantasy Nerds is the shortest **technical current-ROS** candidate pair, but JerryGM rights remain review-required and Fantasy Nerds' weighted-consensus composition prevents it from counting as an independent second vote until overlap is resolved;
- JerryGM + LineupExperts is the next direct-source candidate, but LineupExperts requires exact lost-fumble schema proof and rights clarification;
- the retained 2024 two-source panel establishes non-zero error/disagreement but is not sufficient to promote 2026 candidate-pair uncertainty.

Under the current Forecast route, a current-ROS lost-fumble coordinate may not be spliced into the preserved season/preseason baseline. Clearing the blocker therefore requires either qualifying same-horizon season/PIT evidence or an explicit Management decision to authorize a bounded ordinary-offense current-ROS Forecast lane/rebase. The latter must be a whole evidence-horizon decision, not a FUMBLES_LOST-only exception.

No zero, single-source, cross-horizon, stale-artifact, or auxiliary-tier workaround is authorized.

**MANAGEMENT GATE — RESEARCH / FUMBLES_LOST SAME-HORIZON AUTHORITY**


### Management acceptance constraint — existing FSFFL must recover full capability
The acceptance-policy path that would simply redefine existing FSFFL partial capability as acceptable is closed. Research should pursue the shortest evidence-compliant FUMBLES_LOST path needed to restore the previously fully supported FSFFL league under the current governed model. Return an exact external blocker if evidence cannot clear it; do not recommend acceptance downgrade merely to close the incident.


## Management authorization — 2026 ordinary-offense current-ROS lane
**State: AUTHORIZED — SOURCE CERTIFICATION / ROS EVIDENCE ACQUISITION**

Management accepts the FUMBLES_LOST handoff's second governed direction and authorizes a bounded 2026 current-ROS ordinary-offense Forecast lane for QB/RB/WR/TE.

Research must now pursue the shortest complete same-horizon source path for the **whole ordinary-offense raw-stat Forecast**, not merely FUMBLES_LOST. Start with the candidate path identified in the closeout:
1. JerryGM + Fantasy Nerds if rights/access, live payload health, exact coordinate coverage and source independence can all be proven;
2. if Fantasy Nerds independence cannot be proven, pursue JerryGM + LineupExperts or the next direct independent provider;
3. reuse any already-governed current ROS source only if it passes source health and the same horizon/coverage contract.

Required:
- obtain/verify stage-appropriate private-beta rights for model/ensemble use;
- verify live API schema, player coverage, effective/capture timestamps and exact ROS horizon;
- establish provider independence without double-voting an aggregate source;
- build a coordinate coverage matrix for all ordinary-offense stats consumed by current supported league scoring, including FUMBLES_LOST;
- establish source-compatible non-zero uncertainty using retained PIT evidence and any additional qualifying replay evidence;
- preserve preseason evidence separately; do not backfill or relabel it;
- return an implementation-ready handoff when a qualifying ROS ensemble is certifiable, or an exact external-dependency blocker if credentials/permission/paid access are required.

This authorization does not promote JerryGM, Fantasy Nerds, LineupExperts or any provider by name. Providers remain replaceable behind canonical contracts.


## Management correction — FUMBLES_LOST current-only supplement
**State: BLOCKED — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS**

The prior whole ordinary-offense ROS-lane authorization is superseded. Research should not rebase all ordinary offensive statistics.

Research must instead determine the shortest two-independent-source path for **FUMBLES_LOST only** as a current-intelligence supplement. The source may be ROS/current evidence, but the implementation contract must explicitly separate:
- source/evidence horizon and acquisition time;
- target scoring period/rate used by current Forecast/Simulation;
- preseason/PIT historical eligibility.

Required Research output:
1. identify the best two independent current sources with exact lost-fumble semantics and stage-appropriate rights;
2. validate live health/coverage and provider independence;
3. define a defensible normalization into the target current-scoring quantity (for example remaining-game rate or season-equivalent expectation) without pretending the source was full-season/preseason evidence;
4. specify non-zero uncertainty;
5. mark the coordinate ineligible for preseason comparison/historical PIT claims before acquisition;
6. produce an implementation-ready handoff.

Do not alter unrelated offensive coordinates or reopen broad ordinary-offense source selection.


### Current-only FUMBLES_LOST certification closeout — 2026-09-26

**State: BLOCKED — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS**

Research completed the bounded current-only certification contract without rebasing any unrelated offensive Forecast coordinate.

Durable artifacts:
- `artifacts/research/fumbles_lost_current_only_certification_20260926/CERTIFICATION_LEDGER.md`
- `artifacts/research/fumbles_lost_current_only_certification_20260926/NORMALIZATION_UNCERTAINTY_CONTRACT.md`
- `artifacts/research/fumbles_lost_current_only_certification_20260926/IMPLEMENTATION_HANDOFF.md`

Result:
- shortest technical direct-source pair: **JerryGM + LineupExperts Premium In-Season**;
- JerryGM exact `fumblesLost` current/ROS semantics and health/provenance schema are established publicly;
- LineupExperts Premium publicly proves exact `FmblL`, supports ROS intervals, and its public ROS board demonstrates current schedule-aware projected-game behavior;
- both sources still require external rights/account evidence before private-beta authority can be promoted;
- LineupExperts must additionally confirm endpoint ownership/independence because its general API terms permit third-party content;
- authenticated full-pool live payloads and canonical per-player coverage cannot be validated without provider credentials/entitlements.

The implementation contract keeps source evidence truthfully current/ROS and derives only a **17-game season-equivalent current pace** for the existing current-scoring/Simulation interface. It does not mutate or re-label the ordinary season/preseason Forecast.

Non-zero uncertainty is explicitly required:
- equal-source retained PIT raw-event RMSE floor = **1.13855744535 lost fumbles**;
- provider-disagreement standard deviation = `abs(source_A - source_B) / 2` on the season-equivalent target;
- coordinate stddev = `max(provider_disagreement_std, 1.13855744535)`.

The persisted supplement is ineligible before:
`authority_valid_from = max(source_A.captured_at, source_B.captured_at)`.

It must carry:
- `preseason_eligible=false`;
- `annual_preseason_snapshot_eligible=false`;
- `historical_pit_before_authority_valid_from=false`;
- `backfill_allowed=false`.

Remaining external dependencies:
1. JerryGM API access plus written narrow derived-ensemble/model-input permission.
2. LineupExperts Premium ROS API entitlement, FSFFL application registration, written model-input/persistence permission, and written confirmation of projection ownership/independence.
3. One governed live two-source capture proving player identity, schedule freshness, row health and per-player coverage.

If LineupExperts cannot clear rights/independence, SportsDataIO is the strongest direct licensed fallback. Fantasy Nerds remains aggregate and cannot automatically count as the second vote.

**BLOCKED — RESEARCH / EXTERNAL PROVIDER RIGHTS AND LIVE CREDENTIALS**


## Management directive — first-party FUMBLES_LOST Forecast model
**State: DIRECTIVE COMPLETE — FIRST-PARTY FUMBLES_LOST MODEL READY FOR IMPLEMENTATION**

Management removes bespoke external-vendor permission from the immediate FSFFL recovery critical path.

Research must build and evaluate the smallest defensible Forecast-owned model for exact player FUMBLES_LOST using governed historical football outcomes and point-in-time current inputs already available to FSFFL.

Required research:
- define the exact prediction target and target period used by current scoring/Simulation;
- inventory governed historical FUMBLES_LOST outcomes and candidate pre-cutoff features;
- prefer simple interpretable baselines first (position/opportunity-rate, player-history shrinkage, opportunity-conditioned count/rate models) before higher-complexity challengers;
- use chronological/out-of-time validation only; no random leakage across future seasons;
- compare against omission/zero, position-rate, and any retained historical projection baselines where legally/analytically permitted;
- evaluate MAE/RMSE/calibration, rank/order usefulness where relevant, tail behavior, zero inflation, player/position coverage, and stability by season;
- derive non-zero predictive uncertainty from out-of-time residuals and/or a governed count distribution;
- test whether current canonical opportunity Forecast inputs (for example passing/rushing/receiving opportunity where available) improve the model without making it circular or horizon-incoherent;
- preserve preseason/PIT truth: a current first-party model artifact may be valid only from its actual build/evaluation cutoff unless separately reconstructed historically;
- produce current-player shadows and explicit failure/coverage behavior;
- freeze model/features/coefficients or artifact before live-player inspection; no named-player tuning;
- persist a production-readiness handoff if the model clears the governed accuracy/stability/coverage bar.

The JerryGM + LineupExperts external path remains a fallback/benchmark only and should not block this work.

Do not reopen unrelated Forecast coordinates or long-horizon Intrinsic research.


### First-party FUMBLES_LOST model closeout — 2026-09-26

**State: DIRECTIVE COMPLETE — RESEARCH / FIRST-PARTY FUMBLES_LOST MODEL READY FOR IMPLEMENTATION**

Durable package:
- `artifacts/research/fumbles_lost_first_party_model_20260926/MODEL_SPEC.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_INPUT_ASSESSMENT.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/VALIDATION_RESULTS.json`
- `artifacts/research/fumbles_lost_first_party_model_20260926/OOT_METRICS.csv`
- `artifacts/research/fumbles_lost_first_party_model_20260926/CALIBRATION.csv`
- `artifacts/research/fumbles_lost_first_party_model_20260926/COLD_START_STRESS.csv`
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_SHADOWS.csv`
- `artifacts/research/fumbles_lost_first_party_model_20260926/DATA_LINEAGE.json`

Research selected the smallest model that cleared the predeclared evidence bar:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`.

Chronological OOT:
- 2023 held out after training through 2022;
- 2024 held out after training through 2023;
- 2025 held out after training through 2024;
- only Weeks 1–2 of each target season are permitted as target-season inputs;
- no random split, future leakage or named-player tuning.

Combined primary OOT sample: 1,599 player-seasons.

Selected result:
- RMSE **0.8105091976** vs zero/omission **1.0425150391** and position game-rate **1.0475162746**;
- MAE **0.4868439130**;
- bias **+0.0508840912**;
- Spearman **0.4450645773**;
- zero-calibration gap **0.0347225013**;
- tail RMSE **1.3696260176** vs omission **2.2032564354**.

Held-out RMSE:
- 2023 **0.9103468343**;
- 2024 **0.7819080813**;
- 2025 **0.7332392771**.

Current 2026 train-only global calibration scalar:
`0.6158756078393594`.

Non-zero OOT residual uncertainty floors:
- QB **1.7266303754**;
- RB **0.7375205714**;
- WR **0.4424922528**;
- TE **0.4524060196**;
- cold-start stress **0.7899186992** lost fumbles.

Current 335-player shadow:
- 327/335 deterministic identities = **97.6119%**;
- 258 history+current;
- 40 history-only;
- 28 current-only;
- 1 cold-start;
- 8 identity-light/unmapped.

The eight identity-light current FSFFL rows are BENCH/TAXI in the current State; they remain explicit degraded-evidence rows and must not be interpreted as zeros.

The current canonical FSFFL State reports `completed_through_week=2`, exactly matching the validated cutoff.

The retained 1,675-observation provider Forecast bundle was evaluated as a possible feature source but does not contain the exact opportunity variables required by the accepted model and lacks a comparable multi-season Week-2 PIT archive. It is therefore excluded from v1 rather than used through an unvalidated proxy.

The model output is current-only Forecast evidence. It is ineligible for 2026 preseason comparison, annual preseason snapshots, historical PIT queries before its actual authority timestamp, or backfill.

The external JerryGM + LineupExperts route is now fallback/benchmark only and is not the production-readiness critical path for this coordinate.

Question: **Is there another authorized Research action available now that materially advances the directive before Forecast Implementation begins?**

Answer: **No.**

**DIRECTIVE COMPLETE — RESEARCH / FIRST-PARTY FUMBLES_LOST MODEL READY FOR IMPLEMENTATION**


## Management directive — long-horizon Intrinsic term-structure research
**State: MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE**

The prior FUMBLES_LOST directive's instruction not to reopen long-horizon Intrinsic work is satisfied and superseded for this separate workstream because that Research directive is now complete. Forecast/Product Implementation continues the FSFFL recovery independently.

Research must evaluate the defensible time structure of FSFFL Intrinsic Value rather than assume the current three-year production horizon is permanent.

### Core research questions
- Compare candidate horizon architectures, including at minimum: current/near-term, existing three-year, a longer discrete horizon such as five years, and a terminal/career formulation.
- Determine whether Years 4+ support detailed statistical Forecasts or should instead use career-state/survival, expected role tier, age/position transition, conditional production, replacement surplus and terminal-value evidence.
- Quantify incremental predictive/economic signal beyond the existing Y1–Y3 architecture and identify the point at which extra horizon adds mostly uncertainty rather than useful information.
- Evaluate discounting/decay and terminal-value treatment empirically; do not select coefficients merely because they yield intuitive player rankings.
- Define uncertainty by horizon and require it to widen appropriately where evidence degrades.

### Validation contract
- preserve the current production three-year Intrinsic as the baseline/oracle for the existing governed horizon;
- use historical point-in-time inputs and chronological/out-of-time evaluation wherever the data permit;
- no future leakage, random future-season mixing, current-player outcome leakage, or named-player tuning;
- freeze candidate definitions/metrics before inspecting current-player rank effects where feasible;
- distinguish Forecast-model accuracy from Value-model economic usefulness;
- report where the historical record is insufficient to validate a claimed horizon rather than filling the gap with precision by assumption;
- preserve Value authority separation: Broad Market, League Market and Team Utility are not substitutes for FSFFL Intrinsic and may not leak into its universal coordinates.

### Required horizon-comparison diagnostics
- value and rank for each player at each supported horizon;
- rank/value deltas and crossover players across horizons;
- QB/RB/WR/TE value distributions by horizon;
- positional share of top 25 / top 50 / top 100 and top-percentile assets;
- within-position concentration, dispersion and tail behavior;
- age/experience effects and decay/persistence by position;
- uncertainty growth and sensitivity to terminal/discount assumptions;
- examples where a single blended three-year value hides materially different temporal value profiles.

### Downstream design study
Describe, without implementing, how governed horizon coordinates could later support Trade/Market/Search questions such as near-term-for-long-term exchanges, durable-value acquisition, competitive-window matching and package horizon shifts. Keep Team Utility downstream and do not collapse the term structure into an unexplained master score or fabricated acceptance probability.

### Deliverables / stop condition
Persist reproducible research artifacts, methodology, historical validation, comparative diagnostics, current-player shadows only after the model-selection discipline above, limitations, and a proposed contract. Return control only at `MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE` if evidence supports a candidate architecture, or `DIRECTIVE COMPLETE — RESEARCH` with a negative/insufficient-evidence finding. Do not implement production changes in this workstream.


### Long-horizon Intrinsic research checkpoint — historical selection pass

Branch `research/intrinsic-term-structure-20260926` has completed the first reproducible historical model-selection pass at head `895df9e3f439`; workflow `36220635330` is green. This is **not yet the terminal Research handoff**.

Current empirical checkpoint:
- frozen long-horizon candidate selected: `two_part_state`;
- untouched holdout gate passed;
- Y4 vs Y3-carry: MAE improves 10.5%, RMSE 2.7%, Spearman +0.098;
- Y5 vs Y3-carry: MAE improves 16.8%, RMSE 1.7%, Spearman +0.088;
- historical Shapley bridge correlates 0.862 (2021) and 0.881 (2022) with the current I1-Shapley proxy coordinate;
- terminal predictive ordering remains measurable through Y6–Y8 but weakens with horizon (Spearman approximately 0.419, 0.386, 0.346 respectively);
- uncertainty is defined from OOT residual RMSE by horizon/position and must use a monotone non-decreasing envelope;
- no current named-player ranks were inspected before historical candidate selection was frozen.

Generated diagnostics include Forecast/value horizon metrics, uncertainty by horizon, historical crossovers, position distributions, discount sensitivity, and Shapley bridge validation. Research must still complete the directive's post-selection work, including current-player shadows/rank movement and the final architecture recommendation/limitations, then persist a durable Management-gate handoff. No production Intrinsic change is authorized.


### Management deliverable requirement — plain-language long-horizon report

At the eventual `MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE`, Research must provide a plain-language Management report in addition to reproducible technical artifacts. The preferred user-facing deliverable is a PDF, with a concise executive summary and technical appendix.

The report must explain, without assuming modeling expertise:
- what the current three-year Intrinsic does today;
- what candidate longer-horizon structures were tested and why;
- what the evidence says about Y4/Y5 versus terminal/career value;
- where predictive signal remains useful and where uncertainty becomes too large for precise claims;
- how player values/ranks change by horizon, with representative risers/fallers and crossover examples;
- how QB/RB/WR/TE distributions change by horizon, including top-25/top-50/top-100 share, concentration and age effects;
- what discount/terminal assumptions matter materially;
- what Research recommends, what it does not recommend, and why;
- how horizon-specific Intrinsic could later change Trade/Market/Search behavior without creating a hidden master score;
- the exact Management decisions required before any implementation begins.

Include clear charts/tables for horizon rank movement, positional distributions, uncertainty by horizon and at least a few representative player value curves. Keep the production three-year coordinate unchanged until Management explicitly decides otherwise.

Research should continue beyond the completed historical model-selection pass through current-player post-selection shadows, position/ranking interpretation and this Management-ready report. Do not return control merely because the workflow is green.


### Long-horizon Intrinsic Research closeout — 2026-09-26

**State: MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE**

Research completed the full bounded term-structure directive without changing production Intrinsic.

Durable handoff:
- `artifacts/research/intrinsic_term_structure_20260926/RESEARCH_CLOSEOUT.md`
- `artifacts/research/intrinsic_term_structure_20260926/PROPOSED_TERM_STRUCTURE_CONTRACT.md`
- `artifacts/research/intrinsic_term_structure_20260926/CURRENT_DIAGNOSTICS.md`
- `artifacts/research/intrinsic_term_structure_20260926/REPRODUCIBILITY.md`
- `artifacts/research/intrinsic_term_structure_20260926/CURRENT_SHADOW_SUMMARY.json`

Historical result:
- frozen selected extension: `two_part_state`;
- untouched Y4 OOT: MAE improves **10.5%**, RMSE **2.7%**, Spearman **+0.098** versus Y3 carry;
- untouched Y5 OOT: MAE improves **16.8%**, RMSE **1.7%**, Spearman **+0.088**;
- Y6/Y7/Y8 ordering remains non-random but weakens (Spearman ~**0.419 / 0.386 / 0.346**);
- QB Y4/Y5 rank signal improves but magnitude RMSE remains worse than Y3 carry, so QB is an explicit future H5 gate.

Post-selection 2026 shadow:
- 335 players;
- H3 shadow vs persisted production H3 Spearman **0.99654**;
- H3→H5 median absolute rank move **7**, p90 **19**;
- 36.1% move at least 10 ranks and 9.3% at least 20;
- H3→H8 diagnostic median **12**, p90 **30**;
- young QB/WR/TE cohorts generally gain relative rank with horizon while aging RB/WR/TE generally lose rank;
- current top-25 composition changes from H3 **88% QB / 8% RB / 4% WR** to H5 **76% / 8% / 16%**.

Uncertainty remains large. H5 OOT residual floors are approximately QB **101.1**, RB **52.4**, WR **35.4**, TE **30.4** fantasy points and exceed current mean expected H5 production for every position. Raw later-horizon RMSE can fall because more players realize zero; Research therefore retains a monotone uncertainty floor and does not interpret lower raw Y8 RMSE as higher certainty.

Discount sensitivity shows ranking is relatively stable across 0.70/0.85/0.95 but cardinal magnitude/error is sensitive. Research does not claim a newly optimized H5 discount.

Research recommendation:
`H1 near-term | H3 governed | H5 challenger | terminal/career band`.

- H3 remains current production authority unchanged.
- H5 is empirically supported as a separate challenger horizon, not as a replacement master score.
- exact Y6-Y8/career cardinal value is not supported.
- terminal/career should next be modeled as a coarse persistence/state band with explicit uncertainty.
- no hidden blended master score, market anchor, youth bonus, QB premium or Team Utility input is authorized.

Management decisions are enumerated in the closeout. No production implementation is authorized by this Research result.

Historical workflow: `36220635330`.  
Current-shadow workflow: `36241799792`.

**MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE**


### Superseded presentation checkpoint — prior H5-centered study

The earlier H5-centered Management gate required a plain-language PDF before presentation closeout. That checkpoint is superseded by the reopened comparative Y4+ directive. The comparative study is now complete, and its updated plain-language Management PDF was produced after final model-family selection. The durable authority remains the repository artifacts and canonical gate below.


## Management continuation — comparative Y4+ model-family research
**State: MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**

The prior term-structure study established that post-H3 signal exists, but Management is not accepting Y5 as an assumed breakpoint or two_part_state as the final post-H3 model. Research is reopened for a bounded comparative model-selection phase covering Y4 onward, while production H3 remains unchanged.

Research must evaluate Y4, Y5, Y6, Y7 and Y8 separately and cumulatively where defensible, and determine empirically whether one model family should serve all post-H3 horizons or whether different model families are justified by position and/or horizon.

At minimum, compare the current two_part_state benchmark against purpose-built survival/hazard, multi-state career or role-transition, conditional-production, and other transparent/statistically defensible challengers. A flexible ML challenger may be included only with strict point-in-time chronology, leakage controls, calibration, interpretability diagnostics and complexity penalties.

Do not preselect horizon breakpoints. Do not preassign model families to timeframes. Candidate definitions, model-selection criteria, and any proposed position/horizon routing rules must be frozen before current-player inspection.

At each position × horizon cell, compare candidates on annual production accuracy where cardinal prediction is meaningful, rank/order signal, survival/relevance calibration, state-transition calibration where modeled, economic/Intrinsic bridge usefulness, uncertainty calibration, held-out-season stability, sparse-cell sensitivity, and complexity/robustness versus simpler baselines.

Production H3 remains the governed authority. New model families may be benchmarked on Y1-Y3, but no H3 replacement is authorized. If a challenger materially outperforms H3 on the existing horizon under comparable validation, return that as a separate Management decision.

Longer-horizon coordinates may ultimately be additional decision lenses rather than replacements: users may inspect different horizons according to the decision or franchise timeline. Team Utility remains downstream and cannot rewrite universal Intrinsic.

Deliverables: comparative model matrix by position × horizon, empirical breakpoint/routing analysis, calibration and uncertainty diagnostics, post-selection current-player shadows, and an updated plain-language Management PDF. Return at MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE or DIRECTIVE COMPLETE — RESEARCH with insufficient evidence. No production implementation.

### Comparative Y4+ execution checkpoint — current branch evidence
**State: MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**

Current comparative branch:
`research/intrinsic-y4plus-model-family-20260926`.

The historical six-family comparison and the current comparative-shadow workflow have both completed successfully. The historical selection is frozen before any new named-player routing changes.

Current evidence:
- no empirically defensible position/horizon breakpoint is promoted;
- `two_part_state` remains the robust annual cardinal research family across QB/RB/WR/TE and Y4–Y8;
- across the 20 position × horizon holdout cells, it owns the strongest overall RMSE/survival/tail profile even though `direct_ridge` often lowers MAE by shrinking the upper production tail;
- the development-routed architecture does not establish a superior cardinal model: paired holdout testing shows its later-horizon MAE gains come with materially worse squared error;
- `survival_hazard` remains a useful QB/persistence model-risk challenger but has not earned a separate annual-cardinal route;
- `career_state_transition` remains more promising as a terminal/career state lens than as an annual cardinal points model;
- production H3 remains unchanged and is not being re-litigated by this Y4+ study.

Do not return merely because the current-shadow workflow is green. Continue through:
1. comparative current-player horizon/rank effects and representative crossovers;
2. position-distribution and age/experience interpretation under the frozen selection;
3. uncertainty/calibration and what the challenger families teach us about terminal/career representation;
4. a clear conclusion on whether any dynamic routing is justified (currently: no);
5. the updated accessible **plain-language Management PDF**, including what changed relative to the earlier H5-centered study and the exact Management decisions required.

Stop only at `MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE` or `DIRECTIVE COMPLETE — RESEARCH` with an evidence-supported negative finding. No production implementation is authorized.


### Comparative Y4+ final Research closeout — 2026-09-26

**State: MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**

Management's reopened model-family study is complete.

Durable Research handoff:
- `artifacts/research/intrinsic_y4plus_model_family_20260926/FINAL_CLOSEOUT.md`
- `artifacts/research/intrinsic_y4plus_model_family_20260926/CURRENT_COMPARATIVE_DIAGNOSTICS.md`
- `artifacts/research/intrinsic_y4plus_model_family_20260926/PROPOSED_LONG_HORIZON_CONTRACT.md`
- `artifacts/research/intrinsic_y4plus_model_family_20260926/REPRODUCIBILITY.md`

Historical comparative result:
- six families compared chronologically across QB/RB/WR/TE × Y4-Y8;
- `two_part_state` wins RMSE in **14/20** cells and survival Brier in **14/20**;
- `direct_ridge` wins MAE in **17/20** but RMSE and top-decile tail RMSE in **0/20**, demonstrating central-error improvement through economically material upper-tail compression;
- the development-routed architecture is **not** promoted: at Y6-Y8 it lowers paired MAE but significantly worsens paired MSE, and at Y4-Y5 it does not establish a broad gain;
- `survival_hazard` remains a useful QB/persistence model-risk challenger but does not earn a separate annual-cardinal route;
- `career_state_transition` is more promising as a terminal/persistence-state lens than as annual cardinal expected points.

Final annual Y4-Y8 Research family:
**`two_part_state` for every position and tested horizon.**

Promoted model-family breakpoint:
**none**.

Current 335-player comparative shadows:
- H3 research shadow vs persisted production H3 Spearman **0.99654**;
- primary vs rejected routed sensitivity Spearman declines only from **0.9995 at H4** to **0.9947 at H8**, but tail rank differences widen materially;
- H3→H4/H5/H6/H7/H8 median absolute rank movement = **4 / 7 / 10 / 11 / 12**;
- no current-player discontinuity establishes Y5 as a model breakpoint;
- longer horizons gradually shift top-end composition away from RB toward WR while QB remains dominant;
- young QB/WR/TE cohorts generally gain relative standing while aging RB/WR/TE lose standing, without manual age/youth premiums.

Precision:
- the retained family remains the best robust annual-cardinal challenger, but annual uncertainty is large relative to expected magnitude and rank signal declines continuously;
- this prevents interpreting “one family across Y4-Y8” as “equal precision across Y4-Y8”;
- terminal/career state/persistence remains a separate semantic research opportunity.

Production H3 is preserved unchanged. No H1-Y3 replacement claim is made because the post-H3 challengers use governed Y1-Y3 Forecasts as input features.

Updated Management PDF is the human-readable gate deliverable.

Question: **Is another authorized Research action available now that materially advances the directive without Management choosing the next architecture?**

Answer: **No.**

**MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**
