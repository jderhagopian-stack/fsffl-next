# Forecast Post-Freeze Current-Player Credibility Gate — reproducibility boundary

Date: 2026-09-18  
Authority: one-time post-freeze current-player sanity diagnostic  
Outcome: **C — REPRODUCIBILITY / COORDINATE BOUNDARY**

## Live protected state

Re-fetched before execution:

- research branch live starting head: `4a6ede2a67ef0f6408dafb65dafef7942e016b28`
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

The final Routed Forecast Outcome-A artifacts are present at the research head, including the frozen routing specification.

## Frozen route to be materialized

- default: B2a
- QB experience 0–3: B2a Y2/Y3
- QB experience 4–8: R2 Y2/Y3
- QB experience 9+: R2 Y2, B2a Y3
- RB/WR/TE: B2a Y2/Y3

No current-player board was used to select this route.

## What is reproducible now

### Governed current Year-1 universe
The exact 335-player Y1 coordinate is durable:

- path: `artifacts/research/production_resolution/governed_year1_current_2026_20260918T094231Z/governed_year1_universe.json`
- rows: 335
- position counts: QB 61 / RB 88 / WR 122 / TE 64
- exact artifact SHA-256: `c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f`
- row material SHA-256: `b0e2ddae9296c9b3695534fffd7abdd37a8ecc004ba24687b6574dc654ef49d8`
- scoring basis: governed current-season raw fantasy-point projection coordinate.

### Approved current identity / history coordinate
The replacement current-player materialization coordinate is durable:

- coordinate: `replacement-identity-materialization-v1:2026-09-18T17:06:21Z`
- rows: 335
- coordinate artifact SHA-256: `95fd6565a908b044ca234898cc801749abb2b6aa62a84c2d3c917445d369cda1`
- row-material SHA-256: `1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`
- stable population SHA-256: `095d09458bfe021e7b7075281e8430573514c6d1e5c2dae3d25430f555ceba4b`
- mappings: 73 DIRECT_ID, 227 EXACT_NAME_POSITION, 35 explicit UNMATCHED
- two-genuine-prior-season coverage: 199 / 335
- frozen PIT residual-method parity: PASS, max difference `4.44e-16`

This coordinate was explicitly constructed without executing Y2/Y3 Forecast.

### Previously frozen current-player sentinel
A prior current-player sentinel exists for a different Forecast candidate: fixed routed Forecast + M1a + two-prior-season consistency. It cannot be substituted for the final B2a/R2 route.

The sentinel checkpoint itself records that it is the older candidate and provides only sentinel/current diagnostic outputs for that architecture.

## Missing dependency

The final route cannot be executed exactly without **current-cutoff fitted B2a and R2 treatment material**.

The durable evidence establishes:

1. The B2a bounded-refinement study did not run the preserved 335-player current board because B2a did not freeze under that study's then-governing advance rule.
2. The ordered-state recombination R1/R2 study likewise did not run the 335-player current board because neither R1 nor R2 froze under that study's then-governing advance rule.
3. The later Routed Forecast study reused their already-produced historical rolling-fold prediction rows to select routes. It did not fit a new current-cutoff B2a model or R2 state-conditional learner and did not materialize current Y2/Y3 predictions.
4. The recovered row-level artifacts (`b2_prediction_rows.csv`, `recombination_prediction_rows.csv`, and aligned derivatives) contain historical fold predictions. They do not contain a frozen current-cutoff parameter package that can be applied to the 2026 335-player board without fitting.
5. The replacement identity/history coordinate supplies current identities and PIT history features, but intentionally contains no Y2/Y3 Forecast materialization.

Therefore the missing object is:

> A durable, provenance-locked final-current-cutoff B2a/R2 fitted treatment package (or a row-complete 335-player materialization produced from that already-fitted package) containing the exact B2a correction and R2 state-conditional production machinery needed to compute Y2/Y3 on the frozen 335-player coordinate.

Creating that object now would require fitting/re-estimating B2a and/or R2 on historical data through the current cutoff. Even if the historical methodology is deterministic and already documented, that action is a model refit. This directive explicitly forbids refitting.

## Why no workaround is legal

Not authorized:

- use the older fixed routed + M1a + consistency sentinel as though it were B2a/R2;
- infer current B2a or R2 from historical fold rows;
- fit a final B2a five-bin correction from recovered history;
- fit a final R2 state-conditional learner from recovered history;
- use named-player outputs to choose parameters;
- substitute a different current coordinate;
- compare Y1 against older/non-final Y2/Y3 and issue a credibility judgment.

Those would violate the frozen-model gate.

## Scoring-coordinate consequence

The Y1 side of the requested comparison is available on the governed raw-fantasy-point coordinate.

Final-route Y2/Y3 raw, conditional-active and unconditional fields are not available without the prohibited refit. Therefore the required apples-to-apples Y1/Y2/Y3 scoring-coordinate proof cannot be completed.

No credibility classification of compression or longevity is made.

## Required board disposition

The requested 335-player final-route CSV/XLSX is **not generated** because filling its Y2/Y3 fields would require the prohibited new fit. A partial Y1-only table is deliberately not labeled as the requested Forecast board.

## Final outcome

**C — REPRODUCIBILITY / COORDINATE BOUNDARY.**

The smallest missing dependency is the frozen final-current-cutoff B2a/R2 fitted treatment/materialization package described above.

Execution accounting:

- Forecast model reruns: 0
- Forecast model refits: 0
- coefficient re-estimation: 0
- routing changes: 0
- current-player credibility judgments: 0
- current-player board generated: no
- main changes: 0
- PR #147 changes: 0
- production / Intrinsic / Shapley / Constitution / C=0.25 changes: 0
- model execution runtime: not applicable; no model was executed
- diagnostic wall-clock runtime: not durably instrumented; not invented

STOP FOR MANAGEMENT REVIEW.
