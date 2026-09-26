# FSFFL NEXT — Single-Source Auxiliary Authority Recommendation

Date: 2026-09-25  
State: **RESEARCH RECOMMENDATION — REQUIRES MANAGEMENT DECISION**

## Recommendation

Research supports a **generalized single-source auxiliary authority tier in principle**, with strict quantitative materiality and source-quality gates.

Research does **not** support promoting any current coordinate/source pair merely because one source exists.

The core finding is conjunctive:

> One-source authority can be defensible only when the **incremental unsupported scoring contribution is empirically bounded** *and* the specific source has independently demonstrated that using it is materially better than omission without creating unacceptable error relative to multi-source evidence.

Low event frequency is neither necessary nor sufficient.

## Proposed authority classes

### 1. CORE_MULTI_SOURCE
Default for:
- material volume statistics;
- touchdowns/receptions/yards;
- FUMBLES_LOST at common scoring;
- FG misses in the tested profile;
- common two-point conversions;
- D/ST forced fumbles / recoveries;
- D/ST special-teams TD;
- D/ST blocked kicks at the tested profile;
- nonlinear D/ST PA/YA distributions;
- any coordinate failing auxiliary thresholds.

Authority remains the normal governed multi-source rule.

### 2. AUXILIARY_SINGLE_SOURCE_CANDIDATE
A coordinate/scoring-profile pair may enter this class only after passing **all** materiality thresholds below.

This is a *candidate class*, not production source approval.

### 3. TAIL_UNSUPPORTED
For coordinates that are extremely rare but have high event severity and/or no validated forecast source.

Examples from this study:
- player special-teams TD;
- offensive fumble-recovery TD.

Correct behavior remains explicit omission/PARTIAL unless evidence later earns another tier.

## Materiality gate

Materiality is evaluated on the **incremental scoring contribution actually missing from otherwise governed evidence**, not necessarily the whole raw statistic.

This matters for 60+ kicking:
- if 50+ makes already have governed base authority at five points;
- the unsupported Hodor coordinate is the **+1 incremental point for each 60+ make**;
- materiality is measured on that +1 residual, not all six points.

A candidate must pass all of these league/scoring-profile-specific thresholds:

| Metric | Proposed maximum |
|---|---:|
| P95 absolute seasonal contribution | **3.0 fantasy points** |
| P99 absolute seasonal contribution | **5.0 points** |
| Maximum observed seasonal contribution | **6.0 points** |
| P95 share of subject total points | **3.0%** |
| P95 player/position rank displacement | **2 places** |
| Maximum observed single-event incremental value | **2.0 points** |
| Maximum team-week score delta in sensitivity fixture | **2.0 points** |
| Lineup-selection change rate | **2.0%** |
| 50k max expected-wins delta | **0.05 wins** |
| 50k max playoff-probability delta | **0.25 percentage points** |
| 50k max championship-probability delta | **0.10 percentage points** |

Additionally:
- nonlinear bucket/joint-distribution coordinates are ineligible for this scalar auxiliary tier;
- a major volume coordinate remains CORE even if one unusual league assigns it a tiny coefficient;
- Management may lower these caps later, but implementation must not loosen them without a new governed evidence decision.

These thresholds are intentionally multi-dimensional. No single percentile or frequency can make a coordinate auxiliary.

## Source-quality gate

Even after materiality passes, a **specific provider-coordinate pair** must pass all of:

1. **Exact semantics**
   - native exact coordinate, or exact algebraic transform from same-subject/same-period/same-horizon complete evidence;
   - no heuristic split, neighboring-stat substitution, or absent=zero.

2. **Rights**
   - explicit production right for acquisition, storage, internal processing, derived outputs, and the intended beta/commercial context.

3. **Direct governed source**
   - opaque consensus/aggregate sources do not qualify for one-source authority.

4. **PIT provenance**
   - immutable acquisition time, effective time when available, endpoint/source version, content identity/hash where permitted, and revision history.

5. **Coverage**
   - >=95% of the eligible target subject population in each validation cohort;
   - no systematic missingness concentrated in high-value subjects;
   - automatic demotion on row/provider health failure.

6. **Historical validation**
   - at least **50 subject-seasons across >=2 distinct seasons**, or an equivalently predeclared two-cohort PIT validation with a held-out cohort;
   - one winning season is insufficient.

7. **Improvement over omission**
   - in every required validation cohort:
     - single-source MAE <= 90% of omission MAE; and
     - single-source RMSE <= 90% of omission RMSE.

8. **Bounded cost vs multi-source evidence**
   - where >=2 independent historical sources overlap:
     - single-source MAE <= 110% of multi-source MAE; and
     - single-source RMSE <= 110% of multi-source RMSE.

