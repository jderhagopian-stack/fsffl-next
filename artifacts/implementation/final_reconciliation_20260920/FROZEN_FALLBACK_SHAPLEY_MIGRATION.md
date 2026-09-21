# Final Reconciliation — Frozen Forecast Fallback + Canonical Shapley Intrinsic

Date: 2026-09-20
Directive scope: bounded follow-on to completed PR #162 Forecast/Value reconciliation.

## Management decisions implemented

1. A demonstrably malformed fresh full-season provider revision must not override healthy preserved preseason Forecast authority.
2. Canonical FSFFL Intrinsic is the governed Shapley contract.
3. Legacy replacement-surplus is not an equal universal Intrinsic authority.

No prior reconciliation work was rerun.

## Malformed live Razzball disposition

The completed numerical audit already proved the live Razzball revision effective
`2026-09-20T13:48:44Z`, source version
`razzball-season-projections-html-v3:horizon-isolated`, was malformed upstream.

Representative persisted source-page values included:
- Josh Allen: 7,682 pass yards, 47.9 pass TD, 1,134 rush yards, 21.9 rush TD;
- Jahmyr Gibbs: 2,665 rush yards, 22.7 rush TD, 119 receptions;
- Puka Nacua: 223 receptions, 2,926 receiving yards, 17 receiving TD.

The completed trace proved those values were preserved exactly through:
source row -> CurrentProjectionSnapshot -> normalized ForecastObservation.

## Runtime correction

New module:
`src/fsffl/forecast/source_health.py`

The correction is an operational revision quarantine, not a new Forecast model.

It identifies only the exact proven-bad current revision by:
- provider: `razzball`;
- source version: `razzball-season-projections-html-v3:horizon-isolated`;
- effective timestamp: `2026-09-20T13:48:44Z`;
- converted provider row count: 562.

`build_current_live_forecasts` now applies that source-health check immediately after provider acquisition and before normalization/ensemble construction.

If the bad revision is present:
- Razzball is recorded as a failed source;
- no Razzball observation enters the ensemble;
- the >=2-independent-source live authority remains unchanged;
- if at least two other healthy providers exist, the normal live path continues;
- if fewer than two healthy live sources remain, the live loader fails closed;
- the already-governed persistence-backed resilient loader then uses the preserved preseason baseline when available.

A later Razzball revision does not match the incident identity and remains eligible for the normal live path.

No divisor, clipping rule, provider reweight, single-source FFToday promotion, or Forecast fit was added.

## Frozen preseason authority used

The preserved production baseline remains:
- artifact kind: `preseason_forecast_baseline`;
- record id: 145;
- scope: `sleeper:1312071960615731200:2026`;
- model version: `next2-preseason-baseline-v1`;
- evaluation/capture: `2026-09-10T21:36:41.346326Z`;
- source IDs: FFToday + Razzball;
- raw ensemble observations: 1,675;
- payload SHA-256: `cea4126d353f85f1e1fe66bfba4214e204277f487be04462dbe18fb59ae0f387`;
- raw-array SHA-256: `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`;
- canonical Year-1 board SHA-256: `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`.

This branch does not modify that artifact or its hashes.

Important: this implementation does **not** claim the Sep-10 individual Razzball component was healthy. Individual provider-row snapshots for that historical capture were not retained. The preserved combined baseline was separately recovered, deterministic, plausible, and already governed; that is the authority reused.

## Explicit product provenance

When fallback is active:
- `LiveForecastEvidence.evidence_basis == "preseason_baseline"`;
- season fantasy-point rows are sourced as
  `fsffl:preseason_baseline_league_scored`;
- runtime model version is the preserved preseason authority runtime;
- the failed live-refresh reason includes the source-health quarantine incident;
- intelligence status and refresh responses expose the evidence basis/runtime provenance.

## Canonical Shapley migration

The Franchise Value Lens now calls:
`/api/value/intrinsic-shapley-v1`

It no longer calls:
`/api/value/intrinsic-v1`

The consumer displays:
- raw governed Shapley marginal fantasy-point quantity;
- Shapley presentation percentile for Market comparison;
- year-by-year discounted contribution evidence;
- contract/model/Forecast provenance;
- reduced/fallback evidence path when present.

The presentation states that:
- Broad Market is separate;
- Cardinal is separate;
- League Market Value remains unavailable;
- Team Utility remains downstream;
- raw Market and Intrinsic values are not subtracted.

## Replacement-surplus disposition

After the Franchise migration, no current product presentation consumer requires
`/api/value/intrinsic-v1`.

The route remains temporarily available only as a deprecated compatibility/research endpoint and now declares:
- `authority_status=legacy_replacement_surplus_compatibility_only`;
- canonical Intrinsic endpoint = `/api/value/intrinsic-shapley-v1`;
- no current product consumer.

The underlying replacement-surplus implementation is not deleted in this bounded task because it remains useful for historical/research comparison and compatibility. It is not exposed as canonical universal Intrinsic.

## League Atlas boundary

The existing Atlas value-lens contract continues to expose:
- Broad Market;
- canonical Shapley Intrinsic;
- percentile-rank difference.

It now names Shapley explicitly as the canonical FSFFL Intrinsic authority.

Still not created:
- team Intrinsic totals;
- team value ranks;
- League Market Value;
- owner-adjusted universal Value;
- acceptance probability;
- new Team Utility inputs.
