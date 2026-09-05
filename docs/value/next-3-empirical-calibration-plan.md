# NEXT-3 Empirical Calibration Plan

NEXT-3 should calibrate related value concepts from one reusable, point-in-time evidence panel rather than through isolated coefficient hunts.

## Objective

Build a governed historical panel that can support, from the same normalized evidence backbone:

1. broad dynasty market measurement;
2. format/cohort market calibration;
3. league-specific residual market calibration with shrinkage;
4. directional transaction-price/liquidity calibration;
5. forecast-to-intrinsic-value conversion;
6. pick-value and pick-uncertainty calibration.

The panel is evidence infrastructure. It does not grant production authority to any fitted model. Challenger promotion remains a separate chronological validation decision.

## Data-location rule

Raw third-party evidence is not committed to the public repository unless redistribution rights are explicit and compatible.

The repository may contain:

- acquisition and normalization code;
- schemas and adapters;
- source/rights metadata;
- synthetic fixtures;
- reproducible calibration logic;
- derived parameters/results that may legally be published;
- validation summaries.

Research-only, runtime-only, or privately retained datasets should remain outside git. Their contribution to a fit is represented through provenance metadata and versioned artifacts.

## Point-in-time rule

Every evidence row must record when it was actually observable. A calibration panel for time T must reject evidence observed after T. Historical trade/value reconstruction must never use a later market value or realized football outcome as though it were known earlier.

## Hierarchical market calibration

League-specific market behavior is derived, never hardcoded.

The intended hierarchy is:

`global dynasty market -> comparable format cohort -> specific league residual`

Format and league adjustments should be partially pooled/shrunk toward the broader level. The amount of shrinkage is itself an empirical model output with sample-size and uncertainty metadata, not a fixed league multiplier.

League rules that create structural scarcity must not be counted twice. Market-context calibration should estimate residual market behavior after the authoritative structural economic treatment is accounted for.

## Evidence roles

### Market evidence

Use independent, point-in-time market observations where rights and provenance permit. Market aggregators/comparators are not automatically treated as independent votes if they embed other sources.

### Completed transactions

Use actual dynasty trades where available to estimate clearing behavior, liquidity, directional acquisition/sale effects, and league-specific residual preferences. Package structure must be preserved rather than forcing every trade into an unsupported single-asset equivalence.

### Forecast and realized outcomes

NEXT-2 forecast distributions remain the upstream football evidence. Historical realized outcomes are used for fitting/validation only through chronological, point-in-time-safe joins.

### Pick outcomes

Use historical rookie draft slots, subsequent player outcomes/value paths, class context, and unresolved-pick landing distributions to estimate pick-value distributions. Do not substitute current pick prices for historical point-in-time pick values.

## Initial source-screening notes

Candidate sources are classified separately for predictive usefulness and legal/operational usability.

- DynastyProcess open data is a useful research/reference candidate. Its license and source construction must be respected, and FantasyPros ECR-derived values are market/ranking evidence rather than an independent raw football forecast.
- FantasyCalc is a strong candidate for trade-derived market evidence because its public product exposes dynasty rankings/trade information. Terms and allowed retention/redistribution must be reviewed explicitly before durable ingestion is promoted.
- KeepTradeCut is useful as a public market comparator, but its published FAQ states that scraping values or reproducing the full rankings/values is prohibited. It must not be used as a scraped calibration feed unless permission/terms change.
- Sleeper league histories are appropriate league-specific transaction/state evidence for connected leagues, subject to the canonical state and point-in-time adapters.
- nflverse/nflreadpy remain appropriate for realized NFL outcomes and identity support, not market-price votes.

This list is not a permanent provider lock. Providers remain adapters and may be replaced or expanded as evidence quality, access, and rights change.

## Batch workflow

1. Acquire source snapshots outside git.
2. Normalize into `CalibrationObservation` rows.
3. Materialize one immutable `CalibrationPanel` with a declared `as_of` and panel version.
4. Fit multiple NEXT-3 candidates from the same panel.
5. Record `CalibrationFitMetadata` for every fit.
6. Evaluate chronologically, with held-out windows where data permits.
7. Compare broad, format, and league-level models; measure whether league residuals improve held-out transaction prediction enough to justify complexity.
8. Promote only evidence-supported models. Otherwise retain the simpler baseline and keep challengers non-authoritative.

## Efficiency rule

Do not rebuild a bespoke dataset for each factor. Add a source once, normalize it once, preserve provenance once, and allow the market, transaction, intrinsic, and pick fitters to consume appropriate slices of the same governed panel.
