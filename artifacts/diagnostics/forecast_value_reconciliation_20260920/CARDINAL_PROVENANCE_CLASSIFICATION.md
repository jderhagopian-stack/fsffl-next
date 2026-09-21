# Cardinal provenance and authority classification

Date: 2026-09-20  
Classification: **B — market/reference/compatibility coordinate**

## Decision

FSFFL Cardinal Value is an authoritative **market-cardinal reference/accounting coordinate**. It is not the canonical FSFFL Intrinsic coordinate, not Broad Market percentile, not League Market Value, not Team Utility, and not a universal master player/team value.

## Why classification B is supported

### Original need

The NEXT-3 cardinal plan documented a real gap in the existing Broad Market percentile coordinate: percentile rank preserves ordering but discards economic magnitude. The plan therefore proposed a distinct cardinal score with meaningful spacing, while retaining Market Percentile as a separate relative market-position lens.

It explicitly rejected:
- market-percentile times 10,000 as a fake cardinal scale;
- mixing provider-native scales without a governed transformation;
- treating a convenient provider scale as FSFFL truth without validation;
- assuming package/additivity semantics merely because the display scale is numeric.

### Promotion evidence

The later promotion record promoted **FSFFL Cardinal Market Score** with:
- scale `fsffl-market-cardinal`;
- version `next3-v1`;
- nominal 0–10,000 axis;
- Stats Guy Fantasy dynasty values as the direct reference cohort for the active SF/non-SF league format.

The promotion record explicitly states that this coordinate is:
- a Value-layer market-price representation;
- **not intrinsic dynasty value**;
- not team-specific utility;
- not transaction price;
- not a trade grade;
- not a recommendation.

Broad Market Percentile remains separately authoritative.

### Empirical validation

The current Cardinal research workflow re-ran successfully on PR #162. Its point-in-time cross-source research shows that a monotone piecewise-quantile mapping materially outperformed simple affine/log-affine alternatives, with independent DynastyProcess evidence mapping onto the Stats Guy axis at roughly:
- holdout MAE ~237 FSFFL points;
- RMSE ~553 FSFFL points;
- ~4.5k matched holdout observations.

The user league's clean one-for-one transaction sample remains too old for point-in-time scalar validation against the retained market histories. That limitation is preserved rather than backfilled with current values.

This is adequate provenance for an authoritative **market-cardinal baseline**, but it does not transform Cardinal into intrinsic football economics.

## Current implementation mechanics

Player Cardinal:
- reference source id: `statsguy_market_values`;
- reference scale: `statsguy-dynasty-value`;
- player score preserves the format-locked provider magnitude directly;
- one coherent market context is required;
- duplicate asset rows fail closed;
- the expected SF/non-SF reference format must match.

Future picks:
- generic round-only Stats Guy values are used when exact future draft slot is not yet known;
- slot certainty is recorded explicitly;
- exact future slot is not fabricated.

Team portfolio:
- coherent player/pick Cardinal scores may be summed as **Cardinal accounting**;
- that additive portfolio is not Broad Market Value, Intrinsic, Team Utility, Decision, or league-specific price discovery.

## Historical overextension

Several product surfaces subsequently used generic labels such as `FSFFL Value` or `Franchise value` for Cardinal. Those labels made the coordinate appear more universal than its architecture supports.

PR #162 corrects those presentation aliases where encountered. The coordinate itself remains valid under its explicit name: **FSFFL Cardinal Value / FSFFL Cardinal Market Value**.

## Final classification

**B — market/reference/compatibility coordinate.**

Not A: Cardinal is not intended to own intrinsic football economics or every product definition of value.

Not C: It is not merely an invisible implementation representation beneath Broad Market or Intrinsic; it has its own governed market-cardinal scale and downstream market-magnitude use.

Not D: Durable promotion records do not establish it as obsolete or scheduled for removal. It remains useful for market-cardinal magnitude/accounting where explicitly named.

Not E: Original intent, formula/reference source, promotion, validation and downstream semantics are sufficiently established from durable repository evidence.
