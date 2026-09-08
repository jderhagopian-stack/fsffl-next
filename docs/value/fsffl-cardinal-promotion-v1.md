# FSFFL Cardinal Market Score — NEXT-3 v1 Promotion Record

## Decision

Promote a versioned **FSFFL Cardinal Market Score** as the authoritative current market-cardinal representation for player and rookie-pick assets.

This is a Value-layer market-price representation. It is **not** intrinsic dynasty value, team-specific utility, transaction price, a trade grade, or a recommendation. Those remain distinct typed concepts and downstream authorities.

The promoted product scale is:

- `scale_id`: `fsffl-market-cardinal`
- `version`: `next3-v1`
- nominal range: 0–10,000 FSFFL Value points
- reference axis: Stats Guy Fantasy superflex or non-superflex dynasty values for the active league format

Market Percentile remains separately authoritative as a relative market-position diagnostic.

## Why this scale is being promoted

The previous live NEXT-3 percentile baseline was empirically useful but discarded magnitude. The cardinal research work preserved provider-native magnitude and compared competing mappings without future leakage.

The chronological research panel used:

- Stats Guy: 53 weekly snapshots, 19,826 observations, 2025-09-01 through 2026-08-31;
- DynastyProcess: 45 snapshots, 50,652 observations across the retained contexts, 2025-09-05 through 2026-08-28;
- 16,622 fresh point-in-time overlap pairs from Stats Guy to DynastyProcess;
- 16,598 fresh overlap pairs from DynastyProcess to Stats Guy.

A later chronological holdout beginning in June 2026 compared affine, log-affine, and monotone piecewise-quantile mappings.

### Held-out mapping results

Stats Guy -> DynastyProcess, 4,473 holdout pairs:

- piecewise-quantile MAE: 280.56; RMSE: 619.34;
- affine MAE: 338.49; RMSE: 660.62;
- log-affine MAE: 914.77; RMSE: 1,273.46.

DynastyProcess -> Stats Guy, 4,503 holdout pairs:

- piecewise-quantile MAE: 237.23; RMSE: 553.60; mean signed error: -2.67;
- affine MAE: 245.55; RMSE: 558.39;
- log-affine MAE: 855.98; RMSE: 1,254.69.

The evidence therefore rejects a simple log-shaped common scale and supports a monotone non-linear mapping. The near-zero held-out bias when independent DynastyProcess evidence is mapped onto the Stats Guy axis is especially useful for adopting that axis as the common market-cardinal reference.

## Transaction evidence and limitation

The user league produced four clean player-for-player trades after the explicitly excluded 2022 startup season, but all four occurred in 2023. The retained historical market panels begin in September 2025, so those trades cannot be used as point-in-time scalar validation without future leakage.

This absence is retained as a limitation rather than filled with current values.

The reference source itself is explicitly transaction-derived: Stats Guy documents that its player and pick values are solved from millions of completed trades across a very large set of Sleeper leagues, refreshed approximately daily. That revealed-transaction provenance, combined with the independent chronological DynastyProcess holdout, is sufficient for promotion of a **market-cardinal baseline**. It is not evidence that the score is intrinsic truth or that package arithmetic alone determines trade fairness.

## Draft picks

Stats Guy exposes rookie-pick values on the same dynasty value axis as players, including generic round-only picks, early/mid/late variants, and slot-specific current-class picks.

NEXT v1 uses the generic round-only value for a canonical future pick whose exact eventual slot is unknown. This avoids pretending to know future draft position. A later Value-layer model may replace the generic value with a distribution over projected slots when authoritative pick-slot probabilities are available.

## Source-lineage rule

Stats Guy, Dynasty Dealer, and FantasyCalc are conservatively treated as one revealed-transaction evidence family in the current market-source registry. Promotion of the cardinal score does not grant three independent votes to those feeds.

For v1 current authority:

- Stats Guy provides the direct reference-axis player/pick score when available;
- correlated transaction-derived feeds remain supporting/fallback research evidence unless an explicit governed transform is promoted;
- DynastyProcess remains independent cross-source validation/research evidence and is not live-mapped when canonical identity support is unavailable.

Missing values remain missing rather than being fabricated from Market Percentile.

## Empirical uncertainty

The v1 score records the independent-source held-out mapping diagnostics as scale-validation uncertainty:

- MAE: 237.23 FSFFL points;
- RMSE: 553.60 FSFFL points;
- holdout sample: 4,503 matched asset observations.

These values describe historical cross-source scale disagreement. They are **not** a claim that every individual asset has a normally distributed ±553.60-point true-value error.

## Downstream semantics

The FSFFL Cardinal Market Score may now be consumed as the cardinal market-value input for downstream Value/Decision work.

Trade Decision must not reduce package evaluation to simple score addition. Existing Decision authority continues to own package concentration, best-asset effects, roster-slot compression, liquidity/transaction economics, bilateral team utility, competitive consequences, and other governed package effects.

## Promotion status

`AUTHORITATIVE_MARKET_CARDINAL_V1`

Promotion applies only to the market-cardinal representation described above. Intrinsic dynasty value, team-specific value, transaction price, and package/decision authority retain their existing separate promotion states.
