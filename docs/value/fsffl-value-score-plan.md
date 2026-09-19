# FSFFL Value Score — Cardinal Value Scale Plan

## Purpose

NEXT-3 currently exposes an authoritative market-position estimate on the versioned `dynasty-market-percentile` scale. That scale is useful for ordering assets and for combining providers whose native numeric scales are not directly comparable, but percentile rank is not a cardinal economic measure. Equal percentile gaps do not imply equal economic gaps, and percentile values should not be summed or used as if they preserve magnitude.

The product therefore needs a separate, governed **FSFFL Value Score** that preserves economically meaningful spacing while retaining Market Percentile as supporting market-position evidence.

Target product presentation:

- **FSFFL Value:** cardinal user-facing score, nominally 0–10,000.
- **Market Percentile:** relative market position on the existing 0–1 NEXT-3 scale, displayed as a percentile.

The FSFFL Value Score must not be implemented as `market_percentile * 10,000`. That would merely relabel ordinal/rank information and would not recover lost magnitude.

## Authority

This is a NEXT-3 Value-layer concept.

Value owns the scale definition, provider-scale transformations, uncertainty, provenance, calibration and versioning. Analytics may aggregate or compare an authoritative FSFFL Value Score. Presentation may format and explain it. Decision and Search may consume it only after the scale is validated for the economic operations they require.

The UI must never derive the FSFFL Value Score from percentile or provider-native values.

## What the score must mean

A cardinal score must preserve more than ordering.

For assets A, B and C:

- if `Value(A) - Value(B)` is materially larger than `Value(B) - Value(C)`, the score should represent that difference rather than compressing the three assets into approximately equal rank steps;
- package arithmetic must be validated explicitly rather than assumed from the display scale;
- a 1,000-point difference near the top of the market need not represent the same economic effect as a 1,000-point difference near replacement level unless empirical calibration supports linear interpretation;
- the scale should remain stable enough across refreshes that a score change represents changed evidence/model state rather than arbitrary renormalization.

The 0–10,000 range is a presentation-friendly target, not an authority claim that the economic function is naturally linear over that interval.

## Current evidence available

The live NEXT-3 adapters preserve provider-native market magnitude before the current runtime converts observations to within-source percentiles:

- Dynasty Dealer `current_value`;
- FantasyCalc `value`;
- Stats Guy Fantasy `value`.

Those native values are not directly comparable across providers and must not be averaged without an explicit learned or structurally justified transformation.

Dynasty Dealer, FantasyCalc and Stats Guy are conservatively treated as one revealed-transaction evidence-family root for independent voting until evidence overlap is quantified. The cardinal-score design must preserve that anti-double-voting rule.

## Development sequence

### 1. Preserve native magnitude as typed evidence

Keep provider-native numeric observations alongside the current percentile representation, with explicit source, timestamp, league/format context, native scale identifier and rights/provenance metadata.

Do not promote any provider-native scale to FSFFL authority merely because it has convenient 0–10,000-like units.

### 2. Characterize each provider scale

For each current provider and format cohort, measure:

- range and distribution shape;
- rank monotonicity;
- top-end compression/expansion;
- replacement-level behavior;
- temporal stability;
- sensitivity to league format;
- relationship to completed one-for-one trades and later market prices where point-in-time evidence exists.

This determines whether a simple monotone transformation is defensible or whether a richer calibration is required.

### 3. Build source-to-common-magnitude challengers

Candidate transformations may include monotone quantile mapping, anchored piecewise curves, log/Box-Cox-style transforms, or transaction-calibrated latent-value models. The method should be chosen by held-out evidence, not intuition.

Every challenger must output a typed common cardinal scale with versioned transformation metadata and uncertainty.

### 4. Validate cardinal behavior

Promotion requires more than rank correlation. At minimum test:

- held-out one-for-one transaction pricing/error;
- future market-movement prediction where appropriate;
- stability through time;
- elite/mid/replacement spacing sanity cases;
- superflex versus 1QB behavior;
- position scarcity behavior without creating a second scarcity authority;
- package arithmetic only where transaction evidence supports it;
- resistance to one correlated provider family dominating the ensemble.

Compare challengers against the current percentile baseline and against individual source-native values.

### 5. Define the user-facing FSFFL scale

After a common cardinal latent scale is promoted, map it monotonically to the product-facing nominal 0–10,000 FSFFL Value Score.

The display mapping should:

- preserve ordering and economically validated relative spacing;
- have explicit anchors/versioning;
- avoid arbitrary per-refresh min/max normalization;
- keep score history comparable across time within a model version;
- expose scale/model version in evidence detail.

### 6. Product integration

Once authoritative:

- roster rows show `FSFFL Value` as the primary value number;
- `Market Percentile` remains available beside it or in drilldown/evidence views;
- league portfolio views use the cardinal score only after aggregation semantics are validated;
- Trade Decision consumes the appropriate typed Value concept rather than the display label;
- percentile remains diagnostic and must not substitute for a missing cardinal estimate.

## Promotion gates

The FSFFL Value Score remains **CHALLENGER / NOT YET AUTHORITATIVE** until all of the following are satisfied:

1. common-scale transformation has explicit provenance and versioning;
2. source-native scales are not mixed directly;
3. lineage-aware anti-double-voting is preserved;
4. held-out evidence supports magnitude, not merely ordering;
5. score spacing passes elite/mid/low sanity cases;
6. temporal stability is measured;
7. uncertainty is represented or explicitly bounded;
8. package/additivity behavior is separately validated before downstream use;
9. exact-head CI and regression coverage pass.

## Immediate beta rule

Until the cardinal score is promoted, the product must label the existing live number **Market Percentile**, not Dynasty Value or FSFFL Value. Raw pick count is **Pick Inventory**, not Draft Capital, until authoritative pick-value evidence is attached to that surface.
