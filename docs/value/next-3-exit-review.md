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
| Forecast-to-economic conversion coefficients | PROVISIONAL_GOVERNED | No unsupported universal fallback; operational mappings must carry evidence/version/uncertainty and may be absent explicitly | No |
| Pick-value probability mixture architecture | AUTHORITATIVE | Pick outcomes are represented as empirical probability mixtures with uncertainty rather than hardcoded slot multipliers | No |
| Current pick outcome calibration | PROVISIONAL_GOVERNED | External pick curves are comparator evidence; precise universal outcome curves remain future-updatable and are not invented | No |
| Transaction price representation | AUTHORITATIVE | Directional acquire/sell mappings are typed, versioned and uncertainty-aware; no hidden transaction premium | No |
| Transaction/liquidity coefficients | PROVISIONAL_GOVERNED | Broad independent clearing evidence is not yet sufficient for universal directional offsets; absence is explicit rather than treated as zero or replaced by market price | No |
| Clean one-for-one completed-trade benchmark | CHALLENGER / RESEARCH | Infrastructure implemented: clean player-for-player trades are preserved as pairwise clearing evidence, point-in-time market snapshots are scored without future leakage, and stale evidence is rejected | No |
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

The governed v1 lineage catalog conservatively groups Dynasty Dealer, FantasyCalc and Stats Guy under one revealed-transaction evidence-family root until corpus overlap is quantified. DynastyProcess occupies a separate FantasyPros-consensus-derived evidence family. Provider count therefore cannot masquerade as evidence independence.

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

## Closeout gates

| Gate | Status | Evidence |
| --- | --- | --- |
| One-for-one transaction benchmark infrastructure | COMPLETE | Typed transaction evidence, strict clean-trade extraction, point-in-time percentile benchmark, stale/future evidence protection, CI tests |
| Transaction/liquidity classification | COMPLETE | PROVISIONAL_GOVERNED until broader independent clearing corpus supports universal directional offsets |
| Intrinsic/pick provisional policy | COMPLETE | `next-3-provisional-calibration-policy.md` forbids hidden fallback/substitution and defines updateable governed behavior |
| Authority / anti-double-counting audit | COMPLETE | `next-3-authority-audit.md` assigns each effect to one home; automated import-boundary regression prevents Value from importing downstream authority |
| Source-lineage operationalization | COMPLETE | v1 governed source catalog plus lineage-aware vote collapse and regression tests |
| Final PR scope review | PENDING_FINAL_HEAD | Confirm changed files contain only NEXT-3 Value, research scripts/workflow, tests and documentation; no downstream team-utility/presentation authority |
| Final CI and market research workflow | PENDING_FINAL_HEAD | Must be green on exact final PR head |
| Merge | PENDING | Merge only after the two final-head checks above pass |

## Non-blocking future refinement

The following work should continue after NEXT-3 without delaying NEXT-4:

- broader multi-league completed-trade corpus;
- empirical league-residual shrinkage optimization;
- learned market-source weighting challengers;
- more granular scoring/TE-premium cohorts;
- package-trade implied-value research;
- updated pick curves as additional draft classes mature;
- commercial-rights upgrades or provider replacement where necessary.

## Exit conclusion

There are **no NOT_READY concepts on a path NEXT-4 must consume**. Remaining empirical work concerns parameter maturity, not missing authority or architecture. NEXT-3 is ready to close once the exact final branch head passes scope review, CI and the reproducible market-research workflow.

Empirical parameters remain versioned and updateable by design rather than frozen at the NEXT-3 merge date.
