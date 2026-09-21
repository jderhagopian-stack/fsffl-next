# Cardinal / Broad Market / Intrinsic authority reconciliation

Date: 2026-09-20  
Classification: **B — market/reference/compatibility coordinate**

## Executive conclusion

`FSFFL Cardinal Value` is a governed market-cardinal reference and additive accounting coordinate. It is **not** Broad Market, FSFFL Intrinsic Value, League Market Value, Team Utility, or a universal master value.

The durable history shows that Cardinal was introduced to recover magnitude that percentile rank cannot preserve, then promoted by directly carrying a format-locked Stats Guy trade-derived 0–10,000 reference axis. Later product surfaces overextended the generic label `FSFFL Value` / `Franchise value`, which made the coordinate appear more universal than its implementation or later architecture supports.

The correct reconciliation is therefore to keep Cardinal available where its market-cardinal magnitude and additive accounting semantics are useful, but label it explicitly and prevent it from silently substituting for Broad Market or FSFFL Intrinsic.

## Provenance and original role

1. NEXT-3 originally established distinct concepts for market price, intrinsic dynasty value, pick value and transaction price. Team-specific roster utility remained downstream.
2. Commit `084027593116196f3a2357715c3f28bdd222bb38` added the Cardinal plan because the existing `dynasty-market-percentile` scale is ordinal and non-additive. The plan said the desired cardinal score needed economically meaningful spacing and separately retained Market Percentile.
3. The same plan explicitly warned that provider-native magnitudes were not automatically a common FSFFL scale and initially treated Cardinal as challenger/not-yet-authoritative pending promotion gates.
4. Commit `5b2fc9f53cee031101711fc3f1fc483b37fdadbc` added `FSFFLCardinalValueScore` and promoted a direct Stats Guy reference cohort as `next3-fsffl-market-cardinal-v1`. The class itself calls the quantity an **exchange-market representation, not intrinsic dynasty value**.
5. These Cardinal commits entered through merged PR #10, the interactive private-beta layer. PR #47 later relabeled the additive Cardinal team total as `Franchise value`; PR #87 used Cardinal for roster carrying/optionality callouts. Those were product uses of the market-cardinal coordinate, not evidence that Cardinal became Intrinsic.
6. PR #133 separately promoted FSFFL Intrinsic Value v1. PR #147 later created the separate Shapley-native `/api/value/intrinsic-shapley-v1` contract while explicitly preserving `/api/value/intrinsic-v1` as the legacy replacement/surplus coordinate.
7. PRs #157 and #161 use Broad Market and Shapley Intrinsic as distinct comparison lenses. PR #161 explicitly excludes Cardinal from the League value-lens contract.

## Current Cardinal mechanics

Player Cardinal:
- scale: `fsffl-market-cardinal`, version `next3-v1`;
- model: `next3-fsffl-market-cardinal-v1`;
- reference source: `statsguy_market_values`;
- reference scale: `statsguy-dynasty-value`;
- player scores directly preserve the selected Stats Guy 0–10,000 cohort after format/context checks;
- no percentile rescaling or cross-provider arithmetic is used in the promoted player Cardinal score.

Pick Cardinal:
- uses generic unknown-slot Stats Guy round values when canonical State does not know the future slot;
- explicitly records slot certainty.

Team Cardinal portfolio:
- sums coherent player/pick Cardinal scores;
- is a Value-layer **market-cardinal accounting view**;
- is not Team Utility or Decision authority;
- may remain available only with explicit Cardinal labeling.

## Broad Market

Broad Market is the independent `dynasty-market-percentile` coordinate. Current live source magnitudes are converted to within-source percentiles and combined under NEXT-3 lineage-aware market governance. It is a relative market-position lens, not an additive team-value scale.

The current runtime deliberately returns Total Market Value unavailable because no separate additive Broad Market scale has been promoted.

## Legacy Intrinsic v1

`/api/value/intrinsic-v1` is `intrinsic-value-v1`: three-year weighted replacement-adjusted expected fantasy-point surplus. It uses weights 1.00 / 0.85 / 0.70 and a lineup-derived marginal replacement context. It is explicitly a surplus-over-replacement economic coordinate.

## Shapley Intrinsic

`/api/value/intrinsic-shapley-v1` is the later Shapley-native contract. Its raw quantity is `raw_governed_shapley_marginal_fantasy_points`. It attributes deployment value across the governed Y1/Y2/Y3 Forecast path with discount 0.85 and the frozen Shapley game. Market, owner, trade and Team Utility inputs do not enter the calculation.

Shapley has an efficiency/additivity property inside the governed deployment game, but that does **not** create a promoted product-level summed team Intrinsic value or authorize summing presentation percentiles.

## Legacy Intrinsic disposition

The Franchise Value Lens currently calls `/api/value/intrinsic-v1`, while current Market disagreement and `/api/league/value-lenses` use Shapley Intrinsic.

That is not a semantic-parity migration. Replacement-adjusted surplus and Shapley deployment attribution answer related but mathematically different economic questions. The directive permits a bounded migration only if it is semantic/parity-safe.

**Disposition: do not silently migrate the Franchise lens in this task. Return the migration to management.**

## Reconciled architecture

```text
                           VALUE LAYER

  Broader market evidence ──> Broad Market
                              dynasty-market-percentile
                              relative / non-additive
                                      │
                                      │ compare by rank/percentile only
                                      ▼
  Governed Forecast ────────> FSFFL Intrinsic (Shapley)
                              raw governed Shapley marginal FP
                              market-independent

  Stats Guy market reference ─> FSFFL Cardinal Value
                                explicit market-cardinal reference
                                additive accounting coordinate
                                NOT a substitute for either lens above

  League-specific observed pricing ─> League Market Value
                                      NOT YET PROMOTED

  Roster / competitive context ─────> Team Utility
                                      DOWNSTREAM / SEPARATE
```

## Atlas consequence

The safe Atlas value contract remains **Broad Market | FSFFL Intrinsic | Difference** at player/distribution level. The difference is a presentation rank/percentile gap, not raw-value subtraction. Competitive strength, Simulation and fragility remain separate governed layers.

Cardinal may appear only as an explicitly named optional market-cardinal/accounting lens after product-direction review. It must not define Atlas value authority by implementation inertia.

No League Market Value, summed Broad Market percentile, summed Intrinsic percentile, new team-value coordinate, owner-adjusted Value, recommendation, or acceptance probability is created here.