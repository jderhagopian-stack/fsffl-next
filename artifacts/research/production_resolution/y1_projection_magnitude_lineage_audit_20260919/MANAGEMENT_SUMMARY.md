# FSFFL NEXT - Forecast Y1 Projection Magnitude & Lineage Audit

Date: 2026-09-19  
Final classification: **D - EVIDENCE BOUNDARY**

## Plain-English result

The audit cannot safely answer why the earlier governed Bijan Year-1 projection near 329 points became the current 479.9-point value.

The surviving evidence proves two things at once:

1. The change is real in the named durable outputs. The exact PR #147 supplemental diagnostic records Bijan 329.24, Gibbs 328.02, McCaffrey 315.36, Darnold 281.73 and Rodgers 243.70. The current frozen 335-player coordinate records 479.90, 460.25, 433.50, 383.06 and 344.31 respectively.
2. The exact causal bridge is no longer reproducible from durable evidence.

## Current board

The current coordinate is fully persisted and reloadable:

- coordinate: `year1-current-governed-2026:2026-09-18T09:42:31.889752+00:00`;
- 335 players: QB 61 / RB 88 / WR 122 / TE 64;
- canonical SHA-256: `c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f`;
- workflow run: `35330898624`;
- artifact: `10541375155`;
- artifact ZIP SHA-256: `c23fed641c4ad689513510022f187e6ea05cab2dc88d457d545be9afc1f49ee7`;
- successful governed live sources: FFToday + Razzball.

The persisted current raw metrics are **post-normalization equal-weight ensemble means**. The stored Year-1 league points reproduce exactly from those means for the required named players.

Examples:
- Bijan: 2,131 rush yards, 13.7 rush TD, 113.5 receptions, 1,005.5 receiving yards, 4.55 receiving TD -> 479.90 half-PPR.
- Gibbs: 2,042.5 rush yards, 17.35 rush TD, 95.5 receptions, 780.5 receiving yards, 4.35 receiving TD -> 460.25.
- Puka: 93 rush yards, 0.95 rush TD, 169 receptions, 2,234 receiving yards, 13.1 receiving TD -> 401.50.
- Darnold: 5,899 pass yards, 38.15 pass TD, 20.15 INT, 216 rush yards, 2.2 rush TD -> 383.06.

Those calculations establish internal arithmetic consistency **after ensemble formation**. They do not prove the underlying provider rows were semantically correct.

## Current provider-level evidence boundary

The workflow artifact contains only four files:
- `governed_year1_universe.json`;
- `governed_year1_universe_manifest.json`;
- `reload_verification.json`;
- `report.md`.

The row-complete JSON does not persist each provider's normalized FFToday and Razzball input row. It stores only ensemble means with provenance `fsffl:live_equal_weight[fftoday,razzball]`.

Therefore this audit cannot show:
- FFToday's exact player stat line separately;
- Razzball's exact player stat line separately;
- the exact provider-by-provider contribution to each extreme total;
- whether one provider alone drove the extreme total;
- whether the two source pages represented exactly the same intended season/vintage semantics.

Reconstructing those rows from the ensemble mean/stddev, or fresh-fetching today's provider pages, would violate the directive.

## Prior PR #147 board evidence boundary

The exact named PR #147 values survive in a management artifact at the exact current PR head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.

However, the full old 335-player Year-1 vector does not.

The durable old coordinate is referenced by:
- player count: 335;
- material SHA-256: `70de5578372bca5914a570356d8a2bb2f0f4a16e2763849a316e6b587f90b706`;
- sources: FFToday + Razzball.

A prior dedicated recovery audit already established that the row-complete old vector was not present in repository history, the persisted sentinel artifacts, the activation bundle, or the reviewed GitHub Actions artifacts.

The old activation artifact is still available:
- run `35145456513`;
- artifact `10467264159`;
- ZIP SHA-256 `3866d65353c27cab66f83d701b0af7f892310a71187d02206c49f77181a95ca5`.

Its contents are current I1 facts, frozen h1/h2, frozen h3, and an activation build report. It does not contain the Year-1 live vector.

## Observable named change

The surviving named deltas are:

| Player | Old Y1 | Current Y1 | Change | Percent |
| --- | ---: | ---: | ---: | ---: |
| Bijan Robinson | 329.24 | 479.90 | +150.66 | +45.76% |
| Jahmyr Gibbs | 328.02 | 460.25 | +132.23 | +40.31% |
| Christian McCaffrey | 315.36 | 433.50 | +118.14 | +37.46% |
| Sam Darnold | 281.73 | 383.06 | +101.33 | +35.97% |
| Aaron Rodgers | 243.70 | 344.31 | +100.61 | +41.28% |

These are observations, not causal attributions.

Without the missing old 335 rows and the current pre-ensemble provider rows, it would be speculation to assign these changes to provider vintage, source coverage, weighting, stat interpretation, player matching, season semantics or availability assumptions.

## Stop boundary

Because Stage 0 requires exact provenance for both boards before reconstruction, this audit stops here.

Stages 1-4 were not executed:
- no provider-level arithmetic trace;
- no full 335-player old-vs-new bridge;
- no population-semantic determination;
- no provider consistency audit.

Section 4 of the directive says to stop if an exact board cannot be tied to durable provenance; Section 10 defines the final evidence-boundary classification as **D**. The durable result therefore uses the final four-way taxonomy: **Outcome D - EVIDENCE BOUNDARY**.

## Minimum missing evidence

Two objects are sufficient to reopen this exact audit:

1. The exact old 335-player persisted-baseline Year-1 object, or a canonical equivalent proven to reproduce SHA-256 `70de5578...`, including row-level source provenance.
2. The exact normalized pre-ensemble FFToday and Razzball rows used to create the current 2026-09-18 09:42:31.889752Z board, including provider-effective timestamps and season semantics.

Until those are recovered, do not infer provider rows, fresh-fetch replacements, fix the board, implement the standard-scoring source-coordinate correction, refit Forecast or rerun the extrapolation audit.

## Execution accounting

- Model fits: 0
- Forecast tuning actions: 0
- Route changes: 0
- Production changes: 0
- Fresh provider fetches: 0

**STOP FOR MANAGEMENT REVIEW.**
