# Rolling FUMBLES_LOST — Limitations and Reproducibility

Date: 2026-09-29

## Reproducibility

Research branch:
`research/fumbles-lost-rolling-authority-20260929`

Canonical starting main:
`8d57883759cf2a0f0c0b1fbf4792e15e67a5a1c6`
(`Ops: activate rolling FUMBLES_LOST research gate`)

Frozen protocol commit:
`5163ce90097f53b2e3d5e4ff539e9d1d48e5fcc5`

Validation implementation:
`scripts/run_fumbles_lost_rolling_authority.py`

Workflow:
- run `36525451903`;
- conclusion: **success**;
- artifact `11014727753`;
- digest `sha256:eac8dffa80df5ba9adb6b279267b5c05134fefcbda71146b058fa837dec91db8`;
- retained through 2026-10-29.

Exact governed nflverse source hashes are persisted in `ROLLING_VALIDATION_RESULT.json`.

## Limitations

1. **Only three OOT target seasons.** Rolling evaluation uses held-out 2023-2025. It is chronology-preserving but not a huge era sample.
2. **QB calibration remains weaker.** This was already true in the accepted Week-2 model. The rolling contract does not hide or tune it away; uncertainty grows instead.
3. **Late cutoffs are inherently noisy in season-equivalent units.** Week-17 residual floors are materially larger because a tiny remaining window is annualized.
4. **The materiality rule requires supported fantasy-point uncertainty.** A missing/zero subtotal standard deviation fails closed.
5. **Materiality is consumer-specific.** Passing Simulation does not automatically grant full Forecast coverage or another consumer's authority.
6. **The empirical p99 bound is historical, not a physical maximum.** The additional mean + 1.645×floor branch prevents the bound from relying only on an empirical tail quantile.
7. **No 2026 outcomes were used to tune this contract.** Production scalars use 2022-2025 pseudo-current evidence only.
8. **No preseason backfill.** Rolling authority begins only from actual current-season cutoff evidence.
9. **Week 18 is not a projection cutoff.** The model is authorized Week 2-17 only.
10. **No K/DST consequence.** This work does not repair or reinterpret the separate Hodor K/DST authority boundary.
11. **No runtime architecture conclusion.** #294/#295/#296 lifecycle/restore/publication work is untouched.

## Persisted evidence

- `PROTOCOL_FROZEN.md`
- `ROLLING_PRODUCTION_TABLE.json`
- `validation/ROLLING_VALIDATION_RESULT.json`
- `validation/ROLLING_GATE_RESULTS.csv`
- `validation/ROLLING_CUTOFF_METRICS.csv`
- `validation/ROLLING_CALIBRATION_SCALARS.csv`
- `validation/ROLLING_UNCERTAINTY.csv`
- `validation/MATERIALITY_IMPACT_BOUNDS.csv`
