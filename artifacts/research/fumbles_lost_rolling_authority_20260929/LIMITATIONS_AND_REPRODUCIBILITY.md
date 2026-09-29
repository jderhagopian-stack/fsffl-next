# Rolling FUMBLES_LOST — Limitations and Reproducibility

Date: 2026-09-29

## Reproducibility

Research branch:
`research/fumbles-lost-rolling-authority-20260929`

Original rolling-authority start:
`8d57883759cf2a0f0c0b1fbf4792e15e67a5a1c6`

Original frozen rolling protocol:
`5163ce90097f53b2e3d5e4ff539e9d1d48e5fcc5`

### Rolling Week-2→17 validation

Workflow:
- run `36525451903`;
- conclusion: **success**;
- artifact `11014727753`;
- digest `sha256:eac8dffa80df5ba9adb6b279267b5c05134fefcbda71146b058fa837dec91db8`.

This evidence remains authoritative and was **not reopened** by the lifecycle/P1 correction.

### Population-materiality / season-start validation

Implementation:
`scripts/run_fumbles_lost_materiality_lifecycle.py`

Final workflow:
- run `36559750023`;
- conclusion: **success**;
- artifact `11029278633`;
- digest `sha256:a8f8fc078adde10f7b04b23be873dc77125b195b09542ddf8098f079ae7bc2ae`;
- retained through 2026-10-29.

Exact governed source hashes are persisted in:
- `validation/ROLLING_VALIDATION_RESULT.json`;
- `lifecycle_validation/LIFECYCLE_VALIDATION_RESULT.json`.

## What the P1 correction changed

It did **not** change:
- the Week-2→17 rolling point model;
- any calibration scalar;
- position lost-fumble rates;
- the four-game role prior;
- rolling point-model uncertainty floors.

It changed only the **fallback materiality bound/eligibility**.

The original bound was based on the primary validation population and therefore excluded true cold starts.

The corrected bound:
- is position-wide and tier-independent;
- uses the historical maximum season-equivalent exact-lost-fumble outcome from all completed prior player-seasons;
- can only widen the earlier primary-population bound;
- is validated separately across observed evidence populations.

One unsupported case was found:
- QB cold-start Week 13: 8/9 = 88.9% historical held-out coverage.

Rather than inflate the bound post hoc, Research restricts:
- QB cold-start fallback at Weeks 13-17;
- QB identity-light fallback at Weeks 13-17.

All remaining fallback-eligible observed population/cutoff cells clear the 90% coverage gate.

Identity-light itself is not a directly observed historical mapping-failure population. Its eligibility therefore:
- requires known/non-conflicting canonical position;
- mirrors the matching cold-start eligibility;
- uses the tier-independent position-wide bound.

Unknown/conflicting position fails closed.

## Season-start limitation

No Week-0 or Week-1 first-party point estimate is promoted.

Historical validation supports only:
- explicit omission;
- corrected materiality allowance when eligible and immaterial.

This is deliberately less precise than inventing a preseason/Week-1 model.

The contract does not retroactively create a 2026 preseason artifact.

## Annual rollover limitation

2027 numeric rates/scalars/floors cannot be frozen until finalized 2026 exact weekly data exist.

The annual process is deterministic, but a **minimal governed freeze** remains mandatory before each target season's point authority:
- exact source semantics/hash verification;
- parameter/table build;
- chronology checks;
- bounded adequacy and materiality-population checks.

A failed annual gate returns to explicit omission/materiality or fail-closed authority; it does not trigger automatic model-family search.

## Other limitations

1. Rolling point-model OOT evidence covers only held-out 2023-2025.
2. QB point-model calibration remains weaker than other positions.
3. Late cutoffs are inherently noisy in season-equivalent units.
4. Materiality requires non-zero supported fantasy-point uncertainty; missing/zero subtotal uncertainty fails closed.
5. Materiality is consumer-specific; Simulation permission does not make Forecast coverage complete.
6. Historical maximum is an empirical conservative bound, not a physical mathematical maximum.
7. Late cold-start sample sizes become small; the explicit QB Week-13→17 restriction prevents pretending otherwise.
8. No 2026 outcomes tuned the 2026 rolling point model or materiality threshold.
9. No K/DST authority is changed.
10. No Intrinsic mathematics are changed.
11. No #294/#295/#296 runtime architecture is changed.

## Persisted evidence

Core:
- `PROTOCOL_FROZEN.md`
- `ROLLING_CONTRACT.md`
- `UNCERTAINTY_CONTRACT.md`
- `MATERIALITY_RULE.md`
- `SEASON_START_LIFECYCLE.md`
- `ANNUAL_ROLLOVER_CONTRACT.md`
- `ROLLING_PRODUCTION_TABLE.json`
- `IMPLEMENTATION_HANDOFF.md`
- `FINAL_RESULT.json`

Rolling validation:
- `validation/ROLLING_VALIDATION_RESULT.json`
- `validation/ROLLING_GATE_RESULTS.csv`
- `validation/ROLLING_CUTOFF_METRICS.csv`
- `validation/ROLLING_CALIBRATION_SCALARS.csv`
- `validation/ROLLING_UNCERTAINTY.csv`
- `validation/MATERIALITY_IMPACT_BOUNDS.csv`

Lifecycle/materiality correction:
- `lifecycle_validation/LIFECYCLE_VALIDATION_RESULT.json`
- `lifecycle_validation/MATERIALITY_HELDOUT_BY_POPULATION.csv`
- `lifecycle_validation/MATERIALITY_POOLED_POPULATION_GATES.csv`
- `lifecycle_validation/FALLBACK_PRODUCTION_BOUNDS_2026.csv`
