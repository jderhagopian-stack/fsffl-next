# Bounded Product Sanity — Malformed Provider Fallback + Franchise Shapley

Date: 2026-09-20

This is a bounded implementation sanity using the already-persisted real numerical trace and preserved production baseline. It does not rerun the completed provider audit and is not a live-beta deployment claim.

## A. Malformed current Razzball cannot drive the displayed season projection

Persisted pre-fix two-source current display from the completed numerical trace:

| Player | malformed current two-source display | preserved Sep-10 governed baseline |
| --- | ---: | ---: |
| Josh Allen | 532.13 | 389.0705 |
| Jahmyr Gibbs | 460.45 | 328.0230 |
| Puka Nacua | 399.35 | 276.3080 |

The bad Razzball revision is now rejected before normalization/ensemble.

At current provider health observed in the completed trace:
- Razzball -> quarantined;
- FFToday -> healthy;
- CBS -> unavailable for the full-season coordinate;
- NFL Fantasy -> unavailable for the full-season coordinate.

That leaves one healthy live provider, so the >=2-source live authority fails closed. The persistence-backed resilient loader then uses record 145 rather than displaying the inflated two-source mean.

Focused regression executes this same authority sequence and proves:
- bad Razzball does not enter the live ensemble;
- fallback `evidence_basis` is `preseason_baseline`;
- displayed season source is `fsffl:preseason_baseline_league_scored`;
- failed-source provenance contains
  `razzball-full-season-upstream-inflation-20260920`;
- the persistence store receives zero writes during fallback;
- a later valid Razzball revision continues through `live_full_season`.

## B. Frozen artifact provenance is explicit

Fallback uses the existing immutable preseason artifact and current league scoring.

It does not:
- rewrite Sep-10 raw observations;
- refetch historical providers;
- substitute FFToday alone;
- infer that the Sep-10 Razzball component was healthy.

The branch comparison contains no modification to the preserved baseline artifact directories.

## C. Franchise now consumes canonical Shapley Intrinsic

The Franchise Value Lens consumer now requests the same governed Shapley contract used by newer Market/value-lens architecture.

Visible authority:
- `FSFFL Intrinsic · Shapley`;
- raw quantity `raw_governed_shapley_marginal_fantasy_points`;
- presentation comparison to Broad Market by percentile rank only.

Legacy replacement-surplus is not converted to Shapley and no parity transform exists.

## D. Cardinal / Broad Market remain unaffected

Cardinal:
- remains explicit market-cardinal reference/accounting evidence;
- is not the canonical Intrinsic source.

Broad Market:
- remains `dynasty-market-percentile`;
- is not added to Intrinsic;
- remains non-additive at team level.

## E. Authority boundary check

No change to:
- P0 / D0-D1 routes;
- Forecast coefficients;
- provider weights;
- Shapley mathematics;
- 0.85 Shapley discount;
- Simulation;
- Decision / Search economics;
- Team Utility mathematics;
- League Market Value availability.
