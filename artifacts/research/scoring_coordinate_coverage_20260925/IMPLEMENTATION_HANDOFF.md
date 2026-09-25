# FSFFL NEXT — League-Agnostic Scoring Coverage Implementation Handoff

Date: 2026-09-25  
From: Forecast Research  
Authority: implementation-ready research contract; **no production authority change**

Companion artifacts:
- `SCORING_COORDINATE_REGISTRY.md`
- `SCORING_COORDINATE_REGISTRY.csv`
- `PLATFORM_COVERAGE_MATRIX.csv`
- `PRIMARY_SOURCE_LEDGER.md`
- `GAP_ANALYSIS.md`

## Objective

Make scoring support an explicit, governed mapping problem:

`provider raw evidence → canonical football coordinates → Forecast evidence/distributions → canonical scoring rules → league fantasy points`

without:
- moving league-specific math into Forecast;
- silently approximating missing coordinates;
- discarding provider-native fields before a future league can use them;
- making provider-native fantasy points authoritative;
- breaking accepted current-league behavior.

## Core architectural decision

Implement **two distinct registries/contracts**:

1. **Scoring Coordinate Registry**
   - canonical football/stat coordinates Forecast may estimate;
   - subject family;
   - evidence shape;
   - exact transforms;
   - historical/calibration requirements.

2. **Canonical Scoring Rule Contract**
   - how a league scores those coordinates;
   - linear coefficients, buckets, thresholds, predicates, stacking, quantization and semantic profiles.

Do not encode TE premium, milestone bonuses, or platform semantics as fake Forecast metrics.

## Proposed domain contracts

Names are recommendations, not mandated implementation names.

### ScoringCoordinateDefinition

Fields:
- `coordinate_id`;
- `family`;
- `subject_family`;
- `evidence_shape`:
  - linear total;
  - event count;
  - bucket vector;
  - per-game distribution;
  - joint distribution;
- `unit`;
- `exact_transform_ids`;
- `historical_truth_requirement`;
- `uncertainty_requirement`;
- registry version.

### CanonicalScoringRule

Fields:
- `rule_id`;
- raw platform rule reference;
- `coordinate_ids`;
- operator:
  - `LINEAR`
  - `EVENT_COUNT`
  - `BUCKET_EXCLUSIVE`
  - `BUCKET_CUMULATIVE`
  - `THRESHOLD`
  - `POSITION_MODIFIER`
  - `CONDITIONAL`;
- period: play/game/fantasy-week/season;
- coefficient/points;
- bounds/threshold;
- subject predicate;
- stacking policy;
- fractional/quantization policy;
- negative-value policy;
- semantic-profile ID;
- mapping version.

### ScoringSemanticProfile

Initial use:
- D/ST points allowed;
- D/ST yards allowed;
- team/player special-teams attribution;
- blocked-kick classification;
- defensive/special-teams TD classification.

Profiles are versioned league/scoring-layer policy. They do not belong inside provider Forecast adapters.

### CoordinateEvidence

Keep ordinary scalar observations compatible with `ForecastObservation`.

Add a generic distributional evidence type for any subject family, not only D/ST:
- coordinate ID;
- subject;
- horizon;
- period;
- probability bins / distribution parameters;
- source/provenance;
- model version.

Needed for:
- passing/rushing/receiving milestones;
- D/ST PA/YA buckets;
- IDP thresholds;
- punt-average ranges;
- future conditional rules.

### ScoringCapability

Fields:
- league/rules version;
- subject key;
- horizon;
- evaluation cutoff;
- overall:
  - FULL
  - PARTIAL
  - UNSUPPORTED;
- rule-level capability rows;
- required coordinates;
- missing coordinates;
- missing subject family;
- missing distributional evidence;
- insufficient independent sources;
- rights blockers;
- incompatible uncertainty;
- unresolved platform semantics.

**Important:** PARTIAL is diagnostic only. It must not authorize a fantasy-point total that omits active material rules.

## State / League Configuration migration

Current `ScoringRule(stat, points)` is too narrow for cross-platform semantics but is valuable raw provider state.

Recommended migration:
- preserve current raw `scoring` entries for backward compatibility and audit;
- add a compiled canonical scoring representation rather than destructively replacing raw provider keys;
- persist mapping version and platform semantic profile;
- do not retroactively rewrite historical league snapshots without provenance.

For Sleeper:
- raw numeric `scoring_settings` remains preserved;
- a compiler maps recognized Sleeper keys to canonical rules;
- unknown keys survive raw State and produce explicit UNSUPPORTED capability.

For future ESPN/Yahoo/CBS/Fantrax/MFL connectors:
- import the source platform rule as evidence;
- compile to canonical rules;
- retain source rule identity and raw configuration.

## Subject-family migration

### Stage A
No State enum change required for:
- QB/RB/WR/TE;
- K;
- D/ST.

### Stage B — IDP
Add explicit defensive-player positions/slots, likely:
- DL;
- DE/DT if provider distinguishes;
- LB;
- DB;
- CB/S if provider distinguishes;
- IDP FLEX.

