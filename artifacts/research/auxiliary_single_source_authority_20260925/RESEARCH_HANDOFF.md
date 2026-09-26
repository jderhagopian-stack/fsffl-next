# FSFFL NEXT — Bounded Auxiliary Single-Source Authority Research Handoff

Date: 2026-09-25  
Terminal state: **MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION**

## Directive result

Research completed the Management-authorized bounded auxiliary single-source study.

Required durable package:
- `AUXILIARY_COORDINATE_MATERIALITY.csv`
- `SINGLE_SOURCE_QUALITY_LEDGER.csv`
- `SINGLE_VS_MULTI_SOURCE_REPLAY.csv`
- `DOWNSTREAM_SENSITIVITY.md`
- `AUTHORITY_TIER_RECOMMENDATION.md`
- this `RESEARCH_HANDOFF.md`

No production Forecast, Simulation, Value, Decision, Search, provider, or scoring authority was changed.

## Decision summary

The evidence supports a **generalized auxiliary single-source authority tier in principle**, but only as a strict, certified exception to the normal two-source rule.

It does **not** support enabling any current source automatically.

The research evidence establishes four important facts:

1. **A genuinely bounded materiality class exists.**  
   The clearest example is the +1 incremental scoring contribution for 60+ field goals above an already-governed 50+ base.

2. **Low materiality is not enough.**  
   2024 K XP-miss and D/ST safety forecasts were often no better—or worse—than omission.

3. **Good single-source accuracy is not enough.**  
   FG misses and D/ST turnover coordinates had strong single-source replays, but their downstream effects are too material to relax authority.

4. **Rarity is not enough.**  
   Six-point player/team special-teams events can be rare yet create large stress-case jumps.

## Research recommendation

**Accept the policy framework, but activate zero coordinates at acceptance time.**

That means Management would authorize Implementation to build the certification machinery and tests, while the existing multi-source production rule remains effective for every coordinate until a provider-coordinate certification independently passes all gates.

This avoids two bad choices:
- permanently blocking tiny residual coordinates only because a second provider is unavailable;
- or weakening the entire Forecast source standard to solve one narrow gap.

## Proposed quantitative materiality contract

A league/scoring-profile-specific incremental coordinate must satisfy all:

- p95 abs season contribution <= 3 points;
- p99 <= 5;
- max observed season <= 6;
- p95 contribution share <= 3%;
- p95 positional rank displacement <= 2;
- max single-event incremental value <= 2 points;
- max team-week sensitivity <= 2 points;
- lineup-change rate <= 2%;
- paired 50k max expected-wins delta <= 0.05;
- max playoff-probability delta <= 0.25 percentage points;
- max title-probability delta <= 0.10 percentage points;
- nonlinear distribution/joint-distribution coordinates are ineligible.

The rule applies to the **unsupported incremental contribution**, so a +1 60+ premium can be tested separately from an already-governed 5-point 50+ base.

## Proposed source-quality contract

A source must additionally satisfy all:

- exact semantics;
- explicit production rights;
- direct/non-opaque source;
- immutable PIT provenance;
- >=95% eligible-subject coverage;
- >=50 subject-seasons across >=2 historical seasons or an equivalent predeclared two-cohort/held-out validation;
- MAE and RMSE each at least 10% better than omission in every required cohort;
- where multi-source overlap exists, MAE/RMSE each no more than 10% worse than the multi-source comparator;
- absolute bias <= min(0.5 points/season, 25% of candidate p95 contribution);
- non-zero source-specific empirical residual uncertainty;
- stable source version/horizon behavior;
- automatic demotion on health/rights/coverage/semantic failure.

## Current classifications

### CORE_MULTI_SOURCE
- FUMBLES_LOST at common -1/-2 scoring;
- K FG misses;
- common 2PT conversions;
- D/ST blocked kicks in the tested +2 profile;
- D/ST ST TD;
- D/ST forced fumbles;
- D/ST fumble recoveries;
- nonlinear D/ST PA distributions;
- ordinary high-volume/TD/reception controls.

### AUXILIARY materiality candidates, source not certified
- K 60+ +1 incremental premium;
- K XP miss at -1;
- D/ST safety at +2;
- D/ST defensive two-point return at +2.

### TAIL / explicit omission unless separately governed
- player special-teams TD;
- offensive fumble-recovery TD.

## Current-source implications

### K 60+
The materiality case is strong enough for the proposed tier.

But JerryGM or any other exact 60+ source still needs:
- rights clearance;
- live source-health acceptance;
- historical/held-out source-specific accuracy;
- stability;
- empirical coordinate uncertainty.

No current 60+ authority is promoted.

### XP miss / D/ST safety
Materiality passes, but recovered 2024 source replay does not meet the quality contract. They remain under current authority.

### Defensive 2PT return
Materiality passes but source-quality evidence is insufficient. It remains unsupported/partial.

## Management decision options

### Option A — Accept the generalized tier
Authorize a bounded implementation directive for:
- certification model/registry;
- eligibility evaluator;
- provenance/rights/health hooks;
- source-specific uncertainty requirement;
- capability label `FULL_WITH_CERTIFIED_AUXILIARY_SINGLE_SOURCE`;
- fail-closed demotion;
- zero initial production certifications unless a source separately passes the evidence gate.

**Research recommendation: Option A.**

### Option B — Retain universal two-source authority
No authority-model implementation. Continue treating every missing coordinate as PARTIAL/UNSUPPORTED until two independent sources exist.

This remains defensible, but it knowingly treats empirically tiny residuals and major material coordinates identically.

### Option C — Approve only a Hodor/60+ carve-out
**Not recommended.**

It would be league-specific and would fail the directive's requirement for a generalized coordinate-based rule.

## Implementation boundaries if Option A is accepted

The first PR should implement **authority infrastructure only**, not a provider promotion:
1. certification schema;
2. materiality/source-quality evaluator;
3. scoring-profile fingerprint binding;
4. source-specific uncertainty contract;
5. capability/reporting tier;
6. automatic demotion;
7. regression fixtures proving current outputs unchanged with zero certifications.

Provider-coordinate certification should be a separate evidence-bearing action.

Do not combine a JerryGM promotion, K/DST model promotion, or Hodor readiness claim into the authority-infrastructure PR.

## Operating-protocol test

Question: **Is there another authorized Research action available now that could materially resolve the Management policy decision?**

Answer: **No.**

The required materiality, source replay, downstream sensitivity, controls, and quantitative rule have been produced. Further source-specific work would test a provider against a policy that Management has not yet accepted and would cross the current decision boundary.

**MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION**
