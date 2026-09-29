# Supplemental Scoring Coordinate Materiality Contract

Date: 2026-09-29  
Status: **SUPPORTED — POPULATION-BOUNDED NON_MATERIAL_PARTIAL AUTHORITY**  
Supersedes: the original primary-population-only FUMBLES_LOST materiality bound.

## Purpose

A missing low-impact scoring coordinate must remain visibly missing. It must not be silently replaced with zero or relabeled fully covered.

But “missing” and “material enough to invalidate the entire downstream consumer” are different questions.

## General downstream rule

A supplemental scoring coordinate may be classified:

`NON_MATERIAL_PARTIAL`

for a specific downstream fantasy-point consumer only when all of the following hold:

1. the omitted coordinate remains explicit in provenance/diagnostics;
2. the scoring coefficient/sign is known;
3. coordinate-specific Research supplies a finite conservative impact bound for the **eligible missing-evidence population**;
4. the supported fantasy-point subtotal already has non-zero governed uncertainty;
5. the subject/population is eligible for fallback at that position/cutoff;
6. every subject that can enter that downstream consumer satisfies:

`impact_bound_90 <= 0.10 * (1.645 * supported_fantasy_point_stddev)`.

If any relevant subject is ineligible or fails the inequality, that consumer remains blocked.

Taxi/IR/non-consumed scoping remains governed by the existing consumer contract.

## Why 10%

The 10% threshold was frozen before current-player application.

It treats the omitted coordinate as nuisance-scale only when its conservative score-impact scale is at most one tenth of the already acknowledged 90% fantasy-point uncertainty half-width.

The threshold is not tuned to make the current private-beta acceptance pass.

## Corrected FUMBLES_LOST bound

The original bound used a primary validation population that excluded cold starts. PR #297 correctly identified that this was insufficient for a fallback that could encounter cold-start/identity-light subjects.

The corrected production bound for target season `Y`, position `p`, cutoff `c` is:

`event_bound_90(Y,p,c) = max(previous_frozen_bound, max historical season-equivalent target over all governed player-seasons before Y at p,c)`.

For 2026:
- history is governed exact 2021-2025 data;
- the position-wide historical maximum is **not conditioned on player identity or evidence tier**;
- at Week 2-17 the corrected bound can only widen the original bound, never narrow it;
- Week 0-1 receive bounds but **no point-estimate authority**.

For league scoring coefficient `s`:

`impact_bound_90 = abs(s) * event_bound_90`.

The historical maximum is used because the fallback population can be the least-informed population. It is intentionally more conservative than the original p99-based primary-population bound.

This is an impact bound only. It is never substituted as a player Forecast mean.

## Population validation and eligibility

Historical pseudo-rollover validation used held-out 2023-2025 seasons and evaluated the position-wide prior-history bound separately for:
- history + current evidence;
- history only;
- current only;
- cold start.

The acceptance floor is 90% empirical coverage for every population/cutoff that remains fallback-eligible.

One unsupported cell was found:
- QB cold-start at completed Week 13: **8/9 = 88.9%** coverage.

Later QB cold-start samples are even smaller. Rather than increase the bound after seeing this failure, the authority contract conservatively restricts the entire late-season suffix:

- **QB cold-start fallback: ineligible Weeks 13-17**;
- **QB identity-light fallback: ineligible Weeks 13-17**;
- these cases fail closed when FUMBLES_LOST point authority is unavailable.

All other observed position/cutoff/tier combinations pass the frozen 90% coverage gate.

### Identity-light

There is no directly observed historical “mapping failed” tier.

Identity-light may therefore use fallback only when:
1. canonical offensive position is known and non-conflicting;
2. the matching position/cutoff cold-start population is fallback-eligible;
3. the runtime materiality inequality passes.

Unknown or conflicting position fails closed.

This does not fabricate historical identity-light outcomes; it uses the intentionally tier-agnostic position-wide bound and a stricter eligibility mapping.

## 2026 Week-3 corrected example

FSFFL scores lost fumbles at **-1 point**.

Corrected all-population Week-3 event/score bounds:
- QB: **10.9286**;
- RB: **4.8571**;
- WR: **3.6429**;
- TE: **2.4286**.

Minimum supported fantasy-point standard deviations required for non-material classification:
- QB: **66.44 FP**;
- RB: **29.53 FP**;
- WR: **22.15 FP**;
- TE: **14.76 FP**.

These replace the earlier primary-population-only Week-3 thresholds.

Implementation evaluates the actual governed subtotal uncertainty for each relevant subject. Research does not assert that a named player passes.

## Week 0 and Week 1

No first-party FUMBLES_LOST point estimate is authorized at completed Week 0 or Week 1.

Fallback may still be allowed under the same explicit omission/materiality rule.

2026 conservative bounds:

| Cutoff | QB | RB | WR | TE |
| --- | ---: | ---: | ---: | ---: |
| Week 0 | 9.0000 | 4.0000 | 3.0000 | 3.0000 |
| Week 1 | 9.5625 | 4.2500 | 3.1875 | 3.1875 |

Historical population validation found no eligible Week-0 or Week-1 population failure.

## Required authority semantics when the gate passes

The system must still report:
- Forecast scoring coverage is partial/degraded;
- `fum_lost` is omitted;
- the omission impact bound;
- the population eligibility decision;
- downstream continuation is allowed only as `NON_MATERIAL_PARTIAL`.

The system must **not**:
- create a zero-valued FUMBLES_LOST Forecast row;
- claim COMPLETE/FULL coverage;
- delete the omission from diagnostics;
- apply a bound to an ineligible population;
- use the materiality bound as a Forecast mean.

## Simulation and Intrinsic

Simulation may proceed only when every Simulation-relevant partial subject is both:
- fallback-eligible; and
- below the materiality threshold.

Otherwise the existing blocker remains.

Current Intrinsic mathematics do not change. If its current-season input is allowed through this authority rule, provenance must retain the degraded/non-material-partial state rather than claiming a fully complete Y1 Forecast.

This is an authority/completeness rule, not a new Intrinsic formula.

## Annual rollover

For 2027+ the position-wide fallback bound is refreshed/frozen annually:
- retain the prior frozen bound;
- add the newly completed season;
- take the maximum historical position-wide season-equivalent target;
- revalidate population coverage;
- restrict a failing population rather than tuning the bound after failure.

See `ANNUAL_ROLLOVER_CONTRACT.md`.
