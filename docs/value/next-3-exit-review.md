# NEXT-3 Exit Review

This document is the governing closeout checklist for NEXT-3 Asset & Franchise Valuation. It distinguishes architectural completeness from empirical maturity so NEXT-4 is not blocked by open-ended coefficient hunting.

## Promotion rule

A component may enter NEXT-3 in one of four states:

- **AUTHORITATIVE** — validated enough to be the default production behavior.
- **PROVISIONAL_GOVERNED** — a real effect with incomplete evidence; explicit, bounded, versioned, uncertainty-aware, and designed for future updating.
- **CHALLENGER** — implemented and testable but cannot affect authoritative output.
- **NOT_READY** — missing an acceptable implementation or violates an authority/provenance requirement.

NEXT-4 may consume AUTHORITATIVE and PROVISIONAL_GOVERNED outputs. It must not silently depend on CHALLENGER or NOT_READY behavior.

## Current NEXT-3 classification

| Component | Status | Basis | NEXT-4 blocker? |
| --- | --- | --- | --- |
| Typed value concepts / scale compatibility | AUTHORITATIVE | Separate market, intrinsic, pick, transaction and distribution types; incompatible scales fail closed | No |
| Point-in-time market observation handling | AUTHORITATIVE | Latest admissible observation per provider; future evidence rejected | No |
| Robust market baseline method | AUTHORITATIVE | Median is transparent and robust; 28-day chronological diagnostic favored equal-median ensemble over either historical source alone across 13,442 asset evaluations / 38 windows | No |
| Source-lineage / anti-double-voting | AUTHORITATIVE | Governed source registry plus lineage-aware market voting; identical evidence roots receive one vote; partial overlap fails closed | No |
| Current multi-source acquisition | AUTHORITATIVE_RESEARCH_INFRASTRUCTURE | Four-source concurrent research panel: DynastyProcess, Dynasty Dealer, FantasyCalc, Stats Guy; provider failure isolated | No |
| Exact-format vs broader-family evidence hierarchy | AUTHORITATIVE | Exact format remains distinct; broader QB-premium evidence may inform broader context without being mislabeled as exact | No |
| League-format / league residual market context machinery | AUTHORITATIVE | Global -> format -> league residual hierarchy, explicit shrinkage and point-in-time evidence boundaries | No |
| Empirical shrinkage-strength estimates | PROVISIONAL_GOVERNED | Fitter supports evidence-volume shrinkage, but broad held-out league corpus is not yet sufficient to promote a universal learned shrinkage policy | No |
| Intrinsic value representation and forecast propagation | AUTHORITATIVE | NEXT-2 forecast distribution is upstream; value mapping must be supplied explicitly with evidence metadata; no invented fallback | No |
| Forecast-to-economic conversion coefficients | PROVISIONAL_GOVERNED | Conversion is required for operational intrinsic value but current branch intentionally has no unsupported default; fitted mappings must carry evidence/version/uncertainty | No, provided consumer supplies governed mapping |
| Pick-value probability mixture architecture | AUTHORITATIVE | Pick outcomes are represented as empirical probability mixtures with uncertainty rather than hardcoded slot multipliers | No |
| Current pick outcome calibration | PROVISIONAL_GOVERNED | Historical draft-slot outcome panel still needs broader empirical fit before any precise universal curve is considered mature | No |
| Transaction price representation | AUTHORITATIVE | Directional acquire/sell mappings are typed, versioned and uncertainty-aware; no hidden transaction premium | No |
| Transaction/liquidity coefficients | PROVISIONAL_GOVERNED | Completed-trade calibration is not yet broad enough to justify universal directional offsets; package decomposition must not invent scalar prices | No |
| Clean one-for-one completed-trade benchmark | CHALLENGER / RESEARCH | Preferred first independent clearing-price test; remains separate from package trades | No |
| Package-trade implied valuation | CHALLENGER | Must preserve package structure and concentration/liquidity effects; cannot silently infer per-asset clearing prices | No |
| Market ensemble learned source weights | CHALLENGER | Equal/robust aggregation remains default until independent held-out transaction evidence supports learned weights | No |
| Team-specific roster utility | OUT_OF_SCOPE | NEXT-4 authority | No |

## Empirical evidence already obtained

### Current four-source panel

A successful current research run produced 2,852 normalized observations with no source failures:

- DynastyProcess: 1,260
- Dynasty Dealer: 824
- FantasyCalc: 394
- Stats Guy: 374

The sources are strongly aligned but not identical, supporting an ensemble rather than a single-provider authority.

### Historical evidence

- Stats Guy: 53 weekly snapshots, 19,826 normalized observations, 2025-09-01 through 2026-08-31.
- DynastyProcess: 45 usable snapshots, 50,652 normalized observations, 2025-09-05 through 2026-08-28. Twenty-nine legacy commits were explicitly skipped because they lacked the provider identifier needed for trustworthy point-in-time identity resolution.

### 28-day chronological ensemble diagnostic

Using only contemporaneously available source snapshots and evaluating market position 28 days later:

- Stats Guy source MAE: 0.05281 percentile units
- DynastyProcess source MAE: 0.05222
- Equal-median ensemble MAE: 0.03798
- Asset evaluations: 13,442
- Evaluation windows: 38

This supports the robust equal-median method as the default market baseline. It does **not** by itself validate intrinsic value or transaction clearing price and therefore is not used for those authorities.

## Remaining pre-NEXT-4 work

The following are the only remaining required closeout actions before NEXT-4:

1. Complete the clean one-for-one transaction benchmark infrastructure and classify transaction/liquidity coefficients as promoted or provisional.
2. Record explicit governed provisional policies for any forecast-to-economic and pick-outcome calibration that lacks sufficient held-out evidence.
3. Run the authority-boundary / anti-double-counting audit across market, format context, intrinsic, pick, transaction and uncertainty channels.
4. Confirm CI and research workflow success at the final PR head.
5. Review PR #4 diff for accidental downstream team-utility or presentation logic.
6. Merge NEXT-3 only after every row above is AUTHORITATIVE, PROVISIONAL_GOVERNED, CHALLENGER, or explicitly OUT_OF_SCOPE — no NOT_READY behavior may remain on a path NEXT-4 will consume.

## Non-blocking future refinement

The following work should continue after NEXT-3 without delaying NEXT-4:

- broader multi-league completed-trade corpus;
- empirical league-residual shrinkage optimization;
- learned market-source weighting challengers;
- more granular scoring/TE-premium cohorts;
- package-trade implied-value research;
- updated pick curves as additional draft classes mature;
- commercial-rights upgrades or provider replacement where necessary.

NEXT-3 should be considered architecturally complete when the remaining closeout actions above pass. Empirical parameters remain versioned and updateable by design rather than frozen at the NEXT-3 merge date.
