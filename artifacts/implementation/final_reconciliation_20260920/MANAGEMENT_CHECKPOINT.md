# FSFFL NEXT — Final Reconciliation Management Checkpoint

Date: 2026-09-20

## Directive start

- PR #162 start head required by management: `cd3caee691a3ebd6a202624fc1fab2581290348c`
- prior Forecast/Value reconciliation: preserved; not rerun
- scope executed: malformed-provider frozen fallback + canonical Shapley Franchise migration only

## Validated implementation checkpoint

Implementation/docs head before this checkpoint:
`a953fc74f7a4f91d0f37cc081cfdb2bc3eec2ebd`

Validation at that head:
- CI `35546491629`: PASS — **1,301 passed, 2 warnings**
- Cardinal Value Research `35546491630`: PASS
- League value-lens real-roster audit `35546491659`: PASS

## Malformed-provider behavior

### Before

The completed numerical trace proved the 2026-09-20 Razzball full-season revision was already inflated upstream.

Persisted current two-source displayed means included:
- Josh Allen: 532.13;
- Jahmyr Gibbs: 460.45;
- Puka Nacua: 399.35.

### After

The exact proven-bad provider revision is quarantined immediately after acquisition and before normalization/ensemble construction.

Incident identity:
- provider: Razzball;
- source version: `razzball-season-projections-html-v3:horizon-isolated`;
- effective time: `2026-09-20T13:48:44Z`;
- converted source row count: 562;
- incident: `razzball-full-season-upstream-inflation-20260920`.

This is a source-health quarantine only:
- no divisor;
- no clipping;
- no provider reweight;
- no FFToday-only authority;
- no Forecast fit/tuning.

If two other healthy live providers exist, the governed live path still runs normally.
If the quarantine leaves fewer than two healthy sources, the existing >=2-source live rule fails closed and the persistence-backed resilient loader uses the preserved preseason baseline when available.

A later valid Razzball revision remains eligible for the governed live path.

## Frozen fallback authority

The fallback is the already-governed immutable preseason baseline:
- production record id: 145;
- model version: `next2-preseason-baseline-v1`;
- capture/evaluation: `2026-09-10T21:36:41.346326Z`;
- sources: FFToday + Razzball;
- raw observations: 1,675;
- payload SHA-256: `cea4126d353f85f1e1fe66bfba4214e204277f487be04462dbe18fb59ae0f387`;
- raw-array SHA-256: `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`;
- Year-1 board SHA-256: `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`.

This PR does not rewrite the frozen artifact.

Important limitation retained:
the individual Sep-10 provider rows were not persisted, so this implementation does **not** claim the Sep-10 Razzball component itself was healthy.

## Product provenance after fallback

Regression coverage proves:
- bad Razzball cannot enter the live ensemble;
- fallback `evidence_basis == preseason_baseline`;
- displayed season source is `fsffl:preseason_baseline_league_scored`;
- fallback runtime is the preserved preseason authority runtime;
- failed-source provenance contains the quarantine incident;
- fallback performs zero persistence writes;
- a later valid Razzball revision uses `live_full_season`.

Product intelligence/refresh status now exposes the Forecast evidence basis, runtime model version/evaluation time, and live failure provenance.

## Franchise Shapley migration

Management-confirmed canonical FSFFL Intrinsic is Shapley.

Franchise Value Lens now consumes:
`/api/value/intrinsic-shapley-v1`

It no longer consumes:
`/api/value/intrinsic-v1`

The UI now presents:
- `FSFFL Intrinsic · Shapley`;
- raw governed Shapley marginal fantasy-point value;
- Shapley percentile rank for Broad Market comparison;
- per-year discounted contributions;
- contract, Forecast and evidence-path provenance.

No legacy-to-Shapley conversion or parity transform was introduced.

## Replacement-surplus disposition

After the Franchise migration there is no current product presentation consumer of the legacy replacement-surplus endpoint.

`/api/value/intrinsic-v1` remains only as a deprecated compatibility/research route and explicitly reports:
- `authority_status=legacy_replacement_surplus_compatibility_only`;
- canonical Intrinsic endpoint = `/api/value/intrinsic-shapley-v1`;
- no current product consumer.

The underlying code is retained for bounded compatibility/historical research. It is not canonical universal Value and no new product metric was invented to preserve it.

## League Atlas boundary

The existing Atlas value-lens contract now explicitly identifies:
`canonical_fsffl_intrinsic_authority = shapley_intrinsic`.

The Atlas contract still creates no:
- team Intrinsic total;
- team value rank;
- League Market Value;
- new Team Utility input;
- acceptance probability;
- owner-adjusted universal Value.

Broad Market, Cardinal, Shapley Intrinsic, League Market Value and Team Utility remain separate authorities.

## Frozen boundaries unchanged

No change to:
- P0 / D0-D1 routes or parameters;
- Forecast coefficients;
- provider weights;
- frozen Sep-10 artifact;
- Shapley mathematics;
- Shapley discount;
- Simulation;
- Decision / Search economics;
- Team Utility mathematics.

## Stop

STOP FOR MANAGEMENT REVIEW.

PR #162 remains open/draft and must not be merged or deployed under this directive.
