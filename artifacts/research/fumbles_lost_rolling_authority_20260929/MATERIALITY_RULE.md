# Supplemental Scoring Coordinate Materiality Contract

Date: 2026-09-29  
Status: **SUPPORTED — GENERAL DOWNSTREAM AUTHORITY RULE**

## Problem

A missing low-impact scoring coordinate must remain visibly missing. It must not be silently replaced with zero or relabeled fully covered.

But “missing” and “material enough to invalidate the entire downstream consumer” are different questions.

## General rule

A supplemental scoring coordinate may be classified:

`NON_MATERIAL_PARTIAL`

for a specific downstream fantasy-point consumer only when:

1. the omitted coordinate is explicitly preserved in provenance;
2. the scoring coefficient/sign is known;
3. coordinate-specific Research supplies a finite conservative 90% plausible score-impact bound;
4. the supported fantasy-point subtotal already has non-zero governed uncertainty;
5. every subject that can enter that downstream consumer satisfies:

`impact_bound_90 <= 0.10 * (1.645 * supported_fantasy_point_stddev)`.

If any simulation-relevant subject fails, the consumer remains blocked.

If the supported fantasy-point uncertainty is missing or zero, the gate fails closed.

Taxi/IR/non-consumed subject scoping remains governed by the existing consumer rules.

## Why 10%

This threshold was frozen before rolling results/current-player application.

It treats the omitted coordinate as a nuisance effect only when its conservative one-sided 90% score scale is at most one tenth of the already acknowledged 90% fantasy-point uncertainty half-width.

On a centered standard-deviation scale, 10% corresponds to roughly 1% additional variance under independence. The actual gate is stronger because the numerator includes both location and uncertainty and therefore does not rely on independence to describe the omitted effect's plausible magnitude.

## FUMBLES_LOST bound

For position `p` and cutoff `c`:

`event_bound_90 = max(empirical OOT p99 actual season-equivalent lost fumbles, position_reference_mean + 1.645 * rolling_position_floor)`.

For scoring weight `s`:

`impact_bound_90 = abs(s) * event_bound_90`.

The position reference is a **materiality bound only**. It is not inserted as a player Forecast when player-level authority is unavailable.

## FSFFL current Week-3 example

FSFFL scores a lost fumble at **-1 point**.

At cutoff Week 3, the conservative score-impact bounds are:
- QB: **7.286 points**;
- RB: **3.643**;
- WR: **1.931**;
- TE: **2.429**.

Therefore a missing Week-3 FUMBLES_LOST coordinate is non-material for a subject when the supported fantasy-point standard deviation is at least:
- QB: **44.29 FP**;
- RB: **22.15 FP**;
- WR: **11.74 FP**;
- TE: **14.76 FP**.

These are thresholds, not named-player conclusions. Implementation evaluates them against the actual governed subtotal uncertainty at runtime.

## Required authority semantics when the gate passes

The system must still say:
- Forecast scoring coverage is partial/degraded;
- `fum_lost` is omitted;
- the omission's impact bound is known;
- downstream continuation is allowed because the omission is certified non-material for that consumer.

The system must **not**:
- create a zero-valued FUMBLES_LOST Forecast row;
- report full scoring coverage;
- delete the omission from diagnostics;
- use the rule when the coordinate has no governed impact bound.

## Simulation and Intrinsic

Simulation:
- may proceed when every simulation-relevant subject passes this gate;
- must retain a non-material-partial authority annotation.

Current Intrinsic:
- Shapley/economic mathematics do not change;
- if the current-season fantasy-point input is allowed through this gate, the Intrinsic contract must retain degraded/non-material-partial input provenance rather than claiming a fully complete Y1 Forecast.

This is an authority/completeness rule, not a new Intrinsic value formula.