Do not reuse `DST_*` team-unit metrics for IDP.

Provider position aliases need a canonical mapping with provenance.

### Stage C — specialized subjects
Punter/head-coach/team-offense support is lower priority. The rule compiler must still report these as recognized-but-unsupported subject families rather than dropping them.

## Forecast coordinate expansion

### P0 direct event coordinates

Replace existing provisional scoring inference where direct evidence can be acquired:
- PASS_2PT;
- RUSH_2PT;
- REC_2PT;
- PLAYER_RETURN_TD;
- FUMBLE_RECOVERY_TD.

Do not remove an accepted prior until direct-source coverage and replay tests prove the replacement.

### P1 scalar coordinates

Add:
- PASS_ATTEMPTS;
- PASS_COMPLETIONS;
- PASS_INCOMPLETIONS;
- PASS_SACKS_TAKEN;
- PASS_FIRST_DOWNS;
- PASS_PICK_SIX_THROWN;
- RUSH_ATTEMPTS;
- RUSH_FIRST_DOWNS;
- RECEIVING_TARGETS;
- REC_FIRST_DOWNS;
- FUMBLES;
- player kick/punt return yards;
- D/ST linear points/yards allowed where a semantic profile makes the coordinate meaningful.

Exact transforms must be registered:
- incompletions = attempts − completions;
- misses = attempts − makes;
only under same-subject/same-period/same-horizon completeness.

### P0/P1 distributional coordinates

Add generic per-game distribution support for:
- passing yard milestones;
- rushing yard milestones;
- receiving yard milestones;
- completion/carry thresholds;
- D/ST PA/YA;
- combined rush+rec as joint evidence.

Season expected totals cannot substitute.

### P1 IDP coordinates

Add distinct individual-player defensive metrics:
- tackle / solo / assist;
- sack / sack yards;
- TFL / QB hit / PD;
- INT / return yards / TD;
- FF / FR / return yards / TD;
- safety;
- blocked kick;
- defensive two-point return if platform uses it.

## Provider acquisition contract

### Preserve first, normalize second

Current `CurrentProjectionRow.stats` is already structurally generic, but provider adapters populate a narrow subset.

Change acquisition so a permitted provider capture can retain:
- original provider field name;
- numeric value;
- subject identity;
- horizon;
- captured/effective timestamps;
- source version;
- content identity;
- rights class.

Then map to registry coordinates.

Provider fields that are not yet mapped remain retained with `canonical_coordinate_id = null`.

### High-value fields to stop discarding

At minimum, when provider/source rights allow:
- pass attempts/completions/sacks;
- rush attempts;
- targets;
- 2PT;
- fumbles;
- return yards/TD;
- first downs;
- K native distance fields;
- D/ST PA/YA and event detail;
- IDP fields.

SportsDataIO's documented schema demonstrates that richer commercial feeds can supply many of these coordinates. That is evidence for the preservation architecture, not provider authorization.

## Scoring compilation and evaluation

Recommended flow:

1. **Import raw league rule.**
2. **Compile** it to canonical coordinate requirements + rule semantics.
3. **Resolve exact transforms** from registry metadata.
4. **Evaluate coordinate evidence** by subject/horizon/cutoff.
5. **Evaluate independent-source and rights gates.**
6. **Evaluate uncertainty compatibility.**
7. Return rule-level capability.
8. Only when every active material rule is FULL:
   - compute authoritative expected fantasy points;
   - expose simulation-grade distribution if uncertainty is valid.
9. Otherwise:
   - withhold authoritative total;
   - expose PARTIAL/UNSUPPORTED reason codes.

## Linear scoring engine migration

Do not rewrite accepted scoring all at once.

Create a compiled-rule scorer with a compatibility path:

### Compatibility lane
Current ordinary linear mappings produce identical outputs under the new compiled contract.

Golden fixtures:
- current FSFFL;
- standard PPR;
- half-PPR;
- standard non-PPR.

### Expanded lane
New canonical rules use the same evaluator only after their coordinate evidence is present.

### Nonlinear lane
Bucket/threshold/conditional rules require distributional evidence; they may not fall back to scalar means.

## Uncertainty contract

Scoring expansion must not accidentally make existing uncertainty universal.

### Linear new coordinates
A fantasy-point uncertainty model may remain valid only if:
- its historical scoring fingerprint included the added rule coordinates; or
- a governed recalibration proves compatibility.

### Position modifier
TE premium does not necessarily require a new football-stat projection, but it changes fantasy-point variance and therefore the fantasy-point scoring fingerprint.

### Nonlinear rules
Milestone/bucket rules require:
- per-game coordinate distribution;
- scoring transformation over that distribution;
- replay/validation under the exact scoring fingerprint.

### IDP
Requires separate empirical uncertainty; do not borrow D/ST team-unit or offensive-player coefficients.

## Historical replay / calibration plan

Create a canonical realized-stat mapping parallel to projection mapping.