9. **Bias**
   - absolute mean scoring bias <= min(0.5 points/season, 25% of the coordinate's P95 absolute seasonal contribution).

10. **Source-specific uncertainty**
    - non-zero empirical residual uncertainty for the exact source/coordinate/scoring transform;
    - provider disagreement cannot exist with one source, so it cannot be the uncertainty basis;
    - uncertainty must include at least the promoted source-specific empirical error floor.

11. **Stability**
    - no unresolved year/horizon drift;
    - no material revision instability;
    - no source-health incident that invalidates the validated behavior.

## Failure behavior

A certified auxiliary coordinate must automatically demote to PARTIAL/UNSUPPORTED when:
- source is unavailable;
- row is stale/quarantined;
- semantic shape changes;
- rights expire;
- validated source version materially changes;
- coverage falls below gate;
- scoring coefficient/profile changes enough that materiality no longer passes;
- empirical uncertainty becomes incompatible.

No cached prior, zero, heuristic rate, or adjacent coordinate may silently replace it.

## What the evidence says about current candidates

### K 60+ incremental point
**Materiality: PASS. Source authority: NOT YET CLEARED.**

Evidence:
- starter-relevant p95 season contribution: 1 point;
- p99: ~2.29;
- max: 3;
- no observed position-rank change;
- 50k max playoff delta: 0.040 percentage points;
- max title delta: 0.008 pp.

This is the strongest materiality case for the new tier.

But:
- retained historical provider projections collapse 50+;
- JerryGM is only a current technical exact-capability candidate;
- source-specific historical accuracy/stability and rights are not cleared.

Therefore **no production promotion**.

### K XP miss
**Materiality: PASS. Source authority: FAILS CURRENT QUALITY EVIDENCE.**

The coordinate is small enough:
- p95 season: 3 points;
- max team-week: 1;
- max playoff delta: 0.052 pp.

But 2024:
- CBS and FantasySharks single-source forecasts were worse than omission;
- ESPN improved RMSE only slightly while worsening MAE;
- multi-source mean was also worse than omission.

This is the clearest proof that low materiality cannot substitute for source quality.

### D/ST safety
**Materiality: PASS. Source authority: FAILS CURRENT QUALITY EVIDENCE.**

Downstream sensitivity is tiny, but:
- CBS forecast was effectively equivalent to omission;
- FantasySharks and the two-source mean were worse than omission.

### Defensive two-point return
**Materiality: PASS. Source authority: NOT EVALUABLE.**

Observed impact is tiny, but no qualifying direct historical PIT projection source was recovered for source-quality validation.

### FUMBLES_LOST
**Materiality: FAIL at common scoring / source quality mixed.**

At -2:
- p95 starter-season contribution: 8 points;
- 50k max playoff delta: 3.026 pp;
- max title delta: 1.576 pp.

2024 source replay:
- CBS RMSE was worse than omission;
- FantasySharks improved RMSE modestly but worsened MAE;
- multi-source mean was better than either single.

Keep multi-source/core authority.

### FG misses
**Materiality: FAIL despite good one-source replay.**

This is an important counterexample:
- ESPN single-source 2024 RMSE beat the naive multi-source mean;
- all singles greatly improved on omission;
- but coordinate impact produced a 2.312 pp max playoff delta and 1.360 pp max title delta.

Good one-source accuracy does not make a material coordinate auxiliary.

### D/ST forced fumble / fumble recovery
**Materiality: FAIL despite useful single-source forecasts.**

Some single providers beat the naive multi-source mean in 2024. The coordinates remain CORE because their seasonal and downstream effects are large.

## Why two sources remain the default

The study does not invalidate the two-source architecture.

Two-source evidence remains valuable because:
- single-source accuracy is not stable across coordinates;
- a provider can be best on one coordinate and worse than omission on another;
- independent sources expose scale/content incidents that one source cannot self-diagnose;
- production rights and source health remain independent failure modes.

The proposed tier is a narrow exception for measured low-materiality residual coordinates, not a new general Forecast rule.

## Machine-readable contract recommendation

If Management accepts the policy, Implementation should add a versioned certification record, conceptually:

`AuxiliarySingleSourceAuthorityCertification`

Fields:
- coordinate ID;
- scoring-profile fingerprint / coefficient;
- subject family;
- provider/source version;
- authority tier: `AUXILIARY_SINGLE_SOURCE`;
- materiality evidence artifact/hash;
- source-quality evidence artifact/hash;
- validation seasons/cohorts;
- omission MAE/RMSE;
- single-source MAE/RMSE/bias;
- multi-source comparator where available;
- downstream sensitivity metrics;
- empirical uncertainty model/version;
- rights evidence reference;
- certified_at;
- expires_at / review trigger;
- health/coverage requirements.

Scored output should expose the auxiliary source explicitly in provenance.

## Downstream rule

A fantasy-point total may be called complete under this tier only if:
- every core/material coordinate has normal authority;
- every auxiliary single-source coordinate has an active certification;
- all certified auxiliary coordinates contribute target-compatible uncertainty;
- no active rule is silently omitted.

Suggested capability label:
`FULL_WITH_CERTIFIED_AUXILIARY_SINGLE_SOURCE`

This should remain distinguishable from ordinary `FULL_MULTI_SOURCE` for audit and product explanation.

Simulation may consume it only if the certification includes valid source-specific uncertainty and the target scoring profile still passes materiality.

## Current production implication

**None.**

No source/coordinate is promoted by this Research package.

At present:
- K 60+ incremental: materiality passes, source gate unresolved;
- XP miss: materiality passes, source quality fails;
- D/ST safety: materiality passes, source quality fails;
- defensive two-point return: materiality passes, source quality unavailable.

The existing two-independent-source rule remains production authority until Management decides otherwise and a later implementation directive creates the certification mechanism.

