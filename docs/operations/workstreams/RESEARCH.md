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
**State: ACTIVE — BOUNDED MATERIALITY / SOURCE-AUTHORITY STUDY**

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