Recommended retained unit:
`RealizedCoordinateObservation`

Fields:
- subject;
- coordinate ID;
- NFL game/week/season;
- value;
- source;
- effective/retrieved time;
- semantic profile where applicable;
- mapping version.

Use:
- generic Sleeper weekly stats where semantics are adequate;
- nflverse/PBP for event-level reconstruction;
- other governed sources as rights permit.

For threshold rules, retain weekly/game observations even if annual totals are also stored.

## Capability API contract

Recommended product/API shape:

```text
ScoringCapabilityReport
  overall_status: FULL | PARTIAL | UNSUPPORTED
  subject_family_status[]
  active_rules[]
    source_rule
    canonical_rule_id
    status
    required_coordinates[]
    available_coordinates[]
    missing_coordinates[]
    exact_transform_used?
    distribution_required?
    semantic_profile
    independent_sources
    rights_status
    uncertainty_status
    reason_codes[]
```

Presentation may summarize this, but may not convert PARTIAL into a green readiness state.

## Implementation stages

### Stage 0 — registry + diagnostics, zero model authority change
- add registry definitions;
- add rule/capability models;
- compile existing ordinary Sleeper scoring;
- preserve current scorer as compatibility oracle;
- add FULL/PARTIAL/UNSUPPORTED diagnostics;
- no new production scoring.

Acceptance:
- current FSFFL and no-K/DST leagues are byte/numerically regression-clean;
- unknown rule is explicit, never dropped.

### Stage 1 — provider raw-superset preservation
- retain provider-native numeric fields before canonical reduction;
- mapping registry version;
- no new field becomes authoritative merely because retained.

Acceptance:
- ignored attempts/targets survive capture;
- downstream current scoring remains unchanged.

### Stage 2 — P0 direct events + predicates
- direct 2PT;
- return TD;
- fumble-recovery TD;
- position reception modifier/TE premium;
- scoring-policy metadata.

Acceptance:
- replace priors only where direct evidence satisfies existing authority requirements;
- TE premium uses base reception coordinate + predicate.

### Stage 3 — P0 nonlinear milestone distributions
- generic game-distribution evidence;
- pass/rush/receive milestone scorer;
- explicit stacking;
- DraftKings-style and Sleeper/ESPN/NFL fixtures.

Acceptance:
- `score(E[X])` shortcut prohibited;
- distribution integration matches deterministic fixtures.

### Stage 4 — P1 scalar breadth
- attempts/completions/incompletions/sacks;
- carries;
- first downs;
- targets;
- fumbles;
- return yards;
- linear D/ST PA/YA.

Acceptance:
- source completeness/independence enforced per coordinate.

### Stage 5 — IDP
- State positions/slots;
- player defensive coordinate family;
- provider acquisition;
- realized history;
- empirical uncertainty;
- lineup/Value/Simulation downstream work in their respective authority domains.

### Stage 6 — advanced P2/P3
- long-play/reception-distance event buckets;
- IDP threshold distributions;
- punter;
- head coach;
- arbitrary conditional rule AST.

P3 may remain capability-only until product priority justifies Forecast models.

## Deterministic acceptance suite

Implementation must preserve/implement the fixtures defined in `GAP_ANALYSIS.md`, especially:

- current FSFFL regression;
- Yahoo default half-PPR;
- ESPN volume scoring;
- Sleeper TE premium;
- PPFD;
- DraftKings milestone bonuses;
- nested/exclusive bonus stacking;
- fractional-off quantization;
- negative-yardage policy;
- D/ST semantic profile differences;
- IDP subject isolation;
- team vs player special teams;
- MFL conditional fail-closed;
- provider raw-superset retention;
- unknown-rule fail-closed.

## Required invariants

1. Forecast never reads a league scoring coefficient to decide what raw provider fields to preserve.
2. Provider-native fantasy points never substitute for raw coordinate evidence.
3. A platform-specific rule cannot bypass canonical compilation.
4. Exact transforms are versioned and declared.
5. Nonlinear scoring never uses an aggregate mean as a bucket probability.
6. Position modifiers stay in scoring, not Forecast.
7. D/ST and IDP subjects remain distinct.
8. Unknown rules survive import and fail closed.
9. PARTIAL capability never yields an authoritative incomplete total.
10. Existing production authority is unchanged until an implementation directive separately promotes validated paths.

## Management-facing product definition

After Stage 0, FSFFL can truthfully answer:
- which scoring rules it understands;
- which it can forecast now;
- which are missing raw inputs;
- which need distributions;
- which need a new subject family;
- why a league or player is PARTIAL/UNSUPPORTED.

That capability visibility should precede any marketing/product claim that FSFFL is "league agnostic."

## Recommended next authority boundary

Research is complete when this handoff is accepted.

Implementation should begin with **Stage 0 + Stage 1 only** as a bounded, zero-authority-change work package. Do not combine IDP, nonlinear milestones, all provider expansion, and new production model authority into one PR.

Stages 2+ require their own evidence and acceptance gates.
